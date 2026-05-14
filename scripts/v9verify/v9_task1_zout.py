"""v9 Task 1: Z_out(f, Vbn) sweep of the as-built source-follower OTA.
Sweep Vbn 0.6→1.0 V in 50 mV steps; freq 100 MHz → 5 GHz.
Use convergence options + .nodeset seed to avoid DC hang.
"""
import subprocess, os, re, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v9verify_t1"
TIMEOUT_PER_RUN = 90   # kill after 90 s per ngspice call


def hand_vfo(vbn):
    """Hand-calc Vfo bias point seed. M_tail Vov ~ Vbn-Vt; current drives Mf which sets Vfo.
    Sky130 nfet_01v8 Vt≈0.4 V at TT. For Vbn=0.85, M_tail Vov=0.45, I≈few mA.
    Source-follower with gate at Vbmid=0.9 V → Vfo ≈ Vbmid - Vgs_Mf.
    At I=1 mA in W=400/L=0.15: Vgs-Vt = sqrt(2*I/(µCox*W/L)) ≈ 50 mV → Vfo ≈ 0.45 V."""
    if vbn <= 0.65: return 0.30
    if vbn <= 0.80: return 0.45
    if vbn <= 0.90: return 0.55
    return 0.70


DECK = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

.options gmin=1e-10 gminsteps=20 reltol=1e-3 vntol=1e-5 abstol=1e-9 itl1=500 itl6=500

VVDD VDPWR  GND 1.8
Vbn  Vbn_   GND {vbn:.3f}
Vbmid Vbmid_ GND 0.9
Vinp_dc vin_p Vbmid_ DC 0 AC 0

* Itest at Vfo
Itest GND Vfo AC 1.0

* Silicon-matched source-follower: Mf (W=400 L=0.15)
XM_sf  VDPWR vin_p Vfo  GND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=8 m=10
* Tail (Mb-equivalent W=200 L=0.5)
XM_tail Vfo  Vbn_  GND  GND sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=4 m=5

.nodeset V(Vfo)={vfo_seed:.3f} V(vin_p)={vbmid_seed:.3f}

.control
op
let vfo_dc = v(Vfo)
print vfo_dc
ac dec 50 1e8 5e9
let zout = abs(v(Vfo))
meas ac z27 find zout at=2.7e9
meas ac z10 find zout at=1.0e9
meas ac z30 find zout at=3.0e9
meas ac z05 find zout at=5.0e8
echo MEAS_RESULTS:
print z05
print z10
print z27
print z30
wrdata {dat} frequency zout
.endc
.end
"""


def run_one(vbn):
    vfo_seed = hand_vfo(vbn)
    dat = f"{WORKDIR}/zout_vbn{vbn:.3f}.dat"
    if os.path.exists(dat) and os.path.getsize(dat) > 0:
        pass  # reuse
    deck = DECK.format(vbn=vbn, vfo_seed=vfo_seed, vbmid_seed=0.9, dat=dat)
    deck_path = f"{WORKDIR}/zout_vbn{vbn:.3f}.spice"
    with open(deck_path, 'w') as f: f.write(deck)
    try:
        r = subprocess.run([NGSPICE, "-b", deck_path],
                           capture_output=True, text=True, timeout=TIMEOUT_PER_RUN)
        out = r.stdout
    except subprocess.TimeoutExpired:
        return {"vbn": vbn, "vfo_dc": None, "z27": None, "timeout": True}
    vfo = re.search(r"vfo_dc\s*=\s*([\d.\-e+]+)", out)
    z27 = re.search(r"z27\s*=\s*([\d.\-e+]+)", out)
    z10 = re.search(r"z10\s*=\s*([\d.\-e+]+)", out)
    z30 = re.search(r"z30\s*=\s*([\d.\-e+]+)", out)
    z05 = re.search(r"z05\s*=\s*([\d.\-e+]+)", out)
    return {
        "vbn": vbn,
        "vfo_dc": float(vfo.group(1)) if vfo else None,
        "z05": float(z05.group(1)) if z05 else None,
        "z10": float(z10.group(1)) if z10 else None,
        "z27": float(z27.group(1)) if z27 else None,
        "z30": float(z30.group(1)) if z30 else None,
        "timeout": False,
    }


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    vbn_list = [round(v, 3) for v in np.arange(0.60, 1.001, 0.05)]
    rows = []
    for vbn in vbn_list:
        r = run_one(vbn)
        rows.append(r)
        if r.get("timeout"):
            print(f"TIMEOUT at Vbn={vbn} — skipping")
        else:
            print(f"Vbn={r['vbn']:.3f}V  Vfo={r['vfo_dc']!s:.6}  Z(500MHz)={r['z05']!s:.6}  Z(1GHz)={r['z10']!s:.6}  Z(2.7GHz)={r['z27']!s:.6}  Z(3GHz)={r['z30']!s:.6}")

    # Find Vbn min |Z(2.7G)|
    valid = [r for r in rows if r.get("z27") is not None and r.get("vfo_dc") is not None and 0.2 < r["vfo_dc"] < 1.6]
    if valid:
        best = min(valid, key=lambda r: r["z27"])
        print()
        print(f"BEST Vbn={best['vbn']:.3f}V  Vfo={best['vfo_dc']:.3f}V  |Z_out(2.7GHz)|={best['z27']:.2f}Ω")
        Z_CC = 1.0 / (2 * np.pi * 2.7e9 * 1.4e-12)
        print(f"Z_Cc @ 2.7GHz = {Z_CC:.2f}Ω")
        print(f"Z_out/Z_Cc ratio = {best['z27']/Z_CC:.2f} (PASS <<1, FAIL >>1)")
    else:
        print("NO VIABLE BIAS POINT FOUND")

    with open(f"{WORKDIR}/zout_table.json", 'w') as f:
        json.dump({"rows": rows, "best": best if valid else None}, f, indent=2)


if __name__ == "__main__":
    main()
