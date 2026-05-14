"""v9 Task 7: ui_in[6,7] crosstalk from hierarchical PEX cell parasitics.

Use the cell-level .ext files to estimate per-route crosstalk to V1/V2_in/Vfo nets.
"""
import os, re

PEX_DIR = "/tmp/v9_pex_hier"
TOP_EXT = f"{PEX_DIR}/tt_um_thomas_ep_sensor.ext"

# Parse cap statements from each .ext file. The Magic .ext format has
# "cap <node1> <node2> <cap_aF>" lines.
def parse_caps(ext_path):
    caps = []
    with open(ext_path) as f:
        for line in f:
            m = re.match(r"^cap\s+(\S+)\s+(\S+)\s+([\d.\-eE+]+)", line)
            if m:
                caps.append((m.group(1), m.group(2), float(m.group(3))))
    return caps


print("=== v9 hierarchical PEX cap inventory ===\n")

# Top cell — find all 'cap' statements
top_caps = parse_caps(TOP_EXT)
print(f"Top cell has {len(top_caps)} parasitic caps")
# Sort by magnitude
top_caps.sort(key=lambda c: -c[2])
print("\nTop-cell top-10 largest parasitic caps (aF):")
for n1, n2, val in top_caps[:10]:
    print(f"  {n1} -- {n2}: {val:.1f} aF")

# In Magic .ext, top-level parasitics are between Magic-generated subnets like
# "m3_45236_7344#". These don't directly tell us ui_in[i] vs V2_in coupling because
# the ports were collapsed (well-known v9 label artifact).
#
# As an alternative, we look at ROUTE cells: for ui_in routes, we know the
# coordinates (climb_x, y_H, ui_x). Compute geometric coupling from these.
#
# Per V9 routing (commit ea728d2 + earlier):
# ui_in[6]: climb x=192.10-192.50, y=80-225
# ui_in[7]: climb x=192.65-193.05, y=80-225
# L2 spiral metal at x=193+ (outer turn)
# Distance: ui_in[6] climb to L2 outer turn: ~0.5 µm
#           ui_in[7] climb to L2 outer turn: ~0 µm (overlap)

# Approximate metal-to-metal C using parallel-plate over the overlap length
ESP_SIO2_PER_M = 4.0 * 8.854e-12  # F/m
SAME_LAYER_MIN_SPACE_M2_M3 = 0.36e-6  # M2-M3 inter-layer thickness ≈ 0.36 µm

# ui_in[6] climb at x=192.10-192.50 (W=0.40 µm)
# L2 spiral M3 turn at x=193, y range overlap ~ y=120-160 in the route's y span
# Side-by-side distance ≈ 193 - 192.50 = 0.5 µm
# Vertical overlap length ≈ 40 µm (y=120-160 portion of climb)
# Metal height ≈ 0.8 µm (M2 or M3 thickness)
def estimate_coupling_um(side_dist_um, overlap_len_um, metal_h_um=0.8):
    d = side_dist_um * 1e-6
    A = overlap_len_um * 1e-6 * metal_h_um * 1e-6  # parallel area
    return ESP_SIO2_PER_M * A / d


ui_in_routes_in_l2 = {
    "ui_in[6]": {"climb_x_max": 192.50, "y_overlap_l2_um": 37, "side_dist_to_l2_um": 0.5},
    "ui_in[7]": {"climb_x_max": 193.05, "y_overlap_l2_um": 37, "side_dist_to_l2_um": 0.1},  # overlap!
    "ui_in[5]": {"climb_x_max": 191.95, "y_overlap_l2_um": 37, "side_dist_to_l2_um": 1.05},
    "ui_in[4]": {"climb_x_max": 191.40, "y_overlap_l2_um": 37, "side_dist_to_l2_um": 1.60},
    "ui_in[3]": {"climb_x_max": 189.00, "y_overlap_l2_um": 0, "side_dist_to_l2_um": 4.00},
    "ui_in[2]": {"climb_x_max": 189.60, "y_overlap_l2_um": 0, "side_dist_to_l2_um": 3.40},
    "ui_in[1]": {"climb_x_max": 190.20, "y_overlap_l2_um": 0, "side_dist_to_l2_um": 2.80},
    "ui_in[0]": {"climb_x_max": 190.80, "y_overlap_l2_um": 0, "side_dist_to_l2_um": 2.20},
}

print("\n=== ui_in crosstalk to V2_in (L2 spiral) estimate ===")
C_T2 = 0.836e-12
f0 = 3.06e9
EPS_LSB = 0.0054
KAPPA = 0.379
df_LSB = 2 * (KAPPA * EPS_LSB) ** 0.5 * f0   # ≈ 9.04% of f0
print(f"LSB Δf splitting = {df_LSB/1e6:.1f} MHz ({df_LSB/f0*100:.2f}% of f0)")

max_xt = 0
for name, info in ui_in_routes_in_l2.items():
    if info["y_overlap_l2_um"] == 0:
        c_um = 0
    else:
        c_um = estimate_coupling_um(max(info["side_dist_to_l2_um"], 0.3),
                                     info["y_overlap_l2_um"])
    df_shift = 0.5 * c_um / C_T2 * f0   # half because Δf₀/f₀ ≈ -ΔC/(2C)
    df_pct = df_shift / f0 * 100 if f0 > 0 else 0
    print(f"  {name}: C_xt={c_um*1e15:.2f} fF, Δf_shift={df_shift/1e6:.2f}MHz ({df_pct:.2f}% f0)")
    if c_um > max_xt: max_xt = c_um

# Pass: max code-toggle Δf shift < LSB Δf shift
max_df_xt = 0.5 * max_xt / C_T2 * f0
print(f"\nMax static crosstalk-induced Δf shift = {max_df_xt/1e6:.2f}MHz = {max_df_xt/f0*100:.2f}% of f0")
print(f"LSB-induced Δf splitting = {df_LSB/1e6:.2f}MHz = {df_LSB/f0*100:.2f}% of f0")
if max_df_xt < df_LSB:
    print("PASS: max crosstalk shift < LSB shift")
else:
    print("FAIL: crosstalk exceeds LSB shift")
