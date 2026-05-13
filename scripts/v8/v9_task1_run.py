"""Run task 1 cv sweep with NMOS-only OTA. Single shot per eps, no exploration sweep."""
import subprocess, os, re, json
import numpy as np

NGSPICE = "/foss/tools/ngspice/bin/ngspice"
WORKDIR = "/tmp/v9_task1_run"
DECK_FILE = "/foss/designs/tt_um_thomas_ep_sensor_v7/scripts/v8/v9_task1_fast.spice"

CV_WEIGHTS_FF = [20, 41, 82, 164, 328, 656, 1312, 1312]
C_T1_FF = 1845

def enumerate_eps():
    eps_set = set()
    for bits in range(256):
        s = sum(CV_WEIGHTS_FF[i] for i in range(8) if bits & (1 << i))
        eps_set.add(round(s / (2 * C_T1_FF), 6))
    return sorted(eps_set)


def run_one(eps, run_id):
    out_dat = f"{WORKDIR}/eps_{run_id:03d}.dat"
    if os.path.exists(out_dat): return out_dat
    with open(DECK_FILE) as f:
        deck = f.read()
    deck = re.sub(r'\.param\s+eps\s*=\s*\S+', f'.param eps={eps}', deck)
    deck = deck.replace('.end',
        f"""
.control
op
echo VFO_DC=:
print v(Vfo)
print v(V1)
print v(vin_p)
ac dec 1500 1e9 5e9
let v1mag = abs(v(V1))
let v2mag = abs(v(V2_in))
let vfom = abs(v(Vfo))
wrdata {out_dat} frequency v1mag v2mag vfom
quit
.endc
.end""")
    deck_path = f"{WORKDIR}/eps_{run_id:03d}.spice"
    with open(deck_path, 'w') as f: f.write(deck)
    r = subprocess.run([NGSPICE, "-b", deck_path], capture_output=True, text=True, timeout=60)
    if not os.path.exists(out_dat):
        return None
    # Try to extract Vfo DC
    m = re.search(r"v\(vfo\) = ([\d.\-e+]+)", r.stdout)
    if m:
        vfo_dc = float(m.group(1))
        if run_id == 0:
            print(f"DC: Vfo={vfo_dc:.3f}V")
    return out_dat


def find_peaks(freq, mag):
    peaks = []
    for i in range(2, len(mag)-2):
        if mag[i] > mag[i-1] and mag[i] > mag[i+1] and mag[i] >= mag[i-2] and mag[i] >= mag[i+2]:
            peaks.append((freq[i], mag[i]))
    return peaks


def filter_peaks(peaks, hf=0.15, sep=80e6):
    if not peaks: return []
    mx = max(p[1] for p in peaks)
    f = sorted([p for p in peaks if p[1] >= hf*mx], key=lambda p: p[0])
    if not f: return []
    out = [f[0]]
    for p in f[1:]:
        if p[0] - out[-1][0] < sep:
            if p[1] > out[-1][1]: out[-1] = p
        else: out.append(p)
    return out


def measure(dat):
    arr = np.loadtxt(dat)
    if arr.ndim == 1: arr = arr.reshape(1, -1)
    freq = arr[:, 0]
    # 4 columns: freq, v1m, v2m, vfom — but wrdata writes 8 cols (freq+val per var)
    # cols: 0=freq, 1=v1m_freq, 2=v1m, 3=v2m_freq, 4=v2m, 5=vfom_freq, 6=vfom
    if arr.shape[1] >= 7:
        v1 = arr[:, 2]
        v2 = arr[:, 4]
        vfo = arr[:, 6]
    else:
        v1 = arr[:, 1]
        v2 = arr[:, 2] if arr.shape[1] > 2 else np.zeros_like(freq)
        vfo = np.zeros_like(freq)
    p1 = filter_peaks(find_peaks(freq, v1))
    p2 = filter_peaks(find_peaks(freq, v2))
    peaks = p1 if len(p1) >= 2 else (p2 if len(p2) >= 2 else p1)
    df = 0
    if len(peaks) >= 2:
        pf = sorted(p[0] for p in peaks)
        df = pf[-1] - pf[0]
    return df, len(p1), len(p2)


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    eps_list = [e for e in enumerate_eps() if e == 0 or (0.005 <= e <= 0.3)]
    print(f"Running cv sweep with NMOS-only OTA, {len(eps_list)} ε values")
    results = []
    for i, eps in enumerate(eps_list):
        dat = run_one(eps, i)
        if dat:
            df, n1, n2 = measure(dat)
            results.append({"eps": eps, "df": df, "n_v1": n1, "n_v2": n2})
        if i % 10 == 0:
            print(f"  [{i}/{len(eps_list)}] eps={eps:.5f}")

    # Analyze
    r0 = next((r for r in results if r["eps"] == 0.0), None)
    if r0:
        print(f"\nε=0: n_v1={r0['n_v1']}, n_v2={r0['n_v2']}, Δf={r0['df']/1e6:.1f}MHz")
        ep_pass = r0['n_v2'] == 1 and r0['df'] < 100e6

    in_w = [r for r in results if 0.031 <= r["eps"] <= 0.25 and r["df"] > 0]
    print(f"\nResolved in [0.031, 0.25]: {len(in_w)}")
    if len(in_w) >= 2:
        le = np.array([np.log10(r["eps"]) for r in in_w])
        ld = np.array([np.log10(r["df"]) for r in in_w])
        slope, ic = np.polyfit(le, ld, 1)
        pred = slope*le + ic
        sst = np.sum((ld - ld.mean())**2)
        r2 = 1 - np.sum((ld-pred)**2)/sst if sst > 0 else 0
        print(f"Slope = {slope:.4f}, R² = {r2:.4f}")
        # Pass criteria
        results_summary = {
            "n_resolved": len(in_w),
            "slope": slope,
            "r2": r2,
            "ep_single_peak": (r0['n_v2'] == 1) if r0 else None,
            "df_at_eps0_MHz": r0['df']/1e6 if r0 else None,
        }
        # Pass status
        print(f"\nPass: n_resolved >= 11 → {'YES' if len(in_w) >= 11 else 'NO'}")
        print(f"Pass: slope in [0.45, 0.55] → {'YES' if 0.45 <= slope <= 0.55 else 'NO'}")
        print(f"Pass: R² >= 0.95 → {'YES' if r2 >= 0.95 else 'NO'}")
        print(f"Pass: EP single peak (n_v2=1 at ε=0) → {'YES' if (r0 and r0['n_v2'] == 1) else 'NO'}")
        with open(f"{WORKDIR}/summary.json", 'w') as f:
            json.dump(results_summary, f, indent=2)


if __name__ == "__main__":
    main()
