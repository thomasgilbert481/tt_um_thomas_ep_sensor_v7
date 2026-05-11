# tt_um_thomas_ep_sensor v4 — Zhao chiral exceptional-point sensor (Recipe B)

[![GitHub Actions](../../actions/workflows/gds.yaml/badge.svg)](../../actions/workflows/gds.yaml)

A silicon implementation of the Zhao 2024 (Nat Commun 15:9907) chiral
exceptional-point sensor on the sky130A 2x2 Tiny Tapeout analog tile.
v4 = v2 baseline + 2 GDS-level changes that re-spiral the tank inductors
for higher Q.

## What it is

Two LC tanks (L=0.6 nH spiral, CT~1.8 pF MIM cap) coupled via a
unidirectional capacitive path (Cc=1.36 pF + on-chip diff-pair OTA).
At eps=0 the chip presents a single resonant peak; perturbation through
the 8-bit cv-array splits the eigenmodes following Zhao's hyperbolic
formula:

    Df^2 = Df0^2 + (2 * kappa * f0)^2 * eps

Predicted operation (from sky130 ngspice sim of the extracted chip):
- f0 = 4.6 GHz
- Q_loaded ~ 12
- kappa_eff = 0.339
- Df0 ~ 339 MHz (baseline detuning, hidden under Q-broadening at eps=0
  so chip looks single-peak)
- R^2 of Df^2-vs-eps fit = **0.9996**

## How it differs from v2

| Change | v2 | v4 |
|---|---|---|
| Spiral turns | 4 | 3 |
| Spiral trace width | 10 um | 15 um |
| Spiral metal | M3+M4 stacked + M1 PGS | M3+M4 stacked only (PGS stripped) |
| Spiral Rs | 5.6 Ohm | 1.5 Ohm |
| L per spiral | 1.35 nH | 0.6 nH |
| f0 | 3.06 GHz | 4.6 GHz |
| Loaded Q | ~5 | ~12 |
| eps_min resolved | 0.157 (b5) | **0.022 (b2)** |
| cv-bits resolvable | 2 (b5, b6) | **5 (b2 - b6)** |
| Sub-Zhao window coverage | No | **Yes** |

Same schematic, same pin map, same analog block. Only the spiral metal
and the M1 PGS underneath were re-routed.

## How to test

Apply DC bias: VDPWR=1.8 V, VGND=0 V.

Connect a VNA (1.5 GHz - 7 GHz) to ua[0]. Drive 50 Ohm matched.

Sweep cv-array code on ui[7:0]:
- All 0 (eps=0): single peak at f0 ~ 4.6 GHz
- b2 alone (code 4): 2 peaks split by ~ 552 MHz
- b3 alone (code 8): 2 peaks split by ~ 731 MHz
- b6 alone (code 64): 2 peaks split by ~ 1873 MHz

See the `docs/info.md` for the complete bringup protocol.

## External hardware

None required. The chip is fully on-chip - no SMD inductors, no external
opamp. Just bias supplies and a VNA.

## References

- Zhao et al., "Exceptional points induced by unidirectional coupling in
  electronic circuits", *Nature Communications* **15**, 9907 (2024).
  https://www.nature.com/articles/s41467-024-53929-4
- Tiny Tapeout analog spec: https://tinytapeout.com/specs/analog/
