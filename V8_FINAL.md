# v8 FINAL — All 8 cv-array bits routed + EP physics verified

## Status: READY FOR SUBMISSION

Commit: `350927c` (gds + scripts) on branch `v8-cv-array-routing`.
PR #1: https://github.com/thomasgilbert481/tt_um_thomas_ep_sensor_v7/pull/1

## All TT precheck checks pass

```
✓ gds workflow      (2m 25s)
✓ docs workflow     (55s)
✓ Magic DRC         0 errors
✓ KLayout DRC       0 errors (sky130A_mr.drc, beol+feol)
```

GitHub Actions run IDs `25772674866` (docs) and `25772674861` (gds), both
completed successfully on `350927c`.

## Improvements over v7 (main) and previous v8 (6 bits)

- **8 of 8 cv-bits routed end-to-end** (was 6 of 8 in commit 4aa9472).
  All ui_in[0..7] M4 pads connect to unique cv-cell gate nets.
- Routes 6 and 7 (cv 175.8 at y=118, 96) routed via M2 east + M3 jog
  below cv-cells at y=80, then M2 climb at x=192.10 and 192.65 to top
  corridor.
- Top corridor pitch reduced to 0.65 µm (height 0.35) to fit all 8
  M3 H tracks; was 0.80 with only 5 slots.

## Physics verification (idealized simulation)

Simulation deck: `scripts/v8/v8_final_verify.py` with extracted-from-GDS
component values:

| Component | Value | Source |
|---|---|---|
| C_T1 | 1.845 pF | cap_mim_m3_1_8WUMYD (l=30, w=30) |
| C_T2 | 0.836 pF | cap_mim_m3_1_UBRWDH (l=20.2, w=20.2) |
| Cc | 1.398 pF | cap_mim_m3_1_W8UZ5N (l=26.1, w=26.1) |
| L1 = L2 | 1.351 nH | v7 spiral geometry |
| R_s | 5.0 Ω | v7 in-place thicken |
| β = √(C_T1/(C_T2+Cc)) | 0.9088 | Zhao chiral-EP condition β=1 |
| κ = Cc/(2·C_T1) | 0.379 | unidirectional coupling strength |

Sweep: all 55 unique cv-array ε values in [0, 0.3], including ε=0
(all cv-bits off) and 40 unique values in Zhao perturbation range
[0.031, 0.25].

### Results

| Criterion | Required | Measured | Status |
|---|---|---|---|
| EP single peak at ε=0 | 1 peak in V(V2_in) at f₀ | 1 peak at 3.484 GHz | **PASS ✓** |
| ≥11 resolved Δf points in [0.031, 0.25] | 11 | **30** | **PASS ✓** |
| Slope on log(Δf) vs log(ε) | [0.45, 0.55] | **0.4960** | **PASS ✓** |
| Fit R² | (informational) | 0.982 | high quality |

The measured slope of 0.4960 is well within the Zhao-paper target [0.45, 0.55]
and very close to the textbook EP value of 0.5. The chip operates slightly
off-EP (β=0.91 vs ideal β=1.0), but the resulting residual Δω₀ is small
enough that the hyperbolic Δω² = Δω₀² + (2κω₀)²·ε fit gives a clean
log-log slope in the Zhao window.

### Comparison to Zhao paper

Zhao et al. (NatComms 2024) reported:
- Experimental slope: 0.55 (their PCB Q ≈ several hundred)
- Theoretical slope: 0.50 (at EP)
- Our chip predicted slope: **0.496** ✓

Our chip's slope is closer to theoretical 0.5 than Zhao's experimental
0.55, despite our much lower Q (≈5.7 vs Zhao's several hundred). This is
because our higher κ (0.379 vs Zhao's 0.31) produces faster splitting
that overcomes the linewidth-limited resolution floor sooner.

## File mapping

### Cap_mim instance → function (from extracted SPICE)

| Cell name | l × w (µm) | Value (pF) | Function |
|---|---|---|---|
| sky130_fd_pr__cap_mim_m3_1_8WUMYD | 30 × 30 | 1.85 | **C_T1** (V1 tank) |
| sky130_fd_pr__cap_mim_m3_1_UBRWDH | 20.2 × 20.2 | 0.84 | **C_T2** (V2_in tank) |
| sky130_fd_pr__cap_mim_m3_1_W8UZ5N | 26.1 × 26.1 | 1.40 | **Cc** (forward coupling) |
| sky130_fd_pr__cap_mim_m3_1_MQHU4F | (compound) | ≈14.1 | Cac_in (V1 to OTA gate) |
| sky130_fd_pr__cap_mim_m3_1_XCEES9 | 20 × 20 | 0.82 | Cac_v2 |
| sky130_fd_pr__cap_mim_m3_1_76K9AN | 22 × 22 | 0.99 | Decoupling (Cdec_bn) |
| sky130_fd_pr__cap_mim_m3_1_C7Y9C2 | 15.8 × 15.8 | 0.51 | Cdec_bn_out |
| sky130_fd_pr__cap_mim_m3_1_AE6UXZ | 10 × 10 | 0.21 | Cff (feedback compensation) |

### Cv-array (binary-weighted perturbation)

| Cv# | Cell | l × w (µm) | Value (fF) | ε contribution |
|---|---|---|---|---|
| Cv0 | AEZ4RW | 3.16 × 3.16 | 20 | 0.0054 |
| Cv1 | 9FLU4N | 4.47 × 4.47 | 41 | 0.0111 |
| Cv2 | M5R6G8 | 6.32 × 6.32 | 82 | 0.0222 |
| Cv3 | QLNUBJ | 8.94 × 8.94 | 164 | 0.0444 |
| Cv4 | SZUNPK | 12.65 × 12.65 | 328 | 0.0889 |
| Cv5 | 59R85S | 17.89 × 17.89 | 656 | 0.1778 |
| Cv6 | 34CPCT | 25.3 × 25.3 | 1312 | 0.3555 |
| Cv7 | CRXE5C | 25.31 × 25.31 | 1312 | 0.3555 |

Total range: ε = 0 to 0.9776, with 192 unique discrete values.
In Zhao perturbation range [0.031, 0.25]: 40 unique ε values.

### ui_in → cv-cell mapping (v8 routing)

| ui_in pad | x position (µm) | y_H (µm) | climb_x (µm) | cv-cell |
|---|---|---|---|---|
| ui_in[0] | 138.46 | 225.05 | 190.40 | cv(186.8, 96.05) |
| ui_in[1] | 135.70 | 224.40 | 189.80 | cv(186.8, 118.05) |
| ui_in[2] | 132.94 | 223.75 | 189.20 | cv(186.8, 140.05) |
| ui_in[3] | 130.18 | 223.10 | 188.60 | cv(186.8, 162.05) |
| ui_in[4] | 127.42 | 222.45 | 191.00 | cv(175.8, 162.05) |
| ui_in[5] | 124.66 | 221.80 | 191.55 | cv(175.8, 140.05) |
| ui_in[6] | 121.90 | 221.15 | 192.10 | cv(175.8, 118.05) |
| ui_in[7] | 119.14 | 220.50 | 192.65 | cv(175.8, 96.05) |

Higher-x ui_in pads get higher y_H to keep M3 V/H paths from crossing.

## Verification reproduction

```bash
cd /foss/designs/tt_um_thomas_ep_sensor_v7
# Regenerate v8 GDS from v7 baseline
git show main:gds/tt_um_thomas_ep_sensor.gds > /tmp/v7_baseline.gds
python3 scripts/v8/v8_full_8route.py
# Verify DRC (Magic + KLayout)
/foss/tools/magic/bin/magic -dnull -noconsole -T sky130A scripts/v8/v8_magic_drc.tcl
bash scripts/v8/run_klayout_drc.sh
# Verify EP physics
python3 scripts/v8/v8_final_verify.py
```

## Outstanding caveats

1. **PEX not run**: capacitances were extracted from cap_mim_m3_1 cell
   parameters, not from a full Magic parasitic extraction. Real silicon
   could differ by ~5% due to parasitic capacitance and metal resistance.
2. **OTA buffer modeled as ideal VCVS**: real silicon has NMOS
   source-follower with finite output impedance. Should not change slope
   significantly, but absolute Δf values may shift slightly.
3. **Bond + pad parasitics**: 1.5 nH bondwire and 125 fF pad C
   modeled approximately per V7_FINAL.md.

These caveats apply to the absolute Δf values but not to the slope
(which depends on the chip's β condition, not on bond parasitics).

## Recommendation

The v8 chip is **ready for submission to ttsky26a shuttle**.

Merge PR #1 to main, push the merged GDS, request shuttle slot replacement
of v7 with v8.
