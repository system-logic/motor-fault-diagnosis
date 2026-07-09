"""
broken_bar_visualize.py — диагностические листы по файлам обрыва стержня.

На каждый файл — лист из 6 панелей:
  (1) профиль скорости + окна анализа (зелёные — слип-стабильные, красная рамка —
      окно макс. нагрузки, по которому заголовочные метрики);
  (2) спектрограмма тока с границами окна макс. нагрузки;
  (3) ГРЕБЁНКА: спектр тока на окне макс. нагрузки с предсказанными полосами
      k=1,2,3 и измеренными пиками, подпись SNR первой полосы;
  (4) сигнатура (SNR) vs скольжение по всем окнам файла — ось нагрузки;
  (5) полный спектр тока с шумовым полом;
  (6) КОНТРОЛЬ: зона дисбаланса f1±fr (должна быть пустой) рядом с полосами
      обрыва — показываем, что это ротор-стержень, а не дисбаланс.

Кладётся в папку Broken_Bar рядом с health_baseline.py и broken_bar_analyze.py.
  python broken_bar_visualize.py           — все файлы
  python broken_bar_visualize.py 3000       — только файлы с 3000 в имени
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
import broken_bar_analyze as bb
FS = hb.FS

def spec_db(sig):
    x = (sig - sig.mean()) * np.hanning(len(sig)); sp = np.abs(np.fft.rfft(x)); sp[0] = 0
    f = np.fft.rfftfreq(len(x), 1 / FS); return f, 20 * np.log10(sp / (sp.max() + 1e-12) + 1e-12)

def noise_floor(f, spd, lo, hi):
    m = (f >= lo) & (f <= hi)
    return float(np.median(spd[m])) if m.any() else np.nan

def draw_sheet(path):
    fn = os.path.basename(path)
    X = hb.load_clean(path); ch = hb.classify(X)
    t, rpm = hb.instantaneous_rpm(X[:, ch["keyphase"]])
    A = X[:, ch["current"][0]]; proto = hb.protocol_of(fn)

    # окна анализа: слип-стабильные + выбор макс. нагрузки
    wins = []
    for ts, rpm_med, drift in bb.stable_windows(A, ch["current"], t, rpm):
        i0 = int(ts * FS); i1 = int((ts + bb.WIN_SEC) * FS)
        met = bb.sideband_metrics(A[i0:i1], rpm_med)
        smear = drift / 30.0
        stable = smear < max(met["df"], bb.STAB_FACTOR * met["off_2s"]) and met["off_2s"] > 0
        wins.append(dict(ts=ts, rpm=rpm_med, slip=met["slip"], off=met["off_2s"],
                         snr=met["lsb1_usb1_snr"], stable=stable,
                         resolvable=met["resolvable"], f1=met["f1"], fr=met["fr"]))
    good = [w for w in wins if w["stable"] and w["resolvable"]]
    if not good:
        good = [w for w in wins if w["stable"]] or wins
    head = max(good, key=lambda w: w["slip"])          # окно макс. нагрузки
    i0 = int(head["ts"] * FS); i1 = int((head["ts"] + bb.WIN_SEC) * FS)
    Aw = A[i0:i1]; f1 = head["f1"]; s = head["slip"] / 100; off = head["off"]; fr = head["fr"]

    fig = plt.figure(figsize=(16, 11)); gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.22)

    # (1) профиль + окна
    ax = fig.add_subplot(gs[0, 0]); ax.plot(t, rpm, lw=0.5, color="#333")
    for w in wins:
        if w["stable"]:
            ax.axvspan(w["ts"], w["ts"] + bb.WIN_SEC, color="#2ca02c", alpha=0.10, lw=0)
    ax.axvspan(head["ts"], head["ts"] + bb.WIN_SEC, color="none", ec="#d62728", lw=2)
    ax.set(title="(1) Скорость + окна анализа (зел.=стаб., крас.=макс.нагрузка)",
           xlabel="с", ylabel="об/мин")
    ax.legend(handles=[Patch(fc="#2ca02c", alpha=0.3, label="слип-стабильное окно"),
                       Patch(fc="none", ec="#d62728", label="окно макс. нагрузки")], fontsize=8)

    # (2) спектрограмма
    ax = fig.add_subplot(gs[0, 1])
    nper = 8192; fsg, tsg, Sxx = spectrogram(A - A.mean(), fs=FS, nperseg=nper, noverlap=nper // 2, scaling="spectrum")
    band = fsg <= 70; Sdb = 10 * np.log10(Sxx[band] + 1e-12)
    ax.pcolormesh(tsg, fsg[band], Sdb, shading="auto", cmap="magma",
                  vmin=np.percentile(Sdb, 40), vmax=np.percentile(Sdb, 99.9))
    ax.axvline(head["ts"], color="cyan", lw=1.2); ax.axvline(head["ts"] + bb.WIN_SEC, color="cyan", lw=1.2)
    ax.set(title="(2) Спектрограмма тока (голубое — окно макс. нагрузки)",
           xlabel="с", ylabel="Гц", ylim=(0, 70))

    # (3) гребёнка на окне макс. нагрузки
    ax = fig.add_subplot(gs[1, 0]); f, spd = spec_db(Aw)
    win = max(4 * off, 3.5); m = (f >= f1 - win) & (f <= f1 + win)
    ax.plot(f[m], spd[m], lw=0.9, color="#333")
    ax.axvline(f1, color="k", lw=1); ax.text(f1, 2, "f1", ha="center", fontsize=8)
    for k, col in zip((1, 2, 3), ("#d62728", "#ff7f0e", "#1f77b4")):
        for sgn in (-1, 1):
            ax.axvline(f1 + sgn * 2 * k * s * f1, color=col, ls="--", lw=0.9, alpha=0.8)
        ax.plot([], [], color=col, ls="--", label=f"k={k}")
    ax.set(title=f"(3) Гребёнка полос k=1,2,3 | SNR₁={head['snr']:.0f} дБ, s={head['slip']:.2f}%",
           xlabel="Гц", ylabel="дБ отн f1", ylim=(-95, 5)); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # (4) сигнатура vs слип (ось нагрузки)
    ax = fig.add_subplot(gs[1, 1])
    ws = [w for w in wins if w["stable"] and w["resolvable"]]
    if ws:
        ax.scatter([w["slip"] for w in ws], [w["snr"] for w in ws], s=30, c="#1f77b4",
                   edgecolor="k", lw=0.3, alpha=0.7)
    ax.scatter([head["slip"]], [head["snr"]], s=90, c="#d62728", edgecolor="k", zorder=5, label="макс. нагрузка")
    ax.set(title="(4) Сигнатура (SNR полосы) vs скольжение = ось нагрузки",
           xlabel="скольжение s, %", ylabel="SNR первой полосы, дБ"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # (5) полный спектр + шумовой пол
    ax = fig.add_subplot(gs[2, 0]); mf = f <= 6 * f1 + 20
    ax.plot(f[mf], spd[mf], lw=0.7, color="#1f77b4")
    for k in range(1, 7):
        if k * f1 <= f[mf].max():
            ax.axvline(k * f1, color="#ff7f0e", ls=":", lw=0.7)
    fl = noise_floor(f, spd, 1.5 * f1, 6 * f1)
    ax.axhline(fl, color="#d62728", ls="--", lw=1, label=f"шумовой пол ≈ {fl:.0f} дБ")
    ax.set(title="(5) Полный спектр тока (f1 и гармоники)", xlabel="Гц", ylabel="дБ отн f1",
           ylim=(-95, 5)); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # (6) контроль: зона дисбаланса f1±fr пуста, а полосы обрыва есть
    ax = fig.add_subplot(gs[2, 1])
    span = max(1.5 * fr, 4 * off); mc = (f >= f1 - span) & (f <= f1 + span)
    ax.plot(f[mc], spd[mc], lw=0.9, color="#333")
    ax.axvline(f1, color="k", lw=1)
    for sgn in (-1, 1):
        ax.axvline(f1 + sgn * off, color="#d62728", ls="--", lw=1)      # обрыв 2sf1
        ax.axvline(f1 + sgn * fr, color="#2ca02c", ls=":", lw=1.2)      # дисбаланс fr
    ax.plot([], [], color="#d62728", ls="--", label="полосы обрыва 2s·f1 (ЕСТЬ)")
    ax.plot([], [], color="#2ca02c", ls=":", label="зона дисбаланса f1±fr (пусто)")
    ax.set(title="(6) Контроль: это обрыв (2s·f1), а не дисбаланс (f1±fr)",
           xlabel="Гц", ylabel="дБ отн f1", ylim=(-95, 5)); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    fig.suptitle(f"{fn}  |  {proto}  |  окно макс. нагрузки: {head['rpm']:.0f} об/мин, "
                 f"f1={f1:.2f} Гц, s={head['slip']:.2f}%, 2s·f1={off:.2f} Гц, SNR₁={head['snr']:.0f} дБ",
                 fontsize=11, fontweight="bold", y=0.995)
    out = os.path.join(SCRIPT_DIR, "bbviz_" + os.path.splitext(fn)[0] + ".png")
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
        print("Файлы не найдены."); return
    print(f"Файлов: {len(files)}")
    for f in files:
        print("...", os.path.basename(f))
        out = draw_sheet(f); print("   ->", os.path.basename(out))
    print("Готово. Листы bbviz_*.png рядом со скриптом.")

if __name__ == "__main__":
    main()
