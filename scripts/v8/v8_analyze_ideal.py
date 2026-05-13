"""Analyze ideal sim results with corrected peak detection."""
import os, numpy as np

WORKDIR = "/tmp/v8_ideal_sim"
EPS_VALUES = [0.0] + list(np.logspace(np.log10(0.001), np.log10(0.8), 60))


def find_peaks_simple(freqs, mag):
    """Find local maxima. Returns list of (freq, mag)."""
    peaks = []
    for i in range(2, len(mag)-2):
        if mag[i] > mag[i-1] and mag[i] > mag[i+1]:
            # Need broader confirmation
            if mag[i] >= mag[i-2] and mag[i] >= mag[i+2]:
                peaks.append((freqs[i], mag[i]))
    # Sort by mag descending
    peaks.sort(key=lambda p: -p[1])
    return peaks


def filter_peaks(peaks, min_height_frac=0.20, min_separation_hz=50e6):
    if not peaks: return []
    max_mag = peaks[0][1]
    filtered = [p for p in peaks if p[1] > min_height_frac * max_mag]
    # Cluster close peaks
    if not filtered: return []
    filtered.sort(key=lambda p: p[0])  # sort by freq
    result = [filtered[0]]
    for p in filtered[1:]:
        if p[0] - result[-1][0] < min_separation_hz:
            if p[1] > result[-1][1]:
                result[-1] = p
        else:
            result.append(p)
    return result


results = []
for idx, eps in enumerate(EPS_VALUES):
    dat = f"{WORKDIR}/sweep_{idx:03d}.dat"
    if not os.path.exists(dat): continue
    try:
        arr = np.loadtxt(dat)
        if arr.ndim == 1: arr = arr.reshape(1, -1)
        freq = arr[:, 0]
        v2 = arr[:, 6]
        peaks = find_peaks_simple(freq, v2)
        peaks_f = filter_peaks(peaks, min_height_frac=0.40, min_separation_hz=30e6)
        n = len(peaks_f)
        if n >= 2:
            pf = sorted(p[0] for p in peaks_f)
            df = pf[-1] - pf[0]
        else:
            df = 0
        results.append({"eps": eps, "df": df, "n": n,
                        "peaks_v2": [(p[0]/1e9, p[1]) for p in peaks_f]})
    except Exception as e:
        print(f"FAIL {idx}: {e}")

# Print
for r in results:
    if r["eps"] < 0.001:
        continue
    print(f"ε={r['eps']:.5f}  n={r['n']}  Δf={r['df']/1e6:.2f}MHz  peaks={[f'({f:.3f},{m:.3f})' for f,m in r['peaks_v2'][:3]]}")

print("\n=== Slope in Zhao window [0.031, 0.25] ===")
in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
print(f"Resolved points: {len(in_w)}")
if len(in_w) >= 2:
    log_eps = np.array([np.log10(r["eps"]) for r in in_w])
    log_df = np.array([np.log10(r["df"]) for r in in_w])
    slope, intercept = np.polyfit(log_eps, log_df, 1)
    pred = slope*log_eps + intercept
    ss_tot = np.sum((log_df - log_df.mean())**2)
    r2 = 1 - np.sum((log_df-pred)**2)/ss_tot if ss_tot > 0 else 0
    print(f"  slope = {slope:.4f}  R² = {r2:.4f}")

# ε=0 EP check
r0 = next((r for r in results if r["eps"] == 0.0), None)
if r0:
    print(f"\nε=0: n_peaks = {r0['n']}")
    for f, m in r0["peaks_v2"]:
        print(f"   peak at f={f:.4f} GHz, mag={m:.4f}")
