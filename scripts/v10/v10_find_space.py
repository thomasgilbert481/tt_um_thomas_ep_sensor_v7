"""Find free 7x40 µm rectangles in v9 GDS for adding NQVC98 cells in v10."""
import gdstk

GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"


def get_bb(p):
    bb = p.bounding_box()
    return None if bb is None else (bb[0][0], bb[0][1], bb[1][0], bb[1][1])


lib = gdstk.read_gds(GDS)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

# Cell instance bboxes
cell_bbs = []
for r in top.references:
    bb = r.bounding_box()
    if bb is None: continue
    cell_bbs.append((r.cell.name, bb[0][0], bb[0][1], bb[1][0], bb[1][1]))

# Spiral footprint bbs (M3/M4 large polys)
LAY_M3 = (70, 20); LAY_M4 = (71, 20)
big_metal = []
for p in top.polygons:
    if (p.layer, p.datatype) not in [LAY_M3, LAY_M4]: continue
    b = get_bb(p)
    if b is None: continue
    if (b[2]-b[0]) > 5 and (b[3]-b[1]) > 5:
        big_metal.append(b)

print(f"Cells: {len(cell_bbs)}")
print(f"Big metal polys (>5x5): {len(big_metal)}")

# Candidate placement: NQVC98 footprint is ~7×40
TGT_W, TGT_H = 8, 42  # with margin
KEEPOUT = 1.5

candidates = []
# Try both orientations
ORIENTATIONS = [(TGT_W, TGT_H), (TGT_H, TGT_W)]  # narrow-tall and wide-short
for w, h in ORIENTATIONS:
 for x0 in range(0, 335 - int(w), 2):
    for y0 in range(0, 226 - int(h), 2):
        x1 = x0 + w
        y1 = y0 + h
        x1 = x0 + TGT_W
        y1 = y0 + TGT_H
        box = (x0, y0, x1, y1)
        clear = True
        # Cell overlap
        for (n, cx0, cy0, cx1, cy1) in cell_bbs:
            kb = (cx0-KEEPOUT, cy0-KEEPOUT, cx1+KEEPOUT, cy1+KEEPOUT)
            if box[2] > kb[0] and kb[2] > box[0] and box[3] > kb[1] and kb[3] > box[1]:
                clear = False; break
        if not clear: continue
        # Big-metal overlap
        for mb in big_metal:
            kb = (mb[0]-KEEPOUT, mb[1]-KEEPOUT, mb[2]+KEEPOUT, mb[3]+KEEPOUT)
            if box[2] > kb[0] and kb[2] > box[0] and box[3] > kb[1] and kb[3] > box[1]:
                clear = False; break
        if clear:
            candidates.append((box, (w, h)))

print(f"Free slots found: {len(candidates)}")
# Group by orientation and show non-overlapping ones
horiz = [c for c, o in candidates if o == (TGT_H, TGT_W)]
vert = [c for c, o in candidates if o == (TGT_W, TGT_H)]
print(f"  Horizontal (42x8): {len(horiz)} slots")
print(f"  Vertical (8x42): {len(vert)} slots")
print("\nHorizontal (42x8) candidates:")
for c in horiz[:30]:
    print(f"  ({c[0]:.1f}, {c[1]:.1f}) - ({c[2]:.1f}, {c[3]:.1f})")
