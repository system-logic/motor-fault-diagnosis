# 03_rotor_unbalance — Rotor imbalance (pure class)

This section detects the first **mechanical** fault — rotor imbalance — through
**vibration**, and closes an open item from `01_health`: the ω² law of the 1× component
with correct handling of the ~50 Hz rig resonance.

It is also the section where the analysis itself was caught making a mistake — twice —
and both intermediate runs are preserved as part of the result (**the 2-pole trap**,
see §7 and `docs/imbalance_report.md`).

---

## 1. What this section produces

1. A **per-window table** of the 1×/2×/3× vibration metrics with a per-window
   *resolvability passport* for the f1↔fr proximity, plus a **headline table**
   (one strongest *clean* window per file).
2. **Summary figures**: the ω² law with three exclusion classes marked, the
   load-independence control, radial-vs-axial control.
3. **Per-file diagnostic sheets** (6 panels each).

---

## 2. Contents

```
03_rotor_unbalance/
├── README.md                    ← this file
├── scripts/
│   ├── imbalance_analyze.py     ← per-window analysis, tables, summary figures
│   ├── imbalance_visualize.py   ← per-file 6-panel diagnostic sheets
│   └── health_baseline.py       ← shared module (copy of the one from 01_health)
├── outputs/                     ← generated CSV/PNG (final run)
│   ├── 1_Trap results/          ← run 1 (the trap), preserved
│   └── 2_Trap results/          ← run 2 (the half-fix), preserved
└── data/                        ← Rotor_Unbalance CSVs (not in the repo — see root README)
```

> **Two dependencies to keep next to the scripts:**
> 1. **`health_baseline.py`** — the shared module (`import health_baseline as hb`).
> 2. **`health_baseline_plateaus.csv`** — the healthy 1× reference from `01_health`
>    for the `r1x_over_health` ratio. Auto-searched in the script folder and nearby
>    parents; without it the ratio is skipped, everything else works.

---

## 3. The signature and the data

### Physics (what we look for)

An offset mass *m* at radius *e* creates a rotating centrifugal force **F = m·e·ω²**.
Everything testable follows from this one formula:

- **Frequency:** exactly **1× = fr** (rpm/60). One rotating force — one line.
- **Growth:** amplitude ∝ **ω²** → slope 2 on a log-log plot of 1× vs fr.
- **Direction:** **radial** (the force rotates in the shaft-normal plane); the axial 1×
  must stay low — a strong axial 1× points to misalignment/bend (Episode 4).
- **Load independence:** *m* and *e* don't know the torque → at fixed speed the 1× is
  **flat** across the load sweep.
- **Current cross-check:** eccentric rotation weakly modulates the air gap → f1 ± fr
  sidebands in current (supporting evidence only).

The primary metric is **R1x = √(1×c2² + 1×c3²)** — the response splits between the two
radial axes, so a single axis undercounts it.

### The 2-pole complication (read before touching the numbers)

On a 2-pole machine **fr = f1·(1 − s)**: the electromagnetic line at f1 sits only
**s·f1 Hz** (fractions of a Hz at light load) above the mechanical 1×. Every window
therefore carries a *resolvability passport*: `sep_Hz`, `sep_bins = |f1−fr|/df`, and
flags `f1_in_1x` (merged, sep < 3 bins), `f1_near_1x` (grey zone, kept and twin-checked),
`f1_in_2x` (the same trap at 2× — Episode 4 inherits it), `low_speed_em` (fr < 10 Hz,
a declared method limit), `slip_suspect` (slip < 0.05 %, f1 estimate unreliable).
Vibration harmonics are measured with a **narrow ±1-bin** search (fr is known precisely
from the keyphase). The masker itself is **measured** per window (`vib_f1_line`,
`em_over_1x`).

### Protocols, channels, data layout

Same as `01_health` / `02_broken_bar`: two protocols, channels identified by signal
shape, no torque channel, slip = load proxy. Data placement (scripts search their own
folder recursively; files matched by `…Nm…rpm…` in the name):

```
03_rotor_unbalance/scripts/
├── imbalance_analyze.py
├── imbalance_visualize.py
├── health_baseline.py
├── health_baseline_plateaus.csv        ← copy from 01_health (for the health ratio)
├── speed_circulation/
│   └── Rotor_unbalance_speed_circulation_*Nm_*rpm_*.csv
└── torque_circulation/
    └── Rotor_unbalance_torque_circulation_*Nm_*rpm_*.csv
```

---

## 4. Requirements

Python 3.9+; `numpy`, `pandas`, `scipy`, `matplotlib` (see root `requirements.txt`).

---

## 5. How to run

```bash
# 1) Per-window analysis: tables + summary figures + console report
python imbalance_analyze.py

# 2) Per-file diagnostic sheets (all files, or filter by name substring)
python imbalance_visualize.py
python imbalance_visualize.py 3000
```

Generated files appear next to the script; move them into `outputs/` afterwards.

### Configuration (top of `imbalance_analyze.py`)

- `RESONANCE_HZ` / `RES_GUARD_HZ` — the ~50 Hz rig mode from `01_health` and its guard.
- `AXIAL_RES_HZ = 16.5` — the **candidate** axial rig mode found in this episode
  (flagging only; to be confirmed on health data — Episode 4 prerequisite).
- `SEP_HARD_BINS = 3` — merged-lines exclusion; `SEP_MARGINAL_BINS = 8` — grey zone.
- `LOWSPEED_FR_HZ = 10` — the declared low-speed limit (see §7).
- `WIN_SEC` — torque-protocol window (default 8 s).

---

## 6. Outputs, explained

### `imbalance_analyze.py`
- **`imbalance_windows.csv`** — one row per window: working point (`fr_Hz`, `f1_Hz`,
  `slip_pct`), `R1x`, `R2x_ratio`/`R3x_ratio`, `axial_1x`/`axial_ratio`,
  `onex_snr_dB` (self-sufficient SNR), the resolvability passport (`sep_Hz`, `sep_bins`,
  flags), the measured masker (`vib_f1_line`, `em_over_1x`), resonance flags,
  `r1x_over_health`, controls (`unbalance_pct`, `cur_sb_1x_snr`).
- **`imbalance_headline.csv`** — one row per file: the strongest **clean** window.
- **`imbalance_omega2.png`** — the ω² law with all three exclusion classes marked
  (resonance rings, merged-lines cross, low-speed-limit grey square).
- **`imbalance_load_independence.png`** — R1x vs slip per torque file (flat = rotor).
- **`imbalance_radial_vs_axial.png`** — the direction control (note the ~16.5 Hz
  axial anomaly, §7).
- **Console** — headline table, the trap census, per-level **twin check** (flagged vs
  clean windows at the same speed; ~1.0 = the flags are protective, not destructive).

### `imbalance_visualize.py`
- **`ubviz_<filename>.png`** — 6 panels: (1) speed profile + windows, headline (clean)
  boxed; (2) vibration spectrogram of the dominant radial axis; (3) radial waveform over
  ~4 revolutions; (4) full radial spectrum with 1×/2×/3× and the 50 Hz line;
  (5) 1× zoom with local floor → SNR₁ₓ; (6) control — radial vs axial 1× (speed) or
  R1x vs slip (torque). The title carries `sep` in bins and the exclusion flags.

---

## 7. Key results established here

- **The ω² law holds: n = 2.11, R² = 0.981** — 12 plateaus, 16–41 Hz, both loads on one
  line (itself a second confirmation of load independence).
- **Load independence: CoV 0.8–6.8 %** per torque file across the full load sweep.
- **The ~50 Hz resonance amplifies the fault ×4.7–5.5** over the law and gives the
  largest health ratios (2.8) — a sensitivity zone, deliberately excluded from the law.
- **Detection vs health is modest at working regimes (×1.3–1.9)** — a defensible
  threshold requires the healthy 1× spread (open task).
- **The 2-pole trap, documented:** a wide ±4-bin peak search returned the EM f1 line as
  "the 1×" (run 1, exponent bent to 0.96); a bin-distance filter then failed in both
  directions (run 2). Final rule: narrow measurement + merged-lines exclusion + measured
  masker. Full story: `docs/imbalance_report.md`, artifacts in `outputs/1_Trap results`
  and `2_Trap results`.
- **Two distinct low-speed limits at ~8 Hz:** at 20 Nm the EM line and the 1× are
  physically merged (masker measured); at 40 Nm the lines are separable, the f1 line is
  quiet, yet the 1× carries a ×10 off-law excess — **mechanism unidentified, open
  question**. Mirrors the broken-bar 477 rpm limit: the same low-speed corner is blind
  for both methods, for different reasons.
- **Unplanned discovery — candidate axial rig mode ~16.5 Hz:** the axial 1× spikes
  8–10× above radial exactly at fr ≈ 16.2–16.5 Hz, in both loads and in the *healthy*
  data too. Until confirmed by the Episode-1-style fixed-peak test, the axial control at
  ~1000 rpm is not to be taken at face value. **Blocking prerequisite for Episode 4.**

---

## 8. Analysis conventions specific to this section

- Unit of analysis: speed protocol → one window per plateau (≤18 s); torque protocol →
  8-s sliding windows across the load sweep.
- The ω² fit uses **speed-protocol windows only**, excluding `on_resonance`,
  `f1_in_1x`, `low_speed_em`, `slip_suspect`. Torque windows are the load control only.
- Headline = the strongest **clean** window (falls back to the global max only if no
  clean window exists in the file — then its health ratio is withheld).
- Flat-top window for amplitudes, Hann for floors/SNR — as in Episodes 1–2.

---

## 9. Honest boundaries

- **No severity grades** for this class → speed and load axes only; the ×1.3–1.9 ratio
  cannot be mapped to grams·mm.
- **The healthy spread of the 1×** across protocols is not yet quantified → the
  detection verdict is "elevated", not "thresholded".
- **fr < 10 Hz is outside the method** on this rig (two mechanisms, one of them open).
- **The axial control at ~1000 rpm** is compromised by the candidate 16.5 Hz rig mode
  until the health-data check is run.

---

## 10. Troubleshooting

- *"Unbalance files not found"* — CSVs are not under the script folder or lack
  `…Nm…rpm…` in the name.
- *Import error for `health_baseline`* — put a copy of `health_baseline.py` here.
- *`r1x_over_health` empty* — copy `health_baseline_plateaus.csv` here.
- *A window flagged `f1_in_1x` / `low_speed_em`* — expected at near-zero slip and at
  fr < 10 Hz; the method marks its blind zones instead of reporting noise.
- *Headline of `torque 20 Nm 1000 rpm` has no health ratio* — all windows of that file
  sit at near-zero slip (lines merged); the withheld ratio is deliberate.
