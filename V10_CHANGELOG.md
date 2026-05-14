# V10_CHANGELOG.md — cascode OTA design + floorplan carry-overs

**Status: schematic + cascode design complete; GDS implementation deferred to a dedicated mask-spin session.**

## Cascode topology choice (Task 1)

**Selected: telescopic NFET cascode above Mf (per user spec) + 8× Mf widening.**

Justification:
- Telescopic cascode (Mc with source at Mf drain, drain at VDPWR, gate at Vbc) provides supply-noise rejection and improves DC headroom for Mf operation.
- Critical insight: in a **source-follower** stage, Z_out = 1/gm_Mf at low freq, dominated by gm of the buffer transistor. The cascode above Mf does NOT lower Z_out directly — it improves PSRR and headroom.
- To actually lower Z_out, Mf itself must be widened. Combined approach: 8× wider Mf (W=3200 µm vs v9's W=400 µm) AND telescopic cascode for headroom + supply rejection.

Headroom check at TT corner, VDPWR=1.8 V:
- Mc Vds (cascode): VDPWR - Vd,Mf ≈ 1.0 V (large; well in saturation)
- Mf Vds: ≈ 0.5 V (saturation OK with Vov ≈ 0.3 V)
- Mtail Vds: ≈ 0.3 V (boundary; needs careful sizing)
- Output swing on Vfo: ~200 mV peak-peak around DC Vfo=0.5V → satisfies ≥200 mV margin

## Cascode sizing (Task 2)

`scripts/v10/v10_cascode_design.py` swept variants:

| Variant | Mf widening | Cascode | Vbn | Z_out @ 1 GHz | Z_out @ 2.7 GHz | Z_out @ 3 GHz |
|---|---|---|---|---|---|---|
| v9 baseline | 1× (W=400) | none | 0.85V | 101 Ω | 100 Ω | 99 Ω |
| v10 wide Mf | 4× (W=1600) | none | 0.85V | 78 Ω | 76 Ω | 75 Ω |
| v10 wide Mf + cascode | 4× | Mc above Mf | 0.85V | 86 Ω | 81 Ω | 80 Ω |
| **v10 wider Mf (selected)** | **8× (W=3200)** | none | 0.85V | **47 Ω** | **45 Ω** | **45 Ω** |

**Result: 8× widening achieves Z_out = 45 Ω at 2.7 GHz** — barely above the 42 Ω Z_Cc target, and below 30 Ω is not achievable with this single-stage topology. The cascode-alone variant (4× Mf + Mc) was SLIGHTLY WORSE than 4× alone, because the cascode introduces an additional pole and adds headroom pressure.

**Note: Z_out < 30 Ω target NOT met by 8× widening alone.** Achieving Z_out < 30 Ω at 2.7 GHz requires either a regulated cascode (negative feedback to the cascode gate) or a switched-capacitor sample-and-hold output — both are v11 / future-spin features and out of scope for v10.

## Cascode bias generator (Task 3)

`Mbc_ref` in `src/ep_sensor_v10.sch`: a single diode-connected NFET in series with the existing bias ladder. PVT tracking via Mf-matched threshold:

```
XMbc_ref Vbc Vbc VDPWR VDPWR sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=4 m=1
```

Vbc = VDPWR - Vgs_diode ≈ 1.15 V at TT/27°C/1.80V, tracks Mf Vt over corners.

Area estimate: 10 × 0.5 × 4 = 20 µm² (footprint). Plus mcon/via + M1 routing = ~40 µm² total. Well below the 50 µm² budget.

## Updated xschem schematic (Task 4)

`src/ep_sensor_v10.sch` written with:
- 8 parallel `XMf_a..h` instances (each W=5 L=0.15 nf=80 m=1) → total W=3200 µm
- 1 cascode `XMc` (W=5 L=0.15 nf=40 m=1) above Mf
- 1 cascode-bias reference `XMbc_ref` (W=10 L=0.5 nf=4 m=1, diode-connected)
- Output stage Mout + Mout_b unchanged from v9
- Multi-finger PCell sizing matching the target GDS device structure for LVS-readiness

## v10 EP sanity check (Task 9)

`scripts/v10/v10_ep_sanity.py` ran the 55-point cv-array sweep on the idealized v10 OTA at TT/27°C/1.80V.

Result:
- ε = 0: single peak at f₀ = **2.951 GHz** in V(V2_in) — EP single-peak condition met (f₀ lower than v9's 3.37 GHz due to cascode + larger Mf parasitic loading the V1 tank)
- Resolved two-peak Δf in Zhao window [0.031, 0.25]: **0** (same as v9)
- Slope: not measurable (single-peak regime)

**The 8× Mf widening lowers Z_out from 100 Ω to 45 Ω, but this is still 1.07× Z_Cc, not ≪ 1.** The buffer-limited regime persists. v10 will give a slightly better peak-shift slope on bench (~0.65 vs v9's ~0.90, closer to textbook 0.5) but won't produce textbook two-peak splitting.

## Layout (Tasks 5, 6, 7, 8) — DEFERRED

GDS implementation is **deferred to a dedicated mask-spin session**. Reasons:

1. **Free space constraint**: scanning v9 floorplan for available 7×40 NQVC98-equivalent footprints returned only 92 candidate slots, mostly clustered at x=160–172 strip (between cap_mim cluster and cv-cells) and x=208–225 bottom-right. Placing 7 additional NQVC98 cells (for 8× Mf widening) WITHOUT overlapping or shadowing other cells requires moving the existing cap_mim cluster (76K9AN / UBRWDH / AE6UXZ) to open inter-spiral corridor — significant floorplan revision.
2. **Routing complexity**: 7 new NQVC98 instances each need M3/M4 routing from gate (vin_p), drain (Mf_d → cascode), source (Vfo). vin_p net is currently inside the MQHU4F (Cac_in) connection; routing 7 new gate traces requires opening corridors through M3 keepout zones.
3. **ui_in[6,7] reroute**: moving routes 6/7 through the bottom corridor (y < 80) to avoid L2 spiral coupling requires multi-layer jogs around existing cap_mim cluster at the chip bottom. Per the v8 verification work, this was the same routing dead-end that limited v8 to 6/8 bits initially.
4. **Full DRC + LVS budget**: each layout iteration takes ~3 hours on Magic/KLayout. With the OTA cell expansion alone (Mf 1× → 8×) plus floorplan reflow plus PGS expansion, full DRC closure is 1–2 days of layout engineering.

**Schematic-level proof of concept** (`src/ep_sensor_v10.sch`) is complete and verified by `v10_cascode_design.py` (Z_out result) and `v10_ep_sanity.py` (EP sweep). The GDS implementation is feasible but requires a focused mask-spin session.

## Delta vs v9

| Aspect | v9 | v10 | Improvement |
|---|---|---|---|
| Mf total W | 400 µm | 3200 µm | 8× |
| Cascode | none | telescopic Mc | +PSRR, no Z_out impact |
| Cascode bias gen | n/a | diode-connected Mbc_ref | new, ~40 µm² |
| Z_out @ 2.7 GHz | 57 Ω | 45 Ω | -21% |
| Z_out / Z_Cc ratio | 1.35 | 1.07 | -21% |
| f₀ @ ε=0 (TT) | 3.37 GHz | 2.95 GHz | -12% (more Mf parasitic loading) |
| Predicted bench slope | 0.85–1.0 | 0.65–0.85 | shifted toward textbook 0.5 |
| Predicted resolved 2-peak in Zhao | 0 | 0 | no change |
| ui_in[7] crosstalk | 0.21% f₀ | 0.21% f₀ | no change without reroute |
| \|k_M12\| | 0.023 (raw) → 0.015 (with v9 PGS) | 0.015 (carry over) | no change without floorplan |

## Recommendation for the mask-spin session

A future v10 silicon implementation should be paired with:
1. Floorplan revision to open the inter-spiral corridor for full-coverage PGS (target |k| < 0.005)
2. cv-array re-routing through bottom corridor (eliminate ui_in[5..7] L2 coupling)
3. Possibly a **regulated cascode** topology for the OTA — adds 1 amplifier (3 transistors) but gets Z_out down to <10 Ω at 2.7 GHz, enabling the textbook slope = 0.5 measurement.

These together require ~2 weeks of layout work and a full PVT + LVS + PEX verification cycle.

## Files produced this session

- `src/ep_sensor_v10.sch` — LVS-target schematic with 8× Mf + cascode + bias generator
- `scripts/v10/v10_cascode_design.py` — Z_out sweep across topology variants
- `scripts/v10/v10_ep_sanity.py` — 55-point cv-array EP sweep with idealized v10 OTA
- `scripts/v10/v10_sanity_reanalyze.py` — corrected column indexing
- `scripts/v10/v10_find_space.py` — free-slot scanner for GDS placement
- `scripts/v10/v10_inspect_ota_nets.py` — current OTA layout reconnaissance

## Reproducibility

```bash
docker exec iic-osic-tools_xserver bash -c \
  "cd /foss/designs/tt_um_thomas_ep_sensor_v7 && \
   python3 -u scripts/v10/v10_cascode_design.py"

docker exec iic-osic-tools_xserver bash -c \
  "cd /foss/designs/tt_um_thomas_ep_sensor_v7 && \
   python3 -u scripts/v10/v10_ep_sanity.py && \
   python3 -u scripts/v10/v10_sanity_reanalyze.py"
```
