"""v8 long-haul routing for cv-cell (186.8, 162.05) → ui_in[0].

Path uses the x=187+ corridor (RIGHT of the V1 M2 bus that ends at x=186),
M2 vertical up from escape paddle, via2 to M3 above the cap_mim_MQHU4F
keepout (cap ends at y=219 → M3 OK at y≥220.34), then M3 horizontal
westward to the ui_in[0] x position, M3 vertical up to the pad, via3 to M4.

Obstacles cleared:
- V1 M2 horizontal bus at y=180-181, x=118.14..186.00: my route at x=187+ avoids it
- cap_mim_MQHU4F at y=173..219: my M3 stays at y≥220.4
- M2/M4 power rails at x=165-172: M3 over them is OK (different layer)
- M4 ui_in pads at y=224.76+: via3 lands inside
"""
import gdstk
V8 = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds"

LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)
LAY_V2 = (69, 44); LAY_V3 = (70, 44)

def main():
    lib = gdstk.read_gds(V8)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

    # M2 vertical from escape paddle (existing at y=172.55) up to y=220.95
    m2_vert = gdstk.rectangle(
        (186.85, 172.21), (187.20, 220.95),
        layer=LAY_M2[0], datatype=LAY_M2[1])
    # via2 0.20x0.20 (sky130 via2 min size)
    via2 = gdstk.rectangle(
        (186.925, 220.625), (187.125, 220.825),
        layer=LAY_V2[0], datatype=LAY_V2[1])
    # ONE M3 horizontal spanning ui_in[0] x to escape stub x
    # y=220.50..220.95 (0.45 tall, ≥1.50 from cap_mim y_max=219 → 1.50 ≥ 1.34 ✓)
    UI_X = 138.46
    m3_h = gdstk.rectangle(
        (UI_X - 0.30, 220.50), (187.25, 220.95),
        layer=LAY_M3[0], datatype=LAY_M3[1])
    # M3 vertical from M3 horizontal up to top of chip at ui_in[0] x
    m3_v = gdstk.rectangle(
        (UI_X - 0.30, 220.50), (UI_X + 0.30, 225.55),
        layer=LAY_M3[0], datatype=LAY_M3[1])
    # M4 extension below the ui_in pad (pad is 0.30 wide, too narrow for via3
    # with 0.06 enclosure each side = 0.32 min total). Extension wider so
    # via3 fits cleanly. Merges with existing M4 pad.
    m4_ext = gdstk.rectangle(
        (UI_X - 0.20, 220.55), (UI_X + 0.20, 224.86),
        layer=LAY_M4[0], datatype=LAY_M4[1])
    # via3 inside M4 extension at y=222 (well below the pad, well above the
    # cap_mim_MQHU4F M4 plate at y<=218)
    via3 = gdstk.rectangle(
        (UI_X - 0.10, 222.00), (UI_X + 0.10, 222.20),
        layer=LAY_V3[0], datatype=LAY_V3[1])

    for poly in (m2_vert, via2, m3_h, m3_v, m4_ext, via3):
        top.add(poly)
    print(f"Added route: cv(186.8,162.05) → ui_in[0] via x=187 corridor")
    lib.write_gds(V8)
    print(f"Wrote {V8}")

if __name__ == "__main__":
    main()
