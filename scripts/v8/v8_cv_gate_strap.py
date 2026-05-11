"""v8 step 1 (revised): per cv-cell, add M1 straps tying all 4 gate paddles,
plus via1 + M2 vertical bridge + M2 horizontal escape paddle.

The cv-cell template has 5 internal M1 vertical strips (drain/source taps)
spanning the cell's full y at x = -1.075, -0.595, -0.115, 0.365, 0.845 in
local coords. These strips have 0.23 µm width and 0.25 µm spacing → no
0.30-µm M1 channel exists between them. So we must bridge top and bottom
gate straps via M2 (which doesn't conflict with internal M1).

Per cv-cell at (cx, cy):
- M1 top strap: x=(cx-0.43, cy+10.16)..(cx+0.90, cy+10.50) — ties 2 top paddles
- M1 bot strap: x=(cx-0.87, cy-10.46)..(cx+0.42, cy-10.12) — ties 2 bot paddles
  (Height 0.34 to fit via1 with 0.04 enclosure each side; covers both paddles)
- via1 (0.15x0.15) on top strap: at center (cx-0.025, cy+10.325)
- via1 (0.15x0.15) on bot strap: at center (cx-0.025, cy-10.29)
- M2 vertical bridge: x=(cx-0.14, cy-10.40)..(cx+0.09, cy+10.50)  (width 0.23)
  spans both via1s and a bit beyond, full cell height.
- M2 escape paddle: x=(cx-0.14, cy+10.16)..(cx+1.65, cy+10.50) (horizontal)
  Overlaps vertical bridge at the top, extends right by 1.65 µm.
"""
import gdstk

V7 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M1 = (68, 20)
LAY_M2 = (69, 20)
LAY_V1 = (68, 44)

CV_CELLS = [
    (175.80,  96.05), (186.80,  96.05),
    (175.80, 118.05), (186.80, 118.05),
    (175.80, 140.05), (186.80, 140.05),
    (175.80, 162.05), (186.80, 162.05),
]

def main():
    lib = gdstk.read_gds(V7)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

    for (cx, cy) in CV_CELLS:
        # M1 top strap
        top_strap = gdstk.rectangle(
            (cx - 0.43, cy + 10.16), (cx + 0.90, cy + 10.50),
            layer=LAY_M1[0], datatype=LAY_M1[1])
        # M1 bot strap — H=0.29; top edge matches paddle top to preserve
        # 0.16 µm spacing to cell-internal drain/source strips below cell origin.
        # x extends from -0.91 (leftmost paddle) to +0.42 (rightmost paddle).
        bot_strap = gdstk.rectangle(
            (cx - 0.91, cy - 10.45), (cx + 0.42, cy - 10.16),
            layer=LAY_M1[0], datatype=LAY_M1[1])
        # via1 top: centered at (cx-0.025, cy+10.325), 0.15x0.15
        via1_top = gdstk.rectangle(
            (cx - 0.100, cy + 10.250), (cx + 0.050, cy + 10.400),
            layer=LAY_V1[0], datatype=LAY_V1[1])
        # via1 bot: centered at (cx-0.025, cy-10.305), 0.15x0.15
        via1_bot = gdstk.rectangle(
            (cx - 0.100, cy - 10.380), (cx + 0.050, cy - 10.230),
            layer=LAY_V1[0], datatype=LAY_V1[1])
        # M2 vertical bridge — spans cell height; widened so via1 has ≥0.085
        # M2 enclosure on both horizontal sides (met2.5 rule). via1 x=cx-0.10..cx+0.05,
        # M2 bridge x=cx-0.20..cx+0.15 gives 0.10 / 0.10 horizontal enclosure ≥0.085.
        m2_bridge = gdstk.rectangle(
            (cx - 0.20, cy - 10.45), (cx + 0.15, cy + 10.50),
            layer=LAY_M2[0], datatype=LAY_M2[1])
        # M2 escape paddle — horizontal, overlapping vertical bridge at top
        m2_escape = gdstk.rectangle(
            (cx - 0.20, cy + 10.16), (cx + 1.65, cy + 10.50),
            layer=LAY_M2[0], datatype=LAY_M2[1])
        for poly in (top_strap, bot_strap, via1_top, via1_bot, m2_bridge, m2_escape):
            top.add(poly)

    OUT = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"
    lib.write_gds(OUT)
    print(f"Wrote v8 draft to {OUT}")
    print(f"Added 6 polys per cv-cell x 8 cells = 48 new polys")

if __name__ == "__main__":
    main()
