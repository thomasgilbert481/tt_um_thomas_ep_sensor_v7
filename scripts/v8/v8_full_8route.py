"""v8 FULL 8-route cv-array routing from v7 baseline.

Strategy: 8 distinct y_H slots at pitch 0.60 (height 0.30) in the top corridor.

Right-col cv-cells (x=186.8): direct M2 climb from escape paddle UP to y_H+0.40.
Left-col cv-cells (x=175.8): M2 ext + M3 jog + M2 climb up.

KEY CONSTRAINT: M2 climbs of route j pass through escape y ranges of higher
cv-cell rows. To avoid shorts, the climb x of each route must be CLEAR of all
higher cv-cells' east-extension x ranges.

Specifically, ORDER climbs by cv-cell y (DESCENDING): top cv-cell → leftmost climb.
- cv(186.8, 162) climb at x=188.60-189.00 (leftmost, just right of strap end 188.45)
- cv(186.8, 140) climb at x=189.20-189.60 (≥ cv(186.8,162) east ext end 189.05 + 0.14)
- cv(186.8, 118) climb at x=189.80-190.20 (≥ cv(186.8,140) east ext end 189.65 + 0.14)
- cv(186.8,  96) climb at x=190.40-190.80 (≥ cv(186.8,118) east ext end 190.25 + 0.14)
- cv(175.8, 162) climb at x=191.00-191.40 (≥ cv(186.8, 96) east ext end 190.85 + 0.14)
- cv(175.8, 140) climb at x=191.55-191.95
- cv(175.8, 118) climb at x=192.10-192.50
- cv(175.8,  96) climb at x=192.65-193.05

y_H assignments (higher ui_in_x -> higher y_H to avoid M3 V crossings):
  ui_in[7] (x=119.14) -> y_H=220.50   cv(175.8, 96.05)
  ui_in[6] (x=121.90) -> y_H=221.10   cv(175.8, 118.05)
  ui_in[5] (x=124.66) -> y_H=221.70   cv(175.8, 140.05)
  ui_in[4] (x=127.42) -> y_H=222.30   cv(175.8, 162.05)
  ui_in[3] (x=130.18) -> y_H=222.90   cv(186.8, 162.05)
  ui_in[2] (x=132.94) -> y_H=223.50   cv(186.8, 140.05)
  ui_in[1] (x=135.70) -> y_H=224.10   cv(186.8, 118.05)
  ui_in[0] (x=138.46) -> y_H=224.70   cv(186.8, 96.05)
"""
import gdstk

V7 = "/tmp/v7_baseline.gds"
OUT = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"

LAY_M1 = (68, 20); LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_V1 = (68, 44); LAY_V2 = (69, 44); LAY_V3 = (70, 44)

CV_CELLS = [
    (175.80, 96.05),  (186.80, 96.05),
    (175.80, 118.05), (186.80, 118.05),
    (175.80, 140.05), (186.80, 140.05),
    (175.80, 162.05), (186.80, 162.05),
]

# Per-route geometry, ordered for clear M2 climb spacing.
# y_H slots at pitch 0.65 (height 0.35, gap 0.30, 8 slots from 220.50 to 225.05)
ROUTES = [
    # idx, cv_x, cv_y, ui_x, y_H, climb_x0, climb_x1, jog_y, m2_down_x0, m2_down_x1
    (0, 186.80,  96.05, 138.46, 225.05, 190.40, 190.80, None, None, None),
    (1, 186.80, 118.05, 135.70, 224.40, 189.80, 190.20, None, None, None),
    (2, 186.80, 140.05, 132.94, 223.75, 189.20, 189.60, None, None, None),
    (3, 186.80, 162.05, 130.18, 223.10, 188.60, 189.00, None, None, None),
    (4, 175.80, 162.05, 127.42, 222.45, 191.00, 191.40, 170.40, None, None),
    (5, 175.80, 140.05, 124.66, 221.80, 191.55, 191.95, 148.50, None, None),
    # Route 6 jog_y=80.65 to give 0.30 gap to route 7's jog at 80.00 (with height 0.35)
    (6, 175.80, 118.05, 121.90, 221.15, 192.10, 192.50,  80.65, 177.60, 178.00),
    (7, 175.80,  96.05, 119.14, 220.50, 192.65, 193.05,  80.00, 175.60, 175.95),
]

M3_H_HEIGHT = 0.35   # M3 H height (M3 encl via2 = 0.075 ≥ 0.065 ✓)
CHIP_TOP_M3 = 225.65  # M3 V top edge (extended for via3 enclosure)
PAD_TOP_Y = 225.76    # chip top / M4 pad top
PAD_BOT_Y = 224.76    # M4 pad bottom


def add_strap(top, cx, cy):
    polys = [
        gdstk.rectangle((cx-0.43, cy+10.16), (cx+0.90, cy+10.50), layer=68, datatype=20),
        gdstk.rectangle((cx-0.91, cy-10.45), (cx+0.42, cy-10.16), layer=68, datatype=20),
        gdstk.rectangle((cx-0.10, cy+10.25), (cx+0.05, cy+10.40), layer=68, datatype=44),
        gdstk.rectangle((cx-0.10, cy-10.38), (cx+0.05, cy-10.23), layer=68, datatype=44),
        gdstk.rectangle((cx-0.20, cy-10.45), (cx+0.15, cy+10.50), layer=69, datatype=20),
        gdstk.rectangle((cx-0.20, cy+10.16), (cx+1.65, cy+10.50), layer=69, datatype=20),
    ]
    for p in polys:
        top.add(p)


def add_route(top, route):
    idx, cx, cy, ui_x, y_H, cx0, cx1, jog_y, m2_down_x0, m2_down_x1 = route

    if jog_y is None:
        # RIGHT-COL cv(186.8, *): M2 east extension + M2 climb
        # East ext from strap end (cx+1.65=188.45) to cx1+0.05
        top.add(gdstk.rectangle((cx+1.65-0.04, cy+10.16),
                                 (cx1+0.05, cy+10.50),
                                 layer=69, datatype=20))
        # M2 climb
        top.add(gdstk.rectangle((cx0, cy+10.16), (cx1, y_H+0.40),
                                 layer=69, datatype=20))
    else:
        # LEFT-COL cv(175.8, *)
        if jog_y < cy:  # routes 6, 7: jog BELOW cells
            # For route 6, the M2 down column is OUTSIDE cv-cell footprint (x>=177.60).
            # Need east extension of escape paddle to bridge to column.
            if m2_down_x0 > cx + 1.65:
                # East extension from strap end (cx+1.65) to m2_down_x1+0.05
                top.add(gdstk.rectangle((cx + 1.65 - 0.04, cy+10.16),
                                         (m2_down_x1 + 0.05, cy+10.50),
                                         layer=69, datatype=20))
            # M2 column going DOWN
            top.add(gdstk.rectangle((m2_down_x0, jog_y-0.20),
                                     (m2_down_x1, cy+10.50),
                                     layer=69, datatype=20))
            v2_x = (m2_down_x0 + m2_down_x1) / 2
            top.add(gdstk.rectangle((v2_x-0.10, jog_y-0.10),
                                     (v2_x+0.10, jog_y+0.10),
                                     layer=69, datatype=44))
            # M3 jog
            # M3 jog height 0.35 (via2 encl 0.075 each side ≥ 0.065)
            top.add(gdstk.rectangle((m2_down_x0-0.10, jog_y-0.175),
                                     (cx1+0.10, jog_y+0.175),
                                     layer=70, datatype=20))
            v2_cx_climb = (cx0 + cx1) / 2
            top.add(gdstk.rectangle((v2_cx_climb-0.10, jog_y-0.10),
                                     (v2_cx_climb+0.10, jog_y+0.10),
                                     layer=69, datatype=44))
        else:  # routes 4, 5: jog ABOVE cells
            ext_x0 = cx + 1.45
            ext_x1 = cx + 1.85
            top.add(gdstk.rectangle((ext_x0, jog_y-0.20),
                                     (ext_x1, cy+10.50),
                                     layer=69, datatype=20))
            v2_x = (ext_x0 + ext_x1) / 2
            top.add(gdstk.rectangle((v2_x-0.10, jog_y-0.10),
                                     (v2_x+0.10, jog_y+0.10),
                                     layer=69, datatype=44))
            # M3 jog height 0.35
            top.add(gdstk.rectangle((ext_x0-0.10, jog_y-0.175),
                                     (cx1+0.10, jog_y+0.175),
                                     layer=70, datatype=20))
            v2_cx_climb = (cx0 + cx1) / 2
            top.add(gdstk.rectangle((v2_cx_climb-0.10, jog_y-0.10),
                                     (v2_cx_climb+0.10, jog_y+0.10),
                                     layer=69, datatype=44))

        top.add(gdstk.rectangle((cx0, jog_y-0.20), (cx1, y_H+0.40),
                                 layer=69, datatype=20))

    # Common top-corridor: via2, M3 H, M3 V, M4 ext (merged with pad), via3
    v2_cx_top = (cx0 + cx1) / 2
    # via2 centered in M3 H (height 0.35), via2 0.20 -> 0.075 enclosure each side
    top.add(gdstk.rectangle((v2_cx_top-0.10, y_H+0.075),
                             (v2_cx_top+0.10, y_H+0.275),
                             layer=69, datatype=44))
    # M3 H height M3_H_HEIGHT
    top.add(gdstk.rectangle((ui_x-0.20, y_H),
                             (cx1+0.05, y_H+M3_H_HEIGHT),
                             layer=70, datatype=20))
    # M3 V from y_H to CHIP_TOP_M3 (which is now 225.55)
    top.add(gdstk.rectangle((ui_x-0.20, y_H),
                             (ui_x+0.20, CHIP_TOP_M3),
                             layer=70, datatype=20))
    # M4 ext from y_H up to PAD_TOP_Y (merging with pad, W=0.40)
    top.add(gdstk.rectangle((ui_x-0.20, y_H),
                             (ui_x+0.20, PAD_TOP_Y),
                             layer=71, datatype=20))
    # via3 placed inside M3 V (and M4 ext + pad). v3_y centered in M3 V.
    v3_y = (y_H + CHIP_TOP_M3) / 2
    top.add(gdstk.rectangle((ui_x-0.10, v3_y-0.10),
                             (ui_x+0.10, v3_y+0.10),
                             layer=70, datatype=44))


def main():
    lib = gdstk.read_gds(V7)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
    print(f"v7 baseline: {sum(1 for _ in top.polygons)} polys")
    for cx, cy in CV_CELLS:
        add_strap(top, cx, cy)
    print(f"After straps: {sum(1 for _ in top.polygons)} polys")
    for route in ROUTES:
        add_route(top, route)
        idx, cx, cy, ui_x, y_H, cx0, cx1, jog_y, mx0, mx1 = route
        print(f"  ui_in[{idx}] x={ui_x:.2f} -> cv({cx},{cy})  "
              f"y_H={y_H:.2f}  climb_x={cx0:.2f}-{cx1:.2f}  jog_y={jog_y}")
    print(f"After routes: {sum(1 for _ in top.polygons)} polys")
    lib.write_gds(OUT)
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
