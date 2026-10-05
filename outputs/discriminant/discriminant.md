# Discriminant test results

- Config: FROZEN | sha256 e173213d57f3
- Embedder: sentence-transformers/all-mpnet-base-v2 @ e8c3b32edf5434bc2275fc9bab85f82640a19130
- Controls compared: 17 (FleetTrack SSP controls)

## Verdicts (criteria fixed in DISCRIMINANT_PROTOCOL.md before scoring)

| Hypothesis | Criterion | Result |
|---|---|---|
| H1 aligned degradation | strong > partial > broken (mean Realization) | **PASS** (0.357 > 0.161 > 0.076) |
| H2 Alignment independence | all pair Alignments identical (<= 1e-06) | **PASS** (same pairs: True, max diff 0.00e+00) |
| H3 padding resistance | vague_padded <= partial | **FAIL** (0.340 vs 0.161) |
| H4 wrong-mechanism detection | swapped <= partial | **FAIL** (0.320 vs 0.161) |

Per-control order violations for H1 (reported, not pass/fail): ['ir-8']

## Mean Realization

| Variant | Mean |
|---|---|
| strong | 0.357 |
| partial | 0.161 |
| broken | 0.076 |
| vague_padded | 0.340 |
| swapped | 0.320 |

## Realization per control

| Control | strong | partial | broken | vague_padded | swapped |
|---|---|---|---|---|---|
| ac-2 | 0.129 | 0.062 | 0.019 | 0.124 | 0.122 |
| ac-3 | 0.900 | 0.600 | 0.338 | 0.800 | 0.855 |
| au-2 | 0.450 | 0.300 | 0.000 | 0.400 | 0.370 |
| au-6 | 0.268 | 0.000 | 0.000 | 0.355 | 0.450 |
| ia-2 | 0.818 | 0.412 | 0.338 | 0.800 | 0.900 |
| ia-5 | 0.420 | 0.240 | 0.000 | 0.400 | 0.450 |
| ir-6 | 0.100 | 0.000 | 0.000 | 0.100 | 0.100 |
| ir-8 | 0.100 | 0.049 | 0.064 | 0.100 | 0.100 |
| pm-18 | 0.100 | 0.049 | 0.000 | 0.100 | 0.100 |
| pt-2 | 0.450 | 0.000 | 0.000 | 0.400 | 0.400 |
| pt-3 | 0.400 | 0.285 | 0.169 | 0.400 | 0.214 |
| ra-8 | 0.100 | 0.049 | 0.000 | 0.100 | 0.100 |
| sa-9 | 0.094 | 0.000 | 0.000 | 0.100 | 0.100 |
| sc-28 | 0.200 | 0.200 | 0.200 | 0.200 | 0.200 |
| sc-8 | 0.200 | 0.200 | 0.000 | 0.200 | 0.200 |
| si-12 | 0.900 | 0.000 | 0.000 | 0.800 | 0.600 |
| si-18 | 0.450 | 0.292 | 0.169 | 0.400 | 0.176 |
