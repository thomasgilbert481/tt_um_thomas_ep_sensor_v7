"""Identify free M2 corridors right of cv-cells for routes 6 and 7."""
import gdstk
V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_V1 = (68, 44); LAY_V2 = (69, 44); LAY_V3 = (70, 44)

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])

lib = gdstk.read_gds(V8)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Identify what's RIGHT of cell column at x=177.54..192 for y=20..170
print("=== ALL polys in x=177.54..192, y=20..172 ===")
for lay, layname in [(LAY_M2,"M2"), (LAY_M3,"M3"), (LAY_M4,"M4"), (LAY_V2,"V2")]:
    matches = []
    for p in top.polygons:
        if (p.layer, p.datatype) != lay: continue
        b = get_bb(p)
        if b is None: continue
        if b[2] > 177.54 and b[0] < 192 and b[3] > 20 and b[1] < 172:
            matches.append(b)
    if matches:
        print(f"\n  {layname}: {len(matches)} polys")
        for b in sorted(matches, key=lambda b: (b[1], b[0])):
            print(f"    ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")

# Also count cap_mim cells (different layer system)
print("\n=== cap_mim cell instances in x=170..200, y=0..200 ===")
for ref in top.references:
    name = ref.cell.name
    if 'cap_mim' not in name: continue
    bb = ref.bounding_box()
    if bb is None: continue
    if bb[1][0] > 170 and bb[0][0] < 200 and bb[1][1] > 0 and bb[0][1] < 200:
        print(f"  {name}: ({bb[0][0]:.2f},{bb[0][1]:.2f})-({bb[1][0]:.2f},{bb[1][1]:.2f})")

# Check V1 horizontal M2 bus at y=180-181 explicitly
print("\n=== M2 polys at y in 178-184 ===")
for p in top.polygons:
    if (p.layer, p.datatype) != LAY_M2: continue
    b = get_bb(p)
    if b is None: continue
    if b[1] < 184 and b[3] > 178:
        if (b[2] - b[0]) > 5:  # only big horizontals
            print(f"  ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")

# Identify big M2 verticals (might be V1 rail)
print("\n=== M2 verticals (W<=3, H>=20) in x=80..210 ===")
for p in top.polygons:
    if (p.layer, p.datatype) != LAY_M2: continue
    b = get_bb(p)
    if b is None: continue
    W = b[2] - b[0]
    H = b[3] - b[1]
    if W < 3 and H >= 20 and b[0] > 80 and b[2] < 210:
        print(f"  ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={W:5.2f} H={H:5.2f}")
