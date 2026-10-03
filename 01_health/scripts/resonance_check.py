"""
resonance_check.py — test of the RIG RESONANCE hypothesis near 50 Hz / 3000 rpm.

Context: in the health baseline the vibration 1x on axis c3 jumps at 3000 rpm far
more than the omega^2 law allows (~x30 for a doubling of speed instead of x4). Two
hypotheses:
  H1 — a mechanical resonance of the structure near ~50 Hz (amplifies 1x when fr
       sweeps into it);
  H2 — plain power-law growth of the imbalance 1x, no resonance.

DECISIVE TEST: a resonance sits at a FIXED frequency regardless of speed, while the 1x
moves with the rotation frequency. The intermediate plateaus of the speed protocol put
the 1x at 24–41 Hz (away from 50). If on those plateaus the c3 spectrum shows a
STATIONARY peak near ~50 Hz (separate from the 1x), and at 3000 rpm the 1x drives into
it and balloons — that is H1.

Run from this folder:  python resonance_check.py
  data:    ../data/**/health_*.csv
  module:  ../../common/health_baseline.py
  output:  ../outputs/

Outputs:
  resonance_c3_spectra_overlay.png  — c3 spectra from all speeds overlaid
  resonance_transmissibility.png    — 1x vs fr (log-log) + omega^2 reference, and 1x/fr^2
  console — the verdict: is there a fixed peak near 50 Hz, and by how much does the
            3000 rpm point exceed the power-law extrapolation.
"""
import os, sys, glob, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SECTION_DIR = os.path.dirname(SCRIPT_DIR)                 # 01_health/
REPO_ROOT = os.path.dirname(SECTION_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "common"))     # the single shared module
import health_baseline as hb
DATA_DIR = os.path.join(SECTION_DIR, "data")              # raw CSVs (not in the repo)
OUT_DIR = os.path.join(SECTION_DIR, "outputs")            # everything this script writes
os.makedirs(OUT_DIR, exist_ok=True)
FS = hb.FS

RES_BAND = (40.0, 60.0)     # where the fixed resonance peak is searched, Hz
FIXED_TOL = 3.0             # allowed spread of the "fixed" peak position between plateaus, Hz

# --- linear vibration spectrum (Hann window, one-sided) ---
def vib_spectrum(sig):
    w = np.hanning(len(sig)); x = (sig - sig.mean()) * w
    sp = np.abs(np.fft.rfft(x)) * 2.0 / np.sum(w)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    return f, sp

def amp_at(f, sp, fc, half=1.5):
    m = (f >= fc - half) & (f <= fc + half)
    return float(sp[m].max()) if m.any() else np.nan

def peak_in_band(f, sp, lo, hi, exclude_fc=None, exclude_half=2.5):
    m = (f >= lo) & (f <= hi)
    if exclude_fc is not None:
        m &= ~((f >= exclude_fc - exclude_half) & (f <= exclude_fc + exclude_half))
    if not m.any():
        return np.nan, np.nan
    idx = np.where(m)[0]; k = idx[np.argmax(sp[idx])]
    return f[k], sp[k]

def collect_plateaus():
    """All plateaus of all health files -> list of (rpm, fr, signal slice X, channels)."""
    files = hb.collect_health_files(DATA_DIR)
    if not files:
        print("No health files found under", DATA_DIR); sys.exit(1)
    out = []
    ref_vib = None
    for p in files:
        X = hb.load_clean(p); ch = hb.classify(X)
        if ref_vib is None:
            ref_vib = ch["vibration"]
        t, rpm = hb.instantaneous_rpm(X[:, ch["keyphase"]])
        for (t0, t1, rp) in hb.detect_plateaus(t, rpm):
            t1 = min(t1, t0 + hb.MAX_WIN_SEC)
            seg = X[int(t0 * FS):int(t1 * FS)]
            out.append(dict(rpm=rp, fr=rp / 60.0, seg=seg, vib=ch["vibration"],
                            proto=hb.protocol_of(os.path.basename(p))))
    return out, ref_vib

def pick_primary_radial(plats, vib_idx):
    """The axis whose 1x grows most towards high speed = the main radial axis (c3)."""
    hi = max(plats, key=lambda d: d["rpm"])
    amps = []
    for ci in vib_idx:
        f, sp = vib_spectrum(hi["seg"][:, ci])
        amps.append(amp_at(f, sp, hi["fr"]))
    k = int(np.argmax(amps))
    return vib_idx[k], k, amps

def main():
    plats, vib_idx = collect_plateaus()
    prim, prim_pos, amps_hi = pick_primary_radial(plats, vib_idx)
    labels = ["c2", "c3", "c4"]
    print(f"Vibration channels (columns): {vib_idx} -> {labels}")
    print(f"Main radial axis (max 1x at the highest speed): column {prim} = {labels[prim_pos]}")
    print(f"  1x on the top plateau per axis: " +
          ", ".join(f"{labels[i]}={a:.5f}" for i, a in enumerate(amps_hi)))

    plats = sorted(plats, key=lambda d: d["rpm"])

    # ---------- TEST 1: a fixed peak near 50 Hz on the non-resonant plateaus ----------
    print("\n=== Test 1: stationary peak in the 40–60 Hz band (outside the 1x zone) ===")
    print(f"  {'rpm':>6} {'fr(1x),Hz':>10} {'peak!=1x in 40-60,Hz':>21} {'ampl':>10}")
    fixed_hits = []
    for d in plats:
        f, sp = vib_spectrum(d["seg"][:, prim])
        fc, a = peak_in_band(f, sp, *RES_BAND, exclude_fc=d["fr"])
        # of interest: plateaus where the 1x is NOT inside the resonance band (fr outside 40-60 +/- tol)
        off = not (RES_BAND[0] - 3 <= d["fr"] <= RES_BAND[1] + 3)
        mark = ""
        if off and not np.isnan(fc):
            fixed_hits.append(fc); mark = "  <- fixed?"
        print(f"  {d['rpm']:6.0f} {d['fr']:10.1f} {fc:21.1f} {a:10.5f}{mark}")
    if len(fixed_hits) >= 2:
        med = np.median(fixed_hits); spread = np.ptp(fixed_hits)
        verdict1 = (spread <= FIXED_TOL)
        print(f"  fixed peak: median {med:.1f} Hz, spread {spread:.1f} Hz "
              f"-> {'CONFIRMS a resonance' if verdict1 else 'position drifts (not fixed)'}")
    else:
        verdict1 = None
        print("  not enough non-resonant plateaus for a conclusion")

    # ---------- TEST 2: 1x vs fr, deviation from omega^2 ----------
    print("\n=== Test 2: amplification of the 1x relative to the omega^2 law ===")
    fr = np.array([d["fr"] for d in plats])
    a1 = np.array([amp_at(*vib_spectrum(d["seg"][:, prim]), d["fr"]) for d in plats])
    # reference power law fitted on the LOW speeds (fr < 40 Hz, below the resonance)
    lo = fr < 40
    if lo.sum() >= 3:
        cflog = np.polyfit(np.log(fr[lo]), np.log(a1[lo] + 1e-12), 1)
        slope = cflog[0]
        pred_hi = np.exp(np.polyval(cflog, np.log(fr)))
        amp_factor = a1 / (pred_hi + 1e-12)
        print(f"  power-law slope on the low speeds: {slope:.2f} (omega^2 would give 2.0)")
        print(f"  {'rpm':>6} {'fr':>6} {'1x meas':>9} {'1x law':>9} {'excess x':>11}")
        for i in range(len(fr)):
            tag = "  <-" if amp_factor[i] > 2 else ""
            print(f"  {fr[i]*60:6.0f} {fr[i]:6.1f} {a1[i]:9.5f} {pred_hi[i]:9.5f} {amp_factor[i]:11.1f}{tag}")
        peak_factor = amp_factor.max(); peak_rpm = fr[np.argmax(amp_factor)] * 60
        verdict2 = peak_factor > 3
        print(f"  max excess over the law: x{peak_factor:.1f} at {peak_rpm:.0f} rpm "
              f"-> {'resonant amplification' if verdict2 else 'within power-law growth'}")
    else:
        verdict2 = None; amp_factor = None
        print("  too few points below 40 Hz for a reference law")

    # ---------- Figures ----------
    # (1) c3 spectra overlay
    fig, ax = plt.subplots(figsize=(13, 7))
    cmap = plt.cm.viridis(np.linspace(0, 1, len(plats)))
    for d, c in zip(plats, cmap):
        f, sp = vib_spectrum(d["seg"][:, prim])
        m = f <= 160
        ax.semilogy(f[m], sp[m] + 1e-9, lw=0.8, color=c, alpha=0.8,
                    label=f"{d['rpm']:.0f} rpm (1x={d['fr']:.0f})")
        ax.plot(d["fr"], amp_at(f, sp, d["fr"]) + 1e-9, "o", color=c, ms=5, mec="k", mew=0.4)
    ax.axvspan(RES_BAND[0], RES_BAND[1], color="red", alpha=0.08)
    ax.axvline(50, color="red", ls="--", lw=1, label="suspected resonance ~50 Hz")
    ax.set(xlabel="frequency, Hz", ylabel=f"amplitude {labels[prim_pos]} (rel.)",
           title="Vibration spectra of c3 overlaid across speeds\n"
                 "circle = the 1x of each plateau; looking for a STATIONARY peak near 50 Hz")
    ax.legend(fontsize=7, ncol=2); ax.grid(True, which="both", alpha=0.3)
    plt.tight_layout(); p1 = os.path.join(OUT_DIR, "resonance_c3_spectra_overlay.png")
    plt.savefig(p1, dpi=120); print("\nFigure:", p1)

    # (2) transmissibility
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))
    ax[0].loglog(fr, a1 + 1e-12, "o", ms=6, mec="k", mew=0.4, label="1x measured")
    if lo.sum() >= 3:
        order = np.argsort(fr)
        ax[0].loglog(fr[order], pred_hi[order], "r--", lw=1, label=f"power law x{slope:.1f}")
        ax[0].loglog(fr[order], (a1[lo][0]*(fr/fr[lo][0])**2)[order], "g:", lw=1, label="omega^2 reference")
    ax[0].set(xlabel="fr, Hz", ylabel="1x amplitude", title="1x vs rotation frequency (log-log)")
    ax[0].legend(fontsize=8); ax[0].grid(True, which="both", alpha=0.3)
    comp = a1 / (fr ** 2 + 1e-12)      # compliance ~ peaks at the resonance
    ax[1].plot(fr, comp / np.nanmedian(comp), "o-", ms=5)
    ax[1].axvline(50, color="red", ls="--", lw=1)
    ax[1].set(xlabel="fr, Hz", ylabel="1x/fr^2 (normalised)",
              title="Mechanical compliance 1x/fr^2 (peak = resonance)")
    ax[1].grid(True, alpha=0.3)
    plt.tight_layout(); p2 = os.path.join(OUT_DIR, "resonance_transmissibility.png")
    plt.savefig(p2, dpi=120); print("Figure:", p2)

    # ---------- Verdict ----------
    print("\n" + "=" * 60)
    print("VERDICT:")
    v = []
    if verdict1 is True: v.append("a fixed peak near ~50 Hz IS present")
    elif verdict1 is False: v.append("NO fixed peak")
    if verdict2 is True: v.append("the 1x exceeds omega^2 several-fold near 3000")
    elif verdict2 is False: v.append("1x growth stays within the power law")
    print("  " + "; ".join(v) if v else "  not enough data")
    if verdict1 and verdict2:
        print("  => RIG RESONANCE near ~50 Hz CONFIRMED. The 3000 rpm point cannot be used")
        print("     for a '1x rise vs speed' law — it is resonantly inflated.")
    elif verdict1 is False and verdict2 is False:
        print("  => Resonance NOT confirmed; the jump at 3000 needs another explanation.")
    else:
        print("  => Mixed picture, see the figures (possibly a resonance at the edge of the range).")

if __name__ == "__main__":
    main()
