# LLM baseline analysis (descriptive - the LLMs are a contrast case, not an oracle)

**R1 PCEF reproducibility:** 5 runs -> IDENTICAL (digest c614f88168eb)

## R2 LLM run-to-run variance

| Provider | Condition | Served model(s) | Calls | Failed | Temp rejected | Pairs complete | Identical across runs | Mean SD align | Mean SD real | Max range align | Max range real |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chatgpt | chat_default | ChatGPT 5.6 Sol (medium) | 111 | 0 | 0 | 37 | 1 (2.7%) | 0.0409 | 0.0589 | 0.35 | 0.7 |
| claude | chat_default | Claude Opus 5.5 (medium) | 111 | 0 | 0 | 37 | 3 (8.1%) | 0.0257 | 0.0175 | 0.15 | 0.15 |
| gemini | chat_default | Gemini 3.1 Pro | 111 | 0 | 0 | 37 | 1 (2.7%) | 0.0645 | 0.0621 | 0.4 | 1.0 |

## T1 Triangulation: Spearman rank correlation with PCEF (medians of runs; no threshold)

| Provider | Condition | rho Alignment | rho Realization |
|---|---|---|---|
| chatgpt | chat_default | 0.581 | 0.882 |
| claude | chat_default | 0.498 | 0.884 |
| gemini | chat_default | 0.559 | 0.741 |

## C1 Construct separation: same control, same run, different clause -> same Realization?

PCEF: identical by design (Realization never reads the clause).

| Provider/condition | run x control groups | inconsistent | examples |
|---|---|---|---|
| chatgpt/chat_default | 21 | 5 | {'run2:pt-2': [0.9, 0.2, 0.15, 0.25], 'run2:pt-3': [0.35, 0.1, 0.1, 0.5], 'run2:pm-18': [0.05, 0.0]} |
| claude/chat_default | 21 | 2 | {'run2:ra-8': [0.05, 0.0, 0.0, 0.0], 'run3:ra-8': [0.05, 0.0, 0.0, 0.0]} |
| gemini/chat_default | 21 | 12 | {'run1:pt-2': [1.0, 0.6, 0.3, 1.0], 'run2:pt-2': [0.9, 0.2, 0.0, 0.2], 'run3:pt-2': [0.9, 0.3, 0.0, 0.0]} |

## LLM-to-LLM agreement (Spearman of medians) - compare with each LLM vs PCEF above

| A | B | rho Alignment | rho Realization |
|---|---|---|---|
| chatgpt/chat_default | claude/chat_default | 0.936 | 0.956 |
| chatgpt/chat_default | gemini/chat_default | 0.95 | 0.819 |
| claude/chat_default | gemini/chat_default | 0.892 | 0.811 |

## Panel shortlist - largest alignment disagreements (PCEF vs mean of LLM medians)

| Pair | PCEF | LLM mean | abs diff |
|---|---|---|---|
| s5-u1|pt-2 | 0.442 | 0.9 | 0.458 |
| s8-u1|si-12 | 0.561 | 0.117 | 0.445 |
| s9-u1|si-18 | 0.658 | 0.217 | 0.441 |
| s9-u1|si-12.1 | 0.626 | 0.25 | 0.376 |
| s22-u2|sa-9 | 0.731 | 0.367 | 0.364 |
| s5-u2|pt-3 | 0.467 | 0.133 | 0.333 |
| s24-u4|ra-8 | 0.393 | 0.06 | 0.333 |
| s5-u3|pt-4 | 0.462 | 0.783 | 0.321 |

## Panel shortlist - largest realization disagreements (PCEF vs mean of LLM medians)

| Pair | PCEF | LLM mean | abs diff |
|---|---|---|---|
| s10-u1|ac-2 | 0.129 | 0.6 | 0.471 |
| s8-u2|si-12 | 0.9 | 0.433 | 0.467 |
| s8-u1|si-12 | 0.9 | 0.433 | 0.467 |
| s5-u1|pt-2 | 0.45 | 0.817 | 0.367 |
| s9-u1|si-12 | 0.9 | 0.633 | 0.267 |
| s10-u1|sc-8 | 0.2 | 0.0 | 0.2 |
| s10-u1|sc-28 | 0.2 | 0.0 | 0.2 |
| s5-u2|pt-2 | 0.45 | 0.583 | 0.133 |
