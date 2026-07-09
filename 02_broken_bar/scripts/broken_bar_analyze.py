"""
broken_bar_analyze.py - clean broken-rotor-bar analysis (section 2, stage 2).

Follows broken_bar_catalog.md. Processes ALL broken-bar files (both subfolders); the
healthy reference is taken from the health baseline table.

Key difference from the health logic (recon finding):
  - speed: a plateau = an operating point (slip is stable within the plateau);
  - torque: the plateau must NOT be taken whole (load sweeps -> slip drifts -> the band
    smears). We segment by SLIP: sliding windows where slip ~ const; each stable window
    is a point on the load axis. The per-file headline point is the MAX-load window
    (max slip).

Indicators (both, as decided - deep analysis):
  - rise (naive): band level - healthy floor of the same regime/protocol (health);
  - snr (self-sufficient): band prominence over its shoulders in the same spectrum.

Comb k=1,2,3: bands at f1*(1 +/- 2ks).

Run: place next to health_baseline.py in the Broken_Bar folder. Point HEALTH_CSV at
the health table (or let the script search parent folders for it).
  python broken_bar_analyze.py            - all files in the script folder
"""
import os, sys, glob, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import health_baseline as hb
FS = hb.FS

# ---- segmentation / analysis parameters ----
WIN_SEC = 8.0            # analysis window (df = 1/8 = 0.125 Hz)
STEP_SEC = 2.0
KMAX = 3                 # comb harmonics k=1..KMAX
STAB_FACTOR = 0.25       # window is stable if smear < STAB_FACTOR*off_2s (and < df)
RESOLVE_BINS = 3         # band is resolvable if off_2s > RESOLVE_BINS*df

# health table (for the naive indicator). If empty - search for it.
HEALTH_CSV = ""

def find_health_csv():
    if HEALTH_CSV and os.path.exists(HEALTH_CSV):
        return HEALTH_CSV
    name = "health_baseline_plateaus.csv"
    # recursive - only inside the script folder (a class folder is small)
    hits = glob.glob(os.path.join(SCRIPT_DIR, "**", name), recursive=True)
    # sibling folders up to 2 levels up - NON-recursive (e.g. ../Health/, ../../Health/)
    d = SCRIPT_DIR
    for _ in range(3):
        d = os.path.dirname(d)
        hits += glob.glob(os.path.join(d, name))
        hits += glob.glob(os.path.join(d, "*", name))
    return hits[0] if hits else None

# ---- spectrum / bands ----
def spec_db(sig):
    x = (sig - sig.mean()) * np.hanning(len(sig))
    sp = np.abs(np.fft.rfft(x)); sp[0] = 0
    f = np.fft.rfftfreq(len(x), 1 / FS)
    return f, 20 * np.log10(sp / (sp.max() + 1e-12) + 1e-12)

def f1_of(sig, fmin=3, fmax=80):
    x = (sig - sig.mean()) * np.hanning(len(sig))
    sp = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / FS)
    b = (f >= fmin) & (f <= fmax); idx = np.where(b)[0]; k = idx[np.argmax(sp[idx])]
    if 0 < k < len(sp) - 1:
        a, bb, c = sp[k - 1], sp[k], sp[k + 1]; d = a - 2 * bb + c
        dk = 0.5 * (a - c) / d if abs(d) > 1e-12 else 0.0
    else:
        dk = 0.0
    return (k + dk) * (f[1] - f[0])

def band_peak(f, spd, fc, half):
    m = (f >= fc - half) & (f <= fc + half)
    if not m.any():
        return np.nan, np.nan
    idx = np.where(m)[0]; k = idx[np.argmax(spd[idx])]
    return f[k], spd[k]

def band_snr(f, spd, fc, half):
    pm = (f >= fc - half) & (f <= fc + half)
    if not pm.any():
        return np.nan
    pk = spd[pm].max()
    sh = (((f >= fc - 3 * half) & (f < fc - half)) | ((f > fc + half) & (f <= fc + 3 * half)))
    return pk - (np.median(spd[sh]) if sh.any() else pk)

def sideband_metrics(sig, rpm_w):
    """Full set of k=1..KMAX band metrics for window sig at speed rpm_w."""
    f, spd = spec_db(sig); df = f[1] - f[0]
    f1 = f1_of(sig); n_s = 60 * f1; s = (n_s - rpm_w) / n_s
    off2 = 2 * s * f1; fr = rpm_w / 60.0
    out = dict(f1=f1, slip=s * 100, off_2s=off2, fr=fr, df=df,
               resolvable=bool(off2 > RESOLVE_BINS * df))
    half = max(3 * df, 0.12 * off2)
    coh_ok = 0; coh_tot = 0
    for k in range(1, KMAX + 1):
        ofk = 2 * k * s * f1
        for side, fc in (("lsb", f1 - ofk), ("usb", f1 + ofk)):
            fpk, lvl = band_peak(f, spd, fc, half)
            snr = band_snr(f, spd, fc, half)
            perr = abs(fpk - fc) if not np.isnan(fpk) else np.nan
            out[f"{side}{k}_dB"] = lvl
            out[f"{side}{k}_snr"] = snr
            out[f"{side}{k}_perr"] = perr
            coh_tot += 1
            if not np.isnan(perr) and perr < max(2 * df, 0.15 * ofk):
                coh_ok += 1
    out["comb_coherence"] = coh_ok / coh_tot if coh_tot else np.nan
    # headline indicator - max of LSB1/USB1
    out["lsb1_usb1_snr"] = np.nanmax([out["lsb1_snr"], out["usb1_snr"]])
    out["lsb1_usb1_dB"] = np.nanmax([out["lsb1_dB"], out["usb1_dB"]])
    # imbalance control: band f1 +/- fr (must not rise for a broken bar)
    half_fr = max(3 * df, 0.15 * fr)
    out["cur_sb_fr_snr"] = np.nanmax([band_snr(f, spd, f1 - fr, half_fr),
                                      band_snr(f, spd, f1 + fr, half_fr)])
    return out

def unbalance_pct(A, B, C, f1):
    a = np.exp(1j * 2 * np.pi / 3); N = len(A); n = np.arange(N); w = np.hanning(N)
    ph = lambda s: np.sum(s * w * np.exp(-1j * 2 * np.pi * f1 * n / FS))
    Va, Vb, Vc = ph(A), ph(B), ph(C)
    Vp = abs((Va + a * Vb + a * a * Vc) / 3); Vn = abs((Va + a * a * Vb + a * Vc) / 3)
    big, small = max(Vp, Vn), min(Vp, Vn)
    return small / (big + 1e-12) * 100.0

# ---- slip segmentation ----
def stable_windows(A, cur, t, rpm):
    """List of windows: (start, rpm_med, rpm_drift). drift = |median of last third -
       median of first third| - the real load drift, WITHOUT keyphase jitter."""
    out = []; ts = 0.0; end = len(A) / FS
    while ts + WIN_SEC <= end:
        m = (t >= ts) & (t < ts + WIN_SEC)
        seg = rpm[m]
        if len(seg) >= 6:
            n3 = max(1, len(seg) // 3)
            drift = abs(float(np.median(seg[-n3:])) - float(np.median(seg[:n3])))
            out.append((ts, float(np.median(seg)), drift))
        ts += STEP_SEC
    return out

def parse_regime(fn):
    L = re.search(r"(\d+)Nm", fn); R = re.search(r"(\d+)rpm", fn)
    return (int(L.group(1)) if L else np.nan, int(R.group(1)) if R else np.nan)

def process_file(path, health_floor):
    fn = os.path.basename(path)
    X = hb.load_clean(path); ch = hb.classify(X)
    t, rpm = hb.instantaneous_rpm(X[:, ch["keyphase"]])
    A = X[:, ch["current"][0]]; B = X[:, ch["current"][1]]; C = X[:, ch["current"][2]]
    proto = hb.protocol_of(fn); load_nom, rpm_nom = parse_regime(fn)
    rows = []
    for ts, rpm_med, rpm_drift in stable_windows(A, ch["current"], t, rpm):
        i0, i1 = int(ts * FS), int((ts + WIN_SEC) * FS)
        seg = A[i0:i1]
        met = sideband_metrics(seg, rpm_med)
        df = met["df"]; off2 = met["off_2s"]
        smear = rpm_drift / 30.0                    # Hz of smear from slip DRIFT
        stable = smear < max(df, STAB_FACTOR * off2)
        if not stable or off2 <= 0:
            continue                               # window mixes load / transition - skip
        # naive indicator: rise over the healthy floor of the same regime/protocol
        key = (proto, int(round(rpm_med / 500) * 500))
        floor = health_floor.get(key, np.nan)
        rise = met["lsb1_usb1_dB"] - floor if not np.isnan(floor) else np.nan
        unb = unbalance_pct(A[i0:i1], B[i0:i1], C[i0:i1], met["f1"])
        row = dict(file=fn, protocol=proto, load_nominal_Nm=load_nom, rpm_nominal=rpm_nom,
                   win_start_s=round(ts, 1), rpm=round(rpm_med, 1), rpm_drift=round(rpm_drift, 1),
                   f1_Hz=round(met["f1"], 3), slip_pct=round(met["slip"], 3),
                   off_2s_Hz=round(off2, 3), df_Hz=round(df, 3),
                   resolvable=met["resolvable"], smear_Hz=round(smear, 3),
                   lsb1_dB=round(met["lsb1_dB"], 1), usb1_dB=round(met["usb1_dB"], 1),
                   lsb1_snr=round(met["lsb1_snr"], 1), usb1_snr=round(met["usb1_snr"], 1),
                   headline_snr=round(met["lsb1_usb1_snr"], 1),
                   naive_rise_dB=round(rise, 1) if not np.isnan(rise) else np.nan,
                   comb_coherence=round(met["comb_coherence"], 2),
                   unbalance_pct=round(unb, 2),
                   ctrl_fr_snr=round(met["cur_sb_fr_snr"], 1))
        for k in range(2, KMAX + 1):
            row[f"lsb{k}_snr"] = round(met[f"lsb{k}_snr"], 1)
            row[f"usb{k}_snr"] = round(met[f"usb{k}_snr"], 1)
        rows.append(row)
    return rows, ch

def load_health_floor(csv):
    """{(protocol, rpm_level): sb_floor_bb_dB} from the health table."""
    if not csv or not os.path.exists(csv):
        return {}
    h = pd.read_csv(csv)
    out = {}
    for _, r in h.iterrows():
        key = (r["protocol"], int(round(r["rpm_meas"] / 500) * 500))
        out.setdefault(key, []).append(r["sb_floor_bb_dB"])
    return {k: float(np.mean(v)) for k, v in out.items()}

def main():
    files = sorted(glob.glob(os.path.join(SCRIPT_DIR, "**", "*.csv"), recursive=True))
    files = [f for f in files if re.search(r"\d+Nm", os.path.basename(f))
             and re.search(r"\d+rpm", os.path.basename(f))
             and "baseline" not in os.path.basename(f)]
    if not files:
        print("No broken-bar files found next to the script."); return
    hcsv = find_health_csv()
    health_floor = load_health_floor(hcsv)
    print(f"Files: {len(files)} | health floor: "
          f"{'found ' + os.path.basename(hcsv) if hcsv else 'NOT found (naive indicator skipped)'}")

    all_rows = []
    for f in files:
        print("...", os.path.relpath(f, SCRIPT_DIR))
        rows, ch = process_file(f, health_floor)
        all_rows += rows
    tab = pd.DataFrame(all_rows)
    out = os.path.join(SCRIPT_DIR, "broken_bar_windows.csv")
    tab.to_csv(out, index=False)

    # per-file headline = the max-load (max-slip) window among resolvable ones
    head = []
    for fn, g in tab.groupby("file"):
        gr = g[g.resolvable]
        pick = (gr if len(gr) else g).sort_values("slip_pct").iloc[-1]
        head.append(pick)
    headtab = pd.DataFrame(head)
    headtab.to_csv(os.path.join(SCRIPT_DIR, "broken_bar_headline.csv"), index=False)

    pd.set_option("display.width", 260, "display.max_columns", 60)
    show = ["file", "protocol", "load_nominal_Nm", "rpm", "slip_pct", "off_2s_Hz",
            "resolvable", "headline_snr", "naive_rise_dB", "comb_coherence", "unbalance_pct", "ctrl_fr_snr"]
    print("\n=== Headline points (max-load window per file) ===")
    print(headtab[show].to_string(index=False))

    make_figs(tab, headtab)
    print("\nSaved:", out, "| broken_bar_headline.csv | figures broken_bar_*.png")

def make_figs(tab, headtab):
    C = {"speed": "#1f77b4", "torque": "#ff7f0e"}
    # (1) signature (headline SNR) vs slip - the load axis, both protocols
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.2))
    for p, g in tab[tab.resolvable].groupby("protocol"):
        ax[0].scatter(g.slip_pct, g.headline_snr, c=C.get(p, "gray"), s=28, alpha=0.6,
                      edgecolor="k", lw=0.3, label=p)
    ax[0].set(title="(1) Broken-bar signature (band SNR) vs slip = load axis",
              xlabel="slip s, %", ylabel="first-band SNR, dB")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    # (2) naive rise vs self-sufficient snr (if the health floor is available)
    if tab["naive_rise_dB"].notna().any():
        for p, g in headtab.groupby("protocol"):
            ax[1].scatter(g.naive_rise_dB, g.headline_snr, c=C.get(p, "gray"), s=70,
                          edgecolor="k", lw=0.4, label=p)
        ax[1].set(title="(2) Naive rise over baseline vs self-sufficient SNR\n"
                        "(naive scatter between protocols - the problem from health)",
                  xlabel="naive rise over health floor, dB", ylabel="self-sufficient SNR, dB")
        ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    else:
        ax[1].text(0.5, 0.5, "health floor not found\nnaive indicator skipped",
                   ha="center", va="center", transform=ax[1].transAxes)
    plt.tight_layout(); plt.savefig(os.path.join(SCRIPT_DIR, "broken_bar_signature.png"), dpi=120); plt.close()

    # (3) signature track: measured band offset vs slip (comb follows slip)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.scatter(tab.slip_pct, tab.off_2s_Hz, c=[C.get(p, "gray") for p in tab.protocol], s=22, alpha=0.6)
    ax.set(title="(3) Band offset 2s·f1 vs slip - linearity = broken-bar signature",
           xlabel="slip s, %", ylabel="measured offset 2s·f1, Hz")
    ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(SCRIPT_DIR, "broken_bar_signature_track.png"), dpi=120); plt.close()

if __name__ == "__main__":
    main()
