"""Map the routing landscape for v8 cv-array gate routing.

Goal: route 8 separate gate signals from ui_in[i] M4 pads (at chip top
y=225) to cv-cell M1 gate paddles (at y=85-173). The existing y=180-181
M2 horizontal V1 bus is the main obstacle — avoid it.

Output: per-layer occupancy map of the region x=8-330, y=85-225 in a grid,
plus a list of free channels (rectangles where no metal exists on a given
layer).
"""
import gdstk

V7 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"

LAY_M1 = (68, 20)
LAY_M2 = (69, 20)
LAY_M3 = (70, 20)
LAY_M4 = (71, 20)

# Region of interest
ROI = (100, 80, 200, 230)

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])

def overlaps_roi(b):
    return (b[2] > ROI[0] and b[0] < ROI[2] and
            b[3] > ROI[1] and b[1] < ROI[3])

def in_roi(b):
    return (b[0] >= ROI[0] and b[2] <= ROI[2] and
            b[1] >= ROI[1] and b[3] <= ROI[3])

lib = gdstk.read_gds(V7)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Collect ROI polys per layer
polys = {LAY_M1: [], LAY_M2: [], LAY_M3: [], LAY_M4: []}
for p in top.polygons:
    key = (p.layer, p.datatype)
    if key not in polys: continue
    b = get_bb(p)
    if b and overlaps_roi(b):
        polys[key].append(b)

print(f"ROI x=[{ROI[0]},{ROI[2]}], y=[{ROI[1]},{ROI[3]}]\n")
for lay, name in [(LAY_M1,'M1'), (LAY_M2,'M2'), (LAY_M3,'M3'), (LAY_M4,'M4')]:
    print(f"\n=== {name} polys in ROI: {len(polys[lay])} ===")
    # Sort by y then x
    for b in sorted(polys[lay], key=lambda x: (x[1], x[0]))[:40]:
        print(f"  ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")
