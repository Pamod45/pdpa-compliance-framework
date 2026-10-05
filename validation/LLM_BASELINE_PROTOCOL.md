# LLM baseline protocol (written 2026-10-05, BEFORE any LLM call)

Framing (decisions.md 2026-07-06): the LLMs are a **contrast case, not an oracle**. No claim that PCEF is more
*correct*; there is no ground truth for that. The comparison shows reproducibility, explainability and
triangulation only.

## Setup
- **Scorer of record:** PCEF config FROZEN v1.1, FleetTrack (strong) - the 37 scored pairs of the method-of-record run.
- **LLMs:** 3 hosted models from 3 different providers (Anthropic, OpenAI, Google). Exact model ids are passed on the
  command line and both the requested and the SERVED model id are recorded per call.
- **Conditions:** `temp0` (temperature 0 - the hardest test of LLM variance) and `default` (provider default - how
  people actually use them). If a provider rejects temperature 0, that is recorded and that cell is reported as n/a;
  nothing silently falls back.
- **Runs:** N = 5 per pair, per model, per condition -> 37 x 5 x 3 x 2 = 1,110 calls.
- **Information parity:** each prompt gives the clause's verbatim text, the unit's obligation (action + object) and
  its attributes, the control's catalog text (with parent stems), and FleetTrack's implementation text for that
  control incl. statement remarks - the same inputs PCEF reads. Template, system message and version are fixed and
  hashed (`llm-baseline-prompt v1`).
- **Output asked:** JSON with alignment (0-1, catalog vs obligation on paper), realization (0-1, implementation text
  only), rationale (<= 3 sentences). Parse failures are recorded, not retried.

## Measures (all descriptive; no pass/fail threshold except R1)
- **R1 PCEF reproducibility:** PCEF re-run 5x on the same input -> scores byte-identical. *Prediction: IDENTICAL.*
- **R2 LLM variance:** per provider x condition - % of pairs identical across all 5 runs, mean SD and max range per
  axis, failure rate, temperature rejections. *Prediction: temp0 more stable than default; at least one model not
  100% identical even at temp0.*
- **T1 Triangulation:** Spearman rho between PCEF and each LLM's per-pair median, per axis. Reported, no threshold.
  Agreement = weak triangulated support only.
- **Panel shortlist:** the 8 largest PCEF-vs-LLM disagreements per axis go to the expert panel to adjudicate.
- **E1 Explainability:** qualitative - PCEF gives per-measure provenance (run.json); the LLM gives a free-text rationale.

## AMENDMENT 2026-10-05 (before ANY data was collected): chat apps instead of APIs
The author chose not to use APIs. The baseline now uses the **chat apps** of the same three providers.
- **Design:** 37 pairs in **2 fixed batches** (same content and order every time) x **3 runs** x **3 apps = 18 chats**.
  Prompts: `validation/llm_chat_prompts.py` (hashed in manifest.json). Replies pasted verbatim, parsed by
  `validation/llm_chat_parse.py`; nothing is typed by hand; missing/unparseable pairs are recorded as failures.
- **Rules per chat:** new chat every run; temporary/incognito chat or memory OFF; no custom instructions; all runs of
  one app on the same day; record the model name shown and the date in chat_log.csv.
- **Dropped:** the temp0 condition (chat apps expose no temperature control). Only `chat_default` remains.
- **New limitations:** (1) pairs are scored together in one conversation (possible cross-pair influence; PCEF scores
  pairs independently); (2) hidden chat-app system prompts and possible silent model updates; (3) served model is
  what the app displays, not an API-reported id; (4) N = 3 runs gives a coarse variance estimate.
- R1, R2 (now chat_default only), T1, shortlist and E1 are otherwise unchanged.
