from fielddata.registry import PACKAGES
import csv

from scripts import totals


def test_committed_package_facts_and_totals_contract():
    rows = totals.read_csv(totals.FACTS)
    totals.validate(rows)

    assert len(rows) == len(PACKAGES) * 15  # 14 facts plus energy_coverage (2026-10-16)
    assert len({row["package"] for row in rows}) == 37
    assert {row["basis"] for row in rows} <= {
        "measured", "stated", "derived", "not_in_release", "open"
    }

    markdown, descriptor = totals.build()
    assert "## Headline" in markdown
    assert descriptor["released_units_total"] == 3287.0  # v1.3: li2026_evfault 99 stated vehicles and giu_ebike 1 pack (v1.2: 3,187)
    assert descriptor["zhang_evbattery_overlap"] == 49
    assert descriptor["checksum_matches_files"] + descriptor["checksum_matches_members"] == 6044  # v1.3: +2 (li2026_evfault and giu_ebike archives); v1.2: +5,915 publisher-checksum files and archive members
    assert descriptor["checksum_matches_files"] == descriptor["files_with_reference"]
    assert descriptor["checksum_matches_members"] == descriptor["members_with_reference"]
    assert descriptor["sentinels_documented_packages"] == ["flashbattery-agv", "m5bat-pbacid", "tsukuba"]  # flashbattery-agv and tsukuba from the 2026-10-04 source audit
    assert descriptor["loader_count"] == 37
    assert descriptor["charging_sessions"] == 31449 and descriptor["charging_fault_labels"] == 5680  # separate group, not systems
    assert descriptor["research_groups"] == 28  # v1.3: German International University (giu_ebike)
    assert descriptor["faults"] == 957 and descriptor["fault_batteries"] == 840  # v1.3: li2026_evfault 171 vehicle-level faults in 87 vehicles (paper Fig. 1D), giu_ebike 1 (ledger V1, V2); shenzhen_charging sessions not counted (S1)
    assert descriptor["voltage_snapshot_fault_labels"] == 2236 and descriptor["faults_unidentified_batteries"] == 0
    assert "faults_session_labels" not in descriptor and descriptor["faults_in_batteries"] == 957


def test_fault_total_matches_table3_rows():
    faults, batteries = totals.fault_totals()
    assert faults >= batteries > 0


def test_dashboard_kpi_tiles_follow_totals_json():
    import json
    from scripts import make_dashboard
    from fielddata.registry import PACKAGES
    data = json.loads((totals.ROOT / "reports" / "totals.json").read_text(encoding="utf-8"))
    tiles = make_dashboard.kpis(len(PACKAGES))
    assert [label for _, label in tiles] == ["Releases", "Systems", "Unit-years", "Energy", "Data", "Faults"]
    assert tiles[0][0] == str(len(PACKAGES)) and tiles[1][0] == f"{data['released_units_total']:,.0f}"
    assert tiles[-1][0] == f"{data['faults']:,}"
    html = (totals.ROOT / "docs" / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert make_dashboard.kpi_html(len(PACKAGES)) in html


def test_public_dashboard_has_no_ondeck_until_published():
    from scripts import make_dashboard
    html = (totals.ROOT / "docs" / "dashboard" / "index.html").read_text(encoding="utf-8")
    if not make_dashboard.ONDECK_PUBLIC:
        assert "<h2>On deck</h2>" not in html and "<summary>Screened</summary>" not in html
