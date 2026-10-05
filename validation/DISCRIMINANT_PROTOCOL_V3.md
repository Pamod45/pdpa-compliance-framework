# Discriminant test protocol - DSR iteration 3, the LAST (written 2026-10-05, BEFORE any v3 score was computed)

**Stopping rule (agreed before building):** this is the final iteration. Whatever it shows is reported and the
project moves to the LLM baseline. If it passes, config_v3 becomes the method of record; if not, v1.1 stays.

**Why:** iteration 2 failed H5. Absolute cosine tracked writing STYLE: code-heavy real text sat far from all catalog
prose (si-12 0.900 -> 0.000) while generic filler sat close to all of it (si-12 filler 0.462).

**Change (config_v3/, otherwise identical to v1.1):** relative relevance. For each SSP text:
own = best cosine to its OWN control's catalog rows; others = the same for each OTHER control in the SSP (16 for
FleetTrack); z = (own - mean(others)) / sd(others); factor = clamp(z / 2, 0, 1). Style moves all similarities
together, so z cancels it. 2 = conventional "two standard deviations"; no tuned constant.

**Fresh variants (`degrade_ssp.py --set v3`):** index%3==0 statements deleted (v1: ==2, v2: ==1); LAST half of
sentences kept (v1 first sentence, v2 first half); third filler wording + decoys standards.md / rules.yaml;
third valid rotation. v1 and v2 variants are reported as SECONDARY only.

## Hypotheses and pass criteria (identical to iteration 2)
- **H1** strong > partial > broken. *Prediction: PASS.*
- **H2** Alignment identical across variants. *Prediction: PASS.*
- **H3** vague_padded <= partial. *Prediction: UNCERTAIN, leaning PASS* - generic filler should be about equally
  similar to every control, so z ~ 0.
- **H4** swapped <= partial. *Prediction: likely PASS* - the true control is among the "others", so z < 0.
- **H5** strong keeps >= 80% of its v1.1 Realization. *Prediction: UNCERTAIN* - depends on whether real text points
  at its own control by ~2 SD; texts written at parent level or shared across controls may not.

**Success = H1-H5 all PASS.** Anything less: iteration 3 is reported as tested and not adopted.
