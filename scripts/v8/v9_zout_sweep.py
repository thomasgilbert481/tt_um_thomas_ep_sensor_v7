"""Sweep Vbn and Vbmid to find optimal bias for NMOS source-follower.
Measure Z_out at 2.7 GHz."""
import subprocess, os, re
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v9_zout_sweep"

DECK = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
VVDD VDPWR  GND 1.8
Vbn  Vbn_   GND {vbn}
Vinp vin_p GND DC {vinp} AC 0
Itest GND Vfo  AC 1.0
XM_sf  VDPWR vin_p Vfo  GND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=8 m={m_sf}
XM_tail Vfo  Vbn_  GND  GND sky130_fd_pr__nfet_01v8 W=10 L=0.5  nf=4 m={m_tail}
.control
op
let i_tail = i(Vinp)
echo Vfo:; print v(Vfo)
ac dec 100 1e8 1e10
let z_out = abs(v(Vfo))
meas ac z27 find z_out at=2.7e9
meas ac z10 find z_out at=1.0e9
meas ac z3g find z_out at=3.0e9
echo SUMMARY {label}:
echo Vfo_dc=:; print v(Vfo)
echo Z10:; print z10
echo Z27:; print z27
echo Z3g:; print z3g
.endc
.end
"""

os.makedirs(WORKDIR, exist_ok=True)
configs = []
# Sweep tail current via Vbn and M_sf size
for vbn in [0.7, 0.85, 1.0, 1.2]:
    for vinp in [0.9, 1.2, 1.5]:
        for m_sf in [5, 20, 50, 100]:
            configs.append((vbn, vinp, m_sf, 5))

results = []
for cfg in configs:
    vbn, vinp, m_sf, m_tail = cfg
    label = f"vbn{vbn}_vinp{vinp}_msf{m_sf}_mt{m_tail}"
    deck = DECK.format(vbn=vbn, vinp=vinp, m_sf=m_sf, m_tail=m_tail, label=label)
    deck_path = f"{WORKDIR}/{label}.spice"
    with open(deck_path, 'w') as f: f.write(deck)
    r = subprocess.run([NGSPICE, "-b", deck_path], capture_output=True, text=True, timeout=60)
    if "Z27" not in r.stdout: continue
    out = r.stdout
    vfo_m = re.search(r"v\(vfo\) = ([\d.\-e+]+)", out)
    z27_m = re.search(r"z27\s*=\s*([\d.\-e+]+)", out)
    z3g_m = re.search(r"z3g\s*=\s*([\d.\-e+]+)", out)
    if vfo_m and z27_m and z3g_m:
        vfo = float(vfo_m.group(1))
        z27 = float(z27_m.group(1))
        z3g = float(z3g_m.group(1))
        results.append((cfg, vfo, z27, z3g))
        print(f"{label}: Vfo={vfo:.3f}V Z(2.7)={z27:.1f}Ω Z(3.0)={z3g:.1f}Ω")

# Find best (lowest Z27 with reasonable Vfo)
viable = [r for r in results if 0.3 < r[1] < 1.5]
if viable:
    viable.sort(key=lambda r: r[2])
    best = viable[0]
    print(f"\nBest config: {best[0]}")
    print(f"  Vfo={best[1]:.3f}V Z(2.7)={best[2]:.1f}Ω Z(3.0)={best[3]:.1f}Ω")
    Z_CC = 42
    print(f"  Target Z_out << {Z_CC} Ω")
    if best[2] < Z_CC * 0.5:
        print(f"  PASS: Z_out is {best[2]/Z_CC:.2f}x Z_Cc")
    else:
        print(f"  FAIL: Z_out is {best[2]/Z_CC:.1f}x Z_Cc (need <0.5x)")
