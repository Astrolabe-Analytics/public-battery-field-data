"""Record reference checksums for the on-deck candidates in fielddata/reference_checksums.csv.

What it does: for each on-deck candidate, lists the record's files through the same resolver `python -m fielddata.fetch`
uses (Zenodo, Mendeley Data and Stanford Digital Repository APIs publish an MD5 or SHA-256 per file) and adds one row
per file with the publisher's value. Where the host publishes no checksum (GitHub, or a manual download) and the file is
already downloaded, it adds our own SHA-256 marked "computed on fetch". Rows already in the CSV are left alone, so the
script can be rerun after more downloads finish.

Reads: the record APIs, and the downloaded files under the data folder for hosts without checksums.
Writes: fielddata/reference_checksums.csv (appends rows only).

Run:
    python scripts/checks/ondeck_reference_checksums.py [package ...]
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata import fetch  # noqa: E402
from fielddata.registry import CANDIDATES  # noqa: E402

ONDECK = [name for name, entry in CANDIDATES.items() if entry.get("status") == "on deck"]
FIELDS = ["package", "file", "algorithm", "publisher_value", "bytes_when_recorded", "publisher_url", "provenance"]


def rows_for(package: str, today: str) -> list[dict[str, str]]:
    plan = fetch.plan_package(package)
    if not plan.automatic:
        return []
    rows = []
    for remote in fetch.resolve_files(plan):
        name = f"data/{remote.name}"
        if remote.api_checksum and ":" in remote.api_checksum:
            algorithm, value = remote.api_checksum.split(":", 1)
            provenance = f"{plan.source_kind} API file listing, retrieved {today}"
        else:
            local = plan.destination / Path(*PurePosixPath(remote.name).parts)
            if not local.exists():
                continue
            algorithm, value = "sha256", fetch._hash(local, "sha256")
            provenance = f"computed on fetch, {today}; the host publishes no checksum"
        rows.append({"package": package, "file": name, "algorithm": algorithm, "publisher_value": value,
                     "bytes_when_recorded": str(remote.size or ""), "publisher_url": plan.record_url, "provenance": provenance})
    return rows


def main(packages: list[str]) -> int:
    with fetch.CHECKSUMS.open(newline="", encoding="utf-8") as handle:
        existing = {(row["package"], row["file"]) for row in csv.DictReader(handle)}
    today = date.today().isoformat()
    added = 0
    with fetch.CHECKSUMS.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        for package in packages or ONDECK:
            new = [row for row in rows_for(package, today) if (row["package"], row["file"]) not in existing]
            writer.writerows(new)
            added += len(new)
            print(f"{package}: {len(new)} row(s) added")
    print(f"total added: {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
