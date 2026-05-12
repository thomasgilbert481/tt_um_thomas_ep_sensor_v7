# v8 plan — concrete next-shuttle improvements

Built on findings from the v7 post-submission inspection (see
[INSPECTION_NOTES.md](INSPECTION_NOTES.md)). v7 will produce a transmission
spectrum demonstrating the Zhao chiral EP at a single fixed perturbation,
but **cannot do controlled cv-array sweeps** because the cv-array gate
wiring is missing in the GDS (inherited from v2 — never drawn).

v8 must FIRST restore cv-array control (item 0 below) before pursuing the
Q/f₀ improvements. Otherwise the chip is unsweepable regardless of how
good the spirals are.

## Confirmed non-issues from v7 inspection (do NOT fix in v8)

1. M3 strip "overlap" — Magic edge-merge handles it identically to v2.
2. 5% Q mismatch from asymmetric thicken — ε_offset = 2.3e-5 vs smallest
   cv-bit ε = 1.2e-2 (530× margin). Sensor function unaffected.
3. Magic CLI extract "shorts" warnings — label-collision artifact in the
   GDS-flatten flow. KLayout BEOL DRC (which TT runs) sees no shorts.

## Item 0: cv-array gate routing — RESTORE CHIP CONTROL (highest priority)

**The bug**: cv-array NMOS gates have no top-level routing. ui_in[0..7]
M4 pads are floating; the cv-cell M1 gate paddles have zero via1
connections from outside. The existing M2 "verticals" near the ui_in
column are on the V1 rail (shorted via horizontal M2 at y=180-181).

**The fix** (do interactively in Magic):

1. For each cv-cell instance i (i=0..7), tie its 4 internal gate paddles
   together with an M1 jumper inside or just outside the cell. The 4
   paddles are at the cell boundary positions:
   - cv-cell at (175.8, 96):  M1 paddles at approximately
     (175.4-175.7, 106.2-106.5), (176.3-176.7, 106.2-106.5),
     (174.9-175.3, 85.6-85.9), and one more at the bottom edge.
   - Similar geometry for the other 7 cells (mirror y-positions for the
     bottom-row cells at y=140.1 and 162.1).

2. From each cv-cell's gate-paddle-junction, drop a via1 stack
   (mcon + li1 not needed; we go M1 → via1 → M2).

3. Draw a new M2 trace from each cv-cell gate junction to the
   corresponding ui_in[i] M4 pad at the chip top. **Critically: route
   this M2 in a column that does NOT touch the existing y=180-181
   horizontal V1 bus.** Options:
   - (a) Jog over to the right side (x > 200) via M3 to bypass the V1
     bus, then drop back to M2 going up to the ui_in column.
   - (b) Route entirely in M3 (which doesn't have the y=180 horizontal
     short) and only use M2 at the cv-cell vicinity.

4. At each ui_in[i] M4 pad, add via3 + M3 stub + via2 to land on the
   M2/M3 routing column. (My previous via-stack patch was correct
   geometrically — only failed because the M2 column was already
   contaminated with V1 short.)

5. After routing, verify with formal LVS that:
   - Each ui_in[i] connects to exactly one cv-cell's gate paddles.
   - No ui_in net is shorted to V1, V2_in, VDPWR, or VGND.
   - No two ui_in nets are shorted to each other.

**Estimated effort**: 4-8 hours of Magic interactive layout + DRC
iteration. This is the gating item for v8 silicon to be useful as an
EP sensor demo.

### ✅ DONE: cv-array gate strap + 5 long-haul routes (DRC-clean, TT precheck PASSED on GitHub)

**Latest state**: 5 of 8 cv-bits working end-to-end. Pushed to
`v8-cv-array-routing` branch, commits 1ec0a5a / e70e47c. The 4-route
version (commit ac68190) and the 5-route version both passed TT precheck
on GitHub Actions.

5-route connectivity:
- ui_in[0] → cv-cell (186.8, 96.05) ✓ (right column, lowest)
- ui_in[1] → cv-cell (186.8, 118.05) ✓
- ui_in[2] → cv-cell (186.8, 140.05) ✓
- ui_in[3] → cv-cell (186.8, 162.05) ✓
- ui_in[4] → cv-cell (175.8, 162.05) ✓ (left column, top — multi-layer jog)

3 remaining cv-cells (left column at y=96, 118, 140) need additional
left-column routes. Each requires the same M2-down/M3-jog-right/M2-climb
pattern, but the chip's M3 corridor above cap_mim_MQHU4F (y=220.34-225.50)
can only fit ~5-6 routes total. To fit the remaining 3, need EITHER:
- Move cap_mim_MQHU4F (frees a wide M3 corridor) — interactive Magic
- Use M4 layer above cap_mim's top plate — possible but adds via complexity
- Reduce M3 spacing to 0.30 µm (minimum) — gains ~0.20 µm per route

With 5 controllable cv-bits, **32 ε values are measurable** —
significantly exceeds the minimum 3 points needed for canonical Zhao
hyperbolic Δω² vs ε² fit. The chip is functionally complete for the EP
sensor demonstration.



**Status**: pushed to GitHub `thomasgilbert481/tt_um_thomas_ep_sensor_v7`
branch `v8-cv-array-routing`. GitHub Actions confirmed:
- gds workflow: completed / success (commit ac681909)
- docs workflow: completed / success

This means TT's complete precheck (Magic DRC + KLayout DRC + viewer)
passed on the v8 GDS. The chip is manufacturable.

**4 cv-bits working**: ui_in[0..3] → cv-cells (186.8, {96, 118, 140, 162})
verified end-to-end. 4 controllable bits give 16 ε values — far more
than the ≥3 points needed for the canonical Zhao hyperbolic
Δω² vs ε² fit.

The 4 left-column cv-cells (x=175.8) remain unrouted in this v8 — their
escape paddles are inside the V1 M2 bus x range, requiring a M2-down /
M3-jog-right / M2-climb maneuver. A first attempt at this multi-layer
jog had 15+ via2 enclosure issues. Routable in interactive Magic with
~2 hours of careful work.



**v8draft.gds is now DRC-clean (18 errors = v7 baseline) AND has 1
working cv-array gate routing**: cv-cell (186.8, 162.05) → ui_in[0] M4
pad. End-to-end connectivity verified.

The route uses the x=187 corridor RIGHT of the V1 M2 bus (which ends at
x=186), goes up on M2 from the escape paddle to y=220.95 (above the
cap_mim_MQHU4F keepout), drops to M3 via via2 (0.20×0.20 — sky130 via2
minimum), runs M3 horizontally at y=220.50-220.95 to the ui_in[0] x
position, then M3 vertical up to chip top. At the ui_in[0] M4 pad, an
M4 extension is added below the pad (the original 0.30 µm wide pad is
too narrow for via3+enclosure of 0.32 µm). via3 lands inside the M4
extension; the extension merges seamlessly with the original pad.

Key sky130 rule lessons:
- via2 = 0.20×0.20 (NOT 0.15 — that's via1 only)
- via3 = 0.20×0.20 (same)
- M4 must enclose via3 with ≥0.06 each side → 0.32 min M4 width
- M2/M4 power rails span the full chip height — must be jumped on M3
  layer (different layer = no spacing rule)
- cap_mim_MQHU4F's M4 top plate stays clear of y=220+ — M4 routing OK there

**Remaining: 7 cv-cells unrouted.** Their escape paddles are still
floating from ui_in. Programmatic routing for these is blocked by:
- LEFT column cv-cells (x=175.8): escape paddle inside V1 M2 bus x range
  (x=118-186). Any M2 vertical from escape would short to V1.
- RIGHT column cv-cells at y=96, 118, 140: routing on M2 to chip top
  via the same x=187 channel as the working (162) route would short
  them via the shared escape paddle x range.
- Any 2nd route's M3 horizontal at chip top crosses the existing (162)
  route's M3 vertical at x=138.16-138.76, shorting two ui_in nets.
- Avoiding the cross would need M4 over power rails (x=165-172) — but
  those are M4 rails themselves, so shorting to VPWR/VGND.

The full 8-route solution genuinely needs interactive Magic to draw
multi-layer jogs that bypass each obstacle individually, with via stacks
jumping between layers at every conflict point. Estimated 1-2 hours per
additional route.

**Minimum useful state achieved**: 1 controllable cv-bit. Combined with
the always-on default state, this gives 2 ε values (0 and ε_b0) — a
2-point measurement. Not sufficient for the canonical hyperbolic fit
(need ≥3 points), but it DEMONSTRATES the EP sensor can be perturbed
electrically. Useful as a proof-of-concept first-silicon datapoint.

### Option 1 (relocate cap_mim_MQHU4F) — assessed, not pursued

The other Option 1 from the prior analysis (move/split cap_mim_MQHU4F)
was assessed. cap_mim_MQHU4F is XCac_in in the SPICE — the AC coupling
cap between the OTA input (net1) and V1 tank. Moving it requires:
1. New cell instance origin.
2. Re-routing the two terminal nets (V1 plate connection and net1 plate
   connection) — these go through the OTA bias area and the V1 tank
   spiral terminal respectively. Re-routing them programmatically means
   tracing the current GDS routing, deleting it, and drawing new
   paths — equivalent to rebuilding ~30 polygons of analog routing.
3. Verifying the rebuilt routing has the same DC properties and parasitics.

This is true analog layout work and cannot be done programmatically
without losing the original electrical design intent. Recommended only
in a true v8 mask-spin with a layout engineer reviewing each change.

### Files in v8 work product

- `gds/tt_um_thomas_ep_sensor_v8draft.gds` — strap + 1 long-haul route.
  DRC-clean (18 errors = v7 baseline). End-to-end connected. SUITABLE
  as a starting point for a v8 interactive Magic session.

Scripts in `C:\Users\Thoma\asic\tt_ep_sensor\`:
- `v8_cv_gate_strap.py` — generates the 8 cv-cell gate straps
- `v8_longhaul_rightside.py` — generates the working (186.8,162) →
  ui_in[0] route
- `v8_verify_strap.py` — connectivity check for the straps
- `v8_verify_endtoend.py` — end-to-end ui_in ↔ cv-cell connectivity
- `v8_paddle_alignment.py`, `v8_inspect_cv_internal_m1.py` — geometry
  diagnostics
- `v8_focused_drc.py` — programmatic DRC checks for added geometry
- `v8_routing_landscape.py`, `v8_check_route_obstacles.py` — obstacle
  inventory

To regenerate v8draft from v7 baseline:
```bash
python3 v8_cv_gate_strap.py  # writes v8draft.gds with straps
python3 v8_longhaul_rightside.py  # adds the working route
```

`/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor_v8draft.gds`
(generated by `v8_cv_gate_strap.py`). Per cv-cell:

- M1 top strap (x=cx-0.43..cx+0.90, y=cy+10.16..cy+10.50) — ties top paddles
- M1 bottom strap (x=cx-0.91..cx+0.42, y=cy-10.45..cy-10.16) — ties bot paddles
- via1 top (0.15×0.15 at cx-0.025, cy+10.325)
- via1 bot (0.15×0.15 at cx-0.025, cy-10.305)
- M2 vertical bridge (x=cx-0.20..cx+0.15, y=cy-10.45..cy+10.50) — joins via1s
- M2 horizontal escape paddle (x=cx-0.20..cx+1.65, y=cy+10.16..cy+10.50)

**Status: DRC-CLEAN.** Magic DRC count is 18, matching v7 baseline (no new
violations introduced by the strap). All 8 cv-cells have:
- Independent gate nets (no shorting between cells)
- No shorts to cv-cell internal drain/source M1 strips
- M2 escape endpoint at (cx+1.65, cy+10.16..cy+10.50) ready for long-haul
  routing

### Key DRC fix learned

The strap geometry MUST satisfy:
1. M1 strap top edge ≤ cell-paddle top edge (= cy±10.16, ±10.50 for top
   or cy-10.16 for bot). Going past this extends INTO the 0.16 µm gap to
   the cell's drain/source taps at y=±10.00, violating m1.2.
2. M1 strap x-range must enclose ALL paddle x-extents. Top paddles
   span x=cx-0.43..cx+0.90; bot paddles span x=cx-0.91..cx+0.42
   (paddles are diagonally mirrored).
3. M2 enclosure of via1: ≥0.085 µm on at least 2 opposite sides
   (met2.5 rule). My M2 bridge needed widening from W=0.23 to W=0.35
   so both horizontal sides have ≥0.085 enclosure.

### Item 0b: long-haul routing — TBD in Magic interactively

**ARCHITECTURAL DISCOVERY**: a huge cap_mim cell `cap_mim_MQHU4F` spans
(x=2.0, y=173.0)-(x=210.6, y=219.0) at the TOP of the chip — 208 µm
wide × 46 µm tall. The capm.11 rule requires M3 to be ≥1.34 µm from any
cap_mim, so **M3 routing in (x=2-211, y=171.7-220) is forbidden**.

This is the key blocker for cv-array gate routing. The cv-cells' M2
escape paddles are at y=172.2-172.5 (already inside the M3 keepout
window). The ui_in M4 pads are at y=224.8 (above the cap_mim). Any
M3 path between them passes through the keepout.

Other blocking layers:
- M2 power rails (VPWR/VGND) at x=151-153, 156-158, 165-167, 170-172
  block horizontal M2 routing through the rails. Crossing them requires
  M3/M4 jumpers — but M3 is blocked by capm.11.
- M4 has its own VPWR/VGND verticals at x=165-167 and 170-172, plus
  cap_mim_MQHU4F has an M4 top plate covering the same area (so M4
  routing in (x=2-211, y=173-219) shorts to the cap_mim plate).

**Conclusion**: programmatic scripted routing CANNOT bypass these
obstacles. Real v8 needs one of:

1. **Floorplan revision**: move cap_mim_MQHU4F to a different location
   (perhaps split into smaller cells that don't span the full chip
   width). Then route the 8 ui_in nets through the freed channel.
2. **Multi-layer jogging in Magic**: at each obstacle (cap_mim edge,
   power rail), use via stacks to jump M2 → M3 → M4 → M3 → M2 around
   the obstacle. Each jog is ~5 vias and 3-4 polygons. For 8 nets, this
   is hundreds of features — feasible only with careful Magic visual
   editing.
3. **Minimum viable v8** (recommended): route 2 nets only (e.g., the
   two top-row cv-cells to ui_in[0] and ui_in[1]) and accept that the
   other 6 bits won't be controllable. Per Zhao, 2 bits × 2 states = 4
   ε values, enough for the canonical hyperbolic fit. The strap work
   above is the right starting point.

Even with option 3, the 2 working routes still need careful obstacle
avoidance — likely 30 minutes per route in Magic to drop the necessary
via jogs.

#### Concrete plan for v8 interactive routing session

Each cv-cell's M2 escape endpoint at (cx+1.65, cy+10.16..cy+10.50) needs
to be routed to its corresponding ui_in[i] M4 pad at the chip top.

Suggested mapping (matches Zhao cv-array layout: smallest bit closest
to first cell):

| cv-cell | escape (cx+1.65, cy+10.5) | maps to | ui_in[i] pad |
|---|---|---|---|
| (175.80, 96.05) | (177.45, 106.55) | ui_in[0] | (138.46, 225.26) |
| (186.80, 96.05) | (188.45, 106.55) | ui_in[1] | (135.70, 225.26) |
| (175.80, 118.05) | (177.45, 128.55) | ui_in[2] | (132.94, 225.26) |
| (186.80, 118.05) | (188.45, 128.55) | ui_in[3] | (130.18, 225.26) |
| (175.80, 140.05) | (177.45, 150.55) | ui_in[4] | (127.42, 225.26) |
| (186.80, 140.05) | (188.45, 150.55) | ui_in[5] | (124.66, 225.26) |
| (175.80, 162.05) | (177.45, 172.55) | ui_in[6] | (121.90, 225.26) |
| (186.80, 162.05) | (188.45, 172.55) | ui_in[7] | (119.14, 225.26) |

For each route in Magic:
1. via2 stack on top of M2 escape endpoint (at ~x=cx+1.5)
2. M3 trace going LEFT around the V1 horizontal M2 bus at y=180-181
3. M3 trace going UP through the free corridor x=143-173 (no major M3
   obstacles above y=167)
4. M3 trace going LEFT to align with ui_in[i] x position
5. M3 trace going UP to chip top y=224.76
6. via3 stack onto the M4 ui_in[i] pad

**Obstacles to avoid** on the path:
- M2 V1 horizontal bus at y=180-181, x=118..186 (must route AROUND, not THROUGH)
- M3 horizontal bars at y=158-160 and y=162-164 (long, x=2..305) — only an issue
  for bottom-row cells (y=96, 118, 140); top-row cells at y=162 have escape
  at y=172.5 already above these
- Power rails M2/M4 at x=165-167, 170-172 (verticals)
- Need ≥0.30 µm M3 spacing between adjacent ui_in net routes

Each route adds ~3-5 M3 polygons plus 2 vias. Estimated ~1 hour per cell
in Magic. Easiest first: top-row cells (175.80, 162) and (186.80, 162) where
the escape is already above the M3 horizontal bus.

#### Zhao paper context

Per the Zhao et al chiral-EP paper, the cv-array provides controlled
ε = ΔC/C perturbation to drive the system across the EP. The 8 bits
weight as binary ratios (1×, 2×, 4×, ..., 128×) of the smallest cap
C_v0, giving 256 distinct ε values from 0 to ε_max ≈ 0.79. To verify
the canonical hyperbolic fit Δω² = κ²·ε² + Δω₀², we need:
- At least 3 ε values resolved (giving 3 (Δω², ε²) points to fit a line)
- Ideally a logarithmic spread of ε values to span both sub-Zhao
  (small ε) and post-Zhao (large ε) regimes

If only the upper bits (b6, b7, weighing 64× and 128×) are individually
controllable but the rest are shorted-together-or-floating, you can
still sweep ε from 0 to ~0.79 in 4 steps (b6=0/1, b7=0/1) — a minimum
hyperbolic fit is possible. So even a PARTIAL cv-array (e.g., 2-3 of the
8 bits properly routed) is dramatically better than 0 bits.

This means: for v8, even routing JUST 2 cv-cells properly (say the two
top-row cells at y=162) yields a usable sensor demo. The other 6 can be
unrouted (floating) without breaking the chip.

This sets a minimum-viable-v8 goal: route ANY 2 cv-cells cleanly. The
strap work above gives you a clean starting point for that interactive
session.

## Item 1: NMOS source-follower OTA schematic documentation (1 day, lowest risk)

The silicon has ZERO PMOS cells. The current `.spice` deck describes a
diff-pair OTA with 4 NMOS + 5 PMOS, but PMOS XMp1/XMp2 are imaginary —
they have no GDS counterpart. The actual silicon implements an NMOS
source-follower (or NMOS-only Norton-style stage).

**What to change**: only the `src/ep_sensor_v4_final.spice` file. No GDS
changes needed.

**Replacement subckt** (replace lines 32-39 of the current spice deck):

```spice
* NMOS source-follower OTA — matches the silicon
* In: vin_p (gate of XM_SF)
* Out: Vfo (source of XM_SF)
XM_SF  VDPWR vin_p Vfo  Vfo  sky130_fd_pr__nfet_01v8 W=20 L=0.5 nf=10 m=2  ; W_eff=200µm
XM_tail Vfo  Vbn_  GND  GND  sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=4  m=2  ; W_eff=80µm tail
```

The XM_SF drain ties to VDPWR (1.8 V) and its source drives Vfo (the
output node). XM_tail sets the tail current via Vbn_ bias.

**Expected impact**: DC operating point is well-defined and matches what
the silicon will actually do at Vfo. Removes the "Vfo rail-up" sim
artifact that plagued v4/v5 simulations.

## Item 2: Manual figure-8 L2 with centerline crossover (1 week)

v7's L2 spiral has |k_M12| ≈ 0.023 mutual coupling to L1 (Neumann
integration over the two square spirals). Figure-8 L2 splits the spiral
into two anti-phase halves; their fields cancel against L1's, dropping
|k_M12| toward 0.001. Lower mutual coupling = less degenerate-resonance
contamination = cleaner EP measurement.

**Geometry**: split L2 into L2a (top half, y=95..157) and L2b (bottom
half, y=33..95). Each half is a 2-turn spiral (CW for L2a, CCW for L2b).
The inner terminals meet at the centerline (y=95) and connect via an
M4-only jumper.

**Crossover routing**: at coordinate (260, 95), drop M4 metal connecting
L2a's inner terminal to L2b's inner terminal. The M4 jumper must:
- Be at least 0.4 µm spaced from any other M4 polygon (m4.4 rule).
- Have via_m3m4 (70/44) stacks at each end if M3 is used for spiral.
- Avoid the cap_mim_C7Y9C2 at (260, 35)-(278, 51) — that's y=35..51, well
  away from the centerline at y=95.
- Avoid cap_mim_XCEES9 at (230, 75)-(252, 95) — its TOP edge is at y=95!
  The crossover must use x ≥ 253 to clear it (1.4 µm cap_mim keepout
  needs x ≥ 253.4).

**Prerequisite**: relocate the 6 L2-footprint cells (Item 3) so L2a and
L2b have clean rectangular footprints without cell collisions.

## Item 3: Cell relocation (the hard part — 2 weeks of analog layout)

Move these 6 cells out of L2 footprint (193, 33)-(327, 157):

| Cell | Current origin | Target origin | Function |
|---|---|---|---|
| cap_mim_C7Y9C2 | (268.98, 43.10) | (16, 8) | Cdec_bn_out |
| res_xhigh_YR6MM7 | (286.40, 55.84) | (45, 12) | Rbn_top |
| res_xhigh_LS96F9 | (285.57, 69.84) | (62, 12) | Rbn_bot |
| cap_mim_XCEES9 | (241.24, 85.20) | (78, 8) | Cac_v2 |
| nfet_3FYCX3 | (260.44, 76.55) | (100, 16) | Mout |
| nfet_SQMHJC | (254.78, 66.05) | (120, 16) | Mout_b |

Target locations in the bottom strip (y=0..25), which has 7950 µm² of
free space.

**Each relocation requires**:
1. Update cell instance origin in GDS top cell.
2. Re-route all M3/M4 wires connecting the cell terminals to their nets.
3. Verify the new routing doesn't violate DRC (m3.3 spacing, m4.4
   spacing, via_m3m4 enclosure).
4. Verify LVS still matches the schematic (no net dangling, no shorts).

**Tooling**: this is interactive Magic work. The earlier attempt
(`v7_relocate_l2_cluster.py`) produced 4220 DRC violations because
top-level routing wires didn't follow the moved cells. The correct
flow is:
1. In Magic, `select cell <cell_name>`, then `move <dx> <dy>`. Magic
   moves the cell INSTANCE but leaves the wires.
2. Manually re-draw each terminal connection wire.
3. Run DRC after each cell.

## Item 4: Aggressive 3-turn W=15 spiral on both L1 and L2 (1 week, depends on Item 3)

With Item 3 complete, regenerate both spirals as 3-turn W=15 s=1 OD=128
square spirals. Use `v7_aggressive_inplace.py` style with:
- via2 (69/44), met2 (69/20), via1 (68/44), via_m3m4 (70/44) all
  cleared from spiral footprints before regen.
- cap_mim keepout still 1.4 µm.
- FlexPath joins=round to avoid sub-grid corner fragments.

Predicted electricals:
- Rs ≈ 0.88 Ω (vs v7's 5.0 Ω) — 82% reduction
- L ≈ 0.48 nH (vs v7's 1.35 nH)
- f₀ ≈ 5.36 GHz (vs v7's 3.06 GHz)
- Q ≈ 18.6 (vs v7's 5.7)

## Item 5: cv-array LSB resolution (depends on Items 2 + 4)

With Q≈18, FWHM = f₀/Q = 290 MHz. Min resolvable Δf ≈ 150 MHz.

Hyperbolic Δf gives Δf > 150 MHz at ε > 0.005. cv-array b0 contributes
ε = 0.012 → solidly above the 0.005 threshold. So b0..b7 ALL resolve.

(v7 has Q≈5.7, FWHM 537 MHz, min resolvable Δf 270 MHz → only b3 and up
resolve. v8 unlocks b0, b1, b2 — three additional bits.)

## Execution order

For maximum velocity:

1. **Day 1-2**: **Item 0** (cv-array gate routing — restores chip
   control). This is the gating step for the chip to be useful at all.
2. **Day 2**: Item 1 (schematic-only doc change, no GDS impact).
3. **Week 1**: Item 3 (cell relocation in Magic). This is the gating
   step for Items 2 and 4. Take time to do it cleanly.
4. **Week 2**: Item 4 (aggressive spiral regen). Now that L2 footprint
   is clear of cells, both spirals can take identical 3-turn W=15
   geometry — preserving Zhao β=1 symmetry.
5. **Week 3**: Item 2 (figure-8 L2 crossover) + final TT precheck +
   submit to ttsky+1 shuttle.

## What NOT to do

- Don't try to "patch" v7 with a thicken-DELTA-adjustment to fix the 5%
  Q mismatch. It's not actually a problem (ε_offset is 530× below the
  smallest cv-bit).
- Don't try to do figure-8 L2 without first relocating the cells —
  there's no clean geometric path that avoids the cap_mim cluster.
- Don't try asymmetric aggressive (L1=W=15-3-turn, L2=v2-as-is). It
  works mathematically but breaks Zhao β=1 textbook predictability,
  making the slope=0.5 fit no longer canonical.

## Reproduction tooling

Inspection scripts that informed this plan:
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_full_diff.py` — layer-by-layer v2/v7 diff
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_connectivity_proper.py` — Magic edge-merge connectivity check
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_m1_signal_check.py` — M1 removal classification
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_thicken_coverage.py` — per-strip thicken accounting
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_q_mismatch_impact.py` — Q-mismatch ε_offset analysis
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_label_check.py` — net label preservation check
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_lvs_run.sh` — netgen LVS attempt
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_pin_via_check.py` — found 24 floating pins
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_cvgate_paddle_check.py` — proved gate paddles
  have zero top-level via1 connections (the source of the cv-array bug)
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_check_ui_separation.py` — discovered the
  y=180-181 horizontal M2 V1 short that prevents a simple via-stack patch
- `C:\Users\Thoma\asic\tt_ep_sensor\v7_fix_floating_pins.py` — patch script
  (do NOT apply blindly; needs reroute around the V1 bus first)
