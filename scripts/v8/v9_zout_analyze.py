"""Analyze v9_zout_sweep results by running ngspice on each deck."""
import subprocess, os, re

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v9_zout_sweep"

results = []
for fn in sorted(os.listdir(WORKDIR)):
    if not fn.endswith(".spice"): continue
    path = os.path.join(WORKDIR, fn)
    r = subprocess.run([NGSPICE, "-b", path], capture_output=True, text=True, timeout=60)
    out = r.stdout
    vfo_m = re.search(r"v\(vfo\)\s*=\s*([\d.\-e+]+)", out)
    z27_m = re.search(r"z27\s*=\s*([\d.\-e+]+)", out)
    z3g_m = re.search(r"z3g\s*=\s*([\d.\-e+]+)", out)
    if vfo_m and z27_m:
        vfo = float(vfo_m.group(1))
        z27 = float(z27_m.group(1))
        z3g = float(z3g_m.group(1)) if z3g_m else 0
        # Parse label
        label = fn.replace(".spice", "")
        vbn = float(re.search(r"vbn([\d.]+)", label).group(1))
        vinp = float(re.search(r"vinp([\d.]+)", label).group(1))
        msf = int(re.search(r"msf(\d+)", label).group(1))
        results.append({"label": label, "vbn": vbn, "vinp": vinp, "msf": msf,
                        "vfo": vfo, "z27": z27, "z3g": z3g})

print(f"Total runs: {len(results)}")

# Sort by lowest Z27 with reasonable Vfo (0.3 < Vfo < 1.5)
viable = [r for r in results if 0.3 < r["vfo"] < 1.5]
print(f"Viable (0.3<Vfo<1.5): {len(viable)}")
viable.sort(key=lambda r: r["z27"])
print(f"\n{'label':45s}  {'Vbn':>5s}  {'Vinp':>5s}  {'msf':>4s}  {'Vfo':>5s}  {'Z27Ω':>8s}  {'Z3GΩ':>8s}")
for r in viable[:15]:
    print(f"{r['label']:45s}  {r['vbn']:5.2f}  {r['vinp']:5.2f}  {r['msf']:4d}  {r['vfo']:5.3f}  {r['z27']:8.1f}  {r['z3g']:8.1f}")

Z_CC_27 = 42  # Ω
if viable:
    best = viable[0]
    print(f"\nBEST: {best['label']}")
    print(f"  Vfo={best['vfo']:.3f}V  Z(2.7)={best['z27']:.1f}Ω  Z(3.0)={best['z3g']:.1f}Ω")
    print(f"  Target Z_out << {Z_CC_27} Ω (Z_Cc at 2.7 GHz)")
    if best['z27'] < Z_CC_27 * 0.5:
        print(f"  PASS: Z_out is {best['z27']/Z_CC_27:.2f}x Z_Cc")
    elif best['z27'] < Z_CC_27:
        print(f"  MARGINAL: Z_out is {best['z27']/Z_CC_27:.2f}x Z_Cc (target <0.5x)")
    else:
        print(f"  FAIL: Z_out is {best['z27']/Z_CC_27:.1f}x Z_Cc")
