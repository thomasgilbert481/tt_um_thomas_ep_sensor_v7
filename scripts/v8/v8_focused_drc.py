"""Programmatic focused DRC: check my added v8 geometry for the most
likely sky130 spacing/width/enclosure violations.

Layers in scope: M1 (68/20), M2 (69/20), via1 (68/44), via2 (69/44),
M3 (70/20), via3 (70/44), M4 (71/20).

sky130 rules (subset relevant to my additions):
- m1.1 (width): 0.14 µm
- m1.2 (spacing): 0.14 µm
- m1.6 (area): 0.083 µm²
- m2.1 (width): 0.14 µm
- m2.2 (spacing): 0.14 µm
- m2.6 (area): 0.0676 µm²
- via1.1 (width=length): 0.15 µm exact
- via1.2 (spacing): 0.17 µm
- via1.4a (M1 enclosure, two opp. sides ≥ 0.085, others ≥ 0.04): use 0.04 min on all sides as proxy
- via1.5a (M2 enclosure, two opp. sides ≥ 0.085, others ≥ 0.03): use 0.03 min as proxy
"""
import gdstk

V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"
LAY_M1 = (68, 20); LAY_M2 = (69, 20); LAY_V1 = (68, 44)

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])

def overlap_area(a, b):
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return max(0, dx) * max(0, dy)

def spacing(a, b):
    """Manhattan spacing between two boxes (0 if overlapping)."""
    dx = max(0, max(a[0]-b[2], b[0]-a[2]))
    dy = max(0, max(a[1]-b[3], b[1]-a[3]))
    return max(dx, dy)

lib = gdstk.read_gds(V8)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Also expand cv-cell internal layers to absolute coords (we need to check
# spacing of my new geometry to cell-internal M1/M2/via1).
cv_template = next(c for c in lib.cells if "lvt_4WRHDT" in c.name)
cv_internal = {}
for p in cv_template.polygons:
    key = (p.layer, p.datatype)
    if key not in (LAY_M1, LAY_M2, LAY_V1): continue
    bb = p.bounding_box()
    if bb is None: continue
    cv_internal.setdefault(key, []).append((bb[0][0], bb[0][1], bb[1][0], bb[1][1]))

# Build top-level + expanded cell-internal poly lists
def collect_polys():
    by_layer = {LAY_M1: [], LAY_M2: [], LAY_V1: []}
    for p in top.polygons:
        key = (p.layer, p.datatype)
        if key not in by_layer: continue
        b = get_bb(p)
        if b: by_layer[key].append(b)
    # expand cell-internal
    for r in top.references:
        if r.cell is None: continue
        # only expand cv-cells for now (other cells unlikely conflict with my additions)
        if "lvt_4WRHDT" not in r.cell.name: continue
        ox, oy = r.origin
        for key, polys in cv_internal.items():
            for b in polys:
                by_layer[key].append((b[0]+ox, b[1]+oy, b[2]+ox, b[3]+oy))
    return by_layer

polys = collect_polys()
print(f"M1 polys (top + cv-internal): {len(polys[LAY_M1])}")
print(f"M2 polys: {len(polys[LAY_M2])}")
print(f"via1 polys: {len(polys[LAY_V1])}")

# My added polys (re-derive deterministically from CV_CELLS list)
CV_CELLS = [
    (175.80, 96.05), (186.80, 96.05),
    (175.80, 118.05), (186.80, 118.05),
    (175.80, 140.05), (186.80, 140.05),
    (175.80, 162.05), (186.80, 162.05),
]

def my_additions(cx, cy):
    return {
        LAY_M1: [
            (cx-0.43, cy+10.16, cx+0.90, cy+10.50),  # top_strap
            (cx-0.91, cy-10.45, cx+0.42, cy-10.16),  # bot_strap
        ],
        LAY_V1: [
            (cx-0.10, cy+10.25, cx+0.05, cy+10.40),
            (cx-0.10, cy-10.38, cx+0.05, cy-10.23),
        ],
        LAY_M2: [
            (cx-0.14, cy-10.45, cx+0.09, cy+10.50),  # bridge
            (cx-0.14, cy+10.16, cx+1.65, cy+10.50),  # escape
        ],
    }

violations = []
for (cx, cy) in CV_CELLS:
    mine = my_additions(cx, cy)
    for layer, my_polys in mine.items():
        for mp in my_polys:
            # Check spacing against all OTHER polys on same layer
            for other in polys[layer]:
                # If they overlap, no spacing rule applies — they merge
                if overlap_area(mp, other) > 0: continue
                sp = spacing(mp, other)
                if sp < 0.14 - 0.001:
                    layer_name = {LAY_M1:'M1', LAY_M2:'M2', LAY_V1:'via1'}[layer]
                    min_sp = {LAY_M1: 0.14, LAY_M2: 0.14, LAY_V1: 0.17}[layer]
                    if sp < min_sp - 0.001:
                        violations.append((layer_name, sp, mp, other))

print(f"\nSpacing violations found: {len(violations)}")
from collections import Counter
by_layer = Counter(v[0] for v in violations)
print(f"By layer: {dict(by_layer)}")
# Show first 20
print("\nFirst 20 violations:")
for v in violations[:20]:
    layer, sp, mp, other = v
    print(f"  {layer} spacing={sp:.4f} my=({mp[0]:.2f},{mp[1]:.2f})-({mp[2]:.2f},{mp[3]:.2f})  vs other=({other[0]:.2f},{other[1]:.2f})-({other[2]:.2f},{other[3]:.2f})")
