"""
imbalance_analyze.py - clean rotor-imbalance analysis (section 3, stage 3).

Follows imbalance_catalog.md. Processes ALL Rotor_Unbalance files (both subfolders);
the healthy reference (1x radial magnitude per regime) is taken from the health baseline
table, exactly like the broken-bar naive indicator.

Channel of evidence is VIBRATION (imbalance is a mechanical, radial, once-per-rev fault):
  - primary metric R1x = sqrt(vib_1x_c2^2 + vib_1x_c3^2) - the RADIAL 1x magnitude
    (recon: the imbalance response splits between the two radial axes, do not use one);
  - axial axis c4 is a CONTROL (must stay low - else misalignment/bend, Episode 4).

Protocol handling (recon findings):
  - speed: a plateau = an operating point (rpm stable within the plateau) -> one law point;
    each speed file dwells on its named level +/- one step, so the omega^2 law is built by
    POOLING all speed files, not from one file.
  - torque: speed is const, load sweeps -> slip varies. We slide short windows across the
    load sweep; R1x vs slip must be FLAT (imbalance is load-independent). Torque points do
    NOT enter the omega^2 fit (option A) - they are the load-independence control.

The law: R1x ~ fr^2 (omega^2). The ~50 Hz rig resonance point is EXCLUDED from the fit
(it inflates the radial 1x, rides the c3 mode) and kept as the max-sensitivity zone.

THE 2-POLE TRAP (found on run 1; run-1 outputs preserved in "1_Trap results"):
on a 2-pole machine the electromagnetic f1 line sits only s*f1 Hz above the mechanical
1x (fr). The old wide +/-4-bin search around fr grabbed the f1 line whenever the two
were not resolvable (low speed and/or low slip), inflating "R1x" x7-10 at ~490 rpm and
bending the omega^2 exponent to ~1. Fix: (a) vibration harmonics are measured with a
NARROW +/-1-bin search (fr is known precisely from the keyphase); (b) every window
carries sep_bins = |f1-fr|/df and per-harmonic resolvability flags (flat-top main lobe
half-width ~4.75 bins); (c) hard-contaminated windows (f1_in_1x) are excluded from the
law fit and from the health ratio, but KEPT in the table - they document the trap.

RUN-2 CORRECTION (outputs of run 2 preserved alongside run 1): bin-distance alone is the
WRONG discriminator - it passed the contaminated 478 rpm/40 Nm point (sep 6.2 bins,
x10 over the law) and rejected the provably clean 989 rpm/20 Nm points (their R1x equals
the resolvable 40 Nm twins to 3 digits). The real criterion is the EM f1 line AMPLITUDE
vs the mechanical 1x, and it is regime-dependent: at fr ~ 8 Hz the EM line (0.4-0.6e-3,
grows with load) exceeds the omega^2-extrapolated mechanical 1x (~6e-5) by x7-10 - the
mechanical 1x is UNRESOLVABLE under the EM line. So fr < LOWSPEED_FR_HZ is excluded as a
TRUE METHOD LIMIT (the vibration twin of the broken-bar 477 rpm MCSA limit: the same
low-speed corner is blind for both methods, for different reasons). Hard exclusion by
separation now applies only to truly merged lines (sep < 3 bins). The EM f1 line is
measured per window (vib_f1_line) to document the masker.

Run: place next to health_baseline.py in the Rotor_Unbalance folder. Point HEALTH_CSV at
the health table (or let the script search parent folders for it).
  python imbalance_analyze.py            - all files in the script folder
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

# ---- analysis parameters ----
WIN_SEC = 8.0            # torque load-sweep sub-window (also the spectrum window)
STEP_SEC = 2.0
RESONANCE_HZ = 50.0      # rig resonance from health
RES_GUARD_HZ = 1.5       # |f1-50| or |fr-50| < guard  -> resonance window (excluded from law)
AXIAL_RES_HZ = 16.5      # CANDIDATE axial rig mode seen on run 1 (to be confirmed on health)
FT_LOBE_BINS = 4.75      # flat-top main-lobe half-width, bins
VIB_SEARCH_BINS = 1      # narrow search for vibration harmonics (fr known from keyphase)
SEP_HARD_BINS = 3.0      # lines truly merged: one peak, mech/EM inseparable (excluded)
SEP_MARGINAL_BINS = 8.0  # grey zone - kept in the law, flagged, twin-checked in console
LOWSPEED_FR_HZ = 10.0    # method limit: below this the EM f1 line masks the mech 1x
FIT_MODE = "A"           # "A": omega^2 law from SPEED files only (torque = control).
                         # "B": pool speed+torque into the fit (torque points are clustered).

# health table (for the imbalance-over-health ratio). If empty - search for it.
HEALTH_CSV = ""

def find_health_csv():
    if HEALTH_CSV and os.path.exists(HEALTH_CSV):
        return HEALTH_CSV
    name = "health_baseline_plateaus.csv"
    hits = glob.glob(os.path.join(SCRIPT_DIR, "**", name), recursive=True)
    d = SCRIPT_DIR
    for _ in range(3):
        d = os.path.dirname(d)
        hits += glob.glob(os.path.join(d, name))
        hits += glob.glob(os.path.join(d, "*", name))
    return hits[0] if hits else None

# ---- spectrum / bands ----
def spec_db(sig):
    """Hann dB relative to the maximum. For floors / SNR."""
    x = (sig - sig.mean()) * np.hanning(len(sig))
    sp = np.abs(np.fft.rfft(x)); sp[0] = 0
    f = np.fft.rfftfreq(len(x), 1 / FS)
    return f, 20 * np.log10(sp / (sp.max() + 1e-12) + 1e-12)

def band_snr(f, spd, fc, half):
    """Peak prominence over local shoulders (self-sufficient, same spectrum)."""
    pm = (f >= fc - half) & (f <= fc + half)
    if not pm.any():
        return np.nan
    pk = spd[pm].max()
    sh = (((f >= fc - 3 * half) & (f < fc - half)) | ((f > fc + half) & (f <= fc + 3 * half)))
    return (pk - float(np.median(spd[sh]))) if sh.any() else np.nan

def parse_regime(fn):
    L = re.search(r"(\d+)Nm", fn); R = re.search(r"(\d+)rpm", fn)
    return (int(L.group(1)) if L else np.nan, int(R.group(1)) if R else np.nan)

# ---- metrics on ONE window ----
def metrics_on_window(seg, cur, vib, rpm_w):
    """Imbalance metrics for one window at speed rpm_w."""
    A = seg[:, cur[0]]; B = seg[:, cur[1]]; C = seg[:, cur[2]]
    f1 = hb.f1_of(A); n_s = 60.0 * f1; slip = (n_s - rpm_w) / n_s
    fr = rpm_w / 60.0
    d = dict(f1=f1, fr=fr, slip=slip * 100.0)
    # --- 2-pole trap bookkeeping: how far is the EM f1 line from the mechanical 1x? ---
    df_bin = FS / len(seg)                      # bin width of THIS window
    sep_bins = abs(f1 - fr) / df_bin
    d["sep_Hz"] = abs(f1 - fr); d["sep_bins"] = sep_bins
    d["f1_in_1x"] = bool(sep_bins < SEP_HARD_BINS)          # f1 lobe covers the 1x bin
    d["f1_near_1x"] = bool(SEP_HARD_BINS <= sep_bins < SEP_MARGINAL_BINS)
    d["f1_in_2x"] = bool(2 * sep_bins < SEP_HARD_BINS)      # 2f1 vs 2x (episode 4 guard)
    d["slip_suspect"] = bool(slip * 100.0 < 0.05)           # f1 estimate unreliable near sync
    d["low_speed_em"] = bool(fr < LOWSPEED_FR_HZ)           # method limit: EM line masks 1x
    # flat-top amplitudes per axis (c2, c3 radial; c4 axial), NARROW search:
    # fr comes from the keyphase, so we look only +/-1 bin - the wide default was the trap
    amp = {}
    for lab, ci in zip(("c2", "c3", "c4"), vib):
        v = seg[:, ci]
        for h, name in ((1, "1x"), (2, "2x"), (3, "3x")):
            amp[f"{name}_{lab}"] = hb.amp_flattop(v, h * fr, search_bins=VIB_SEARCH_BINS)
        d[f"vib_1x_{lab}"] = amp[f"1x_{lab}"]
        d[f"vib_2x_{lab}"] = amp[f"2x_{lab}"]
        d[f"vib_3x_{lab}"] = amp[f"3x_{lab}"]
    # radial magnitude (primary) and axial control
    d["R1x"] = float(np.hypot(amp["1x_c2"], amp["1x_c3"]))
    d["R2x"] = float(np.hypot(amp["2x_c2"], amp["2x_c3"]))
    d["axial_1x"] = amp["1x_c4"]
    d["axial_ratio"] = amp["1x_c4"] / (d["R1x"] + 1e-12)
    # self-sufficient 1x SNR on the stronger radial axis
    dom = vib[0] if amp["1x_c2"] >= amp["1x_c3"] else vib[1]
    d["dom_radial"] = "c2" if dom == vib[0] else "c3"
    # the masker, measured: EM f1 line amplitude in the dominant radial channel
    # (meaningful when the lines are separable, i.e. sep_bins >~ 3; else ~= the 1x value)
    d["vib_f1_line"] = hb.amp_flattop(seg[:, dom], f1, search_bins=VIB_SEARCH_BINS)
    d["em_over_1x"] = d["vib_f1_line"] / (float(np.hypot(amp["1x_c2"], amp["1x_c3"])) + 1e-12)
    f, spd = spec_db(seg[:, dom]); df = f[1] - f[0]
    half = max(3 * df, 0.10 * fr)
    d["onex_snr_dB"] = band_snr(f, spd, fr, half)
    # current cross-check: f1 +/- fr sidebands (weak positive for eccentricity)
    fA, sA = spec_db(A); dfA = fA[1] - fA[0]; halfc = max(3 * dfA, 0.15 * fr)
    d["cur_sb_1x_snr"] = np.nanmax([band_snr(fA, sA, f1 - fr, halfc),
                                    band_snr(fA, sA, f1 + fr, halfc)])
    # control: current unbalance must not rise (else stator/supply)
    d["unbalance_pct"] = hb.unbalance_pct(A, B, C, f1)
    # resonance flags
    d["f1_on_res"] = bool(abs(f1 - RESONANCE_HZ) < RES_GUARD_HZ)
    d["fr_on_res"] = bool(abs(fr - RESONANCE_HZ) < RES_GUARD_HZ)
    d["fr_on_axial_res"] = bool(abs(fr - AXIAL_RES_HZ) < RES_GUARD_HZ)   # candidate, run 1
    return d

def _row(fn, proto, load_nom, rpm_nom, win_kind, ts, rpm_w, met, health_r1x):
    lvl = int(round(rpm_w / 500) * 500)
    h = health_r1x.get((proto, lvl), np.nan)
    ratio = met["R1x"] / h if (h and not np.isnan(h)) else np.nan
    if met["f1_in_1x"] or met["low_speed_em"]:
        ratio = np.nan          # numerator is the EM f1 line, not the mechanical 1x
    row = dict(file=fn, protocol=proto, load_nominal_Nm=load_nom, rpm_nominal=rpm_nom,
               win_kind=win_kind, win_start_s=round(ts, 1), rpm=round(rpm_w, 1),
               rpm_level=lvl, f1_Hz=round(met["f1"], 3), fr_Hz=round(met["fr"], 3),
               slip_pct=round(met["slip"], 3),
               R1x=round(met["R1x"], 6), R2x=round(met["R2x"], 6),
               axial_1x=round(met["axial_1x"], 6), axial_ratio=round(met["axial_ratio"], 3),
               dom_radial=met["dom_radial"], onex_snr_dB=round(met["onex_snr_dB"], 1),
               cur_sb_1x_snr=round(met["cur_sb_1x_snr"], 1),
               unbalance_pct=round(met["unbalance_pct"], 2),
               f1_on_res=met["f1_on_res"], fr_on_res=met["fr_on_res"],
               on_resonance=bool(met["f1_on_res"] or met["fr_on_res"]),
               sep_Hz=round(met["sep_Hz"], 3), sep_bins=round(met["sep_bins"], 1),
               f1_in_1x=met["f1_in_1x"], f1_near_1x=met["f1_near_1x"],
               f1_in_2x=met["f1_in_2x"], slip_suspect=met["slip_suspect"],
               low_speed_em=met["low_speed_em"],
               vib_f1_line=round(met["vib_f1_line"], 6), em_over_1x=round(met["em_over_1x"], 2),
               fr_on_axial_res=met["fr_on_axial_res"],
               r1x_over_health=round(ratio, 2) if not np.isnan(ratio) else np.nan)
    for lab in ("c2", "c3", "c4"):
        for h_ in ("1x", "2x", "3x"):
            row[f"vib_{h_}_{lab}"] = round(met[f"vib_{h_}_{lab}"], 6)
    return row

def process_file(path, health_r1x):
    fn = os.path.basename(path)
    X = hb.load_clean(path); ch = hb.classify(X)
    kp = X[:, ch["keyphase"]]
    t, rpm = hb.instantaneous_rpm(kp)
    plateaus = hb.detect_plateaus(t, rpm)
    proto = hb.protocol_of(fn); load_nom, rpm_nom = parse_regime(fn)
    cur, vib = ch["current"], ch["vibration"]
    rows = []
    plateau_report = [(round(a, 1), round(b, 1), round(r, 0)) for a, b, r in plateaus]

    if proto == "speed":
        # one row per plateau = one omega^2 law point
        for (t0, t1, rp) in plateaus:
            t1 = min(t1, t0 + hb.MAX_WIN_SEC)
            i0, i1 = int(t0 * FS), int(t1 * FS)
            met = metrics_on_window(X[i0:i1], cur, vib, rp)
            rows.append(_row(fn, proto, load_nom, rpm_nom, "plateau", t0, rp, met, health_r1x))
    else:
        # torque: slide across the load sweep of the longest plateau -> load axis
        if plateaus:
            t0, t1, _ = max(plateaus, key=lambda p: p[1] - p[0])
        else:
            t0, t1 = t[0], t[-1]
        ts = t0
        while ts + WIN_SEC <= t1 + 1e-6:
            i0, i1 = int(ts * FS), int((ts + WIN_SEC) * FS)
            m = (t >= ts) & (t < ts + WIN_SEC)
            rp = float(np.median(rpm[m])) if m.sum() >= 6 else np.nan
            if not np.isnan(rp):
                met = metrics_on_window(X[i0:i1], cur, vib, rp)
                rows.append(_row(fn, proto, load_nom, rpm_nom, "load_seg", ts, rp, met, health_r1x))
            ts += STEP_SEC
    return rows, ch, plateau_report

def load_health_r1x(csv):
    """{(protocol, rpm_level): mean radial 1x magnitude} from the health table."""
    if not csv or not os.path.exists(csv):
        return {}
    h = pd.read_csv(csv)
    out = {}
    for _, r in h.iterrows():
        r1x = float(np.hypot(r.get("vib_1x_c2", np.nan), r.get("vib_1x_c3", np.nan)))
        key = (r["protocol"], int(round(r["rpm_meas"] / 500) * 500))
        out.setdefault(key, []).append(r1x)
    return {k: float(np.nanmean(v)) for k, v in out.items()}

def omega_fit(tab):
    """log-log fit R1x vs fr, excluding resonance. Returns (exponent, intercept, used_df)."""
    src = tab[tab.protocol == "speed"] if FIT_MODE == "A" else tab
    use = src[(~src.on_resonance) & (~src.f1_in_1x) & (~src.slip_suspect)
              & (~src.low_speed_em) & (src.R1x > 0) & (src.fr_Hz > 0)]
    if len(use) < 3:
        return np.nan, np.nan, use
    n, b = np.polyfit(np.log(use.fr_Hz.values), np.log(use.R1x.values), 1)
    return float(n), float(b), use

def main():
    files = sorted(glob.glob(os.path.join(SCRIPT_DIR, "**", "*.csv"), recursive=True))
    files = [f for f in files if re.search(r"\d+Nm", os.path.basename(f))
             and re.search(r"\d+rpm", os.path.basename(f))
             and "baseline" not in os.path.basename(f)]
    if not files:
        print("No Rotor_Unbalance files found next to the script."); return
    hcsv = find_health_csv()
    health_r1x = load_health_r1x(hcsv)
    print(f"Files: {len(files)} | health table: "
          f"{'found ' + os.path.basename(hcsv) if hcsv else 'NOT found (health ratio skipped)'}")
    print(f"Fit mode: {FIT_MODE} "
          f"({'speed-only law, torque=control' if FIT_MODE == 'A' else 'speed+torque pooled'})")

    all_rows = []; chmaps = []
    print("\n=== Plateaus found per file (verifies the 'named level +/- one step' pattern) ===")
    for f in files:
        rows, ch, prep = process_file(f, health_r1x)
        all_rows += rows; chmaps.append((os.path.basename(f), ch))
        print(f"  {os.path.relpath(f, SCRIPT_DIR)}")
        print(f"     plateaus: " + ", ".join(f"{r:.0f}rpm[{a}-{b}s]" for a, b, r in prep))
    tab = pd.DataFrame(all_rows)
    out = os.path.join(SCRIPT_DIR, "imbalance_windows.csv")
    tab.to_csv(out, index=False)

    # channel-map consistency
    ref = chmaps[0][1]; consistent = all(
        ch["keyphase"] == ref["keyphase"] and ch["current"] == ref["current"]
        and ch["vibration"] == ref["vibration"] for _, ch in chmaps)
    print(f"\nChannel map consistent across files: {consistent}")

    # per-file headline = strongest operating point (max radial 1x)
    head = []
    for fn, g in tab.groupby("file"):
        clean = g[(~g.on_resonance) & (~g.f1_in_1x) & (~g.low_speed_em)]
        head.append((clean if len(clean) else g).sort_values("R1x").iloc[-1])
    headtab = pd.DataFrame(head)
    headtab.to_csv(os.path.join(SCRIPT_DIR, "imbalance_headline.csv"), index=False)

    pd.set_option("display.width", 260, "display.max_columns", 60)
    show = ["file", "protocol", "load_nominal_Nm", "rpm", "fr_Hz", "slip_pct",
            "R1x", "axial_ratio", "onex_snr_dB", "on_resonance", "sep_bins", "f1_in_1x",
            "r1x_over_health", "unbalance_pct"]
    print("\n=== Headline points (strongest window per file) ===")
    print(headtab[show].to_string(index=False))

    # 2-pole trap census
    trap = tab[tab.f1_in_1x]; near = tab[tab.f1_near_1x]; lo = tab[tab.low_speed_em]
    print(f"\n=== 2-pole trap: {len(trap)} merged (sep<{SEP_HARD_BINS} bins, excluded), "
          f"{len(near)} marginal (kept, flagged), "
          f"{len(lo)} low-speed (fr<{LOWSPEED_FR_HZ} Hz - EM line masks 1x, excluded) ===")
    if len(lo):
        print("  low-speed EM line (the masker), per window: "
              + ", ".join(f"{r.fr_Hz:.1f}Hz->{r.vib_f1_line:.2e}" for _, r in
                          lo.drop_duplicates("file").iterrows()))
    # twin check: marginal windows vs clean windows at the same rpm level
    for lvl, g in tab[tab.protocol == "speed"].groupby("rpm_level"):
        m = g[g.f1_in_1x | g.f1_near_1x]; c = g[~(g.f1_in_1x | g.f1_near_1x | g.on_resonance)]
        if len(m) and len(c):
            print(f"  twin check @ {lvl} rpm: flagged R1x={m.R1x.mean():.3e} vs "
                  f"clean {c.R1x.mean():.3e} (ratio {m.R1x.mean()/c.R1x.mean():.2f} - "
                  f"~1.0 means the flagged points are in fact clean)")

    # omega^2 law
    n, b, use = omega_fit(tab)
    print("\n=== Omega^2 law (R1x ~ fr^n, resonance excluded) ===")
    if np.isnan(n):
        print("  not enough non-resonance speed points to fit (need the full speed set).")
    else:
        r2 = np.corrcoef(np.log(use.fr_Hz), np.log(use.R1x))[0, 1] ** 2
        print(f"  exponent n = {n:.2f}  (omega^2 => 2.0),  R^2 = {r2:.3f},  points = {len(use)}")
        res = tab[tab.on_resonance & (tab.protocol == "speed")]
        for _, r in res.iterrows():
            pred = np.exp(b + n * np.log(r.fr_Hz))
            print(f"  resonance {r.rpm:.0f}rpm: R1x={r.R1x:.4g}, law={pred:.4g}, "
                  f"inflation x{r.R1x / max(pred, 1e-12):.1f}")

    # load-independence control (torque)
    print("\n=== Load-independence control (torque: R1x vs slip should be flat) ===")
    tq = tab[tab.protocol == "torque"]
    if tq.empty:
        print("  (no torque files in this set)")
    for fn, g in tq.groupby("file"):
        cov = 100 * g.R1x.std() / (g.R1x.mean() + 1e-12)
        print(f"  {fn}: slip {g.slip_pct.min():.2f}-{g.slip_pct.max():.2f}%, "
              f"R1x CoV = {cov:.1f}%  {'FLAT -> rotor, not load' if cov < 20 else 'CHECK'}")

    make_figs(tab, headtab, n, b)
    print("\nSaved:", out, "| imbalance_headline.csv | figures imbalance_*.png")

def make_figs(tab, headtab, n, b):
    C = {"speed": "#1f77b4", "torque": "#ff7f0e"}
    sp = tab[tab.protocol == "speed"]; tq = tab[tab.protocol == "torque"]

    # (1) omega^2 law: R1x vs fr, log-log, fit excluding resonance, resonance flagged
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    trap = sp[sp.f1_in_1x]
    lowv = sp[sp.low_speed_em & ~sp.f1_in_1x]
    reg = sp[(~sp.on_resonance) & (~sp.f1_in_1x) & (~sp.low_speed_em)]
    res = sp[sp.on_resonance]
    ax.loglog(reg.fr_Hz, reg.R1x, "o", color="#1f77b4", ms=8, mec="k", label="speed (law)")
    if not res.empty:
        ax.loglog(res.fr_Hz, res.R1x, "o", color="none", mec="red", mew=2, ms=14,
                  label="~50 Hz resonance (excluded)")
    if not trap.empty:
        ax.loglog(trap.fr_Hz, trap.R1x, "x", color="#d62728", ms=11, mew=2,
                  label="f1 merged with 1x - excluded")
    if not lowv.empty:
        ax.loglog(lowv.fr_Hz, lowv.R1x, "s", color="#aaaaaa", mec="k", ms=9,
                  label="low-speed limit - excluded")
    if not np.isnan(n):
        fr = np.linspace(sp.fr_Hz.min(), sp.fr_Hz.max(), 50)
        ax.loglog(fr, np.exp(b) * fr ** n, "k--", lw=1, label=f"fit n={n:.2f} (omega^2=2)")
    ax.set(title="(law) Radial 1x magnitude vs rotation freq",
           xlabel="fr = rpm/60, Hz", ylabel="R1x = sqrt(c2^2+c3^2)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3, which="both")
    plt.tight_layout(); plt.savefig(os.path.join(SCRIPT_DIR, "imbalance_omega2.png"), dpi=120); plt.close()

    # (2) load-independence: R1x vs slip in torque (flat lines)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for fn, g in tq.groupby("file"):
        g = g.sort_values("slip_pct")
        lab = re.search(r"(\d+Nm_\d+rpm)", fn)
        ax.plot(g.slip_pct, g.R1x, "o-", ms=5, label=lab.group(1) if lab else fn)
    ax.set_yscale("log")
    ax.set(title="(control) TORQUE: R1x vs slip = load axis -> FLAT = rotor, not load",
           xlabel="slip s, % (load proxy)", ylabel="R1x")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(SCRIPT_DIR, "imbalance_load_independence.png"), dpi=120); plt.close()

    # (3) radial vs axial 1x vs fr (axial must stay low for imbalance)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.loglog(sp.fr_Hz, sp.R1x, "s", color="#d62728", ms=8, mec="k", label="radial R1x")
    ax.loglog(sp.fr_Hz, sp.axial_1x, "^", color="#2ca02c", ms=8, mec="k", label="axial c4 1x")
    ax.set(title="(control) Radial vs axial 1x (axial low = pure imbalance)",
           xlabel="fr, Hz", ylabel="1x amplitude")
    ax.legend(fontsize=8); ax.grid(alpha=0.3, which="both")
    plt.tight_layout(); plt.savefig(os.path.join(SCRIPT_DIR, "imbalance_radial_vs_axial.png"), dpi=120); plt.close()

if __name__ == "__main__":
    main()