"""Find free corridors for routes 6 and 7 (cv at 175.8, y=96 and y=118)."""
import gdstk
V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])

lib = gdstk.read_gds(V8)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Box 1: vertical strip at x=175-200, y=20-85 (below row 1 cv-cells, above bottom rails)
# Box 2: vertical strip at x=190-200, y=85-225 (right of cv-cells, climb corridor)
boxes = [
    ("vert strip x=174-180 y=20-85", 174, 20, 180, 85),
    ("vert strip x=190-200 y=20-225", 190, 20, 200, 225),
    ("inter-row1-row2 x=170-200 y=106-108", 170, 106, 200, 108),
    ("inter-row2-row3 x=170-200 y=128-130", 170, 128, 200, 130),
    ("right edge x=200-220 y=20-225", 200, 20, 220, 225),
]
for name, x0, y0, x1, y1 in boxes:
    print(f"\n=== {name} ===")
    for lay, layname in [(LAY_M2,"M2"), (LAY_M3,"M3"), (LAY_M4,"M4")]:
        matches = []
        for p in top.polygons:
            if (p.layer, p.datatype) != lay: continue
            b = get_bb(p)
            if b is None: continue
            # overlap
            if b[2] > x0 and b[0] < x1 and b[3] > y0 and b[1] < y1:
                matches.append(b)
        if matches:
            print(f"  {layname}: {len(matches)} polys")
            for b in matches[:8]:
                print(f"    ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")

# Check cell instances in these boxes
print("\n=== Cell instances overlapping x=170-200 y=20-225 ===")
for ref in top.references:
    bb = ref.bounding_box()
    if bb is None: continue
    if bb[1][0] > 170 and bb[0][0] < 200 and bb[1][1] > 20 and bb[0][1] < 225:
        print(f"  {ref.cell.name}: ({bb[0][0]:.2f},{bb[0][1]:.2f})-({bb[1][0]:.2f},{bb[1][1]:.2f})")
