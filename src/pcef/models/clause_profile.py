"""
Pydantic contract for the symbolized PDPA clause profiles.

Locks the structure of Artefact/data/symbolized/pdpa_clause_profiles.json
(schema_version 0.1). Loading the JSON through PDPAProfileSet both freezes the
schema as a typed contract and validates the data, including intra-document
referential integrity. Pydantic v2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


class _Base(BaseModel):
    # Reject any JSON key not declared below. This is what makes the model a
    # drift detector rather than a lossy filter.
    model_config = ConfigDict(extra="forbid")


# --- definitions -----------------------------------------------------------

class DefinitionSource(_Base):
    kind: Literal["s56_glossary", "local", "schedule", "none"]
    clause: Optional[str] = None       # kind == "local"
    subsection: Optional[str] = None   # kind == "local"
    ref: Optional[str] = None          # kind == "schedule"


class Definition(_Base):
    def_id: str
    term: str
    source: DefinitionSource
    text: Optional[str] = None                        # null for undefined_flagged
    status: Literal["defined", "undefined_flagged"]
    note: Optional[str] = None


# --- attributes ------------------------------------------------------------

class Attribute(_Base):
    attr_id: str
    name: str
    kind: Literal["condition", "quality", "process", "temporal", "outcome"]
    specified_in_act: bool
    def_ref: Optional[str] = None
    quantifier: Optional[Literal["any", "all"]] = None
    note: Optional[str] = None


# --- applicability conditions ---------------------------------------------

class ApplicabilityCondition(_Base):
    # Permissive single model: `kind` selects which optional fields apply.
    # Discriminated-union-per-kind is the future refinement if we want
    # per-kind required-field enforcement.
    kind: str
    value: Optional[str] = None                 # most kinds
    target: Optional[str] = None                # kind == "clause_satisfaction"
    targets: Optional[list[str]] = None         # kind == "any_trigger_met"
    def_ref: Optional[str] = None
    note: Optional[str] = None


# --- control hints ---------------------------------------------------------

class ControlHint(_Base):
    family: Optional[str] = None                 # null when no anchor found
    candidate_controls: list[str] = []
    anchor_strength: Literal["strong", "moderate", "weak", "partial", "none_found"]
    note: Optional[str] = None


# --- obligation units ------------------------------------------------------

class ObligationUnit(_Base):
    unit_id: str
    unit_type: str
    actor: Literal["controller", "processor", "public_authority"]
    modality: Literal["shall", "shall_not", "may", "deemed", "conditional"]
    action: str
    object: str
    attributes: list[Attribute] = []
    applicability_conditions: list[ApplicabilityCondition] = []
    temporal_qualifier: Optional[str] = None
    keywords: list[str] = []
    control_hints: list[ControlHint] = []

    # exemption-family extras (present only on exemption / reclassification units)
    exempts: Optional[list[str]] = None          # attr_ids this unit modifies
    scope: Optional[str] = None

    # scoring control (only the not-scored unit carries these; default is scored)
    scored: bool = True
    scoring_note: Optional[str] = None


# --- dependencies & deferred specs ----------------------------------------

class Dependency(_Base):
    dep_type: str
    target: str
    via_unit: Optional[str] = None
    confidence: Literal["statutory", "annotator_judgment"]
    note: Optional[str] = None


class DeferredSpecification(_Base):
    aspect: str
    delegated_to: str
    instrument_status: Literal["unknown", "draft"]   # extend when a rule is gazetted
    working_reference: str
    affects_attributes: list[str] = []


# --- clause ----------------------------------------------------------------

class ClauseProfile(_Base):
    clause_id: str
    title: str
    status: str
    part: str
    clause_shapes: list[str] = []
    security_domains: list[str] = []
    verbatim_text: str
    simplified_text: str
    obligation_units: list[ObligationUnit] = []
    dependencies: list[Dependency] = []
    deferred_specifications: list[DeferredSpecification] = []
    definitions_used: list[str] = []
    annotation_notes: str


# --- meta & root -----------------------------------------------------------

class Meta(_Base):
    source: str
    source_version: str
    schema_version: str
    schema_status: str
    annotator: str
    extraction_date: str
    selected_clauses: list[str] = []


class PDPAProfileSet(_Base):
    meta: Meta
    definitions: list[Definition] = []
    clauses: list[ClauseProfile] = []

    # ---- id indexes ----
    def definition_ids(self) -> set[str]:
        return {d.def_id for d in self.definitions}

    def unit_ids(self) -> set[str]:
        return {u.unit_id for c in self.clauses for u in c.obligation_units}

    def attribute_ids(self) -> set[str]:
        return {
            a.attr_id
            for c in self.clauses
            for u in c.obligation_units
            for a in u.attributes
        }

    # ---- intra-document referential integrity ----
    @model_validator(mode="after")
    def _check_referential_integrity(self) -> "PDPAProfileSet":
        errors: list[str] = []
        def_ids, unit_ids, attr_ids = (
            self.definition_ids(),
            self.unit_ids(),
            self.attribute_ids(),
        )

        for c in self.clauses:
            for ref in c.definitions_used:
                if ref not in def_ids:
                    errors.append(f"{c.clause_id}: definitions_used '{ref}' unknown")

            for u in c.obligation_units:
                for a in u.attributes:
                    if a.def_ref and a.def_ref not in def_ids:
                        errors.append(f"{a.attr_id}: def_ref '{a.def_ref}' unknown")
                for ac in u.applicability_conditions:
                    if ac.def_ref and ac.def_ref not in def_ids:
                        errors.append(
                            f"{u.unit_id}: applicability def_ref '{ac.def_ref}' unknown"
                        )
                    for t in ac.targets or []:
                        if t not in unit_ids:
                            errors.append(
                                f"{u.unit_id}: any_trigger_met target '{t}' not a unit_id"
                            )
                for e in u.exempts or []:
                    if e not in attr_ids:
                        errors.append(f"{u.unit_id}: exempts '{e}' not an attr_id")

            for ds in c.deferred_specifications:
                for aff in ds.affects_attributes:
                    if aff not in attr_ids:
                        errors.append(
                            f"{c.clause_id}: affects_attributes '{aff}' not an attr_id"
                        )

            for dep in c.dependencies:
                if dep.via_unit and dep.via_unit not in unit_ids:
                    errors.append(
                        f"{c.clause_id}: dependency via_unit '{dep.via_unit}' not a unit_id"
                    )

        if errors:
            raise ValueError(
                "Referential integrity failed:\n  - " + "\n  - ".join(errors)
            )
        return self

    @classmethod
    def from_json_file(cls, path: str | Path) -> "PDPAProfileSet":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)
