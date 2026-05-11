# v4 bench fixture, bring-up procedure, and v5 wishlist

Addresses the three real issues identified during pre-tapeout sim and
documents what would need to change for a v5 mask spin.

## Real issue 1 — VDPWR PSRR (must fix at bench, not silicon)

### Problem

V1 is DC-coupled to VDPWR through the on-chip spiral inductor (L1 between
V1 and VDPWR). At AC, the spiral has impedance jωL = j·17 Ω at 4.6 GHz —
nothing in series isolates V1 from VDPWR noise. The simulation shows:
- PSRR at low f: 0.2 dB (VDPWR ripple → V1 essentially 1:1)
- PSRR at 4.6 GHz (resonance): **−10 dB** (3× amplification by the resonant tank)

Any bench supply ripple AT or near f₀ shows up directly on the measured
peaks and shifts them.

### Bench supply fixture (required)

```
[ wall AC ]
    │
[ linear PSU 5V ]            (1 µV noise, < 1 mV ripple typical)
    │
[ LDO TPS7A47 ] ─ output cap 4.7 µF + 100 nF
    │                          (60+ dB PSRR up to 1 MHz; 30 dB at 100 MHz)
[ ferrite bead 600Ω@100MHz ]
    │
[ tantalum bulk cap 47 µF ]
    │
[ MLCC 100 nF + 10 nF + 1 nF (X7R) ]   — decoupling network
    │
[ chip VDPWR pin (PCB trace < 5 mm) ]
```

The ferrite + bulk cap network is critical for >100 MHz isolation. Without
it, 100 MHz LDO output noise will appear on V1.

### PCB layout requirements
- VDPWR plane: separate pour or thin trace, NOT shared with digital VDD
- Decoupling caps placed within 2 mm of VDPWR pin
- Star-ground at the chip; no common impedance with digital pin return
- Optional: ground guard ring around the analog VDPWR trace

### Expected PSRR after fixture
- DC — 1 MHz: > 60 dB (LDO does the work)
- 1 — 100 MHz: > 40 dB (ferrite + bulk cap)
- 100 MHz — 1 GHz: > 30 dB (MLCC self-resonance handles)
- 1 — 6 GHz: > 20 dB (ferrite + π-section)

This puts the V1 noise floor at < 10 µV which is well below the noise-floor
limit (3.8 MHz Δf resolution from intrinsic chip noise).

## Real issue 2 — cv-switch Ron at LSB (v5 fix only)

### Problem

The cv-array NFET switches have small W (v2 used W=2 µm) to keep the parasitic
Coff low. But Ron at W=2 is ~1.2 kΩ which is comparable to the LSB cap's
impedance Z_cap = 1/(2π·4.6G·20fF) = 1.7 kΩ. Result: Ron/Z_cap = 0.71 →
the LSB cap is effectively reduced by 1/(1 + Ron/Z_cap) = 0.58, and below
b3 the cv-bit-to-ε mapping becomes nonlinear.

This is why b0, b1 don't resolve cleanly: the cap effectively has half the
expected value, putting the splitting below the Q-broadening floor.

### Mitigation (no chip change)
- Skip b0, b1 in the cv-code sweep. Use b2 (ε=0.022) as the lowest-ε point.
- v4 still resolves 5 cv-bits (b2..b6) which is enough for clean Δω²-vs-ε fit.

### v5 cv-array switch sizing recommendation

| W (µm) | Ron (Ω) | Ron/Z_cap_LSB | Coff (fF) | recommendation |
|---|---|---|---|---|
| 2 | 1235 | 0.71 | 2 | v2 current — degrades LSB |
| 4 | 617 | 0.36 | 4 | minor improvement, still limited |
| **8** | **309** | **0.18** | **8** | **v5 RECOMMENDED** |
| 16 | 154 | 0.09 | 16 | acceptable but more Coff |
| 32 | 77 | 0.04 | 32 | overkill, eats LSB ratio |

Note: Coff scales with W, so the trade-off is:
- Larger W → lower Ron (better LSB) but higher Coff (LSB cap effectively
  smaller when bit is "off")
- Sweet spot: W=8, Ron=309 Ω, Coff=8 fF → effective LSB cap 20-8 = 12 fF
  (60% of nominal, but resolvable)

### v5 alternative: hierarchical cv-array

Use a unary-coded array of 16 identical 80-fF caps for the high-significance
bits, plus a binary-weighted bottom array of 4 bits (20, 40, 80, 160 fF).
This removes the b6→b7 monotonicity glitch we see in v2 (where MSB=LSB,
non-monotonic at code 127→128). Effort: 1 cell-layout iteration.

## Real issue 3 — Vfo startup rails to VDPWR

### Problem

Simulation of VDPWR ramp 0 → 1.8 V over 100 µs shows:
- VDPWR follows the ramp linearly
- Vfo (OTA output) reaches 1.8 V at t=100 µs and stays there
- V1 reaches 1.75 V

Expected: Vfo settles at mid-rail ~0.92 V via the feedback path (Rfb to
Vbmid). Instead it's stuck at VDPWR.

### Diagnosis

The diff-pair OTA at startup has both inputs at the same potential (vin_p
and Vfo both near 0 V before bias is established). The differential output
fo1 is undefined; current mirror XMp2 inherits this and Vfo may latch
to VDPWR via XMp2's drain current saturation.

### Bring-up procedure

1. Apply Vbn = 0 V (tail current OFF)
2. Apply VDPWR = 1.8 V (ramp 100 µs is fine)
3. Wait 1 ms for analog block to settle DC-wise
4. Ramp Vbn 0 → 0.70 V over 1 ms (slowly engage the tail current)
5. Wait 10 ms for Vfo to settle
6. Confirm Vfo ≈ 0.92 V via DC probe before starting cv-array sweep

If Vfo doesn't settle to 0.92 V after this sequence:
- Power cycle and try again (sometimes the OTA settles to a different
  point depending on initial conditions)
- Try a small step on Vbn after Vfo measurement to nudge out of latch

### v5 fix

Add a 5 µA bias current source to Vfo (from VDPWR, mirrored from Vbn) so
that Vfo always has a defined DC operating point. ~2 transistors added.

## Repeatable bench protocol for Δf vs ε sweep

```
1. Power up per the "Bring-up procedure" above
2. Set cv = 00000000 (all bits off, ε = 0)
3. Sweep VNA 1.5 GHz → 7 GHz, 1801 points, IFBW = 10 kHz
4. Locate peak (should be at f₀ ≈ 4.6 GHz). Record f₀ and FWHM.
5. For cv-code in [4, 8, 16, 32, 64]:  // b2 through b6
     a. Set cv bits
     b. Wait 100 µs for cv-array settle
     c. Re-sweep VNA, locate the 2 peaks
     d. Record f_low, f_high, Δf
6. Fit Δf² = Δf₀² + a² · ε
7. Report κ_eff = a/(2·f₀), Δf₀, R²
```

The single-bit codes b2..b6 give 5 data points spanning 16× in ε
(0.022 to 0.352). Adding combination codes (b2+b3, b3+b4, etc.) gives
more data points for the fit but isn't strictly needed for R² > 0.99.
