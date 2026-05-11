# v7 attempt log — what was tried in-session and why it failed

This session attempted the v7 plan from V7_PLAN.md. Multiple approaches were
explored; all hit DRC walls that need interactive layout tools to resolve.

## Attempt 1: Cluster relocation (move 6 cells out of L2 spiral footprint)

**Approach**: Move cap_mim_C7Y9C2, cap_mim_XCEES9, 2 bias resistors, 2 bias
NMOS cells from inside L2 footprint to the bottom strip (y=0-25).
Add M3 "extension wires" to reconnect each moved cell to its original net
endpoints.

**Result**: 4,220 BEOL DRC violations
- 2,500 via3.2 (via size 0.2 µm rule)
- 1,250 via3.1_a (via spacing rule)
- 298 ct.2 (contact rule)
- Plus m1.6, li.3, m1.2, others

**Root cause**: Cells contain internal via stacks and substrate features that
become rule-violators when displaced into empty silicon. Top-level routing
wires didn't move with the cells, creating dangling/conflicting routes.

**Fix needed**: Manual M3/M4/M1 routing in Magic from each new cell terminal
back to its original net target. ~1 day per cell × 6 cells = 6 days.

## Attempt 2: Aggressive 3-turn spiral on L1 only (L1 has no cells inside)

**Approach**: Keep L2 as v6 in-place thicken. Replace L1 with 3-turn w=15
spiral. L1's footprint (8, 28)-(142, 162) has no cell collisions.

**Result**: 1 m4.5ab violation at cap_mim_76K9AN cell edge (right boundary of L1)

**Sub-attempt 2a**: Shrink OD from 130 to 128 to clear cap_mim
**Result**: 25 m3.4_a violations (tiny 0.2×0.2 M3 fragments at FlexPath ends)

**Sub-attempt 2b**: FlexPath with rounded corners instead of overlapping rectangles
**Result**: Same 25 m3.4_a fragments — sub-grid polygon artifacts from
gdstk's FlexPath-to-polygon discretization at path endpoints.

**Sub-attempt 2c**: Various W/S combinations (w=12 s=4, w=14 s=4, w=10 s=6)
**Result**: 70-185 m3.4_a violations (worse with wider spacing — increased
edge-pair counts).

**Root cause**: Square spiral geometry with abrupt path endpoints produces
sub-grid fragments that violate M3 spacing rules at the topology level.
Manual cleanup of each fragment is needed.

**Fix needed**: Interactive Magic editing to merge fragments or trim
sub-resolution features. ~1 day.

## Attempt 3: Figure-8 L2 (not attempted)

**Status**: blocked. Vertical figure-8 (only geometry giving perfect M_12
cancellation) requires L2 cluster to be relocated first (Attempt 1).
Side-by-side figure-8 collides with the cluster too.

## Attempt 4: NMOS source-follower OTA replacement (not attempted)

**Status**: deferred. Replacing the OTA layout (4 NMOS today + 5
schematic-PMOS that don't exist in GDS) with 2 explicit source-follower
NMOS requires layout work on a different part of the chip. Could be
attempted separately but interacts with the OTA bias routing.

## Conclusion

The programmatic v7 hits real physical-design limits in the v2 floorplan.
A proper v7 needs interactive layout tools (Magic) and manual rerouting
work that totals ~2-3 weeks of analog layout time, as estimated in
V7_PLAN.md.

For this session: v7 GDS reverts to identical-with-v6 (passing TT precheck).
The v7 plan and attempt log remain as roadmap documentation.
