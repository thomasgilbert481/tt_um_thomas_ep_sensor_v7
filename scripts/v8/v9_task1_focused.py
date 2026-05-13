"""Task 1 focused: run Z_out + cv sweep at ONE bias point with silicon-matched OTA.

Use the actual silicon device sizes:
- Mf (NQVC98): W=5 L=0.15 nf=80 -- input amplifier (will use as SF for now)
- Mb (GPUJJ4): W=10 L=0.5 nf=20 -- tail/bias
- Mout (3FYCX3): W=5 L=0.15 nf=40 -- second-stage (could chain after first)
- Mout_b (SQMHJC): W=10 L=0.5 nf=10 -- second-stage bias

For Vbn that gives reasonable bias, sweep ε across cv-array values.
"""
import subprocess, os, re, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v9_task1"

# Discrete cv-array ε values in Zhao window
CV_WEIGHTS_FF = [20, 41, 82, 164, 328, 656, 1312, 1312]
C_T1_FF = 1845

def enumerate_eps():
    out = set()
    for bits in range(256):
        s = sum(CV_WEIGHTS_FF[i] for i in range(8) if bits & (1 << i))
        out.add(round(s / (2 * C_T1_FF), 6))
    return sorted(out)


DECK_TEMPLATE = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
VVDD VDPWR  GND 1.8
Vbn  Vbn_   GND {vbn}
Vbmid Vbmid_ GND {vbmid}
Vin     v_vna    GND  DC 0 AC 1
R_VNA   v_vna    v_pad1in 50
L_BOND1 v_pad1in v_pad1n  1.5e-9
R_BOND1 v_pad1n  v_pad1n2 0.05
C_PAD1  v_pad1n2 GND      125e-15
R_chip1 v_pad1n2 V1       0.5
L1 V1 nL1 1.351e-9
R1 nL1 VDPWR 5.0
C_T1 V1 GND  1.845p
C_SRF1 V1 GND 0.18p
L2 V2_in nL2 1.351e-9
R2 nL2 GND 5.0
C_T2 V2_in GND 0.836p
C_SRF2 V2_in GND 0.18p
K_M12 L1 L2 -0.032
Cac     V1     vin_p   14.112p
RbiasIn vin_p  Vbmid_  1e7

* NMOS source-follower with silicon-matched sizing
XM_sf  VDPWR vin_p Vfo  GND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=8 m={msf_m}
XM_tail Vfo  Vbn_  GND  GND sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=4 m={mt_m}

Cc      Vfo    V2_in   1.398p
.param eps={eps}
Ceps    V1     V2_in   'max(2*1.845e-12*eps, 1e-21)'
Rfb     Vfo    Vbmid_  1e7
R_chip2 V2_in  v_pad2n  0.5
C_PAD2  v_pad2n GND    125e-15
L_BOND2 v_pad2n v_pad2  1.5e-9
R_load  v_pad2 GND      50

.control
op
let vfo_dc = v(Vfo)
let v1_dc = v(V1)
let i_tail = i(VVDD)
print vfo_dc v1_dc i_tail
ac dec 1500 0.5e9 5e9
let v1m = abs(v(V1))
let v2m = abs(v(V2_in))
let vfom = abs(v(Vfo))
wrdata {out} frequency v1m v2m vfom
quit
.endc
.end
"""

# Probe Z_out separately
ZOUT_TEMPLATE = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
VVDD VDPWR GND 1.8
Vbn Vbn_ GND {vbn}
Vbmid Vbmid_ GND {vbmid}
* DC bias for input
Vin_dc vin_p GND DC {vinp_dc} AC 0
* Small AC probe at Vfo via Itest
Itest GND Vfo AC 1.0
XM_sf  VDPWR vin_p Vfo  GND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=8 m={msf_m}
XM_tail Vfo  Vbn_  GND  GND sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=4 m={mt_m}
.control
op
let vfo_dc = v(Vfo)
print vfo_dc
ac dec 100 1e8 1e10
let z_out = abs(v(Vfo))
meas ac z27 find z_out at=2.7e9
meas ac z30 find z_out at=3.0e9
meas ac z10 find z_out at=1.0e9
echo ZOUT_RESULTS
.endc
.end
"""

def run_zout(vbn, vbmid, msf_m, mt_m, vinp_dc):
    deck = ZOUT_TEMPLATE.format(vbn=vbn, vbmid=vbmid, msf_m=msf_m, mt_m=mt_m, vinp_dc=vinp_dc)
    deck_path = f"{WORKDIR}/zout.spice"
    with open(deck_path, 'w') as f: f.write(deck)
    r = subprocess.run([NGSPICE, "-b", deck_path], capture_output=True, text=True, timeout=60)
    out = r.stdout
    vfo_m = re.search(r"vfo_dc\s*=\s*([\d.\-e+]+)", out)
    z27_m = re.search(r"z27\s*=\s*([\d.\-e+]+)", out)
    z3g_m = re.search(r"z30\s*=\s*([\d.\-e+]+)", out)
    z10_m = re.search(r"z10\s*=\s*([\d.\-e+]+)", out)
    vfo = float(vfo_m.group(1)) if vfo_m else 0
    z27 = float(z27_m.group(1)) if z27_m else 0
    z3g = float(z3g_m.group(1)) if z3g_m else 0
    z10 = float(z10_m.group(1)) if z10_m else 0
    return vfo, z10, z27, z3g, out


def find_peaks(freq, mag):
    peaks = []
    for i in range(2, len(mag)-2):
        if mag[i] > mag[i-1] and mag[i] > mag[i+1] and mag[i] >= mag[i-2] and mag[i] >= mag[i+2]:
            peaks.append((freq[i], mag[i]))
    return peaks


def filter_peaks(peaks, min_height_frac=0.15, min_sep_hz=80e6):
    if not peaks: return []
    mx = max(p[1] for p in peaks)
    f = sorted([p for p in peaks if p[1] >= min_height_frac*mx], key=lambda p: p[0])
    if not f: return []
    out = [f[0]]
    for p in f[1:]:
        if p[0] - out[-1][0] < min_sep_hz:
            if p[1] > out[-1][1]: out[-1] = p
        else: out.append(p)
    return out


def run_cv_sweep(vbn, vbmid, msf_m, mt_m):
    eps_values = [e for e in enumerate_eps() if e == 0 or (0.005 <= e <= 0.3)]
    print(f"Sweep {len(eps_values)} ε values with real OTA Vbn={vbn} Vbmid={vbmid}")
    results = []
    for i, eps in enumerate(eps_values):
        out_dat = f"{WORKDIR}/cv_{i:03d}.dat"
        deck = DECK_TEMPLATE.format(vbn=vbn, vbmid=vbmid, msf_m=msf_m, mt_m=mt_m, eps=eps, out=out_dat)
        deck_path = f"{WORKDIR}/cv_{i:03d}.spice"
        with open(deck_path, 'w') as f: f.write(deck)
        r = subprocess.run([NGSPICE, "-b", deck_path], capture_output=True, text=True, timeout=60)
        if not os.path.exists(out_dat): continue
        try:
            arr = np.loadtxt(out_dat)
            if arr.ndim == 1: arr = arr.reshape(1, -1)
            freq = arr[:, 0]
            v1 = arr[:, 4] if arr.shape[1] >= 7 else arr[:, 2]
            v2 = arr[:, 6] if arr.shape[1] >= 7 else arr[:, 4]
            p1 = filter_peaks(find_peaks(freq, v1))
            p2 = filter_peaks(find_peaks(freq, v2))
            peaks = p1 if len(p1) >= 2 else (p2 if len(p2) >= 2 else p1)
            df = 0
            if len(peaks) >= 2:
                pf = sorted(p[0] for p in peaks)
                df = pf[-1] - pf[0]
            results.append({"eps": eps, "df": df, "n_v1": len(p1), "n_v2": len(p2)})
        except Exception as e:
            print(f"  parse error eps={eps}: {e}")
    return results


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    print("=== Task 1: Real OTA EP Verification ===\n")

    # First, find Vbn that gives reasonable Vfo and low Z_out
    print("--- Z_out sweep ---")
    candidates = []
    for vbn in [0.7, 0.85, 1.0, 1.2]:
      for msf_m in [10, 50, 100, 200]:
        for vinp_dc in [0.9, 1.2, 1.4]:
            vfo, z10, z27, z3g, _ = run_zout(vbn, 0.9, msf_m, 5, vinp_dc)
            if 0.3 < vfo < 1.5 and z27 > 0:
                candidates.append((vbn, msf_m, vinp_dc, vfo, z10, z27, z3g))
                print(f"  Vbn={vbn} msf={msf_m} vinp={vinp_dc}: Vfo={vfo:.3f} Z10={z10:.1f} Z27={z27:.1f} Z3G={z3g:.1f}")

    if not candidates:
        print("NO VIABLE BIAS POINT FOUND")
        return

    # Pick lowest Z27
    candidates.sort(key=lambda c: c[5])
    best = candidates[0]
    vbn, msf_m, vinp_dc, vfo, z10, z27, z3g = best
    print(f"\nBest: Vbn={vbn} msf={msf_m} vinp={vinp_dc}")
    print(f"  Vfo={vfo:.3f}V, Z(1G)={z10:.1f}Ω, Z(2.7G)={z27:.1f}Ω, Z(3G)={z3g:.1f}Ω")

    Z_CC = 42
    if z27 < Z_CC * 0.5:
        print(f"  Z_out < {Z_CC/2}Ω: PASS")
    elif z27 < Z_CC:
        print(f"  Z_out < {Z_CC}Ω but > {Z_CC/2}Ω: MARGINAL — slope may degrade")
    else:
        print(f"  Z_out > {Z_CC}Ω: EXPECT SLOPE > 0.7")

    # Vbmid for cv sweep: choose to roughly match Vfo
    vbmid_for_cv = 0.9 if vinp_dc < 1.0 else 0.9  # keeps DC of Cac stable
    print(f"\n--- CV sweep at best bias (Vbn={vbn}, Vbmid={vbmid_for_cv}, msf_m={msf_m}) ---")
    results = run_cv_sweep(vbn, vbmid_for_cv, msf_m, 5)
    in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
    print(f"\n{len(in_w)} resolved Δf points in Zhao window")
    if len(in_w) >= 2:
        le = np.array([np.log10(r["eps"]) for r in in_w])
        ld = np.array([np.log10(r["df"]) for r in in_w])
        slope, ic = np.polyfit(le, ld, 1)
        pred = slope*le + ic
        sst = np.sum((ld - ld.mean())**2)
        r2 = 1 - np.sum((ld-pred)**2)/sst if sst > 0 else 0
        r0 = next((r for r in results if r["eps"] == 0.0), None)
        n_v2_0 = r0["n_v2"] if r0 else None
        print(f"Slope = {slope:.4f}, R² = {r2:.4f}")
        print(f"ε=0: n_v2 = {n_v2_0}")
        print(f"\n  Pass: ≥11 resolved → {'YES' if len(in_w) >= 11 else 'NO'}")
        print(f"  Pass: slope ∈ [0.45,0.55] → {'YES' if 0.45 <= slope <= 0.55 else 'NO'}")
        print(f"  Pass: R² ≥ 0.95 → {'YES' if r2 >= 0.95 else 'NO'}")
        print(f"  Pass: ε=0 single peak (n_v2=1) → {'YES' if n_v2_0 == 1 else 'NO'}")
        # Save
        with open(f"{WORKDIR}/task1_summary.json", 'w') as f:
            json.dump({
                "vbn": vbn, "vbmid": vbmid_for_cv, "msf_m": msf_m,
                "vfo": vfo, "z_out_1G": z10, "z_out_2.7G": z27, "z_out_3G": z3g,
                "n_resolved": len(in_w),
                "slope": slope, "r2": r2,
                "ep_single_peak": (n_v2_0 == 1) if n_v2_0 is not None else None,
            }, f, indent=2)


if __name__ == "__main__":
    main()
