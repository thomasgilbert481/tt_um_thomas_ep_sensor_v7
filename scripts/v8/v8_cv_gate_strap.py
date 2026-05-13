"""v8 step 1: cv-cell gate strap with per-row escape paddle widths.

Right-column cv-cells (x=186.8) get progressively longer escape paddles
so each cell's M2 vertical climb has a unique x channel:
- (186.8, 96):  escape to x=189.50  | M2 v at x=189.20..189.50
- (186.8, 118): escape to x=188.95  | M2 v at x=188.65..188.95
- (186.8, 140): escape to x=188.40  | M2 v at x=188.10..188.40
- (186.8, 162): escape to x=187.85  | M2 v at x=187.55..187.85

Left-column cv-cells (x=175.8) keep the basic short escape (no long-haul yet).
"""
import gdstk

V7 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M1 = (68, 20); LAY_M2 = (69, 20); LAY_V1 = (68, 44)

CV_CELLS = [
    (175.80,  96.05, 1.65),  # (cx, cy, escape_x_extension)
    (186.80,  96.05, 2.75),  # extends to 189.55
    (175.80, 118.05, 1.65),
    (186.80, 118.05, 2.20),  # extends to 189.00
    (175.80, 140.05, 1.65),
    (186.80, 140.05, 1.65),  # extends to 188.45
    (175.80, 162.05, 1.65),
    (186.80, 162.05, 1.10),  # extends to 187.90
]

def main():
    lib = gdstk.read_gds(V7)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
    for (cx, cy, esc_ext) in CV_CELLS:
        top_strap = gdstk.rectangle((cx-0.43, cy+10.16), (cx+0.90, cy+10.50),
                                     layer=LAY_M1[0], datatype=LAY_M1[1])
        bot_strap = gdstk.rectangle((cx-0.91, cy-10.45), (cx+0.42, cy-10.16),
                                     layer=LAY_M1[0], datatype=LAY_M1[1])
        via1_top = gdstk.rectangle((cx-0.100, cy+10.250), (cx+0.050, cy+10.400),
                                    layer=LAY_V1[0], datatype=LAY_V1[1])
        via1_bot = gdstk.rectangle((cx-0.100, cy-10.380), (cx+0.050, cy-10.230),
                                    layer=LAY_V1[0], datatype=LAY_V1[1])
        m2_bridge = gdstk.rectangle((cx-0.20, cy-10.45), (cx+0.15, cy+10.50),
                                     layer=LAY_M2[0], datatype=LAY_M2[1])
        m2_escape = gdstk.rectangle((cx-0.20, cy+10.16), (cx+esc_ext, cy+10.50),
                                     layer=LAY_M2[0], datatype=LAY_M2[1])
        for poly in (top_strap, bot_strap, via1_top, via1_bot, m2_bridge, m2_escape):
            top.add(poly)
    OUT = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"
    lib.write_gds(OUT)
    print(f"Wrote v8draft with per-row escape paddles to {OUT}")

if __name__ == "__main__":
    main()
