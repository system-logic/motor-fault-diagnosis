# Health-baseline parameter catalog — ZZU-MCC5

Reference document for building the **health** analysis over both protocols
(`speed_circulation` + `torque_circulation`). It fixes WHAT we measure, HOW, IN WHICH
WINDOW, and WHY (which future fault each metric calibrates).

---

## 0. Scope and fixed decisions

- **Scope:** health files only, both protocols. The baseline and thresholds are built
  and validated here; they are applied to faults in later sections.
- **Unit of analysis = the PLATEAU (operating point), not the file.** One file yields
  several plateaus. In `torque` plateaus differ by load (f1 ~const); in `speed` by
  speed (f1 steps). The table = metrics over the (speed × load) plane.
- **Poles fixed at 2 (1 pole pair), n_s = 60·f1.** No 2/4/6/8 auto-search. Correctness
  is checked separately (slip in range). Confirmed on data.
- **Vibration in consistent digital units from health itself, relative.** No datasheet
  sensitivity (mV/g); no physical mm/s claimed. All vibration conclusions are in terms
  of "how many times / how many dB".
- **Spread — both kinds, threshold from the larger** (see group 4).

---

## 0-bis. Recon on real data (4 health files, both protocols)

Checked on `*40Nm_3000rpm*` and `*20Nm_1000rpm*` of both protocols.

**File structure:** 90 s record, Fs = 12800 Hz, 1 152 000 rows, 9 columns (last one
all-NaN). After cleaning — 8 columns, of which 7 are physical.

**Channel map (confirmed by signal shape):**

| column | channel | tell |
|---|---|---|
| col0 | **time counter — DROP** | sawtooth, slope exactly 1.0/s, reset every 1.28 s (2¹⁴ samples) |
| col1 | keyphase | pulses at rotation frequency; rpm matches the nominal |
| col2, col3, col4 | vibration (3 axes) | high-frequency, small amplitude |
| col5, col6, col7 | current (3 phases) | dominant at f1, phase shifts 120°/240° |

**THERE IS NO TORQUE CHANNEL.** What an old script would take for torque (col0,
low dominant freq) is the timer. Consequences: `load_Nm_meas` is not measured → the
load coordinate = nominal from the file name; plateaus are detected by SPEED, not
torque; in `classify` the timer channel is detected explicitly (sawtooth, slope
≈1.0/s) and dropped.

**f1 steps between plateaus in speed_circulation — confirmed:**
- speed 40/3000: f1 per plateau 50.11 → 41.83 → 50.11 Hz, slip ~2.9% (≈const);
- speed 20/1000: f1 per plateau 16.76 → 8.29 → 16.74 Hz, slip ~1.7% (≈const).

So the drive changes f1, slip holds (load const), speed steps. Speed profile:
high → low → high. The intermediate speed-protocol levels (≈2450, ≈490 rpm) do NOT
fall on the 1000/2000/3000 grid — bonus coverage of the speed axis, though the
crossing point with the torque protocol is mostly at the nominal (top) level.

**torque_circulation — confirmed:** f1 fixed, speed sits at the nominal with small
steps (e.g. 2900/2950/3000) — these are LOAD steps shown through slip.

**2 poles — confirmed:** n_s = 60·f1 gives slip 1.7–3% (physical).

**Vibration axes — determined (updated):** on health the 1× is near noise on all
three axes, so the "lowest 1×" heuristic is unreliable. However, the **speed-dependence**
of the residual 1× (axis `c3` rises strongly toward 3000 rpm, `c4` stays low) already
assigns the axes, and this is **confirmed by the resonance check**:
`c3` = **main radial** (imbalance-sensitive), `c4` = **axial**, `c2` = second radial.

---

## 1. Unit of analysis and the regime plane

Each output row = **one plateau**. Row key (actual table fields):

| field | meaning |
|---|---|
| `protocol` | speed / torque |
| `file` | source file name |
| `plateau_idx` | plateau index within the file |
| `rpm_meas` / `rpm_level` | plateau speed (measured / rounded) |
| `load_nominal_Nm` | plateau load (nominal from the file name) |

The plane is covered by the two protocols complementarily: `torque` densely covers the
**load** axis (at 3 speeds), `speed` covers the **speed** axis (at 2 loads). Points
reached by BOTH protocols (same speed and load) are **crossing points**: health metrics
there must agree. A mismatch = a flag (hysteresis / transient / measurement issue) and
the first substantive result of the analysis.

---

## 2. Group 1 — Working point (coordinates and geometry)

| metric | unit | channel | how | window | calibrates / meaning |
|---|---|---|---|---|---|
| `f1_Hz` | Hz | current A | spectral peak 5–80 Hz + parabolic interpolation | Hann | coordinate; drive frequency; steps between plateaus in `speed` |
| `rpm_meas` | rpm | keyphase | median inter-edge interval, sub-sample edge time | — | accurate speed; more reliable than torque |
| `fr_Hz` | Hz | = rpm/60 | rotation frequency | — | driver of 1×/2×/3× and current bands f1±fr |
| `load_nominal_Nm` | Nm | file name | nominal 20/40 | — | load coordinate (NO torque channel — see 0-bis) |
| `slip_pct` | % | f1, rpm | (n_s−rpm)/n_s, n_s=60·f1 | — | working point; **pole check** |
| `sb_offset_Hz` | Hz | = 2·s·f1 | broken-bar sideband offset | — | geometry/resolvability of the future signature |

**Sanity expectations:** f1 linear in rpm (≈50 Hz @ 3000); slip > 0, in ~0.3–4%;
slip going negative or jumping to a 4-pole reading = an error.

---

## 3. Group 2 — Signature floors (normal level for future faults)

The heart of the baseline: for each fault family, health sets the "quiet" level that
later becomes a threshold.

| metric | unit | channel | how | window | for which fault |
|---|---|---|---|---|---|
| `sb_floor_bb_dB` | dB rel. f1 | current A | max level in f1 ± (guard..2s·f1) | Hann | **broken bar** → threshold |
| `vib_1x_{c2,c3,c4}` | rel. | vib 3 axes | amplitude at fr | **flat-top** | **imbalance** (main), misalignment, bend |
| `vib_2x_{c2,c3,c4}` | rel. | vib 3 axes | amplitude at 2·fr | **flat-top** | misalignment, looseness; imbalance control |
| `vib_3x_{c2,c3,c4}` | rel. | vib 3 axes | amplitude at 3·fr | **flat-top** | misalignment / looseness (higher orders) |
| `cur_sb_1x_dB` | dB rel. f1 | current A | floor of bands f1 ± fr | Hann | **imbalance/eccentricity via current** — NEW |
| `bearing_floor_*` | dB | vib | floor at BPFO/BPFI/BSF | Hann | bearings — **reserved**, needs geometry |

Notes:
- `vib_1x` is **not zero** on a healthy motor — residual imbalance always exists. The
  baseline captures that level; a fault is measured from it, not from zero.
- `cur_sb_1x_dB` was absent in the old code; needed for imbalance-via-current.
- `bearing_floor_*` — placeholder reserved in the schema, computed in the bearing
  section (needs bearing geometry for the characteristic frequencies).

---

## 4. Group 3 — Current unbalance and harmonics (winding / voltage)

| metric | unit | channel | how | window | for which fault |
|---|---|---|---|---|---|
| `I_rms` | rel. | current A | RMS on the plateau | — | current-amplitude baseline |
| `thd_pct` | % | current A | harmonics 2..7 rel. f1 | Hann | distortion baseline |
| `unbalance_pct` | % | current A,B,C | weak-sequence fraction (rotation-agnostic) | Hann | **inter-turn short** + **voltage unbalance** (one baseline, separated later) |

Note: the phase sequence in the dataset is reversed — unbalance is computed as the
ratio of the smaller symmetrical component to the larger, otherwise a strict
Vneg/Vpos "explodes".

---

## 5. Group 4 — Spread (basis for thresholds)

For each group 2–3 metric we compute TWO spreads:

| spread | how | answers |
|---|---|---|
| `*__std_in`, `*__ptp_in` | over non-overlapping sub-windows within the plateau | does the metric wobble at fixed conditions (instantaneous stability) |
| between-protocol | over repeats of one operating point (duplicates + protocol crossing points) | does the norm reproduce run-to-run (rig stability) |

- **The alarm threshold is built from `max(within, between)`.** Within-plateau alone
  gives an optimistically narrow threshold → false alarms on a healthy file from another
  series.
- The between spread is estimated from 2–3 values → **an indicator, not statistics**.
  Stated honestly: within-plateau is the main spread for thresholds; between-run is a
  separate confidence flag.
- The spread at **protocol crossing points** is literally the measured "cost" of
  merging the two protocols into one baseline. Small → the merge is honest.

---

## 6. Group 5 — Sanity / data quality (trust gate, shown once)

| metric | meaning |
|---|---|
| `channel_map_consistent` | were channels identified the same way in all files |
| `speed_jitter_pct` | keyphase interval spread (rotation-sensor quality) |
| `f1_linearity_resid` | residual of the f1 ∝ rpm linearity |
| `slip_in_range` | slip in the physical range (indirectly confirms 2 poles) |
| `plateau_found`, `n_plateau` | was a stable plateau found, and how many |

---

## 7. Window choice — why two

| task | window | reason |
|---|---|---|
| **amplitude** (`vib_1x/2x/3x`) | flat-top | accurate amplitude regardless of bin placement; Hann underestimates by up to ~1.4 dB |
| **frequency / floors / SNR / dB rel. f1** | Hann | narrow main lobe, good resolution; amplitude not critical there |

Two windows for two tasks — a deliberate choice, not an inconsistency.

---

## 8. Validation outputs of this stage (all on health)

1. **f1 vs rpm**, both protocols overlaid → confirms 2 poles and drive operation.
2. **slip vs load** → slip grows monotonically with load.
3. **floors (`sb_floor_bb`, `cur_sb_1x`, `vib_1x`) vs speed** with spread bars.
4. **Agreement table at protocol crossing points** (metric match).
5. **Sanity table** (group 5) — once, a pipeline-trust gate.

---

## 9. Open questions (resolved / status)

- **Vibration XYZ axis orientation** — **RESOLVED** (see 0-bis): `c3` main radial,
  `c4` axial, `c2` second radial, from residual-1× speed-dependence and confirmed by
  the resonance check.
- **File selection — by regex** on `(\d+)Nm` and `(\d+)rpm` + protocol by substring,
  not by an exact `circulation` match (guards against future name typos). Implemented.
- **Duplicate operating points** (outside health, same policy): with ≥2 files per
  point — a deliberate pick or averaging, not counting the point twice.
- **Bearing geometry** — for `bearing_floor_*`, reserved for the bearing section.

---

## 10. What changed vs the old `analize_health.py` (historical)

- Unit of analysis: **file → plateau** (several plateaus per file, both protocols).
- **col0 is a timer, not torque:** detect the counter sawtooth and drop it; the old
  `classify` would have taken it for torque. Torque as a channel is ABSENT.
- Stationarity/plateaus — **by speed** (from keyphase), not torque.
- Poles: **2/4/6/8 auto-search → fixed 2** with a slip check.
- `vib_2x`/`3x`: were computed but not written to the table → **restored**.
- **Added** `cur_sb_1x_dB` (floor of current bands f1±fr) — for imbalance.
- Amplitude metrics: **flat-top** window instead of Hann.
- Spread: added the **between-run** spread on top of within-plateau.
- In `speed_circulation`: f1 and slip are computed **per plateau**, not globally per file.
