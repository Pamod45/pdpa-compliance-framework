# Discriminant test protocol - DSR iteration 2 (written 2026-10-05, BEFORE any relevance score was computed)

**Why iteration 2:** v1 (config v1.1) failed H3 (padding) and H4 (wrong-mechanism): Maturity scores how specific
text *looks*, never whether it is *about* the control. v1 results stand unchanged; this is a declared second iteration.

**Change (config_v2/, everything else identical to v1.1):** each SSP by-component score is multiplied by a 0-1 ramp of
cosine(text, the catalog row it is attached to, incl. parent stem); ramp 0.25 -> 0.45 (re-used from Coverage, no new constants).

**Fresh variants (v2 rules, generated before scoring, `degrade_ssp.py --set v2`):** different statements deleted
(index%3==1), first HALF of sentences kept, different filler and decoy files, second valid rotation (k=4 vs k=3 in v1).
The v1 variants have been seen, so under the v2 scorer they are reported as SECONDARY only, never as evidence.

## Hypotheses and pass criteria (fixed now; same H1-H4 criteria as v1, plus H5)
- **H1** mean Realization strong > partial > broken. *Prediction: PASS.*
- **H2** all pair Alignments identical across variants. *Prediction: PASS* (relevance touches Realization only).
- **H3** vague_padded <= partial. *Prediction: UNCERTAIN* - catalog prose is itself generic, so generic filler may still look related.
- **H4** swapped <= partial. *Prediction: likely PASS* - text about another control should sit far from this row.
- **H5 (new, guards the fix)** strong FleetTrack under config_v2 keeps >= 80% of its mean Realization under v1.1.
  *Prediction: UNCERTAIN* - real FleetTrack text is code-heavy (e.g. "require_roles() in rbac.py") and may sit far from catalog prose.

A fix that passes H3/H4 but fails H5 is NOT a success: it would mean the check punishes genuine implementations.
All results are reported whatever they show.
