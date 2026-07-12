# Series roadmap — ZZU-MCC5 induction-motor diagnostics

Ordering principle: each episode **grows out of** the previous one and **closes**
specific questions. The threads the logic follows:

- **Signature channel:** current (rotor-electrical, stator) → vibration (mechanical,
  bearings). We move from simple single-channel analysis to multi-channel.
- **Tooling:** direct plateau spectrum → envelope / demodulation (bearings) →
  multi-class streaming engine.
- **Open threads left by health** — both now closed:
  (1) cross-protocol broken-bar floor → self-sufficient SNR indicator (closed in E2);
  (2) ~50 Hz resonance → the ω² law with correct resonance handling (closed in E3).
- **New threads opened along the way** (tracked at the episodes that own them):
  the 2-pole f1↔fr trap and its resolvability passport (E3 → inherited by E4 at 2×);
  the candidate ~16.5 Hz axial rig mode (E3 → must be confirmed before E4);
  the unexplained low-speed 1× excess at 478 rpm / 40 Nm (E3, open).

Notation: `[folders]` = dataset classes; H/L = available severity axis.

**Repository mapping.** Episodes map to the numbered section folders
(`01_health`, `02_broken_bar`, …). The exact folder/file layout of the repo lives in
`docs/tree.txt`.

═══════════════════════════════════════════════════════════════════════

## Episode 1 — Foundation: dataset, health baseline, resonance  ✅ DONE
Investigations: dataset preparation · health baseline · resonance check.
- Grows from: —
- Closes: data structure, channels, plateaus, the two protocols, the baseline and
  thresholds, the ~50 Hz rig resonance, vibration-axis orientation.
- Deliberately left open: cross-protocol broken-bar floor; behaviour at 3000 rpm.
- `[Health]`  →  folder `01_health`

═══════════════════════════════════════════════════════════════════════

## Episode 2 — Rotor-electrical: broken bar
Status: **pure class ✅ DONE** (12 files, both indicators, load axis, both
resolvability limits) · **composite rotor-part ⏳ pending**.
Investigations: broken bar (pure) · self-sufficient indicator · rotor signature in
composites.
- Grows from: the current sideband floor and the cross-protocol calibration question (E1).
- Channel/tool: CURRENT, MCSA, single-plateau-window spectrum; the shift from
  "peak over the baseline" to "peak over the local floor in the same window"
  (SNR indicator).
- What we show: the f1±2s·f1 bands rise over the floor; the resolvability limit at a
  low-speed/high-load regime (speed 40/1000); in broken_bar+bearing composites the
  rotor part is visible in the current (bearing part deferred — an honest boundary).
- Closes: (1) the self-sufficient indicator — no cross-protocol calibration needed;
  first look at a composite.
- Severity axis: NONE (H only) → only a "signature vs speed/load" axis.
- `[Broken_Bar]` · `[Broken_Bar-Bearing_Inner]` · `[Broken_Bar-Bearing_Outer]`
  →  folder `02_broken_bar`

═══════════════════════════════════════════════════════════════════════

## Episode 3 — Rotor mechanics I: imbalance  ✅ DONE
Investigations: imbalance (pure) · the ω² law · load-independence control ·
**the 2-pole trap** (found here, not planned).
- Grows from: the vibration axes (c3 radial, c4 axial) and the resonance (E1);
  the self-sufficient SNR (E2), reused unchanged for the 1×.
- Channel/tool: VIBRATION, 1× amplitude (flat-top, **narrow ±1-bin search at fr from
  the keyphase** — see the trap below), R1x = √(1×c2² + 1×c3²).
- Shown: **the ω² law holds — n = 2.11, R² = 0.981** over 12 plateaus (16–41 Hz),
  both loads on one line; load-independence control CoV 0.8–6.8 % per torque file;
  the 50 Hz resonance inflates the fault 1× **×4.7–5.5** over the law and yields the
  largest health ratios (2.8) — excluded from the law, kept as the max-sensitivity
  zone; detection vs healthy ×1.3–1.9 at working regimes (threshold pending the
  healthy-spread task below).
- Closes: (2) the ω² law with correct resonance handling; imbalance vs healthy.
- **Found here (took three runs; runs 1–2 preserved in the section's
  `outputs/1_Trap results` and `2_Trap results`; full story in
  `docs/imbalance_report.md`):**
  · **the 2-pole trap** — on a 2-pole machine the EM f1 line sits only s·f1 from the
    mechanical 1×; a wide ±4-bin peak search returned the EM line as "the 1×" and bent
    the exponent to 0.96; a bin-distance filter then failed in both directions; final
    method = narrow measurement + merged-lines exclusion (sep < 3 bins) + the masker
    **measured per window** (`vib_f1_line`) + a printed twin-check (final: 1.009);
  · **two low-speed limits at ~8 Hz, distinct mechanisms** — 20 Nm: lines physically
    merged (masker measured at 2.7·10⁻⁴); 40 Nm: a ×10 off-law excess at fr itself
    with the f1 line quiet — **mechanism unidentified, open**. Mirrors the E2 477 rpm
    MCSA limit: the same low-speed corner is blind for both methods;
  · **candidate axial rig mode ~16.5 Hz** — axial 1× spikes ×8–10 over radial at
    fr ≈ 16.2–16.5 Hz, both loads, and in the *healthy* data too → rig, not fault.
    **Must be confirmed by the E1-style fixed-peak test BEFORE Episode 4**;
  · the `f1_in_2x` guard prepared for E4 (the same trap at 2f1 vs 2×fr).
- Open tasks owned by this episode: the healthy 1× spread (to turn ×1.3–1.9 into a
  defensible threshold); the 478 rpm / 40 Nm excess mechanism.
- Severity axis: NONE (no severity label) → speed and load axes only.
- `[Rotor_Unbalance]`  →  folder `03_rotor_unbalance`

═══════════════════════════════════════════════════════════════════════

## Episode 4 — Rotor mechanics II: misalignment and bend
Investigations: misalignment · shaft bend · separating the 1× family.
- Grows from: imbalance as the 1× reference (E3); **prerequisites inherited from E3:**
  confirm/refute the ~16.5 Hz axial rig mode on health data (misalignment lives in the
  axial channel — without this check the axial control at ~1000 rpm is unusable), and
  apply the `f1_in_2x` guard (the 2-pole trap repeats at 2f1 vs 2×fr).
- Channel/tool: VIBRATION, 1× + 2× + 3×, the axial axis (c4).
- What we show: misalignment gives a strong 2× and a noticeable AXIAL vibration; bend
  gives 1× + 2× with its own ratio. Key idea: imbalance, misalignment and bend ALL
  give 1× — we separate them by 2×, the axial component, and phase.
- Closes: the "imbalance / misalignment / bend" separation — the first row of the
  future discrimination matrix.
- Severity axis: misalignment H/L (available!) → a severity axis; bend — no label.
- `[Rotor_Misalignment]` (H/L) · `[Bend]`  →  folder `04_misalignment_bend`

═══════════════════════════════════════════════════════════════════════

## Episode 5 — Bearings I: tooling + raceways
Investigations: characteristic-frequency theory + envelope · outer race · inner race.
- Grows from: the vibration floor (E1); this is NEW tooling.
- Channel/tool: VIBRATION, band-pass + envelope (demodulation), characteristic
  frequencies BPFO/BPFI/BSF from bearing geometry.
- What we show: why a bearing is invisible in the direct spectrum but visible in the
  envelope; outer race → BPFO (a stable line); inner race → BPFI modulated at 1×
  (sidebands around BPFI).
- Closes: the envelope tool; the BPFO and BPFI signatures.
- Severity axis: both H/L → we show the signature growing with severity.
- `[Bearing_Outer]` (H/L) · `[Bearing_Inner]` (H/L)  →  folder `05_bearings_races`

═══════════════════════════════════════════════════════════════════════

## Episode 6 — Bearings II: rolling elements + race composite
Investigations: ball (rolling element) · inner+outer at once · severity axis.
- Grows from: the envelope tool (E5).
- Channel/tool: VIBRATION, envelope; BSF and its modulation by the cage (FTF).
- What we show: the ball signature (BSF, often weaker and "drifting"); in the two-race
  composite — two characteristic lines at once, checking additivity.
- Closes: the full bearing family; signature additivity (prepares the composites).
- Severity axis: ball H/L; race composite — H only.
- `[Bearing_Ball]` (H/L) · `[Bearing_Inner-Bearing_Outer]`  →  folder `06_bearings_ball`

═══════════════════════════════════════════════════════════════════════

## Episode 7 — Stator-electrical: winding and supply
Investigations: inter-turn winding short · voltage unbalance · local vs symmetric.
- Grows from: the clean current-unbalance and THD floor (E1).
- Channel/tool: CURRENT, symmetrical components (negative sequence), phase unbalance;
  harmonics.
- What we show: an inter-turn short raises the unbalance and specific harmonics
  LOCALLY (one phase); supply unbalance raises the unbalance SYMMETRICALLY across the
  supply. We tell the source apart by the sequence picture.
- Closes: stator-electrical; the "winding vs voltage" separation.
- Note: voltage unbalance was recorded ONLY under torque (no speed protocol) — state
  this as a limitation.
- Severity axis: winding H/L; voltage — L only.
- `[Winding]` (H/L) · `[Voltage_Unbalance-Torque_Circulation]` (L)  →  folder `07_stator`

═══════════════════════════════════════════════════════════════════════

## Episode 8 — Composite faults and anomaly resolution
Investigations: bearing composites (superposition) · resolving the inner/outer speed
mix-up · the fault discrimination matrix.
- Grows from: ALL single signatures (E2–E7) — cannot be assembled earlier.
- Channel/tool: current and vibration together; signature superposition.
- What we show: in composites the rotor/stator part (current) and the bearing part
  (envelope) live in different places and add up rather than interfere; all of it is
  collapsed into a DISCRIMINATION MATRIX (which fault, in which channel, at which
  frequency).
- Anomaly resolved: `[Rotor_Misalignment-Bearing_Outer]/speed` — 12 files while the
  inner folder is empty; split by BPFI/BPFO (the tool from E5).
- Closes: composite handling; the naming anomaly; the discrimination matrix.
- `[*-Bearing_Inner]` · `[*-Bearing_Outer]` composites (broken bar, imbalance,
  misalignment, winding) · the misalignment-outer/speed anomaly
  →  folder `08_composites`

═══════════════════════════════════════════════════════════════════════

## Episode 9 — Dynamic diagnostician: engine and early warning
Investigations: multi-class engine · streaming states and trend logic · early warning.
- Grows from: the discrimination matrix (E8) and all indicators.
- Channel/tool: sliding window; gates (plateau / transition / poorly-resolvable);
  sticky alarm; trend confirmation; parallel indicators for all classes.
- What we show: one pass emits a status per fault type; a degradation demo
  healthy → watch → alarm, with the modelled axis honestly flagged.
- Closes: the project's end goal — dynamic condition assessment and a diagnosis over
  the listed parameters.
- `[all classes together]`  →  folder `09_engine`

═══════════════════════════════════════════════════════════════════════

## Dependencies (what cannot be assembled without what)

    E1 ─┬─> E2 (broken bar) ─────────────────────────┐
        ├─> E3 (imbalance) ─> E4 (misalign./bend) ───┤
        ├─> E5 (bearings I) ─> E6 (bearings II) ──────┼─> E8 (composites+matrix) ─> E9 (engine)
        └─> E7 (stator) ──────────────────────────────┘

- E8 needs ALL singles (E2–E7): superposition and the matrix cannot be built without them.
- The misalignment inner/outer anomaly in E8 needs the envelope tool from E5.
- E9 needs the matrix from E8.
- **E4 additionally needs two E3 deliverables:** the ~16.5 Hz axial-mode verdict on
  health data, and the `f1_in_2x` resolvability guard.

## Possible reordering (optional)
The stator block (E7) is electrical and independent of mechanics/bearings; it could be
moved right after broken bar (E2) to finish all CURRENT-based electrical faults in a
row (rotor → stator → supply) before switching to vibration. Order would then be
E2 → E7 → E3 → E4 → E5 → E6 → E8 → E9. Downside: it breaks the resonance→imbalance
mechanical block that currently follows straight from E1. Current order is preferred.

## Severity-axis notes
"Signature grows with severity" can be shown where H/L exists: bearings (all three),
misalignment, winding. NO severity label: broken bar, imbalance, bend, composites —
there we build only the "signature vs speed/load" axis.
