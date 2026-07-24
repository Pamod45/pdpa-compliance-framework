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

```powershell
python -m venv .venv                 # create the environment (once)
.\.venv\Scripts\Activate.ps1         # activate (PowerShell)
pip install -e .                     # install pcef editable + its deps (pydantic)
pip install pytest                   # dev-only test runner
```

If PowerShell blocks activation ("running scripts is disabled"), run once in that
window: `Set-ExecutionPolicy -Scope Process RemoteSigned`, then re-activate.

## Run the tests
```powershell
pytest              # run all tests
pytest -v           # verbose: one line per test
```
Expected: all tests green — good data loads, malformed data is rejected.

## Layout
```
src/pcef/            the package
  models/            schema contracts (ClauseProfile locked; NormalizedControl next)
data/                build/test data inputs (symbolized profiles, catalogs, SSPs)
tests/               pytest suite
pyproject.toml       package definition + pytest config
```