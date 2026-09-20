"""
Stage 4: validity gates. A pair that fails a gate is excluded, not scored low.

The applicability gate compares a unit's actor and conditions with the system's
PDPA role(s), taken from --system-role, else the SSP property `pdpa-role`
(comma-separated). If no role is declared, the actor check is skipped and the
pair is flagged; the gate never excludes on an assumed role. A system may hold
several roles, and a unit applies if its actor matches any of them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..models import ObligationUnit

ROLE_PROP = "pdpa-role"


@dataclass
class GateResult:
    passed: bool
    reason: str = ""
    flags: list[str] = field(default_factory=list)


def parse_roles(raw: Optional[str]) -> Optional[frozenset[str]]:
    if not raw:
        return None
    roles = frozenset(r.strip() for r in raw.split(",") if r.strip())
    return roles or None


def applicability_gate(unit: ObligationUnit, roles: Optional[frozenset[str]],
                       role_source: str) -> GateResult:
    flags: list[str] = []
    if roles is None:
        flags.append("actor_unverified: no PDPA role declared for the system; actor check skipped")
    elif unit.actor not in roles:
        return GateResult(False, f"unit actor '{unit.actor}' not in system roles "
                                 f"{sorted(roles)} (from {role_source})", flags)

    for cond in unit.applicability_conditions:
        target = cond.value or cond.target or cond.targets
        if cond.kind == "event_trigger":
            flags.append(f"prospective: duty fires on event ({target}); assessed as readiness")
        elif cond.kind == "clause_satisfaction":
            flags.append(f"dependency_not_scored (J7): depends on {target}")
        else:
            flags.append(f"unresolved_condition: {cond.kind}={target} (SSP does not state)")
    return GateResult(True, "applicable", flags)


def relatedness_floor_gate(relatedness: float, floor: float) -> GateResult:
    if relatedness < floor:
        return GateResult(False, f"relatedness {relatedness:.3f} < floor {floor:.2f}")
    return GateResult(True, "above floor")
