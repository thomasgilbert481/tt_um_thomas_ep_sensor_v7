"""Faster optimization: sweep eps inside ngspice .control block (single run per CT1_extra)."""
import subprocess, os, re, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v8_fast_opt"

DECK_BASE = """
.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

Vin     v_vna    GND  AC 1
R_VNA   v_vna    v_pad1in 50
L_BOND1 v_pad1in v_pad1n  1.5e-9
R_BOND1 v_pad1n  v_pad1n2 0.05
C_PAD1  v_pad1n2 GND      125e-15
R_chip1 v_pad1n2 V1       0.5

L1 V1 nL1 1.351e-9
R1 nL1 0 5.0
C_T1 V1 GND  {ct1}p
C_SRF1 V1 GND 0.18e-12

L2 V2_in nL2 1.351e-9
R2 nL2 0 5.0
C_T2 V2_in GND 0.836e-12
C_SRF2 V2_in GND 0.18e-12

K_M12 L1 L2 -0.032

E_buf Vbuf 0 V1 0 1.0

Cc      Vbuf    V2_in   1.398e-12

.param eps_val=0
Ceps    V1     V2_in   'max(2*1.845e-12*eps_val, 1e-21)'

R_chip2 V2_in  v_pad2n  0.5
C_PAD2  v_pad2n GND    125e-15
L_BOND2 v_pad2n v_pad2  1.5e-9
R_load  v_pad2  GND     50

.control
let i = 0
foreach eps {EPSILON_LIST}
  alterparam eps_val=$eps
  reset
  ac dec 8000 0.5e9 5e9
  let v2mag = abs(v(V2_in))
  let v1mag = abs(v(V1))
  wrdata {workdir}/eps_$i_ct1.dat frequency v1mag v2mag
  let i = i + 1
end
quit
.endc
.end
"""


def find_peaks(freqs, mag, min_prom=0.005, min_height_frac=0.1):
    peaks = []
    threshold = mag.max() * min_height_frac
    for i in range(5, len(mag)-5):
        if mag[i] <= threshold: continue
        if not (mag[i] > mag[i-1] and mag[i] > mag[i+1]): continue
        if not (mag[i] >= mag[i-3] and mag[i] >= mag[i+3]): continue
        window = mag[max(0,i-30):min(len(mag),i+30)]
        if mag[i] - window.min() < min_prom: continue
        peaks.append((freqs[i], mag[i]))
    if not peaks: return []
    clustered = [peaks[0]]
    for p in peaks[1:]:
        if abs(p[0] - clustered[-1][0]) < 50e6:
            if p[1] > clustered[-1][1]: clustered[-1] = p
        else:
            clustered.append(p)
    return clustered


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    eps_values = list(np.logspace(np.log10(0.005), np.log10(0.8), 30))
    eps_str = " ".join(f"{e:.6f}" for e in eps_values)

    # Sweep CT1_extra from 0 to 1.5 pF
    ct1_extras = [0.0, 0.1, 0.2, 0.3, 0.39, 0.45, 0.5, 0.6, 0.8, 1.0]
    summary = []

    for ct1_idx, ct1_extra in enumerate(ct1_extras):
        ct1_total = 1.845 + ct1_extra
        beta = (ct1_total / (0.836 + 1.398)) ** 0.5
        print(f"\n=== CT1_extra={ct1_extra:.2f} pF, CT1_total={ct1_total:.3f} pF, β={beta:.4f} ===")

        deck = DECK_BASE.replace("{ct1}", f"{ct1_total*1e-12:.4e}".replace("e-12", "e-12").replace("0p", "p"))
        deck = deck.replace("{ct1}p", f"{ct1_total:.4f}p")
        deck = deck.replace("{EPSILON_LIST}", eps_str)
        deck = deck.replace("{workdir}", WORKDIR + f"/ct1_{ct1_idx:02d}")
        os.makedirs(WORKDIR + f"/ct1_{ct1_idx:02d}", exist_ok=True)

        deck_path = f"{WORKDIR}/deck_ct1_{ct1_idx:02d}.spice"
        with open(deck_path, 'w') as f:
            f.write(deck)

        result = subprocess.run([NGSPICE, "-b", deck_path],
                                capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(f"FAILED: {result.stderr[:500]}")
            continue

        # Parse all eps_$i.dat files in this CT1 dir
        results = []
        for i, eps in enumerate(eps_values):
            dat = f"{WORKDIR}/ct1_{ct1_idx:02d}/eps_{i}_ct1.dat"
            if not os.path.exists(dat):
                continue
            try:
                arr = np.loadtxt(dat)
                if arr.ndim == 1: arr = arr.reshape(1, -1)
                freq = arr[:, 0]
                v2 = arr[:, 6] if arr.shape[1] >= 7 else arr[:, 4]
                pks = find_peaks(freq, v2)
                if len(pks) < 2:
                    df = 0
                else:
                    pf = sorted(p[0] for p in pks)
                    df = pf[-1] - pf[0]
                results.append({"eps": eps, "df": df, "n": len(pks)})
            except Exception as e:
                continue

        # Slope in Zhao
        in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
        if len(in_w) >= 2:
            log_eps = np.array([np.log10(r["eps"]) for r in in_w])
            log_df = np.array([np.log10(r["df"]) for r in in_w])
            slope, intercept = np.polyfit(log_eps, log_df, 1)
            pred = slope*log_eps + intercept
            ss_tot = np.sum((log_df - log_df.mean())**2)
            r2 = 1 - np.sum((log_df - pred)**2)/ss_tot if ss_tot > 0 else 0
            in_w_count = len(in_w)
            print(f"  Zhao window: {in_w_count} resolved pts, slope={slope:.4f}, R²={r2:.4f}")
            # Also check ε=0 (or smallest)
            min_eps_r = min(results, key=lambda r: r["eps"])
            print(f"  smallest ε={min_eps_r['eps']:.5f}: Δf={min_eps_r['df']/1e6:.1f}MHz, n_peaks={min_eps_r['n']}")
            summary.append({"ct1_extra": ct1_extra, "beta": beta, "slope": slope, "r2": r2, "n_zhao": in_w_count})
        else:
            print(f"  Only {len(in_w)} resolved in Zhao window")
            summary.append({"ct1_extra": ct1_extra, "beta": beta, "slope": None, "r2": None, "n_zhao": len(in_w)})

    print("\n=== Summary ===")
    print(f"{'CT1_extra':>10} {'β':>7} {'slope':>8} {'R²':>7} {'n_zhao':>7}")
    for s in summary:
        s_str = f"{s['slope']:.4f}" if s['slope'] is not None else "N/A"
        r_str = f"{s['r2']:.4f}" if s['r2'] is not None else "N/A"
        print(f"{s['ct1_extra']:10.3f} {s['beta']:7.4f} {s_str:>8} {r_str:>7} {s['n_zhao']:7d}")

    with open(f"{WORKDIR}/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
