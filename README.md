# motor-fault-diagnosis

**Physics-first fault diagnosis of an induction motor — an open research series on public data.**

Electrical Signature Analysis (MCSA) and vibration analysis of a 2.2 kW VFD-driven induction
motor: healthy baseline → broken rotor bar → rotor imbalance → (in progress) misalignment,
bearings. Every claim is validated against the physics of the machine, every threshold is
justified, negative controls are run, and dead ends are documented instead of hidden.

> **Why this repo looks the way it does.** This is not a "train a classifier on
> spectrograms" project. The goal is a diagnosis you can *defend*: each fault signature is
> predicted from first principles, located where the physics says it must be, checked
> against controls where it must be absent, and pushed until the method's real limits are
> found. Machine learning may come later — after the signal-level ground truth is solid.

---

## Key results so far

| # | Result | Evidence |
|---|--------|----------|
| 1 | **Healthy baseline built per operating point** — 26 plateaus across two rig protocols: working point (f1, slip), signature floors, current unbalance / THD, vibration 1×/2×/3× per axis, within-plateau spreads | `01_health`, [baseline catalog](docs/health_baseline_catalog.md) |
| 2 | **Pole count confirmed from data, not the nameplate** — f1 vs rpm regression, R² = 0.999; the small slope excess over 1.0 encodes the mean slip (~1.4 %) | `01_health` |
| 3 | **No torque channel in the data** → load read *through slip* (slip as load proxy), computed per plateau | `01_health` |
| 4 | **Vibration axes identified from physics** (speed-dependence + resonance response): c3 = main radial, c4 = axial | `01_health` |
| 5 | **Test-rig resonance near 50 Hz proven by two independent tests** — a fixed 50.0 ± 0.7 Hz peak while speed changes six-fold, and a ×9–14 amplification of 1× over the ω² law as it sweeps through 50 Hz. Consequence: the 3000 rpm point is excluded from any "1× vs speed" law | [resonance report](docs/health_resonance_report.md) |
| 6 | **Broken rotor bar detected by MCSA** — the f1·(1 ± 2ks) sideband comb, k = 1, 2, 3; band positions track measured slip to fractions of a Hz across all 12 files | `02_broken_bar`, [full report](docs/broken_bar_report.md) |
| 7 | **Two negative controls pass** — phase unbalance stays at baseline (0.06–0.34 %), and a signature-free control zone (f1 ± fr) stays empty | `02_broken_bar` |
| 8 | **A naive alarm indicator fails on real rig data — and is replaced.** "Level minus healthy floor" scatters by up to ~15 dB between rig protocols at the same operating point, and the floor is simply *undefined* in 4 of 6 torque regimes. Replaced with a **self-sufficient SNR** (band prominence over its own local floor in the same window) — no cross-protocol calibration needed | [report §5.2](docs/broken_bar_report.md) |
| 9 | **Load is the strength axis, speed is the resolvability axis** — median first-band SNR 37 dB at 40 Nm vs 19 dB at 20 Nm; the true method limit found at low speed + high load (477 rpm, f1 ≈ 8.3 Hz: the 0.72 Hz offset hugs the f1 skirt, SNR drops to ~2 dB) | [report §5.3–5.4](docs/broken_bar_report.md) |
| 10 | **The ω² law of rotor imbalance holds** — vibration 1× vs rotation frequency fits n = 2.11, R² = 0.981 over 12 plateaus, both loads on one line; load-independence control CoV 0.8–6.8 % per file; the 50 Hz resonance amplifies the fault 1× ×4.7–5.5 (the max-sensitivity zone, excluded from the law) | `03_rotor_unbalance`, [imbalance report](docs/imbalance_report.md) |
| 11 | **The 2-pole trap found, dissected and closed** — on a 2-pole machine the EM line at f1 sits only s·f1 from the mechanical 1×; a wide peak search returned the wrong line and bent the ω² exponent to ~1. Fixed with a narrow keyphase-anchored measurement, a per-window resolvability passport and a *measured* masker; two low-speed method limits documented (one with the masker measured, one an open question); a candidate ~16.5 Hz **axial** rig mode flagged for the misalignment episode. Both wrong runs are preserved in the repo | [imbalance report §3–6](docs/imbalance_report.md) |

---

## The data

**Dataset:** *Multi-mode Fault Diagnosis Datasets of Three-phase Asynchronous Motor Under
Variable Working Conditions* (MCC5-THU), MCC5 Group Shanghai & Tsinghua University.
Public, on Mendeley Data: [doi:10.17632/6s3dggj9mw.1](https://data.mendeley.com/datasets/6s3dggj9mw/1).

- **Machine:** three-phase squirrel-cage induction motor, 2.2 kW, 2-pole, VFD-driven
- **Sampling:** 12 800 Hz, 90 s per record (1 152 000 samples/channel)
- **Channels used:** keyphase (once-per-rev), 3 phase currents, 3 vibration axes.
  Channels are identified **by signal shape**, not by assumed column order; the time-counter
  column is detected and dropped. No usable torque channel is present in the analyzed
  classes — load is the nominal value from the file name, slip is the load proxy.
- **Two rig protocols:** `speed_circulation` (load held, speed stepped) and
  `torque_circulation` (speed held, load swept 0 → nominal)
- **Classes:** healthy, single faults (broken bar, unbalance, misalignment, bearing…) and
  electromechanical compound faults, with severity levels for some classes

Raw CSVs are ~100 MB each and are **not** stored in this repository. Download the dataset
from Mendeley and place the files as described in each section's README.

---

## Repository map

```
├── 01_health/            ✅ healthy baseline + rig resonance check      (scripts, README, outputs)
├── 02_broken_bar/        ✅ broken rotor bar via MCSA, pure class       (scripts, README, outputs)
├── 03_rotor_unbalance/   ✅ imbalance via vibration 1×: the ω² law,
│                            the 2-pole trap, two low-speed limits       (scripts, README, outputs)
├── 04_...                ⏳ misalignment & bend, bearings — see the roadmap
├── common/               shared analysis module (health_baseline.py)
└── docs/                 full written reports, per-file catalogs, series roadmap
```

Each numbered section is **self-contained**: its own README (data layout, how to run,
outputs explained), its own scripts, and a copy of the shared module so it runs standalone.

- 📘 [Series roadmap](docs/series_roadmap.md) — the full episode plan and what each block closes
- 📗 [Health & resonance report](docs/health_resonance_report.md)
- 📕 [Broken-bar report](docs/broken_bar_report.md) — physics, method, all 12 files, both limits
- 📙 [Imbalance report](docs/imbalance_report.md) — the ω² law, the 2-pole trap in three runs, two low-speed limits
- 📒 [Imbalance catalog](docs/imbalance_catalog.md) — metrics, the resolvability passport, exclusion classes

---

## Method principles (used everywhere)

1. **Unit of analysis = plateau** (a steady operating point), never the whole file.
   f1 and slip are computed per plateau.
2. **Two spectral windows by purpose:** flat-top for amplitudes, Hann for floors / dB / SNR.
3. **Predict, then look.** Signature frequencies are computed from measured slip *first*;
   a real fault sits exactly where the physics puts it. A peak that doesn't track slip
   is not a broken bar.
4. **Negative controls are mandatory.** A detection claim is paired with a place the
   signature must *not* appear — and doesn't.
5. **Self-sufficient indicators over calibrated ones.** If a threshold needs a healthy
   background that doesn't reproduce between rig protocols, the threshold — not the data —
   is the problem.
6. **Errors stay in the record.** Two lived examples: file-name numbers misread as the
   plateau load (E1, rolled back and documented in the catalogs), and the 2-pole trap —
   a wide peak search returning the EM f1 line as the mechanical 1× (E3; both wrong runs
   preserved in `03_rotor_unbalance/outputs`, dissected in the report). The process is
   part of the result.
7. **Measure the masker.** When a neighbouring line can contaminate an indicator, its
   amplitude is recorded next to the indicator in every window — exclusion decisions are
   made on measurements, not on geometry.

---

## How to run

```bash
pip install numpy pandas scipy matplotlib   # Python 3.9+
```

Then follow the README inside each section — scripts auto-locate their data and run from
their own folder, e.g.:

```bash
cd 01_health/scripts
python health_baseline.py      # baseline table + validation figure + sanity report
python resonance_check.py      # two-test resonance verdict
```

---

## Roadmap (short version)

| Episode | Topic | Status |
|---|---|---|
| 1 | Health baseline + rig resonance | ✅ done |
| 2 | Broken rotor bar (MCSA), self-sufficient SNR indicator | ✅ pure class done |
| 3 | Rotor unbalance (ω² law, the 2-pole trap, low-speed limits) | ✅ done |
| 4 | Misalignment & shaft bend (separating the 1× family; needs the ~16.5 Hz axial-mode verdict first) | ⏳ next |
| 5–6 | Bearings: envelope analysis, raceway faults | planned |
| 7+ | Compound faults, severity axes, streaming engine, hardware (STM32) | planned |

Full version with what each episode *closes*: [docs/series_roadmap.md](docs/series_roadmap.md).

---

## Background

I come from **EMC engineering** — 5+ years localizing conducted-emission sources in power
converters by their spectral signatures (publications and utility-model patents in the
field), plus several years operating industrial power systems at a gas production
facility. Motor-current diagnostics and EMC turned out to be the same discipline:
**find the physical source behind a spectral line and prove it**. That background is why
this project treats VFD artifacts, measurement floors, and rig resonances as first-class
citizens rather than nuisances.

Questions, corrections, and challenges to any conclusion are welcome — open an issue.
