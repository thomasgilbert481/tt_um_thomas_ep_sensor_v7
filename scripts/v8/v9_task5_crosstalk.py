"""Task 5: Crosstalk capacitance from each ui_in[i] route to V1/V2_in/Cc/Vfo nets.

Approximation:
- V1 net is bound to L1 spiral footprint and 8WUMYD CT1 cap
- V2_in net is bound to L2 spiral footprint and UBRWDH CT2 cap
- Vfo (buffer output) is connected to Cc (W8UZ5N)
- Cac_in (V1->OTA) is bounded to MQHU4F

For each ui_in route polygon, compute capacitive coupling to nearby V1/V2/Vfo metal
using a parallel-plate approximation with fringing correction.

Pass criterion: f0 shift from any single ui_in code change must be < LSB-cv-code shift.
LSB shift estimate: with ε_LSB = 0.0054 and 4κω0^2 coupling, f0 shifts ~140 MHz
For our chip C_T1 = 1.85 pF: max allowed crosstalk C = 0.17 pF.
"""
import gdstk
import numpy as np

GDS = "/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds"
LAY_M2 = (69, 20); LAY_M3 = (70, 20); LAY_M4 = (71, 20)

EPS_SIO2 = 4.0 * 8.854e-12  # F/m
M2_M3_SPACE = 0.36e-6  # vertical spacing M2 to M3 (typical sky130)
M3_M4_SPACE = 0.40e-6
M2_M4_SPACE = M2_M3_SPACE + M3_M4_SPACE  # rough
SAME_LAYER_SPACE = 0.30e-6


# Net affinity regions (V1, V2_in, Vfo bounded by these cell instances)
# Each region is "all metal inside this area belongs to this net"
REGIONS = {
    "V1": {
        "boxes": [
            (10, 30, 140, 150),   # L1 spiral
            (241.7, 192, 273.86, 222.4),  # 8WUMYD = CT1
        ]
    },
    "V2_in": {
        "boxes": [
            (190, 30, 330, 160),  # L2 spiral
            (140, 30, 165, 51),   # UBRWDH = CT2
        ]
    },
    "Vfo": {
        "boxes": [
            (306, 192, 334.26, 218.5),  # W8UZ5N = Cc, V_fo side
        ]
    },
}

# ui_in routes (from v8_full_8route.py routing): each is bounded by
# (m2_climb_x, M3_H y_H zone, ui_in pad column at top)
UI_ROUTES = {
    "ui_in[0]": {"climb_x_range": (190.40, 190.80), "ui_x": 138.46, "y_H": 225.05, "cv_x": 186.8, "cv_y": 96.05},
    "ui_in[1]": {"climb_x_range": (189.80, 190.20), "ui_x": 135.70, "y_H": 224.40, "cv_x": 186.8, "cv_y": 118.05},
    "ui_in[2]": {"climb_x_range": (189.20, 189.60), "ui_x": 132.94, "y_H": 223.75, "cv_x": 186.8, "cv_y": 140.05},
    "ui_in[3]": {"climb_x_range": (188.60, 189.00), "ui_x": 130.18, "y_H": 223.10, "cv_x": 186.8, "cv_y": 162.05},
    "ui_in[4]": {"climb_x_range": (191.00, 191.40), "ui_x": 127.42, "y_H": 222.45, "cv_x": 175.8, "cv_y": 162.05},
    "ui_in[5]": {"climb_x_range": (191.55, 191.95), "ui_x": 124.66, "y_H": 221.80, "cv_x": 175.8, "cv_y": 140.05},
    "ui_in[6]": {"climb_x_range": (192.10, 192.50), "ui_x": 121.90, "y_H": 221.15, "cv_x": 175.8, "cv_y": 118.05},
    "ui_in[7]": {"climb_x_range": (192.65, 193.05), "ui_x": 119.14, "y_H": 220.50, "cv_x": 175.8, "cv_y": 96.05},
}


def get_bb(p):
    bb = p.bounding_box()
    return None if bb is None else (bb[0][0], bb[0][1], bb[1][0], bb[1][1])


def overlap_area(a, b):
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return max(0, dx) * max(0, dy)


def edge_distance(a, b):
    """Min distance between rectangles a and b (0 if overlapping)."""
    if overlap_area(a, b) > 0: return 0
    dx = max(0, max(a[0]-b[2], b[0]-a[2]))
    dy = max(0, max(a[1]-b[3], b[1]-a[3]))
    return max(dx, dy)


def assign_net(poly_bb, regions):
    """Determine which net a polygon belongs to based on its bbox center."""
    cx = (poly_bb[0] + poly_bb[2]) / 2
    cy = (poly_bb[1] + poly_bb[3]) / 2
    for net, info in regions.items():
        for box in info["boxes"]:
            if box[0] <= cx <= box[2] and box[1] <= cy <= box[3]:
                return net
    return None


def is_ui_in_route_poly(poly_bb, route):
    """Determine if a polygon is part of a given ui_in route.
    Route includes: M2 climb at climb_x_range, M3 H/V at y near y_H, M4 ext at ui_x."""
    cx = (poly_bb[0] + poly_bb[2]) / 2
    cy = (poly_bb[1] + poly_bb[3]) / 2
    # M2 climb
    cx_range = route["climb_x_range"]
    if cx_range[0] - 0.5 <= cx <= cx_range[1] + 0.5 and cy >= 80:
        return True
    # M3 H at y_H (height 0.35)
    y_H = route["y_H"]
    if y_H - 0.5 <= cy <= y_H + 1.0 and cx >= route["ui_x"] - 0.5 and cx <= cx_range[1] + 0.5:
        return True
    # M3 V at ui_in pad x
    if abs(cx - route["ui_x"]) < 0.5 and cy >= y_H - 0.5:
        return True
    return False


def main():
    lib = gdstk.read_gds(GDS)
    top = next(c for c in lib.cells if c.name == "tt_um_thomas_ep_sensor")

    # Bucket polys by layer
    polys_by_layer = {LAY_M2: [], LAY_M3: [], LAY_M4: []}
    for p in top.polygons:
        k = (p.layer, p.datatype)
        if k not in polys_by_layer: continue
        b = get_bb(p)
        if b: polys_by_layer[k].append(b)

    print("=== Task 5: cv-array routing crosstalk to V1/V2_in/Vfo ===\n")
    results = {}
    for ui_name, route in UI_ROUTES.items():
        all_route_polys = []
        for layer, polys in polys_by_layer.items():
            for pb in polys:
                if is_ui_in_route_poly(pb, route):
                    all_route_polys.append((pb, layer))

        # Compute coupling to each net
        coupling = {"V1": 0.0, "V2_in": 0.0, "Vfo": 0.0}
        for route_bb, route_layer in all_route_polys:
            for net in coupling:
                for net_box in REGIONS[net]["boxes"]:
                    # Find polys in net_box on any metal layer
                    for net_layer, net_polys in polys_by_layer.items():
                        # Compute lateral and vertical distance
                        same_layer = (net_layer == route_layer)
                        for net_pb in net_polys:
                            # Skip if this poly is part of route
                            if route_bb == net_pb: continue
                            # Is the polygon within the net's region?
                            ncx = (net_pb[0] + net_pb[2]) / 2
                            ncy = (net_pb[1] + net_pb[3]) / 2
                            if not (net_box[0] <= ncx <= net_box[2] and net_box[1] <= ncy <= net_box[3]): continue
                            # Compute capacitive coupling
                            if same_layer:
                                # Side-by-side coupling
                                d = edge_distance(route_bb, net_pb) * 1e-6
                                if d < 1e-9: continue
                                if d > 5e-6: continue  # too far, neglect
                                # Approximate overlap perimeter
                                # Use min dim of route × side-by-side distance
                                shared_extent = min(route_bb[3]-route_bb[1], net_pb[3]-net_pb[1])
                                if route_bb[2] < net_pb[0] or net_pb[2] < route_bb[0]:
                                    # horizontal neighbor
                                    shared_extent = min(route_bb[3]-route_bb[1], net_pb[3]-net_pb[1])
                                C = EPS_SIO2 * shared_extent * 1e-6 / d  # F per metre perimeter
                                # Multiply by thickness (~1 µm)
                                C *= 1.0e-6
                                coupling[net] += C
                            else:
                                # Different layers — parallel-plate via vertical spacing
                                # Use overlap area
                                A = overlap_area(route_bb, net_pb) * 1e-12  # m²
                                if A < 1e-15: continue
                                ldiff = abs(route_layer[0] - net_layer[0])
                                if ldiff == 1: d = M3_M4_SPACE if route_layer == LAY_M3 or net_layer == LAY_M3 else M2_M3_SPACE
                                elif ldiff == 2: d = M2_M4_SPACE
                                else: d = 0.5e-6
                                C = EPS_SIO2 * A / d
                                coupling[net] += C

        results[ui_name] = coupling
        print(f"{ui_name}: V1={coupling['V1']*1e15:.2f} fF  V2_in={coupling['V2_in']*1e15:.2f} fF  Vfo={coupling['Vfo']*1e15:.2f} fF")

    # Compute f0 shift
    print("\n=== f₀ shift analysis ===")
    C_T1 = 1.845e-12
    C_T2 = 0.836e-12
    f0 = 3.06e9
    max_v1 = max(r["V1"] for r in results.values())
    max_v2 = max(r["V2_in"] for r in results.values())
    print(f"Max ui_in coupling to V1: {max_v1*1e15:.2f} fF (shift Δf0/f0 = {0.5 * max_v1/C_T1*100:.2f}%)")
    print(f"Max ui_in coupling to V2_in: {max_v2*1e15:.2f} fF (shift Δf0/f0 = {0.5 * max_v2/C_T2*100:.2f}%)")

    # LSB shift: ε_LSB = 0.0054, splitting Δf at LSB
    # Δω(LSB) = 2*sqrt(κ*ε_LSB) * ω0 = 2*sqrt(0.379*0.0054)*ω0 ≈ 0.090*ω0
    # f0 shift from LSB ≈ half this = 0.045 = 4.5%
    LSB_shift_pct = 4.5
    crosstalk_shift_pct_v1 = 0.5 * max_v1/C_T1 * 100
    crosstalk_shift_pct_v2 = 0.5 * max_v2/C_T2 * 100
    max_xt = max(crosstalk_shift_pct_v1, crosstalk_shift_pct_v2)
    print(f"\nLSB-induced f0 shift ≈ {LSB_shift_pct:.2f}%")
    print(f"Max ui_in crosstalk f0 shift = {max_xt:.2f}%")
    if max_xt < LSB_shift_pct:
        print(f"PASS: crosstalk < LSB shift")
    else:
        print(f"FAIL: crosstalk > LSB shift, digital bits leak into analog")


if __name__ == "__main__":
    main()
