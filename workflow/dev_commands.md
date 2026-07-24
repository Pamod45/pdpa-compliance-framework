# PCEF dev commands (personal quick-reference)

## Every session - activate first
```
cd C:\Users\pubup\Desktop\Degree\Dissertation\pdpa-compliance-framework
.\.venv\Scripts\Activate.ps1
```
# prompt should show (.venv). If not, DON'T pip install - you'd hit global Python.

## One-time / after dependency changes
```
pip install -e .          # only needed again if pyproject deps change
pip install pytest
```
## Tests
```
pytest                    # all
pytest -v                 # verbose
pytest -k dangling        # only tests matching "dangling"
pytest tests/test_clause_profile.py::test_bad_modality_rejected   # one exact test
```
## Quick manual load check (no test)
```
python -c "from pcef.models import PDPAProfileSet; p = PDPAProfileSet.from_json_file(r'..\pdpa-compliance-dissertation\Artefact\data\symbolized\pdpa_clause_profiles.json'); print('OK', len(p.clauses), len(p.definitions))"
```
## Sync canonical JSON -> framework copy (option a: dissertation is canonical)
```
Copy-Item ..\pdpa-compliance-dissertation\Artefact\data\symbolized\pdpa_clause_profiles.json .\data\symbolized\pdpa_clause_profiles.json
```
## Exit the env
```
deactivate
```