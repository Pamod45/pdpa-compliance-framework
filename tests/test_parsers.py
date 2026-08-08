"""Stage 2 parser tests: catalog loader, SSP loader, and the A3 fuse.

Expected values are NOT round-trips of the code under test. Every count here was
derived independently against the raw OSCAL JSON before the parsers existed, or
worked out by hand from the A3 decision (decisions.md 2026-08-06). That is what
makes them regression tests rather than snapshots.
"""

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from pcef.parsers import (
    CatalogIndex,
    SspDocument,
    SspIntegrityError,
    declares_na,
    normalize_all,
    normalize_control,
)
from pcef.parsers.catalog import _PLACEHOLDER

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "raw" / "catalogs" / "nist_sp800_53_rev5" / "NIST_SP-800-53_rev5_catalog.json"
FLEETTRACK = ROOT / "data" / "raw" / "ssps" / "fleettrack" / "fleettrack_ssp.json"
NIST_EXAMPLE = ROOT / "data" / "raw" / "ssps" / "public" / "nist_example" / "enterprise_logging_auditing_ssp.json"


# Module-scoped: the catalog is 1196 controls, too slow to reload per test.
@pytest.fixture(scope="module")
def catalog():
    return CatalogIndex.from_file(CATALOG)


@pytest.fixture(scope="module")
def fleettrack():
    return SspDocument.from_file(FLEETTRACK)


@pytest.fixture(scope="module")
def nist_example():
    return SspDocument.from_file(NIST_EXAMPLE)


# --------------------------------------------------------------------------
# Catalog loader
# --------------------------------------------------------------------------

def test_catalog_loads(catalog):
    assert len(catalog) == 1196
    assert catalog.version == "5.2.0"
    assert catalog.oscal_version == "1.2.2"


def test_catalog_leaves_are_catalog_defined_not_ssp_defined(catalog):
    """au-2 has five obligations in the catalog. FleetTrack addresses none of
    them by name - the row set must come from here regardless."""
    assert [n.smt_id for n in catalog["au-2"].leaves] == [
        "au-2_smt.a", "au-2_smt.b", "au-2_smt.c", "au-2_smt.d", "au-2_smt.e",
    ]
    assert len(catalog["ac-2"].leaves) == 18
    assert len(catalog["ac-3"].leaves) == 1      # ac-3_smt is itself a leaf
    assert len(catalog["au-1"].leaves) == 6


def test_no_unresolved_odp_placeholders(catalog):
    """Regression guard. A select param's own choices can contain further
    placeholders (ac-7), and re.sub never rescans what it inserts - 67
    occurrences across 46 statements survive a single pass."""
    leftover = [
        (c.control_id, n.smt_id)
        for c in catalog if c.statement
        for n in c.statement.walk()
        if _PLACEHOLDER.search(n.prose)
    ]
    assert leftover == []


def test_every_leaf_has_prose(catalog):
    """Leaves become scored rows, so empty catalog_text would be a silent hole."""
    empty = [n.smt_id for c in catalog for n in c.leaves if not n.prose]
    assert empty == []
    assert sum(len(c.leaves) for c in catalog) == 1751


def test_ancestors_are_nearest_first(catalog):
    assert catalog["au-1"].ancestors("au-1_smt.a.1.a") == (
        "au-1_smt.a.1", "au-1_smt.a", "au-1_smt",
    )
    assert catalog["au-1"].ancestors("au-1_smt") == ()


def test_part_ids_detect_version_drift(catalog):
    """NIST's own example SSP references ids Rev 5 does not contain."""
    parts = catalog["au-1"].part_ids
    assert "au-1_smt.c.1" in parts
    assert "au-1_smt.b.1" not in parts
    assert "au-1_smt.b.2" not in parts


def test_withdrawn_controls_flagged(catalog):
    withdrawn = [c for c in catalog if c.withdrawn]
    assert len(withdrawn) == 182
    # Two withdrawn controls still carry a statement; the rest carry none.
    assert sorted(c.control_id for c in withdrawn if c.statement) == ["cp-10.3", "sc-19"]


# --------------------------------------------------------------------------
# SSP loader
# --------------------------------------------------------------------------

def test_fleettrack_loads(fleettrack):
    assert fleettrack.system_name == "FleetTrack"
    assert len(fleettrack.components) == 10
    assert len(fleettrack) == 17
    non_operational = sum(
        1 for c in fleettrack for s in c.statements.values()
        for b in s.by_components if not b.is_operational
    )
    assert non_operational == 6


def test_nist_example_loads(nist_example):
    assert len(nist_example.components) == 6
    assert len(nist_example) == 1
    set_params = sum(
        len(b.set_parameters) for c in nist_example
        for s in c.statements.values() for b in s.by_components
    )
    assert set_params == 8


def test_silent_statement_vs_na_declaration(nist_example):
    """Same shape - zero by-components - opposite meaning. The fuse has to tell
    these apart, so the loader must preserve the difference faithfully."""
    au1 = nist_example["au-1"]
    assert au1.statements["au-1_smt"].by_components == ()
    assert au1.statements["au-1_smt"].remarks is None
    assert au1.statements["au-1_smt.b"].by_components == ()
    assert au1.statements["au-1_smt.b"].remarks == "N/A"


def _mutated(tmp_path, mutate):
    raw = json.loads(FLEETTRACK.read_text())
    mutate(raw)
    path = tmp_path / "mutated_ssp.json"
    path.write_text(json.dumps(raw))
    return path


def test_dangling_component_uuid_rejected(tmp_path):
    def mutate(d):
        irs = d["system-security-plan"]["control-implementation"]["implemented-requirements"]
        irs[0]["statements"][0]["by-components"][0]["component-uuid"] = "00000000-dead-beef-0000-000000000000"

    with pytest.raises(SspIntegrityError) as exc:
        SspDocument.from_file(_mutated(tmp_path, mutate))
    assert "not declared in system-implementation" in str(exc.value)


def test_duplicate_control_id_rejected(tmp_path):
    def mutate(d):
        irs = d["system-security-plan"]["control-implementation"]["implemented-requirements"]
        irs.append(copy.deepcopy(irs[0]))

    with pytest.raises(SspIntegrityError):
        SspDocument.from_file(_mutated(tmp_path, mutate))


def test_duplicate_statement_id_rejected(tmp_path):
    def mutate(d):
        sts = d["system-security-plan"]["control-implementation"]["implemented-requirements"][0]["statements"]
        sts.append(copy.deepcopy(sts[0]))

    with pytest.raises(SspIntegrityError):
        SspDocument.from_file(_mutated(tmp_path, mutate))


def test_ir_level_by_components_parse(tmp_path):
    """Legal OSCAL that neither sample SSP uses. Must not be dropped."""
    def mutate(d):
        ir = d["system-security-plan"]["control-implementation"]["implemented-requirements"][0]
        ir["by-components"] = copy.deepcopy(ir["statements"][0]["by-components"])
        del ir["statements"]

    doc = SspDocument.from_file(_mutated(tmp_path, mutate))
    assert sum(len(c.by_components) for c in doc) == 1


def test_implementation_status_parses(tmp_path):
    """Optional in OSCAL, absent from both sample SSPs."""
    def mutate(d):
        bc = d["system-security-plan"]["control-implementation"]["implemented-requirements"][0]["statements"][0]["by-components"][0]
        bc["implementation-status"] = {"state": "partial"}

    doc = SspDocument.from_file(_mutated(tmp_path, mutate))
    states = [
        b.implementation_status for c in doc
        for s in c.statements.values() for b in s.by_components
    ]
    assert "partial" in states


# --------------------------------------------------------------------------
# N/A detector
# --------------------------------------------------------------------------

@pytest.mark.parametrize("remarks", [
    "N/A", "n/a", "n/a.", "N.A.", "N.A. - not collected", "Not Applicable",
    "N/A - system does not process this",
    "Not applicable: no external processors.",
])
def test_na_declarations_accepted(remarks):
    assert declares_na(remarks) is True


@pytest.mark.parametrize("remarks", [
    None, "",
    # FleetTrack's real remarks. Misreading either as N/A would lift a
    # deliberately-left gap out of the denominator and hide it.
    "KNOWN GAP - flagged explicitly, not glossed over. See chat discussion, 2026-07-16.",
    "Manual/ad hoc review only in the current skeleton - records exist and are complete.",
    "Flagged prominently: this is the single largest gap between narrative ambition and built reality.",
    # near-misses that begin with the letters "na"
    "National security exemption applies.",
    "Narrative only - no real integration exists.",
])
def test_commentary_not_mistaken_for_na(remarks):
    assert declares_na(remarks) is False


# --------------------------------------------------------------------------
# Fuse - the A3 walk
# --------------------------------------------------------------------------

def test_au1_resolves_to_the_expected_six_rows(catalog, nist_example):
    """Hand-derived from the A3 decision before the fuse was written."""
    nc = normalize_control("au-1", catalog, nist_example)
    actual = [
        (sp.smt_id, sp.status, sp.source_smt_id, len(sp.by_components), tuple(sp.superseded_sources))
        for sp in nc.sub_parts
    ]
    assert actual == [
        ("au-1_smt.a.1.a", "inherited",   "au-1_smt.a.1", 1, ("au-1_smt.a",)),
        ("au-1_smt.a.1.b", "inherited",   "au-1_smt.a.1", 1, ("au-1_smt.a",)),
        ("au-1_smt.a.2",   "implemented", "au-1_smt.a.2", 3, ()),
        ("au-1_smt.b",     "na",          "au-1_smt.b",   0, ()),
        ("au-1_smt.c.1",   "absent",      None,           0, ()),
        ("au-1_smt.c.2",   "absent",      None,           0, ()),
    ]


def test_unmatched_statements_retained_not_dropped(catalog, nist_example):
    """au-1_smt.b.1/.b.2 describe policy review - Rev 5 numbers that .c.1/.c.2.
    Version drift, and real evidence that must survive the join."""
    nc = normalize_control("au-1", catalog, nist_example)
    assert [u.smt_id for u in nc.unmatched_statements] == ["au-1_smt.b.1", "au-1_smt.b.2"]
    assert [len(u.by_components) for u in nc.unmatched_statements] == [1, 3]


def test_nearest_ancestor_wins_and_records_what_it_skipped(catalog, nist_example):
    """au-1_smt.a carries four by-components that are scored nowhere, because
    every leaf beneath it finds a nearer source. The loss must be visible."""
    nc = normalize_control("au-1", catalog, nist_example)
    leaf = next(sp for sp in nc.sub_parts if sp.smt_id == "au-1_smt.a.1.a")
    assert leaf.source_smt_id == "au-1_smt.a.1"
    assert leaf.superseded_sources == ["au-1_smt.a"]


def test_parent_level_authorship_inherits_rather_than_scoring_zero(catalog, fleettrack):
    """au-2's SSP prose is among the most specific in the file. Without
    inheritance a catalog-master row set would score it 0.0 across all leaves."""
    nc = normalize_control("au-2", catalog, fleettrack)
    assert len(nc.sub_parts) == 5
    assert all(sp.status == "inherited" for sp in nc.sub_parts)
    assert all(sp.source_smt_id == "au-2_smt" for sp in nc.sub_parts)
    assert all(len(sp.by_components) == 1 for sp in nc.sub_parts)


def test_leaf_level_authorship_exposes_real_gaps(catalog, fleettrack):
    """ac-2 addresses three leaves by name and never touches ac-2_smt, so the
    other fifteen have no ancestor to inherit from. Those are true gaps."""
    nc = normalize_control("ac-2", catalog, fleettrack)
    counts = Counter(sp.status for sp in nc.sub_parts)
    assert counts == {"implemented": 3, "absent": 15}
    implemented = {sp.smt_id for sp in nc.sub_parts if sp.status == "implemented"}
    assert implemented == {"ac-2_smt.a", "ac-2_smt.f", "ac-2_smt.g"}


def test_fleettrack_full_status_distribution(catalog, fleettrack):
    controls, report = normalize_all(catalog, fleettrack)
    assert len(controls) == 17
    counts = Counter(sp.status for nc in controls for sp in nc.sub_parts)
    assert counts == {"implemented": 8, "inherited": 54, "absent": 15}
    assert sum(len(nc.sub_parts) for nc in controls) == 77
    assert report.is_clean


def test_component_state_survives_the_fuse(catalog, fleettrack):
    """sa-9's evidence is narrative-only; the state is what the horizontal
    collapse discounts on."""
    nc = normalize_control("sa-9", catalog, fleettrack)
    states = [b.component_status for sp in nc.sub_parts for b in sp.by_components]
    assert states == ["disposition"] * 6


def test_control_absent_from_ssp_still_normalizes(catalog, fleettrack):
    """Stage 3 may pair a clause against a control the SSP never named. The
    silence is the finding, so it must not crash or vanish."""
    nc = normalize_control("sc-42", catalog, fleettrack)
    assert len(nc.sub_parts) == 2
    assert all(sp.status == "absent" and sp.source_smt_id is None for sp in nc.sub_parts)
    assert nc.unmatched_statements == []


def test_unknown_control_id_reported_not_raised(catalog, fleettrack):
    """An SSP written against another catalog revision is a real condition."""
    _, report = normalize_all(catalog, fleettrack, control_ids=["ac-3", "xx-99"])
    assert report.unknown_control_ids == ["xx-99"]


@pytest.mark.parametrize("ssp_name", ["fleettrack", "nist_example"])
def test_subpart_invariants_hold(catalog, ssp_name, request):
    """Invariants the fuse guarantees. Asserted across every row of both SSPs
    so a future change cannot quietly break the status/source contract."""
    ssp = request.getfixturevalue(ssp_name)
    controls, _ = normalize_all(catalog, ssp)
    for nc in controls:
        for sp in nc.sub_parts:
            if sp.status == "implemented":
                assert sp.source_smt_id == sp.smt_id
                assert sp.by_components
            elif sp.status == "inherited":
                assert sp.source_smt_id is not None and sp.source_smt_id != sp.smt_id
                assert sp.by_components
            elif sp.status == "na":
                assert not sp.by_components
            elif sp.status == "absent":
                assert sp.source_smt_id is None
                assert not sp.by_components
            if sp.superseded_sources:
                assert sp.status == "inherited"
            assert sp.catalog_text
