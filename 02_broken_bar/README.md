# 02_broken_bar — Broken rotor bar (pure class)

This section detects the first real fault: a **broken rotor bar**. It confirms the
fault's current signature, quantifies how well it can be seen across speed and load,
and **closes an open question from `01_health`** — how to build an alarm threshold when
the healthy background does not transfer between the two test protocols.

The answer built here is a **self-sufficient SNR indicator**, demonstrated against a
naive one on real data.

---

## 1. What this section produces

1. A **per-window table** of the sideband signature across every file, plus a
   **headline table** (one strongest, max-load point per file).
2. **Summary figures**: signature vs load, naive-vs-SNR indicator comparison, and the
   "signature follows slip" proof.
3. **Per-file diagnostic sheets** (6 panels each) showing the sideband comb, the
   analysis windows, the load axis, and the discrimination control.

---

## 2. Contents

```
02_broken_bar/
├── README.md                    ← this file
├── scripts/
│   ├── broken_bar_analyze.py    ← per-window analysis, tables, summary figures
│   ├── broken_bar_visualize.py  ← per-file 6-panel diagnostic sheets
│   └── health_baseline.py       ← shared module (copy of the one from 01_health)
├── outputs/                     ← generated CSV/PNG go here (see "How to run")
└── data/                        ← broken-bar CSVs (not in the repo — see repository root README)
```

> **Two dependencies to keep next to the scripts:**
> 1. **`health_baseline.py`** — the shared module both scripts import
>    (`import health_baseline as hb`). Keep a copy in this folder.
> 2. **`health_baseline_plateaus.csv`** — the healthy baseline table from `01_health`,
>    used by the *naive* indicator. `broken_bar_analyze.py` searches for it in the
>    script folder and nearby parent folders; you can also set its path explicitly
>    (see "Configuration"). If it is missing, the naive indicator is skipped and the
>    self-sufficient SNR indicator (the one we actually rely on) still works.

---

## 3. The signature and the data

### Physics (what we look for)

A broken bar breaks the symmetry of the rotor cage. This induces a backward-rotating
field, which shows up in the **stator current** as **sidebands** around the supply
line f1, at frequencies:

```
f = f1 · (1 ± 2k·s),   k = 1, 2, 3 …
```

- `f1` — supply frequency; `s` — slip; `k` — harmonic number.
- The first pair sits at an offset **2·s·f1** from f1, the second at **4·s·f1**, the
  third at **6·s·f1**. Together they form a **comb**.
- The lower sideband (LSB) is the primary indicator; the upper (USB) is weaker.

Three properties drive every check:
- **The bands track slip** — their position is fixed by the measured `s`. A real
  broken bar sits exactly where slip predicts; a random peak does not.
- **Strength grows with load** — more load ⇒ larger slip ⇒ bands further from f1 and
  higher in amplitude ⇒ easier to see.
- **The comb confirms** — the full k=1,2,3 series (not a single peak) is strong
  evidence of a genuine broken bar.

### Protocols and channels

Same as `01_health`: `speed_circulation` (load fixed, speed/f1 steps) and
`torque_circulation` (speed fixed, load swept 0 → nominal). Channels are identified by
signal shape (keyphase, 3 currents, 3 vibration axes; the time-counter column is
dropped; there is no torque channel). Load is the nominal from the file name; **slip is
the load proxy**.

### Data layout

The raw CSV files are large and are **not** stored in the repository. Obtain the
dataset as described in the repository root `README`, then place the broken-bar class
files so the scripts can find them (they search their own folder **recursively**):

```
02_broken_bar/scripts/
├── broken_bar_analyze.py
├── broken_bar_visualize.py
├── health_baseline.py
├── health_baseline_plateaus.csv        ← copy from 01_health (for the naive indicator)
├── speed_circulation/
│   └── broken_bar_H_speed_circulation_*Nm_*rpm_*.csv
└── torque_circulation/
    └── broken_bar_H_torque_circulation_*Nm_*rpm_*.csv
```

Files are matched by a regex on `…Nm…rpm…` in the name; the healthy baseline CSV is
excluded automatically.

---

## 4. Requirements

- Python 3.9+
- `numpy`, `pandas`, `scipy`, `matplotlib`

```bash
pip install numpy pandas scipy matplotlib
```

---

## 5. How to run

Run from the folder that contains the scripts and the data (paths are auto-located).

```bash
# 1) Per-window analysis: tables + summary figures + console headline report
python broken_bar_analyze.py

# 2) Per-file diagnostic sheets (all files, or filter by a name substring)
python broken_bar_visualize.py
python broken_bar_visualize.py 40Nm      # only files whose name contains "40Nm"
```

Generated files appear **next to the script**; move them into `outputs/` afterwards to
keep the repo tidy.

### Configuration (top of `broken_bar_analyze.py`)

- `WIN_SEC` — analysis window length (default 8 s ⇒ frequency resolution ≈ 0.125 Hz).
  Shorter = more slip-stable but coarser resolution.
- `HEALTH_CSV` — explicit path to `health_baseline_plateaus.csv`. Leave empty to
  auto-search the script folder and nearby parent folders.

---

## 6. Outputs, explained

### `broken_bar_analyze.py`
- **`broken_bar_windows.csv`** — one row per slip-stable analysis window. Key columns:
  `protocol`, `load_nominal_Nm`, `rpm`, `slip_pct`, `off_2s_Hz` (= 2·s·f1),
  `resolvable`, `lsb1_dB` / `usb1_dB`, `lsb1_snr` / `usb1_snr`, `headline_snr`,
  `naive_rise_dB`, `comb_coherence`, `unbalance_pct` (control),
  `ctrl_fr_snr` (imbalance-band control), and `lsb2/3_snr`, `usb2/3_snr` (comb).
- **`broken_bar_headline.csv`** — one row per file: the **max-load** (max-slip)
  resolvable window — the strongest operating point.
- **`broken_bar_signature.png`** — 2 panels:
  1. **signature (band SNR) vs slip** = the load axis;
  2. **naive rise vs self-sufficient SNR** — shows the naive indicator scattering
     between protocols while SNR stays tight.
- **`broken_bar_signature_track.png`** — sideband offset vs slip: the linear trend is
  the "signature follows slip" proof.
- **Console** — the headline table and a per-file summary.

### `broken_bar_visualize.py`
- **`bbviz_<filename>.png`** — one 6-panel sheet per file:
  (1) speed profile with slip-stable windows shaded and the max-load window boxed;
  (2) current spectrogram; (3) the **sideband comb** on the max-load window with the
  predicted k=1,2,3 positions; (4) **signature vs slip** for this file (load axis);
  (5) full current spectrum with noise floor; (6) **control** — the broken-bar zone
  (2·s·f1, peaks present) next to the imbalance zone (f1±fr, empty), i.e. this is a
  rotor bar, not imbalance.

---

## 7. Key results established here

- **Signature confirmed on all files** — the sidebands sit exactly where slip predicts
  (position error of a fraction of a Hz), and the full comb k=1,2,3 is present.
- **Self-sufficient SNR beats the naive indicator** — the naive "rise over the healthy
  floor" scatters by up to ~15 dB between protocols at the same regime, so no single
  threshold fits it; the SNR of the same points stays tight. **Diagnosis is built on
  SNR.** (The naive indicator is also *unavailable* where the healthy floor was
  undefined — an extra argument for SNR.)
- **Load is the strength axis** — under heavy load (40 Nm) the band SNR is ~37–44 dB;
  under light load (20 Nm) ~15–26 dB. Broken bars are most reliably caught under load.
- **Two distinct resolvability limits:**
  1. *False limit (load-mixing artifact)* — in `torque_circulation` at light load, a
     merged window averages over the load sweep and destroys the band. Fixed by
     **slip segmentation** (the method used here); the signature comes back.
  2. *True limit (physics)* — at `speed 40 Nm / 1000 rpm`, slip is high but f1 is only
     ~8 Hz, so the offset (~0.7 Hz) hugs the f1 skirt and the band drowns
     (SNR ≈ 2 dB). Signature **strength grows with load**, but **resolvability grows
     with speed** — at low speed + high load they conflict.

---

## 8. Analysis conventions specific to this section

- **Unit of analysis = a slip-stable window.** In `speed_circulation` these fall inside
  speed plateaus; in `torque_circulation` they are short segments of constant load.
  The per-file **headline** metric is taken on the **max-load** window.
- **Slip segmentation is mandatory in `torque_circulation`** — never analyse the whole
  merged plateau, because the load (and thus slip and band offset) drifts within it.
- **Comb k=1,2,3** is measured for robustness against false peaks.
- **Two controls** confirm the fault is a rotor bar: current **unbalance** must not
  rise (else it is a stator problem), and the **f1±fr** imbalance zone must stay empty
  (else it is imbalance).

---

## 9. Honest boundaries

- **Only the severe defect (label H)** is present — no severity grades — so there is no
  "defect depth / number of broken bars" axis; only speed and load axes.
- **Number of broken bars** is not calibrated (needs severity grades); qualitative only.
- **No time-degradation recording** — any early-warning demo must model the growth rate
  and say so explicitly.
- **Composite classes** (bar + bearing) are treated only by their **rotor part**
  (current); the bearing part belongs to a later section.

---

## 10. Troubleshooting

- *"Broken-bar files not found"* — the CSVs are not under the script's folder, or their
  names don't contain `…Nm…rpm…`.
- *Import error for `health_baseline`* — put a copy of `health_baseline.py` in this
  folder.
- *`naive_rise_dB` is empty / "health floor not found"* — copy
  `health_baseline_plateaus.csv` here, or set `HEALTH_CSV`. SNR results are unaffected.
- *A regime is flagged `resolvable = NO`* — expected at low speed + high load
  (e.g. `speed 40 Nm / 1000 rpm`); the method marks it rather than reporting noise.
