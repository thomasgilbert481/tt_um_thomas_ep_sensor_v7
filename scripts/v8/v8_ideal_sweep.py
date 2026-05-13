"""Sweep ε with IDEAL buffer deck to isolate EP physics from OTA issues."""
import subprocess, os, re, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
DECK_TEMPLATE = "/foss/designs/tt_um_thomas_ep_sensor_v7/scripts/v8/v8_ideal_deck.spice"
WORKDIR = "/tmp/v8_ideal_sim"

def run_ngspice(eps_value, sim_idx):
    with open(DECK_TEMPLATE) as f:
        deck = f.read()
    deck = re.sub(r'\.param\s+eps\s*=\s*\S+', f'.param eps={eps_value}', deck)
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
    return f"{WORKDIR}/sweep_{sim_idx:03d}.dat" if result.returncode == 0 else None


def load_dat(path):
    arr = np.loadtxt(path)
    return arr[:, 0], arr[:, 4], arr[:, 6]


def find_peaks(freqs, mag, min_prom=0.005, min_height_frac=0.10):
    peaks = []
    threshold = mag.max() * min_height_frac
    for i in range(5, len(mag)-5):
        if mag[i] <= threshold: continue
        if not (mag[i] > mag[i-1] and mag[i] > mag[i+1]): continue
        if not (mag[i] >= mag[i-3] and mag[i] >= mag[i+3]): continue
        # prominence: distance from this peak to lowest min in 30 samples
        window = mag[max(0,i-30):min(len(mag),i+30)]
        prom = mag[i] - window.min()
        if prom < min_prom: continue
        peaks.append((freqs[i], mag[i]))
    # cluster close peaks (within 50 MHz)
    if not peaks: return peaks
    clustered = [peaks[0]]
    for p in peaks[1:]:
        if abs(p[0] - clustered[-1][0]) < 50e6:
            if p[1] > clustered[-1][1]:
                clustered[-1] = p
        else:
            clustered.append(p)
    return clustered


def compute_df(eps, dat):
    freqs, v1, v2 = load_dat(dat)
    # Try BOTH V1 and V2 for peak finding
    peaks_v2 = find_peaks(freqs, v2)
    peaks_v1 = find_peaks(freqs, v1)
    # For S21 (= V2), use V2 peaks
    peaks = peaks_v2 if peaks_v2 else peaks_v1
    if len(peaks) == 0:
        return 0, [], 0, peaks_v1, peaks_v2
    pf = sorted(p[0] for p in peaks)
    n = len(pf)
    df = pf[-1] - pf[0] if n >= 2 else 0
    return df, pf, n, peaks_v1, peaks_v2


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    # 50 ε values log-spaced + ε=0
    eps_values = [0.0] + list(np.logspace(np.log10(0.001), np.log10(0.8), 60))
    results = []
    for idx, eps in enumerate(eps_values):
        dat = f"{WORKDIR}/sweep_{idx:03d}.dat"
        if not os.path.exists(dat):
            dat = run_ngspice(eps, idx)
        if dat is None or not os.path.exists(dat):
            print(f"[{idx:03d}] eps={eps:.5f} FAILED")
            continue
        df, pf, n, pv1, pv2 = compute_df(eps, dat)
        results.append({"eps": eps, "df_hz": df, "n_peaks": n,
                        "peaks_v2": [(f/1e9, m) for f, m in pv2],
                        "peaks_v1": [(f/1e9, m) for f, m in pv1]})
        peaks_str = " ".join(f"{f/1e9:.3f}" for f in pf)
        print(f"[{idx:03d}] eps={eps:.5f}  n_v1={len(pv1)} n_v2={len(pv2)}  Δf={df/1e6:.3f}MHz  peaks=[{peaks_str}]")
    with open(f"{WORKDIR}/sweep_results.json", 'w') as f:
        json.dump(results, f, indent=2)

    # Slope analysis in Zhao window
    print("\n=== Slope fit (window 0.031-0.25) ===")
    in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df_hz"] > 0]
    print(f"Points in Zhao window: {len(in_w)}")
    if len(in_w) >= 2:
        log_eps = np.array([np.log10(r["eps"]) for r in in_w])
        log_df = np.array([np.log10(r["df_hz"]) for r in in_w])
        slope, intercept = np.polyfit(log_eps, log_df, 1)
        pred = slope*log_eps + intercept
        ss_res = np.sum((log_df - pred)**2)
        ss_tot = np.sum((log_df - log_df.mean())**2)
        r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
        print(f"  Slope: {slope:.4f}  Intercept: {intercept:.4f}  R²: {r2:.4f}")

    print("\n=== ε=0 EP condition ===")
    r0 = next((r for r in results if r["eps"] == 0.0), None)
    if r0:
        print(f"  V2 peaks: {r0['peaks_v2']}")
        print(f"  V1 peaks: {r0['peaks_v1']}")

if __name__ == "__main__":
    main()
