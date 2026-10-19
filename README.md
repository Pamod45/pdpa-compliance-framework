# PCEF - Parametric PDPA Compliance Evaluation Framework

PCEF evaluates how well the security controls described in an OSCAL System Security Plan
(SSP) support the obligations of Sri Lanka's Personal Data Protection Act No. 9 of 2022.
Each PDPA obligation unit is paired with NIST SP 800-53 Rev 5 controls and scored on two
separate axes:

- **Alignment** - how well the control, as written in the catalog, addresses the obligation
  (Coverage, Relatedness, Directionality and Strength Match). It never reads the SSP.
- **Realization** - how fully and specifically the SSP describes implementing the control
  (Maturity). It never reads the clause.

Every score is deterministic and traceable to the inputs, the frozen configuration and the
embedding model revision recorded in each run.

## Requirements
- Python 3.10 or later (tested on 3.12)
- For real results: `sentence-transformers` (installed with the `sbert` extra below)
- For the web app: the packages in `requirements-app.txt`

The symbolized PDPA clause profiles in `data/symbolized/` are a copy of the set maintained
in the companion dissertation repository.

## First-time setup
From the repository root:

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install pytest
```

If PowerShell blocks activation ("running scripts is disabled"), run
`Set-ExecutionPolicy -Scope Process RemoteSigned` in that window, then activate again.

Re-run `pip install -e .` if a new subpackage appears under `src/pcef/` and the import
fails; an editable install does not see a directory that did not exist at install time.

## Run the tests
```bash
pytest              # all tests
pytest -v           # one line per test
pytest -k parsers   # only the Stage 2 parser suite
```
Run from the repository root; test data paths are relative to it. The pipeline tests use
the TF-IDF stand-in embedder, so no model download is needed. The web app tests are
skipped unless the packages in `requirements-app.txt` are installed.

## Running the pipeline (stages 3-7)
```bash
pip install -e ".[sbert]"     # adds sentence-transformers and PyTorch
python -m pcef.pipeline.run --clauses PDPA-s10 PDPA-s23 --embedder sbert --out outputs/run_s10_s23
python -m pcef.pipeline.run --all --embedder sbert --out outputs/run_full
python -m pcef.pipeline.run --all --embedder sbert --ssp path/to/other_ssp.json --out outputs/other
```
Each run writes `run.json` (full results with provenance) and `report.md` (summary tables).
Parameters are read from `config/`. `--embedder tfidf` is a stand-in for tests and offline
checks; its scores are not results.

## Web app
```bash
pip install -r requirements-app.txt
python -m app.server            # opens http://127.0.0.1:8000
```
Run the pipeline on the sample FleetTrack SSP or an uploaded OSCAL SSP, browse the results
by clause, control and gap, and trace any score back to its inputs. The prebuilt frontend in
`app/static/` is served directly, so Node is not needed. To rebuild it from
`app/frontend/`, run `npm install` and `npm run build` in that folder.

## Validation and evidence
The scripts in `validation/` reproduce the evaluation. Results are kept in `outputs/`.

| Folder | What it holds |
|---|---|
| `run_method_of_record_v1_1/` | Method-of-record run (v1.1, 37 FleetTrack pairs) and the non-redundancy check (maximum \|r\| = 0.437) |
| `discriminant/`, `discriminant_v1_1/` | Discriminant test on degraded SSP variants (H1-H4), on v1.0 and v1.1 |
| `discriminant_v2/`, `discriminant_v3/` | DSR iterations 2 and 3 (H5 not met; v1.1 retained) |
| `llm_chat/` | LLM baseline: prompts, verbatim replies, chat log, parsed calls and analysis |
| `panel/` | Expert-panel pack (14 pairs) and anonymised responses (E001-E003) |
| `ch5/` | Reproducibility runs: FleetTrack x3 and the NIST example SSP x2 |
| `run_full*/`, `run_s10_s23/`, `run_nist_example/`, `floor_check/`, `relatedness_*/` | Pre-freeze calibration runs, kept for transparency; not evaluation evidence |

Each pre-registered protocol (`validation/*_PROTOCOL*.md`) was committed before the results
it governs.

```bash
python validation/redundancy.py outputs/run_method_of_record_v1_1/run.json
python validation/degrade_ssp.py --set v1
python validation/discriminant.py --embedder sbert
python validation/discriminant.py --embedder sbert --set v3 --config config_v3 --out outputs/discriminant_v3
python validation/llm_chat_parse.py
python validation/llm_analyse.py --calls outputs/llm_chat/calls.jsonl --out outputs/llm_chat
python validation/build_panel_pack.py
python validation/ch5_runs.py
```

## Configuration fingerprints
The v1.1 parameter values were frozen on 2026-10-05 (tag `method-of-record-2026-10-05`).
On 2026-10-19 descriptive comment fields (keys starting with `_`) in `config/`, `config_v2/`
and `config_v3/` were shortened. No parameter value changed. Runs recorded before that date
carry the earlier fingerprints; the reproducibility runs in `outputs/ch5/` were repeated on
the current files and every score is identical.

| File | Earlier fingerprint | Current fingerprint |
|---|---|---|
| `config/pcef_params.json` | `debb78cfde93` | `f058aa26ce7d` |
| `config_v2/pcef_params.json` | `1cfb59e69746` | `bdc96b40c2cb` |
| `config_v3/pcef_params.json` | `313e9baa5734` | `d75188e9aefa` |
| `directionality_table.json` (all three) | `f8fc636288ca` | `d92f281c87f1` |

The v1.0 configuration (`e173213d57f3`) and the pre-freeze draft configurations were
superseded on 2026-10-05 and are not retained; their runs record the fingerprints used.

## Layout
```
src/pcef/            the package
  models/            schema contracts
  parsers/           Stage 2: catalog loader, SSP loader, fuse -> NormalizedControl
  pipeline/          Stages 3-7: pairing, gates, measures, aggregation, report
config/              frozen method-of-record parameters (v1.1)
config_v2/, config_v3/  DSR iteration configurations
app/                 web app: FastAPI backend, React frontend, prebuilt static bundle
validation/          protocols and evaluation scripts
data/                inputs: symbolized profiles, NIST catalog, SSPs and degraded variants
outputs/             run results and evaluation evidence
tests/               pytest suite
```
