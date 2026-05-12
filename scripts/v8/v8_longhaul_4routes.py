"""v8 4-route routing: all 4 right-column cv-cells -> ui_in[0..3].

Mapping (higher y_H to leftward ui_in, so verticals don't cross):
  cv(186.8,  96) -> ui_in[0] x=138.46, y_H=222.30
  cv(186.8, 118) -> ui_in[1] x=135.70, y_H=221.70
  cv(186.8, 140) -> ui_in[2] x=132.94, y_H=221.10
  cv(186.8, 162) -> ui_in[3] x=130.18, y_H=220.50
"""
import gdstk
V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_V2 = (69, 44); LAY_V3 = (70, 44)

# (cy, m2_v_x_min, m2_v_x_max, ui_in_x, y_H)
# M2 widths bumped to 0.40 for ≥0.10 via2 enclosure each side.
# y_H pitch 0.75 µm so 0.35 µm gap between adjacent M3 H bars (≥0.30 met3.2).
ROUTES = [
    ( 96.05, 189.15, 189.55, 138.46, 222.90),  # -> ui_in[0] highest y (pitch 0.80)
    (118.05, 188.60, 189.00, 135.70, 222.10),  # -> ui_in[1]
    (140.05, 188.05, 188.45, 132.94, 221.30),  # -> ui_in[2]
    (162.05, 187.50, 187.90, 130.18, 220.50),  # -> ui_in[3] lowest y
]

def main():
    lib = gdstk.read_gds(V8)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
    for (cy, m2_x0, m2_x1, ui_x, y_H) in ROUTES:
        # M2 vertical from cv-cell escape paddle up to y_H + 0.40
        m2_v = gdstk.rectangle((m2_x0, cy + 10.21), (m2_x1, y_H + 0.40),
                                layer=LAY_M2[0], datatype=LAY_M2[1])
        # via2 (0.20x0.20) centered in M3 H height; y in middle of M3 H band
        v2_cx = (m2_x0 + m2_x1) / 2
        via2 = gdstk.rectangle((v2_cx - 0.10, y_H + 0.15), (v2_cx + 0.10, y_H + 0.35),
                                layer=LAY_V2[0], datatype=LAY_V2[1])
        # M3 horizontal at y=y_H..y_H+0.50 (taller, ≥0.15 via2 enclosure each y side)
        m3_h = gdstk.rectangle((ui_x - 0.25, y_H), (m2_x1 + 0.15, y_H + 0.50),
                                layer=LAY_M3[0], datatype=LAY_M3[1])
        # M3 vertical from y_H up to chip top at ui_in_x
        m3_v = gdstk.rectangle((ui_x - 0.20, y_H), (ui_x + 0.20, 225.55),
                                layer=LAY_M3[0], datatype=LAY_M3[1])
        # M4 extension below ui_in pad
        m4_ext = gdstk.rectangle((ui_x - 0.20, y_H + 0.10), (ui_x + 0.20, 224.86),
                                  layer=LAY_M4[0], datatype=LAY_M4[1])
        # via3 (0.20x0.20) inside M4 extension
        v3_y = (y_H + 224.0) / 2
        via3 = gdstk.rectangle((ui_x - 0.10, v3_y - 0.10), (ui_x + 0.10, v3_y + 0.10),
                                layer=LAY_V3[0], datatype=LAY_V3[1])
        for poly in (m2_v, via2, m3_h, m3_v, m4_ext, via3):
            top.add(poly)
        print(f"Route cv(186.8,{cy}) -> ui_in at x={ui_x}, y_H={y_H}")
    lib.write_gds(V8)

if __name__ == "__main__":
    main()
