"""Find free space on the chip to add a 1.16 pF cap_mim_m3_1.
Need ~24x24 µm area without any cap_mim, spiral, OTA cell, or critical routing."""
import gdstk

GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)

def get_bb(p):
    bb = p.bounding_box()
    return None if bb is None else (bb[0][0], bb[0][1], bb[1][0], bb[1][1])


lib = gdstk.read_gds(GDS)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# All cell instance bboxes
all_cells = []
for r in top.references:
    bb = r.bounding_box()
    if bb is None: continue
    all_cells.append((r.cell.name, bb[0][0], bb[0][1], bb[1][0], bb[1][1]))

# All cap_mim, nfet, pfet, res cells (large blockers)
blockers = [c for c in all_cells if any(s in c[0] for s in ("cap_mim", "nfet", "pfet", "res_"))]

# Also large M3/M4 polys (spirals)
m3_blockers = []
m4_blockers = []
for p in top.polygons:
    b = get_bb(p)
    if b is None: continue
    w = b[2] - b[0]; h = b[3] - b[1]
    if (p.layer, p.datatype) == LAY_M3 and (w > 5 or h > 5):
        m3_blockers.append(b)
    if (p.layer, p.datatype) == LAY_M4 and (w > 5 or h > 5):
        m4_blockers.append(b)

print(f"Cell blockers: {len(blockers)}")
print(f"M3 blockers (>5µm): {len(m3_blockers)}")
print(f"M4 blockers (>5µm): {len(m4_blockers)}")

# Sweep candidate positions: 24×24 µm boxes on a coarse grid
TARGET_W, TARGET_H = 25, 25  # cap_mim_m3_1 with W=24,L=24 → bbox ~25×25
KEEPOUT = 2.0  # safety margin
candidates = []

for x in range(int(KEEPOUT), int(335-TARGET_W-KEEPOUT), 5):
    for y in range(int(KEEPOUT), int(225-TARGET_H-KEEPOUT), 5):
        box = (x, y, x+TARGET_W, y+TARGET_H)
        # Check no cell overlap
        clear = True
        for (name, cx0, cy0, cx1, cy1) in blockers:
            cbox = (cx0-KEEPOUT, cy0-KEEPOUT, cx1+KEEPOUT, cy1+KEEPOUT)
            if (box[2] > cbox[0] and cbox[2] > box[0]
                    and box[3] > cbox[1] and cbox[3] > box[1]):
                clear = False
                break
        if not clear: continue
        # Check no M3/M4 large polys overlap
        for b in m3_blockers + m4_blockers:
            bp = (b[0]-KEEPOUT, b[1]-KEEPOUT, b[2]+KEEPOUT, b[3]+KEEPOUT)
            if (box[2] > bp[0] and bp[2] > box[0]
                    and box[3] > bp[1] and bp[3] > box[1]):
                clear = False
                break
        if clear:
            candidates.append((x, y, x+TARGET_W, y+TARGET_H))

print(f"\nFound {len(candidates)} candidate free spots (25×25 µm with 2µm keepout)")
for c in candidates[:20]:
    print(f"  ({c[0]:.1f}, {c[1]:.1f}) - ({c[2]:.1f}, {c[3]:.1f})")
