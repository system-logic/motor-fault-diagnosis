# 01_health — Healthy-motor baseline & rig resonance check

This section builds the **health baseline** of the motor — the reference picture of a
*healthy* machine — and validates it physically. Every later fault is detected as a
**deviation from this baseline**, so this is the foundation of the whole project.

It also contains a focused experiment that confirms a **mechanical resonance of the
test rig near 50 Hz**, a finding that shapes how vibration is interpreted later.

---

## 1. What this section produces

1. A **per-plateau baseline table** with all reference metrics (working point,
   signature floors, current unbalance/THD, spreads) across both test protocols.
2. **Validation figures** that prove the baseline is physically consistent
   (2 poles, slip behaviour, sideband floors, residual vibration).
3. **Per-file diagnostic sheets** (6 panels each) for visual inspection.
4. A **resonance verdict** with two figures, isolating the rig's ~50 Hz resonance.

---

## 2. Contents

```
01_health/
├── README.md                 ← this file
├── scripts/
│   ├── build_baseline.py     ← builds the baseline table (runner around common/health_baseline.py)
│   ├── health_visualize.py   ← per-file 6-panel diagnostic sheets
│   └── resonance_check.py    ← rig resonance hypothesis test
├── outputs/                  ← the scripts write here (CSV/PNG, committed)
└── data/                     ← health CSVs go here (not in the repo — see "Data layout")
```

> **Shared module.** All analysis code lives in **`common/health_baseline.py`** at the
> repository root — channel identification, plateaus, f1/slip, spectra, the baseline
> builder. Every script in every section imports it (`import health_baseline as hb`)
> through a path computed from its own location, so nothing has to be copied.

---

## 3. The motor and the data

**Object.** Three-phase squirrel-cage induction motor, 2.2 kW, **2-pole**, driven by a
variable-frequency drive (VFD). Sampling rate **12 800 Hz**, record length **90 s**
(1 152 000 samples per channel).

**Two test protocols** (both present for the healthy class):

| Protocol            | What is held         | What is swept                | Inside one file          |
|---------------------|----------------------|------------------------------|--------------------------|
| `speed_circulation` | load constant        | **speed** steps (f1 changes) | one load, several speeds |
| `torque_circulation`| speed constant       | **load** steps (0 → nominal) | one speed, several loads |

**Channels (8 columns, identified by signal shape — see findings below):**

| Column        | Channel                         |
|---------------|---------------------------------|
| col0          | time counter — **dropped**      |
| col1          | keyphase (once-per-rev pulse)   |
| col2, col3, col4 | vibration, 3 axes (`c2`,`c3`,`c4`) |
| col5, col6, col7 | current, 3 phases            |

There is **no torque channel**. Load is taken as the **nominal value from the file
name**; where a load axis is needed, **slip** is used as a load proxy.

### Data layout

The raw CSV files are large (~100 MB each) and are **not** stored in the repository.
Obtain the dataset as described in the repository root `README`, then place the
healthy-class CSVs under this section's **`data/`** folder (searched **recursively**;
the folder is git-ignored). Any sub-structure works; the dataset's own is fine:

```
01_health/data/
├── speed_circulation/
│   └── health_speed_circulation_*Nm_*rpm_*.csv
└── torque_circulation/
    └── health_torque_circulation_*Nm_*rpm_*.csv
```

On Windows a directory junction to the unpacked dataset avoids copying:
`mklink /J 01_health\data "<dataset>\Health"`.

Files are matched by a regex on `…Nm…rpm…` in the name (this tolerates typos in the
word *circulation*), and must start with `health`.

---

## 4. Requirements

- Python 3.9+
- `numpy`, `pandas`, `scipy`, `matplotlib`

```bash
pip install numpy pandas scipy matplotlib
```

---

## 5. How to run

Run each script from `01_health/scripts/` (paths are derived from the script's own
location; nothing to edit):

```bash
# 1) Build the baseline table + validation figure + console sanity report
python build_baseline.py
python build_baseline.py <folder>      # or point it at any folder of health CSVs

# 2) Per-file diagnostic sheets (all files, or filter by a name substring)
python health_visualize.py
python health_visualize.py 3000        # only files whose name contains "3000"

# 3) Rig resonance test (two figures + a printed verdict)
python resonance_check.py
```

All generated files go to **`01_health/outputs/`**. The table
`outputs/health_baseline_plateaus.csv` is the healthy reference that sections 02 and 03
read from this location.

---

## 6. Outputs, explained

### `build_baseline.py` (→ `common/health_baseline.py`)
- **`health_baseline_plateaus.csv`** — one row per plateau (operating point). Columns
  include: `protocol`, `load_nominal_Nm`, `rpm_meas`, `f1_Hz`, `slip_pct`,
  `sb_offset_Hz` (= 2·s·f1), `sb_floor_bb_dB` (broken-bar sideband floor),
  `cur_sb_1x_dB` (imbalance current-sideband floor), `vib_1x/2x/3x_c2/c3/c4`,
  `thd_pct`, `unbalance_pct`, and `*__std_in` / `*__ptp_in` within-plateau spreads.
- **`health_baseline_validation.png`** — 4 panels:
  1. `f1 vs speed` (linearity ⇒ 2 poles),
  2. `slip vs speed` (grows with load),
  3. `broken-bar sideband floor ± spread` (future alarm threshold),
  4. `vibration 1x per axis` (residual-imbalance baseline).
- **Console** — channel-map consistency, slip-range check, protocol crossing points
  (how much the baseline differs where both protocols meet the same operating point).

### `health_visualize.py`
- **`viz_<filename>.png`** — one 6-panel sheet per file:
  (1) speed profile with shaded plateaus, (2) current spectrogram, (3) 3-phase
  current waveform, (4) full current spectrum with noise floor, (5) zoom around f1
  (broken-bar and imbalance band zones), (6) vibration c3 spectrum with 1×/2×/3×
  and the 50 Hz resonance line.

### `resonance_check.py`
- **`resonance_c3_spectra_overlay.png`** — c3 spectra from all speeds overlaid; a
  **fixed** peak near 50 Hz (separate from the moving 1×) indicates a resonance.
- **`resonance_transmissibility.png`** — 1× vs rotation frequency (log-log) with a
  power-law and ω² reference, plus the compliance curve `1×/fr²`.
- **Console** — a two-test verdict (fixed-peak test + ω²-excess test).

---

## 7. Key reference facts established here

These results are relied upon by every later section:

- **The motor is 2-pole**, confirmed by data: `f1 = rpm/60` with R² = 0.999. The tiny
  slope excess encodes the mean slip (~1.4 %).
- **No torque channel** — load = nominal from the file name; **slip** is the load proxy.
  In `torque_circulation` the per-plateau load actually varies over the sweep, so a
  near-synchronous plateau is a *low-load* point, not the nominal one.
- **Vibration axes:** `c3` is the **main radial** axis (most sensitive to imbalance),
  `c4` is the **axial** axis; `c2` is the second radial. (Determined from
  speed-dependence, then confirmed by the resonance test.)
- **Rig resonance near ~50 Hz is real** (confirmed: a fixed spectral peak plus ~×14
  amplification of 1× as it moves into 50 Hz at 3000 rpm). Consequence: **do not** use
  the 3000 rpm point when fitting a "1× vs speed" law — it is resonantly inflated.
- **Cross-protocol caveat:** the broken-bar sideband **floor does not transfer well**
  between the two protocols (up to ~9 dB difference at the same operating point). This
  motivates the *self-sufficient SNR indicator* introduced in `02_broken_bar`.
- **Clean electrical baseline:** current unbalance (0.06–0.34 %) and THD (1.1–1.6 %)
  are low and tight — a solid floor for later winding / voltage-unbalance diagnosis.

---

## 8. Analysis conventions (used across the project)

- **Unit of analysis = plateau** (a steady operating point), not the whole file.
- **Poles fixed at 2**, `n_s = 60·f1`; slip checked to stay in a physical range.
- **Two spectral windows:** flat-top for **amplitudes** (vibration 1×/2×/3×),
  Hann for **floors / dB / SNR**.
- **f1 and slip are computed per plateau** (essential in `speed_circulation`, where
  f1 steps between plateaus).

---

## 9. Troubleshooting

- *"No health files found"* — the CSVs are not under `01_health/data/`, or their
  names don't contain `…Nm…rpm…`, or they don't start with `health`.
- *Import error for `health_baseline`* — the script computes the path to
  `common/health_baseline.py` from its own location; keep the repository layout
  (section folder → `scripts/`) intact.
- *Fewer files than expected* — the console prints the count and the paths it found;
  check that both `speed_circulation/` and `torque_circulation/` are present.
