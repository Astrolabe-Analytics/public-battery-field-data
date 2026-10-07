import csv

from scripts import totals


def test_committed_package_facts_and_totals_contract():
    rows = totals.read_csv(totals.FACTS)
    totals.validate(rows)

    assert len(rows) == 23 * 14
    assert len({row["package"] for row in rows}) == 23
    assert {row["basis"] for row in rows} <= {
        "measured", "stated", "derived", "not_in_release", "open"
    }

    markdown, descriptor = totals.build()
    assert "## Headline" in markdown
    assert descriptor["released_units_total"] == 3025.0  # aitio (1,027) admitted for v1.1; cloverleaf counts 3 packs from 2026-10-03
    assert descriptor["zhang_evbattery_overlap"] == 49
    assert descriptor["checksum_matches_files"] + descriptor["checksum_matches_members"] == 127
    assert descriptor["checksum_matches_files"] == descriptor["files_with_reference"]
    assert descriptor["checksum_matches_members"] == descriptor["members_with_reference"]
    assert descriptor["sentinels_documented_packages"] == ["flashbattery-agv", "m5bat-pbacid", "tsukuba"]  # flashbattery-agv and tsukuba from the 2026-10-04 source audit
    assert descriptor["loader_count"] == 23


def test_fault_total_matches_table3_rows():
    faults, batteries = totals.fault_totals()
    assert faults >= batteries > 0


def test_dashboard_totals_line_follows_totals_json():
    import json
    from scripts import make_dashboard
    from fielddata.registry import PACKAGES
    data = json.loads((totals.ROOT / "reports" / "totals.json").read_text(encoding="utf-8"))
    line = make_dashboard.totals_line(len(PACKAGES))
    assert line.startswith(f"{len(PACKAGES)} releases · {data['released_units_total']:,.0f} systems")
    assert line.endswith(f"{data['faults']:,} faults")
    html = (totals.ROOT / "docs" / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert f'<p class="totals">{line}</p>' in html
