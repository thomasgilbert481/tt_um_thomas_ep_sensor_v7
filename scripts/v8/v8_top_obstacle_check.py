"""Check for M4 power rails and obstacles in top corridor for routes 6, 7."""
import gdstk
V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_TXT = (64, 59)  # text labels
LAY_VPWR_LBL = (71, 5)  # M4 pin label

def get_bb(p):
    bb = p.bounding_box()
    if bb is None: return None
    return (bb[0][0], bb[0][1], bb[1][0], bb[1][1])

lib = gdstk.read_gds(V8)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Find all labels at top and bottom of chip with positions (use both labels and texts)
print("=== M4 labels (text, pin) at top of chip y>=200 ===")
for L in top.labels:
    if L.layer == LAY_M4[0] and L.origin[1] >= 200:
        print(f"  M4 layer={L.layer}/{L.texttype} '{L.text}' at ({L.origin[0]:.2f}, {L.origin[1]:.2f})")

print()
print("=== M4 polys spanning chip vertically (H>=100) — power rails ===")
for p in top.polygons:
    if (p.layer, p.datatype) != LAY_M4: continue
    b = get_bb(p)
    if b and (b[3] - b[1]) >= 100:
        print(f"  ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")

print()
print("=== M2 polys spanning chip vertically (H>=100) — power/V1 rails ===")
for p in top.polygons:
    if (p.layer, p.datatype) != LAY_M2: continue
    b = get_bb(p)
    if b and (b[3] - b[1]) >= 100:
        print(f"  ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")

print()
print("=== ALL ui_in pad x positions (M4 polys with y_min>=224.76, y_max<=225.76, W~0.30) ===")
ui_pads = []
for p in top.polygons:
    if (p.layer, p.datatype) != LAY_M4: continue
    b = get_bb(p)
    if b and b[1] >= 224.5 and b[3] <= 225.8 and (b[2]-b[0]) <= 1.0 and (b[3]-b[1]) >= 0.8:
        ui_pads.append(b)
ui_pads.sort(key=lambda b: b[0])
for b in ui_pads:
    cx = (b[0]+b[2])/2
    print(f"  ui pad x={cx:.2f}: ({b[0]:.2f},{b[1]:.2f})-({b[2]:.2f},{b[3]:.2f})")

print()
print("=== M4 polys in y=215-225 ROI x=100-220 (top corridor obstacles) ===")
for p in top.polygons:
    if (p.layer, p.datatype) != LAY_M4: continue
    b = get_bb(p)
    if b is None: continue
    # Wide M4 polys (not pad stubs) in top corridor
    if b[3] >= 215 and b[1] <= 225 and b[0] >= 100 and b[2] <= 220:
        if (b[2]-b[0]) >= 1.0 or (b[3]-b[1]) >= 2.5:  # excludes 0.30x1.0 pad stubs
            print(f"  ({b[0]:6.2f},{b[1]:6.2f})-({b[2]:6.2f},{b[3]:6.2f})  W={b[2]-b[0]:5.2f} H={b[3]-b[1]:5.2f}")
