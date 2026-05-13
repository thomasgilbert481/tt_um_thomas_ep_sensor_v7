"""Optimize C_T1 by sweeping its value and finding the slope=0.5 point.

Uses the extracted-values deck. Adds CT1_extra to C_T1.
"""
import subprocess, os, re, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
DECK = "/foss/designs/tt_um_thomas_ep_sensor_v7/scripts/v8/v8_extracted_deck.spice"
WORKDIR = "/tmp/v8_opt_ct1"

# Sweep CT1_extra from 0 to 1.5 pF
CT1_EXTRA_VALUES = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2]  # pF
# ε values in Zhao window
EPS_VALUES = list(np.logspace(np.log10(0.005), np.log10(0.8), 35))


def run_sim(ct1_extra_pf, eps, run_idx):
    """Run ngspice with given CT1_extra and eps."""
    with open(DECK) as f:
        deck = f.read()
    deck = re.sub(r'\.param\s+CT1_extra\s*=\s*\S+', f'.param CT1_extra={ct1_extra_pf*1e-12}', deck)
    deck = re.sub(r'\.param\s+eps\s*=\s*\S+', f'.param eps={eps}', deck)
    deck = deck.replace('.end',
        f"""
.control
ac dec 8000 0.5e9 5e9
let v1mag = abs(v(V1))
let v2mag = abs(v(V2_in))
wrdata {WORKDIR}/run_{run_idx:04d}.dat frequency v1mag v2mag
quit
.endc
.end""")
    deck_path = f"{WORKDIR}/run_{run_idx:04d}.spice"
    with open(deck_path, 'w') as f:
        f.write(deck)
    result = subprocess.run([NGSPICE, "-b", deck_path],
                            capture_output=True, text=True, timeout=120)
    return f"{WORKDIR}/run_{run_idx:04d}.dat" if result.returncode == 0 else None


def find_peaks(freqs, mag, min_prom=0.005, min_height_frac=0.1):
    peaks = []
    threshold = mag.max() * min_height_frac
    for i in range(5, len(mag)-5):
        if mag[i] <= threshold: continue
        if not (mag[i] > mag[i-1] and mag[i] > mag[i+1]): continue
        if not (mag[i] >= mag[i-3] and mag[i] >= mag[i+3]): continue
        window = mag[max(0,i-30):min(len(mag),i+30)]
        prom = mag[i] - window.min()
        if prom < min_prom: continue
        peaks.append((freqs[i], mag[i]))
    if not peaks: return peaks
    clustered = [peaks[0]]
    for p in peaks[1:]:
        if abs(p[0] - clustered[-1][0]) < 50e6:
            if p[1] > clustered[-1][1]:
                clustered[-1] = p
        else:
            clustered.append(p)
    return clustered


def measure(dat_path):
    arr = np.loadtxt(dat_path)
    freqs = arr[:, 0]
    v2 = arr[:, 6]
    peaks = find_peaks(freqs, v2)
    if len(peaks) < 2:
        return 0, len(peaks)
    pf = sorted(p[0] for p in peaks)
    return pf[-1] - pf[0], len(peaks)


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    summary = []
    for ct1_idx, ct1_extra in enumerate(CT1_EXTRA_VALUES):
        results = []
        print(f"\n=== CT1_extra = {ct1_extra} pF (β predicted: ", end="")
        ct1_total = 1.845 + ct1_extra
        c2_cc = 0.836 + 1.398
        beta = (ct1_total / c2_cc) ** 0.5
        print(f"{beta:.4f}) ===")
        for eps_idx, eps in enumerate(EPS_VALUES):
            run_idx = ct1_idx * 100 + eps_idx
            dat = run_sim(ct1_extra, eps, run_idx)
            if dat is None or not os.path.exists(dat):
                continue
            df, n = measure(dat)
            results.append({"eps": eps, "df_hz": df, "n_peaks": n})
        # Slope fit in Zhao window
        in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df_hz"] > 0]
        if len(in_w) >= 2:
            log_eps = np.array([np.log10(r["eps"]) for r in in_w])
            log_df = np.array([np.log10(r["df_hz"]) for r in in_w])
            slope, intercept = np.polyfit(log_eps, log_df, 1)
            pred = slope*log_eps + intercept
            ss_res = np.sum((log_df - pred)**2)
            ss_tot = np.sum((log_df - log_df.mean())**2)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
            print(f"  N_resolved={len(in_w)} in Zhao window, slope={slope:.4f}, R²={r2:.4f}")
            summary.append({"ct1_extra": ct1_extra, "beta": beta, "slope": slope, "r2": r2, "n_resolved": len(in_w)})
        else:
            print(f"  Only {len(in_w)} resolved points in Zhao window")
            summary.append({"ct1_extra": ct1_extra, "beta": beta, "slope": None, "r2": None, "n_resolved": len(in_w)})

    print("\n\n=== SUMMARY ===")
    print(f"{'CT1_ext':>8}  {'β':>6}  {'slope':>7}  {'R²':>6}  {'N_res':>6}")
    for s in summary:
        slope_str = f"{s['slope']:.4f}" if s['slope'] is not None else "N/A"
        r2_str = f"{s['r2']:.4f}" if s['r2'] is not None else "N/A"
        print(f"{s['ct1_extra']:8.2f}  {s['beta']:6.4f}  {slope_str:>7}  {r2_str:>6}  {s['n_resolved']:6d}")

    with open(f"{WORKDIR}/optimization_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
