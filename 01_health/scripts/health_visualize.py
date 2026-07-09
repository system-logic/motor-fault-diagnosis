"""
health_visualize.py - diagnostic sheets for health files.

One sheet per file, 6 panels:
  (1) full speed profile with SHADED plateaus and their rpm labels;
  (2) current spectrogram (time-frequency): plateaus show as f1 bands, noise as background;
  (3) 3-phase current waveform (zoom on the longest plateau);
  (4) full current spectrum on the longest plateau: f1, harmonics, NOISE FLOOR line;
  (5) zoom around f1: broken-bar sideband zone + imbalance current bands 1x;
  (6) vibration spectrum c3: 1x/2x/3x and the 50 Hz resonance, noise floor.

Place next to health_baseline.py in the Health folder. Run:
  python health_visualize.py            - all health files
  python health_visualize.py 3000       - only files whose name contains "3000"
"""
import os, sys, glob, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy.signal import spectrogram

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import health_baseline as hb
FS = hb.FS
RESONANCE_HZ = 50.0

def longest_plateau(plateaus):
    return max(plateaus, key=lambda p: p[1] - p[0]) if plateaus else None

def spec_db(sig):
    x = (sig - sig.mean()) * np.hanning(len(sig))
    sp = np.abs(np.fft.rfft(x)); sp[0] = 0
    f = np.fft.rfftfreq(len(x), 1 / FS)
    return f, 20 * np.log10(sp / (sp.max() + 1e-12) + 1e-12)

def noise_floor_db(f, spd, lo, hi):
    """Robust noise floor = median dB over band [lo,hi] (peaks ignored)."""
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan
    v = spd[m]
    return float(np.median(v))

def draw_sheet(path):
    fname = os.path.basename(path)
    X = hb.load_clean(path); ch = hb.classify(X)
    kp = X[:, ch["keyphase"]]; cur = ch["current"]; vib = ch["vibration"]
    t, rpm = hb.instantaneous_rpm(kp)
    plateaus = hb.detect_plateaus(t, rpm)
    proto = hb.protocol_of(fname)
    A = X[:, cur[0]]                      # phase A current

    p = longest_plateau(plateaus)
    if p is None:
        print("  no plateaus:", fname); return None
    t0, t1, rp = p; t1 = min(t1, t0 + hb.MAX_WIN_SEC)
    i0, i1 = int(t0 * FS), int(t1 * FS)
    Aw = A[i0:i1]
    f1 = hb.f1_of(Aw); n_s = 60 * f1; slip = (n_s - rp) / n_s
    off = 2 * slip * f1; fr = rp / 60.0

    fig = plt.figure(figsize=(16, 11))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1], hspace=0.38, wspace=0.22)

    # ---------- (1) speed profile + plateaus ----------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(t, rpm, lw=0.6, color="#333")
    for k, (a, b, r) in enumerate(plateaus):
        ax1.axvspan(a, b, color="#2ca02c", alpha=0.22, lw=0)
        ax1.text((a + b) / 2, r, f"{r:.0f}", ha="center", va="bottom",
                 fontsize=8, fontweight="bold", color="#1a6b1a")
    ax1.set(title=f"(1) Speed profile — {len(plateaus)} plateaus shaded",
            xlabel="time, s", ylabel="rpm")
    ax1.grid(alpha=0.3)
    ax1.legend(handles=[Patch(facecolor="#2ca02c", alpha=0.3, label="steady plateau")],
               fontsize=8, loc="best")

    # ---------- (2) current spectrogram ----------
    ax2 = fig.add_subplot(gs[0, 1])
    nper = 8192
    fsg, tsg, Sxx = spectrogram(A - A.mean(), fs=FS, nperseg=nper,
                                noverlap=nper // 2, scaling="spectrum")
    band = fsg <= 70
    Sdb = 10 * np.log10(Sxx[band] + 1e-12)
    im = ax2.pcolormesh(tsg, fsg[band], Sdb, shading="auto", cmap="magma",
                        vmin=np.percentile(Sdb, 40), vmax=np.percentile(Sdb, 99.9))
    for (a, b, r) in plateaus:
        ax2.axvline(a, color="cyan", lw=0.6, alpha=0.7)
        ax2.axvline(b, color="cyan", lw=0.6, alpha=0.7)
    ax2.set(title="(2) Current spectrogram: f1 per plateau (cyan — plateau borders)",
            xlabel="time, s", ylabel="frequency, Hz", ylim=(0, 70))
    fig.colorbar(im, ax=ax2, label="dB", pad=0.01)

    # ---------- (3) 3-phase current waveform ----------
    ax3 = fig.add_subplot(gs[1, 0])
    ncyc = 3.0 / max(f1, 1.0)                      # ~3 periods
    z = int(ncyc * FS)
    tt = np.arange(z) / FS * 1000                  # ms
    for ci, lab, col in zip(cur, ("A", "B", "C"), ("#d62728", "#2ca02c", "#1f77b4")):
        ax3.plot(tt, X[i0:i0 + z, ci], lw=1.0, color=col, label=f"phase {lab}")
    ax3.set(title=f"(3) 3-phase currents (~3 periods zoom, f1={f1:.1f} Hz)",
            xlabel="time, ms", ylabel="current (rel.)")
    ax3.grid(alpha=0.3); ax3.legend(fontsize=8, ncol=3, loc="upper right")

    # ---------- (4) full current spectrum + noise floor ----------
    ax4 = fig.add_subplot(gs[1, 1])
    f, spd = spec_db(Aw)
    m = f <= 6 * f1 + 20
    ax4.plot(f[m], spd[m], lw=0.7, color="#1f77b4")
    for k in range(1, 7):
        fk = k * f1
        if fk <= f[m].max():
            ax4.axvline(fk, color="#ff7f0e", ls=":", lw=0.8)
            ax4.text(fk, 2, f"{k}f1", ha="center", fontsize=7, color="#cc6600")
    floor = noise_floor_db(f, spd, 1.5 * f1, 6 * f1)
    ax4.axhline(floor, color="#d62728", ls="--", lw=1,
                label=f"noise floor ≈ {floor:.0f} dB")
    ax4.set(title="(4) Current spectrum on plateau: f1 and harmonics above noise floor",
            xlabel="frequency, Hz", ylabel="dB rel. f1", ylim=(-90, 5))
    ax4.grid(alpha=0.3); ax4.legend(fontsize=8, loc="upper right")

    # ---------- (5) zoom around f1 ----------
    ax5 = fig.add_subplot(gs[2, 0])
    span = max(3 * off, 4 * fr, 4.0)
    m5 = (f >= f1 - span) & (f <= f1 + span)
    ax5.plot(f[m5], spd[m5], lw=0.9, color="#1f77b4")
    ax5.axvline(f1, color="k", ls="-", lw=0.8); ax5.text(f1, 1, "f1", ha="center", fontsize=8)
    # broken-bar sideband zone
    for sgn in (-1, 1):
        ax5.axvspan(f1 + sgn * off - 0.06 * off, f1 + sgn * off + 0.06 * off,
                    color="#d62728", alpha=0.18, lw=0)
        ax5.axvline(f1 + sgn * off, color="#d62728", ls="--", lw=0.9)
        ax5.axvline(f1 + sgn * fr, color="#2ca02c", ls=":", lw=0.9)
    floor5 = noise_floor_db(f, spd, f1 - span, f1 + span)
    ax5.axhline(floor5, color="#d62728", ls="--", lw=0.8, alpha=0.6)
    ax5.set(title=f"(5) f1 zoom: red — broken-bar bands 2s·f1={off:.2f} Hz, "
                  f"green — imbalance 1× f1±fr", xlabel="frequency, Hz",
            ylabel="dB rel. f1", ylim=(-90, 5))
    ax5.grid(alpha=0.3)
    ax5.legend(handles=[Patch(facecolor="#d62728", alpha=0.3, label="broken-bar band zone"),
                        Patch(facecolor="#2ca02c", alpha=0.3, label="imbalance bands 1×")],
               fontsize=8, loc="upper right")

    # ---------- (6) vibration spectrum c3 ----------
    ax6 = fig.add_subplot(gs[2, 1])
    # c3 = axis with the most energy on this plateau (main radial axis)
    c3 = vib[int(np.argmax([X[i0:i1, ci].std() for ci in vib]))]
    fv, spv = spec_db(X[i0:i1, c3])
    mv = fv <= 160
    ax6.plot(fv[mv], spv[mv], lw=0.6, color="#6a3d9a")
    for hh, lab, col in zip((1, 2, 3), ("1×", "2×", "3×"), ("#d62728", "#ff7f0e", "#2ca02c")):
        ax6.axvline(hh * fr, color=col, ls=":", lw=0.9)
        ax6.text(hh * fr, 2, lab, ha="center", fontsize=7, color=col)
    ax6.axvline(RESONANCE_HZ, color="red", ls="--", lw=1.2)
    ax6.text(RESONANCE_HZ, -6, "50 Hz resonance", fontsize=7, color="red", rotation=90, va="top")
    floor6 = noise_floor_db(fv, spv, 60, 150)
    ax6.axhline(floor6, color="#333", ls="--", lw=0.8, alpha=0.6,
                label=f"noise floor ≈ {floor6:.0f} dB")
    ax6.set(title="(6) Vibration spectrum c3: 1×/2×/3× and 50 Hz resonance",
            xlabel="frequency, Hz", ylabel="dB rel. max", ylim=(-90, 5))
    ax6.grid(alpha=0.3); ax6.legend(fontsize=8, loc="upper right")

    fig.suptitle(f"{fname}  |  {proto}  |  longest plateau {rp:.0f} rpm, "
                 f"f1={f1:.2f} Hz, s={slip*100:.2f}%, 2s·f1={off:.2f} Hz",
                 fontsize=12, fontweight="bold", y=0.995)
    out = os.path.join(SCRIPT_DIR, "viz_" + os.path.splitext(fname)[0] + ".png")
    plt.savefig(out, dpi=110, bbox_inches="tight")
    plt.close()
    return out

def main():
    mask = sys.argv[1] if len(sys.argv) > 1 else None
    files = hb.collect_health_files(SCRIPT_DIR)
    if mask:
        files = [f for f in files if mask in os.path.basename(f)]
    if not files:
        print("No files found (mask:", mask, ")"); return
    print(f"Files to process: {len(files)}")
    for f in files:
        print("...", os.path.basename(f))
        out = draw_sheet(f)
        if out:
            print("    ->", os.path.basename(out))
    print("Done. Sheets viz_*.png are next to the script.")

if __name__ == "__main__":
    main()
