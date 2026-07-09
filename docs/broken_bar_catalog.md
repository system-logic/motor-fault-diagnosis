# Parameter catalog — broken rotor bar (Episode 2)

Reference document for the broken-bar block. Fixes what we measure, with what, in which
window, with which indicators, and where the honest boundaries are. Modelled on
`health_baseline_catalog.md` and built on its results.

Fixed decisions for this block:
- **Deep indicator analysis:** the NAIVE one first (rise over the healthy baseline) — to
  show the cross-protocol problem live — then the SELF-SUFFICIENT SNR as the cure.
- **Harmonic comb k=1,2,3:** bands at f1·(1±2ks). More harmonics = more robust rejection
  of false peaks AND a chance to rescue poorly-resolvable regimes (higher bands are
  further from f1).
- Always go deep; when choosing "simpler vs deeper", go deeper.

═══════════════════════════════════════════════════════════════════════

## 0. What we inherit (not reinvented)

Carried over from health and the earlier work as-is:
- plateau detection, single-plateau window, channel identification (col0 timer dropped,
  current = 3 phases, vibration = 3 axes, no torque);
- **f1 and slip computed PER PLATEAU** (critical for the speed protocol);
- poles fixed at 2, n_s = 60·f1;
- the current sideband floor from the health baseline (`sb_floor_bb_dB`) — the starting
  reference for the naive indicator;
- prototypes: `compare_fault` (healthy vs fault in current, unbalance as a control),
  `plateau_spectrum` (single-plateau spectrum, peak sharpness), `stage_3.sb_snr`
  (band prominence over shoulders — the core of the self-sufficient indicator).

═══════════════════════════════════════════════════════════════════════

## 0-bis. Recon on 4 files, then confirmed on all 12

Checked on pure `Broken_Bar`, both protocols, 20 Nm at 1000 and 3000 rpm (recon), then
run on the full 12 files (both loads, both protocols).

**Confirmed:**
- Channel identification and plateaus — as in health (kp=1, current=5,6,7,
  vib=2,3,4, timer=0), no changes. df=0.056 Hz ≪ the offset — resolution is sufficient.
- **The signature is real and strong:** bands land exactly on f1(1±2ks) by the measured
  slip (error < 0.04 Hz at 1000, up to 0.13 at 3000). The comb k=1,2,3 is visible. In
  speed the first-band SNR is 20–24 dB.
- Channel control: the same layout on the fault as on the norm.

**FINDING (changes torque handling):** at light load (20 Nm) the speed in torque wanders
only ~18 rpm < the merge threshold → the detector merges the WHOLE record into one
"plateau". But inside it the load sweeps full→0, slip drifts 1.6%→−0.2%, the 2s·f1
offset drifts 0.54→0 Hz → the band SMEARS over ~0.6 Hz and dies (SNR 5 dB). A max-load
segment taken separately → SNR **52 dB**. The signature was huge; it was being killed by
averaging over load.

**Results confirmed on the full run:**
1. **Torque must be segmented by slip** (slip = the load proxy from health): sliding
   short windows with slip ≈ const, analysing the MAX-load window (max slip). This gives
   the "signature vs load" axis for free.
2. The "poorly-resolvable" notion **splits into two**, both now confirmed:
   (a) **true unresolvability** — 2s·f1 too small even at stable slip (bands at the f1
   skirt); (b) **load-mixing smear** — fixed by segmentation, NOT a real limit.
   The **true limit (a) is confirmed** at `speed 40/1000`: slip is high (4.3%) but f1 is
   only ~8 Hz, so the offset ~0.7 Hz hugs the f1 skirt and SNR drops to ~2 dB — while an
   upper plateau of the same file gave 26–30 dB.
3. **Naive vs SNR proven:** the naive rise scatters by up to ~15 dB between protocols at
   the same regime, while the self-sufficient SNR stays tight — the self-sufficient
   indicator solves the cross-protocol problem. (Naive is also unavailable where the
   health floor was undefined — another point for SNR.)
4. **Load = strength axis:** 40 Nm → band SNR ~37–44 dB; 20 Nm → ~15–26 dB.
5. In speed there is no problem: load is const within a plateau, slip is stable, bands
   are sharp — which is why the speed regimes gave clean 20+ dB.

═══════════════════════════════════════════════════════════════════════

## 1. Signature physics (what exactly we look for)

A broken bar makes the rotor cage asymmetric → induces a backward-rotating field → the
stator current gets SIDEBANDS around f1 at:

    f_sb(k) = f1 · (1 ± 2k·s),   k = 1, 2, 3

- k=1: lower LSB = f1(1−2s), upper USB = f1(1+2s); offset 2s·f1.
- k=2: f1(1±4s); offset 4s·f1.  k=3: f1(1±6s); offset 6s·f1.
- **The lower band (LSB) is the primary indicator** (directly tied to rotor asymmetry).
  The upper (USB) is weaker and depends on inertia / speed ripple — we measure both but
  rely on LSB.

Key properties the checks grow from:
- **Bands FOLLOW slip.** Position is strictly f1(1±2ks) by the MEASURED s. A real broken
  bar sits exactly where slip predicts; a random peak does not. This is the signature
  (analogous to the slip-slope signature in health).
- **Load/speed dependence.** More load ⇒ larger s ⇒ larger offset ⇒ bands more
  resolvable and stronger. At no load s→0 ⇒ bands collapse into f1 ⇒ invisible. Hence
  poorly-resolvable regimes (40/1000: 2s·f1 ≈ 1.1 Hz).
- **The comb k=1,2,3 confirms.** The full comb (not a single peak) is strong evidence of
  a broken bar. Note the higher bands are FURTHER from f1 (4s·f1, 6s·f1) → at low slip
  they resolve better than the first, though they are weaker.

═══════════════════════════════════════════════════════════════════════

## 2. Group 1 — Working point and band geometry (per window)

| metric | unit | how | meaning |
|---|---|---|---|
| `f1_Hz` | Hz | current peak 3–80 Hz + parabolic | carrier; per plateau |
| `rpm` | rpm | keyphase | window speed |
| `slip_pct` | % | (60f1−rpm)/(60f1) | driver of band position |
| `fr_Hz` | Hz | rpm/60 | for the control (imbalance bands f1±fr) |
| `off_2s_Hz` | Hz | 2s·f1 | k=1 band offset |
| (4s·f1, 6s·f1) | Hz | 4s·f1, 6s·f1 | k=2, k=3 offsets (used internally) |
| predicted f_lsb/f_usb | Hz | f1(1∓2ks), k=1,2,3 | predicted band centres |

═══════════════════════════════════════════════════════════════════════

## 3. Group 2 — Band signatures (heart of the block)

Per band (LSB/USB × k=1,2,3), as built in `broken_bar_analyze.py`:

| metric | how | meaning |
|---|---|---|
| `lsb{k}_dB`, `usb{k}_dB` | max level in the search window, dB rel. f1 | band level |
| `naive_rise_dB` (NAIVE) | headline band level − healthy floor of the same regime/protocol | rise over baseline — STAGE A |
| `lsb{k}_snr`, `usb{k}_snr` (SNR) | peak − median of shoulders at the same offset | prominence over the local floor — STAGE B |
| `headline_snr` | max(lsb1_snr, usb1_snr) | per-window headline indicator |
| `comb_coherence` | fraction of k=1,2,3 bands whose position error is in tolerance | signature genuine? |

(Position error per band is computed internally; peak `width` is optional and not stored.)

Band search window: `half = max(3·df, 0.12·off_2s)`, centred on the predicted f_lsb/f_usb.

**Two indicators — why both (the narrative):**
- STAGE A, `naive_rise_dB` — naive. Needs the healthy floor of the same protocol.
  INHERITS the cross-protocol spread from health (up to 9 dB) → we SHOW the problem on it.
- STAGE B, `lsb/usb{k}_snr` — self-sufficient. Numerator and denominator from one
  spectrum → common noise cancels → no cross-protocol calibration. The cure.
- B's success test: at the same points speed vs torque the SNR agrees far more tightly
  than the naive rise. **Confirmed** (naive ~15 dB spread vs SNR tight).

═══════════════════════════════════════════════════════════════════════

## 4. Group 3 — Controls and rejection (this is the rotor, not something else)

| metric | expected for a broken bar | why |
|---|---|---|
| `unbalance_pct` | does NOT rise (≈ health) | broken bar is rotor, not stator; control as in compare_fault |
| `ctrl_fr_snr` (f1±fr) | does NOT rise | rejects imbalance (whose bands sit at fr, not 2sf1) |
| `comb_coherence` | k=1,2,3 ALL follow s | a false peak won't line up this way |
| `resolvable` (flag) | off_2s > 3·df → resolvable, else marked | honest unresolvability zone |

═══════════════════════════════════════════════════════════════════════

## 5. Group 4 — Spread (basis for thresholds and the proof of the cure)

- Within-window / within-file spread of a metric = its own noise.
- **Between-protocol spread** at the same operating point is the key one: for the naive
  rise it is large, for the SNR it is small. That is the quantitative proof that the
  self-sufficient indicator solves the problem. It is **shown via the naive-vs-SNR
  figure** rather than stored as a column.
- A watch/alarm threshold is built from the SNR spread for the chosen indicator (SNR).

═══════════════════════════════════════════════════════════════════════

## 6. Group 5 — Sanity + comb coherence

- Inherited from health: channel consistency, slip in range, plateau found.
- **Is the frequency resolution enough?** df = 1/T_window must be well below off_2s
  (else the k=1 band won't separate from f1). Flagged via `resolvable` (off_2s > 3·df).
- **Comb coherence:** the fraction of k=1,2,3 bands whose position error is in tolerance.
  High → genuine signature; low → random peaks.

═══════════════════════════════════════════════════════════════════════

## 7. Windows and the frequency-resolution requirement

- Spectrum — **Hann** (we care about band position and level, not absolute amplitude →
  flat-top not needed, unlike imbalance 1×).
- **Window length matters:** to separate a band from f1 we need df ≪ off_2s. At 40/1000
  off_2s≈1.1 Hz → T ≳ 10 s (df ≲ 0.1 Hz).
- **BUT (recon): the window must have STABLE slip.** In torque at light load a merged
  plateau mixes load (slip drifts) → the offset drifts → the band smears, and a long
  window HURTS. Rule: segment by slip, take a window where slip ≈ const (the slip range
  in the window gives a smear 2·Δs·f1 — keep it < df). For characterising the fault, use
  the MAX-load window (max slip). Length↔stability trade-off: shorter window → worse df
  but steadier slip; choose empirically (in recon, a 6 s max-load window beat an 18 s
  merged one decisively). As built: `WIN_SEC = 8 s`, `STEP_SEC = 2 s`.
- Higher harmonics (k=2,3) resolve better than the first at low s → a further plus of the
  comb.

═══════════════════════════════════════════════════════════════════════

## 8. Validation outputs of the block

1. Healthy vs broken bar: overlaid spectra on a focus regime with LSB/USB (k=1..3) marks.
2. Per-window table: band levels / rise / SNR for both protocols.
3. Naive vs SNR at protocol crossing points → proof that SNR removes the cross-protocol
   spread. **Done.**
4. Signature vs speed and load; resolvability map (where not resolvable). **Done.**
5. Signature track: measured band centres vs predicted f1(1±2ks) — do they line up. **Done.**
6. Control: unbalance healthy ≈ broken bar (did not rise). **Done.**
7. Composites: rotor bands alive, unbalance did not rise (block Stage 4 — **pending**).

═══════════════════════════════════════════════════════════════════════

## 9. Honest boundaries of the block

- **Only the severe defect (H), no severity label** → no "depth / number of broken bars"
  axis; we build only the "signature vs speed/load" axis.
- **Number of broken bars** (classic formulas from LSB level) is NOT calibrated without
  severity grades — qualitative at most, with a caveat.
- **No time-degradation recording** → the growth rate is MODELLED with a disclaimer (as
  in the old stage_4); the run-time axis is nominal.
- **Composites** `Broken_Bar-Bearing_Inner/Outer` are taken ONLY by the rotor part
  (current); the bearing part is out of this block and moves to Episode 5.
- **Poorly-resolvable regimes** (small 2s·f1, e.g. 40/1000) are flagged honestly — we do
  not pass noise off as signal.

═══════════════════════════════════════════════════════════════════════

## 10. Diff vs the old code (historical)

- `compare_fault`: hard-coded paths and one FOCUS regime → moved to folder auto-resolve
  and ALL regimes of both protocols; f1/s per plateau; added k=2,3.
- `plateau_spectrum`: gives a sharp peak on one plateau → we reuse its window/sharpness
  but expand it into a batch over all plateaus + the comb.
- `stage_3.sb_snr`: the core of the self-sufficient indicator — carried over as STAGE B.
- New: the naive `rise` indicator as a contrast; position error / comb coherence; the
  between-protocol spread as proof; the frequency-resolution flag (`resolvable`).

═══════════════════════════════════════════════════════════════════════

## Block dataset
- `[Broken_Bar]` — speed/H:6, torque/H:6 (pure class).
- `[Broken_Bar-Bearing_Inner]` — speed/H:6, torque/H:6 (composite, Stage 4).
- `[Broken_Bar-Bearing_Outer]` — speed/H:6, torque/H:6 (composite, Stage 4).
- The health baseline is already built (reference for the naive indicator).
