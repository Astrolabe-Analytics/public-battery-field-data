"""Check repair cache manifests against the current producing-code fingerprint.

Reads repair unit inventories through loaders and processed-copy manifests from the SSD cache root.
Writes a package-level fingerprint summary to reports/checks/layer2_failed_releases/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fielddata
from fielddata.processed import cache_root, code_version


DEFAULT_PACKAGES = (
    "birds_cubesat",
    "bilfinger2025",
    "ku_leuven_bev",
    "tongji_rest",
    "tumftm",
    "m5bat-pbacid",
    "zhou2026",
)
CODE_KEYS = ("code_sha256", "format_version", "pandas", "pyarrow")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", nargs="+", default=DEFAULT_PACKAGES)
    args = parser.parse_args()

    current = code_version()
    rows = []
    for package in args.packages:
        systems = fielddata.standard_systems(package)
        expected = set(systems.loc[systems["standard_status"].eq("supported"), "unit"].astype(str))
        manifests = sorted((cache_root() / package).rglob("manifest.json"))
        stale = 0
        hashes: set[str] = set()
        units: set[str] = set()
        for path in manifests:
            with path.open(encoding="utf-8") as manifest_file:
                manifest = json.load(manifest_file)
            version = manifest["code_version"]
            units.add(manifest["unit"])
            hashes.add(version["code_sha256"])
            if any(version.get(key) != current.get(key) for key in CODE_KEYS):
                stale += 1
        rows.append(
            {
                "package": package,
                "manifests": len(manifests),
                "missing": len(expected - units),
                "stale": stale,
                "stored_code_sha256": ";".join(sorted(hashes)),
                "current_code_sha256": current["code_sha256"],
            }
        )

    output = ROOT / "reports/checks/layer2_failed_releases/code_fingerprint_check.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"{row['package']}: manifests={row['manifests']}, missing={row['missing']}, "
            f"stale={row['stale']}, current_code_sha256={row['current_code_sha256']}"
        )
    if any(row["stale"] or row["missing"] or not row["manifests"] for row in rows):
        raise SystemExit("Missing or stale repair manifests. See code_fingerprint_check.csv.")


if __name__ == "__main__":
    main()
