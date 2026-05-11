"""Per cv-cell, enumerate the 4 M1 gate paddles in absolute coordinates.
Group by cv-cell so we know exactly where to drop the strap + via stack."""
import gdstk

V7 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M1 = (68, 20)

lib = gdstk.read_gds(V7)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Find cv-cell template
cv_template = next(c for c in lib.cells if "lvt_4WRHDT" in c.name)

# M1 polygons in the template, filtered to "small paddle" shape (< 1x1 µm)
paddles_local = []
for p in cv_template.polygons:
    if (p.layer, p.datatype) != LAY_M1: continue
    bb = p.bounding_box()
    if bb is None: continue
    w = bb[1][0]-bb[0][0]; h = bb[1][1]-bb[0][1]
    if w < 1.0 and h < 1.0:
        paddles_local.append((bb[0][0], bb[0][1], bb[1][0], bb[1][1]))

print(f"cv-template '{cv_template.name}' has {len(paddles_local)} small M1 paddles (local coords):")
for b in sorted(paddles_local, key=lambda x: (x[1], x[0])):
    cx = (b[0]+b[2])/2; cy = (b[1]+b[3])/2
    print(f"  bbox=({b[0]:.3f},{b[1]:.3f})-({b[2]:.3f},{b[3]:.3f})  center=({cx:.3f},{cy:.3f})")

# For each instance, compute absolute paddle positions
print("\nPer cv-cell absolute paddle centers:")
for r in top.references:
    if not r.cell or "lvt_4WRHDT" not in r.cell.name: continue
    ox, oy = r.origin
    rot = r.rotation
    refl = r.x_reflection
    print(f"\n  cv-cell at origin=({ox:.2f},{oy:.2f}) rot={rot} refl={refl}")
    for b in paddles_local:
        cx_loc = (b[0]+b[2])/2; cy_loc = (b[1]+b[3])/2
        # Apply reflection then rotation
        if refl:
            cy_loc = -cy_loc
        if rot == 90:
            cx_loc, cy_loc = -cy_loc, cx_loc
        elif rot == 180:
            cx_loc, cy_loc = -cx_loc, -cy_loc
        elif rot == 270:
            cx_loc, cy_loc = cy_loc, -cx_loc
        cx_abs = ox + cx_loc; cy_abs = oy + cy_loc
        print(f"    paddle center=({cx_abs:.3f},{cy_abs:.3f})")
