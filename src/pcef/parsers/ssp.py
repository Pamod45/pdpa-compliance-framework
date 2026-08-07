"""
SSP loader - the organizational half of Stage 2.

Reads an OSCAL System Security Plan and exposes what the document actually
claims, keyed by control id and statement id. It applies NO scoring rules and
makes NO judgements: the A3 leaf-resolution walk, the na/absent decision and
both aggregation rules live downstream in the fuse. This module's only job is
to surface the SSP faithfully, including the parts that are missing.

Written against the OSCAL SSP schema, not against FleetTrack. Shapes neither
sample SSP uses - IR-level by-components, `implementation-status`, non-
operational component states - are handled because they are legal OSCAL and a
real SSP will eventually use them.

Deliberately NOT Pydantic, for the same reason as the catalog loader: this is a
parser internal, and modelling the full OSCAL SSP schema would mean rejecting
valid documents over fields the framework never reads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional


class SspIntegrityError(ValueError):
    """The SSP violates a structural guarantee the parser relies on.

    Raised loudly rather than worked around. A dangling component-uuid or a
    duplicated statement-id is a broken document, not a stylistic variation -
    and silently dropping either would corrupt scores in ways that are very
    hard to trace back from a final number.
    """


def _flatten_set_parameters(raw: Optional[list]) -> dict[str, str]:
    """OSCAL set-parameters -> {param-id: "value; value"}.

    Values are a list because a parameter may take several. Joined rather than
    kept as a list so downstream feature checks can treat every parameter value
    uniformly as a string.
    """
    out: dict[str, str] = {}
    for sp in raw or []:
        pid = sp.get("param-id")
        if pid:
            out[pid] = "; ".join(str(v) for v in sp.get("values", []))
    return out


@dataclass(frozen=True)
class Component:
    """A system component as declared in system-implementation."""

    uuid: str
    title: str
    type: str                               # software / policy / process / guidance / this-system
    state: str                              # operational / disposition / under-development / other
    description: str = ""
    remarks: Optional[str] = None

    @property
    def is_operational(self) -> bool:
        """Whether this component is live.

        The horizontal collapse discounts anything non-operational. Expressed as
        a positive test rather than a list of bad states so that an unfamiliar
        state value fails closed (discounted) instead of silently counting full.
        """
        return self.state == "operational"


@dataclass(frozen=True)
class SspByComponent:
    """One component's account of one statement. The unit Maturity scores."""

    component_uuid: str
    description: str
    set_parameters: dict[str, str] = field(default_factory=dict)
    remarks: Optional[str] = None
    implementation_status: Optional[str] = None   # absent from both sample SSPs; optional in OSCAL

    # Denormalized from system-implementation so the fuse never has to carry the
    # component table around just to read a state.
    component_title: str = ""
    component_type: str = ""
    component_state: str = ""

    @property
    def is_operational(self) -> bool:
        return self.component_state == "operational"


@dataclass(frozen=True)
class SspStatement:
    """What the SSP said about one statement-id.

    `by_components` may legitimately be empty: NIST's own example lists
    au-1_smt.b with no by-components and remarks "N/A", and lists au-1_smt with
    neither. Distinguishing "declared inapplicable" from "listed but silent" is
    the fuse's job, not this module's.
    """

    smt_id: str
    remarks: Optional[str] = None
    by_components: tuple[SspByComponent, ...] = ()


@dataclass(frozen=True)
class SspControl:
    """One implemented-requirement."""

    control_id: str
    statements: dict[str, SspStatement] = field(default_factory=dict)
    set_parameters: dict[str, str] = field(default_factory=dict)
    remarks: Optional[str] = None

    # OSCAL permits by-components directly on an implemented-requirement, with no
    # statement in between. Neither sample SSP does this, but it is valid and
    # dropping it would discard real implementation evidence. Kept separate
    # rather than folded into a fabricated statement id - the fuse decides what
    # control-level evidence means.
    by_components: tuple[SspByComponent, ...] = ()

    @property
    def statement_ids(self) -> frozenset[str]:
        return frozenset(self.statements)


class SspDocument:
    """One parsed SSP."""

    def __init__(
        self,
        uuid: str,
        system_name: str,
        oscal_version: str,
        components: dict[str, Component],
        controls: dict[str, SspControl],
        source_path: Optional[str] = None,
    ):
        self.uuid = uuid
        self.system_name = system_name
        self.oscal_version = oscal_version
        self.components = components
        self.controls = controls
        self.source_path = source_path

    @classmethod
    def from_file(cls, path: str | Path) -> "SspDocument":
        with open(path, encoding="utf-8") as fh:
            ssp = json.load(fh)["system-security-plan"]

        components: dict[str, Component] = {}
        for raw in ssp.get("system-implementation", {}).get("components", []):
            components[raw["uuid"]] = Component(
                uuid=raw["uuid"],
                title=raw.get("title", ""),
                type=raw.get("type", ""),
                state=(raw.get("status") or {}).get("state", ""),
                description=raw.get("description", ""),
                remarks=raw.get("remarks"),
            )

        controls: dict[str, SspControl] = {}
        for ir in ssp.get("control-implementation", {}).get("implemented-requirements", []):
            cid = ir["control-id"]
            if cid in controls:
                raise SspIntegrityError(
                    f"control-id {cid!r} appears in more than one implemented-requirement; "
                    "merging them would silently pick a winner"
                )

            statements: dict[str, SspStatement] = {}
            for st in ir.get("statements", []):
                sid = st["statement-id"]
                if sid in statements:
                    raise SspIntegrityError(
                        f"statement-id {sid!r} appears more than once under control {cid!r}"
                    )
                statements[sid] = SspStatement(
                    smt_id=sid,
                    remarks=st.get("remarks"),
                    by_components=cls._by_components(st.get("by-components"), components, cid, sid),
                )

            controls[cid] = SspControl(
                control_id=cid,
                statements=statements,
                set_parameters=_flatten_set_parameters(ir.get("set-parameters")),
                remarks=ir.get("remarks"),
                by_components=cls._by_components(ir.get("by-components"), components, cid, None),
            )

        meta = ssp.get("metadata", {})
        chars = ssp.get("system-characteristics", {})
        return cls(
            uuid=ssp.get("uuid", ""),
            system_name=chars.get("system-name", meta.get("title", "")),
            oscal_version=meta.get("oscal-version", ""),
            components=components,
            controls=controls,
            source_path=str(path),
        )

    @staticmethod
    def _by_components(
        raw: Optional[list],
        components: dict[str, Component],
        control_id: str,
        smt_id: Optional[str],
    ) -> tuple[SspByComponent, ...]:
        out: list[SspByComponent] = []
        for b in raw or []:
            cuuid = b["component-uuid"]
            comp = components.get(cuuid)
            if comp is None:
                where = f"{control_id}/{smt_id}" if smt_id else f"{control_id} (control level)"
                raise SspIntegrityError(
                    f"by-component at {where} references component-uuid {cuuid!r}, "
                    "which is not declared in system-implementation"
                )
            out.append(
                SspByComponent(
                    component_uuid=cuuid,
                    description=b.get("description", ""),
                    set_parameters=_flatten_set_parameters(b.get("set-parameters")),
                    remarks=b.get("remarks"),
                    implementation_status=(b.get("implementation-status") or {}).get("state"),
                    component_title=comp.title,
                    component_type=comp.type,
                    component_state=comp.state,
                )
            )
        return tuple(out)

    def get(self, control_id: str) -> Optional[SspControl]:
        return self.controls.get(control_id)

    def __getitem__(self, control_id: str) -> SspControl:
        return self.controls[control_id]

    def __contains__(self, control_id: object) -> bool:
        return control_id in self.controls

    def __len__(self) -> int:
        return len(self.controls)

    def __iter__(self) -> Iterator[SspControl]:
        return iter(self.controls.values())
