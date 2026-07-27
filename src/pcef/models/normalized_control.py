"""
NormalizedControl - the fused control-side object for Stage 2.

DRAFT (not a lock). One NormalizedControl represents a single NIST SP 800-53
control after the two OSCAL layers are joined: the CATALOG (normative "what the
control requires") and the SSP (one organization's "what we actually did"). The
Stage-2 parser BUILDS these; nothing loads them from a file - contrast
ClauseProfile, which mirrors an authored JSON and is therefore locked. Expect
revisions once the real parser exercises this shape. Pydantic v2.
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


class SubPart(_Base):
    """One statement piece of a control (e.g. ra-8_smt, or ac-2_smt.a).

    Sub-parts are enumerated from the CATALOG (the normative set) and annotated
    with what the SSP did. A catalog piece the SSP never addressed is kept with
    status="absent" rather than silently dropped - that is what lets Coverage and
    Maturity see gaps.
    """

    smt_id: str                             # join key; matches catalog part id and SSP statement-id
    catalog_text: str                       # normative prose, ODP placeholders resolved/stripped
    status: Literal["implemented", "na", "absent"]
    remarks: Optional[str] = None           # statement-level note (e.g. "N/A", "KNOWN GAP - ...")
    by_components: list[ByComponent] = []   # SSP side; empty for na / absent


class NormalizedControl(_Base):
    """A catalog control fused with its SSP implementation, for one system."""

    control_id: str                         # "ra-8" - the join key everywhere
    family: str                             # "RA"
    title: str
    implementation_level: Optional[str] = None  # "organization" | "system"; a Directionality signal
    withdrawn: bool = False                 # catalog status; withdrawn controls filtered pre-pairing
    sub_parts: list[SubPart] = []
    # related_control_ids deliberately omitted for now: the catalog ships a
    # related-links graph, but that is a Stage-3 candidate-expansion hint we are
    # not consuming yet. Add when Stage 3 needs it.
