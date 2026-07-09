"""
resonanse_check.py — проверка гипотезы РЕЗОНАНСА стенда около 50 Гц / 3000 об/мин.

Контекст: в health-базе 1× вибрации на оси c3 подскочил на 3000 об/мин заметно
сильнее закона ω² (≈×30 на удвоение скорости вместо ×4). Две гипотезы:
  H1 — механический резонанс конструкции у ~50 Гц (усиливает 1×, когда fr туда въезжает);
  H2 — просто степенной рост 1× дисбаланса, без резонанса.

РЕШАЮЩИЙ ТЕСТ: резонанс сидит на ФИКСИРОВАННОЙ частоте независимо от оборотов,
а 1× едет с частотой вращения. Промежуточные полки speed-протокола ставят 1× на
24–41 Гц (в стороне от 50). Если на них в спектре c3 есть НЕПОДВИЖНЫЙ пик у ~50 Гц
(отдельно от 1×), а на 3000 об/мин 1× в него въезжает и раздувается — это H1.

Скрипт кладётся в папку Health и сам находит health-файлы (обе подпапки).
Переиспользует опознание каналов из health_baseline.py (лежит рядом).

Выход:
  resonance_c3_spectra_overlay.png  — наложение спектров c3 с разных скоростей
  resonance_transmissibility.png    — 1× vs fr (log-log) + эталон ω², и 1x/fr²
  консоль — вердикт: есть ли фиксированный пик у 50 Гц и во сколько раз 3000
            превышает степенную экстраполяцию.
"""
import os, sys, glob, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import health_baseline as hb   # load_clean, classify, instantaneous_rpm, detect_plateaus, f1_of
FS = hb.FS

RES_BAND = (40.0, 60.0)     # где ищем фиксированный пик резонанса, Гц
FIXED_TOL = 3.0             # разброс положения «фиксированного» пика между полками, Гц

# --- линейный спектр вибрации (Ханнинг, односторонний) ---
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
    """Все полки всех health-файлов -> список (rpm, fr, срез сигнала X, каналы)."""
    files = hb.collect_health_files(SCRIPT_DIR)
    if not files:
        print("Health-файлы не найдены рядом со скриптом."); sys.exit(1)
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
    """Ось с наибольшим ростом 1× к высокой скорости = главная радиальная (c3)."""
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
    print(f"Каналы вибрации (столбцы): {vib_idx} -> {labels}")
    print(f"Главная радиальная ось (макс. 1× на высокой скорости): столбец {prim} = {labels[prim_pos]}")
    print(f"  1× на верхней полке по осям: " +
          ", ".join(f"{labels[i]}={a:.5f}" for i, a in enumerate(amps_hi)))

    plats = sorted(plats, key=lambda d: d["rpm"])

    # ---------- ТЕСТ 1: фиксированный пик у 50 Гц на нерезонансных полках ----------
    print("\n=== Тест 1: неподвижный пик в полосе 40–60 Гц (вне зоны 1×) ===")
    print(f"  {'rpm':>6} {'fr(1×),Гц':>10} {'пик≠1× в 40-60,Гц':>18} {'ампл':>10}")
    fixed_hits = []
    for d in plats:
        f, sp = vib_spectrum(d["seg"][:, prim])
        fc, a = peak_in_band(f, sp, *RES_BAND, exclude_fc=d["fr"])
        # интересны полки, где 1× НЕ в полосе резонанса (fr вне 40-60 ± tol)
        off = not (RES_BAND[0] - 3 <= d["fr"] <= RES_BAND[1] + 3)
        mark = ""
        if off and not np.isnan(fc):
            fixed_hits.append(fc); mark = "  <- фиксированный?"
        print(f"  {d['rpm']:6.0f} {d['fr']:10.1f} {fc:18.1f} {a:10.5f}{mark}")
    if len(fixed_hits) >= 2:
        med = np.median(fixed_hits); spread = np.ptp(fixed_hits)
        verdict1 = (spread <= FIXED_TOL)
        print(f"  фиксированный пик: медиана {med:.1f} Гц, разброс {spread:.1f} Гц "
              f"-> {'ПОДТВЕРЖДАЕТ резонанс' if verdict1 else 'положение плывёт (не фиксирован)'}")
    else:
        verdict1 = None
        print("  недостаточно нерезонансных полок для вывода")

    # ---------- ТЕСТ 2: 1× vs fr, отклонение от ω² ----------
    print("\n=== Тест 2: усиление 1× относительно закона ω² ===")
    fr = np.array([d["fr"] for d in plats])
    a1 = np.array([amp_at(*vib_spectrum(d["seg"][:, prim]), d["fr"]) for d in plats])
    # опорный степенной закон по НИЖНИМ скоростям (fr < 40 Гц, до резонанса)
    lo = fr < 40
    if lo.sum() >= 3:
        cflog = np.polyfit(np.log(fr[lo]), np.log(a1[lo] + 1e-12), 1)
        slope = cflog[0]
        pred_hi = np.exp(np.polyval(cflog, np.log(fr)))
        amp_factor = a1 / (pred_hi + 1e-12)
        print(f"  степенной наклон по нижним скоростям: {slope:.2f} (ω² дал бы 2.0)")
        print(f"  {'rpm':>6} {'fr':>6} {'1×изм':>9} {'1×закон':>9} {'превышение×':>11}")
        for i in range(len(fr)):
            tag = "  <-" if amp_factor[i] > 2 else ""
            print(f"  {fr[i]*60:6.0f} {fr[i]:6.1f} {a1[i]:9.5f} {pred_hi[i]:9.5f} {amp_factor[i]:11.1f}{tag}")
        peak_factor = amp_factor.max(); peak_rpm = fr[np.argmax(amp_factor)] * 60
        verdict2 = peak_factor > 3
        print(f"  макс. превышение закона: ×{peak_factor:.1f} на {peak_rpm:.0f} об/мин "
              f"-> {'резонансное усиление' if verdict2 else 'в пределах степенного роста'}")
    else:
        verdict2 = None; amp_factor = None
        print("  мало точек ниже 40 Гц для опорного закона")

    # ---------- Графики ----------
    # (1) наложение спектров c3
    fig, ax = plt.subplots(figsize=(13, 7))
    cmap = plt.cm.viridis(np.linspace(0, 1, len(plats)))
    for d, c in zip(plats, cmap):
        f, sp = vib_spectrum(d["seg"][:, prim])
        m = f <= 160
        ax.semilogy(f[m], sp[m] + 1e-9, lw=0.8, color=c, alpha=0.8,
                    label=f"{d['rpm']:.0f} об/мин (1×={d['fr']:.0f})")
        ax.plot(d["fr"], amp_at(f, sp, d["fr"]) + 1e-9, "o", color=c, ms=5, mec="k", mew=0.4)
    ax.axvspan(RES_BAND[0], RES_BAND[1], color="red", alpha=0.08)
    ax.axvline(50, color="red", ls="--", lw=1, label="подозрение на резонанс ~50 Гц")
    ax.set(xlabel="частота, Гц", ylabel=f"амплитуда {labels[prim_pos]} (отн.)",
           title="Наложение спектров вибрации c3 по скоростям\n"
                 "кружок = 1× каждой полки; ищем НЕПОДВИЖНЫЙ пик у 50 Гц")
    ax.legend(fontsize=7, ncol=2); ax.grid(True, which="both", alpha=0.3)
    plt.tight_layout(); p1 = os.path.join(SCRIPT_DIR, "resonance_c3_spectra_overlay.png")
    plt.savefig(p1, dpi=120); print("\nГрафик:", p1)

    # (2) транссмиссивность
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))
    ax[0].loglog(fr, a1 + 1e-12, "o", ms=6, mec="k", mew=0.4, label="1× изм.")
    if lo.sum() >= 3:
        order = np.argsort(fr)
        ax[0].loglog(fr[order], pred_hi[order], "r--", lw=1, label=f"степень×{slope:.1f}")
        ax[0].loglog(fr[order], (a1[lo][0]*(fr/fr[lo][0])**2)[order], "g:", lw=1, label="эталон ω²")
    ax[0].set(xlabel="fr, Гц", ylabel="1× амплитуда", title="1× vs частота вращения (log-log)")
    ax[0].legend(fontsize=8); ax[0].grid(True, which="both", alpha=0.3)
    comp = a1 / (fr ** 2 + 1e-12)      # податливость ~ пик у резонанса
    ax[1].plot(fr, comp / np.nanmedian(comp), "o-", ms=5)
    ax[1].axvline(50, color="red", ls="--", lw=1)
    ax[1].set(xlabel="fr, Гц", ylabel="1×/fr² (норм.)",
              title="Механическая податливость 1×/fr² (пик = резонанс)")
    ax[1].grid(True, alpha=0.3)
    plt.tight_layout(); p2 = os.path.join(SCRIPT_DIR, "resonance_transmissibility.png")
    plt.savefig(p2, dpi=120); print("График:", p2)

    # ---------- Вердикт ----------
    print("\n" + "=" * 60)
    print("ВЕРДИКТ:")
    v = []
    if verdict1 is True: v.append("фиксированный пик у ~50 Гц ЕСТЬ")
    elif verdict1 is False: v.append("фиксированного пика НЕТ")
    if verdict2 is True: v.append("1× превышает ω² в разы у 3000")
    elif verdict2 is False: v.append("рост 1× в пределах степенного")
    print("  " + "; ".join(v) if v else "  недостаточно данных")
    if verdict1 and verdict2:
        print("  => РЕЗОНАНС стенда у ~50 Гц ПОДТВЕРЖДЁН. На 3000 об/мин строить")
        print("     закон 'подъём 1× от скорости' нельзя — точка резонансно раздута.")
    elif verdict1 is False and verdict2 is False:
        print("  => Резонанс НЕ подтверждён; всплеск на 3000 нуждается в другом объяснении.")
    else:
        print("  => Картина смешанная, см. графики (возможно резонанс на краю диапазона).")

if __name__ == "__main__":
    main()