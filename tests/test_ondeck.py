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
    assert not CANDIDATES


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
