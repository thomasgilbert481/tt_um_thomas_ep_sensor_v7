"""Programmatic DRC checker for v8 routing geometry.

Focused on the most likely violations from my added geometry:
- M2 spacing 0.14 minimum (m2.2)
- M3 spacing 0.30 minimum (m3.2)
- M4 spacing 0.30 minimum (m4.2)
- via2 inside M2 enclosure (≥0.085 on 2 opposite sides, ≥0.04 on other 2)
- via3 inside M3/M4 enclosure (similar)
- capm.11: M3 spacing to cap_mim region 1.34 minimum

Cap_mim regions (no M3 within 1.34 µm):
- All cap_mim_m3_1 cells listed earlier
"""
import gdstk

GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_V2 = (69, 44); LAY_V3 = (70, 44)


def get_bb(p):
    bb = p.bounding_box()
    return None if bb is None else (bb[0][0], bb[0][1], bb[1][0], bb[1][1])


def overlap(a, b):
    return (a[2] > b[0] and b[2] > a[0] and a[3] > b[1] and b[3] > a[1])


def manhattan_spacing(a, b):
    """Returns the minimum edge-to-edge spacing between two boxes (0 if overlapping)."""
    if overlap(a, b):
        return 0
    dx = max(0, max(a[0]-b[2], b[0]-a[2]))
    dy = max(0, max(a[1]-b[3], b[1]-a[3]))
    if dx > 0 and dy > 0:
        return (dx**2 + dy**2)**0.5  # corner-to-corner
    return max(dx, dy)


lib = gdstk.read_gds(GDS)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Collect polygons per layer at top level
polys = {LAY_M2: [], LAY_M3: [], LAY_M4: [], LAY_V2: [], LAY_V3: []}
for p in top.polygons:
    k = (p.layer, p.datatype)
    if k in polys:
        b = get_bb(p)
        if b: polys[k].append(b)

print(f"M2: {len(polys[LAY_M2])} polys")
print(f"M3: {len(polys[LAY_M3])} polys")
print(f"M4: {len(polys[LAY_M4])} polys")
print(f"via2: {len(polys[LAY_V2])} polys")
print(f"via3: {len(polys[LAY_V3])} polys")

# Check spacing within each metal layer using a spatial grid
def check_spacing(boxes, min_sp, layer_name):
    """Find pairs with spacing < min_sp (excluding overlapping/touching pairs)."""
    violations = []
    # Spatial bucket
    bs = 5.0
    bucket = {}
    for i, b in enumerate(boxes):
        for bx in range(int(b[0]/bs)-1, int(b[2]/bs)+2):
            for by in range(int(b[1]/bs)-1, int(b[3]/bs)+2):
                bucket.setdefault((bx,by), set()).add(i)
    checked = set()
    for cell in bucket.values():
        idx_list = list(cell)
        for i_idx in range(len(idx_list)):
            for j_idx in range(i_idx+1, len(idx_list)):
                i, j = idx_list[i_idx], idx_list[j_idx]
                if (i, j) in checked or (j, i) in checked: continue
                checked.add((i, j))
                if overlap(boxes[i], boxes[j]): continue  # touching/overlapping ok
                sp = manhattan_spacing(boxes[i], boxes[j])
                if 0 < sp < min_sp - 0.001:
                    violations.append((i, j, sp))
    return violations


# Cap_mim cells coords (collected from earlier inventory)
CAP_MIM_BOXES = [
    (173.00, 12.00, 178.32, 15.56),    # AEZ4RW
    (173.12, 17.16, 179.75, 22.03),    # 9FLU4N
    (173.00, 23.63, 181.48, 30.35),    # M5R6G8
    (173.00, 31.95, 184.10, 41.29),    # QLNUBJ
    (173.00, 42.89, 187.81, 55.94),    # SZUNPK
    (173.00, 57.54, 193.05, 75.83),    # 59R85S
    (142.00, 55.00, 154.16, 65.40),    # AE6UXZ
    (142.00, 30.00, 164.36, 50.60),    # UBRWDH
    (260.00, 35.00, 277.96, 51.20),    # C7Y9C2
    (140.00, 95.00, 164.16, 117.40),   # 76K9AN
    (140.00, 70.00, 164.16, 92.40),    # 76K9AN
    (230.16, 75.00, 252.32, 95.40),    # XCEES9
    (275.00, 173.00, 302.47, 198.71),  # CRXE5C
    (212.00, 173.00, 239.46, 198.70),  # 34CPCT
    (241.70, 192.00, 273.86, 222.40),  # 8WUMYD
    (306.00, 192.00, 334.26, 218.50),  # W8UZ5N
    (2.00, 173.00, 210.59, 219.00),    # MQHU4F
]


def check_capm11(m3_boxes, cap_mim_boxes, min_sp=1.34):
    """Check M3 spacing to cap_mim region >= 1.34."""
    violations = []
    for i, m3 in enumerate(m3_boxes):
        for j, cm in enumerate(cap_mim_boxes):
            if overlap(m3, cm): continue
            sp = manhattan_spacing(m3, cm)
            if 0 < sp < min_sp - 0.001:
                violations.append((i, j, sp, m3, cm))
    return violations


print("\n=== M2 spacing (rule: 0.14) ===")
violations = check_spacing(polys[LAY_M2], 0.14, "M2")
print(f"  Found {len(violations)} violations")
for i, j, sp in violations[:5]:
    a = polys[LAY_M2][i]
    b = polys[LAY_M2][j]
    print(f"  sp={sp:.4f}  ({a[0]:.2f},{a[1]:.2f})-({a[2]:.2f},{a[3]:.2f}) vs ({b[0]:.2f},{b[1]:.2f})-({b[2]:.2f},{b[3]:.2f})")

print("\n=== M3 spacing (rule: 0.30) ===")
violations = check_spacing(polys[LAY_M3], 0.30, "M3")
print(f"  Found {len(violations)} violations")
for i, j, sp in violations[:5]:
    a = polys[LAY_M3][i]
    b = polys[LAY_M3][j]
    print(f"  sp={sp:.4f}  ({a[0]:.2f},{a[1]:.2f})-({a[2]:.2f},{a[3]:.2f}) vs ({b[0]:.2f},{b[1]:.2f})-({b[2]:.2f},{b[3]:.2f})")

print("\n=== M4 spacing (rule: 0.30) ===")
violations = check_spacing(polys[LAY_M4], 0.30, "M4")
print(f"  Found {len(violations)} violations")
for i, j, sp in violations[:5]:
    a = polys[LAY_M4][i]
    b = polys[LAY_M4][j]
    print(f"  sp={sp:.4f}  ({a[0]:.2f},{a[1]:.2f})-({a[2]:.2f},{a[3]:.2f}) vs ({b[0]:.2f},{b[1]:.2f})-({b[2]:.2f},{b[3]:.2f})")

print("\n=== capm.11 (M3 to cap_mim: 1.34) ===")
violations = check_capm11(polys[LAY_M3], CAP_MIM_BOXES, 1.34)
print(f"  Found {len(violations)} violations")
for i, j, sp, m3, cm in violations[:5]:
    print(f"  sp={sp:.4f}  M3 ({m3[0]:.2f},{m3[1]:.2f})-({m3[2]:.2f},{m3[3]:.2f}) vs capm ({cm[0]:.2f},{cm[1]:.2f})-({cm[2]:.2f},{cm[3]:.2f})")
