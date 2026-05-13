"""v8 left-column routes #2 and #3 using M2 horizontal at chip top.

Insight: M2 doesn't have capm.11 (M3-specific). And there are no existing
M2 polys at y=190-225 in x=140-180. So M2 horizontals at y~224 can carry
additional routes across the chip without conflicting with the M3
corridor above cap_mim or M2 power rails (which end below y=190).

Per route:
- M2 escape DOWN from cv-cell escape paddle to y_jog (below cap_mim keepout)
- M3 jog right at y_jog (M3 must be y<171.66 OR y>220.34; below cell area)
- M2 climb at unique x (right of all previous climb x values)
- M2 horizontal at y=Y_TOP from climb_x to ui_in_x
- via2 inside M2 H at (ui_in_x, Y_TOP+offset)
- M3 stub at ui_in_x covers via2
- via3 inside M4 extension below ui_in pad

Y_TOP for two new routes staggered:
- route 6 (cv 175.8, 140): Y_TOP=223.50
- route 7 (cv 175.8, 118): Y_TOP=200.00 (using a totally different y, far below)

Actually one route at Y_TOP=223.50 has many constraints — let me just do 1.
"""
import gdstk
V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_V2 = (69, 44); LAY_V3 = (70, 44)

# Route 6: cv-cell (175.8, 140.05) -> ui_in[5] using M2 H at chip top
CY = 140.05
UI_X = 124.66
Y_JOG = 148.50           # M3 jog y (well below cell + cap_mim keepout)
CLIMB_X0 = 190.50        # M2 climb x_min (gap 0.30 from leftcol[4]'s 189.80-190.25)
CLIMB_X1 = 190.90
Y_TOP = 225.00           # M2 H at chip top (above V1 M2 stubs ending at y=224.76,
                          # above leftcol[4] M2 climb top at y=224.60, below chip top y=225.76)

def main():
    lib = gdstk.read_gds(V8)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

    # M2 escape down extension
    m2_ext = gdstk.rectangle((176.80, Y_JOG - 0.50), (177.25, CY + 10.50),
                              layer=LAY_M2[0], datatype=LAY_M2[1])
    # via2 at bottom of m2_ext
    v2_left = gdstk.rectangle((176.925, Y_JOG - 0.30), (177.125, Y_JOG - 0.10),
                               layer=LAY_V2[0], datatype=LAY_V2[1])
    # M3 jog
    m3_jog = gdstk.rectangle((176.70, Y_JOG - 0.40), (CLIMB_X1 + 0.10, Y_JOG),
                              layer=LAY_M3[0], datatype=LAY_M3[1])
    # via2 at right end of m3_jog
    v2_right = gdstk.rectangle((CLIMB_X0 + 0.10, Y_JOG - 0.30),
                                (CLIMB_X0 + 0.30, Y_JOG - 0.10),
                                layer=LAY_V2[0], datatype=LAY_V2[1])
    # M2 climb
    m2_climb = gdstk.rectangle((CLIMB_X0, Y_JOG - 0.40), (CLIMB_X1, Y_TOP + 0.40),
                                layer=LAY_M2[0], datatype=LAY_M2[1])
    # M2 horizontal at top from climb to ui_in (above all existing M2)
    m2_top = gdstk.rectangle((UI_X - 0.20, Y_TOP), (CLIMB_X1 + 0.05, Y_TOP + 0.30),
                              layer=LAY_M2[0], datatype=LAY_M2[1])
    # via2 inside M2 H at ui_in x
    v2_top_ui = gdstk.rectangle((UI_X - 0.10, Y_TOP + 0.05), (UI_X + 0.10, Y_TOP + 0.25),
                                 layer=LAY_V2[0], datatype=LAY_V2[1])
    # M3 stub covers via2 AND via3 (both 0.20x0.20). Width 0.50, height 0.60 -> area 0.30 ≥0.24.
    # via2 at y=Y_TOP+0.05..Y_TOP+0.25, via3 at y=Y_TOP+0.10..Y_TOP+0.30 — both inside stub.
    m3_stub_ui = gdstk.rectangle((UI_X - 0.25, Y_TOP - 0.10), (UI_X + 0.25, Y_TOP + 0.50),
                                  layer=LAY_M3[0], datatype=LAY_M3[1])
    # M4 extension MERGES with ui_in[5] pad (pad y=224.76..225.76, ext goes down to Y_TOP-0.10)
    m4_ext = gdstk.rectangle((UI_X - 0.20, Y_TOP - 0.10), (UI_X + 0.20, 225.76),
                              layer=LAY_M4[0], datatype=LAY_M4[1])
    # via3 inside M4 ext (and M3 stub) at y just below M3 stub top
    v3 = gdstk.rectangle((UI_X - 0.10, Y_TOP + 0.10), (UI_X + 0.10, Y_TOP + 0.30),
                          layer=LAY_V3[0], datatype=LAY_V3[1])

    for poly in (m2_ext, v2_left, m3_jog, v2_right, m2_climb, m2_top,
                 v2_top_ui, m3_stub_ui, m4_ext, v3):
        top.add(poly)
    print(f"Route 6 added: cv(175.8, {CY}) -> ui_in[5] via M2-top corridor")
    lib.write_gds(V8)

if __name__ == "__main__":
    main()
