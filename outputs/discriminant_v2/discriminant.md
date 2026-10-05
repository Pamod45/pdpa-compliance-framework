# Discriminant test results

- Variant set: v2 | Scorer config: FROZEN v2.0 2026-10-05 (sha256 1cfb59e69746) | relevance check: ON
- Embedder: sentence-transformers/all-mpnet-base-v2 @ e8c3b32edf5434bc2275fc9bab85f82640a19130
- Controls compared: 17 (FleetTrack SSP controls)

## Verdicts (criteria fixed in the protocol before scoring)

| Hypothesis | Criterion | Result |
|---|---|---|
| H1 aligned degradation | strong > partial > broken | **PASS** (0.157 > 0.094 > 0.002) |
| H2 Alignment independence | identical (<= 1e-06) | **PASS** (same pairs: True, max diff 0.00e+00) |
| H3 padding resistance | vague_padded <= partial | **FAIL** (0.131 vs 0.094) |
| H4 wrong-mechanism detection | swapped <= partial | **PASS** (0.054 vs 0.094) |
| H5 genuine text kept | strong(this) >= 80% of strong(baseline) | **FAIL** (0.157 vs 80% x 0.357 = 0.286) |

Per-control order violations for H1 (reported, not pass/fail): ['au-2', 'ia-5', 'si-18']

## Mean Realization

| Variant | Mean |
|---|---|
| strong | 0.157 |
| partial | 0.094 |
| broken | 0.002 |
| vague_padded | 0.131 |
| swapped | 0.054 |

## SECONDARY (already-seen variants of the other set, same scorer) - not evidence

| Variant | Mean |
|---|---|
| partial | 0.073 |
| broken | 0.035 |
| vague_padded | 0.250 |
| swapped | 0.029 |

## Realization per control

| Control | strong | partial | broken | vague_padded | swapped |
|---|---|---|---|---|---|
| ac-2 | 0.129 | 0.060 | 0.012 | 0.072 | 0.000 |
| ac-3 | 0.800 | 0.600 | 0.000 | 0.469 | 0.312 |
| au-2 | 0.204 | 0.000 | 0.003 | 0.143 | 0.000 |
| au-6 | 0.242 | 0.211 | 0.000 | 0.294 | 0.108 |
| ia-2 | 0.716 | 0.322 | 0.000 | 0.034 | 0.369 |
| ia-5 | 0.000 | 0.000 | 0.023 | 0.312 | 0.047 |
| ir-6 | 0.100 | 0.100 | 0.000 | 0.097 | 0.000 |
| ir-8 | 0.100 | 0.000 | 0.000 | 0.048 | 0.000 |
| pm-18 | 0.053 | 0.000 | 0.000 | 0.023 | 0.000 |
| pt-2 | 0.000 | 0.000 | 0.000 | 0.180 | 0.000 |
| pt-3 | 0.000 | 0.000 | 0.000 | 0.044 | 0.007 |
| ra-8 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| sa-9 | 0.000 | 0.000 | 0.000 | 0.015 | 0.050 |
| sc-28 | 0.024 | 0.000 | 0.000 | 0.000 | 0.024 |
| sc-8 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| si-12 | 0.000 | 0.000 | 0.000 | 0.462 | 0.000 |
| si-18 | 0.298 | 0.300 | 0.000 | 0.036 | 0.000 |
