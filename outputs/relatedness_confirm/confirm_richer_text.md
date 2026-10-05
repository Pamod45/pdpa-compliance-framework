# Relatedness diagnostic - CONFIRM on held-out set: richer_text

- Negative controls: pe-9, pe-10, pe-12, ma-3, ma-4
- Models: sentence-transformers/all-mpnet-base-v2 @ e8c3b32edf5434bc2275fc9bab85f82640a19130
- Bar: every unit margin > 0 AND unrelated pass rate at tightest safe floor < 20%

| Variant | Meets bar | Units with margin <= 0 | Worst margin | Unrelated pass @ tightest floor | Tightest floor | Pass @ config floor | Median real | Median unrelated |
|---|---|---|---|---|---|---|---|---|
| richer_text | no | 2/19 | -0.0427 | 20% | 0.3287 | 68% | 0.5214 | 0.2442 |

## Margin per unit (negative = an unrelated control beat a real one)

| Unit | richer_text |
|---|---|
| s10-u1 | 0.0895 |
| s12-u1 | 0.1139 |
| s22-u1 | 0.0386 |
| s22-u2 | 0.1528 |
| s22-u3 | 0.0646 |
| s22-u4 | -0.0427 |
| s23-u1 | 0.1831 |
| s24-u1 | 0.3877 |
| s24-u2 | 0.0806 |
| s24-u3 | -0.0268 |
| s24-u4 | 0.0511 |
| s5-u1 | 0.1119 |
| s5-u2 | 0.2314 |
| s5-u3 | 0.0766 |
| s6-u1 | 0.2068 |
| s7-u1 | 0.0528 |
| s8-u1 | 0.1135 |
| s8-u2 | 0.0439 |
| s9-u1 | 0.1865 |
