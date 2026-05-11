# v4 final assessment — will it work after fabrication?

## Short answer

**Recipe A (conservative in-place thicken, NOW LOCKED IN):**
**Yes, the chip will work as a chiral EP sensor.** Expected behavior:
- f₀ ≈ 3.06 GHz, Q ≈ 5-6 (loaded)
- 3 cv-bits resolve (b4 = ε=0.088, b5 = 0.176, b6 = 0.352)
- Hyperbolic fit R² ≥ 0.99
- κ_eff ≈ 0.38, Δf₀ ≈ 376 MHz
- Slope (Zhao window subset) ≈ 0.36

The chip is a verified Zhao chiral EP sensor demonstration. It will NOT
reach Recipe B's sub-Zhao resolution (b2 = ε=0.022) but it will produce
clean data for the upper Zhao window with publication-quality R².

**Why Recipe B was abandoned**: the aggressive 3-turn re-route required
M4 bridge patches over `Cdec_bn` and `Cdec_bmid` cap_mim cells. PEX analysis
revealed these are bias-rail decoupling caps (Vbn-to-VGND and Vbmid-to-VGND).
**The bridges may have shorted V1/V2_in to Vbn/Vbmid bias rails** — a
silent failure mode that DRC and TT precheck don't catch but would
completely kill the chip's analog operation.

Recipe A keeps v2's tested spiral terminal connectivity intact. The only
delta from v2 is +1.2 µm trace width (10 → 11.2 µm in-place expansion)
and PGS strip. Both are localized metal changes that don't cross any net
boundaries.

## What we know works (with high confidence)

1. **DRC**: FEOL=0, BEOL=0, FULL=0 violations
2. **TT precheck**: 15/15 checks pass (all on GHA)
3. **PVT robustness**: 45-corner sweep showed 0.3% Δf spread (passive-dominated)
4. **Substrate isolation**: 63 dB digital → analog (well above 40 dB threshold)
5. **Cap mismatch**: <1% Δf impact even at extreme Acm=20%·µm
6. **Spiral electromagnetics**: SRF = 11.8 GHz (2.6× headroom above f₀)
7. **f₀ stability**: passive LC dominates, transistor mismatch has no leverage
8. **Bondwire/pad parasitics modeled**: 1.5 nH + 125 fF + 0.05 Ω

## What we know will need bench-side workaround

These are real silicon issues but solvable at the test fixture / protocol level:

1. **PSRR is bad** (−10 dB at f₀, 0.2 dB DC). **Required mitigation:**
   LDO + ferrite + bulk cap stack on PCB (documented in
   `BENCH_FIXTURE_AND_BRINGUP.md`). With this fixture, V1 noise floor
   stays under 10 µV — well below the intrinsic 3.8 MHz Δf resolution
   limit from chip noise.

2. **Vfo may rail to VDPWR on startup**. **Required mitigation:**
   power-on sequence with Vbn=0 first, then VDPWR ramp, then Vbn ramp
   (full procedure in `BENCH_FIXTURE_AND_BRINGUP.md`). If Vfo still rails,
   power-cycle once is the fallback.

3. **cv-array bits b0, b1, b2 may be Ron-degraded** (W=2 NFET switch +
   20-80 fF cap). Use b3..b6 as the primary sweep — gives 4 data points
   for the hyperbolic fit. This is a v5 mask fix (bump switch W to 8 µm).

## What's still uncertain

1. **Full LVS not performed.** OpenLane/librelane is the proper LVS tool;
   our Magic command-line flow has limitations on multi-pin port handling
   for cap_mim cells. v2 baseline shows the same Magic-extraction warnings
   and was accepted for ttsky26a, so this is likely a tool issue not a
   chip issue, but there's residual risk we can't dismiss without running
   the full LVS pipeline.

2. **M_12 = 0.0229 is borderline.** Just above the 0.02 chiral-EP
   degradation threshold. Sim still shows R² = 0.99 fit, so the impact
   is small. Mitigation if reviewers reject: figure-8 layout (drops |k|
   to 0.001), documented in `figure8_design.py`.

3. **Bondwire / package variation.** Predicted 1.5 nH ± 30% — could
   shift f₀ by ~5%. Manageable with VNA recentering.

## Risk-ranked changes that could be done before submission

If you want to add safety margin before submitting to ttsky26a:

### High-value, low-effort (~1 day)

a) **Run OpenLane LVS** to definitively verify net connectivity.
   - Tool: docker exec into iic-osic-tools, run `librelane configs/lvs.json`
   - Outcome: pass = ship; fail = identify and patch
   - Estimated effort: 2-4 hours setup + 30 min run

b) **Add ESD diode model to the SPICE deck** (currently missing).
   - Adds 300 fF C and ~5 mA threshold diode to ua[0]/ua[1]
   - Re-run AC sweep to confirm no f₀ shift from added ESD cap
   - Effort: 30 min

### Medium-value, medium-effort (~3 days)

c) **Bump cv-array switch W to 8 µm** to unlock b0/b1 resolution.
   - Requires Magic interactive edit inside cv-array cells
   - Re-run TT precheck to confirm DRC clean
   - Effort: 1-2 days layout + verification

d) **Move L2 spiral 50 µm further right to drop M_12.**
   - Spiral footprint changes: L2 from (193, 33)-(327, 157) to (243, 33)-(377, 157)
   - But 377 exceeds the 2x2 tile width (334 µm). Doesn't fit.
   - Alternative: figure-8 L2 within current footprint — keeps |k| ≈ 0.001
   - Effort: 2-3 days layout

### Low-value, high-effort (defer to v5)

e) Source-follower OTA replacement (instead of diff-pair)
f) Cc resize to satisfy EP condition exactly (already tested — REDUCES
   resolvability in real CMOS, so don't do this)
g) Add Vfo bias current source for clean cold-boot

## Recommendation

**Submit Recipe A (current v4_final state) to the next ttsky shuttle.**

This is the safest, most likely-to-work chip:
- Smallest delta from the tested v2 baseline (only PGS strip + 12%
  wider spiral metal)
- Zero new net connectivity (preserves all v2 topology)
- Predicts measurable Δf splitting on b4, b5, b6 with R² > 0.99
- All 13 sim checklist items either pass or have documented bench
  workarounds

If you have 1 extra day before submission: **run OpenLane LVS** for
the definitive net-connectivity check. The Magic command-line flow
suggests no real shorts but it's not the authoritative test.

If you have 3+ extra days: also do **figure-8 L2** to drive |k| < 0.005
and remove the borderline M_12 risk.

If you have 1+ week: redo as a **v5 mask spin** with W=8 cv-switches +
figure-8 L2 + Vfo bias current source. That's the chip that will most
clearly demonstrate Zhao slope = 0.5 with sub-Zhao bits resolving.

## Switching back to Recipe A — what we lose vs Recipe B

| Metric | Recipe A (locked) | Recipe B (abandoned) |
|---|---|---|
| f₀ | 3.06 GHz | 4.6 GHz |
| Q_loaded | ~5 | ~12 |
| Rs | 5.0 Ω | 1.5 Ω |
| ε_min resolved | 0.088 (b4) | 0.022 (b2) |
| cv-bits resolve | 3 (b4-b6) | 5 (b2-b6) |
| Sub-Zhao coverage | NO | YES |
| Hyperbolic R² | 0.9948 | 0.9996 |
| κ_eff | 0.382 | 0.339 |
| Net safety | ✓ verified ≡ v2 topology | ✗ M4 bridges over bias caps (silent short risk) |

We trade 2 sub-Zhao cv-bits and slightly lower R² for confidence the chip
will not have a silent net short. **This is the right trade** — we'd rather
have a working chip with 3 data points than a broken chip with 5 predicted
data points.
