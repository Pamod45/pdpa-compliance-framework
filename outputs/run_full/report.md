# PCEF run report

- Run at (UTC): 2026-10-05T07:15:25+00:00
- Embedder: sentence-transformers/all-mpnet-base-v2 @ e8c3b32edf5434bc2275fc9bab85f82640a19130
- Clauses: PDPA-s5, PDPA-s6, PDPA-s7, PDPA-s8, PDPA-s9, PDPA-s10, PDPA-s12, PDPA-s22, PDPA-s23, PDPA-s24, PDPA-s26 | SSP: FleetTrack
- Thresholds: floor=0.2, coverage=0.35
- Placeholders in effect: relatedness row roll-up = max; maturity horizontal rule = max; maturity vertical rule = mean_excluding_na; config values are DRAFT, not frozen

## Clause level (one row per unit x control pair)

| Clause | Unit | Control | Source | Status | Rel | Cov | Str | Dir | Alignment | Realization |
|---|---|---|---|---|---|---|---|---|---|---|
| PDPA-s10 | s10-u1 | ac-3 | explicit_hint | scored | 0.560 | 1.000 | 1.000 | 1.000 | 0.890 | 0.900 |
| PDPA-s10 | s10-u1 | ac-2 | family_hint | scored | 0.581 | 0.750 | 1.000 | 0.800 | 0.758 | 0.129 |
| PDPA-s10 | s10-u1 | sc-28 | explicit_hint | scored | 0.543 | 0.500 | 1.000 | 1.000 | 0.711 | 0.600 |
| PDPA-s10 | s10-u1 | sc-8 | explicit_hint | scored | 0.486 | 0.500 | 1.000 | 1.000 | 0.697 | 0.600 |
| PDPA-s10 | s10-u1 | sc-13 | explicit_hint | scored | 0.490 | 0.250 | 1.000 | 1.000 | 0.610 | 0.000 |
| PDPA-s12 | s12-u1 | pm-18 | explicit_hint | scored | 0.560 | 0.500 | 1.000 | 1.000 | 0.715 | 0.150 |
| PDPA-s12 | s12-u1 | pm-19 | explicit_hint | scored | 0.472 | 0.375 | 1.000 | 1.000 | 0.649 | 0.000 |
| PDPA-s22 | s22-u1 | sa-9 | explicit_hint | excluded (applicability) | 0.348 | - | - | - | - | - |
| PDPA-s22 | s22-u2 | sa-9 | explicit_hint | excluded (applicability) | 0.489 | - | - | - | - | - |
| PDPA-s22 | s22-u3 | sa-9 | explicit_hint | excluded (applicability) | 0.478 | - | - | - | - | - |
| PDPA-s22 | s22-u4 | sa-9 | explicit_hint | excluded (applicability) | 0.330 | - | - | - | - | - |
| PDPA-s23 | s23-u1 | ir-8.1 | explicit_hint | scored | 0.676 | 0.667 | 1.000 | 1.000 | 0.802 | 0.000 |
| PDPA-s23 | s23-u1 | ir-6 | explicit_hint | scored | 0.550 | 0.333 | 1.000 | 1.000 | 0.654 | 0.250 |
| PDPA-s23 | s23-u1 | ir-8 | family_hint | scored | 0.454 | 0.333 | 1.000 | 1.000 | 0.630 | 0.109 |
| PDPA-s24 | s24-u1 | ra-8 | explicit_hint | scored | 0.701 | 0.667 | 1.000 | 1.000 | 0.809 | 0.150 |
| PDPA-s24 | s24-u2 | ra-8 | explicit_hint | scored | 0.398 | 0.000 | 1.000 | 1.000 | 0.499 | 0.150 |
| PDPA-s24 | s24-u3 | ra-8 | explicit_hint | scored | 0.237 | 0.000 | 1.000 | 1.000 | 0.459 | 0.150 |
| PDPA-s24 | s24-u4 | ra-8 | explicit_hint | scored | 0.320 | 0.000 | 1.000 | 1.000 | 0.480 | 0.150 |
| PDPA-s5 | s5-u1 | pt-2 | explicit_hint | scored | 0.502 | 0.000 | - | 1.000 | 0.442 | 0.450 |
| PDPA-s5 | s5-u1 | pt-3 | family_hint | scored | 0.472 | 0.000 | - | 1.000 | 0.433 | 0.400 |
| PDPA-s5 | s5-u2 | pt-3 | family_hint | scored | 0.522 | 0.000 | - | 1.000 | 0.448 | 0.400 |
| PDPA-s5 | s5-u2 | pt-2 | explicit_hint | scored | 0.505 | 0.000 | - | 1.000 | 0.443 | 0.450 |
| PDPA-s5 | s5-u3 | pt-4 | explicit_hint | scored | 0.509 | 0.000 | - | 1.000 | 0.444 | 0.000 |
| PDPA-s5 | s5-u3 | pt-2 | family_hint | scored | 0.460 | 0.000 | - | 1.000 | 0.429 | 0.450 |
| PDPA-s5 | s5-u3 | pt-5 | explicit_hint | scored | 0.433 | 0.000 | - | 1.000 | 0.421 | 0.000 |
| PDPA-s5 | s5-u3 | pt-3 | family_hint | scored | 0.433 | 0.000 | - | 1.000 | 0.421 | 0.400 |
| PDPA-s6 | s6-u1 | pt-3 | explicit_hint | scored | 0.781 | 0.750 | 1.000 | 1.000 | 0.858 | 0.400 |
| PDPA-s6 | s6-u1 | pt-2 | family_hint | scored | 0.660 | 0.000 | 1.000 | 1.000 | 0.565 | 0.450 |
| PDPA-s7 | s7-u1 | pm-25 | explicit_hint | scored | 0.594 | 0.333 | 1.000 | 0.700 | 0.590 | 0.000 |
| PDPA-s7 | s7-u1 | pm-18 | family_hint | scored | 0.542 | 0.000 | 1.000 | 0.700 | 0.461 | 0.150 |
| PDPA-s8 | s8-u1 | si-18 | explicit_hint | scored | 0.693 | 1.000 | 1.000 | 0.400 | 0.773 | 0.450 |
| PDPA-s8 | s8-u1 | si-12 | family_hint | scored | 0.368 | 0.500 | 1.000 | 0.400 | 0.517 | 0.900 |
| PDPA-s8 | s8-u2 | si-18 | explicit_hint | scored | 0.697 | 0.500 | 1.000 | 0.400 | 0.599 | 0.450 |
| PDPA-s8 | s8-u2 | si-12 | family_hint | scored | 0.428 | 0.000 | 1.000 | 0.400 | 0.357 | 0.900 |
| PDPA-s9 | s9-u1 | si-18 | family_hint | scored | 0.571 | 0.500 | 1.000 | 0.400 | 0.568 | 0.450 |
| PDPA-s9 | s9-u1 | si-12 | explicit_hint | scored | 0.519 | 0.500 | 1.000 | 0.400 | 0.555 | 0.900 |
| PDPA-s9 | s9-u1 | si-12.1 | explicit_hint | scored | 0.562 | 0.000 | 1.000 | 0.400 | 0.391 | 0.000 |

- Unanchored units (no control hint): ['s5-u4', 's6-u2', 's9-u2', 's24-t1', 's24-t2', 's24-t3', 's26-u1', 's26-u2', 's26-u3', 's26-u4']
- Not-scored units: [('s22-u5', 'Represented but NOT scored: a conditional legal status-change trigger, not a data-handling or documentation obligation. None of SSS/CACR/CRS/CIMS/OIAS is designed to detect this. Flagged as open in clause_selection.md; whether the parameter set gains a treatment for reclassification triggers is an open decision.')]
- Dropped hints: none

Applicability flags raised:
- actor_assumed: SSP does not declare a PDPA role; assumed 'controller'
- prospective: duty fires on event (material change in methodology, technology, or process); assessed as readiness
- prospective: duty fires on event (personal data breach has occurred); assessed as readiness
- unresolved_condition: any_trigger_met=['s24-t1', 's24-t2', 's24-t3'] (SSP does not state)
- unresolved_condition: chosen_basis=consent (SSP does not state)
- unresolved_condition: conditional_on=a DPO has been designated under s.20 (SSP does not state)
- unresolved_condition: data_category=special_categories (SSP does not state)

## Control level (Realization is a control property)

| Control | Realization | Rows counted | Row statuses |
|---|---|---|---|
| ac-2 | 0.129 | 18 | absent:15, implemented:3 |
| ac-3 | 0.900 | 1 | implemented:1 |
| ir-6 | 0.250 | 2 | inherited:2 |
| ir-8 | 0.109 | 14 | inherited:14 |
| ir-8.1 | 0.000 | 3 | absent:3 |
| pm-18 | 0.150 | 7 | inherited:7 |
| pm-19 | 0.000 | 1 | absent:1 |
| pm-25 | 0.000 | 4 | absent:4 |
| pt-2 | 0.450 | 2 | inherited:2 |
| pt-3 | 0.400 | 4 | inherited:4 |
| pt-4 | 0.000 | 1 | absent:1 |
| pt-5 | 0.000 | 5 | absent:5 |
| ra-8 | 0.150 | 3 | inherited:3 |
| sa-9 | 0.094 | 3 | inherited:3 |
| sc-13 | 0.000 | 2 | absent:2 |
| sc-28 | 0.600 | 1 | implemented:1 |
| sc-8 | 0.600 | 1 | implemented:1 |
| si-12 | 0.900 | 1 | implemented:1 |
| si-12.1 | 0.000 | 1 | absent:1 |
| si-18 | 0.450 | 2 | inherited:2 |
