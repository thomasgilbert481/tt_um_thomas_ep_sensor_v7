"""Analyze V(V1) for peak splitting (instead of V(V2_in))."""
import os, numpy as np

WORKDIR = "/tmp/v8_ideal_sim"
EPS_VALUES = [0.0] + list(np.logspace(np.log10(0.001), np.log10(0.8), 60))


def find_peaks_local(freqs, mag):
    peaks = []
    for i in range(2, len(mag)-2):
        if mag[i] > mag[i-1] and mag[i] > mag[i+1]:
            if mag[i] >= mag[i-2] and mag[i] >= mag[i+2]:
                peaks.append((freqs[i], mag[i]))
    return peaks


def filter_peaks(peaks, min_height_frac=0.40, min_separation_hz=30e6):
    if not peaks: return []
    max_mag = max(p[1] for p in peaks)
    filtered = [p for p in peaks if p[1] >= min_height_frac * max_mag]
    filtered.sort(key=lambda p: p[0])
    if not filtered: return []
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
    arr = np.loadtxt(dat)
    if arr.ndim == 1: arr = arr.reshape(1, -1)
    freq = arr[:, 0]
    v1 = arr[:, 4]
    peaks = find_peaks_local(freq, v1)
    peaks_f = filter_peaks(peaks, min_height_frac=0.40)
    df = peaks_f[-1][0] - peaks_f[0][0] if len(peaks_f) >= 2 else 0
    results.append({"eps": eps, "df": df, "n": len(peaks_f),
                    "peaks": [(p[0]/1e9, p[1]) for p in peaks_f]})

print("V(V1) peak analysis:")
for r in results:
    if r["n"] >= 2 or r["eps"] in [0, 0.03, 0.06, 0.12, 0.25]:
        peak_str = " ".join(f"({f:.4f},{m:.3f})" for f, m in r["peaks"])
        print(f"  ε={r['eps']:.5f}  n={r['n']}  Δf={r['df']/1e6:.1f} MHz  peaks={peak_str}")

# More relaxed peak detection
print("\n\nWith looser min_height_frac=0.25:")
for r in results:
    arr = np.loadtxt(f"{WORKDIR}/sweep_{EPS_VALUES.index(r['eps']):03d}.dat")
    freq = arr[:, 0]
    v1 = arr[:, 4]
    peaks = find_peaks_local(freq, v1)
    peaks_f = filter_peaks(peaks, min_height_frac=0.25)
    df = peaks_f[-1][0] - peaks_f[0][0] if len(peaks_f) >= 2 else 0
    r["df_loose"] = df
    r["n_loose"] = len(peaks_f)
    if len(peaks_f) >= 2:
        peak_str = " ".join(f"({p[0]/1e9:.4f},{p[1]:.3f})" for p in peaks_f)
        print(f"  ε={r['eps']:.5f}  n={r['n_loose']}  Δf={df/1e6:.1f} MHz  peaks={peak_str}")
