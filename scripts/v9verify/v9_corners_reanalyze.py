"""Re-analyze v9 corner sweep with correct column indices."""
import os, json
import numpy as np

WORKDIR = "/tmp/v9verify_corners"
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
    v1 = arr[:, 4]   # CORRECTED
    v2 = arr[:, 6]
    p1 = filt(find_peaks(freq, v1))
    p2 = filt(find_peaks(freq, v2))
    peaks = p1 if len(p1) >= 2 else (p2 if len(p2) >= 2 else p1)
    df = 0; f0 = 0
    if len(peaks) >= 2:
        pf = sorted(p[0] for p in peaks); df = pf[-1] - pf[0]; f0 = sum(pf)/len(pf)
    elif len(peaks) == 1:
        f0 = peaks[0][0]
    return df, f0, len(p1), len(p2)


CORNERS = ["SS_85_1.62V", "TT_27_1.80V", "FF_0_1.98V"]


def main():
    full_eps = [e for e in enumerate_eps() if e == 0 or (0.005 <= e <= 0.3)]
    eps_subset = full_eps[::3]
    if 0 not in eps_subset: eps_subset = [0] + eps_subset

    summary = {}
    for corner in CORNERS:
        print(f"\n=== {corner} ===")
        results = []
        for i, eps in enumerate(eps_subset):
            dat = f"{WORKDIR}/{corner}_eps{i:03d}.dat"
            if not os.path.exists(dat): continue
            df, f0, n1, n2 = measure(dat)
            results.append({"eps": eps, "df": df, "f0": f0, "n_v1": n1, "n_v2": n2})
        r0 = next((r for r in results if r["eps"] == 0.0), None)
        in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
        f0_eps0 = r0["f0"] if r0 else 0
        # Single-peak shift slope (for buffer-limited regime)
        valid_shift = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["f0"] > 0]
        shift_slope = None
        if r0 and len(valid_shift) >= 2:
            le = np.array([np.log10(r["eps"]) for r in valid_shift])
            shifts = np.array([f0_eps0 - r["f0"] for r in valid_shift])
            # Only fit positive shifts
            mask = shifts > 0
            if mask.sum() >= 2:
                ld = np.log10(shifts[mask])
                lex = le[mask]
                slope, ic = np.polyfit(lex, ld, 1)
                shift_slope = float(slope)
        # Two-peak split slope (if any resolved)
        split_slope = None
        if len(in_w) >= 2:
            le = np.array([np.log10(r["eps"]) for r in in_w])
            ld = np.array([np.log10(r["df"]) for r in in_w])
            s, ic = np.polyfit(le, ld, 1)
            split_slope = float(s)
        print(f"  n_v1@ε=0={r0['n_v1'] if r0 else 'N/A'}  n_v2@ε=0={r0['n_v2'] if r0 else 'N/A'}")
        print(f"  f0@ε=0={f0_eps0/1e9:.3f} GHz")
        print(f"  resolved 2-peak: {len(in_w)}")
        print(f"  single-peak shift slope: {shift_slope}")
        print(f"  2-peak split slope: {split_slope}")
        summary[corner] = {"f0_eps0_GHz": f0_eps0/1e9, "n_resolved_2peak": len(in_w),
                            "shift_slope": shift_slope, "split_slope": split_slope}

    f0s = [v["f0_eps0_GHz"] for v in summary.values() if v["f0_eps0_GHz"] > 0]
    shift_slopes = [v["shift_slope"] for v in summary.values() if v["shift_slope"] is not None]
    print("\n=== Envelope ===")
    if f0s: print(f"f0 envelope: {min(f0s):.3f} – {max(f0s):.3f} GHz")
    if shift_slopes: print(f"shift slope envelope: {min(shift_slopes):.3f} – {max(shift_slopes):.3f}")

    with open(f"{WORKDIR}/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
