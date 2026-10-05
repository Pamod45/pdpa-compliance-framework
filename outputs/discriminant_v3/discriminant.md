# Discriminant test results

- Variant set: v3 | Scorer config: FROZEN v3.0 2026-10-05 (sha256 313e9baa5734) | relevance check: ON
- Embedder: sentence-transformers/all-mpnet-base-v2 @ e8c3b32edf5434bc2275fc9bab85f82640a19130
- Controls compared: 17 (FleetTrack SSP controls)

## Verdicts (criteria fixed in the protocol before scoring)

| Hypothesis | Criterion | Result |
|---|---|---|
| H1 aligned degradation | strong > partial > broken | **PASS** (0.276 > 0.060 > 0.010) |
| H2 Alignment independence | identical (<= 1e-06) | **PASS** (same pairs: True, max diff 0.00e+00) |
| H3 padding resistance | vague_padded <= partial | **PASS** (0.040 vs 0.060) |
| H4 wrong-mechanism detection | swapped <= partial | **FAIL** (0.096 vs 0.060) |
| H5 genuine text kept | strong(this) >= 80% of strong(baseline) | **FAIL** (0.276 vs 80% x 0.357 = 0.286) |

Per-control order violations for H1 (reported, not pass/fail): ['pm-18', 'pt-2']

## Mean Realization

| Variant | Mean |
|---|---|
| strong | 0.276 |
| partial | 0.060 |
| broken | 0.010 |
| vague_padded | 0.040 |
| swapped | 0.096 |

## SECONDARY (already-seen variant sets, same scorer) - not evidence

| Set:variant | Mean |
|---|---|
| v1:broken | 0.013 |
| v1:partial | 0.118 |
| v1:swapped | 0.102 |
| v1:vague_padded | 0.055 |
| v2:broken | 0.008 |
| v2:partial | 0.110 |
| v2:swapped | 0.114 |
| v2:vague_padded | 0.046 |

## Realization per control

| Control | strong | partial | broken | vague_padded | swapped |
|---|---|---|---|---|---|
| ac-2 | 0.129 | 0.065 | 0.012 | 0.096 | 0.010 |
| ac-3 | 0.885 | 0.000 | 0.000 | 0.058 | 0.000 |
| au-2 | 0.450 | 0.300 | 0.000 | 0.000 | 0.061 |
| au-6 | 0.268 | 0.225 | 0.016 | 0.015 | 0.000 |
| ia-2 | 0.784 | 0.000 | 0.000 | 0.000 | 0.401 |
| ia-5 | 0.420 | 0.225 | 0.000 | 0.134 | 0.437 |
| ir-6 | 0.092 | 0.060 | 0.056 | 0.075 | 0.000 |
| ir-8 | 0.100 | 0.000 | 0.000 | 0.079 | 0.000 |
| pm-18 | 0.023 | 0.025 | 0.000 | 0.000 | 0.000 |
| pt-2 | 0.185 | 0.031 | 0.085 | 0.079 | 0.112 |
| pt-3 | 0.152 | 0.000 | 0.000 | 0.099 | 0.000 |
| ra-8 | 0.023 | 0.000 | 0.000 | 0.000 | 0.000 |
| sa-9 | 0.094 | 0.090 | 0.005 | 0.050 | 0.016 |
| sc-28 | 0.200 | 0.000 | 0.000 | 0.000 | 0.200 |
| sc-8 | 0.171 | 0.000 | 0.000 | 0.000 | 0.171 |
| si-12 | 0.262 | 0.000 | 0.000 | 0.000 | 0.000 |
| si-18 | 0.450 | 0.000 | 0.000 | 0.000 | 0.226 |
