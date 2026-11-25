"""Check the new on-deck entries against public metadata, without downloading data.

Reads the registry, RWTH's deposited DOI metadata, Zenodo's record metadata and
the author's versioned GitHub file tree. Writes reports/checks/ondeck_metadata.json.
No archive, telemetry, code ZIP, physical-cell census or collection totals are read.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fielddata.registry import CANDIDATES, PACKAGES


def metadata(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "public-battery-field-data-metadata-check"})
    with urlopen(request, timeout=90) as response:
        return json.load(response)


def check(document: dict) -> list[str]:
    errors = []
    for name in ("rwth_commercial_fleet", "cornejo_stabl"):
        if name not in CANDIDATES or name in PACKAGES:
            errors.append(f"{name}: must be on deck, not admitted")
    rwth = CANDIDATES["rwth_commercial_fleet"]
    if rwth["license"] != "not confirmed":
        errors.append("RWTH license must remain unconfirmed pending publisher evidence")
    if "Battery Electric Vehicles in Commercial Fleets" not in document["rwth"]["title"]:
        errors.append("RWTH publisher title differs from the intended dataset")
    cornejo = CANDIDATES["cornejo_stabl"]
    source = document["cornejo"]
    if (source["title"], source["version"], source["license"]) != ("BatteryRecursiveGPs.jl", "v0.1.0", "mit-license"):
        errors.append("Cornejo publisher title, version or license differs")
    if source["files"] != cornejo["catalog"]["source_files"]:
        errors.append("Cornejo publisher filenames, sizes or checksums differ from registry")
    paths = {row["path"] for row in source["author_data_file_listing"]}
    required = {
        "yuasa/data/cycles/cell_voltages.csv",
        "yuasa/data/validation/combined_log_20260131_200948.parquet",
        "yuasa/data/validation/combined_log_20260201_181000.parquet",
        "yuasa/data/validation/reference_ocv.csv",
    }
    if not required <= paths:
        errors.append("Author versioned file tree lacks expected cycle or validation filenames")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saved", action="store_true", help="Check the saved metadata without network requests.")
    args = parser.parse_args()
    target = ROOT / "reports" / "checks" / "ondeck_metadata.json"
    if args.saved:
        document = json.loads(target.read_text(encoding="utf-8"))
    else:
        rwth_url = "https://api.datacite.org/dois/10.18154/RWTH-2024-01907"
        zenodo_url = "https://zenodo.org/api/records/22281621"
        tree_url = "https://api.github.com/repos/martincornejo/BatteryRecursiveGPs.jl/git/trees/v0.1.0?recursive=1"
        rwth = metadata(rwth_url)["data"]["attributes"]
        zenodo = metadata(zenodo_url)
        tree = metadata(tree_url)
        if tree.get("truncated"):
            raise ValueError("Author file tree is truncated")
        abstract = " ".join(row["description"] for row in rwth["descriptions"]
                            if row["descriptionType"] == "Abstract")
        if not all(text in abstract for text in ("for nine vehicles", "2014 to 2016", "chassis dynamometer")):
            raise ValueError("RWTH publisher abstract no longer supports the recorded fleet context")
        document = {
            "scope": "Publisher/author metadata only. No data downloaded or measured.",
            "rwth": {
                "metadata_source": rwth_url,
                "publisher_record": "https://publications.rwth-aachen.de/record/979878",
                "title": rwth["titles"][0]["title"],
                "abstract_claims": {"vehicles": 9, "field_test_period": "2014 to 2016",
                                    "capacity_test_method": "chassis dynamometer"},
                "rights_in_doi_deposit": rwth.get("rightsList", []),
                "license_status": "unconfirmed; intake supplied CC BY 4.0, not substantiated",
                "file_listing_basis": "Indexed publisher files page, direct access blocked by browser challenge",
                "files": [{"name": "Electric_Vehicle_and_Battery_Data.zip",
                           "display_size": "82.0 MB", "bytes": None, "checksum": None}],
            },
            "cornejo": {
                "metadata_source": zenodo_url, "title": zenodo["metadata"]["title"],
                "version": zenodo["metadata"]["version"],
                "license": zenodo["metadata"]["license"]["id"],
                "concept_doi": zenodo["conceptdoi"], "version_doi": zenodo["doi"],
                "files": [{"name": row["key"], "bytes": row["size"], "checksum": row["checksum"]}
                          for row in zenodo["files"]],
                "author_file_listing_source": tree_url,
                "author_data_file_listing": [
                    {"path": row["path"], "bytes": row["size"]}
                    for row in tree["tree"]
                    if row["type"] == "blob" and row["path"].startswith("yuasa/data/")
                ],
            },
        }
    errors = check(document)
    document["check_errors"] = errors
    if not args.saved:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    if errors:
        raise SystemExit("\n".join(errors))
    print("On-deck registry matches saved publisher metadata. RWTH license remains unconfirmed."
          if args.saved else
          "On-deck registry matches fetched publisher metadata. RWTH license remains unconfirmed.")


if __name__ == "__main__":
    main()
