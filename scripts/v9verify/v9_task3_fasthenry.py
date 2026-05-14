"""v9 Task 3: FastHenry pre-PGS and post-PGS k extraction.

Build proper FastHenry input with all N<name> declared BEFORE E<name> segments.
Generate clean 3-turn square spiral filaments for L1 and L2.
"""
import subprocess, os, re
import numpy as np

FH = "/foss/tools/bin/fasthenry"
WORKDIR = "/tmp/v9_fasthenry"

# Spiral geometry (per project memory + V7_FINAL.md)
# 3-turn square spiral, W=11.6 µm (post-thicken), s=1 µm, OD=128 µm, ID=20 µm
# Center L1: (75, 90), L2: (260, 95)
N_TURNS = 3
WIDTH = 11.6
SPACING = 1.0
OD = 128
ID = 20
M3_Z = 2.0
M4_Z = 3.0
METAL_THICKNESS = 0.8  # each layer
SIGMA = 30  # S/m * 1e-6 — sky130 met3/met4 sheet resistance ~ 0.04 ohm/sq, σ ≈ 30 MS/m


def gen_spiral_filaments(center_x, center_y, turns=N_TURNS, w=WIDTH, s=SPACING, od=OD, id_=ID, label="L"):
    """Generate filaments for a square spiral (M3+M4 stacked) from outside-in.
    Returns list of (x0, y0, z, x1, y1, z, w, h, name).
    Both M3 and M4 layers are returned (in parallel)."""
    fils = []
    # Outer turn at radius od/2 - w/2 = (128-11.6)/2 = 58.2
    # Inner turn at id/2 + w/2 = (20+11.6)/2 = 15.8
    # Going outside-in: 3 turns at r = 58.2, 58.2-w-s = 45.6, 45.6-w-s = 33.0
    r_outer = (od - w) / 2
    pitch = w + s
    # For 3 turns each with 4 segments: 12 segments per layer, 24 total

    # Start at top-left corner of outer turn
    # The path goes (TL → TR) along top, (TR → BR) along right, (BR → BL) along bottom,
    # (BL → IL) one segment inward, then next turn TL, etc.
    # Simplified: 4 straight segments per turn

    for turn in range(turns):
        r = r_outer - turn * pitch
        # Top edge (going right)
        x0 = center_x - r; y0 = center_y + r
        x1 = center_x + r; y1 = center_y + r
        for z, layer in [(M3_Z, "m3"), (M4_Z, "m4")]:
            fils.append((x0, y0, z, x1, y1, z, w, METAL_THICKNESS, f"{label}_{layer}_t{turn}_top"))
        # Right edge (going down)
        x0 = center_x + r; y0 = center_y + r
        x1 = center_x + r; y1 = center_y - r
        for z, layer in [(M3_Z, "m3"), (M4_Z, "m4")]:
            fils.append((x0, y0, z, x1, y1, z, w, METAL_THICKNESS, f"{label}_{layer}_t{turn}_right"))
        # Bottom edge (going left)
        x0 = center_x + r; y0 = center_y - r
        x1 = center_x - r; y1 = center_y - r
        for z, layer in [(M3_Z, "m3"), (M4_Z, "m4")]:
            fils.append((x0, y0, z, x1, y1, z, w, METAL_THICKNESS, f"{label}_{layer}_t{turn}_bot"))
        # Left edge (going up + one step inward for spiral)
        next_r = r_outer - (turn + 1) * pitch if turn + 1 < turns else r - w - s
        x0 = center_x - r; y0 = center_y - r
        x1 = center_x - next_r if turn + 1 < turns else center_x - r + (w + s)
        y1 = center_y + r
        # Going up and slightly right for spiral
        for z, layer in [(M3_Z, "m3"), (M4_Z, "m4")]:
            fils.append((x0, y0, z, x0, y1, z, w, METAL_THICKNESS, f"{label}_{layer}_t{turn}_left"))
    return fils


def gen_pgs_segments(x0, y0, x1, y1, stripe_w=1.0, stripe_gap=1.0, z=1.0, thick=0.4):
    """Generate PGS stripe filaments grounded to a common rail.
    Returns list of filaments and the shared GND-rail node names."""
    fils = []
    x = x0
    while x + stripe_w <= x1:
        fils.append((x + stripe_w/2, y0, z, x + stripe_w/2, y1, z, stripe_w, thick, f"pgs_x{x:.0f}"))
        x += stripe_w + stripe_gap
    return fils


def build_fasthenry_input(fil_list_l1, fil_list_l2, with_pgs=False, pgs_fils=None):
    """Build FastHenry input with proper node-then-segment ordering."""
    lines = []
    lines.append("* FastHenry input for sky130 L1/L2 mutual extraction")
    lines.append(".units um")
    lines.append(f".default sigma=30 nwinc=4 nhinc=2")
    lines.append("")

    # Collect all nodes
    nodes = {}
    def get_node_name(x, y, z):
        key = (round(x, 3), round(y, 3), round(z, 3))
        if key not in nodes:
            nodes[key] = f"n{len(nodes):04d}"
        return nodes[key]

    # First pass: assign node names
    segments_to_write = []
    for fils in [fil_list_l1, fil_list_l2] + ([pgs_fils] if with_pgs else []):
        for x0, y0, z, x1, y1, z2, w, h, name in fils:
            na = get_node_name(x0, y0, z)
            nb = get_node_name(x1, y1, z2)
            segments_to_write.append((name, na, nb, w, h))

    # Declare ALL nodes first
    for (x, y, z), name in sorted(nodes.items()):
        lines.append(f"N{name} x={x:.3f} y={y:.3f} z={z:.3f}")

    lines.append("")
    # Then declare segments
    for name, na, nb, w, h in segments_to_write:
        lines.append(f"E{name} N{na} N{nb} w={w:.3f} h={h:.3f}")

    lines.append("")
    # External ports: L1 start↔end, L2 start↔end
    # Find first and last nodes for L1 (outermost top-left = first, innermost = last)
    l1_first_x, l1_first_y, l1_first_z = fil_list_l1[0][0], fil_list_l1[0][1], fil_list_l1[0][2]
    l1_last_x, l1_last_y, l1_last_z = fil_list_l1[-1][3], fil_list_l1[-1][4], fil_list_l1[-1][5]
    l2_first_x, l2_first_y, l2_first_z = fil_list_l2[0][0], fil_list_l2[0][1], fil_list_l2[0][2]
    l2_last_x, l2_last_y, l2_last_z = fil_list_l2[-1][3], fil_list_l2[-1][4], fil_list_l2[-1][5]

    n1a = get_node_name(l1_first_x, l1_first_y, l1_first_z)
    n1b = get_node_name(l1_last_x, l1_last_y, l1_last_z)
    n2a = get_node_name(l2_first_x, l2_first_y, l2_first_z)
    n2b = get_node_name(l2_last_x, l2_last_y, l2_last_z)
    lines.append(f".external N{n1a} N{n1b} L1port")
    lines.append(f".external N{n2a} N{n2b} L2port")

    lines.append(".freq fmin=2.7e9 fmax=2.7e9 ndec=1")
    lines.append(".end")
    return "\n".join(lines)


def run_fasthenry(inp_path):
    cwd = os.path.dirname(inp_path)
    fn = os.path.basename(inp_path)
    r = subprocess.run([FH, fn], cwd=cwd, capture_output=True, text=True, timeout=900)
    return r.stdout, r.stderr, r.returncode


def parse_zc_mat(zc_path):
    """Parse FastHenry Zc.mat output. Returns 2x2 complex Z matrix."""
    if not os.path.exists(zc_path):
        return None
    with open(zc_path) as f:
        content = f.read()
    # FastHenry format: each row has 2 complex numbers separated by space
    # Look for the impedance data after "Impedance matrix"
    nums = re.findall(r"([-+]?\d+\.?\d*[eE]?[-+]?\d*)\s+([+\-])j([\d.eE+\-]+)", content)
    if len(nums) >= 4:
        Z = np.zeros((2, 2), dtype=complex)
        for i, m in enumerate(nums[:4]):
            real = float(m[0])
            imag = float(m[2]) if m[1] == '+' else -float(m[2])
            Z[i // 2, i % 2] = real + 1j * imag
        return Z
    return None


def main():
    os.makedirs(WORKDIR, exist_ok=True)

    print("Generating L1 filaments...")
    l1 = gen_spiral_filaments(75, 90, label="L1")
    print(f"  L1: {len(l1)} filaments (M3+M4)")

    print("Generating L2 filaments...")
    l2 = gen_spiral_filaments(260, 95, label="L2")
    print(f"  L2: {len(l2)} filaments (M3+M4)")

    # === Pre-PGS extraction ===
    print("\n=== Pre-PGS extraction ===")
    inp_pre = f"{WORKDIR}/pre_pgs.inp"
    with open(inp_pre, 'w') as f:
        f.write(build_fasthenry_input(l1, l2, with_pgs=False))
    print(f"Wrote {inp_pre} ({sum(1 for _ in open(inp_pre))} lines)")
    out, err, rc = run_fasthenry(inp_pre)
    print(f"rc={rc}")
    if rc == 0:
        zc_path = f"{WORKDIR}/Zc.mat"
        if os.path.exists(zc_path):
            print(open(zc_path).read())
        else:
            print("Zc.mat not produced")
    else:
        print("STDERR:")
        print(err[:1000])
        print("STDOUT (last 30):")
        print("\n".join(out.split("\n")[-30:]))


if __name__ == "__main__":
    main()
