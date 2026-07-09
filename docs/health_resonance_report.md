# ZZU-MCC5 induction-motor diagnostics — Health baseline & rig resonance

**Detailed report:** how the healthy-motor reference is built and validated, and how the
test rig's ~50 Hz mechanical resonance is confirmed.

**Object:** three-phase squirrel-cage induction motor, 2.2 kW, 2-pole, VFD-driven.
Sampling 12 800 Hz, record length 90 s. **Scripts:** `health_baseline.py`,
`health_visualize.py`, `resonanse_check.py`.

> **Figures.** Summary figures are the standard English outputs of the scripts.
> `health_baseline_validation.png` comes from `health_baseline.py`;
> `resonance_c3_spectra_overlay.png` and `resonance_transmissibility.png` from
> `resonanse_check.py`; per-file `viz_*.png` sheets from `health_visualize.py`.
> They are referenced from a `figures/` folder next to this report.

---

## 1. What this report is about

We are building a fault-diagnosis system that reads the motor's own signals — current
and vibration. Before catching faults, we must know exactly what a **healthy** motor
looks like: its normal signal levels, how they depend on speed and load, and their
natural spread. That reference map is the **health baseline**. Every later fault is
recognised as a **deviation** from it.

The report covers two experiments:
- **`health_baseline.py`** — walks all healthy records, cuts each into steady segments,
  and measures the full set of normal parameters. Builds the baseline and validates it.
- **`resonanse_check.py`** — tests a hypothesis that surfaced during the baseline
  analysis: that the rig has a mechanical resonance near 50 Hz that distorts vibration
  at 3000 rpm.

**Two rig protocols** (both must be understood — they drive the whole pipeline):
- **torque_circulation** — speed held constant, **load** stepped 0→nominal. One file =
  one speed, several loads.
- **speed_circulation** — load held constant, **speed** stepped. One file = one load,
  several speeds; here the supply frequency f1 changes between steps.

**Unit of analysis = a "plateau"** — a steady segment (one speed + one load). Each file
yields several; each plateau is one table row.

---

## 2. Data: the measured channels

Each file is 1 152 000 rows (90 s × 12 800 Hz) × 8 channels. Channels are identified by
signal shape, not column order:

| Column | Channel | How identified |
|---|---|---|
| col0 | **time counter — DROPPED** | sawtooth rising exactly 1.0/s, resetting every 1.28 s; a DAQ counter, not a physical signal |
| col1 | keyphase (once-per-rev pulse) | one pulse per shaft revolution; gives instantaneous speed |
| col2, col3, col4 | vibration (3 axes) | high-frequency, small-amplitude |
| col5, col6, col7 | current (3 phases) | dominant at f1, mutual shifts of 120° and 240° |

**Key point:** there is **no torque channel** — what could be mistaken for it is the
time counter. So load is taken from the file name (nominal), and steadiness is judged by
speed. Below we show this is not a loss: load is recovered indirectly from **slip**.

---

## 3. Glossary of measured variables

**Group 1 — working point ("where we are")**
- `f1` (Hz) — supply frequency set by the VFD; sets the synchronous speed.
- `rpm_meas` — measured shaft speed from the keyphase pulse.
- `fr` (Hz) = rpm/60 — rotation frequency; mechanical faults sit here (imbalance at 1×fr).
- `slip` (%) — how far the rotor lags the field: s = (n_s − rpm)/n_s, n_s = 60·f1.
  Always > 0; grows with load. Used as a **load proxy**.
- `sb_offset` (Hz) = 2·s·f1 — distance from f1 to the broken-bar sidebands.

**Group 2 — signature floors (normal level of future faults)**
- `sb_floor_bb_dB` — noise level in the broken-bar sideband zone (future threshold).
- `vib_1x_c2/c3/c4` — vibration amplitude at 1×fr per axis (residual-imbalance baseline).
- `vib_2x, vib_3x` — amplitudes at 2× and 3× (for misalignment/looseness separation).
- `cur_sb_1x_dB` — current-sideband floor at f1±fr (imbalance-via-current signature).

**Group 3 — current unbalance & distortion**
- `thd_pct` — total harmonic distortion of the current (baseline "cleanliness").
- `unbalance_pct` — three-phase current unbalance (rises on winding short or voltage unbalance).

**Group 4 — spread** — within-plateau and between-run variation of each metric; the
alarm threshold is built with margin over the larger of the two.

**Group 5 — sanity** — channel-map consistency, keyphase stability, f1∝rpm linearity,
slip in range. A trust gate: if any of these fails, the data is read wrong.

---

## 4. Experiment 1 — building the health baseline

12 healthy files (6 speed + 6 torque), 26 plateaus. The validation figure below has four
panels; the findings follow.

![Health baseline validation: f1 vs speed, slip vs speed, broken-bar floor, vibration 1x](figures/health_baseline_validation.png)

**4.1. Poles — confirmed by physics.** f1 is strictly proportional to rpm (R² = 0.999).
The slope is not exactly 1 but 1.014 — that excess is the *slip signature*: since
f1 = rpm/(60·(1−s)), the small excess corresponds to a mean slip ~1.4 %, matching the
measurements. The motor is **2-pole**, confirmed by the data itself.

**4.2. Slip recovers the lost load axis.** Slip tracks load: at ~1000 rpm it runs
1.6 % (20 Nm) → 3.4 % (40 Nm); monotonic. So load can be read from slip — the torque
channel is not needed. This also revealed that in torque_circulation the load **varies
within a file**: a near-synchronous plateau (slip ≈ 0) is the *zero-load* end of the
sweep, not 40 Nm. "40 Nm" in the file name is the sweep peak, not each plateau's load.

**4.3. Broken-bar floor & the cross-protocol caveat.** The median floor is −41.9 dB
(quiet). The worst regime is 40 Nm / 1000 rpm (−33.8 dB, noisy) — small band offset,
bands hugging the f1 skirt. **Red flag:** the floor does **not reproduce** between
protocols — up to ~9 dB apart at the same operating point, while the future alarm
threshold is ~6 dB. Consequence: a single absolute threshold cannot merge the two
protocols for broken bar → use a **self-sufficient SNR indicator** (built in the
broken-bar section).

**4.4. Vibration axes — resolved here.** The residual 1× grows with speed unevenly:
axis **c3** rises sharply toward 3000 rpm, **c4** stays low, c2 is in between. So
**c3 = main radial** (imbalance-sensitive), **c4 = axial**, c2 = second radial. (Later
confirmed by the resonance test.) The strong c3 jump at 3000 is *larger than* the ω²
centrifugal law predicts — the trigger for Experiment 2.

**4.5. Clean electrical baseline.** Current unbalance (0.06–0.34 %) and THD (1.1–1.6 %)
are low and tight — a solid floor for later winding / voltage-unbalance diagnosis.

---

## 5. Experiment 2 — confirming the rig resonance

**Hypothesis.** The c3 1× jump at 3000 rpm is either (H1) a **mechanical resonance**
near 50 Hz amplifying the 1× as fr moves into it, or (H2) plain power-law growth.

**Decisive idea.** A resonance is a property of the *structure* — a **fixed** frequency
regardless of rpm — while the 1× *moves* with speed. Intermediate speed-protocol
plateaus put 1× at 24–41 Hz (away from 50). If a fixed peak still sits at ~50 Hz, that
is H1.

> Regenerate these two figures in English with `resonanse_check.py` on the health data.

![Resonance: c3 spectra overlaid by speed — a fixed peak at 50 Hz](figures/resonance_c3_spectra_overlay.png)

**Test 1 — the fixed peak stands still.** On every plateau below 3000 (1× at 8–41 Hz),
a peak sits at **50.0 ± 0.7 Hz** and does not move, though speed changes six-fold. That
is the definition of a resonance.

![Resonance: 1x vs speed (log-log) and the 1x/fr² compliance curve](figures/resonance_transmissibility.png)

**Test 2 — 1× inflates into 50 Hz.** Below resonance the 1× barely grows (slope ~0.9);
at 2917–2970 rpm, where 1× reaches 49–50 Hz, it jumps **×9–14** over the power-law
extrapolation. The compliance curve 1×/fr² peaks exactly at 50 Hz. Both tests agree.

**Resonance vs mains hum?** A fixed 50 Hz peak could be mains pickup. But Test 2 settles
it: a pure electrical line cannot amplify the *rotational* 1× — yet it amplifies ×14. So
a **mechanical resonance near 50 Hz is real**. A narrow mains line may also exist, but it
does not change the conclusion.

**Consequence.** The 3000 rpm point cannot be used to fit a "1× vs speed" law — it is
resonantly inflated ~×10. But 3000 rpm is *not* useless: the resonance amplifies
imbalance there, so **sensitivity is highest** — we split roles: 3000 for detection, the
ω² law from speeds ≤2500 plus the intermediate plateaus.

---

## 6. Conclusions

1. **The baseline is built and physically valid** — 26 operating points, all checks pass.
2. **No torque channel** — load is read from slip; in torque_circulation the load varies
   within a file, so plateaus are labelled by slip, not the nominal.
3. **Vibration axes resolved:** c3 main radial, c4 axial.
4. **Rig resonance ~50 Hz confirmed** — exclude 3000 rpm from a quantitative imbalance
   law, but keep it as the zone of maximum sensitivity.
5. **Broken-bar floor does not transfer between protocols (~9 dB)** — motivates the
   self-sufficient SNR indicator in the next section.
6. **Clean electrical baseline** (unbalance, THD) — a good floor for winding / voltage.

---

## 7. Appendix — per-plateau table (26 operating points)

Columns: protocol; nominal load; measured speed; f1; slip; band offset 2s·f1;
broken-bar floor (dB); vibration 1× per axis; THD; current unbalance.

| prot | Nm | rpm | f1 | s% | 2sf1 | bb floor | 1x c2 | 1x c3 | 1x c4 | THD% | unb% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| speed | 20 | 489 | 8.3 | 1.96 | 0.33 | -40.1 | 0.0000 | 0.0002 | 0.0000 | 1.1 | 0.17 |
| speed | 20 | 987 | 16.7 | 1.68 | 0.56 | -42.0 | 0.0001 | 0.0002 | 0.0008 | 1.3 | 0.25 |
| speed | 20 | 988 | 16.7 | 1.61 | 0.54 | -41.0 | 0.0001 | 0.0002 | 0.0008 | 1.3 | 0.25 |
| speed | 20 | 1477 | 25.0 | 1.54 | 0.77 | -48.0 | 0.0003 | 0.0002 | 0.0003 | 1.4 | 0.23 |
| speed | 20 | 1975 | 33.4 | 1.39 | 0.93 | -46.7 | 0.0006 | 0.0006 | 0.0004 | 1.3 | 0.23 |
| speed | 20 | 1978 | 33.4 | 1.25 | 0.84 | -43.1 | 0.0006 | 0.0006 | 0.0004 | 1.4 | 0.23 |
| speed | 20 | 2480 | 41.8 | 1.17 | 0.98 | -38.3 | 0.0006 | 0.0004 | 0.0003 | 1.4 | 0.24 |
| speed | 20 | 2967 | 50.1 | 1.35 | 1.35 | -42.8 | 0.0011 | 0.0074 | 0.0004 | 1.4 | 0.25 |
| speed | 20 | 2970 | 50.1 | 1.23 | 1.23 | -37.1 | 0.0011 | 0.0074 | 0.0004 | 1.4 | 0.24 |
| speed | 40 | 478 | 8.3 | 4.28 | 0.71 | -42.0 | 0.0000 | 0.0002 | 0.0000 | 1.6 | 0.06 |
| speed | 40 | 969 | 16.7 | 3.52 | 1.18 | -41.9 | 0.0000 | 0.0002 | 0.0010 | 1.4 | 0.13 |
| speed | 40 | 969 | 16.7 | 3.52 | 1.18 | -41.1 | 0.0001 | 0.0002 | 0.0010 | 1.4 | 0.13 |
| speed | 40 | 1451 | 25.0 | 3.28 | 1.64 | -48.3 | 0.0003 | 0.0002 | 0.0003 | 1.2 | 0.17 |
| speed | 40 | 1939 | 33.4 | 3.19 | 2.13 | -42.0 | 0.0005 | 0.0006 | 0.0004 | 1.1 | 0.19 |
| speed | 40 | 1944 | 33.4 | 2.96 | 1.98 | -43.8 | 0.0005 | 0.0006 | 0.0004 | 1.1 | 0.19 |
| speed | 40 | 2434 | 41.8 | 3.02 | 2.53 | -38.4 | 0.0006 | 0.0005 | 0.0004 | 1.1 | 0.20 |
| speed | 40 | 2917 | 50.1 | 3.01 | 3.02 | -41.8 | 0.0018 | 0.0049 | 0.0003 | 1.6 | 0.17 |
| speed | 40 | 2920 | 50.1 | 2.90 | 2.91 | -43.1 | 0.0018 | 0.0048 | 0.0003 | 1.6 | 0.20 |
| torque | 20 | 990 | 16.7 | 1.44 | 0.48 | -37.9 | 0.0001 | 0.0002 | 0.0007 | 1.2 | 0.31 |
| torque | 20 | 1980 | 33.4 | 1.20 | 0.80 | -36.1 | 0.0006 | 0.0005 | 0.0004 | 1.2 | 0.30 |
| torque | 20 | 2977 | 50.1 | 1.02 | 1.03 | -37.8 | 0.0008 | 0.0044 | 0.0004 | 1.3 | 0.34 |
| torque | 40 | 972 | 16.7 | 3.20 | 1.07 | -33.8 | 0.0000 | 0.0001 | 0.0007 | 1.3 | 0.22 |
| torque | 40 | 1943 | 33.4 | 3.00 | 2.01 | -47.7 | 0.0005 | 0.0006 | 0.0004 | 1.2 | 0.20 |
| torque | 40 | 1998 | 33.4 | 0.31 | 0.20 | nan | 0.0008 | 0.0005 | 0.0004 | 1.2 | 0.30 |
| torque | 40 | 2922 | 50.1 | 2.85 | 2.86 | -41.4 | 0.0018 | 0.0052 | 0.0003 | 1.5 | 0.20 |
| torque | 40 | 3008 | 50.1 | 0.01 | 0.01 | nan | 0.0011 | 0.0050 | 0.0005 | 1.3 | 0.24 |

*Full column set (2×/3× vibration and all spreads) is in `health_baseline_plateaus.csv`.*
