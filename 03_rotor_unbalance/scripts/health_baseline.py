"""
Health-базлайн ZZU-MCC5 — чистовой извлекатель (по health_baseline_catalog.md).

Единица анализа — ПОЛКА (рабочая точка), не файл. Каждый health-файл даёт
несколько полок; каждая полка -> одна строка таблицы.

Каналы (подтверждено разведкой, раздел 0-bis каталога):
  col0  — счётчик времени (пила, наклон 1.0/с) -> ОТБРАСЫВАЕТСЯ
  col1  — keyphase
  col2..4 — вибрация (3 оси, ярлык оси пока не присвоен)
  col5..7 — ток (3 фазы)
  Момента как канала НЕТ -> нагрузка = номинал из имени, полки по скорости.

Окна: flat-top для АМПЛИТУД (vib 1x/2x/3x), Ханнинг для ПОЛОВ/дБ/SNR.
Полюса: жёстко 2 (n_s = 60*f1).
"""
import os, glob, re
import numpy as np
import pandas as pd
from scipy.signal.windows import flattop

FS = 12800.0
# --- полки ---
PLATEAU_TOL_RPM = 40.0     # размах внутри полки для склейки (об/мин)
PLATEAU_MIN_SEC = 4.0      # мин. длина полки после отступов
EDGE_MARGIN = 1.0          # отступ от краёв полки, с
MAX_WIN_SEC = 18.0         # макс. окно внутри полки
# --- подокна для разброса ---
SUB_SEC = 4.0
SUB_STEP = 2.0
# --- полосы/пороги ---
GUARD_BINS = 3             # защитная зона вокруг f1, бинов

# ======================================================================
# Чтение и опознание каналов
# ======================================================================
def load_clean(path):
    X = pd.read_csv(path, header=None).dropna(axis=1, how="all").values.astype(float)
    return X

def _is_timer(col):
    """Счётчик времени: пила с наклоном ~1.0/с и периодическими сбросами."""
    d = np.diff(col)
    pos = d[d > 0]
    if len(pos) < 100:
        return False
    slope_per_s = np.median(pos) * FS
    has_resets = np.any(d < -0.5)
    return has_resets and abs(slope_per_s - 1.0) < 0.05

def _fingerprint(col):
    x = col - col.mean()
    lo, hi = np.percentile(col, 1), np.percentile(col, 99); rng = hi - lo
    pulse = 0.0 if rng < 1e-9 else (np.mean(np.abs(col - lo) < 0.1 * rng) +
                                    np.mean(np.abs(col - hi) < 0.1 * rng))
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))); sp[0] = 0
    conc = sp.max() / (sp.sum() + 1e-12)
    return pulse, conc

def classify(X):
    """-> dict(keyphase, current[3], vibration[3], timer)."""
    n = X.shape[1]
    timer = [i for i in range(n) if _is_timer(X[:, i])]
    usable = [i for i in range(n) if i not in timer]
    fps = {i: _fingerprint(X[:, i]) for i in usable}
    keyphase = max(usable, key=lambda i: fps[i][0])
    rest = [i for i in usable if i != keyphase]
    current = sorted(sorted(rest, key=lambda i: fps[i][1], reverse=True)[:3])
    vibration = sorted(i for i in rest if i not in current)
    return dict(keyphase=keyphase, current=current, vibration=vibration,
                timer=(timer[0] if timer else None))

# ======================================================================
# Скорость и полки
# ======================================================================
def instantaneous_rpm(kp):
    thr = kp.min() + 0.5 * (kp.max() - kp.min()); above = kp > thr
    rises = np.where((~above[:-1]) & (above[1:]))[0]
    frac = (thr - kp[rises]) / (kp[rises + 1] - kp[rises] + 1e-12)
    et = (rises + frac) / FS; iv = np.diff(et); med = np.median(iv)
    keep = np.concatenate([[True], iv > 0.4 * med]); et = et[keep]; iv = np.diff(et)
    w = max(3, int(0.5 / med) | 1)
    rpm = pd.Series(60.0 / iv).rolling(w, center=True, min_periods=1).median().values
    return et[:-1], rpm

def detect_plateaus(t, rpm, grid_dt=0.05, smooth_sec=1.0):
    tg = np.arange(t[0], t[-1], grid_dt); rg = np.interp(tg, t, rpm)
    k = max(3, int(round(smooth_sec / grid_dt)) | 1)
    rgs = pd.Series(rg).rolling(k, center=True, min_periods=1).median().values
    out = []; i = 0; n = len(rgs)
    while i < n:
        acc = [rgs[i]]; j = i + 1
        while j < n and abs(rgs[j] - np.median(acc)) <= PLATEAU_TOL_RPM:
            acc.append(rgs[j]); j += 1
        if tg[j - 1] - tg[i] >= PLATEAU_MIN_SEC + 2 * EDGE_MARGIN:
            out.append((tg[i] + EDGE_MARGIN, tg[j - 1] - EDGE_MARGIN, float(np.median(acc))))
        i = j
    return out

def speed_jitter_pct(kp):
    thr = kp.min() + 0.5 * (kp.max() - kp.min()); above = kp > thr
    rises = np.where((~above[:-1]) & (above[1:]))[0]
    iv = np.diff(rises)
    return float(np.std(iv) / np.median(iv) * 100.0)

# ======================================================================
# Спектры: два окна
# ======================================================================
def spec_db_hann(sig):
    """дБ относительно максимума (= f1). Для полов/SNR."""
    x = (sig - sig.mean()) * np.hanning(len(sig))
    sp = np.abs(np.fft.rfft(x)); sp[0] = 0
    f = np.fft.rfftfreq(len(x), 1 / FS)
    return f, 20 * np.log10(sp / (sp.max() + 1e-12) + 1e-12)

def amp_flattop(sig, fc, search_bins=4):
    """Физ. амплитуда синуса на частоте fc (flat-top, точная амплитуда)."""
    w = flattop(len(sig)); x = (sig - sig.mean()) * w
    sp = np.abs(np.fft.rfft(x)) * 2.0 / np.sum(w)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    k = int(np.argmin(np.abs(f - fc)))
    k0, k1 = max(0, k - search_bins), min(len(sp), k + search_bins + 1)
    return float(sp[k0:k1].max())

def f1_of(sig, fmin=3.0, fmax=80.0):
    """f1 с параболической интерполяцией пика."""
    x = (sig - sig.mean()) * np.hanning(len(sig))
    sp = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / FS)
    b = (f >= fmin) & (f <= fmax); idx = np.where(b)[0]
    k = idx[np.argmax(sp[idx])]
    if 0 < k < len(sp) - 1:
        a, b_, c = sp[k - 1], sp[k], sp[k + 1]; d = a - 2 * b_ + c
        dk = 0.5 * (a - c) / d if abs(d) > 1e-12 else 0.0
    else:
        dk = 0.0
    return (k + dk) * (f[1] - f[0])

def band_floor_db(f, spd, fc_lo, fc_hi):
    m = (f >= fc_lo) & (f <= fc_hi)
    return float(spd[m].max()) if m.any() else np.nan

# ======================================================================
# Ток: THD и небаланс
# ======================================================================
def _amp_at(f, sp, freq, hb=2):
    k = int(round(freq / (f[1] - f[0])))
    k0, k1 = max(0, k - hb), min(len(sp), k + hb + 1)
    return sp[k0:k1].max() if k1 > k0 else 0.0

def thd_pct(sig, f1, nharm=7):
    x = (sig - sig.mean()) * np.hanning(len(sig))
    sp = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / FS)
    v1 = _amp_at(f, sp, f1)
    harm = np.sqrt(sum(_amp_at(f, sp, k * f1) ** 2 for k in range(2, nharm + 1)))
    return float(harm / (v1 + 1e-12) * 100.0)

def _phasor(sig, f1):
    N = len(sig); n = np.arange(N); w = np.hanning(N)
    return np.sum(sig * w * np.exp(-1j * 2 * np.pi * f1 * n / FS))

def unbalance_pct(A, B, C, f1):
    a = np.exp(1j * 2 * np.pi / 3)
    Va, Vb, Vc = _phasor(A, f1), _phasor(B, f1), _phasor(C, f1)
    Vp = abs((Va + a * Vb + a * a * Vc) / 3); Vn = abs((Va + a * a * Vb + a * Vc) / 3)
    big, small = max(Vp, Vn), min(Vp, Vn)
    return float(small / (big + 1e-12) * 100.0)

# ======================================================================
# Метрики на ОДНОМ окне (полке или подокне)
# ======================================================================
def metrics_on_window(seg, cur_idx, vib_idx, rpm_w):
    """seg: срез X по времени. Возвращает dict метрик группы 2-3 для окна."""
    A = seg[:, cur_idx[0]]; B = seg[:, cur_idx[1]]; C = seg[:, cur_idx[2]]
    f1 = f1_of(A); n_s = 60.0 * f1; slip = (n_s - rpm_w) / n_s
    off = 2 * slip * f1; fr = rpm_w / 60.0
    f, spd = spec_db_hann(A)
    df = f[1] - f[0]; guard = GUARD_BINS * df
    # пол полос обрыва стержня: f1 ± (guard .. off)
    sb_bb = max(band_floor_db(f, spd, f1 - off, f1 - guard),
                band_floor_db(f, spd, f1 + guard, f1 + off))
    # пол токовых полос дисбаланса: f1 ± fr
    half = max(3 * df, 0.15 * fr)
    cur_sb = max(band_floor_db(f, spd, f1 - fr - half, f1 - fr + half),
                 band_floor_db(f, spd, f1 + fr - half, f1 + fr + half))
    d = dict(f1=f1, slip=slip * 100, off=off, fr=fr,
             sb_floor_bb_dB=sb_bb, cur_sb_1x_dB=cur_sb,
             I_rms=float(np.sqrt(np.mean((A - A.mean()) ** 2))),
             thd_pct=thd_pct(A, f1), unbalance_pct=unbalance_pct(A, B, C, f1))
    # вибрация — амплитуды flat-top
    for lab, ci in zip(("c2", "c3", "c4"), vib_idx):
        v = seg[:, ci]
        d[f"vib_1x_{lab}"] = amp_flattop(v, fr)
        d[f"vib_2x_{lab}"] = amp_flattop(v, 2 * fr)
        d[f"vib_3x_{lab}"] = amp_flattop(v, 3 * fr)
    return d

FLOOR_KEYS = ["sb_floor_bb_dB", "cur_sb_1x_dB",
              "vib_1x_c2", "vib_1x_c3", "vib_1x_c4"]

# ======================================================================
# Обработка файла -> строки по полкам
# ======================================================================
def parse_regime(fname):
    L = re.search(r"(\d+)Nm", fname); R = re.search(r"(\d+)rpm", fname)
    return (int(L.group(1)) if L else np.nan, int(R.group(1)) if R else np.nan)

def protocol_of(fname):
    return "speed" if "speed_circ" in fname else ("torque" if "torque_circ" in fname else "?")

def process_file(path):
    fname = os.path.basename(path)
    X = load_clean(path); ch = classify(X)
    kp = X[:, ch["keyphase"]]
    t, rpm = instantaneous_rpm(kp)
    jitter = speed_jitter_pct(kp)
    plateaus = detect_plateaus(t, rpm)
    load_nom, rpm_nom = parse_regime(fname); proto = protocol_of(fname)
    rows = []
    for p_idx, (t0, t1, rp) in enumerate(plateaus):
        t1 = min(t1, t0 + MAX_WIN_SEC)
        i0, i1 = int(t0 * FS), int(t1 * FS)
        seg_full = X[i0:i1]
        # рабочая точка — по полному окну полки
        base = metrics_on_window(seg_full, ch["current"], ch["vibration"], rp)
        # разброс — по подокнам
        sub_vals = {k: [] for k in FLOOR_KEYS}
        st = t0; nsub = 0
        while st + SUB_SEC <= t1 + 1e-6:
            s0, s1 = int(st * FS), int((st + SUB_SEC) * FS)
            mv = metrics_on_window(X[s0:s1], ch["current"], ch["vibration"], rp)
            for k in FLOOR_KEYS:
                sub_vals[k].append(mv[k])
            nsub += 1; st += SUB_STEP
        row = dict(protocol=proto, file=fname, plateau_idx=p_idx,
                   load_nominal_Nm=load_nom, rpm_nominal=rpm_nom,
                   rpm_meas=round(rp, 1), rpm_level=int(round(rp / 50) * 50),
                   on_grid=bool(round(rp / 500) * 500 in (500, 1000, 1500, 2000, 2500, 3000)
                               and abs(rp - round(rp / 500) * 500) < 60),
                   plateau_dur_s=round(t1 - t0, 1), n_sub=nsub,
                   speed_jitter_pct=round(jitter, 3))
        # рабочая точка
        row.update(f1_Hz=round(base["f1"], 3), fr_Hz=round(base["fr"], 3),
                   slip_pct=round(base["slip"], 3), sb_offset_Hz=round(base["off"], 3))
        # полы/ток (mean по полке)
        for k in ["sb_floor_bb_dB", "cur_sb_1x_dB", "I_rms", "thd_pct", "unbalance_pct"]:
            row[k] = round(base[k], 3)
        for lab in ("c2", "c3", "c4"):
            for h in ("1x", "2x", "3x"):
                row[f"vib_{h}_{lab}"] = round(base[f"vib_{h}_{lab}"], 6)
        # внутриполочный разброс
        for k in FLOOR_KEYS:
            arr = np.array(sub_vals[k]) if sub_vals[k] else np.array([base[k]])
            row[f"{k}__std_in"] = round(float(arr.std()), 3)
            row[f"{k}__ptp_in"] = round(float(np.ptp(arr)), 3)
        rows.append(row)
    return rows, ch

def collect_health_files(root):
    """Рекурсивно собирает health-файлы из root и подпапок (speed/torque_circulation).
       Отбор регуляркой по Nm/rpm — защита от опечаток в слове circulation."""
    found = glob.glob(os.path.join(root, "**", "*.csv"), recursive=True)
    out = []
    for p in found:
        b = os.path.basename(p).lower()
        if b.startswith("health") and re.search(r"\d+nm", b) and re.search(r"\d+rpm", b):
            out.append(p)
    return sorted(out)

def make_plots(tab, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    C = {"speed": "#1f77b4", "torque": "#ff7f0e"}
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))

    # (1) f1 vs rpm — линейность => 2 полюса и работа привода
    for proto, g in tab.groupby("protocol"):
        ax[0, 0].scatter(g["rpm_meas"], g["f1_Hz"], c=C.get(proto, "gray"),
                         label=proto, s=45, edgecolor="k", lw=0.4)
    rr = np.array([tab["rpm_meas"].min(), tab["rpm_meas"].max()])
    ax[0, 0].plot(rr, rr / 60.0, "k--", lw=0.8, label="f1 = rpm/60 (иде-ал 2 полюса, s=0)")
    ax[0, 0].set(title="f1 vs скорость (линейность => 2 полюса)",
                 xlabel="об/мин", ylabel="f1, Гц"); ax[0, 0].legend(fontsize=8); ax[0, 0].grid(alpha=0.3)

    # (2) slip vs скорость, по нагрузке
    for (proto, load), g in tab.groupby(["protocol", "load_nominal_Nm"]):
        ax[0, 1].scatter(g["rpm_meas"], g["slip_pct"], c=C.get(proto, "gray"),
                         marker="o" if load == 40 else "s", s=45, edgecolor="k", lw=0.4,
                         label=f"{proto} {load}Н·м")
    ax[0, 1].set(title="Скольжение vs скорость", xlabel="об/мин", ylabel="s, %")
    ax[0, 1].legend(fontsize=7); ax[0, 1].grid(alpha=0.3)

    # (3) полы боковых полос vs скорость, с внутриполочным разбросом
    for proto, g in tab.groupby("protocol"):
        ax[1, 0].errorbar(g["rpm_meas"], g["sb_floor_bb_dB"], yerr=g["sb_floor_bb_dB__ptp_in"],
                          fmt="o", c=C.get(proto, "gray"), capsize=3, label=f"{proto} обрыв-пол",
                          ms=6, mec="k", mew=0.4)
    ax[1, 0].set(title="Пол полос обрыва стержня (± разброс) — будущий порог",
                 xlabel="об/мин", ylabel="дБ отн. f1"); ax[1, 0].legend(fontsize=8); ax[1, 0].grid(alpha=0.3)

    # (4) 1x вибрации по 3 осям vs скорость
    for lab, mk in zip(("c2", "c3", "c4"), ("o", "s", "^")):
        ax[1, 1].scatter(tab["rpm_meas"], tab[f"vib_1x_{lab}"], marker=mk, s=45,
                         edgecolor="k", lw=0.4, label=f"1x {lab}")
    ax[1, 1].set(title="1x вибрации по осям vs скорость (база остаточного дисбаланса)",
                 xlabel="об/мин", ylabel="амплитуда (отн.)"); ax[1, 1].legend(fontsize=8); ax[1, 1].grid(alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(out_dir, "health_baseline_validation.png")
    plt.savefig(fig_path, dpi=120)
    print("График:", fig_path)

def crossing_report(tab):
    """Согласованность метрик в точках, достигнутых ОБОИМИ протоколами
       (одинаковые rpm_level и нагрузка) — стоимость объединения протоколов."""
    print("\n=== Точки пересечения протоколов (σ_между) ===")
    key = ["rpm_level", "load_nominal_Nm"]
    any_found = False
    for (lvl, load), g in tab.groupby(key):
        if g["protocol"].nunique() < 2:
            continue
        any_found = True
        print(f"  {lvl} об/мин, {load} Н·м  (протоколы: {sorted(g['protocol'].unique())})")
        for k in ["f1_Hz", "slip_pct", "sb_floor_bb_dB", "cur_sb_1x_dB"]:
            sp = g[g.protocol == "speed"][k].mean(); tq = g[g.protocol == "torque"][k].mean()
            print(f"     {k:16s}: speed {sp:8.3f} | torque {tq:8.3f} | Δ {abs(sp - tq):7.3f}")
    if not any_found:
        print("  (нет режимов, покрытых обоими протоколами в этом наборе)")

def main():
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    print("Корень поиска:", root)
    files = collect_health_files(root)
    if not files:
        print("Health-файлы не найдены (искал рекурсивно health_*Nm*rpm*.csv)."); return
    print(f"Найдено файлов: {len(files)}")
    all_rows = []; chmaps = []
    for f in files:
        print("...", os.path.relpath(f, root))
        rows, ch = process_file(f)
        all_rows += rows; chmaps.append((os.path.basename(f), ch))
    tab = pd.DataFrame(all_rows)
    out = os.path.join(root, "health_baseline_plateaus.csv")
    tab.to_csv(out, index=False)

    # --- санитария: консистентность карты каналов ---
    print("\n=== Карта каналов по файлам ===")
    ref = chmaps[0][1]; consistent = True
    for name, ch in chmaps:
        same = (ch["keyphase"] == ref["keyphase"] and ch["current"] == ref["current"]
                and ch["vibration"] == ref["vibration"])
        consistent &= same
        print(f"  {name}: kp={ch['keyphase']} cur={ch['current']} vib={ch['vibration']} "
              f"timer={ch['timer']} {'' if same else '<< ОТЛИЧАЕТСЯ'}")
    print(f"  консистентна: {consistent}")
    # слип в диапазоне?
    bad = tab[(tab.slip_pct <= 0) | (tab.slip_pct > 6)]
    print(f"  слип вне (0..6%]: {len(bad)} полок" + (" — OK" if bad.empty else " << ПРОВЕРИТЬ"))

    pd.set_option("display.width", 260, "display.max_columns", 80)
    show = ["protocol", "load_nominal_Nm", "rpm_meas", "on_grid", "f1_Hz", "slip_pct",
            "sb_offset_Hz", "sb_floor_bb_dB", "cur_sb_1x_dB",
            "vib_1x_c2", "vib_1x_c3", "vib_1x_c4", "thd_pct", "unbalance_pct", "n_sub"]
    print("\n=== База по полкам (ключевые столбцы) ===")
    print(tab[show].to_string(index=False))
    crossing_report(tab)
    make_plots(tab, root)
    print("\nСохранено:", out)
    return tab

if __name__ == "__main__":
    main()
