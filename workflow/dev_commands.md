# PCEF dev commands (personal quick-reference)

Primary environment is **macOS** (Apple Silicon, Homebrew Python 3.14.6, `.venv/bin/`).
Windows/PowerShell equivalents are given alongside each block for the old machine.

Repo roots assumed below:

| | path |
|---|---|
| macOS | `~/Documents/Degree/Project Dissertation/pdpa-compliance-framework` |
| Windows | `C:\Users\pubup\Desktop\Degree\Dissertation\pdpa-compliance-framework` |

Note the parent folders differ between machines (`Documents/Degree/Project Dissertation`
vs `Desktop\Degree\Dissertation`) — check which one you're on before copying a path.

Where a snippet below uses `python3`, Windows uses `python`. Everything else in
those snippets is identical.

---

## Every session - activate first

**macOS / Linux**
```bash
cd "$HOME/Documents/Degree/Project Dissertation/pdpa-compliance-framework"
source .venv/bin/activate
```

**Windows (PowerShell)**
```powershell
cd C:\Users\pubup\Desktop\Degree\Dissertation\pdpa-compliance-framework
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation ("running scripts is disabled"), run once in that
window: `Set-ExecutionPolicy -Scope Process RemoteSigned`, then re-activate.

Prompt should show `(.venv)`. If it doesn't, DON'T `pip install` - you'd hit the
system Python.

Verify you're on the right interpreter:

**macOS / Linux**
```bash
which python3          # -> .../pdpa-compliance-framework/.venv/bin/python3
python3 -V             # -> Python 3.14.6
```

**Windows (PowerShell)**
```powershell
where.exe python       # -> ...\pdpa-compliance-framework\.venv\Scripts\python.exe
python -V
```

---

## One-time / after dependency changes

Identical on both platforms once the venv is active:

```bash
pip install -e .          # needed again if pyproject deps change
pip install pytest
```

Also re-run `pip install -e .` if a **new subpackage** appears under `src/pcef/`
and the import fails - a strict editable install won't see a directory that did
not exist at install time. (`src/pcef/parsers/` was added 2026-08-06.)

If `.venv` is missing entirely, recreate it:

**macOS / Linux**
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e . && pip install pytest
```

**Windows (PowerShell)**
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e .; pip install pytest
```

---

## Tests

Identical on both platforms:

```bash
pytest                    # all
pytest -v                 # verbose
pytest -k parsers         # only the Stage 2 parser suite
pytest -k dangling        # only tests matching "dangling"
pytest tests/test_clause_profile.py::test_bad_modality_rejected   # one exact test
```

---

## Quick manual load checks (no test)

Run from the repo root. The data paths are relative, which is what makes the
working directory matter - the `pcef` import itself resolves from the editable
install and works anywhere.

Clause side - the locked contract:

```bash
python3 -c "
from pcef.models import PDPAProfileSet
p = PDPAProfileSet.from_json_file('../pdpa-compliance-dissertation/Artefact/data/symbolized/pdpa_clause_profiles.json')
print('OK', len(p.clauses), len(p.definitions))
"
```

Control side - Stage 2 parsers:

```bash
python3 -c "
from pcef.parsers import CatalogIndex, SspDocument

ix = CatalogIndex.from_file('data/raw/catalogs/nist_sp800_53_rev5/NIST_SP-800-53_rev5_catalog.json')
print(len(ix), 'controls |', ix.version, '| oscal', ix.oscal_version)
print('au-2 leaves:', [n.smt_id for n in ix['au-2'].leaves])
print('ancestors  :', ix['au-1'].ancestors('au-1_smt.a.1.a'))

d = SspDocument.from_file('data/ssps/fleettrack/fleettrack_ssp.json')
print(d.system_name, '|', len(d.components), 'components |', len(d), 'controls')
print(sum(1 for c in d for s in c.statements.values()
          for b in s.by_components if not b.is_operational), 'non-operational by-components')
"
```

Expected:

```
1196 controls | 5.2.0 | oscal 1.2.2
au-2 leaves: ['au-2_smt.a', 'au-2_smt.b', 'au-2_smt.c', 'au-2_smt.d', 'au-2_smt.e']
ancestors  : ('au-1_smt.a.1', 'au-1_smt.a', 'au-1_smt')
FleetTrack | 10 components | 17 controls
6 non-operational by-components
```

Full A3 fuse output - the status distribution across all 17 FleetTrack controls:

```bash
python3 -c "
import collections
from pcef.parsers import CatalogIndex, SspDocument, normalize_all

ix = CatalogIndex.from_file('data/raw/catalogs/nist_sp800_53_rev5/NIST_SP-800-53_rev5_catalog.json')
d  = SspDocument.from_file('data/ssps/fleettrack/fleettrack_ssp.json')
ctrls, rep = normalize_all(ix, d)
tot = collections.Counter(sp.status for nc in ctrls for sp in nc.sub_parts)
print(dict(tot), '|', sum(len(nc.sub_parts) for nc in ctrls), 'rows | clean:', rep.is_clean)
"
```

Expected: `{'implemented': 8, 'absent': 15, 'inherited': 54} | 77 rows | clean: True`

On Windows, substitute `python` for `python3` in all three snippets. PowerShell
handles the multi-line double-quoted string the same way bash does.

---

## Sync canonical JSON -> framework copy

Dissertation repo is canonical for the symbolized clause profiles
(decisions.md 2026-07-27); the framework copy is a manual mirror, so re-run this
after ANY edit to the canonical file.

**macOS / Linux**
```bash
cp "../pdpa-compliance-dissertation/Artefact/data/symbolized/pdpa_clause_profiles.json" \
   "./data/symbolized/pdpa_clause_profiles.json"

diff "../pdpa-compliance-dissertation/Artefact/data/symbolized/pdpa_clause_profiles.json" \
     "./data/symbolized/pdpa_clause_profiles.json" && echo "in sync"
```

**Windows (PowerShell)**
```powershell
Copy-Item ..\pdpa-compliance-dissertation\Artefact\data\symbolized\pdpa_clause_profiles.json .\data\symbolized\pdpa_clause_profiles.json

if (-not (Compare-Object (Get-Content ..\pdpa-compliance-dissertation\Artefact\data\symbolized\pdpa_clause_profiles.json) (Get-Content .\data\symbolized\pdpa_clause_profiles.json))) { "in sync" }
```

FleetTrack's SSP has the same drift risk in the other direction - the framework
copy at `data/ssps/fleettrack/fleettrack_ssp.json` carries a back-matter UUID
conformance fix. Re-copy after any SSP edit.

---

## Exit the env

Identical on both platforms:

```bash
deactivate
```

---

## Notes / open environment risks

- **Nothing is version-pinned.** `requirements.txt` is `pydantic>=2.0`, `pymupdf`,
  `pytest` with no pins. The reproducibility claim in the methodology depends on a
  fixed environment, so pin everything - including the SBERT model name and
  revision - before generating any result intended for the dissertation.
- **`sentence-transformers` is not installed yet**, and Relatedness needs it for
  the Stage 0 relatedness-floor gate, not just Stage 5 scoring. Worth installing
  early to confirm it works on Python 3.14 - PyTorch wheels historically lag new
  Python releases, and if they aren't available, a second venv on 3.12 is the
  fallback. Cheap to check now, expensive to discover in week 6:
```bash
  pip install sentence-transformers && python3 -c "import sentence_transformers, torch; print(torch.__version__)"
```