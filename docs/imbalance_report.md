# Rotor unbalance — vibration 1x analysis, the 2-pole trap, and two low-speed limits

**Episode 3 of the ZZU-MCC5 (MCC5-THU) diagnostics series.**
Class: `Rotor_Unbalance`, 12 files (2 protocols × 2 loads × 3 nominal speeds).
Channel of evidence: **vibration** (radial axes c2/c3, axial c4); current is a cross-check.
This episode took **three iterations** to get right. All intermediate outputs are preserved
(`1_Trap results`, `2_Trap results`) — the mistakes and their corrections are part of the
result, and this report walks through them in order.

---

## 1. Physics: what unbalance is and where it must show up

A rotor is unbalanced when its mass centre does not sit on the rotation axis. The offset
mass *m* at radius *e* produces a centrifugal force that rotates with the shaft:

> F = m · e · ω²,  pointing outward, once per revolution.

Every property of the expected signature follows from this one formula:

1. **Frequency**: exactly 1× — the rotation frequency fr = rpm/60. Not a sideband, not a
   harmonic family: one rotating force, one line.
2. **Growth law**: amplitude ∝ ω². Double the speed → four times the force. On a log-log
   plot of 1x amplitude vs fr the points must fall on a straight line of **slope 2**.
3. **Direction**: the force rotates in the plane perpendicular to the shaft → the response
   is **radial**. The axial channel must stay quiet (a strong axial 1x points to
   misalignment or a bent shaft — Episode 4 territory, not unbalance).
4. **Load independence**: m and e do not care how much torque the motor delivers. At a
   fixed speed, the 1x amplitude must be **flat** across the load sweep. This is the
   cleanest way to tell a rotor problem from a load problem.
5. **Current cross-check**: the eccentric rotation modulates the air gap, which weakly
   modulates the stator current → sidebands at f1 ± fr. Supporting evidence, not primary.

Each item above is a testable prediction, and the analysis is built as five tests, each
with its own figure. The primary metric is **R1x = √(c2² + c3²)** — the unbalance response
splits between the two radial axes (recon finding), so using a single axis undercounts it.

**The one complication this machine adds**: the motor has 2 poles. For a 2-pole machine
the supply frequency f1 and the rotation frequency fr are almost the same number —
fr = f1·(1 − s), so they are separated by only s·f1, a fraction of a hertz at light load.
The electromagnetic vibration line at f1 (present on any healthy motor) therefore sits
*right next to* the mechanical 1x we are trying to measure. This proximity is the villain
of the whole episode.

---

## 2. Data and method

- 12 files, 90 s each at 12.8 kHz: `speed_circulation` (load held at 20 or 40 Nm, speed
  stepped through plateaus) and `torque_circulation` (speed held near 1000/2000/3000 rpm,
  load swept 0 → nominal).
- **speed protocol** → one analysis window per detected rpm plateau (≤18 s) → one point of
  the ω² law each.
- **torque protocol** → 8-s windows sliding across the load sweep → the load axis. Torque
  points do not enter the ω² fit; they are the load-independence control.
- Amplitudes are taken with a **flat-top window** (accurate peak height); floors and SNR
  with a **Hann window** — same split of duties as in Episodes 1–2.
- f1 and slip are computed per window from the current spectrum and the keyphase rpm.
- The healthy reference for each (protocol, rpm level) comes from the Episode 1 baseline
  table; the ratio `r1x_over_health` compares like with like.
- Known rig features carried over from Episode 1: the ~50 Hz structural resonance
  (windows with f1 or fr within ±1.5 Hz of it are flagged `on_resonance` and excluded
  from the law fit — they are kept as a sensitivity zone, not thrown away).

---

## 3. Run 1 — the trap springs

**Result of the first run: the law came out with exponent n = 0.96 instead of 2.** A
factor-of-two error in the exponent is not a detail; it says the model of the signal is
wrong. Outputs preserved in `1_Trap results`.

The cause was a default that had been harmless in every previous episode: the amplitude
reader searched for the peak in a **±4-bin window** around the target frequency. For
current signatures that tolerance is a virtue (it forgives small errors in the predicted
frequency). For the vibration 1x of a **2-pole** machine it is a trap: at ~490 rpm the EM
line f1 sits only 0.15 Hz from fr — inside the search zone — and the reader happily
returned the EM line as "the 1x".

Three independent pieces of evidence, all from the run-1 tables, convict the EM line:

1. **Against the law**: the clean mid-range points (16–41 Hz) extrapolate to ≈ 6·10⁻⁵ at
   8 Hz; the measured "R1x" there was 4.2–5.6·10⁻⁴ — an excess of ×7–10.
2. **Load dependence where there must be none**: the ~490 rpm "R1x" grew from 4.2·10⁻⁴ at
   20 Nm to 5.6·10⁻⁴ at 40 Nm. A mechanical unbalance cannot do that (the torque control
   proves it); an EM line, which strengthens with load, can.
3. **The low-slip bump**: in the torque files at 1000 rpm, "R1x" rose by ~10 % exactly at
   slip < 0.8 % — where the separation s·f1 collapses and the lines merge — and the bump
   was absent at 2000/3000 rpm, where the mechanical 1x is 5–50× larger than the EM line
   and the contamination drowns.

One mechanism, three fingerprints. The lesson worth keeping: **a wide peak search is a
hidden model assumption** ("the nearest strong peak is my signal"). It fails silently the
moment a stronger neighbour moves into the zone.

---

## 4. Run 2 — the fix that half-worked, and why that was informative

The correction had two parts: (a) measure vibration harmonics with a **narrow ±1-bin**
search — fr is known precisely from the keyphase, so hunting is unnecessary; (b) give
every window a *resolvability passport*: `sep_bins = |f1 − fr| / bin width`, and exclude
windows where the flat-top main lobe of the f1 line geometrically covers the 1x bin.

The narrow search was right and stayed. The **bin-distance exclusion rule failed in both
directions**, and the run-2 data (preserved in `2_Trap results`) show it cleanly:

- The 478 rpm / 40 Nm point (sep = 6.2 bins) **passed** the filter — and again bent the
  exponent to 0.99, sitting ×10 above the law.
- The 989 rpm / 20 Nm points (sep = 4.5 bins) were **rejected** — yet they are provably
  clean: their R1x (2.26–2.30·10⁻⁴) equals the fully-resolvable 40 Nm twins at the same
  speed (2.25–2.27·10⁻⁴) to the third digit. If a value does not change when the
  separation grows from 4.5 to 10 bins, there was nothing to contaminate it.

The lesson of run 2 is the methodological core of the episode: **geometric resolvability
is the wrong criterion — what matters is the amplitude of the masking line relative to
the signal**, and that ratio is regime-dependent. Near 8 Hz the EM/low-frequency content
is an order of magnitude above the ω²-extrapolated mechanical 1x; near 16.5 Hz it is
already well below it. A filter built on line spacing alone cannot know that.

---

## 5. The final method (runs 3–4)

- Vibration harmonics: narrow ±1-bin measurement at fr, 2fr, 3fr (all axes).
- `sep_bins` is kept as a per-window **diagnostic**, not a verdict.
- Hard exclusion by separation only for truly **merged** lines (sep < 3 bins — one peak,
  mechanical and EM contributions inseparable in principle).
- The masker is **measured**, not presumed: `vib_f1_line` = the amplitude at f1 in the
  dominant radial channel, plus the ratio `em_over_1x`.
- **fr < 10 Hz is excluded as a declared low-speed limit** of the method (see §6.5) —
  from the law fit and from the health ratio; the windows stay in the table.
- Built-in validation: the console prints a **twin check** per rpm level — flagged
  windows vs clean windows at the same speed. On the final run the 1000-rpm twin ratio is
  **1.009**: the marginal 20 Nm points differ from their clean 40 Nm twins by 0.9 %,
  i.e. the surviving flags mark real risk zones without poisoning the law.
- Headline windows (per-file summary and sheets) are chosen among clean windows only.

---

## 6. Results

### 6.1 The ω² law holds

With the two low-speed windows excluded, all remaining speed plateaus — **both loads
pooled** — fall on one line:

> **n = 2.11, R² = 0.981, 12 points (16–41 Hz).**

The theoretical slope is 2; the small excess is within the scatter of an 8-point-per-decade
fit on a real rig. The fact that 20 Nm and 40 Nm points lie on the *same* line is itself a
second, independent confirmation of load independence.

### 6.2 Load independence — the flat lines

Across all six torque files the R1x-vs-slip curves are flat: coefficient of variation
**0.8–6.8 %** per file (clean windows), while the load changes by the full sweep. At
1000 rpm the 20 Nm and 40 Nm curves overlap almost exactly. Whatever produces the 1x sits
on the rotor, not in the load path.

### 6.3 The ~50 Hz resonance, revisited

The four plateaus at ~2930–2980 rpm sit ×**4.7–5.5** above the corrected law — the same
structural mode that Episode 1 characterised on the healthy machine (fixed 50.0 ± 0.7 Hz
peak, ×9–14 amplification of the healthy 1x over its own speed law). The order of
magnitude agrees; the exact factor differs because the two baselines are built
differently (healthy-1x law vs unbalance-1x law). Practically: readings taken near
3000 rpm on this rig measure the resonance as much as the fault — they are excluded from
the law but noted as the **maximum-sensitivity zone** (see 6.4).

### 6.4 Detection against the healthy baseline — honest and modest

At the working regimes the unbalance class shows `r1x_over_health` of **1.3–1.9**
(i.e. +2.3…+5.6 dB). The largest ratios appear exactly on the resonance (torque-3000:
**2.8**) — the resonance amplifies the fault response as predicted, which supports using
it deliberately as a sensitivity amplifier rather than avoiding it.

Two honest caveats:

- A ratio of 1.3 is a *weak* detection unless the healthy spread at the same regime is
  known to be much tighter. Quantifying that spread (from the Episode 1 sub-window and
  cross-protocol statistics) is the open task before any threshold is declared.
- The current cross-check (f1 ± fr sidebands) is strongly present (SNR 18–41 dB across
  headline windows), consistent with eccentric rotation modulating the air gap — but it
  has not yet been compared against the healthy baseline for the same indicator, so it is
  reported as an observation, not evidence.

### 6.5 Two low-speed regimes, two different failure mechanisms

Both ~8 Hz plateaus are excluded from the law, but **for different, measured reasons** —
and the difference only surfaced because the masker is now measured per window:

- **490 rpm / 20 Nm — merged lines.** sep = 0.15 Hz ≈ 2.7 bins: the EM f1 line and the
  mechanical 1x form one peak. The masker is directly visible: `vib_f1_line` ≈ 2.7·10⁻⁴
  next to a law-predicted mechanical 1x of ≈ 6·10⁻⁵. The measured "1x" here is mostly the
  EM line, and no window length fixes that — the lines are physically unresolved at this
  slip.
- **478 rpm / 40 Nm — an unexplained excess at fr itself.** Here the lines are separable
  (sep = 6.2 bins), and the f1 line is *quiet* (`vib_f1_line` = 7·10⁻⁶) — yet the peak at
  fr carries 5.6·10⁻⁴, ×10 above the law. This is **not** the EM-line mechanism. The
  excess sits at the true rotation frequency, grows with load, and appears only at low
  speed. Candidate explanations — VFD torque ripple at low output frequency, rotor
  rocking under high torque at low speed, speed-controller hunting — are listed, not
  chosen: **the mechanism is an open question of this episode.**

Practical conclusion, mirroring Episode 2: the broken-bar analysis found its blind zone
at 477 rpm (the MCSA sideband drowns in the f1 skirt); the vibration 1x analysis finds
its own blind zone at the same speeds (merged lines at light load, an unexplained
off-law excess at heavy load). **The same low-speed corner of the regime map is hostile
to both methods, for different physical reasons.** On this rig, sub-500 rpm diagnostics
would need a different toolset.

### 6.6 An unplanned discovery: a candidate axial rig mode near 16.5 Hz

The "axial must stay low" control produced an anomaly too consistent to be noise: the
axial (c4) 1x amplitude has a sharp bump exactly around fr ≈ 16.2–16.5 Hz —
**8–10× above the radial 1x** at those plateaus (both loads, both files), against
0.07–0.97 everywhere else. The same elevation shows up in the *healthy* data at the same
speed, which points away from the fault and toward the test rig: a structural **axial
mode near ~16.5 Hz**, an axial sibling of the known 50 Hz radial resonance.

Status: **candidate, not yet proven.** The proof is the same two-test procedure Episode 1
used at 50 Hz (a fixed-frequency peak while speed changes; amplification over the
expected law). Until then, the axial control at ~1000 rpm is unusable at face value —
and this matters directly for Episode 4, where misalignment is diagnosed largely through
the axial channel. Running that check on the health data is the first task of Episode 4's
preparation.

### 6.7 Headline summary (strongest clean window per file)

| file (short) | proto | Nm | rpm | fr, Hz | s, % | R1x | ax/rad | SNR₁ₓ, dB | vs health |
|---|---|---|---|---|---|---|---|---|---|
| speed 20Nm 1000rpm | speed | 20 | 989 | 16.48 | 1.54 | 2.30e-4 | 8.19* | 38 | 1.32 |
| speed 20Nm 2000rpm | speed | 20 | 1980 | 32.99 | 1.19 | 1.07e-3 | 0.47 | 53 | 1.35 |
| speed 20Nm 3000rpm | speed | 20 | 2479 | 41.32 | 1.24 | 1.41e-3 | 0.71 | 56 | 1.89 |
| speed 40Nm 1000rpm | speed | 40 | 970 | 16.16 | 3.42 | 2.27e-4 | 10.39* | 37 | 1.30 |
| speed 40Nm 2000rpm | speed | 40 | 1947 | 32.45 | 2.81 | 1.16e-3 | 0.46 | 53 | 1.47 |
| speed 40Nm 3000rpm | speed | 40 | 2443 | 40.72 | 2.67 | 1.43e-3 | 0.70 | 56 | 1.91 |
| torque 20Nm 1000rpm | torque | 20 | 1003 | 16.71 | 0.18 | 2.63e-4† | 5.69* | 35 | — |
| torque 20Nm 2000rpm | torque | 20 | 1978 | 32.96 | 1.28 | 1.07e-3 | 0.48 | 49 | 1.27 |
| torque 20Nm 3000rpm | torque | 20 | 2970 | 49.49 | 1.27 | 1.42e-2 | 0.07 | 71 (res.) | 2.81 |
| torque 40Nm 1000rpm | torque | 40 | 981 | 16.35 | 2.24 | 2.48e-4 | 9.05* | 32 | 1.46 |
| torque 40Nm 2000rpm | torque | 40 | 1944 | 32.39 | 2.98 | 1.15e-3 | 0.47 | 50 | 1.38 |
| torque 40Nm 3000rpm | torque | 40 | 2940 | 49.01 | 2.23 | 1.44e-2 | 0.07 | 71 (res.) | 2.84 |

\* inflated by the candidate axial mode near 16.5 Hz (§6.6), not by the fault.
† all windows of this file sit at near-zero slip (lines merged); the headline is the
fallback maximum and its health ratio is deliberately withheld.

Note the pleasing regularity down the R1x column: ~2.3·10⁻⁴ at 1000 rpm, ~1.1·10⁻³ at
2000 rpm, ~1.4·10⁻³ at 2450 rpm, ~1.4·10⁻² on the resonance — the ω² law plus the
resonance, readable straight from the table, identically in both protocols.

---

## 7. Errors made, and what each one taught

This episode is documented with its mistakes on purpose — each one changed the method.

1. **The wide peak search** (run 1) — a convenient default became a silent model
   assumption and returned the wrong physical line. *Lesson: every tolerance in a
   measurement is a claim about the signal's neighbourhood; on a 2-pole machine the 1x
   has a strong neighbour by construction.*
2. **The bin-distance filter** (run 2) — a geometrically reasonable rule rejected clean
   points and passed a contaminated one. *Lesson: resolvability is about the masker's
   amplitude, not only its distance; measure the masker.*
3. **Headline selection by maximum** (runs 1–2) — "show the strongest window" reliably
   selected the resonance or a contaminated window, i.e. the least representative one.
   *Lesson: a summary statistic needs the same exclusion logic as the analysis itself.*
4. **Plot honesty** (run 3) — excluded points were still drawn in the law-point style.
   Fixed by giving every exclusion class its own marker. *Lesson: a figure that hides the
   filtering claims more than the fit supports.*

The self-sufficient SNR carried over from Episode 2 unchanged and worked; the trap lived
entirely in the *amplitude* pathway, which is exactly why both indicator families are
kept.

---

## 8. How to read the diagnostic sheets (`ubviz_*.png`)

Six panels per file: **(1)** speed profile with analysis windows, the headline (strongest
*clean*) window boxed in red; **(2)** vibration spectrogram of the dominant radial axis —
the 1x ridge follows the speed, the 50 Hz resonance is the horizontal dashed line;
**(3)** raw radial waveform over ~4 revolutions — visible once-per-rev wobble;
**(4)** full radial spectrum with 1×/2×/3× markers, the 50 Hz line and the noise floor;
**(5)** zoom on the 1x with the local floor → the self-sufficient SNR₁ₓ; **(6)** the
control panel — radial vs axial 1x (speed files) or R1x vs slip (torque files). The title
carries the working point, R1x, SNR₁ₓ, the separation in bins and the exclusion flags.

---

## 9. Status and what's next

Closed in this episode: the ω² law (n = 2.11, R² = 0.981, both loads on one line); the
load-independence control (CoV ≤ 6.8 %); the resonance behaving as the predicted
sensitivity amplifier (×4.7–5.5 over the law, largest health ratios there); two
documented low-speed limits with measured, distinct mechanisms; a validated per-window
resolvability passport for the 2-pole f1↔fr proximity — which Episode 4 inherits
directly, since the same trap awaits at 2× (2f1 vs 2fr).

Open questions, in priority order:

1. **The axial ~16.5 Hz candidate mode** — run the Episode-1-style fixed-peak test on the
   health data. Blocking issue for Episode 4 (misalignment lives in the axial channel).
2. **The healthy spread of the 1x amplitude** across protocols and sub-windows — required
   to turn the 1.3–1.9 ratios into a defensible threshold (or an honest "not separable at
   light severity" statement).
3. **The 478 rpm / 40 Nm excess** — identify the mechanism (VFD torque ripple, rotor
   rocking, controller hunting) or bound it.
4. The severity axis, if the dataset provides unbalance levels — a monotone
   ratio-vs-severity curve would upgrade the detection verdict from "elevated" to
   "quantified".
