# Non-redundancy check

- Source: `outputs\run_method_of_record_v1_1\run.json` | config FROZEN v1.1 2026-10-05
- Scored pairs: 37 | rule: |r| > 0.85 -> flagged for collapse-or-report review

## Measure spread

| Measure | n | min | max | distinct values |
|---|---|---|---|---|
| relatedness | 37 | 0.329 | 0.773 | 36 |
| coverage | 37 | 0.000 | 1.000 | 27 |
| strength | 29 | 1.000 | 1.000 | 1 |
| directionality | 37 | 0.700 | 1.000 | 3 |
| maturity | 37 | 0.000 | 0.900 | 8 |

## Pairwise Pearson r

| Pair | n | r | Flag |
|---|---|---|---|
| relatedness - coverage | 37 | 0.437 |  |
| relatedness - strength | 29 | undefined | n/a: zero variance (second measure is constant) |
| relatedness - directionality | 37 | 0.041 |  |
| relatedness - maturity | 37 | 0.055 |  |
| coverage - strength | 29 | undefined | n/a: zero variance (second measure is constant) |
| coverage - directionality | 37 | -0.036 |  |
| coverage - maturity | 37 | 0.04 |  |
| strength - directionality | 29 | undefined | n/a: zero variance (first measure is constant) |
| strength - maturity | 29 | undefined | n/a: zero variance (first measure is constant) |
| directionality - maturity | 37 | 0.215 |  |
