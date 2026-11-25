"""Publisher checksums for the v1.3 intake (lin_agv, li2026_evfault, giu_ebike), from their held Zenodo records.

What it does: reads each release's record/zenodo_record.json (the Zenodo API record, retrieved 2026-11-19 with the
download) and adds one row per published file to fielddata/reference_checksums.csv, with the MD5 Zenodo publishes.
Rows already present for a package are replaced, so a rerun gives the same file. It reads no data files.
Reads: <data root>/<release>/record/zenodo_record.json. Writes: fielddata/reference_checksums.csv.

Run: python scripts/checks/v13_reference_checksums.py
Then: python -m fielddata.verify lin_agv li2026_evfault giu_ebike
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata.loaders._base import directory  # noqa: E402
from fielddata.registry import metadata  # noqa: E402

PACKAGES = ["lin_agv", "li2026_evfault", "giu_ebike"]
TABLE = ROOT / "fielddata" / "reference_checksums.csv"


def rows_for(package: str) -> list[dict]:
    entry = metadata(package)
    record_path = directory(package).parent / "record" / "zenodo_record.json"  # the record, not data
    record = json.loads(record_path.read_text(encoding="utf-8"))
    out = []
    for item in sorted(record["files"], key=lambda f: f["key"]):
        algorithm, value = item["checksum"].split(":", 1)
        out.append({"package": package, "file": f"data/{item['key']}", "algorithm": algorithm, "publisher_value": value,
                    "bytes_when_recorded": item["size"], "publisher_url": entry["urls"]["data"],
                    "provenance": f"zenodo API record {record['id']} (held in record/zenodo_record.json), retrieved 2026-11-19"})
    return out


def main() -> None:
    with TABLE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        kept = [row for row in reader if row["package"] not in PACKAGES]
    new = [row for package in PACKAGES for row in rows_for(package)]
    with TABLE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept + new)
    for package in PACKAGES:
        print(package, sum(row["package"] == package for row in new), "publisher checksums")


if __name__ == "__main__":
    main()
