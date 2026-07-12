"""
imbalance_visualize.py - diagnostic sheets for rotor-imbalance files.

One sheet per file, 6 panels:
  (1) speed profile + plateaus (speed) / load-sweep windows (torque); the headline
      window (strongest 1x) is boxed in red;
  (2) vibration spectrogram of the dominant radial axis (1x band follows fr);
  (3) radial waveform zoom (~4 revolutions - the 1x wobble is visible);
  (4) full radial spectrum: 1x / 2x / 3x, the 50 Hz resonance line, noise floor;
  (5) 1x zoom: fr marker + local floor -> the self-sufficient 1x SNR;
  (6) CONTROL: radial R1x vs axial c4 1x (axial must stay low), and - in torque -
      R1x vs slip across the file (load-independence).

Place in the Rotor_Unbalance folder next to health_baseline.py and imbalance_analyze.py.
  python imbalance_visualize.py            - all files
  python imbalance_visualize.py 3000       - only files whose name contains "3000"
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
import imbalance_analyze as ib
FS = hb.FS
RESONANCE_HZ = ib.RESONANCE_HZ

def spec_db(sig):
    x = (sig - sig.mean()) * np.hanning(len(sig)); sp = np.abs(np.fft.rfft(x)); sp[0] = 0
    f = np.fft.rfftfreq(len(x), 1 / FS); return f, 20 * np.log10(sp / (sp.max() + 1e-12) + 1e-12)

def noise_floor(f, spd, lo, hi):
    m = (f >= lo) & (f <= hi)
    return float(np.median(spd[m])) if m.any() else np.nan

def windows_of(path):
    """Return (X, ch, t, rpm, proto, wins). wins: list of dicts per analysis window."""
    fn = os.path.basename(path)
    X = hb.load_clean(path); ch = hb.classify(X)
    kp = X[:, ch["keyphase"]]
    t, rpm = hb.instantaneous_rpm(kp)
    plateaus = hb.detect_plateaus(t, rpm)
    proto = hb.protocol_of(fn)
    cur, vib = ch["current"], ch["vibration"]
    wins = []
    if proto == "speed":
        for (t0, t1, rp) in plateaus:
            t1c = min(t1, t0 + hb.MAX_WIN_SEC)
            met = ib.metrics_on_window(X[int(t0 * FS):int(t1c * FS)], cur, vib, rp)
            wins.append(dict(ts=t0, te=t1c, rpm=rp, met=met))
    else:
        if plateaus:
            t0, t1, _ = max(plateaus, key=lambda p: p[1] - p[0])
        else:
            t0, t1 = t[0], t[-1]
        ts = t0
        while ts + ib.WIN_SEC <= t1 + 1e-6:
            m = (t >= ts) & (t < ts + ib.WIN_SEC)
            rp = float(np.median(rpm[m])) if m.sum() >= 6 else np.nan
            if not np.isnan(rp):
                met = ib.metrics_on_window(X[int(ts * FS):int((ts + ib.WIN_SEC) * FS)], cur, vib, rp)
                wins.append(dict(ts=ts, te=ts + ib.WIN_SEC, rpm=rp, met=met))
            ts += ib.STEP_SEC
    return X, ch, t, rpm, proto, wins

def draw_sheet(path):
    fn = os.path.basename(path)
    X, ch, t, rpm, proto, wins = windows_of(path)
    if not wins:
        print("   no windows:", fn); return None
    vib = ch["vibration"]
    clean = [w for w in wins if not (w["met"]["f1_on_res"] or w["met"]["fr_on_res"]
                                     or w["met"]["f1_in_1x"] or w["met"]["low_speed_em"])]
    head = max(clean or wins, key=lambda w: w["met"]["R1x"])  # strongest CLEAN 1x window
    i0, i1 = int(head["ts"] * FS), int(head["te"] * FS)
    met = head["met"]; fr = met["fr"]; f1 = met["f1"]
    dom = vib[0] if met["dom_radial"] == "c2" else vib[1]     # dominant radial axis idx
    Vw = X[i0:i1, dom]

    fig = plt.figure(figsize=(16, 11)); gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.22)

    # (1) speed profile + windows
    ax = fig.add_subplot(gs[0, 0]); ax.plot(t, rpm, lw=0.5, color="#333")
    for w in wins:
        ax.axvspan(w["ts"], w["te"], color="#2ca02c", alpha=0.10, lw=0)
    ax.axvspan(head["ts"], head["te"], color="none", ec="#d62728", lw=2)
    ax.set(title="(1) Speed + analysis windows (green=window, red=headline)",
           xlabel="time, s", ylabel="rpm")
    ax.legend(handles=[Patch(fc="#2ca02c", alpha=0.3, label="analysis window"),
                       Patch(fc="none", ec="#d62728", label="headline (max 1x)")], fontsize=8)

    # (2) vibration spectrogram of the dominant radial axis
    ax = fig.add_subplot(gs[0, 1])
    Vs = X[:, dom]; nper = 8192
    fsg, tsg, Sxx = spectrogram(Vs - Vs.mean(), fs=FS, nperseg=nper, noverlap=nper // 2, scaling="spectrum")
    band = fsg <= 70; Sdb = 10 * np.log10(Sxx[band] + 1e-12)
    ax.pcolormesh(tsg, fsg[band], Sdb, shading="auto", cmap="magma",
                  vmin=np.percentile(Sdb, 40), vmax=np.percentile(Sdb, 99.9))
    ax.axhline(RESONANCE_HZ, color="cyan", ls="--", lw=0.8, alpha=0.7)
    ax.axvline(head["ts"], color="cyan", lw=1.2); ax.axvline(head["te"], color="cyan", lw=1.2)
    ax.set(title=f"(2) Vibration spectrogram {met['dom_radial']} (cyan — headline, 50 Hz)",
           xlabel="time, s", ylabel="Hz", ylim=(0, 70))

    # (3) radial waveform zoom (~4 revolutions)
    ax = fig.add_subplot(gs[1, 0])
    z = int(min(4.0 / max(fr, 1.0) * FS, len(Vw)))
    tt = np.arange(z) / FS * 1000.0
    ax.plot(tt, Vw[:z] - Vw[:z].mean(), lw=1.0, color="#6a3d9a")
    ax.set(title=f"(3) Radial waveform {met['dom_radial']} (~4 rev, fr={fr:.1f} Hz)",
           xlabel="time, ms", ylabel="vib (rel.)"); ax.grid(alpha=0.3)

    # (4) full radial spectrum: 1x/2x/3x, 50 Hz resonance, floor
    ax = fig.add_subplot(gs[1, 1]); f, spd = spec_db(Vw); mf = f <= 160
    ax.plot(f[mf], spd[mf], lw=0.7, color="#6a3d9a")
    for h, lab, col in zip((1, 2, 3), ("1x", "2x", "3x"), ("#d62728", "#ff7f0e", "#2ca02c")):
        ax.axvline(h * fr, color=col, ls=":", lw=0.9); ax.text(h * fr, 2, lab, ha="center", fontsize=7, color=col)
    ax.axvline(RESONANCE_HZ, color="red", ls="--", lw=1.1)
    ax.text(RESONANCE_HZ, -6, "50 Hz res.", fontsize=7, color="red", rotation=90, va="top")
    fl = noise_floor(f, spd, 60, 150)
    ax.axhline(fl, color="#333", ls="--", lw=0.8, alpha=0.6, label=f"noise floor ≈ {fl:.0f} dB")
    ax.set(title="(4) Radial spectrum: 1x/2x/3x and 50 Hz resonance", xlabel="Hz",
           ylabel="dB rel. max", ylim=(-95, 5)); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # (5) 1x zoom: fr marker + local floor -> SNR
    ax = fig.add_subplot(gs[2, 0])
    span = max(6 * fr / 8.0, 4.0); m5 = (f >= fr - span) & (f <= fr + span)
    ax.plot(f[m5], spd[m5], lw=0.9, color="#6a3d9a")
    ax.axvline(fr, color="#d62728", ls="--", lw=1); ax.text(fr, 1, "fr (1x)", ha="center", fontsize=8, color="#d62728")
    half = max(3 * (f[1] - f[0]), 0.10 * fr)
    sh = (((f >= fr - 3 * half) & (f < fr - half)) | ((f > fr + half) & (f <= fr + 3 * half)))
    if sh.any():
        ax.axhline(float(np.median(spd[sh])), color="#333", ls=":", lw=0.9, alpha=0.7, label="local floor")
    ax.set(title=f"(5) 1x zoom: SNR₁ₓ = {met['onex_snr_dB']:.0f} dB",
           xlabel="Hz", ylabel="dB rel. max", ylim=(-95, 5)); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # (6) control: radial vs axial 1x; in torque also R1x vs slip
    ax = fig.add_subplot(gs[2, 1])
    if proto == "torque" and len(wins) >= 3:
        sl = [w["met"]["slip"] for w in wins]; r1 = [w["met"]["R1x"] for w in wins]
        order = np.argsort(sl)
        ax.plot(np.array(sl)[order], np.array(r1)[order], "o-", ms=5, color="#1f77b4", label="R1x vs slip")
        ax.axhline(np.mean(r1), color="#2ca02c", ls="--", lw=0.9, label="mean (flat = rotor)")
        ax.set(title="(6) Control: R1x vs slip (flat = load-independent)",
               xlabel="slip s, % (load)", ylabel="R1x"); ax.set_yscale("log")
        ax.legend(fontsize=8)
    else:
        labels = ["radial\nR1x", "axial\nc4 1x"]; vals = [met["R1x"], met["axial_1x"]]
        ax.bar(labels, vals, color=["#d62728", "#2ca02c"], edgecolor="k")
        ax.set(title=f"(6) Control: radial vs axial 1x (axial/radial={met['axial_ratio']:.2f})",
               ylabel="1x amplitude"); ax.set_yscale("log")
    ax.grid(alpha=0.3, axis="y")

    on_res = "  [ON RESONANCE]" if (met["f1_on_res"] or met["fr_on_res"]) else ""
    on_res += "  [f1 IN 1x BIN]" if met["f1_in_1x"] else ""
    on_res += "  [LOW SPEED - EM MASKS 1x]" if met["low_speed_em"] else ""
    on_res += f"  sep={met['sep_bins']:.1f} bins" 
    fig.suptitle(f"{fn}  |  {proto}  |  headline {head['rpm']:.0f} rpm, fr={fr:.2f} Hz, "
                 f"f1={f1:.2f} Hz, s={met['slip']:.2f}%, R1x={met['R1x']:.4g}, "
                 f"SNR₁ₓ={met['onex_snr_dB']:.0f} dB{on_res}",
                 fontsize=11, fontweight="bold", y=0.995)
    out = os.path.join(SCRIPT_DIR, "ubviz_" + os.path.splitext(fn)[0] + ".png")
    plt.savefig(out, dpi=110, bbox_inches="tight"); plt.close()
    return out

def main():
    mask = sys.argv[1] if len(sys.argv) > 1 else None
    files = sorted(glob.glob(os.path.join(SCRIPT_DIR, "**", "*.csv"), recursive=True))
    files = [f for f in files if re.search(r"\d+Nm", os.path.basename(f))
             and re.search(r"\d+rpm", os.path.basename(f)) and "baseline" not in os.path.basename(f)]
    if mask:
        files = [f for f in files if mask in os.path.basename(f)]
    if not files:
        print("No files found."); return
    print(f"Files: {len(files)}")
    for f in files:
        print("...", os.path.basename(f))
        out = draw_sheet(f)
        if out:
            print("   ->", os.path.basename(out))
    print("Done. Sheets ubviz_*.png are next to the script.")

if __name__ == "__main__":
    main()
