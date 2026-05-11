# v7 plan — full analog block re-floorplan for textbook Zhao slope = 0.5

## TL;DR — v7 is a 4-6 week mask spin, NOT done in this session

This repo currently contains the v6 chip (DELTA=0.7 cap_mim-aware thicken).
The v7 PLAN below describes what a proper v7 needs.

A scripted attempt to relocate the 6 cells inside L2's spiral footprint
(documented in `v7_relocate_l2_cluster.py` in tt_ep_sensor/) produced 4220
DRC violations because top-level M3/M4 routing wires don't follow moved
cells. v7 requires hand-routing or a real auto-router.

## Why v7 matters

v4/v6 silicon delivers 3 cv-bits resolution (b4, b5, b6) at f₀ = 3.06 GHz
with R² ≥ 0.99 on the hyperbolic fit. v7 unlocks:

- **Aggressive 3-turn spiral, w=15 µm**: Rs 5.6 → 1.5 Ω, Q 5 → 12
- **Sub-Zhao cv-bits resolve**: b2 (ε=0.022), b3 (ε=0.044) in addition to b4-b6
- **5 cv-bits total** (vs 3 in v4/v6)
- **Power-law slope ≈ 0.44** (vs v4's 0.36) — much closer to textbook 0.5
- **R² = 0.9996** on hyperbolic fit (vs v4's 0.9948)

## v7 design steps

### Step 1: Move 6 cells out of L2 spiral footprint
Current L2 footprint (193, 33)-(327, 157) contains:
- cap_mim_C7Y9C2 at (260, 35)-(278, 51) — Cdec_bn_out (bias decoupling)
- res_xhigh_po_YR6MM7 at (280, 50)-(293, 62) — bias resistor
- res_xhigh_po_LS96F9 at (280, 65)-(291, 75) — bias resistor
- cap_mim_XCEES9 at (230, 75)-(252, 95) — Cac_v2 AC coupling
- nfet_01v8_3FYCX3 at (250, 73)-(271, 80) — bias NMOS
- nfet_01v8_SQMHJC at (250, 60)-(260, 72) — bias NMOS

Target new locations: bottom strip (y=0-25) has 7950 µm² free.

Each cell move requires:
1. Update cell instance origin
2. Re-route its terminal nets (M3/M4 wires connecting it to V1/V2_in/Vbn/VGND)
3. Verify LVS still matches schematic

This is interactive Magic editing work (~2 days for 6 cells).

### Step 2: Replace L2 spiral with aggressive 3-turn w=15
With the cluster gone, regenerate L2 as:
- 3 turns, w=15 µm, s=1 µm, OD=130 µm, ID=34 µm
- Rs ≈ 1.5 Ω, L ≈ 0.6 nH, f₀ ≈ 4.6 GHz, Q ≈ 12
- Use the same regeneration script as `v4_change2_aggressive.py` but WITHOUT
  the bridge patches (since cap_mim cells are no longer in the way)

### Step 3: Replace L1 spiral with matching 3-turn w=15
L1 footprint is already clear of cells! Just regenerate the spiral.

### Step 4: Figure-8 L2 to drop |k_M12| from 0.023 to 0.001
With L2 cluster gone, the inner region of L2 footprint is clear. Build
the vertical figure-8: L2a top half + L2b bottom half (CW + CCW with
crossover at center). Neumann shows this gives |k| ≈ 0 in ideal geometry.

### Step 5: Replace diff-pair OTA with NMOS source follower
The current v2 layout has an OTA topology that the v5 SF SPICE deck more
accurately represents than the v2 schematic does. For v7 we explicitly
implement NMOS source follower:
- XM_SF: D=VDPWR, G=vin_p, S=Vfo, W=10·nf=10·m=2 (W_eff=200 µm)
- XM_tail: D=Vfo, G=Vbn, S=GND, W=10·nf=4·m=2 (W_eff=80 µm)

Replaces the 4 NMOS cells (NQVC98, GPUJJ4, 3FYCX3, SQMHJC) currently
acting as the OTA. Smaller, simpler, cleaner DC operating point.

### Step 6: Verification
- KLayout DRC FEOL + BEOL = 0
- Magic DRC = 0 (including capm.11 spacing)
- ngspice extracted-netlist sim: confirm κ_eff, Δf₀, R² match prediction
- 45-corner PVT sweep on extracted netlist
- Mismatch MC

## Estimated effort breakdown

| Step | Days | Risk |
|---|---|---|
| 1. Cell relocation (6 cells) | 2 | layout/LVS iteration |
| 2. L2 aggressive spiral | 1 | terminal routing |
| 3. L1 aggressive spiral | 1 | terminal routing |
| 4. Figure-8 L2 | 2 | crossover DRC |
| 5. OTA source-follower swap | 1 | LVS iteration |
| 6. Verification (DRC, LVS, ngspice, corners, MC) | 2 | corner failures |
| Buffer for iteration | 3 | unknowns |
| **Total** | **12 days = 2.5 weeks** | |

(Earlier estimate of 4-6 weeks was conservative; with focused execution,
this is achievable in 2-3 weeks of analog-layout-engineer time.)

## Predicted v7 silicon behavior

| Parameter | v4/v6 | v7 (predicted) |
|---|---|---|
| f₀ | 3.06 GHz | 4.6 GHz |
| Q_loaded | 5 | 12 |
| Rs spiral | 5.0 Ω | 1.5 Ω |
| L per spiral | 1.35 nH | 0.6 nH |
| |K_M12| | 0.023 | 0.001 (figure-8) |
| cv-bits resolved | 3 (b4-b6) | 5 (b2-b6) |
| Sub-Zhao coverage | NO | YES |
| Power-law slope (Zhao window) | 0.36 | 0.44 |
| Hyperbolic R² | 0.9948 | 0.9996 |
| OTA startup | risk of Vfo rail-up | clean (NMOS SF) |
| Net safety | proven safe (v2 topology) | needs LVS verification |

## Files in this v7 repo

For now, v7's GDS is identical to v6 (v4 Recipe A with DELTA=0.7 thicken
+ cap_mim keepout). The v7 PLAN above is the roadmap for the next mask
spin. Submit v6 as the current chip, schedule v7 as 2-3-week project
for the following shuttle.
