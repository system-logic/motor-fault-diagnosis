# Parameter catalog — rotor imbalance (Episode 3)

Reference document for the imbalance block. Fixes what we measure, with what, in which
window, with which indicators, and where the honest boundaries are. Modelled on
`broken_bar_catalog.md` and built on the health baseline.

Fixed decisions for this block:
- **Vibration is the primary channel** (the fault is mechanical); current is a
  cross-check only (f1 ± fr sidebands).
- **R1x = √(1×c2² + 1×c3²)** — the rotating force splits between the radial axes; a
  single axis undercounts.
- **The ω² law is the centrepiece**, with three explicit exclusion classes: the ~50 Hz
  resonance, merged f1↔1× lines, the fr < 10 Hz low-speed limit.
- **The masker is measured, not presumed** — every window carries the EM f1 line
  amplitude next to the 1×.
- Always go deep; when choosing "simpler vs deeper", go deeper.

═══════════════════════════════════════════════════════════════════════

## 0. What we inherit (not reinvented)

Carried over from `01_health` / `02_broken_bar` as-is:
- plateau detection, channel identification (timer dropped, kp=1, vib=2,3,4,
  current=5,6,7, no torque channel), f1 and slip **per window**, poles = 2;
- the ~50 Hz rig resonance (two-test proof from E1) with its ±1.5 Hz guard;
- the **self-sufficient SNR** concept from E2 (peak over its own local floor, no
  cross-protocol calibration) — reused unchanged as `onex_snr_dB`;
- flat-top for amplitudes / Hann for floors and SNR;
- the healthy 1× reference per (protocol, rpm level) from
  `health_baseline_plateaus.csv` → the `r1x_over_health` ratio.

═══════════════════════════════════════════════════════════════════════

## 0-bis. Three runs, two preserved mistakes (the 2-pole trap)

This block took three iterations; runs 1–2 are archived (`1_Trap results`,
`2_Trap results`) and analysed in `docs/imbalance_report.md` §3–4. Summary:

- **Run 1** — the default ±4-bin peak search returned the EM f1 line as "the 1×"
  wherever s·f1 shrank below the zone (low speed / low slip). Exponent bent to 0.96;
  the "R1x" at ~490 rpm was ×7–10 above the law and grew with load — impossible for a
  mechanical imbalance, natural for an EM line. Three independent fingerprints in the
  run-1 tables convict the same mechanism.
- **Run 2** — narrow ±1-bin measurement (kept) + a bin-distance exclusion rule
  (rejected by the data): it passed a contaminated point (sep 6.2 bins, ×10 off-law)
  and rejected provably clean ones (equal to resolvable twins to 3 digits).
  **Lesson fixed in the method: resolvability is about the masker's amplitude, not its
  distance.**
- **Run 3+ (final)** — narrow measurement; `sep_bins` demoted to a diagnostic; hard
  exclusion only for merged lines (< 3 bins); `low_speed_em` (fr < 10 Hz) as a declared
  method limit; the masker measured per window; a per-level **twin check** printed as
  built-in validation (final value at 1000 rpm: 1.009).

═══════════════════════════════════════════════════════════════════════

## 1. Unit of analysis and windows

- **speed protocol** → one window per rpm plateau, capped at 18 s (df ≈ 0.056 Hz).
  Each plateau = one point of the ω² law.
- **torque protocol** → 8-s windows (df = 0.125 Hz) sliding with 2-s step across the
  load sweep. These form the load axis only; they never enter the ω² fit.
- Headline (per-file summary and sheet) = the strongest **clean** window: not on
  resonance, not merged, not below the low-speed limit.

## 2. Per-window metrics (columns of `imbalance_windows.csv`)

**Working point:** `protocol`, `load_nominal_Nm`, `rpm`, `rpm_level` (rounded to 500),
`fr_Hz`, `f1_Hz`, `slip_pct`, `t_start`/`t_end`.

**Primary indicator:**
- `R1x` — √(1×c2² + 1×c3²), flat-top amplitude, **narrow ±1-bin** search at fr from the
  keyphase.
- `onex_snr_dB` — self-sufficient SNR of the 1× on the dominant radial axis (Hann dB
  spectrum, peak over the median of the ±[1×half, 3×half] shoulders).
- `r1x_over_health` — R1x over the healthy mean at the same (protocol, rpm level).
  **Deliberately NaN** when the window is merged or below the low-speed limit — the
  numerator would not be the mechanical 1×.

**Shape of the harmonic family:** `R2x_ratio`, `R3x_ratio` (2×/1×, 3×/1×) and
`axial_1x`, `axial_ratio` (c4 1× over radial R1x) — the inputs of the future
imbalance / misalignment / bend separation (Episode 4).

**The resolvability passport (2-pole trap bookkeeping):**
- `sep_Hz`, `sep_bins` = |f1 − fr| and the same in bins of *this* window;
- `f1_in_1x` — merged lines (sep < 3 bins): one peak, mechanical/EM inseparable in
  principle; excluded from the law and the ratio, kept in the table;
- `f1_near_1x` — grey zone (3–8 bins): kept in the law, twin-checked in the console;
- `f1_in_2x` — the same trap at the second harmonic (2f1 vs 2×fr) — Episode 4 guard;
- `low_speed_em` — fr < 10 Hz: the declared low-speed limit (see §4);
- `slip_suspect` — slip < 0.05 %: the f1 estimate is unreliable near synchronism
  (includes the occasional negative-slip artifact);
- `vib_f1_line`, `em_over_1x` — the **measured masker**: the EM f1 line amplitude in
  the dominant radial channel and its ratio to the 1×.

**Rig-feature flags:** `f1_on_res`, `fr_on_res`, `on_resonance` (±1.5 Hz of 50 Hz);
`fr_on_axial_res` (±1.5 Hz of the **candidate** 16.5 Hz axial mode — flagging only).

**Controls:** `unbalance_pct` (current phase unbalance — must stay at baseline, else it
is a stator problem), `cur_sb_1x_snr` (f1 ± fr sidebands in current — the eccentricity
cross-check; observed strong, 18–41 dB, but not yet baselined against health).

## 3. The ω² fit

Log-log linear fit of R1x vs fr over **speed-protocol** windows with
`~on_resonance & ~f1_in_1x & ~low_speed_em & ~slip_suspect`. Both loads pooled — their
coincidence on one line is itself part of the load-independence evidence.
**Final: n = 2.11, R² = 0.981, 12 points (16–41 Hz).**

## 4. The three exclusion classes (and their markers on `imbalance_omega2.png`)

| class | marker | criterion | meaning |
|---|---|---|---|
| resonance | red rings | f1 or fr within ±1.5 Hz of 50 Hz | rig mode inflates 1× ×4.7–5.5; kept as the max-sensitivity zone |
| merged lines | red × | sep < 3 bins | EM f1 and mechanical 1× form one peak; masker measured (2.7·10⁻⁴ at 490 rpm/20 Nm) |
| low-speed limit | grey square | fr < 10 Hz | declared method limit; at 40 Nm the excess sits at fr itself with the f1 line quiet — mechanism **open** |

## 5. Honest boundaries

- No severity grades → no grams·mm calibration; ratios only.
- The healthy 1× spread across protocols is not quantified yet → the ×1.3–1.9 working-
  regime ratios are "elevated", not "thresholded".
- The axial control at ~1000 rpm is compromised by the candidate 16.5 Hz axial rig mode
  until the health-data fixed-peak test is run (Episode 4 prerequisite).
- The 478 rpm / 40 Nm ×10 excess at fr is unexplained (VFD torque ripple / rotor
  rocking / controller hunting are candidates, none chosen).
- The current cross-check (`cur_sb_1x_snr`) is an observation, not evidence, until
  compared to the healthy baseline for the same indicator.
