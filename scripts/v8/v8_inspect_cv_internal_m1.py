"""Dump all 9 internal M1 polygons of the cv-cell template so we can check
whether my straps overlap or touch any non-gate M1 (drain/source taps)."""
import gdstk

V7 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M1 = (68, 20)

lib = gdstk.read_gds(V7)
cv_template = next(c for c in lib.cells if "lvt_4WRHDT" in c.name)

print(f"cv-cell template bbox: {cv_template.bounding_box()}")
print(f"\nAll M1 polygons in cv-template (local coords):")
m1s = []
for p in cv_template.polygons:
    if (p.layer, p.datatype) != LAY_M1: continue
    bb = p.bounding_box()
    if bb is None: continue
    m1s.append((bb[0][0], bb[0][1], bb[1][0], bb[1][1]))

for b in sorted(m1s, key=lambda x: (x[1], x[0])):
    w = b[2]-b[0]; h = b[3]-b[1]
    typ = "paddle" if w < 1 and h < 1 else "OTHER"
    print(f"  ({b[0]:7.3f},{b[1]:7.3f})-({b[2]:7.3f},{b[3]:7.3f})  W={w:5.2f} H={h:5.2f}  {typ}")

# My strap geometry (in local coords, where cell center is 0,0):
print("\nMy strap geometry (local coords, would-be):")
print(f"  top strap: (-0.43, 10.16)-(0.90, 10.50)")
print(f"  bot strap: (-0.87, -10.40)-(0.90, -10.16)")
print(f"  v_stub:    (0.60, -10.16)-(0.90, 10.16)")
print(f"  M2 escape: (0.60, 10.16)-(1.65, 10.50)  (layer M2)")
print(f"  via1:      (0.665, 10.24)-(0.835, 10.41)  (layer via1)")

print("\nDo any non-paddle M1 polys overlap or touch the straps?")
strap_polys = [
    ("top_strap", -0.43, 10.16, 0.90, 10.50),
    ("bot_strap", -0.87, -10.40, 0.90, -10.16),
    ("v_stub",    0.60, -10.16, 0.90, 10.16),
]
def touch(a, b, tol=0.001):
    return (a[2]+tol >= b[0] and b[2]+tol >= a[0] and
            a[3]+tol >= b[1] and b[3]+tol >= a[1])

for sname, *sb in strap_polys:
    sbox = tuple(sb)
    for mb in m1s:
        w = mb[2]-mb[0]; h = mb[3]-mb[1]
        if w < 1 and h < 1: continue  # skip paddles
        if touch(sbox, mb):
            print(f"  !!! {sname} TOUCHES non-paddle M1 ({mb[0]:.3f},{mb[1]:.3f})-({mb[2]:.3f},{mb[3]:.3f})")
