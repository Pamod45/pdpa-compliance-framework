# PCEF run report

- Run at (UTC): 2026-10-05T09:33:02+00:00
- Embedder: sentence-transformers/all-mpnet-base-v2 @ e8c3b32edf5434bc2275fc9bab85f82640a19130
- Clauses: PDPA-s5, PDPA-s6, PDPA-s7, PDPA-s8, PDPA-s9, PDPA-s10, PDPA-s12, PDPA-s22, PDPA-s23, PDPA-s24, PDPA-s26 | SSP: FleetTrack
- System PDPA role(s): ['controller', 'processor'] (SSP prop 'pdpa-role')
- Unit text mode: keywords | Floor gate: ON
- Thresholds: floor=0.2 | Coverage: ramp 0.25-0.45
- Rules: relatedness row roll-up = max; maturity horizontal = max; maturity vertical = mean (na excluded, absent = 0)
- Config status: FROZEN v2.0 2026-10-05

## Clause level (one row per unit x control pair)

| Clause | Unit | Control | Source | Status | Rel | Cov | Str | Dir | Alignment | Realization |
|---|---|---|---|---|---|---|---|---|---|---|
| PDPA-s10 | s10-u1 | ac-3 | explicit_hint | scored | 0.539 | 0.765 | 1.000 | 1.000 | 0.768 | 0.800 |
| PDPA-s10 | s10-u1 | sc-28 | explicit_hint | scored | 0.605 | 0.460 | 1.000 | 1.000 | 0.661 | 0.024 |
| PDPA-s10 | s10-u1 | ac-2 | family_hint | scored | 0.518 | 0.658 | 1.000 | 0.800 | 0.658 | 0.129 |
| PDPA-s10 | s10-u1 | sc-8 | explicit_hint | scored | 0.573 | 0.387 | 1.000 | 1.000 | 0.622 | 0.000 |
| PDPA-s10 | s10-u1 | sc-13 | explicit_hint | scored | 0.567 | 0.319 | 1.000 | 1.000 | 0.592 | 0.000 |
| PDPA-s12 | s12-u1 | pm-18 | explicit_hint | scored | 0.563 | 0.473 | 1.000 | 1.000 | 0.654 | 0.053 |
| PDPA-s12 | s12-u1 | pm-19 | explicit_hint | scored | 0.521 | 0.400 | 1.000 | 1.000 | 0.612 | 0.000 |
| PDPA-s22 | s22-u1 | sa-9 | explicit_hint | scored | 0.409 | 0.542 | 1.000 | 1.000 | 0.638 | 0.000 |
| PDPA-s22 | s22-u2 | sa-9 | explicit_hint | scored | 0.506 | 0.699 | 1.000 | 1.000 | 0.731 | 0.000 |
| PDPA-s22 | s22-u3 | sa-9 | explicit_hint | scored | 0.471 | 1.000 | 1.000 | 1.000 | 0.845 | 0.000 |
| PDPA-s22 | s22-u4 | sa-9 | explicit_hint | scored | 0.329 | 0.299 | 1.000 | 1.000 | 0.514 | 0.000 |
| PDPA-s23 | s23-u1 | ir-8.1 | explicit_hint | scored | 0.660 | 0.502 | 1.000 | 1.000 | 0.695 | 0.000 |
| PDPA-s23 | s23-u1 | ir-6 | explicit_hint | scored | 0.510 | 0.450 | 1.000 | 1.000 | 0.629 | 0.100 |
| PDPA-s23 | s23-u1 | ir-8 | family_hint | scored | 0.384 | 0.234 | 1.000 | 1.000 | 0.503 | 0.100 |
| PDPA-s24 | s24-u1 | ra-8 | explicit_hint | scored | 0.676 | 0.400 | 1.000 | 1.000 | 0.658 | 0.000 |
| PDPA-s24 | s24-u2 | ra-8 | explicit_hint | scored | 0.357 | 0.000 | 1.000 | 1.000 | 0.399 | 0.000 |
| PDPA-s24 | s24-u3 | ra-8 | explicit_hint | scored | 0.335 | 0.000 | 1.000 | 1.000 | 0.393 | 0.000 |
| PDPA-s24 | s24-u4 | ra-8 | explicit_hint | scored | 0.336 | 0.000 | 1.000 | 1.000 | 0.393 | 0.000 |
| PDPA-s5 | s5-u1 | pt-2 | explicit_hint | scored | 0.504 | 0.000 | - | 1.000 | 0.442 | 0.000 |
| PDPA-s5 | s5-u1 | pt-3 | family_hint | scored | 0.446 | 0.000 | - | 1.000 | 0.425 | 0.000 |
| PDPA-s5 | s5-u2 | pt-3 | family_hint | scored | 0.587 | 0.000 | - | 1.000 | 0.467 | 0.000 |
| PDPA-s5 | s5-u2 | pt-2 | explicit_hint | scored | 0.580 | 0.000 | - | 1.000 | 0.465 | 0.000 |
| PDPA-s5 | s5-u3 | pt-4 | explicit_hint | scored | 0.571 | 0.000 | - | 1.000 | 0.462 | 0.000 |
| PDPA-s5 | s5-u3 | pt-2 | family_hint | scored | 0.455 | 0.000 | - | 1.000 | 0.428 | 0.000 |
| PDPA-s5 | s5-u3 | pt-3 | family_hint | scored | 0.402 | 0.033 | - | 1.000 | 0.426 | 0.000 |
| PDPA-s5 | s5-u3 | pt-5 | explicit_hint | scored | 0.418 | 0.000 | - | 1.000 | 0.417 | 0.000 |
| PDPA-s6 | s6-u1 | pt-3 | explicit_hint | scored | 0.773 | 0.765 | 1.000 | 1.000 | 0.837 | 0.000 |
| PDPA-s6 | s6-u1 | pt-2 | family_hint | scored | 0.635 | 0.186 | 1.000 | 1.000 | 0.557 | 0.000 |
| PDPA-s7 | s7-u1 | pm-25 | explicit_hint | scored | 0.535 | 0.481 | 1.000 | 0.700 | 0.561 | 0.000 |
| PDPA-s7 | s7-u1 | pm-18 | family_hint | scored | 0.448 | 0.046 | 1.000 | 0.700 | 0.357 | 0.053 |
| PDPA-s8 | s8-u1 | si-18 | explicit_hint | scored | 0.632 | 0.642 | 1.000 | 1.000 | 0.744 | 0.298 |
| PDPA-s8 | s8-u1 | si-12 | family_hint | scored | 0.455 | 0.324 | 1.000 | 1.000 | 0.561 | 0.000 |
| PDPA-s8 | s8-u2 | si-18 | explicit_hint | scored | 0.666 | 0.500 | 1.000 | 1.000 | 0.696 | 0.298 |
| PDPA-s8 | s8-u2 | si-12 | family_hint | scored | 0.375 | 0.149 | 1.000 | 1.000 | 0.466 | 0.000 |
| PDPA-s9 | s9-u1 | si-12 | explicit_hint | scored | 0.528 | 0.563 | 1.000 | 1.000 | 0.681 | 0.000 |
| PDPA-s9 | s9-u1 | si-18 | family_hint | scored | 0.538 | 0.500 | 1.000 | 1.000 | 0.658 | 0.298 |
| PDPA-s9 | s9-u1 | si-12.1 | explicit_hint | scored | 0.583 | 0.389 | 1.000 | 1.000 | 0.626 | 0.000 |

- Unanchored units (no control hint): ['s5-u4', 's6-u2', 's9-u2', 's24-t1', 's24-t2', 's24-t3', 's26-u1', 's26-u2', 's26-u3', 's26-u4']
- Not-scored units: [('s22-u5', 'Represented but NOT scored: a conditional legal status-change trigger, not a data-handling or documentation obligation. None of SSS/CACR/CRS/CIMS/OIAS is designed to detect this. Flagged as open in clause_selection.md; whether the parameter set gains a treatment for reclassification triggers is an open decision.')]
- Dropped hints: none

Applicability flags raised:
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
| ac-3 | 0.800 | 1 | implemented:1 |
| ir-6 | 0.100 | 2 | inherited:2 |
| ir-8 | 0.100 | 14 | inherited:14 |
| ir-8.1 | 0.000 | 3 | absent:3 |
| pm-18 | 0.053 | 7 | inherited:7 |
| pm-19 | 0.000 | 1 | absent:1 |
| pm-25 | 0.000 | 4 | absent:4 |
| pt-2 | 0.000 | 2 | inherited:2 |
| pt-3 | 0.000 | 4 | inherited:4 |
| pt-4 | 0.000 | 1 | absent:1 |
| pt-5 | 0.000 | 5 | absent:5 |
| ra-8 | 0.000 | 3 | inherited:3 |
| sa-9 | 0.000 | 3 | inherited:3 |
| sc-13 | 0.000 | 2 | absent:2 |
| sc-28 | 0.024 | 1 | implemented:1 |
| sc-8 | 0.000 | 1 | implemented:1 |
| si-12 | 0.000 | 1 | implemented:1 |
| si-12.1 | 0.000 | 1 | absent:1 |
| si-18 | 0.298 | 2 | inherited:2 |
