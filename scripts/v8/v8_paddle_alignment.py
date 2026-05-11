"""Find the exact x-extent of all 4 paddles per cv-cell (combining top-level
and cell-internal versions) so my strap fully encloses them — no width
violations from misaligned wings."""
import gdstk
V7 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M1 = (68, 20)

lib = gdstk.read_gds(V7)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
cv_template = next(c for c in lib.cells if "lvt_4WRHDT" in c.name)

# All small M1 in template (cell-internal paddles)
internal = []
for p in cv_template.polygons:
    if (p.layer, p.datatype) != LAY_M1: continue
    bb = p.bounding_box()
    if bb is None: continue
    if (bb[1][0]-bb[0][0]) < 1.0 and (bb[1][1]-bb[0][1]) < 1.0:
        internal.append((bb[0][0], bb[0][1], bb[1][0], bb[1][1]))

# Top-level small M1 (at cv-cell positions)
toplev = []
for p in top.polygons:
    if (p.layer, p.datatype) != LAY_M1: continue
    bb = p.bounding_box()
    if bb is None: continue
    if (bb[1][0]-bb[0][0]) < 1.0 and (bb[1][1]-bb[0][1]) < 1.0:
        # only near a cv-cell
        if 170 < bb[0][0] < 195 and 80 < bb[0][1] < 200:
            toplev.append((bb[0][0], bb[0][1], bb[1][0], bb[1][1]))

print("Cell-internal paddles (local coords):")
for b in sorted(internal, key=lambda x: (x[1], x[0])):
    print(f"  ({b[0]:7.3f},{b[1]:7.3f})-({b[2]:7.3f},{b[3]:7.3f})  W={b[2]-b[0]:.3f} H={b[3]-b[1]:.3f}")

print("\nTop-level paddles (absolute coords; only first cv-cell at (175.8, 96)):")
cell_paddles = [b for b in toplev if 173 < b[0] < 178 and 85 < b[1] < 108]
for b in sorted(cell_paddles, key=lambda x: (x[1], x[0])):
    print(f"  ({b[0]:7.3f},{b[1]:7.3f})-({b[2]:7.3f},{b[3]:7.3f})  W={b[2]-b[0]:.3f} H={b[3]-b[1]:.3f}")

# Compute the COMBINED x-extent for top paddles and bot paddles of cv-cell at (175.8, 96)
top_paddles = [b for b in cell_paddles if b[1] > 100]  # top edge
bot_paddles = [b for b in cell_paddles if b[1] < 100]  # bot edge
if top_paddles:
    top_x_min = min(b[0] for b in top_paddles)
    top_x_max = max(b[2] for b in top_paddles)
    top_y_min = min(b[1] for b in top_paddles)
    top_y_max = max(b[3] for b in top_paddles)
    print(f"\nTop paddles combined: x=({top_x_min:.3f}..{top_x_max:.3f})  y=({top_y_min:.3f}..{top_y_max:.3f})")
if bot_paddles:
    bot_x_min = min(b[0] for b in bot_paddles)
    bot_x_max = max(b[2] for b in bot_paddles)
    bot_y_min = min(b[1] for b in bot_paddles)
    bot_y_max = max(b[3] for b in bot_paddles)
    print(f"Bot paddles combined: x=({bot_x_min:.3f}..{bot_x_max:.3f})  y=({bot_y_min:.3f}..{bot_y_max:.3f})")
print(f"\nFor cx=175.80, cy=96.05:")
print(f"  Top paddles in local coords: x=({top_x_min-175.80:.3f}..{top_x_max-175.80:.3f})  y=({top_y_min-96.05:.3f}..{top_y_max-96.05:.3f})")
print(f"  Bot paddles in local coords: x=({bot_x_min-175.80:.3f}..{bot_x_max-175.80:.3f})  y=({bot_y_min-96.05:.3f}..{bot_y_max-96.05:.3f})")
