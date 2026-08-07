"""
Catalog loader - the normative half of Stage 2.

Reads the NIST SP 800-53 Rev 5 OSCAL catalog and exposes, per control, the
statement tree with ODP placeholders resolved. This side never touches an SSP:
under Set C, Stage 1 Alignment reads the clause and the CATALOG only, so
catalog_text must not be contaminated with any organization's chosen parameter
values. Organization values live on ByComponent.set_parameters and feed
Realization instead.

Deliberately NOT Pydantic. The catalog is trusted, fixed input and the objects
here are parser internals, not the pipeline's output contract - that is
NormalizedControl. Typed on the way out, plain on the way in.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

# The catalog uses exactly one placeholder form, verified across all 2945
# occurrences: "{{ insert: param, <param-id> }}".
_PLACEHOLDER = re.compile(r"\{\{\s*insert:\s*param,\s*([\w.\-]+)\s*\}\}")

# Part names that carry normative obligation text. "guidance",
# "assessment-objective" etc. are excluded - they are commentary, not duties.
_STATEMENT_NAMES = ("statement", "item")


def _render_param(param: dict) -> str:
    """Human-readable stand-in for an unfilled ODP.

    Plain text, no brackets or markers: this prose is fed to SBERT for
    Relatedness, and bracketed metadata is noise that shifts the embedding
    without adding meaning.
    """
    if "label" in param:
        return param["label"]
    sel = param.get("select")
    if sel:
        choices = "; ".join(sel.get("choice", []))
        lead = "one or more of" if sel.get("how-many") == "one-or-more" else "one of"
        return f"{lead}: {choices}"
    return param.get("id", "")


def _resolve(prose: str, params: dict, _max_passes: int = 8) -> str:
    """Substitute ODP placeholders, repeatedly.

    One pass is not enough: a `select` param's own choices can contain further
    placeholders (ac-7's choice reads "lock the account or node for
    {{ insert: param, ac-07_odp.04 }}"), and re.sub never rescans the text it
    inserts. 67 occurrences across 46 statements survive a single pass.

    Bounded rather than while-True: a malformed or cyclic param reference would
    otherwise loop forever. If the cap is hit, any remaining placeholder is left
    visible in the prose rather than silently deleted - a visible artefact is
    debuggable, a silent deletion is not.
    """
    for _ in range(_max_passes):
        if not _PLACEHOLDER.search(prose):
            break
        prose = _PLACEHOLDER.sub(
            lambda m: _render_param(params.get(m.group(1), {"id": m.group(1)})),
            prose,
        )
    # Substitution leaves doubled spaces and space-before-punctuation where the
    # catalog padded around its placeholders. Tidy, so the prose SBERT sees is
    # not littered with artefacts of the templating.
    prose = re.sub(r"\s+", " ", prose)
    prose = re.sub(r"\s+([;,.])", r"\1", prose)
    return prose.strip()


@dataclass(frozen=True)
class StatementNode:
    """One node of a control's statement tree (a `statement` or `item` part)."""

    smt_id: str
    prose: str                              # ODP-resolved; "" for pure containers
    param_ids: tuple[str, ...]              # ODPs referenced by this node's own prose
    children: tuple["StatementNode", ...]

    @property
    def is_leaf(self) -> bool:
        """A leaf is a node with no statement/item children.

        Leaves are the row set A3 fixes for every SSP (decisions.md 2026-08-06).
        """
        return not self.children

    def walk(self) -> Iterator["StatementNode"]:
        yield self
        for c in self.children:
            yield from c.walk()


@dataclass(frozen=True)
class CatalogControl:
    """One control as the catalog defines it. No SSP data here."""

    control_id: str                         # "au-2", "ac-2.13"
    family: str                             # "AU", "AC"
    title: str
    implementation_level: Optional[str]     # "organization" | "system" | None
    withdrawn: bool
    statement: Optional[StatementNode]      # None for most withdrawn controls
    _nodes: dict[str, StatementNode] = field(repr=False, default_factory=dict)
    _parents: dict[str, Optional[str]] = field(repr=False, default_factory=dict)

    @property
    def leaves(self) -> tuple[StatementNode, ...]:
        if self.statement is None:
            return ()
        return tuple(n for n in self.statement.walk() if n.is_leaf)

    @property
    def part_ids(self) -> frozenset[str]:
        """Every statement/item id in this control.

        The unmatched sweep uses this: an SSP statement-id not in here has no
        catalog counterpart (NIST's own example does this - au-1_smt.b.1/.b.2).
        """
        return frozenset(self._nodes)

    def node(self, smt_id: str) -> Optional[StatementNode]:
        return self._nodes.get(smt_id)

    def ancestors(self, smt_id: str) -> tuple[str, ...]:
        """Ancestor ids, nearest first - the A3 walk order.

        Uses real parent pointers, never string manipulation. Splitting ids on
        "." is structurally unsafe because enhancement control ids contain dots:
        "ac-2.13_smt.a" would rsplit to "ac-2.13_smt" and then to "ac-2", a
        CONTROL id. No leaf in Rev 5 v5.2.0 is nested deeply enough for the two
        approaches to diverge today, so this is a latent hazard rather than a
        live bug - but parent pointers cost nothing and remove it.
        """
        out: list[str] = []
        cur = self._parents.get(smt_id)
        while cur is not None:
            out.append(cur)
            cur = self._parents.get(cur)
        return tuple(out)


class CatalogIndex:
    """All controls in one catalog, keyed by control id."""

    def __init__(self, controls: dict[str, CatalogControl], version: str, oscal_version: str):
        self._controls = controls
        self.version = version
        self.oscal_version = oscal_version

    @classmethod
    def from_file(cls, path: str | Path) -> "CatalogIndex":
        with open(path, encoding="utf-8") as fh:
            cat = json.load(fh)["catalog"]

        # Global param index. Params are normally defined on the control that
        # uses them, but three controls (ia-13.3, sc-42.2, si-10.1) reference a
        # param defined on their base control, so a control-local index alone
        # would leave those placeholders unresolved.
        params: dict[str, dict] = {}
        for _, raw in cls._iter_raw(cat):
            for p in raw.get("params", []):
                params[p["id"]] = p

        controls: dict[str, CatalogControl] = {}
        for group_id, raw in cls._iter_raw(cat):
            ctrl = cls._build_control(raw, group_id, params)
            controls[ctrl.control_id] = ctrl

        meta = cat.get("metadata", {})
        return cls(controls, meta.get("version", ""), meta.get("oscal-version", ""))

    @staticmethod
    def _iter_raw(cat: dict) -> Iterator[tuple[str, dict]]:
        """Yield (group_id, control) for base controls and their enhancements."""
        for group in cat.get("groups", []):
            gid = group.get("id", "")
            for ctrl in group.get("controls", []):
                yield gid, ctrl
                for enh in ctrl.get("controls", []):
                    yield gid, enh

    @classmethod
    def _build_control(cls, raw: dict, group_id: str, params: dict) -> CatalogControl:
        props = raw.get("props", [])

        def prop(name: str) -> Optional[str]:
            for p in props:
                if p.get("name") == name and p.get("class") is None:
                    return p.get("value")
            return None

        withdrawn = prop("status") == "withdrawn"

        root = None
        for part in raw.get("parts", []):
            if part.get("name") == "statement":
                root = cls._build_node(part, params)
                break

        nodes: dict[str, StatementNode] = {}
        parents: dict[str, Optional[str]] = {}
        if root is not None:
            parents[root.smt_id] = None
            stack = [root]
            while stack:
                n = stack.pop()
                nodes[n.smt_id] = n
                for c in n.children:
                    parents[c.smt_id] = n.smt_id
                    stack.append(c)

        return CatalogControl(
            control_id=raw["id"],
            family=group_id.upper(),
            title=raw.get("title", ""),
            implementation_level=prop("implementation-level"),
            withdrawn=withdrawn,
            statement=root,
            _nodes=nodes,
            _parents=parents,
        )

    @classmethod
    def _build_node(cls, part: dict, params: dict) -> StatementNode:
        raw_prose = part.get("prose", "") or ""
        param_ids = tuple(dict.fromkeys(_PLACEHOLDER.findall(raw_prose)))
        prose = _resolve(raw_prose, params)
        children = tuple(
            cls._build_node(p, params)
            for p in (part.get("parts") or [])
            if p.get("name") in _STATEMENT_NAMES
        )
        return StatementNode(
            smt_id=part["id"],
            prose=prose,
            param_ids=param_ids,
            children=children,
        )

    def __getitem__(self, control_id: str) -> CatalogControl:
        return self._controls[control_id]

    def get(self, control_id: str) -> Optional[CatalogControl]:
        return self._controls.get(control_id)

    def __contains__(self, control_id: object) -> bool:
        return control_id in self._controls

    def __len__(self) -> int:
        return len(self._controls)

    def __iter__(self) -> Iterator[CatalogControl]:
        return iter(self._controls.values())
