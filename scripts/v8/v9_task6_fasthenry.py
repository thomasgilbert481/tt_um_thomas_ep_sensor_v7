"""Task 6: FastHenry 2-port extraction of L1, L2 spirals → compute M12 and k.

Build a FastHenry input file from the GDS spiral geometry,
run fasthenry, parse the impedance matrix.
"""
import gdstk
import numpy as np
import subprocess
import os
import re

GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M3 = (70, 20); LAY_M4 = (71, 20)
WORKDIR = "/tmp/v9_fasthenry"

# Approximate spiral footprints
L1_BBOX = (10, 30, 140, 150)
L2_BBOX = (190, 30, 330, 160)

# Layer z-heights (sky130 typical, after etch)
# M3 mid-z ≈ 2.0 µm, thickness 0.8 µm
# M4 mid-z ≈ 3.0 µm, thickness 0.8 µm
M3_Z = 2.0
M3_THICK = 0.8
M4_Z = 3.0
M4_THICK = 0.8

# Conductivity of metal (sky130 M3/M4 ≈ aluminum, σ ≈ 30 MS/m for sheet)
SIGMA = 3e7  # S/m


def extract_segments(gds_path, bbox, layer):
    """Extract straight-line metal segments in given bbox for the specified layer.
    Returns list of dicts with x0, y0, x1, y1, width."""
    lib = gdstk.read_gds(gds_path)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
    segs = []
    for p in top.polygons:
        if (p.layer, p.datatype) != layer: continue
        b = p.bounding_box()
        if b is None: continue
        x0, y0 = b[0]; x1, y1 = b[1]
        if x0 < bbox[0] or x1 > bbox[2] or y0 < bbox[1] or y1 > bbox[3]: continue
        w = x1 - x0; h = y1 - y0
        if max(w, h) < 2.0: continue
        # Treat as filament along longest axis
        if w >= h:
            # horizontal: from (x0, (y0+y1)/2) to (x1, (y0+y1)/2), width = h
            y_mid = (y0 + y1) / 2
            segs.append({"x0": x0, "y0": y_mid, "x1": x1, "y1": y_mid, "width": h})
        else:
            x_mid = (x0 + x1) / 2
            segs.append({"x0": x_mid, "y0": y0, "x1": x_mid, "y1": y1, "width": w})
    return segs


def write_fasthenry(segs1_m3, segs1_m4, segs2_m3, segs2_m4, out_path):
    """Build FastHenry input.
    Two ports: L1 (between port nodes N1_a, N1_b) and L2 (between N2_a, N2_b)."""
    nodes = {}
    next_node = [0]

    def get_node(x, y, z, label=""):
        key = (round(x, 3), round(y, 3), round(z, 3))
        if key not in nodes:
            nodes[key] = f"n{next_node[0]}"
            next_node[0] += 1
        return nodes[key]

    lines = []
    lines.append("* FastHenry input for L1, L2 mutual inductance extraction")
    lines.append(".units um")
    lines.append(".default sigma=3e1 nwinc=4 nhinc=2")
    lines.append("")

    # Build M3 + M4 stacked: each filament has parallel M3 and M4 segments
    # FastHenry: define nodes, then segments
    seg_lines = []
    fil_count = 0
    for seg, z, thick, layer_tag in (
            [(s, M3_Z, M3_THICK, "L1m3") for s in segs1_m3] +
            [(s, M4_Z, M4_THICK, "L1m4") for s in segs1_m4] +
            [(s, M3_Z, M3_THICK, "L2m3") for s in segs2_m3] +
            [(s, M4_Z, M4_THICK, "L2m4") for s in segs2_m4]):
        n_a = get_node(seg["x0"], seg["y0"], z, f"{layer_tag}_a{fil_count}")
        n_b = get_node(seg["x1"], seg["y1"], z, f"{layer_tag}_b{fil_count}")
        seg_lines.append(f"E{fil_count} {n_a} {n_b} w={seg['width']:.3f} h={thick:.3f}")
        fil_count += 1

    # Output node definitions
    for (x, y, z), name in nodes.items():
        lines.append(f"N{name} x={x:.3f} y={y:.3f} z={z:.3f}")
    lines.append("")
    lines.extend(seg_lines)
    lines.append("")
    # Simplistic: connect any two arbitrary nodes as ports — but in reality the spiral is
    # one connected path. For now, .external from min to max x of L1, and same for L2.
    # Find approx port nodes
    l1_x = []
    l2_x = []
    for (x, y, z), n in nodes.items():
        if 10 < x < 140 and 30 < y < 150:
            l1_x.append((x, n))
        elif 190 < x < 330 and 30 < y < 160:
            l2_x.append((x, n))
    l1_x.sort(); l2_x.sort()
    if l1_x and l2_x:
        lines.append(f".external {l1_x[0][1]} {l1_x[-1][1]}")
        lines.append(f".external {l2_x[0][1]} {l2_x[-1][1]}")

    lines.append(".freq fmin=2.7e9 fmax=2.7e9 ndec=1")
    lines.append(".end")
    with open(out_path, 'w') as f:
        f.write("\n".join(lines))
    return out_path


def run_fasthenry(inp_path):
    """Run fasthenry, return Zc.mat lines."""
    cwd = os.path.dirname(inp_path)
    r = subprocess.run(["/foss/tools/bin/fasthenry", os.path.basename(inp_path)],
                       cwd=cwd, capture_output=True, text=True, timeout=600)
    return r.stdout, r.stderr, r.returncode


def parse_zc_mat(zc_path):
    """Parse Zc.mat file. Returns 2x2 complex impedance matrix at the freq."""
    with open(zc_path) as f: content = f.read()
    # FastHenry output format: rows of complex numbers per row of matrix
    # Look for "Impedance matrix" or similar
    lines = content.strip().split("\n")
    Z = np.zeros((2, 2), dtype=complex)
    for i, line in enumerate(lines):
        if "Row" in line and " 1" in line:
            # Next line(s) have the row data
            data = lines[i+1].split()
            # ... parse
    # Simpler: assume format is row1: r1+j*x1 r2+j*x2 \n row2: r3+j*x3 r4+j*x4
    # Look for numbers
    nums = re.findall(r"[-+]?\d+\.?\d*[eE]?[-+]?\d*\s*[-+]\s*[-+]?\d+\.?\d*[eE]?[-+]?\d*j", content)
    return Z, nums, content


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    print("Extracting L1 M3+M4 segments...")
    l1_m3 = extract_segments(GDS, L1_BBOX, LAY_M3)
    l1_m4 = extract_segments(GDS, L1_BBOX, LAY_M4)
    print(f"  L1 M3: {len(l1_m3)} M4: {len(l1_m4)}")
    print("Extracting L2 segments...")
    l2_m3 = extract_segments(GDS, L2_BBOX, LAY_M3)
    l2_m4 = extract_segments(GDS, L2_BBOX, LAY_M4)
    print(f"  L2 M3: {len(l2_m3)} M4: {len(l2_m4)}")

    inp = f"{WORKDIR}/spirals.inp"
    write_fasthenry(l1_m3, l1_m4, l2_m3, l2_m4, inp)
    print(f"\nWrote {inp}")
    print(f"  {sum(1 for _ in open(inp))} lines")

    print("\nRunning FastHenry...")
    stdout, stderr, rc = run_fasthenry(inp)
    print(f"  rc={rc}")
    print("STDOUT (last 30 lines):")
    print("\n".join(stdout.split("\n")[-30:]))
    if stderr:
        print("STDERR (last 10 lines):")
        print("\n".join(stderr.split("\n")[-10:]))

    # Look for Zc.mat
    zc_path = f"{WORKDIR}/Zc.mat"
    if os.path.exists(zc_path):
        print(f"\nZc.mat:")
        print(open(zc_path).read()[:2000])
    else:
        print("Zc.mat not found")


if __name__ == "__main__":
    main()
