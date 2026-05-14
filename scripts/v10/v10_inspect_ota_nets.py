"""Find Mf (NQVC98) instance position and identify nearby V_in_p, VDPWR, Vfo nets.

This guides v10 placement of parallel NQVC98 cells.
"""
import gdstk

GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"


def get_bb(p):
    bb = p.bounding_box()
    return None if bb is None else (bb[0][0], bb[0][1], bb[1][0], bb[1][1])


lib = gdstk.read_gds(GDS)
top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")
mf_template = next(c for c in lib.cells if c.name == "sky130_fd_pr__nfet_01v8_NQVC98")

# Find Mf reference position
mf_origin = None
for r in top.references:
    if r.cell.name == "sky130_fd_pr__nfet_01v8_NQVC98":
        mf_origin = r.origin
        print(f"Mf origin: {r.origin}")
        print(f"Mf bbox: {r.bounding_box()}")
        break

# Look for VDPWR / VPWR labels in v9 GDS
print("\nLabels near Mf:")
for lab in top.labels:
    if abs(lab.origin[0] - mf_origin[0]) < 30 and abs(lab.origin[1] - mf_origin[1]) < 30:
        print(f"  '{lab.text}' at ({lab.origin[0]:.2f}, {lab.origin[1]:.2f}) L{lab.layer}/{lab.texttype}")

# Print all VPWR / VGND labels
print("\nAll VPWR/VGND labels:")
for lab in top.labels:
    if lab.text in ("VPWR", "VDPWR", "VGND"):
        print(f"  '{lab.text}' at ({lab.origin[0]:.2f}, {lab.origin[1]:.2f}) L{lab.layer}/{lab.texttype}")

# M4 power rails (wide vertical M4)
print("\nM4 vertical power rails (W~2µm, H>100µm):")
LAY_M4 = (71, 20)
for p in top.polygons:
    if (p.layer, p.datatype) != LAY_M4: continue
    b = get_bb(p)
    if b is None: continue
    w = b[2]-b[0]; h = b[3]-b[1]
    if 1.5 < w < 3.0 and h > 100:
        print(f"  ({b[0]:.2f}, {b[1]:.2f}) - ({b[2]:.2f}, {b[3]:.2f}) W={w:.2f} H={h:.2f}")

# Mf template cell internals — find gate/drain/source pins
print("\nMf template (NQVC98) structure:")
labs = list(mf_template.labels)
print(f"  Labels: {len(labs)}")
for lab in labs[:5]:
    print(f"    '{lab.text}' at ({lab.origin[0]:.3f}, {lab.origin[1]:.3f}) L{lab.layer}/{lab.texttype}")
bb_m = mf_template.bounding_box()
print(f"  bbox: {bb_m}")
