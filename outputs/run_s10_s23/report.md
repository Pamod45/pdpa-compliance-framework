# PCEF run report

- Run at (UTC): 2026-10-05T07:09:56+00:00
- Embedder: sentence-transformers/all-mpnet-base-v2 @ e8c3b32edf5434bc2275fc9bab85f82640a19130
- Clauses: PDPA-s10, PDPA-s23 | SSP: FleetTrack
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
| PDPA-s23 | s23-u1 | ir-8.1 | explicit_hint | scored | 0.676 | 0.667 | 1.000 | 1.000 | 0.802 | 0.000 |
| PDPA-s23 | s23-u1 | ir-6 | explicit_hint | scored | 0.550 | 0.333 | 1.000 | 1.000 | 0.654 | 0.250 |
| PDPA-s23 | s23-u1 | ir-8 | family_hint | scored | 0.454 | 0.333 | 1.000 | 1.000 | 0.630 | 0.109 |

Applicability flags raised:
- actor_assumed: SSP does not declare a PDPA role; assumed 'controller'
- prospective: duty fires on event (personal data breach has occurred); assessed as readiness

## Control level (Realization is a control property)

| Control | Realization | Rows counted | Row statuses |
|---|---|---|---|
| ac-2 | 0.129 | 18 | absent:15, implemented:3 |
| ac-3 | 0.900 | 1 | implemented:1 |
| ir-6 | 0.250 | 2 | inherited:2 |
| ir-8 | 0.109 | 14 | inherited:14 |
| ir-8.1 | 0.000 | 3 | absent:3 |
| sc-13 | 0.000 | 2 | absent:2 |
| sc-28 | 0.600 | 1 | implemented:1 |
| sc-8 | 0.600 | 1 | implemented:1 |
