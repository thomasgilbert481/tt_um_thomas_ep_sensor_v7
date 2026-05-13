"""Simulate chip with cv-array's ACTUAL ε values (256 binary combinations).
Verify ≥11 points in Zhao window [0.031, 0.25] with slope ∈ [0.45, 0.55].
"""
import subprocess, os, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v8_cvarray_sim"

# cv-array weights (fF) from extracted netlist
# Cv0..Cv7 = 20, 41, 82, 164, 328, 656, 1312, 1312 fF (binary weighted, doubled MSB)
CV_WEIGHTS_FF = [20, 41, 82, 164, 328, 656, 1312, 1312]
C_T1_FF = 1845  # 8WUMYD
# ε = total_cv / (2 * C_T1)

def enumerate_eps():
    """Enumerate all 256 cv-array combinations and their ε values."""
    eps_dict = {}  # eps_value -> bit_combo
    for bits in range(256):
        total = sum(CV_WEIGHTS_FF[i] for i in range(8) if bits & (1 << i))
        eps = total / (2 * C_T1_FF)
        eps_dict.setdefault(round(eps, 6), []).append(bits)
    return eps_dict

DECK = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

Vin     v_vna    GND  AC 1
R_VNA   v_vna    v_pad1in 50
L_BOND1 v_pad1in v_pad1n  1.5e-9
R_BOND1 v_pad1n  v_pad1n2 0.05
C_PAD1  v_pad1n2 GND      125e-15
R_chip1 v_pad1n2 V1       0.5

L1 V1 nL1 1.351e-9
R1 nL1 0 5.0
C_T1 V1 GND  1.845p
C_SRF1 V1 GND 0.18e-12

L2 V2_in nL2 1.351e-9
R2 nL2 0 5.0
C_T2 V2_in GND 0.836p
C_SRF2 V2_in GND 0.18e-12

K_M12 L1 L2 -0.032

E_buf Vbuf 0 V1 0 1.0

Cc      Vbuf    V2_in   1.398p

.param eps={eps}
Ceps    V1     V2_in   'max(2*1.845e-12*eps, 1e-21)'

R_chip2 V2_in  v_pad2n  0.5
C_PAD2  v_pad2n GND    125e-15
L_BOND2 v_pad2n v_pad2  1.5e-9
R_load  v_pad2  GND     50

.control
ac dec 2000 0.5e9 6e9
let v1mag = abs(v(V1))
let v2mag = abs(v(V2_in))
wrdata {out} frequency v1mag v2mag
quit
.endc
.end
"""

def run(eps, run_id):
    out = f"{WORKDIR}/eps_{run_id}.dat"
    if os.path.exists(out):
        return out
    deck = DECK.format(eps=eps, out=out)
    deck_path = f"{WORKDIR}/eps_{run_id}.spice"
    with open(deck_path, 'w') as f:
        f.write(deck)
    r = subprocess.run([NGSPICE, "-b", deck_path],
                       capture_output=True, text=True, timeout=60)
    return out if r.returncode == 0 and os.path.exists(out) else None


def find_peaks(freqs, mag):
    peaks = []
    for i in range(2, len(mag)-2):
        if mag[i] > mag[i-1] and mag[i] > mag[i+1]:
            if mag[i] >= mag[i-2] and mag[i] >= mag[i+2]:
                peaks.append((freqs[i], mag[i]))
    return peaks


def filter_peaks(peaks, min_height_frac=0.20, min_sep_hz=80e6):
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
    # Use V1 — it shows splitting better than V2 for off-EP chip
    p1 = filter_peaks(find_peaks(freq, v1), min_height_frac=0.20)
    p2 = filter_peaks(find_peaks(freq, v2), min_height_frac=0.20)
    # Pick the one with more peaks (or V1 default)
    peaks = p1 if len(p1) >= 2 else (p2 if len(p2) >= 2 else p1)
    if len(peaks) >= 2:
        pf = sorted(p[0] for p in peaks)
        return pf[-1] - pf[0], len(p1), len(p2), pf
    return 0, len(p1), len(p2), [p[0] for p in peaks] if peaks else []


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    eps_dict = enumerate_eps()
    # Sort unique ε values
    unique_eps = sorted(eps_dict.keys())
    print(f"Total unique ε values from cv-array: {len(unique_eps)}")
    in_zhao = [e for e in unique_eps if 0.031 <= e <= 0.25]
    print(f"ε in Zhao window [0.031, 0.25]: {len(in_zhao)}")

    # Run sim at each unique ε
    results = []
    print("\nRunning ngspice for each unique ε...")
    for i, eps in enumerate(unique_eps):
        dat = run(eps, f"{i:03d}")
        if dat is None:
            continue
        df, n1, n2, pks = measure(dat)
        results.append({
            "eps": eps,
            "bits": eps_dict[eps][0],  # representative
            "df": df,
            "n_v1": n1, "n_v2": n2,
            "peaks_ghz": [p/1e9 for p in pks],
        })
        if i % 30 == 0:
            print(f"  {i}/{len(unique_eps)}: eps={eps:.5f} Δf={df/1e6:.1f}MHz")

    # Filter to Zhao window with measurable Δf
    in_w_res = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
    print(f"\nResolved in Zhao window: {len(in_w_res)}")

    # ε=0 case
    r0 = next((r for r in results if r["eps"] == 0.0), None)
    if r0:
        print(f"\n=== ε=0 EP check ===")
        print(f"  n_v1 = {r0['n_v1']}, n_v2 = {r0['n_v2']}")
        print(f"  Peaks: {r0['peaks_ghz']}")
        if r0['n_v2'] == 1:
            print(f"  V2 single peak (S21): ✓ EP condition met")
        else:
            print(f"  ✗ V2 has {r0['n_v2']} peaks (expected 1 for EP)")

    # Slope fit
    if len(in_w_res) >= 2:
        le = np.array([np.log10(r["eps"]) for r in in_w_res])
        ld = np.array([np.log10(r["df"]) for r in in_w_res])
        slope, ic = np.polyfit(le, ld, 1)
        pred = slope*le + ic
        sst = np.sum((ld - ld.mean())**2)
        r2 = 1 - np.sum((ld-pred)**2)/sst if sst > 0 else 0
        print(f"\n=== Slope in Zhao window ===")
        print(f"  Slope: {slope:.4f}")
        print(f"  R²: {r2:.4f}")
        print(f"  N resolved: {len(in_w_res)}")
        print(f"")
        print(f"  Criterion: slope ∈ [0.45, 0.55] → {'PASS ✓' if 0.45 <= slope <= 0.55 else 'FAIL ✗'}")
        print(f"  Criterion: ≥11 points → {'PASS ✓' if len(in_w_res) >= 11 else 'FAIL ✗'}")

    # Save results
    with open(f"{WORKDIR}/results.json", 'w') as f:
        json.dump([{"eps": r["eps"], "df": r["df"], "n_v1": r["n_v1"], "n_v2": r["n_v2"]} for r in results], f, indent=2)


if __name__ == "__main__":
    main()
