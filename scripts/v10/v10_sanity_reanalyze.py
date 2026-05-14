"""v10 sanity: re-analyze with correct column indexing."""
import os, json
import numpy as np

WORKDIR = "/tmp/v10_sanity"
CV_WEIGHTS_FF = [20, 41, 82, 164, 328, 656, 1312, 1312]
C_T1_FF = 1845


def enumerate_eps():
    s = set()
    for bits in range(256):
        v = sum(CV_WEIGHTS_FF[i] for i in range(8) if bits & (1 << i))
        s.add(round(v / (2 * C_T1_FF), 6))
    return sorted(s)


def find_peaks(freq, mag):
    p = []
    for i in range(2, len(mag)-2):
        if mag[i] > mag[i-1] and mag[i] > mag[i+1] and mag[i] >= mag[i-2] and mag[i] >= mag[i+2]:
            p.append((freq[i], mag[i]))
    return p


def filt(peaks, hf=0.15, sep=80e6):
    if not peaks: return []
    mx = max(p[1] for p in peaks)
    f = sorted([p for p in peaks if p[1] >= hf*mx], key=lambda p: p[0])
    if not f: return []
    out = [f[0]]
    for p in f[1:]:
        if p[0] - out[-1][0] < sep:
            if p[1] > out[-1][1]: out[-1] = p
        else: out.append(p)
    return out


def measure(dat):
    arr = np.loadtxt(dat)
    if arr.ndim == 1: arr = arr.reshape(1, -1)
    freq = arr[:, 0]
    v1 = arr[:, 4]; v2 = arr[:, 6]
    p1 = filt(find_peaks(freq, v1))
    p2 = filt(find_peaks(freq, v2))
    peaks = p1 if len(p1) >= 2 else (p2 if len(p2) >= 2 else p1)
    df = 0; f0 = 0
    if len(peaks) >= 2:
        pf = sorted(p[0] for p in peaks); df = pf[-1] - pf[0]; f0 = sum(pf)/len(pf)
    elif len(peaks) == 1:
        f0 = peaks[0][0]
    return df, f0, len(p1), len(p2)


def main():
    eps_list = [e for e in enumerate_eps() if e == 0 or (0.005 <= e <= 0.3)]
    results = []
    for i, eps in enumerate(eps_list):
        dat = f"{WORKDIR}/eps_{i:03d}.dat"
        if not os.path.exists(dat): continue
        df, f0, n1, n2 = measure(dat)
        results.append({"eps": eps, "df": df, "f0": f0, "n_v1": n1, "n_v2": n2})

    r0 = next((r for r in results if r["eps"] == 0.0), None)
    print(f"Got {len(results)} sims")
    if r0:
        print(f"\nε=0: n_v1={r0['n_v1']} n_v2={r0['n_v2']} Δf={r0['df']/1e6:.1f}MHz f0={r0['f0']/1e9:.3f}GHz")

    in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
    print(f"Resolved in Zhao window: {len(in_w)}")
    if len(in_w) >= 2:
        le = np.array([np.log10(r["eps"]) for r in in_w])
        ld = np.array([np.log10(r["df"]) for r in in_w])
        slope, ic = np.polyfit(le, ld, 1)
        pred = slope*le + ic
        sst = np.sum((ld - ld.mean())**2)
        r2 = 1 - np.sum((ld-pred)**2)/sst if sst > 0 else 0
        print(f"SLOPE={slope:.4f} R²={r2:.4f}")
        print(f"Pass slope∈[0.48,0.55]: {'YES' if 0.48 <= slope <= 0.55 else 'NO'}")
        print(f"Pass ≥30 resolved: {'YES' if len(in_w) >= 30 else 'NO'}")

    with open(f"{WORKDIR}/v10_sanity.json", 'w') as f:
        json.dump({"results": results}, f, indent=2)


if __name__ == "__main__":
    main()
