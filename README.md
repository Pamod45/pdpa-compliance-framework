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
The app runs the same frozen v1.1 scorer as the command line. Its scores are never different
from a pipeline run on the same inputs. A public instance runs at https://www.pcef.help.

| Page | What it does |
|---|---|
| Home | What PCEF does, with buttons to score the sample or upload a plan |
| Explore an SSP | Score the FleetTrack sample or an uploaded OSCAL SSP; overview, clause-to-controls, gaps, controls and map views; open any pair to trace its scores; printable report, CSV and JSON |
| How scoring works | Follows one duty (s.10) with two controls (AC-3 and SC-28) through all seven stages, using values from a live run |
| Learn the basics | Short explanations of the PDPA, NIST SP 800-53, SSPs and OSCAL, with an annotated SSP and the sample to download |
| My runs | For signed-in users: saved runs to reopen, rename, delete, compare two at a time, or print |
| Expert panel | The fixed panel pack used in the evaluation (admins only when admins are configured) |
| Admin | Accounts, saved runs and storage (admins only) |
| Privacy | What is stored, why and for how long |
| Draft an SSP (beta) | An LLM drafts an OSCAL SSP from a prose document; the draft is checked against the catalog and the SSP parser |

The sidebar also offers a guided tour of a sample run and a presenter mode with larger text for
demonstrations (`?present` in the URL turns it on). The overview headline shows how many duties are
covered and built, and the average Alignment and Realization over duties with a scored control.
These are two separate averages, never combined into one score, and are not a compliance rating.

The prebuilt frontend in `app/static/` is served directly, so Node is not needed. To rebuild it
from `app/frontend/`, run `npm install` and `npm run build` in that folder.

### Accounts and saved runs
Signing in is optional. Accounts use email and password; passwords are stored only as argon2id
hashes, and sessions keep only a SHA-256 of the browser's token. Runs scored while signed in are
saved by the server, so a saved result is always one the scorer produced. Saved runs quote the
plan's implementation text, so confidential plans are better scored without signing in. Users can
download everything stored about them as JSON, or delete their account with all its runs.

### Settings
All are optional environment variables; the defaults suit a local run.

| Variable | Default | Meaning |
|---|---|---|
| `HOST`, `PORT` | `127.0.0.1`, `8000` | Address and port to listen on |
| `PCEF_EMBEDDER` | `sbert` | `sbert` for real results, `tfidf` for the offline stand-in |
| `PCEF_MODEL_REVISION` | none | Pin the embedding model to an exact revision |
| `PCEF_OPEN_BROWSER` | `1` | `0` stops the browser opening on start-up |
| `PCEF_WARM_SAMPLE` | `1` | `0` skips scoring the sample in the background on start-up |
| `PCEF_MAX_UPLOAD_MB` | `5` | Largest SSP upload accepted |
| `PCEF_DATA_DIR` | not set | Folder for panel responses and the account database; when not set, responses go to `outputs/panel` and the database to `instance/` |
| `PCEF_DB` | `<PCEF_DATA_DIR>/pcef.sqlite3`, else `instance/pcef.sqlite3` | Account database file |
| `PCEF_RETENTION_DAYS` | `365` | Days a saved run is kept; `0` keeps runs until the user deletes them |
| `PCEF_ADMIN_EMAILS` | none | Comma-separated admin emails; when set, the expert panel is for admins only |
| `PCEF_PANEL_WRITES` | `1` | `0` stops accepting panel responses |
| `GEMINI_API_KEY` | none | Enables *Draft an SSP*; without it the page says drafting is not set up |
| `PCEF_LLM_MODEL` | `gemini-flash-latest` | Gemini model for drafting; the exact version used is recorded with each draft |
| `PCEF_LLM_DAILY_LIMIT` | `20` | Drafting calls allowed per day for the whole site |

When `PCEF_DATA_DIR` is not set, the account database is created in `instance/`, which is ignored
by git. Create an admin account before adding its email to `PCEF_ADMIN_EMAILS`, because whoever
registers an address first owns it.

### Drafting an SSP with an LLM
*Draft an SSP* sends a prose description of a system to the Gemini API and turns the answer into an
OSCAL SSP. The model may use only a fixed list of controls; anything else is dropped with a warning,
and the result must pass PCEF's SSP parser. The LLM never produces scores. On the public instance it
runs on Gemini's free tier, where Google may use and review what is sent, so the public can draft
only the built-in sample document and only admins can draft their own text. Sample drafts are stored
after the first call, so repeat visits do not use the quota.

Before scoring, the draft is shown for review: each statement can be corrected, marked as a known gap
or removed, and the PDPA role can be set. A scored draft carries a label with the model version, the
source document and the number of changes, shown in the results and the printed report. For the
sample, the draft's headline is shown next to the hand-written FleetTrack plan's.

### Deployment
The `Dockerfile` builds a CPU-only image with the embedding model downloaded at the pinned
revision, so the container runs offline. The public instance is deployed from this repository:

- at least 2 GB of memory, since the model and PyTorch need well over 1 GB;
- a persistent volume mounted at `/data`, with `PCEF_DATA_DIR=/data`, so accounts and saved
  runs survive redeploys;
- `PCEF_ADMIN_EMAILS` set to the site owner's address.

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
app/                 web app: FastAPI backend (server, accounts, saved runs, admin),
                     React frontend and the prebuilt static bundle
validation/          protocols and evaluation scripts
data/                inputs: symbolized profiles, NIST catalog, SSPs and degraded variants
outputs/             run results and evaluation evidence
tests/               pytest suite
```
