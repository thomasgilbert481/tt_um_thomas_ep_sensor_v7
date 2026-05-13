"""Compare AC spectra at different eps values."""
import numpy as np

files = [(0, "eps=0"), (10, "eps=0.016"), (15, "eps=0.039"),
         (20, "eps=0.080"), (25, "eps=0.241"), (30, "eps=0.6")]
data = []
for i, lbl in files:
    arr = np.loadtxt(f"/tmp/v8_sim/sweep_{i:03d}.dat")
    data.append((lbl, arr))
freq = data[0][1][:,0]

def print_table(col, name):
    print(f"\n--- {name} ---")
    print(f"  Freq (GHz)  " + "  ".join(f"{str(lbl):>10s}" for lbl,_ in files))
    for f_target in [2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.05, 3.1, 3.15, 3.2, 3.3, 3.4, 3.6, 3.8]:
        idx = np.argmin(np.abs(freq - f_target*1e9))
        print(f"   {freq[idx]/1e9:.3f}    ", end="")
        for lbl, arr in data:
            print(f"  {arr[idx, col]:.5f}", end="  ")
        print()

print_table(4, "V(V1) magnitude")
print_table(6, "V(V2_in) magnitude")

# Find local maxima with tighter parameters
def find_peaks(freqs, mag, min_height_frac=0.3, min_prominence=0.005):
    peaks = []
    threshold = mag.max() * min_height_frac
    for i in range(5, len(mag)-5):
        if (mag[i] > mag[i-1] and mag[i] > mag[i+1]
                and mag[i] > mag[i-3] and mag[i] > mag[i+3]
                and mag[i] > threshold):
            # check prominence
            window = mag[max(0,i-100):min(len(mag),i+100)]
            prom = mag[i] - window.min()
            if prom > min_prominence:
                peaks.append((freqs[i], mag[i]))
    return peaks

print("\n\n--- Peak detection (relaxed) ---")
for lbl, arr in data:
    v2 = arr[:, 6]
    peaks = find_peaks(freq, v2, 0.3, 0.005)
    print(f"  {lbl}: {len(peaks)} V2 peaks: " + " ".join(f"({p[0]/1e9:.3f},{p[1]:.4f})" for p in peaks))
