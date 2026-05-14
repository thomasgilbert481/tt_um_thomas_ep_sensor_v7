"""v9 Task 6: 3 stress corners SS/85/1.62V, TT/27/1.80V, FF/0/1.98V.

Re-run cv sweep with real OTA at each corner. Report slope envelope.
"""
import subprocess, os, re, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v9verify_corners"

CV_WEIGHTS_FF = [20, 41, 82, 164, 328, 656, 1312, 1312]
C_T1_FF = 1845

def enumerate_eps():
    s = set()
    for bits in range(256):
        v = sum(CV_WEIGHTS_FF[i] for i in range(8) if bits & (1 << i))
        s.add(round(v / (2 * C_T1_FF), 6))
    return sorted(s)


CORNERS = [
    {"name": "SS_85_1.62V", "lib": "ss", "temp": 85, "vdd": 1.62},
    {"name": "TT_27_1.80V", "lib": "tt", "temp": 27, "vdd": 1.80},
    {"name": "FF_0_1.98V",  "lib": "ff", "temp": 0,  "vdd": 1.98},
]


DECK = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice {lib}
.options gmin=1e-10 gminsteps=20 reltol=1e-3 vntol=1e-5 abstol=1e-9 itl1=500 itl6=500
.options TEMP={temp} TNOM=27

VVDD VDPWR  GND {vdd}
Vbn  Vbn_   GND 1.0
Vbmid Vbmid_ GND 0.9

Vin v_vna GND DC 0 AC 1
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

K_M12 L1 L2 -0.020

Cac     V1     vin_p   14.112p
RbiasIn vin_p  Vbmid_  1e7

XM_sf  VDPWR vin_p Vfo  GND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=8 m=10
XM_tail Vfo  Vbn_  GND  GND sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=4 m=5

Cc      Vfo    V2_in   1.398p
.param eps={eps}
Ceps    V1     V2_in   'max(2*1.845e-12*eps, 1e-21)'

Rfb     Vfo    Vbmid_  1e7
R_chip2 V2_in  v_pad2n  0.5
C_PAD2  v_pad2n GND    125e-15
L_BOND2 v_pad2n v_pad2  1.5e-9
R_load  v_pad2 GND      50

.nodeset V(Vfo)=0.1 V(vin_p)=0.9

.control
op
ac dec 1500 1e9 5e9
let v1m = abs(v(V1))
let v2m = abs(v(V2_in))
wrdata {dat} frequency v1m v2m
quit
.endc
.end
"""


def run_one(corner, eps, idx):
    dat = f"{WORKDIR}/{corner['name']}_eps{idx:03d}.dat"
    if os.path.exists(dat) and os.path.getsize(dat) > 0:
        return dat
    deck = DECK.format(lib=corner['lib'], temp=corner['temp'], vdd=corner['vdd'],
                        eps=eps, dat=dat)
    deck_path = f"{WORKDIR}/{corner['name']}_eps{idx:03d}.spice"
    with open(deck_path, 'w') as f: f.write(deck)
    try:
        subprocess.run([NGSPICE, "-b", deck_path],
                       capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return None
    return dat if os.path.exists(dat) else None


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
    v1 = arr[:, 2] if arr.shape[1] >= 5 else arr[:, 1]
    v2 = arr[:, 4] if arr.shape[1] >= 5 else arr[:, 2]
    p1 = filt(find_peaks(freq, v1))
    p2 = filt(find_peaks(freq, v2))
    peaks = p1 if len(p1) >= 2 else (p2 if len(p2) >= 2 else p1)
    df = 0; f0 = 0
    if len(peaks) >= 2:
        pf = sorted(p[0] for p in peaks); df = pf[-1] - pf[0]; f0 = sum(pf) / len(pf)
    elif len(peaks) == 1:
        f0 = peaks[0][0]
    return df, f0


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    # Use a smaller subset of eps for corner sweep (20 points instead of 55) to save time
    full_eps = [e for e in enumerate_eps() if e == 0 or (0.005 <= e <= 0.3)]
    eps_subset = full_eps[::3]  # every 3rd
    if 0 not in eps_subset: eps_subset = [0] + eps_subset
    print(f"Corner sweep: {len(eps_subset)} eps × {len(CORNERS)} corners")
    summary = {}
    for corner in CORNERS:
        print(f"\n=== {corner['name']} ===")
        results = []
        for i, eps in enumerate(eps_subset):
            dat = run_one(corner, eps, i)
            if not dat: continue
            df, f0 = measure(dat)
            results.append({"eps": eps, "df": df, "f0": f0})
        r0 = next((r for r in results if r["eps"] == 0.0), None)
        in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
        f0_at_eps0 = r0['f0'] if r0 else None
        slope = r2 = None
        if len(in_w) >= 2:
            le = np.array([np.log10(r["eps"]) for r in in_w])
            ld = np.array([np.log10(r["df"]) for r in in_w])
            slope, ic = np.polyfit(le, ld, 1)
            pred = slope*le + ic
            sst = np.sum((ld - ld.mean())**2)
            r2 = 1 - np.sum((ld-pred)**2)/sst if sst > 0 else 0
        print(f"  n_resolved={len(in_w)}, slope={slope!s:.6}, R²={r2!s:.6}, f0@ε=0={f0_at_eps0!s}")
        summary[corner['name']] = {"slope": slope, "r2": r2, "n_resolved": len(in_w),
                                    "f0_at_eps0": f0_at_eps0}

    print("\n=== Envelope summary ===")
    slopes = [v["slope"] for v in summary.values() if v["slope"] is not None]
    f0s = [v["f0_at_eps0"] for v in summary.values() if v["f0_at_eps0"] is not None]
    n_res = [v["n_resolved"] for v in summary.values()]
    if slopes:
        print(f"  slope envelope: {min(slopes):.4f} – {max(slopes):.4f}")
    if f0s:
        print(f"  f0 envelope (GHz): {min(f0s)/1e9:.3f} – {max(f0s)/1e9:.3f}")
    print(f"  n_resolved envelope: {min(n_res)} – {max(n_res)}")

    with open(f"{WORKDIR}/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
