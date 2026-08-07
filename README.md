# PCEF - Parametric PDPA Compliance Evaluation Framework

Evaluates OSCAL-formatted security controls against symbolized PDPA clauses.
Python package under `src/pcef`, installed editable, tested with pytest.

## Requirements
- Python ≥ 3.10 (developed on 3.14)
- The sibling repo `pdpa-compliance-dissertation` cloned alongside this one
  (tests read a framework-local copy of the symbolized profiles; the canonical
  source is the dissertation repo — see `decisions.md`).

## First-time setup
From the framework root (`pdpa-compliance-framework/`):

**macOS / Linux**
```bash
python3 -m venv .venv                # create the environment (once)
source .venv/bin/activate            # activate
pip install -e .                     # install pcef editable + its deps (pydantic)
pip install pytest                   # dev-only test runner
```

**Windows (PowerShell)**
```powershell
python -m venv .venv                 # create the environment (once)
.\.venv\Scripts\Activate.ps1         # activate
pip install -e .                     # install pcef editable + its deps (pydantic)
pip install pytest                   # dev-only test runner
```

If PowerShell blocks activation ("running scripts is disabled"), run once in that
window: `Set-ExecutionPolicy -Scope Process RemoteSigned`, then re-activate.

Your prompt should show `(.venv)` once active. If it doesn't, stop — don't
`pip install`, or you'll hit the system Python. Confirm with:

```bash
which python3        # macOS/Linux  -> .../pdpa-compliance-framework/.venv/bin/python3
where.exe python     # Windows      -> ...\pdpa-compliance-framework\.venv\Scripts\python.exe
```

Re-run `pip install -e .` if a new subpackage appears under `src/pcef/` and the
import fails — a strict editable install won't see a directory that didn't exist
at install time.

## Run the tests
```bash
pytest              # run all tests
pytest -v           # verbose: one line per test
pytest -k parsers   # only the Stage 2 parser suite
```
Expected: all tests green — good data loads, malformed data is rejected, and the
catalog/SSP/fuse counts match values derived independently from the raw OSCAL.

Run from the repo root. The `pcef` import resolves from the editable install and
works anywhere, but the test data paths are relative to the root.

## Layout
```
src/pcef/            the package
  models/            schema contracts (ClauseProfile locked; NormalizedControl draft)
  parsers/           Stage 2: catalog loader, SSP loader, A3 fuse -> NormalizedControl
data/                build/test data inputs (symbolized profiles, catalogs, SSPs)
tests/               pytest suite (clause contracts + Stage 2 parsers)
workflow/            dev command reference
pyproject.toml       package definition + pytest config
```

See `workflow/dev_commands.md` for the full command reference, including the
manual load checks and the canonical-JSON sync step.