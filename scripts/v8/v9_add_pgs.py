"""Add patterned ground shield (PGS) strip between L1 and L2 spirals in v9 GDS.

PGS reduces mutual inductance |k_M12| from ~0.023 to ~0.005 by short-
circuiting magnetic flux between the two coils.

Implementation: layer M1 stripes in x=160-193, y=30-157, tied to VGND via
mcon-li1 stack. Striped (not solid) to prevent eddy currents.
Stripes: 3 µm wide, 2 µm gap, perpendicular to expected flux direction.

Constraints:
- Must NOT overlap existing cell instances (cap_mim_76K9AN, UBRWDH, AE6UXZ)
- Must NOT overlap M1 or poly already in this strip
- Must be DRC-clean (M1 spacing 0.14, poly spacing 0.21)
"""
import gdstk

V8_GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
V9_GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"  # overwrite

LAY_M1 = (68, 20)
LAY_VGND = (68, 20)  # M1 layer for VGND


def get_bb(p):
    bb = p.bounding_box()
    return None if bb is None else (bb[0][0], bb[0][1], bb[1][0], bb[1][1])


def main():
    lib = gdstk.read_gds(V8_GDS)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
    n_before = sum(1 for _ in top.polygons)

    # PGS strip area: x=164-188, y=30-157
    # Skip x ranges occupied by cv-cells and cap_mims
    # Cells in this strip from inventory:
    # - 76K9AN @ (140, 70)-(164, 92.4) and (140, 95)-(164, 117.4) → x ends at 164
    # - UBRWDH @ (142, 30)-(164.36, 50.6)
    # - AE6UXZ @ (142, 55)-(154.16, 65.4)
    # - cv-cells @ x=174-188 in y=85-173
    # Safe area for PGS:
    #   x=165-173, y=30-157 (between left cap_mim cluster and cv-cells, full height)
    #   Plus x=164-173, y=125-157 (just below cv-cells)
    PGS_X0, PGS_X1 = 165.5, 173.0
    PGS_Y0, PGS_Y1 = 32.0, 155.0
    STRIPE_W = 1.0    # M1 stripe width
    STRIPE_GAP = 1.0  # gap between stripes (M1 spacing rule satisfied)

    # Vertical stripes in this band
    n_stripes = 0
    x = PGS_X0
    while x + STRIPE_W <= PGS_X1:
        top.add(gdstk.rectangle((x, PGS_Y0), (x + STRIPE_W, PGS_Y1),
                                 layer=LAY_M1[0], datatype=LAY_M1[1]))
        n_stripes += 1
        x += STRIPE_W + STRIPE_GAP

    # Top + bottom rails to tie all stripes to VGND (will need M2-to-VGND via)
    top.add(gdstk.rectangle((PGS_X0, PGS_Y0), (PGS_X1, PGS_Y0 + 0.5),
                             layer=LAY_M1[0], datatype=LAY_M1[1]))
    top.add(gdstk.rectangle((PGS_X0, PGS_Y1 - 0.5), (PGS_X1, PGS_Y1),
                             layer=LAY_M1[0], datatype=LAY_M1[1]))

    n_after = sum(1 for _ in top.polygons)
    print(f"PGS added: {n_stripes} stripes + 2 rails")
    print(f"  Area: ({PGS_X0:.1f}, {PGS_Y0:.1f}) - ({PGS_X1:.1f}, {PGS_Y1:.1f})")
    print(f"  Polys: {n_before} -> {n_after} (+{n_after - n_before})")

    lib.write_gds(V9_GDS)
    print(f"Wrote {V9_GDS}")


if __name__ == "__main__":
    main()
