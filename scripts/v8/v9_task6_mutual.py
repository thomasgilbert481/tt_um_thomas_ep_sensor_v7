"""Task 6: Compute mutual inductance M12 between L1 and L2 spirals
using Neumann's formula via numerical integration over spiral filament segments.

Pass criterion: |k| = |M12| / sqrt(L1·L2) ≤ 0.02
"""
import gdstk
import numpy as np

GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M3 = (70, 20); LAY_M4 = (71, 20)

# Spiral footprints (approximate, from V7_FINAL.md / project memory)
L1_BBOX = (10, 30, 140, 150)   # x_min, y_min, x_max, y_max — left spiral
L2_BBOX = (190, 30, 330, 160)  # right spiral
# Spiral metal layers
SPIRAL_LAYERS = [LAY_M3, LAY_M4]

MU0 = 4 * np.pi * 1e-7  # H/m


def extract_spiral_segments(gds_path, bbox, layers):
    """Extract spiral metal traces in the given bbox.
    Returns list of (x_center, y_center, length, direction_vector) for each segment.
    Spiral segments are horizontal or vertical rectangles."""
    lib = gdstk.read_gds(gds_path)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
    segs = []
    for p in top.polygons:
        if (p.layer, p.datatype) not in layers: continue
        b = p.bounding_box()
        if b is None: continue
        x0, y0 = b[0]
        x1, y1 = b[1]
        # Filter to bbox
        if x0 < bbox[0] or x1 > bbox[2] or y0 < bbox[1] or y1 > bbox[3]: continue
        w = x1 - x0
        h = y1 - y0
        if max(w, h) < 1.0: continue  # skip tiny features
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        if w >= h:
            # Horizontal segment
            length = w
            direction = (1.0, 0.0)
        else:
            length = h
            direction = (0.0, 1.0)
        segs.append({"cx": cx, "cy": cy, "length": length, "dir": direction,
                     "layer": (p.layer, p.datatype), "bbox": (x0, y0, x1, y1)})
    # Deduplicate (M3 and M4 might have same geometry at same position — count once for M)
    # Actually for parallel M3+M4, they carry the same current, count as ONE filament
    # Group by (cx, cy, length, direction)
    unique = {}
    for s in segs:
        key = (round(s["cx"], 2), round(s["cy"], 2), round(s["length"], 2), s["dir"])
        unique[key] = s
    return list(unique.values())


def neumann_mutual_um(seg1, seg2):
    """Neumann mutual inductance between two filaments (length in µm).
    Returns mutual in H."""
    L1 = seg1["length"] * 1e-6  # m
    L2 = seg2["length"] * 1e-6
    cx1 = seg1["cx"] * 1e-6
    cy1 = seg1["cy"] * 1e-6
    cx2 = seg2["cx"] * 1e-6
    cy2 = seg2["cy"] * 1e-6
    d1 = seg1["dir"]
    d2 = seg2["dir"]
    # Dot product of direction vectors
    dot = d1[0]*d2[0] + d1[1]*d2[1]
    if abs(dot) < 1e-9: return 0.0  # perpendicular segments: M ≈ 0
    # Numerical integration of Neumann formula
    # M = (μ0/4π) ∫∫ (dl1·dl2)/r
    N = 30  # integration points per segment
    M = 0.0
    for i in range(N):
        t1 = (i + 0.5) / N - 0.5
        x1 = cx1 + d1[0] * L1 * t1
        y1 = cy1 + d1[1] * L1 * t1
        for j in range(N):
            t2 = (j + 0.5) / N - 0.5
            x2 = cx2 + d2[0] * L2 * t2
            y2 = cy2 + d2[1] * L2 * t2
            dx = x1 - x2
            dy = y1 - y2
            # Assume z=0 plane (planar spiral); add small height for self-cap
            r = np.sqrt(dx*dx + dy*dy + 1e-12)
            if r < 5e-7: continue  # avoid singularity
            M += dot * (L1/N) * (L2/N) / r
    M *= MU0 / (4 * np.pi)
    return M


def total_self_inductance(segs):
    """Approximate self-inductance via segment self-L + mutual between own segments."""
    L_total = 0.0
    for i, s1 in enumerate(segs):
        # Self-L of a rectangular strip (Grover formula approximation, treating as wire)
        l = s1["length"] * 1e-6
        # Assume W ≈ 11.6 µm (v7 thicken: 10+0.8*2), H_metal ≈ 1 µm
        w = 11.6e-6
        h = 1.0e-6
        # Self-inductance of rectangular bar (Grover)
        L_self = (MU0 * l / (2 * np.pi)) * (np.log(2*l / (w+h)) + 0.5 + 0.2235 * (w+h)/l)
        L_total += L_self
        # Add mutual between own segments
        for j, s2 in enumerate(segs):
            if i == j: continue
            M = neumann_mutual_um(s1, s2)
            L_total += M
    return L_total


def total_mutual(segs1, segs2):
    """Sum mutual inductance between all segment pairs."""
    M_total = 0.0
    for s1 in segs1:
        for s2 in segs2:
            M_total += neumann_mutual_um(s1, s2)
    return M_total


print("Extracting L1 spiral segments...")
L1_segs = extract_spiral_segments(GDS, L1_BBOX, SPIRAL_LAYERS)
print(f"  L1: {len(L1_segs)} unique segments")
print("Extracting L2 spiral segments...")
L2_segs = extract_spiral_segments(GDS, L2_BBOX, SPIRAL_LAYERS)
print(f"  L2: {len(L2_segs)} unique segments")

print("\nComputing mutual inductance via Neumann integration...")
M12 = total_mutual(L1_segs, L2_segs)
print(f"  M12 = {M12*1e12:.3f} pH")

print("\nComputing self-inductance via Grover + Neumann...")
L1_self = total_self_inductance(L1_segs)
L2_self = total_self_inductance(L2_segs)
print(f"  L1 = {L1_self*1e9:.3f} nH")
print(f"  L2 = {L2_self*1e9:.3f} nH")

# k = M / sqrt(L1*L2)
if L1_self > 0 and L2_self > 0:
    k = M12 / np.sqrt(L1_self * L2_self)
    print(f"\nMutual coupling k = M12/sqrt(L1·L2) = {k:.5f}")
    print(f"  |k| = {abs(k):.5f}")
    if abs(k) <= 0.02:
        print(f"  PASS: |k| = {abs(k):.5f} ≤ 0.02")
    else:
        print(f"  FAIL: |k| = {abs(k):.5f} > 0.02 — need v9 mitigation (PGS or rotation)")
        print(f"  Action: re-run cv sweep with K_M12={k:.4f} in deck to check slope impact")
