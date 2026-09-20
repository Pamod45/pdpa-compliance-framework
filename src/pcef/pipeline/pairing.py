"""
Stage 3: candidate clause-control pairs from control hints.

A unit is paired with its explicitly hinted controls ("explicit_hint") and with
every SSP control in a hinted family ("family_hint"). A hinted control that the
SSP does not mention is still paired, so its absence shows as zero Realization.
Units with no usable hint are reported as unanchored rather than dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import ClauseProfile, ObligationUnit
from ..parsers import CatalogIndex, SspDocument


@dataclass
class CandidatePair:
    clause: ClauseProfile
    unit: ObligationUnit
    control_id: str
    source: str  # "explicit_hint" | "family_hint"


@dataclass
class PairingResult:
    pairs: list[CandidatePair] = field(default_factory=list)
    unanchored_units: list[str] = field(default_factory=list)
    not_scored_units: list[tuple[str, str]] = field(default_factory=list)
    dropped_hints: list[tuple[str, str, str]] = field(default_factory=list)  # (unit, control, why)


def generate_pairs(
    clauses: list[ClauseProfile], catalog: CatalogIndex, ssp: SspDocument
) -> PairingResult:
    res = PairingResult()
    ssp_ids = [c.control_id for c in ssp]

    for clause in clauses:
        for unit in clause.obligation_units:
            if not unit.scored:
                res.not_scored_units.append((unit.unit_id, unit.scoring_note or "scored: false"))
                continue

            chosen: dict[str, str] = {}
            families: set[str] = set()
            for hint in unit.control_hints:
                if hint.family:
                    families.add(hint.family.upper())
                for cid in hint.candidate_controls:
                    cat = catalog.get(cid)
                    if cat is None:
                        res.dropped_hints.append((unit.unit_id, cid, "not in catalog"))
                    elif cat.withdrawn:
                        res.dropped_hints.append((unit.unit_id, cid, "withdrawn"))
                    else:
                        chosen.setdefault(cid, "explicit_hint")

            for cid in ssp_ids:
                cat = catalog.get(cid)
                if cat and not cat.withdrawn and cat.family.upper() in families:
                    chosen.setdefault(cid, "family_hint")

            if not chosen:
                res.unanchored_units.append(unit.unit_id)
                continue
            for cid in sorted(chosen):
                res.pairs.append(CandidatePair(clause, unit, cid, chosen[cid]))
    return res
