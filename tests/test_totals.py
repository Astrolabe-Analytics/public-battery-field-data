import csv

from scripts import totals


def test_committed_package_facts_and_totals_contract():
    rows = totals.read_csv(totals.FACTS)
    totals.validate(rows)

    assert len(rows) == 22 * 14
    assert len({row["package"] for row in rows}) == 22
    assert {row["basis"] for row in rows} <= {
        "measured", "stated", "derived", "not_in_release", "open"
    }

    markdown, descriptor = totals.build()
    assert "## Headline" in markdown
    assert descriptor["released_units_total"] == 1998.0  # cloverleaf counts 3 packs from 2026-10-03
    assert descriptor["zhang_evbattery_overlap"] == 49
    assert descriptor["checksum_matches_files"] + descriptor["checksum_matches_members"] == 127
    assert descriptor["checksum_matches_files"] == descriptor["files_with_reference"]
    assert descriptor["checksum_matches_members"] == descriptor["members_with_reference"]
    assert descriptor["sentinels_documented_packages"] == ["flashbattery-agv", "m5bat-pbacid", "tsukuba"]  # flashbattery-agv and tsukuba from the 2026-10-04 source audit
    assert descriptor["loader_count"] == 22
