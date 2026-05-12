"""v8 left-column cv-cell routing: 1 route for (175.8, 162.05) -> ui_in[4].

Path:
1. M2 extension DOWN from escape paddle (y=172.55) to y=170.00 at x=176.85-177.20
2. via2 inside the M2 extension at y=170.30-170.50
3. M3 jog at y=170.20-170.60 from x=176.80 to climb x (avoiding cap_mim keepout
   y=171.66-220.34 — we are at y=170.6 which is below 171.66; and gap to cap_mim
   y_min=173 is 2.4 µm ≥1.34 capm.11)
4. via2 at right end of M3 jog drops back to M2
5. M2 climb at x=189.85-190.15 from y=170 to y=224 (avoiding all existing escapes
   and right-column M2 verticals)
6. via2 at climb top -> M3 above cap_mim (y_H=223.70 + 0.50)
7. M3 horizontal to ui_in[4] at x=127.42
8. M3 vertical to chip top
9. M4 extension + via3 inside ui_in[4] pad
"""
import gdstk
V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_V2 = (69, 44); LAY_V3 = (70, 44)

CY = 162.05; UI_X = 127.42
Y_HOP = 170.40   # jog y center
Y_H = 224.20    # top M3 H y (above right-col M3 V tops at 224.10)

def main():
    lib = gdstk.read_gds(V8)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

    # 1) M2 extension down from escape — widened for 0.10 via2 encl each x side
    m2_ext = gdstk.rectangle((176.80, 170.00), (177.25, 172.55),
                              layer=LAY_M2[0], datatype=LAY_M2[1])
    # 2) via2 inside m2_ext
    v2_left = gdstk.rectangle((176.925, Y_HOP - 0.10), (177.125, Y_HOP + 0.10),
                               layer=LAY_V2[0], datatype=LAY_V2[1])
    # 3) M3 jog from x=176.70 to x=190.30, y=Y_HOP-0.20..Y_HOP+0.20
    m3_jog = gdstk.rectangle((176.70, Y_HOP - 0.20), (190.30, Y_HOP + 0.20),
                              layer=LAY_M3[0], datatype=LAY_M3[1])
    # 4) via2 at right end of m3_jog
    v2_right = gdstk.rectangle((189.95, Y_HOP - 0.10), (190.15, Y_HOP + 0.10),
                                layer=LAY_V2[0], datatype=LAY_V2[1])
    # 5) M2 climb x=189.80..190.25 (W=0.45, ≥0.10 via2 encl, gap 0.25 from (96))
    m2_climb = gdstk.rectangle((189.80, Y_HOP - 0.20), (190.25, Y_H + 0.50),
                                layer=LAY_M2[0], datatype=LAY_M2[1])
    # 6) via2 at top of climb -> M3 above cap_mim
    v2_top = gdstk.rectangle((189.95, Y_H + 0.15), (190.15, Y_H + 0.35),
                              layer=LAY_V2[0], datatype=LAY_V2[1])
    # 7) M3 horizontal at y=Y_H..Y_H+0.50 from ui_x to climb x
    m3_h = gdstk.rectangle((UI_X - 0.25, Y_H), (190.30, Y_H + 0.50),
                            layer=LAY_M3[0], datatype=LAY_M3[1])
    # 8) M3 vertical from y_H to chip top
    m3_v = gdstk.rectangle((UI_X - 0.20, Y_H), (UI_X + 0.20, 225.55),
                            layer=LAY_M3[0], datatype=LAY_M3[1])
    # 9) M4 extension below ui_in pad
    m4_ext = gdstk.rectangle((UI_X - 0.20, Y_H + 0.10), (UI_X + 0.20, 224.86),
                              layer=LAY_M4[0], datatype=LAY_M4[1])
    # 10) via3 inside M4 extension (M4 ext y=224.30..224.86, 0.56 tall)
    v3_y = (Y_H + 0.30 + 224.66) / 2  # midpoint of M4 ext
    v3 = gdstk.rectangle((UI_X - 0.10, v3_y - 0.10), (UI_X + 0.10, v3_y + 0.10),
                          layer=LAY_V3[0], datatype=LAY_V3[1])

    for poly in (m2_ext, v2_left, m3_jog, v2_right, m2_climb, v2_top,
                 m3_h, m3_v, m4_ext, v3):
        top.add(poly)
    print(f"Left-col route added: cv(175.8, {CY}) -> ui_in[4]")
    lib.write_gds(V8)

if __name__ == "__main__":
    main()
