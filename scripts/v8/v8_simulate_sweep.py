"""v8 EP sensor simulation: sweep eps, extract Δf, fit slope.

Uses the v4_final.spice deck as the simulation model (matches v8 silicon
topology: in-place thicken spirals + PGS strip).

Sweep plan:
- ε = 0 (EP condition): single peak verification
- 30 ε values log-spaced in [0.003, 0.6]: covers Zhao window [0.031, 0.25]
- Extract peak locations from |V(V1)| AC response (or |V(V2_in)|)
- For each ε > 0: Δf = |f_peak1 - f_peak2|
- Fit log(Δf) vs log(ε) in Zhao window, extract slope

Output:
- CSV: eps, Δf, peak positions
- Plot: log-log Δf vs ε with slope fit
"""
import subprocess
import os
import sys
import re
import json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
DECK_TEMPLATE = "/foss/designs/tt_um_thomas_ep_sensor_v7/src/ep_sensor_v4_final.spice"
WORKDIR = "/tmp/v8_sim"

# Zhao window
EPS_LO, EPS_HI = 0.031, 0.25

def run_ngspice(eps_value, sim_idx):
    """Run ngspice for a single eps value, return ac.dat path."""
    with open(DECK_TEMPLATE) as f:
        deck = f.read()
    # Replace .param eps=0 with .param eps=<value>
    deck = re.sub(r'\.param\s+eps\s*=\s*\S+', f'.param eps={eps_value}', deck)
    # Add control block to write data
    deck = deck.replace('.end',
        f"""
.control
ac dec 8000 0.5e9 5e9
let v1mag = abs(v(V1))
let v2mag = abs(v(V2_in))
wrdata {WORKDIR}/sweep_{sim_idx:03d}.dat frequency v1mag v2mag
quit
.endc
.end""")
    deck_path = f"{WORKDIR}/deck_{sim_idx:03d}.spice"
    with open(deck_path, 'w') as f:
        f.write(deck)
    result = subprocess.run([NGSPICE, "-b", deck_path],
                            capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"ngspice failed for eps={eps_value}: {result.stderr[:500]}")
        return None
    return f"{WORKDIR}/sweep_{sim_idx:03d}.dat"


def load_dat(path):
    """Load ngspice wrdata file: 7 columns are:
    col 0: freq, col 1: freq (real), col 2: 0 (imag), col 3: freq, col 4: v1mag,
    col 5: freq, col 6: v2mag."""
    arr = np.loadtxt(path)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr[:, 0], arr[:, 4], arr[:, 6]


def find_peaks_robust(freqs, mag, min_height_frac=0.3):
    """Find local maxima in magnitude. Return list of (freq, mag) sorted by mag descending."""
    # Smooth slightly using moving average
    n = len(mag)
    smoothed = mag.copy()
    # local max detection
    peaks = []
    threshold = mag.max() * min_height_frac
    for i in range(2, n-2):
        if (smoothed[i] > smoothed[i-1] and smoothed[i] > smoothed[i+1]
                and smoothed[i] > smoothed[i-2] and smoothed[i] > smoothed[i+2]
                and smoothed[i] > threshold):
            peaks.append((freqs[i], smoothed[i]))
    return peaks


def compute_df(eps, dat_path):
    """Return (df_hz, peak_freqs, n_peaks).
    Use V(V2_in) — this is the S21 transmission observable.
    For EP type-2 perturbation, V2_in shows 1 peak at ε=0 and splits into 2 at ε>0."""
    freqs, v1, v2 = load_dat(dat_path)
    # use V(V2_in) - the S21 transmission observable
    peaks = find_peaks_robust(freqs, v2, min_height_frac=0.20)
    if len(peaks) == 0:
        return 0, [], 0
    peaks_sorted = sorted(peaks, key=lambda p: p[0])
    pf = [p[0] for p in peaks_sorted]
    n = len(peaks_sorted)
    if n == 1:
        return 0, pf, 1
    df = pf[-1] - pf[0]
    return df, pf, n


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    # ε values: 0 plus 30 log-spaced in [0.003, 0.6]
    eps_values = [0.0] + list(np.logspace(np.log10(0.003), np.log10(0.6), 30))
    results = []
    for idx, eps in enumerate(eps_values):
        dat = f"{WORKDIR}/sweep_{idx:03d}.dat"
        if not os.path.exists(dat):
            dat = run_ngspice(eps, idx)
        if dat is None or not os.path.exists(dat):
            print(f"[{idx:03d}] eps={eps:.5f} sim FAILED")
            continue
        df, pf, n = compute_df(eps, dat)
        # Report
        f0_str = f"f0={pf[0]/1e9:.4f}GHz" if n >= 1 else "no peaks"
        results.append({"eps": eps, "df_hz": df, "n_peaks": n,
                        "peaks_ghz": [p/1e9 for p in pf]})
        print(f"[{idx:03d}] eps={eps:.5f}  n_peaks={n}  Δf={df/1e6:.3f} MHz  peaks={[round(p/1e9,4) for p in pf]}")
    # Save
    with open(f"{WORKDIR}/sweep_results.json", 'w') as f:
        json.dump(results, f, indent=2)

    # Slope fit in Zhao window
    print("\n=== Slope fit in Zhao window ε ∈ [0.031, 0.25] ===")
    in_window = [r for r in results if EPS_LO <= r["eps"] <= EPS_HI and r["df_hz"] > 0]
    print(f"Points in window: {len(in_window)}")
    if len(in_window) >= 2:
        log_eps = np.array([np.log10(r["eps"]) for r in in_window])
        log_df = np.array([np.log10(r["df_hz"]) for r in in_window])
        slope, intercept = np.polyfit(log_eps, log_df, 1)
        print(f"  Slope: {slope:.4f}")
        print(f"  Intercept: {intercept:.4f}")
        # R-squared
        pred = slope * log_eps + intercept
        ss_res = np.sum((log_df - pred)**2)
        ss_tot = np.sum((log_df - log_df.mean())**2)
        r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
        print(f"  R²: {r2:.4f}")

    # EP condition check
    eps0_result = next((r for r in results if r["eps"] == 0.0), None)
    if eps0_result:
        print(f"\n=== EP Condition (ε=0) ===")
        print(f"  n_peaks: {eps0_result['n_peaks']}")
        if eps0_result['n_peaks'] == 1:
            print(f"  SINGLE PEAK at f={eps0_result['peaks_ghz'][0]:.4f} GHz ✓")
        else:
            print(f"  {eps0_result['n_peaks']} peaks — NOT a clean EP")
            print(f"  Peaks: {eps0_result['peaks_ghz']}")


if __name__ == "__main__":
    main()
