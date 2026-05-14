"""v10 cascode OTA design exploration.

Topology candidates:
  A) Telescopic NFET cascode above Mf (per user spec)
     - Mc above Mf, drain=VDPWR, source=Mf_drain, gate=Vbc
     - Z_out: same as SF (1/gm_Mf) — cascode doesn't lower Z_out directly
  B) Increase Mf gm via paralleling (add 3 more NQVC98-equivalent → W=1600)
     - Z_out_DC = 1/gm ≈ 17.8 Ω at I=1 mA, W=1600 L=0.15
  C) Cascoded source-follower: Mc in CG between Vfo and output Vout
     - Vfo → Mc(CG) → Vout
     - Z_out = (1/gm_Mc) || (1/gm_Mf · g_m_Mc · r_o_Mc) ≈ 1/(gm² · ro)
     - For Mc W=200, gm_Mc=15 mS, ro=10kΩ → Z_out ≈ 4 mΩ (way too low actually)
     - Realistic Z_out limited by Cgs parasitic at high freq

Plan: combine B+C — widen Mf to W=1600 AND add Mc CG stage at output.
Verify Z_out at 2.7 GHz < 30 Ω.
"""
import subprocess, os, re
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v10_cascode"

# Variants to test
VARIANTS = [
    {
        "name": "v9_baseline",
        "desc": "as-built Mf W=400, M_tail W=200 — for reference",
        "mf_m": 10, "mt_m": 5, "mc_m": 0, "mc_W": 5, "mc_nf": 8,
    },
    {
        "name": "v10_wide_Mf",
        "desc": "Mf widened 4x to W=1600, no cascode",
        "mf_m": 40, "mt_m": 5, "mc_m": 0, "mc_W": 5, "mc_nf": 8,
    },
    {
        "name": "v10_wide_Mf_cascode",
        "desc": "Mf widened 4x + telescopic cascode Mc above Mf",
        "mf_m": 40, "mt_m": 5, "mc_m": 20, "mc_W": 5, "mc_nf": 8,
    },
    {
        "name": "v10_wider_Mf",
        "desc": "Mf widened 8x to W=3200 (limit-case)",
        "mf_m": 80, "mt_m": 8, "mc_m": 0, "mc_W": 5, "mc_nf": 8,
    },
]


DECK_WITH_CASCODE = """.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.options gmin=1e-10 gminsteps=20 reltol=1e-3 vntol=1e-5 abstol=1e-9 itl1=500 itl6=500

VVDD VDPWR  GND 1.8
Vbn  Vbn_   GND 0.85
Vbc  Vbc_   GND 1.15   ; cascode gate bias
Vinp_dc vin_p GND DC 0.9 AC 0

* Test stimulus
Itest GND Vout AC 1.0

* Mf: source-follower input, drain to Mf_d (cascode-protected if cascode present)
XM_sf  Mf_d  vin_p Mf_s  GND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=8 m={mf_m}

* Cascode Mc above Mf
{mc_section}

* Cascode Mc' below output (CG stage to lower Z_out)
{mc_out_section}

* M_tail: tail current
XM_tail Mf_s Vbn_ GND GND sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=4 m={mt_m}

.nodeset V(Mf_s)=0.5 V(Mf_d)=0.9 V(Vout)=0.7

.control
op
let vfs = v(Mf_s)
let vfd = v(Mf_d)
let vout_dc = v(Vout)
print vfs vfd vout_dc
echo OPRESULTS
ac dec 50 1e8 5e9
let z_out = abs(v(Vout))
meas ac z27 find z_out at=2.7e9
meas ac z10 find z_out at=1.0e9
meas ac z30 find z_out at=3.0e9
echo MEAS_VALUES:
print z10
print z27
print z30
.endc
.end
"""


def build_deck(mf_m, mt_m, mc_m, mc_W, mc_nf):
    if mc_m > 0:
        # Cascode Mc above Mf
        mc_sec = (f"XMc_top VDPWR Vbc_ Mf_d GND sky130_fd_pr__nfet_01v8 "
                  f"W={mc_W} L=0.15 nf={mc_nf} m={mc_m}")
    else:
        mc_sec = "R_Mf_d_short Mf_d VDPWR 0.001  ; no cascode, tie drain to supply"

    # Always include CG output stage to lower Z_out
    # Mc_out: G=Vbc, D=VDPWR, S=Vout, but we tap Vfo (=Mf_s) to drive it
    # Actually for lower Z_out, we need a regulated buffer
    # Simplest: just Vfo = Mf_s directly (the SF output). No second stage.
    mc_out_sec = "R_short Mf_s Vout 0.001  ; direct tap, no second stage"

    return DECK_WITH_CASCODE.format(
        mf_m=mf_m, mt_m=mt_m, mc_section=mc_sec, mc_out_section=mc_out_sec
    )


def run(variant):
    deck = build_deck(**{k: variant[k] for k in ["mf_m", "mt_m", "mc_m", "mc_W", "mc_nf"]})
    deck_path = f"{WORKDIR}/{variant['name']}.spice"
    with open(deck_path, 'w') as f: f.write(deck)
    try:
        r = subprocess.run([NGSPICE, "-b", deck_path],
                           capture_output=True, text=True, timeout=90)
        out = r.stdout
    except subprocess.TimeoutExpired:
        return {"timeout": True}
    vfs = re.search(r"vfs\s*=\s*([\d.\-e+]+)", out)
    vfd = re.search(r"vfd\s*=\s*([\d.\-e+]+)", out)
    vout = re.search(r"vout_dc\s*=\s*([\d.\-e+]+)", out)
    z27 = re.search(r"z27\s*=\s*([\d.\-e+]+)", out)
    z10 = re.search(r"z10\s*=\s*([\d.\-e+]+)", out)
    z30 = re.search(r"z30\s*=\s*([\d.\-e+]+)", out)
    return {
        "vfs": float(vfs.group(1)) if vfs else None,
        "vfd": float(vfd.group(1)) if vfd else None,
        "vout": float(vout.group(1)) if vout else None,
        "z10": float(z10.group(1)) if z10 else None,
        "z27": float(z27.group(1)) if z27 else None,
        "z30": float(z30.group(1)) if z30 else None,
        "out": out[-1500:],
    }


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    Z_CC_27 = 1 / (2 * np.pi * 2.7e9 * 1.4e-12)
    print(f"Target: Z_out @ 2.7 GHz << {Z_CC_27:.1f} Ω")
    print()
    for v in VARIANTS:
        print(f"=== {v['name']}: {v['desc']} ===")
        r = run(v)
        if r.get("timeout"):
            print("  TIMEOUT")
            continue
        print(f"  Vfs={r['vfs']!s:.6} Vfd={r['vfd']!s:.6} Vout={r['vout']!s:.6}")
        print(f"  Z(1G)={r['z10']!s:.6}Ω  Z(2.7G)={r['z27']!s:.6}Ω  Z(3G)={r['z30']!s:.6}Ω")
        if r["z27"]:
            print(f"  Z_out/Z_Cc = {r['z27']/Z_CC_27:.2f}")
        print()


if __name__ == "__main__":
    main()
