"""Rebuild and extend layer-2 processed copies with per-release checkpoints.

Reads released data only through loaders and processed checksum verification.
Writes progress and verification tables under reports/checks/layer2_extension.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import pandas as pd
import pandas.testing as pdt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fielddata
from fielddata import processed
from fielddata.registry import PACKAGES as REGISTRY_PACKAGES

OUT = ROOT / "reports" / "checks" / "layer2_extension"
COORD = Path.home() / "Desktop" / "agent-coord" / "A.md"
PILOT_AND_FAULT = ["cao", "schaeffer", "ppl", "xie", "zhang2023", "evbattery", "aitio"]


def _save(frame: pd.DataFrame, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def _coord_update(rows: pd.DataFrame):
    text = COORD.read_text(encoding="utf-8") if COORD.exists() else "# A\n"
    text = re.sub(r"^Current phase:.*$",
                  "Current phase: building and verifying each release from smallest to largest.",
                  text, count=1, flags=re.MULTILINE)
    before = text.partition("Release checkpoints:")[0]
    checkpoints = [
        f"- {row.package}: standard={row.standard_done}, processed={row.processed_done}, "
        f"rows={row.rows}, bytes={row.size_bytes}, verified={row.verified} ({row.checkpoint})"
        for row in rows.itertuples(index=False)
    ]
    text = before.rstrip() + "\n\nRelease checkpoints:\n" + "\n".join(checkpoints) + "\n"
    COORD.write_text(text, encoding="utf-8", newline="\n")


def _status_update(rows: pd.DataFrame):
    path = ROOT / "STATUS.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Layer 2 rebuild and extension, 2026-10-18"
    before = text.partition(marker)[0]
    lines = [
        marker,
        "",
        "This table is generated incrementally by `python scripts/checks/layer2_extension.py`. Rows and Parquet size "
        "are read from the build summary and on-disk copy; verified means every supported unit manifest and output "
        "part passed validation and one loader-to-copy spot check matched.",
        "",
        "| Release | Standard view done | Processed copy done | Rows | Size (bytes) | Verified |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in rows.itertuples(index=False):
        lines.append(f"| {row.package} | {row.standard_done} | {row.processed_done} | {row.rows} | "
                     f"{row.size_bytes} | {row.verified} |")
    path.write_text(before.rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _source_bytes(package: str) -> int:
    try:
        return sum(path.stat().st_size for path in processed.source_paths(package))
    except (OSError, ValueError):
        return -1


def _parquet_bytes(package: str) -> int:
    root = processed.cache_root() / package
    return sum(path.stat().st_size for path in root.rglob("*.parquet")) if root.exists() else 0


def _spot_check(package: str, unit: str):
    if package == "stanford_ev":
        expected = next(fielddata.iter_standard(package, unit, signal="V_pack_bms"))
        manifest = processed.validate(package, unit)
        first_part = manifest["parts"][0]
        expected = expected.loc[expected["time"].dt.strftime("%Y-%m") == first_part["month"]]
        if len(expected) != first_part["rows"]:
            raise AssertionError(f"{package} {unit}: loader and first processed partition row counts differ")
        actual = pd.read_parquet(processed.unit_directory(package, unit) / first_part["file"])
        index = sorted({0, min(9, len(expected) - 1), len(expected) // 2, len(expected) - 1})
        pdt.assert_frame_equal(actual.iloc[index].reset_index(drop=True),
                               expected.iloc[index].reset_index(drop=True),
                               check_dtype=False)
        return len(index)
    expected = fielddata.standard(package, unit)
    if not isinstance(expected, pd.DataFrame) or expected.empty:
        raise ValueError(f"{package} {unit}: no standard rows for spot check")
    actual = processed.load(package, unit)
    if len(expected) != len(actual):
        raise AssertionError(f"{package} {unit}: row mismatch in spot check")
    index = sorted({0, min(9, len(expected) - 1), len(expected) // 2, len(expected) - 1})
    pdt.assert_frame_equal(actual.iloc[index].reset_index(drop=True),
                           expected.iloc[index].reset_index(drop=True),
                           check_dtype=False)
    return len(index)


def _run_release(package: str) -> dict:
    row = {"package": package, "standard_done": "no", "processed_done": "no", "rows": 0,
           "size_bytes": 0, "verified": "no", "checkpoint": ""}
    try:
        systems = fielddata.standard_systems(package)
    except Exception as error:
        row["checkpoint"] = f"blocked standard inventory: {error}"
        return row
    row["standard_done"] = "yes"
    supported = systems[systems["standard_status"] == "supported"]
    if supported.empty:
        row["checkpoint"] = "no supported units"
        return row
    try:
        summary = processed.build(package)
    except Exception as error:
        row["checkpoint"] = f"build failed: {error}"
        return row
    ok = summary[summary["status"].isin(["built", "reused"])]
    row["processed_done"] = "yes" if len(ok) == len(supported) else "partial"
    row["rows"] = int(ok["rows"].sum())
    row["size_bytes"] = _parquet_bytes(package)
    try:
        sources = processed.verify_sources(package)
        version = processed.code_version()
        for unit in supported["unit"]:
            processed.validate(package, str(unit), sources=sources, version=version)
        spot_unit = str(supported["unit"].iloc[0])
        spots = _spot_check(package, spot_unit)
    except Exception as error:
        row["checkpoint"] = f"verification failed: {error}"
        return row
    row["verified"] = "yes"
    row["checkpoint"] = f"validated all supported units; spot rows={spots} on {spot_unit}"
    return row


def run(packages=None):
    OUT.mkdir(parents=True, exist_ok=True)
    status_path = OUT / "release_status.csv"
    all_packages = [package for package in REGISTRY_PACKAGES]
    remaining = [package for package in all_packages if package not in PILOT_AND_FAULT]
    ordered_remaining = sorted(remaining, key=lambda package: _source_bytes(package))
    sequence = [*PILOT_AND_FAULT, *ordered_remaining]
    selected = sequence if packages is None else packages
    unknown = set(selected) - set(sequence)
    if unknown:
        raise ValueError(f"unknown release(s): {sorted(unknown)}")
    rows_by_package = {}
    if packages is not None and status_path.exists():
        previous = pd.read_csv(status_path, dtype=str).fillna("")
        rows_by_package = {row["package"]: row for row in previous.to_dict("records")}
    for package in selected:
        row = _run_release(package)
        rows_by_package[package] = row
        current = pd.DataFrame([rows_by_package[name] for name in sequence
                                if name in rows_by_package])
        _save(current, "release_status.csv")
        _coord_update(current)
        _status_update(current)
    with (OUT / "sequence.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump({"pilot_and_fault": PILOT_AND_FAULT, "remaining_small_to_large": ordered_remaining}, handle, indent=2)
        handle.write("\n")
    (OUT / "README.md").write_text(
        "# Layer 2 rebuild and extension check\n\n"
        "The release status table is checkpointed after each package. The check builds or reuses every supported "
        "unit, verifies source files against committed checksums or holding snapshots, validates manifest and "
        "Parquet hashes, and compares selected rows from the standard loader with the processed copy.\n\n"
        "Reproduce with `python scripts/checks/layer2_extension.py` (set `LIBARCHIVE` to the installed DLL for "
        "Xie and Changan on Windows). To rerun selected releases without discarding other checkpoints, add "
        "`--packages <release> [<release> ...]`. Results are in `release_status.csv`; `sequence.json` records the "
        "processing order. Blocked or unverified releases are stated in the CSV rather than reported as successful.\n",
        encoding="utf-8", newline="\n")
    current = pd.DataFrame([rows_by_package[name] for name in sequence if name in rows_by_package])
    print(current.to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", nargs="+", choices=REGISTRY_PACKAGES,
                        help="rebuild and checkpoint only the selected releases")
    run(parser.parse_args().packages)
