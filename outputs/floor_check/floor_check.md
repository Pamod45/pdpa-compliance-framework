# Relatedness floor check

- Embedder: sentence-transformers/all-mpnet-base-v2 @ e8c3b32edf5434bc2275fc9bab85f82640a19130
- Floor in config: 0.2
- Negative controls: pe-13, pe-14, pe-15, ma-2, ma-6

| Set | n | min | p25 | median | p75 | max |
|---|---|---|---|---|---|---|
| Real pairs | 37 | 0.2374 | 0.4544 | 0.5054 | 0.5625 | 0.7808 |
| Unrelated pairs | 95 | 0.0936 | 0.2197 | 0.2854 | 0.3435 | 0.5335 |

- Unrelated pairs at/above floor (would wrongly pass): 77 of 95
- Real pairs below floor (would wrongly be excluded): 0 of 37

## Per unit (sorted by margin; negative margin = an unrelated control beat a real one)

| Unit | Lowest real | Highest unrelated | Margin |
|---|---|---|---|
| s22-u4 | 0.3295 | 0.4235 | -0.094 |
| s24-u3 | 0.2374 | 0.2981 | -0.0608 |
| s24-u4 | 0.3196 | 0.3797 | -0.0601 |
| s22-u3 | 0.4776 | 0.5335 | -0.0559 |
| s22-u1 | 0.3484 | 0.3862 | -0.0378 |
| s10-u1 | 0.4861 | 0.4845 | 0.0017 |
| s8-u2 | 0.4283 | 0.4203 | 0.0081 |
| s8-u1 | 0.368 | 0.3444 | 0.0236 |
| s12-u1 | 0.4722 | 0.4363 | 0.0359 |
| s5-u2 | 0.5054 | 0.4312 | 0.0742 |
| s5-u3 | 0.4327 | 0.3446 | 0.0881 |
| s23-u1 | 0.4544 | 0.3578 | 0.0965 |
| s24-u2 | 0.3975 | 0.2942 | 0.1032 |
| s9-u1 | 0.5191 | 0.3979 | 0.1211 |
| s7-u1 | 0.5422 | 0.3991 | 0.1431 |
| s5-u1 | 0.4724 | 0.3206 | 0.1518 |
| s22-u2 | 0.4894 | 0.3025 | 0.1869 |
| s6-u1 | 0.6602 | 0.3948 | 0.2654 |
| s24-u1 | 0.7014 | 0.2757 | 0.4256 |

## Ten highest unrelated pairs

| Unit | Control | Rel |
|---|---|---|
| s22-u3 | ma-2 | 0.5335 |
| s10-u1 | ma-2 | 0.4845 |
| s10-u1 | pe-13 | 0.479 |
| s12-u1 | ma-2 | 0.4363 |
| s10-u1 | pe-15 | 0.4362 |
| s5-u2 | ma-2 | 0.4312 |
| s10-u1 | pe-14 | 0.428 |
| s22-u4 | ma-2 | 0.4235 |
| s8-u2 | ma-2 | 0.4203 |
| s22-u3 | pe-14 | 0.402 |
