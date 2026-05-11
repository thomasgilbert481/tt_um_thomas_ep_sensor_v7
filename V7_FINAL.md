# v7 FINAL — aggressive in-place thicken (DRC-clean, all GHA passing)

## What we delivered

**v7 chip**: v2 baseline + PGS strip + 2-stage cap_mim-aware aggressive thicken.

### Geometry
- Base pass: DELTA=0.8 (w=10→11.6 µm)
- Secondary pass: D=10 with full cap_mim keepout (CK=1.4 µm) and footprint clamp
- Result: 70 of 92 spiral strips widened to mean **26.3 µm** (range 10.0-31.6)
- 22 strips left at 11.6 µm (those that abutted cap_mim keepout zones)

### Estimated electrical
| Metric | v2 baseline | v4 (D=0.6) | v6 (D=0.7) | **v7 (D=0.8 + D=10)** |
|---|---|---|---|---|
| Mean strip w | 10 µm | 11.2 µm | 11.4 µm | **26.3 µm** |
| Rs | 5.6 Ω | 5.0 Ω | 4.9 Ω | **~2.8 Ω** |
| Q at f₀=3 GHz | 4.6 | 5.0 | 5.5 | **~9** |
| cv-bits resolved (predicted) | b5 (1) | b4-b6 (3) | b4-b6 (3) | **b3-b6 (4)** |
| ε_min | 0.157 | 0.088 | 0.080 | **0.044** |

### Predicted Zhao fit
Same fit shape as v4/v6 but with higher κ_eff (less Q broadening):
- Hyperbolic R² ≥ 0.99
- Power-law slope on Zhao window: ~0.38-0.42 (improved from v4's 0.36)
- Δf at b3 (ε=0.044) now resolvable: predicted ~600 MHz

## TT precheck results (GHA verified)

| Run | gds | precheck | viewer |
|---|---|---|---|
| v7 D=0.7 | ✓ | ✓ | ✓ |
| v7 D=0.8 | ✓ | ✓ | ✓ |
| v7 D=3.0 (asymmetric L1) | ✓ | ✓ | ✓ |
| v7 D=5.0 (both spirals) | ✓ | ✓ | ✓ |
| **v7 D=10 (FINAL)** | ✓ | ✓ | ✓ |

All 15 TT precheck checks pass.

## How to reproduce

```bash
# Start from v2 baseline GDS
cp tt_um_thomas_ep_sensor_v2/gds/tt_um_thomas_ep_sensor.gds \
   tt_um_thomas_ep_sensor_v7/gds/
# Step 1: strip PGS
python3 v4_change1_strip_pgs.py
# Step 2: DELTA=0.8 baseline thicken with cap_mim keepout
python3 v4_change2_inplace_thicken.py   # with DELTA=0.8
# Step 3: secondary aggressive thicken D=10 with all-cap_mim keepout
# (see v7_aggressive_inplace.py)
```

## Submission recommendation

**Submit v7 to ttsky shuttle.** Strictly better than v6 (which is strictly better
than v4), with TT precheck verified passing. Same v2-derived topology (no
new routing risk, no LVS concerns from re-floorplan).

The v6/v4 repos remain as fallback options if any v7-specific issue arises
in fab review.

## What v7 didn't deliver (and why)

- **3-turn aggressive spiral**: tried; gdstk-generated geometry has sub-grid
  fragment issues at spiral corners. Needs interactive Magic tools.
- **Figure-8 L2**: requires L2 cluster relocation (6 cells); programmatic
  relocation breaks routing (~4220 DRC violations). Needs LVS-aware router.
- **NMOS source follower OTA replacement**: deferred; v5 SF analysis showed
  the actual silicon may already be NMOS-only (no PMOS in GDS).
  Schematic-level redesign without GDS change has marginal value.

These remain on the roadmap for a real 2-3 week analog re-floorplan (v8?).
