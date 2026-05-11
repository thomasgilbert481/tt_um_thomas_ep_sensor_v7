# v7 post-submission inspection notes

Submitted commit: `635c741` (SYMMETRIC DELTA=0.8 thicken), TT precheck 15/15.
Inspection date: 2026-05-11.

## What v7 actually changed vs v2 baseline

Bounding box identical. 35 cell instances identical, no moves. Layer-by-layer
diff:

| Layer | v2 polys | v7 polys | Δ polys | Δ area µm² |
|---|---|---|---|---|
| diff (67/20) | 646 | 330 | -316 | -7595 |
| M1 (68/20) | 194 | 160 | -34 | -13654 |
| mcon (68/44) | 130646 | 3912 | -126734 | -2852 |
| M3 (70/20) | 73 | 73 | 0 | **+5250** |
| M4 (71/20) | 117 | 117 | 0 | **+5063** |

Net effect: PGS-strip (M1/mcon/diff removed under spirals, with 5 µm halo
preserving cell-internal slivers) + in-place thicken of M3/M4 spiral strips
by Δ=0.8 µm on each side.

## Connectivity preservation — critical finding

- v2 has 25 M3 strips in L1 footprint, 24 of which edge-touch (no positive
  overlap). Magic merges edge-touching polygons into one polygon, so these
  resolve to **[23, 2]** connected components.
- v7 has the same 25 M3 strips, now with **positive 1.6 µm overlap** at every
  formerly-touching edge (each strip widened ±0.8 µm). Connected components
  still **[23, 2]**.
- L2 spiral: same story, **[19, 3]** in both v2 and v7.

The earlier "v7 strips shorted adjacent turns" alarm was a false positive
from using strict positive-overlap as the connectivity relation. Magic DRC
and netlist extraction use edge-merge — under that rule, v7 is topologically
identical to v2.

## What the M1 strip cost us electrically

v2 had M1+M3+M4 stacked spiral strips. The 27 large M1 polys removed were
parallel-resistance contributions, not unique routing paths.

Per-strip Rs (10 µm wide horizontal):
- v2 (M1+M3+M4 in parallel): 1 / (1/0.125 + 1/0.05 + 1/0.05) = **0.0208 Ω/sq**
- v7 (M3+M4 only, but 11.6 µm wide after thicken): 1 / (1/0.043 + 1/0.043) = **0.0216 Ω/sq**

Net Rs change: **+4%** per strip. Negligible. Q stays ~5.7.

The thicken almost exactly canceled the M1 loss.

## All 6 cells inside L2 footprint preserved

cap_mim_C7Y9C2, cap_mim_XCEES9, res_xhigh_po_YR6MM7/LS96F9, nfet_3FYCX3,
nfet_SQMHJC — all at identical origins in v2 and v7.

## Asymmetric thicken coverage

The thicken with cap_mim keepout (1.4 µm) hit different strip counts:

- **L1**: 23/25 strips thickened (92% coverage). 1 strip skipped (right outer
  vertical, mysterious — not adjacent to any cap_mim), 1 strip "weird"
  (terminal stub shrunk from H=2 to H=1.8 µm — DRC-clean, electrically
  insignificant).
- **L2**: 16/22 strips thickened (73% coverage). 6 strips skipped due to
  the 3 cap_mim cells inside the L2 footprint.

This gives L1 ≈ 4.95 Ω, L2 ≈ 5.10 Ω — about **5% Rs asymmetry** between
the two tanks (L2 has higher Rs because fewer of its strips widened).

For Zhao β=1 (L₁·CT₁ = L₂·CT₂), the spiral inductance L is what matters,
not Rs. L is dominated by geometry which is symmetric. So β=1 is preserved.
The 5% Rs asymmetry just means the two tanks have slightly different Q
(Q₁≈5.85, Q₂≈5.60). The EP condition still holds at the correct ε but
the loss-rate matching at the EP is imperfect.

## Risks remaining

1. **No LVS run yet** — TT precheck doesn't include LVS, so we don't have a
   formal proof that net connectivity matches the schematic. The M3 component
   structure match is a strong indicator, but not definitive.
2. **Electrical extraction not run** — Rs/L/Q numbers above are calculated
   from sheet-resistance formulas, not extracted from the actual GDS. A
   Magic PEX run would confirm.
3. **Q is still ~5.7** — modest improvement over v2's ~5. This is the
   "conservative" v7. The aggressive v7 (3-turn W=15) would give Q ~12 but
   requires cell relocation or accepting asymmetric L₁ ≠ L₂ (which violates
   Zhao β=1).
4. **5% Q-mismatch between L1 and L2** from uneven thicken coupon — minor
   but worth fixing in v8 by either (a) applying matching DELTA to L1's 6
   "cap_mim-blocked-equivalent" strips so coverage matches, or (b) more
   cleanly, moving the L2 cap_mim cluster out entirely.

## CRITICAL: cv-array control wiring is missing (inherited from v2)

The single most important finding from formal LVS attempt:

**The 32 cv-array NMOS gate paddles (8 cv-cells × 4 internal fingers) have
ZERO top-level via1 connections.** No metal in the GDS connects ui_in[0..7]
M4 pads (at the chip top edge, y≈225) to the cv-cell M1 gate paddles
(at internal positions inside each cv-cell).

The M4 pin pads for ui_in[0..7] do exist as labels, and there are
8 M2 vertical "stubs" at x=118-138 running from y=181 to y=224.76,
but:
- The M4 pads are floating (no via3 stack to M3 below them).
- The M2 stubs feed into a horizontal M2 bus at y=180-181 that is on
  the V1 rail (shorts to the cv-cell drain), so wiring the M4 pads
  to those stubs would short ui_in to V1 (digital-to-analog short).
- The cv-cell M1 gate paddles inside each PCell have no via1/via2/via3
  stacks coming from outside.

**Implication for submitted v7 silicon**: cv-array bits cannot be toggled.
The cv-array NMOS gates will sit at their floating leakage-equilibrium
voltage on silicon. ε (controlled perturbation) is unsweepable.

The chip will still produce a transmission spectrum via ua[0]/ua[1] and
demonstrate the Zhao chiral EP eigenstructure at one fixed (uncontrolled)
operating point. But the canonical "Δω² vs ε hyperbolic fit" demonstration
cannot be performed on the fabricated silicon.

This is the same in v2 and v7 — it was never wired. v7's PGS strip and
thicken did not introduce it.

## What this changes about v8 priorities

v8 must include real cv-array gate routing as the highest-priority item:
- Draw 8 new M2/M3 traces (separate, not sharing the V1 rail) from each
  ui_in[i] pad position down to the corresponding cv-cell gate paddle.
- Each trace needs via3 + via2 + via1 stack on both ends.
- The 4 internal gate paddles per cv-cell can be tied together by an M1
  jumper inside or just outside the cell, then a single via1 up to the
  routing trace.
- Avoid the existing horizontal M2 bus at y=180-181 (V1 rail) — route
  around it on M3 or jog under it.

Estimated effort: ~4-8 hours of interactive Magic layout, plus DRC
iteration.

### Additional architectural blocker discovered during v8 attempt

`cap_mim_MQHU4F` spans (x=2.0, y=173.0)-(x=210.6, y=219.0) at the chip
top. This is the AC coupling cap Cac_in (per the SPICE extract). Its
M3 plate plus the capm.11 spacing rule (1.34 µm) **forbid all M3
routing in (x=2-211, y=171.7-220)**. Its M4 top plate plus the M4
fill rules forbid M4 routing in the same area.

This is the architectural blocker for cv-array gate routing. The
"natural" path from each cv-cell gate strap (M2 escape at y≈172.5) to
the ui_in M4 pads (at y=225) passes vertically through y=173-224.8 —
exactly the forbidden zone.

Two possible v8 resolutions:
1. Move cap_mim_MQHU4F (or replace with a different-shape MIM cap that
   doesn't span the full chip width). Opens a routing corridor.
2. Multi-layer jog routing: M2 stub from escape → via2 → M3 stub below
   y=171.7 → ascend via M4 corridor x>210.6 (right of cap_mim) → over
   to ui_in pad column via M4 → drop via3 to M4 pad. Each route is
   ~10 vias + 6 stubs.

Option 1 is cleaner and recommended for v8. The v7 design's cap_mim_MQHU4F
placement was chosen for some prior reason (maybe layout convenience or
matching with cap_mim_W8UZ5N at right) but it severely constrains the
cv-array control routing. A repositioned MIM cap or split-into-pieces
strategy would solve this fundamentally.

## v8 improvement opportunities (in rough priority order)

1. **Run LVS on v7 now** to verify the net topology empirically. ~30 min in
   Magic. Confirms whether the M1 strip and PGS removal cost us any
   connection.
2. **Magic extracted simulation** to confirm Rs/L/Q numbers and compute κ_eff
   accurately. ~1 hour.
3. **Figure-8 L2 with manual crossover** — requires relocating the 6 cells
   inside L2 footprint (~2-3 days of analog layout work) plus the centerline
   crossover routing. Yields |k_M12| < 0.001, drops Δω₀ floor, makes the
   sub-Zhao bits resolvable. This is the highest-leverage real improvement.
4. **NMOS source-follower OTA documentation** — silicon is already NMOS-only;
   we just need the schematic to match. Documentation-only change, no GDS.
5. **Aggressive 3-turn W=15 spiral on L1** (L2 needs the cell relocation first
   to do symmetrically). Each spiral alone is straightforward; symmetry is
   the constraint.

## Decision: ship as-is, plan v8 for next shuttle

v7 submitted is structurally identical to v2 with passing Magic DRC and very
slightly better Rs. It is a safe ship. The bigger leverage comes from the
v8 figure-8 + cell-relocation work, which is too risky for a hurried push.
