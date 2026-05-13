"""Inventory of top-of-chip routing area to find space for routes 7 & 8.

Maps M2/M3/M4 polygons in:
- Top corridor (y >= 215)
- Right corridor (x >= 195)
- Bottom corridor (y <= 25)
- cap_mim_MQHU4F bounds

Outputs free x slots in y=215-225, free y slots in x=195-225, etc.
"""
import gdstk
import json

V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_CAPM = (89, 44)  # cap_mim layer marker; might also be 70/13 (between M3/M4)
LAY_NWELL = (64, 20)

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])

lib = gdstk.read_gds(V8)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Find cap_mim cells via reference scan
print("=== Cap_mim cells ===")
for ref in top.references:
    name = ref.cell.name
    if name.startswith("cap_mim"):
        bb = ref.bounding_box()
        if bb:
            print(f"  {name}: ({bb[0][0]:.2f},{bb[0][1]:.2f}) -> ({bb[1][0]:.2f},{bb[1][1]:.2f})  origin=({ref.origin[0]:.2f},{ref.origin[1]:.2f})")

print()
print("=== Top corridor: M2/M3/M4 polys with y_min>=215 ===")
for lay, name in [(LAY_M2,"M2"), (LAY_M3,"M3"), (LAY_M4,"M4")]:
    matches = []
    for p in top.polygons:
        if (p.layer, p.datatype) != lay: continue
        b = get_bb(p)
        if b and b[1] >= 215:
            matches.append(b)
    matches.sort(key=lambda b: (b[1], b[0]))
    print(f"\n  {name}: {len(matches)} polys")
    for b in matches:
        print(f"    ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")

print()
print("=== Right corridor: M2/M3/M4 polys with x_min>=195, y in 100-225 ===")
for lay, name in [(LAY_M2,"M2"), (LAY_M3,"M3"), (LAY_M4,"M4")]:
    matches = []
    for p in top.polygons:
        if (p.layer, p.datatype) != lay: continue
        b = get_bb(p)
        if b and b[0] >= 195 and b[1] >= 100 and b[3] <= 225:
            matches.append(b)
    matches.sort(key=lambda b: (b[0], b[1]))
    print(f"\n  {name}: {len(matches)} polys")
    for b in matches[:30]:
        print(f"    ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")

print()
print("=== Bottom corridor: M2/M3/M4 polys with y_max<=30 ===")
for lay, name in [(LAY_M2,"M2"), (LAY_M3,"M3"), (LAY_M4,"M4")]:
    matches = []
    for p in top.polygons:
        if (p.layer, p.datatype) != lay: continue
        b = get_bb(p)
        if b and b[3] <= 30:
            matches.append(b)
    matches.sort(key=lambda b: (b[1], b[0]))
    print(f"\n  {name}: {len(matches)} polys")
    for b in matches[:30]:
        print(f"    ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")
