"""On-deck candidates (v1.2 intake phase 1): registry entries, download routes and reference checksums, offline."""
import csv

from fielddata import fetch
from fielddata.registry import CANDIDATES, PACKAGES

ONDECK = ["stanford_ev", "cell_to_pack", "rise_conbat", "birds_cubesat", "ved", "shenzhen_charging", "tum_id3_2022",
          "brazil_star", "tongji_rest", "beijing_ev"]


def test_ondeck_were_admitted_in_v12():
    for name in ONDECK:
        assert name in PACKAGES and name not in CANDIDATES, name
        assert "status" not in PACKAGES[name]
    # v1.3 (2026-11-24): li2026_evfault and giu_ebike admitted; lin_agv stays a candidate until its paper is out
    assert set(CANDIDATES) == {"rwth_commercial_fleet", "cornejo_stabl", "lin_agv"}


def test_routes():
    kinds = {name: fetch.plan_package(name, to="data").source_kind for name in ONDECK}
    assert kinds["stanford_ev"] == "sdr"
    assert kinds["birds_cubesat"] == kinds["shenzhen_charging"] == kinds["beijing_ev"] == "mendeley"
    assert kinds["ved"] == "github"
    assert kinds["tum_id3_2022"] == "tumdataserv"
    assert {kinds[n] for n in ("cell_to_pack", "rise_conbat", "brazil_star", "tongji_rest")} == {"zenodo"}


def test_mendeley_and_sdr_ids():
    assert fetch._mendeley_id_version("https://doi.org/10.17632/c7gg94tmvz.3") == ("c7gg94tmvz", "3")
    assert fetch._mendeley_id_version("https://data.mendeley.com/datasets/8kp25ycf63/1") == ("8kp25ycf63", "1")


def test_stanford_is_loader_only():
    assert "no converted or derived data files" in PACKAGES["stanford_ev"]["derived_outputs"]


def test_publisher_checksums_recorded():
    with fetch.CHECKSUMS.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["package"] in ONDECK]
    by_package = {}
    for row in rows:
        by_package.setdefault(row["package"], []).append(row)
    assert len(by_package["stanford_ev"]) == 5516
    assert len(by_package["cell_to_pack"]) == 20
    for name in ("rise_conbat", "birds_cubesat", "shenzhen_charging", "brazil_star", "tongji_rest", "cell_to_pack"):
        assert all(row["algorithm"] in ("md5", "sha256") and row["publisher_value"] for row in by_package[name]), name


def test_fei_bus_uses_mendeley_route_and_bilfinger_stays_manual():
    # fei_bus moved to the Mendeley route on 2026-10-16 (held files match); the bilfinger zips stay manual
    assert fetch.plan_package("fei_bus", to="data").source_kind == "mendeley"
    for name in ("bilfinger2024", "bilfinger2025", "bilfinger2026"):
        assert fetch.plan_package(name, to="data").source_kind == "manual"


def test_new_candidates_are_metadata_only_and_not_admitted():
    for name in ("rwth_commercial_fleet", "cornejo_stabl"):
        entry = CANDIDATES[name]
        assert name not in PACKAGES
        assert entry["slug"] == name and entry["status"] == "on deck"
        assert entry["license_source"] and entry["checksum_source"]
        assert entry["data_files"] and entry["catalog"]
        assert "No data downloaded" in (
            entry["catalog"].get("screening_notes", "") + entry["catalog"].get("checksum_note", "")
        )
    rwth = CANDIDATES["rwth_commercial_fleet"]
    assert rwth["license"] == "not confirmed"
    assert "not independently confirmed" in rwth["catalog"]["license_note"]
    assert "do not redistribute" in rwth["derived_outputs"]
    cornejo = CANDIDATES["cornejo_stabl"]
    assert cornejo["license"] == "MIT"
    assert cornejo["catalog"]["source_files"] == [{
        "name": cornejo["data_files"][0], "bytes": 19516459,
        "checksum": "md5:3c8b7980e24692039e9f61f83e4d780f",
    }]


def test_ondeck_dashboard_and_roster_include_new_candidates():
    from scripts import make_dashboard
    html = make_dashboard.ondeck_html()
    # private.html is left out of the public export (scripts/export_release.py), so its checks run only where it exists
    private_path = make_dashboard.OUT / "private.html"
    private = private_path.read_text(encoding="utf-8") if private_path.exists() else None
    roster = (make_dashboard.ROOT / "SCREENING.md").read_text(encoding="utf-8")
    for name in ("rwth_commercial_fleet", "cornejo_stabl"):
        assert name in html and name in roster
        assert private is None or name in private
    assert html.count("not downloaded") == len(CANDIDATES)
    assert "not confirmed" in html
    assert private is None or "not counted in the totals" in private
