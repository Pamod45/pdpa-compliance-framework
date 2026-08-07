"""
NormalizedControl - the fused control-side object for Stage 2.

DRAFT (not a lock). One NormalizedControl represents a single NIST SP 800-53
control after the two OSCAL layers are joined: the CATALOG (normative "what the
control requires") and the SSP (one organization's "what we actually did"). The
Stage-2 parser BUILDS these; nothing loads them from a file - contrast
ClauseProfile, which mirrors an authored JSON and is therefore locked. Expect
revisions once the real parser exercises this shape. Pydantic v2.

Still a DRAFT. Revised 2026-08-06 to carry the A3 granularity decision
(decisions.md): sub-parts are the CATALOG'S LEAF parts, each resolved by walking
up the statement tree against the SSP, so a leaf covered only by an ancestor
statement is `inherited` rather than lost or mistaken for `absent`.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    # Mirrors clause_profile._Base; kept local so the locked ClauseProfile file
    # stays untouched. Extract to a shared models/_base.py if a third model needs it.
    model_config = ConfigDict(extra="forbid")


class ByComponent(_Base):
    """One organization's implementation of a sub-part, through one component.

    A sub-part can have several by-components (ac-3 and sa-9 do in FleetTrack),
    so these are always a list on the SubPart.
    """

    component_uuid: str
    description: str                        # SSP implementation prose - Maturity's main input
    remarks: Optional[str] = None           # by-component note, e.g. "KNOWN GAP: ..."
    component_status: Optional[str] = None  # resolved at parse time from component-uuid ->
                                            # component.status.state ("operational" |
                                            # "disposition" | ...); the Option A gap signal
    set_parameters: dict[str, str] = {}     # org-chosen ODP values; {} when absent (usual case)


class UnmatchedStatement(_Base):
    """An SSP statement-id with no counterpart anywhere in the catalog control.

    Real and not rare: NIST's own example SSP addresses au-1_smt.b.1 and
    au-1_smt.b.2, neither of which exists in SP 800-53 Rev 5 - they describe
    policy/procedure review, which Rev 5 numbers .c.1/.c.2. That is catalog
    version drift, not a malformed SSP.

    Retained and reported, never scored: there is no catalog_text to align
    against, so no Alignment measure can read it. Dropping it instead would
    silently discard real implementation evidence.
    """

    smt_id: str                             # the SSP's statement-id, absent from the catalog
    remarks: Optional[str] = None
    by_components: list[ByComponent] = []


class SubPart(_Base):
    """One LEAF statement piece of a control (e.g. au-2_smt.a, ac-2_smt.d.1).

    The row set is the catalog's leaf parts, identically for every SSP (A3,
    decisions.md 2026-08-06) - never whatever statement-ids the SSP happened to
    write. Each leaf is resolved by walking UP the statement tree against the SSP
    and takes exactly one status:

      implemented - the leaf itself carries by-components
      inherited   - it does not, but its NEAREST ancestor does; that ancestor's
                    by-components are borrowed here and scored at an a-priori
                    discount, because covering an obligation only through a
                    general statement is weaker evidence than addressing it
      na          - the leaf is present in the SSP with no by-components and its
                    remarks declare N/A
      absent      - nothing at the leaf or anywhere above it

    How these statuses are treated arithmetically (numerator/denominator) is the
    VERTICAL aggregation rule and is still OPEN - see project.md. This model only
    records which status applies.
    """

    smt_id: str                             # join key; a catalog LEAF part id
    catalog_text: str                       # normative prose, ODP placeholders resolved/stripped
    status: Literal["implemented", "inherited", "na", "absent"]
    source_smt_id: Optional[str] = None     # which statement the by_components actually came from:
                                            #   implemented -> == smt_id
                                            #   inherited   -> the nearest ancestor's id
                                            #   na          -> == smt_id (the N/A marker's home)
                                            #   absent      -> None
                                            # Without this, implemented and inherited are
                                            # indistinguishable in the output and provenance
                                            # cannot show where the text came from.
    superseded_sources: list[str] = []      # ancestor statement-ids that DO carry by-components but
                                            # were skipped because a nearer source won. Nearest-
                                            # ancestor-only discards real text (au-1_smt.a's four
                                            # by-components are scored nowhere); the decision
                                            # requires that loss be visible in provenance, not
                                            # silent. Ids only - text is re-fetchable from the SSP.
    remarks: Optional[str] = None           # statement-level note (e.g. "N/A", "KNOWN GAP - ...")
    by_components: list[ByComponent] = []   # SSP side; empty for na / absent


class NormalizedControl(_Base):
    """A catalog control fused with its SSP implementation, for one system."""

    control_id: str                         # "ra-8" - the join key everywhere
    family: str                             # "RA"
    title: str
    implementation_level: Optional[str] = None  # "organization" | "system"; a Directionality signal
    withdrawn: bool = False                 # catalog status; withdrawn controls filtered pre-pairing
    sub_parts: list[SubPart] = []           # ALWAYS the catalog's leaf parts (A3), never the SSP's
    unmatched_statements: list[UnmatchedStatement] = []  # SSP statement-ids with no catalog match
    # related_control_ids deliberately omitted for now: the catalog ships a
    # related-links graph, but that is a Stage-3 candidate-expansion hint we are
    # not consuming yet. Add when Stage 3 needs it.
