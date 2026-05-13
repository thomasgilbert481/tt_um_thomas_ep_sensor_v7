"""Simple sweep: test slope with different C_T1_total values."""
import subprocess, os, re, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v8_simple"

DECK = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

Vin     v_vna    GND  AC 1
R_VNA   v_vna    v_pad1in 50
L_BOND1 v_pad1in v_pad1n  1.5e-9
R_BOND1 v_pad1n  v_pad1n2 0.05
C_PAD1  v_pad1n2 GND      125e-15
R_chip1 v_pad1n2 V1       0.5

L1 V1 nL1 1.351e-9
R1 nL1 0 5.0
C_T1 V1 GND  {ct1_val:.4e}
C_SRF1 V1 GND 0.18e-12

L2 V2_in nL2 1.351e-9
R2 nL2 0 5.0
C_T2 V2_in GND 0.836e-12
C_SRF2 V2_in GND 0.18e-12

K_M12 L1 L2 -0.032

E_buf Vbuf 0 V1 0 1.0

Cc      Vbuf    V2_in   1.398e-12

.param eps={eps}
Ceps    V1     V2_in   'max(2*1.845e-12*eps, 1e-21)'

R_chip2 V2_in  v_pad2n  0.5
C_PAD2  v_pad2n GND    125e-15
L_BOND2 v_pad2n v_pad2  1.5e-9
R_load  v_pad2  GND     50

.ac dec 8000 0.5e9 5e9
.control
ac dec 8000 0.5e9 5e9
let v1mag = abs(v(V1))
let v2mag = abs(v(V2_in))
wrdata {out} frequency v1mag v2mag
quit
.endc
.end
"""


def run(ct1_pf, eps, run_id):
    out = f"{WORKDIR}/run_{run_id:04d}.dat"
    deck = DECK.format(ct1_val=ct1_pf*1e-12, eps=eps, out=out)
    deck_path = f"{WORKDIR}/run_{run_id:04d}.spice"
    with open(deck_path, 'w') as f:
        f.write(deck)
    r = subprocess.run([NGSPICE, "-b", deck_path],
                       capture_output=True, text=True, timeout=120)
    return out if r.returncode == 0 and os.path.exists(out) else None


def find_peaks(freqs, mag):
    peaks = []
    for i in range(2, len(mag)-2):
        if mag[i] > mag[i-1] and mag[i] > mag[i+1]:
            if mag[i] >= mag[i-2] and mag[i] >= mag[i+2]:
                peaks.append((freqs[i], mag[i]))
    return peaks


def filter_peaks(peaks, min_height_frac=0.25, min_sep_hz=30e6):
    if not peaks: return []
    max_mag = max(p[1] for p in peaks)
    f = sorted([p for p in peaks if p[1] >= min_height_frac*max_mag], key=lambda p: p[0])
    if not f: return []
    result = [f[0]]
    for p in f[1:]:
        if p[0] - result[-1][0] < min_sep_hz:
            if p[1] > result[-1][1]: result[-1] = p
        else:
            result.append(p)
    return result


def measure(dat):
    arr = np.loadtxt(dat)
    if arr.ndim == 1: arr = arr.reshape(1, -1)
    freq = arr[:, 0]
    v1 = arr[:, 4]
    v2 = arr[:, 6]
    # Try V1 first (where splitting is more visible)
    p1 = filter_peaks(find_peaks(freq, v1))
    p2 = filter_peaks(find_peaks(freq, v2))
    # Use V1 if shows >=2 peaks, else V2
    use_peaks = p1 if len(p1) >= 2 else p2
    if len(use_peaks) < 2:
        return 0, len(p1), len(p2)
    pf = sorted(p[0] for p in use_peaks)
    return pf[-1] - pf[0], len(p1), len(p2)


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    # Sweep ε across Zhao window
    eps_values = list(np.logspace(np.log10(0.005), np.log10(0.5), 25))
    # Test ct1_total values
    ct1_list = [1.845, 2.0, 2.10, 2.20, 2.24, 2.30, 2.40, 2.50]

    print(f"\nMeasuring slope with V1 fallback to V2:")
    print(f"{'CT1':>5} {'β':>6} {'slope':>7} {'R²':>6} {'n_zhao':>7} {'Δf(eps=0.031)':>14}")
    summary = []
    for ct1_idx, ct1 in enumerate(ct1_list):
        ct1_total = ct1
        beta = (ct1_total / (0.836 + 1.398)) ** 0.5
        results = []
        for eps_idx, eps in enumerate(eps_values):
            run_id = ct1_idx * 100 + eps_idx
            dat = run(ct1_total, eps, run_id)
            if dat is None: continue
            df, n1, n2 = measure(dat)
            results.append({"eps": eps, "df": df, "n1": n1, "n2": n2})
        in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
        if len(in_w) < 2:
            print(f"{ct1:5.2f} {beta:6.4f} {'N/A':>7} {'N/A':>6} {len(in_w):7d}")
            continue
        le = np.array([np.log10(r["eps"]) for r in in_w])
        ld = np.array([np.log10(r["df"]) for r in in_w])
        slope, ic = np.polyfit(le, ld, 1)
        pred = slope*le + ic
        sst = np.sum((ld - ld.mean())**2)
        r2 = 1 - np.sum((ld-pred)**2)/sst if sst > 0 else 0
        # Smallest in-window eps Δf
        rmin = min(in_w, key=lambda r: r["eps"])
        df_min = rmin["df"]
        print(f"{ct1:5.2f} {beta:6.4f} {slope:7.4f} {r2:6.4f} {len(in_w):7d} {df_min/1e6:14.1f}")
        summary.append({"ct1": ct1, "beta": beta, "slope": slope, "r2": r2, "n_zhao": len(in_w)})

    with open(f"{WORKDIR}/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
