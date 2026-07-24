from pathlib import Path
import pytest
from pydantic import ValidationError
from pcef.models import PDPAProfileSet, ObligationUnit

# Framework-local copy of the symbolized profiles (build/test data input).
PROFILES = (
    Path(__file__).resolve().parents[1]
    / "data" / "symbolized" / "pdpa_clause_profiles.json"
)

def test_profiles_load_and_validate():
    """The symbolized JSON conforms to the locked schema and passes
    referential integrity."""
    assert PROFILES.exists(), f"profiles not found at {PROFILES}"
    profile_set = PDPAProfileSet.from_json_file(PROFILES)
    assert len(profile_set.clauses) == 11
    assert len(profile_set.definitions) == 23


# 1. extra="forbid" — an unknown key must be rejected
def test_unknown_key_rejected():
    with pytest.raises(ValidationError):
        ObligationUnit(
            unit_id="x-u1", unit_type="obligation", actor="controller",
            modality="shall", action="a", object="o",
            surprise_field="should not be allowed",   # stray key
        )


# 2. Literal — a value outside the closed vocabulary must be rejected
def test_bad_modality_rejected():
    with pytest.raises(ValidationError):
        ObligationUnit(
            unit_id="x-u1", unit_type="obligation", actor="controller",
            modality="shall_maybe",   # not in the Literal set
            action="a", object="o",
        )


# 3. Referential integrity — a dangling def_ref must be rejected
def test_dangling_def_ref_rejected():
    broken = {
        "meta": {
            "source": "t", "source_version": "t", "schema_version": "0.1",
            "schema_status": "t", "annotator": "t", "extraction_date": "t",
            "selected_clauses": [],
        },
        "definitions": [],   # empty — so any def_ref is dangling
        "clauses": [{
            "clause_id": "PDPA-sX", "title": "t", "status": "symbolized",
            "part": "I", "verbatim_text": "t", "simplified_text": "t",
            "annotation_notes": "t",
            "obligation_units": [{
                "unit_id": "sX-u1", "unit_type": "obligation",
                "actor": "controller", "modality": "shall",
                "action": "a", "object": "o",
                "attributes": [{
                    "attr_id": "sX-u1-a1", "name": "n", "kind": "process",
                    "specified_in_act": True,
                    "def_ref": "def-does-not-exist",   # points at nothing
                }],
            }],
        }],
    }
    with pytest.raises(ValidationError) as exc:
        PDPAProfileSet.model_validate(broken)
    assert "def_ref 'def-does-not-exist' unknown" in str(exc.value)