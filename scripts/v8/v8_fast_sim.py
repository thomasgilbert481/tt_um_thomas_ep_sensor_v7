"""Fast sim: use coarser AC sweep + ideal buffer + extracted cap values.
Sweep ε across log-spaced points and measure slope in Zhao window.

Tests TWO scenarios:
1. As-built chip: C_T1=1.85, C_T2=0.84, Cc=1.40 (extracted from v13)
2. β=1 corrected: C_T1=2.24 (+0.39 pF added)
"""
import subprocess, os, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v8_fast_sim"

DECK = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

Vin     v_vna    GND  AC 1
R_VNA   v_vna    v_pad1in 50
L_BOND1 v_pad1in v_pad1n  1.5e-9
R_BOND1 v_pad1n  v_pad1n2 0.05
C_PAD1  v_pad1n2 GND      125e-15
R_chip1 v_pad1n2 V1       0.5

L1 V1 nL1 1.351e-9
R1 nL1 0 5.0
C_T1 V1 GND  {ct1}p
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
ac dec 1500 0.5e9 6e9
let v1mag = abs(v(V1))
let v2mag = abs(v(V2_in))
wrdata {out} frequency v1mag v2mag
quit
.endc
.end
"""


def run(ct1, eps, run_id):
    out = f"{WORKDIR}/run_{run_id}.dat"
    if os.path.exists(out):
        return out
    deck = DECK.format(ct1=ct1, eps=eps, out=out)
    deck_path = f"{WORKDIR}/run_{run_id}.spice"
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


def filter_peaks(peaks, min_height_frac=0.20, min_sep_hz=50e6):
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
    p1 = filter_peaks(find_peaks(freq, v1), min_height_frac=0.30)
    p2 = filter_peaks(find_peaks(freq, v2), min_height_frac=0.30)
    # Prefer V1 if shows >=2 peaks
    peaks = p1 if len(p1) >= 2 else p2
    if len(peaks) >= 2:
        pf = sorted(p[0] for p in peaks)
        return pf[-1] - pf[0], len(p1), len(p2)
    return 0, len(p1), len(p2)


def sweep(ct1_pf, label):
    print(f"\n=== {label}: C_T1={ct1_pf:.3f} pF ===")
    beta = (ct1_pf / (0.836 + 1.398)) ** 0.5
    print(f"  β = {beta:.4f}")

    # 30 log-spaced ε values for Zhao window resolution
    eps_values = sorted(set([0.0] + list(np.logspace(np.log10(0.005), np.log10(0.4), 30))))
    results = []
    for i, eps in enumerate(eps_values):
        run_id = f"{label[:3]}_{i:02d}"
        dat = run(ct1_pf, eps, run_id)
        if dat is None:
            print(f"  [{i:02d}] eps={eps:.5f} sim FAIL")
            continue
        df, n1, n2 = measure(dat)
        results.append({"eps": eps, "df_hz": df, "n_v1": n1, "n_v2": n2})

    # ε=0 check
    r0 = next((r for r in results if r["eps"] == 0.0), None)
    if r0:
        print(f"  ε=0: n_v1={r0['n_v1']}, n_v2={r0['n_v2']}, Δf={r0['df_hz']/1e6:.1f} MHz")

    # Slope fit in Zhao window
    in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df_hz"] > 0]
    print(f"  Resolved in Zhao window: {len(in_w)} / {sum(1 for r in results if 0.031 <= r['eps'] <= 0.25)}")
    if len(in_w) >= 2:
        le = np.array([np.log10(r["eps"]) for r in in_w])
        ld = np.array([np.log10(r["df_hz"]) for r in in_w])
        slope, intercept = np.polyfit(le, ld, 1)
        pred = slope*le + intercept
        sst = np.sum((ld - ld.mean())**2)
        r2 = 1 - np.sum((ld-pred)**2)/sst if sst > 0 else 0
        print(f"  SLOPE = {slope:.4f}  R² = {r2:.4f}")
        print(f"  Target: slope ∈ [0.45, 0.55]  →  {'PASS ✓' if 0.45 <= slope <= 0.55 else 'FAIL ✗'}")
        print(f"  Target: ≥11 points → {'PASS ✓' if len(in_w) >= 11 else 'FAIL ✗'}")
        return {"slope": slope, "r2": r2, "n_zhao": len(in_w), "beta": beta}
    return None


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    r1 = sweep(1.845, "AS_BUILT")
    r2 = sweep(2.24, "BETA_1_TUNED")

    print("\n\n=== SUMMARY ===")
    if r1: print(f"As-built:  β={r1['beta']:.4f}, slope={r1['slope']:.4f}, R²={r1['r2']:.4f}, N_zhao={r1['n_zhao']}")
    if r2: print(f"β=1 tuned: β={r2['beta']:.4f}, slope={r2['slope']:.4f}, R²={r2['r2']:.4f}, N_zhao={r2['n_zhao']}")


if __name__ == "__main__":
    main()
