"""
Stage 2 fuse - joins the catalog and the SSP into NormalizedControl.

This is where the A3 granularity decision (decisions.md 2026-08-06) is
implemented. The row set is ALWAYS the catalog's leaf statement parts, never
whatever the SSP happened to write; each leaf is resolved by walking UP the
statement tree against the SSP, nearest ancestor wins.

The fuse decides STRUCTURE only - which rows exist and where their text came
from. It computes no scores. The horizontal and vertical aggregation rules are
still open (project.md) and live downstream in Stage 5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from ..models import ByComponent, NormalizedControl, SubPart, UnmatchedStatement
from .catalog import CatalogControl, CatalogIndex
from .ssp import SspByComponent, SspControl, SspDocument, SspStatement

# Deliberately narrow. FleetTrack's statement remarks are commentary - "KNOWN GAP
# - flagged explicitly, not glossed over" on sc-8 and sc-28 - and those
# statements DO carry by-components. A loose detector that matched on "gap" or
# any substring would reclassify them as `na`, lift them out of the denominator,
# and erase the two gaps that were deliberately left in the SSP.
#
# Anything that has zero by-components but does NOT match is reported in
# NormalizationReport.ambiguous_na rather than silently treated as absent, so a
# real declaration phrased unusually surfaces instead of quietly scoring 0.
_NA_FORMS = frozenset({"n/a", "na", "n.a", "not applicable"})
# Lookahead rather than \b: after "N.A." the next char is a space, and "." and
# " " are both non-word, so \b does not match there and "N.A. - not collected"
# would be missed. The lookahead is also what keeps "na" from firing on
# "National security exemption applies" or "Narrative only".
_NA_PREFIX = re.compile(
    r"^(not applicable|n/a|n\.a\.|na)(?=$|[\s\-:;,.])", re.IGNORECASE
)


def declares_na(remarks: Optional[str]) -> bool:
    """Whether a statement's remarks declare the obligation inapplicable."""
    if not remarks:
        return False
    text = re.sub(r"\s+", " ", remarks.strip()).lower()
    # rstrip(" .") is greedy by design: "n.a." -> "n.a", which is the stored form.
    if text.rstrip(" .") in _NA_FORMS:
        return True
    return bool(_NA_PREFIX.match(text))


@dataclass
class NormalizationReport:
    """Conditions the fuse met that a human should see.

    None of these are errors - they are places where the parser had to apply a
    rule that the data does not currently exercise, or where an SSP said
    something the framework cannot score. Collected rather than logged so tests
    can assert on them.
    """

    unknown_control_ids: list[str] = field(default_factory=list)
    withdrawn_control_ids: list[str] = field(default_factory=list)
    # zero by-components, remarks present, but not recognised as an N/A declaration
    ambiguous_na: list[tuple[str, str, str]] = field(default_factory=list)
    # a leaf took `na` from an ANCESTOR rather than from itself (see note below)
    inherited_na: list[tuple[str, str, str]] = field(default_factory=list)
    # controls whose evidence sits on the implemented-requirement, not a statement
    control_level_evidence: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not (
            self.unknown_control_ids
            or self.ambiguous_na
            or self.inherited_na
            or self.control_level_evidence
        )


def _to_model(b: SspByComponent) -> ByComponent:
    return ByComponent(
        component_uuid=b.component_uuid,
        description=b.description,
        remarks=b.remarks,
        component_status=b.component_state or None,
        set_parameters=dict(b.set_parameters),
    )


def _resolve_leaf(
    leaf_id: str,
    catalog_text: str,
    cat: CatalogControl,
    ssp_ctrl: Optional[SspControl],
    report: NormalizationReport,
) -> SubPart:
    """The A3 walk for one catalog leaf. Own beats ancestor, nearest ancestor wins."""

    def stmt(sid: str) -> Optional[SspStatement]:
        return ssp_ctrl.statements.get(sid) if ssp_ctrl else None

    own = stmt(leaf_id)

    # 1. The leaf speaks for itself.
    if own and own.by_components:
        return SubPart(
            smt_id=leaf_id,
            catalog_text=catalog_text,
            status="implemented",
            source_smt_id=leaf_id,
            remarks=own.remarks,
            by_components=[_to_model(b) for b in own.by_components],
        )

    # 2. The leaf is listed but declared inapplicable. Own beats ancestor, so this
    #    outranks any ancestor that does carry text.
    if own and declares_na(own.remarks):
        return SubPart(
            smt_id=leaf_id,
            catalog_text=catalog_text,
            status="na",
            source_smt_id=leaf_id,
            remarks=own.remarks,
        )

    # Listed, silent, and the remarks did not parse as a declaration. Not treated
    # as N/A - but surfaced, because guessing either way would be wrong.
    if own and own.remarks:
        report.ambiguous_na.append((cat.control_id, leaf_id, own.remarks))

    # 3. Walk up. Nearest ancestor with by-components wins; any further ancestor
    #    that also carries text is recorded as superseded, not scored.
    source_id: Optional[str] = None
    source_stmt: Optional[SspStatement] = None
    superseded: list[str] = []

    for anc_id in cat.ancestors(leaf_id):
        anc = stmt(anc_id)
        if anc is None:
            continue
        if anc.by_components:
            if source_id is None:
                source_id, source_stmt = anc_id, anc
            else:
                superseded.append(anc_id)
        elif source_id is None and declares_na(anc.remarks):
            # An ancestor obligation declared inapplicable, and nothing nearer
            # spoke. Its sub-obligations inherit that. NOT exercised by either
            # sample SSP - au-1_smt.b is the only N/A anywhere and it is a leaf -
            # so this is an implementation reading, not a recorded decision.
            report.inherited_na.append((cat.control_id, leaf_id, anc_id))
            return SubPart(
                smt_id=leaf_id,
                catalog_text=catalog_text,
                status="na",
                source_smt_id=anc_id,
                remarks=anc.remarks,
            )

    if source_id is not None and source_stmt is not None:
        return SubPart(
            smt_id=leaf_id,
            catalog_text=catalog_text,
            status="inherited",
            source_smt_id=source_id,
            superseded_sources=superseded,
            remarks=source_stmt.remarks,
            by_components=[_to_model(b) for b in source_stmt.by_components],
        )

    # 4. OSCAL allows by-components directly on the implemented-requirement, with
    #    no statement in between. Treated as evidence for the whole control, so
    #    every unaddressed leaf inherits it. source_smt_id is the CONTROL id,
    #    which is honest about where the text came from. Also unexercised.
    if ssp_ctrl and ssp_ctrl.by_components:
        if cat.control_id not in report.control_level_evidence:
            report.control_level_evidence.append(cat.control_id)
        return SubPart(
            smt_id=leaf_id,
            catalog_text=catalog_text,
            status="inherited",
            source_smt_id=ssp_ctrl.control_id,
            remarks=ssp_ctrl.remarks,
            by_components=[_to_model(b) for b in ssp_ctrl.by_components],
        )

    # 5. Nothing at the leaf, nothing above it. A real gap.
    return SubPart(
        smt_id=leaf_id,
        catalog_text=catalog_text,
        status="absent",
        source_smt_id=None,
    )


def _ancestor_context(cat: CatalogControl, smt_id: str) -> str:
    """Ancestor prose, top-down, so a list-item leaf keeps the stem that gives it meaning."""
    parts = []
    for anc in reversed(cat.ancestors(smt_id)):
        node = cat.node(anc)
        if node is not None and node.prose.strip():
            parts.append(node.prose.strip())
    return " ".join(parts)


def normalize_control(
    control_id: str,
    catalog: CatalogIndex,
    ssp: Optional[SspDocument] = None,
    report: Optional[NormalizationReport] = None,
) -> NormalizedControl:
    """Fuse one control. Works whether or not the SSP mentions it.

    A control the SSP never names still produces a NormalizedControl with every
    leaf `absent` - Stage 3 may pair a clause against a control the organization
    said nothing about, and that silence is the finding.
    """
    report = report if report is not None else NormalizationReport()
    cat = catalog.get(control_id)
    if cat is None:
        raise KeyError(f"control-id {control_id!r} is not in the catalog")

    if cat.withdrawn and control_id not in report.withdrawn_control_ids:
        report.withdrawn_control_ids.append(control_id)

    ssp_ctrl = ssp.get(control_id) if ssp else None

    sub_parts = [
        _resolve_leaf(leaf.smt_id, leaf.prose, cat, ssp_ctrl, report).model_copy(
            update={"catalog_context": _ancestor_context(cat, leaf.smt_id)}
        )
        for leaf in cat.leaves
    ]

    unmatched: list[UnmatchedStatement] = []
    if ssp_ctrl:
        for sid in sorted(ssp_ctrl.statement_ids - cat.part_ids):
            st = ssp_ctrl.statements[sid]
            unmatched.append(
                UnmatchedStatement(
                    smt_id=sid,
                    remarks=st.remarks,
                    by_components=[_to_model(b) for b in st.by_components],
                )
            )

    return NormalizedControl(
        control_id=cat.control_id,
        family=cat.family,
        title=cat.title,
        implementation_level=cat.implementation_level,
        withdrawn=cat.withdrawn,
        sub_parts=sub_parts,
        unmatched_statements=unmatched,
    )


def normalize_all(
    catalog: CatalogIndex,
    ssp: SspDocument,
    control_ids: Optional[Iterable[str]] = None,
) -> tuple[list[NormalizedControl], NormalizationReport]:
    """Fuse every control the SSP addresses, or a caller-supplied set.

    Control ids the SSP names but the catalog does not contain are collected in
    the report rather than raised: an SSP written against a different catalog
    revision is a real condition, and it should be visible, not fatal.
    """
    report = NormalizationReport()
    ids = list(control_ids) if control_ids is not None else list(ssp.controls)

    out: list[NormalizedControl] = []
    for cid in ids:
        if cid not in catalog:
            report.unknown_control_ids.append(cid)
            continue
        out.append(normalize_control(cid, catalog, ssp, report))
    return out, report
