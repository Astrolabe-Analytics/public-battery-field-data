"""Repair Layer 2 failures without rebuilding releases that already verified.

Reads held source files through loaders and hashes missing-checksum sources in place.
Writes held checksums, progress, release diagnostics and processed copies on the SSD.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shutil
import sys
import time

import pandas as pd
import pandas.testing as pdt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fielddata
from fielddata import processed
from fielddata.registry import metadata

OUT = ROOT / "reports" / "checks" / "layer2_failed_releases"
COORD = Path.home() / "Desktop" / "agent-coord" / "A.md"
RELEASES = [
    "cell_to_pack",
    "rise_conbat",
    "birds_cubesat",
    "bilfinger2025",
    "ku_leuven_bev",
    "tongji_rest",
    "tumftm",
    "m5bat-pbacid",
    "zhou2026",
    "changan",
]
ACTIVE_RELEASES = RELEASES[:-1]
CHANGAN_PAUSE = (
    "Changan: 7-Zip fallback and sensor-token fix done; rebuild paused at 23 of 300 vehicles, "
    "resume only when a task needs Changan."
)


def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _committed_hash(package: str, file: str, references: list[dict[str, str]],
                    snapshots: list[dict[str, str]]) -> bool:
    reference = next((row for row in references
                      if row["package"] == package and row["file"] == file), {})
    if reference.get("algorithm") in {"md5", "sha1", "sha256", "sha512"} and reference.get("publisher_value"):
        return True
    own_sha = metadata(package).get("own_sha256", {})
    if file.removeprefix("data/") in own_sha:
        return True
    snapshot = next((row for row in snapshots
                     if row["package"] == package and row["file"] == file), {})
    if any(token.split(":", 1)[0] in {"md5", "sha1", "sha256", "sha512"}
           for token in snapshot.get("measured", "").split() if ":" in token):
        return True
    return snapshot.get("algorithm") in {"md5", "sha1", "sha256", "sha512"} and bool(snapshot.get("measured"))


def _ensure_held_checksums(package: str) -> list[dict[str, object]]:
    reference_path = ROOT / "fielddata" / "reference_checksums.csv"
    verify_path = ROOT / "reports" / "verify_log.csv"
    verify_fields, snapshots = _rows(verify_path)
    _, references = _rows(reference_path)
    created = []
    data_root = processed.cache_root().parent
    data_directory = data_root / metadata(package)["data_directory"]
    for path in processed.source_paths(package):
        file = "data/" + path.relative_to(data_directory).as_posix()
        if _committed_hash(package, file, references, snapshots):
            continue
        before = path.stat()
        start = time.perf_counter()
        sha256 = processed._hashes(path)["sha256"]
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"{package} {file}: held file changed while hashing")
        row = {
            "package": package,
            "file": file,
            "algorithm": "sha256",
            "expected": "",
            "measured": f"sha256:{sha256}",
            "bytes": str(after.st_size),
            "status": "held-file snapshot; hashed locally without re-download",
            "seconds": f"{time.perf_counter() - start:.3f}",
        }
        with verify_path.open("a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=verify_fields, lineterminator="\n").writerow(row)
        snapshots.append(row)
        created.append({**row, "sha256": sha256})
    return created


def _no_build_line(package: str) -> str:
    systems = fielddata.standard_systems(package)
    supported = systems[systems["standard_status"] == "supported"]
    if not supported.empty:
        raise AssertionError(f"{package}: expected no supported units, found {len(supported)}")
    reasons = sorted(set(systems["standard_reason"].dropna().astype(str)) - {""})
    return f"no build: {len(systems)} entries; " + ("; ".join(reasons) if reasons else "no supported unit records")


def _verify_tongji_converted_inputs() -> None:
    from fielddata.loaders import tongji_rest

    _, conversion = _rows(ROOT / "reports" / "candidates" / "tongji_rest" / "pickle_conversion.csv")
    references = {row["output"]: row for row in conversion}
    converted_root = (data_root() / metadata("tongji_rest")["data_directory"]).parent / "converted"
    paths = [path for unit in tongji_rest.FIELD for kind in ("charge", "rest")
             for path in tongji_rest.segments(unit, kind)]
    names = {path.relative_to(converted_root).as_posix() for path in paths}
    if names != set(references):
        raise ValueError("tongji_rest: held converted inputs differ from the conversion manifest")
    verified = []
    for path in paths:
        name = path.relative_to(converted_root).as_posix()
        reference = references[name]
        before = path.stat()
        if reference["error"] or before.st_size != int(reference["output_bytes"]):
            raise ValueError(f"tongji_rest {name}: conversion error or size mismatch")
        sha256 = processed._hashes(path)["sha256"]
        after = path.stat()
        if sha256 != reference["output_sha256"]:
            raise ValueError(f"tongji_rest {name}: converted input checksum mismatch")
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"tongji_rest {name}: converted input changed while hashing")
        verified.append({"package": "tongji_rest", "file": "converted/" + name,
                         "bytes": after.st_size, "sha256": sha256,
                         "reference": "committed pickle conversion manifest"})
    _save_package_rows("converted_source_verification.csv", "tongji_rest", verified)
    print("tongji_rest: converted loader inputs match committed sizes and SHA-256 checksums", flush=True)


def _timestamp_issues(package: str, units: list[str]) -> int:
    if package not in {"ku_leuven_bev", "tongji_rest"}:
        return 0
    source_column = "source__Timestamp_raw" if package == "ku_leuven_bev" else "source__reqDate"
    identifiers = ["session"] if package == "ku_leuven_bev" else ["source__segment"]
    issues = []
    for unit in units:
        manifest = processed._read_manifest(package, unit)
        for part in manifest["parts"]:
            if part["month"] != "undated":
                continue
            path = processed.unit_directory(package, unit) / part["file"]
            columns = ["time", source_column, *identifiers]
            frame = pd.read_parquet(path, columns=columns)
            invalid = frame[frame["time"].isna()]
            grouped = invalid.groupby([*identifiers, source_column], dropna=False).size()
            for keys, count in grouped.items():
                if not isinstance(keys, tuple):
                    keys = (keys,)
                record = dict(zip(identifiers, keys[:len(identifiers)]))
                raw_value = keys[-1]
                issues.append({
                    "package": package,
                    "unit": unit,
                    **record,
                    "source_timestamp_value": "<null>" if pd.isna(raw_value) else str(raw_value),
                    "rows_preserved": int(count),
                    "partition": part["month"],
                })
    if issues:
        path = OUT / "timestamp_issues.csv"
        old = pd.read_csv(path) if path.exists() else pd.DataFrame()
        old = old[~old["package"].eq(package)] if not old.empty else old
        pd.concat([old, pd.DataFrame(issues)], ignore_index=True).to_csv(
            path, index=False, lineterminator="\n")
    return sum(row["rows_preserved"] for row in issues)


def _spot_check(package: str, unit: str) -> dict[str, object]:
    if package in {"m5bat-pbacid", "tumftm"}:
        if package == "m5bat-pbacid":
            from fielddata.loaders import m5bat_pbacid
            batches = m5bat_pbacid.iter_load(source=unit.rsplit(":", 1)[1], chunksize=4096)
        else:
            from fielddata.loaders import tumftm
            batches = tumftm.iter_load(unit, chunksize=4096)
        try:
            expected = fielddata.standardize(package, unit, next(batches))
        finally:
            batches.close()
        scope = "first loader batch"
    elif package == "zhou2026":
        expected = fielddata.standardize(package, unit, fielddata.load(package, unit=unit, part=0))
        scope = "first loader partition"
    else:
        expected = fielddata.standard(package, unit)
        scope = "whole loader unit"
    manifest = processed._read_manifest(package, unit)
    if scope == "whole loader unit" and len(expected) != manifest["rows"]:
        raise AssertionError(f"{package} {unit}: loader and processed row counts differ")
    if expected.empty or len(expected) > manifest["rows"]:
        raise AssertionError(f"{package} {unit}: invalid loader sample length")
    indices = sorted({0, min(9, len(expected) - 1), len(expected) // 2, len(expected) - 1})
    actual_rows = []
    offset = 0
    for part in manifest["parts"]:
        selected = [index for index in indices if offset <= index < offset + part["rows"]]
        if selected:
            frame = pd.read_parquet(processed.unit_directory(package, unit) / part["file"])
            sample = frame.iloc[[index - offset for index in selected]].copy()
            for column in part.get("attrs", {}).get("source_value_encodings", {}):
                sample[column] = sample[column].map(
                    lambda value: json.loads(value)["value"] if pd.notna(value) else None
                )
            actual_rows.append(sample)
        offset += part["rows"]
    actual = pd.concat(actual_rows, ignore_index=True)
    pdt.assert_frame_equal(
        actual, expected.iloc[indices].reset_index(drop=True), check_dtype=False
    )
    return {"package": package, "unit": unit, "scope": scope,
            "loader_rows": len(expected), "processed_rows": manifest["rows"],
            "spot_rows": len(indices), "result": "matched"}


def _save_package_rows(name: str, package: str, rows: list[dict]) -> None:
    path = OUT / name
    previous = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if not previous.empty:
        previous = previous[~previous["package"].eq(package)]
    pd.concat([previous, pd.DataFrame(rows)], ignore_index=True).to_csv(
        path, index=False, lineterminator="\n"
    )


def _verify_loader_row_counts(package: str) -> None:
    if package not in {"tumftm", "m5bat-pbacid", "zhou2026"}:
        return
    systems = fielddata.standard_systems(package)
    rows = []
    for system in systems[systems["standard_status"].eq("supported")].itertuples():
        if package == "m5bat-pbacid":
            from fielddata.loaders import m5bat_pbacid
            loader_rows = sum(len(batch) for batch in m5bat_pbacid.iter_load(
                source=system.unit.rsplit(":", 1)[1], columns=[], chunksize=1_000_000
            ))
            basis = "full raw loader stream, measurement columns excluded"
        else:
            loader_rows = int(system.rows)
            basis = "raw loader systems inventory"
        processed_rows = processed._read_manifest(package, system.unit)["rows"]
        if loader_rows != processed_rows:
            raise AssertionError(f"{package} {system.unit}: loader and processed row counts differ")
        rows.append({"package": package, "unit": system.unit, "loader_rows": loader_rows,
                     "processed_rows": processed_rows, "basis": basis, "result": "matched"})
    _save_package_rows("loader_row_counts.csv", package, rows)
    print(f"{package}: full loader row counts match processed manifests", flush=True)


def _probe_birds() -> None:
    rows = []
    for unit in fielddata.systems("birds_cubesat")["unit"].astype(str):
        frame = fielddata.load("birds_cubesat", unit=unit)
        for column in frame.select_dtypes(include="object").columns:
            counts = frame[column].dropna().map(lambda value: type(value).__name__).value_counts()
            if len(counts) > 1:
                examples = {
                    kind: repr(frame.loc[frame[column].map(lambda value: type(value).__name__).eq(kind),
                                        column].iloc[0])
                    for kind in counts.index
                }
                rows.append({
                    "unit": unit,
                    "column": column,
                    "types": json.dumps(counts.to_dict(), sort_keys=True),
                    "examples": json.dumps(examples, sort_keys=True),
                })
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=["unit", "column", "types", "examples"]).to_csv(
        OUT / "birds_mixed_types.csv", index=False, lineterminator="\n")
    print(f"Birds CubeSat mixed object columns: {len(rows)}", flush=True)


def _build(package: str, new_checksums: list[dict[str, object]]) -> tuple[str, int, int]:
    systems = fielddata.standard_systems(package)
    supported = systems[systems["standard_status"] == "supported"]
    if supported.empty:
        return _no_build_line(package), 0, 0
    if package == "tongji_rest":
        _verify_tongji_converted_inputs()
    result = processed.build(package, chunksize=100_000 if package == "m5bat-pbacid" else 250_000)
    completed = result[result["status"].isin(["built", "reused"])]
    if len(completed) != len(supported):
        failures = result[~result["status"].isin(["built", "reused"])]
        raise RuntimeError(f"{package}: incomplete units: {failures.to_dict('records')[:8]}")
    sources = processed._read_manifest(package, str(completed["unit"].iloc[0]))["sources"]
    _save_package_rows("source_verification.csv", package,
                       [{"package": package, **source} for source in sources])
    version = processed.code_version()
    spots = []
    for unit in completed["unit"]:
        processed.validate(package, str(unit), sources=sources, version=version)
        spots.append(_spot_check(package, str(unit)))
    _save_package_rows("loader_spot_checks.csv", package, spots)
    _verify_loader_row_counts(package)
    invalid_time_rows = _timestamp_issues(package, [str(unit) for unit in completed["unit"]])
    rows = int(completed["rows"].sum())
    size = sum(path.stat().st_size for path in processed.cache_root().joinpath(package).rglob("*.parquet"))
    detail = (f"built or reused and validated {len(completed)} units with loader spot checks, rows={rows}, bytes={size}; "
              f"new held checksums={len(new_checksums)}; invalid timestamps preserved={invalid_time_rows}")
    return detail, rows, size


def _write_progress(results: list[dict[str, object]], before: dict[str, int]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(results)
    temporary = OUT / "progress.csv.tmp"
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(OUT / "progress.csv")
    free_after = shutil.disk_usage(processed.cache_root().parent).free
    status = [
        "## Layer 2 failed-release repairs, 2026-10-20",
        "",
        f"Free SSD space before: {before['free_bytes']} bytes. Free SSD space after: {free_after} bytes.",
        "",
        "Each verified result records fresh held-input size/checksum checks, processed-part hashes and raw "
        "row counts, and loader-to-copy spot checks under the code fingerprint at that release's check. "
        "Run the fingerprint check after the full repair run to detect any later code changes. "
        "The earlier verified releases were not rebuilt. Changan remains paused and its partial SSD "
        "output is not counted as verified or committed.",
        "",
        "| Progress | Release | Result | Rows | Processed bytes | Detail |",
        "|---:|---|---|---:|---:|---|",
    ]
    for row in results:
        status.append(
            f"| {row['progress']} | {row['release']} | {row['result']} | "
            f"{row['rows']} | {row['processed_bytes']} | {row['detail']} |"
        )
    path = ROOT / "STATUS.md"
    text = path.read_text(encoding="utf-8")
    for row in results:
        if row["result"] != "verified":
            continue
        old_lines = text.splitlines()
        prefix = f"| {row['release']} | yes |"
        text = "\n".join(
            f"| {row['release']} | yes | yes | {row['rows']} | {row['processed_bytes']} | yes |"
            if line.startswith(prefix) else line for line in old_lines
        ) + "\n"
    marker = "## Layer 2 failed-release repairs, 2026-10-20"
    path.write_text(text.partition(marker)[0].rstrip() + "\n\n" + "\n".join(status) + "\n",
                    encoding="utf-8", newline="\n")
    coord = COORD.read_text(encoding="utf-8")
    marker = "## Layer 2 failed-release repairs"
    coord = coord.partition(marker)[0].rstrip()
    lines = [marker, "", f"SSD free space before: {before['free_bytes']} bytes."]
    lines.extend(
        f"- done {row['progress']} releases: {row['release']} - {row['result']}: {row['detail']}"
        for row in results if row["result"] != "paused"
    )
    lines.append(CHANGAN_PAUSE)
    lines.append(f"SSD free space after latest checkpoint: {free_after} bytes.")
    COORD.write_text(coord + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run(selected: list[str]) -> None:
    if "changan" in selected:
        raise ValueError(CHANGAN_PAUSE)
    OUT.mkdir(parents=True, exist_ok=True)
    before_usage = shutil.disk_usage(processed.cache_root().parent)
    before = {"free_bytes": before_usage.free, "total_bytes": before_usage.total}
    prior = []
    progress_path = OUT / "progress.csv"
    if progress_path.exists():
        _, prior_rows = _rows(progress_path)
        prior = prior_rows
    by_package = {row["release"]: row for row in prior}
    by_package["changan"] = {
        "progress": "", "release": "changan", "result": "paused", "rows": 0,
        "processed_bytes": 0, "detail": CHANGAN_PAUSE,
    }
    for package in selected:
        checksums: list[dict[str, object]] = []
        try:
            if package in {"cell_to_pack", "rise_conbat"}:
                detail = _no_build_line(package)
                rows = size = 0
                result = "not built"
            else:
                checksums = _ensure_held_checksums(package)
                if checksums:
                    checksum_path = OUT / "checksums.csv"
                    previous_checksums = pd.read_csv(checksum_path) if checksum_path.exists() else pd.DataFrame()
                    updated = pd.concat([previous_checksums, pd.DataFrame(checksums)], ignore_index=True)
                    updated.to_csv(checksum_path, index=False, lineterminator="\n")
                detail, rows, size = _build(package, checksums)
                result = "verified"
            record = {
                "progress": f"{RELEASES.index(package) + 1} of {len(RELEASES)}",
                "release": package,
                "result": result,
                "rows": rows,
                "processed_bytes": size,
                "detail": detail,
            }
        except Exception as error:
            record = {
                "progress": f"{RELEASES.index(package) + 1} of {len(RELEASES)}",
                "release": package,
                "result": "incomplete",
                "rows": 0,
                "processed_bytes": 0,
                "detail": f"{type(error).__name__}: {error}",
            }
        by_package[package] = record
        results = [by_package[name] for name in RELEASES if name in by_package]
        _write_progress(results, before)
        print(f"done {record['progress']} releases - {package}: {record['result']} - {record['detail']}",
              flush=True)
    (OUT / "README.md").write_text(
        "# Layer 2 failed-release repair\n\n"
        "The runner processes only previously failed or blocked releases, with no-build and smaller-copy work first. "
        "Held checksums are SHA-256 values computed from already-present files and recorded in "
        "`reports/verify_log.csv`; no source file is downloaded or changed. Timestamp rows that cannot be "
        "assigned a calendar month are preserved in an `undated` partition and counted in their manifests. "
        "The progress table records each release result and SSD space at the start and final checkpoint.\n\n"
        "The repairs cover lossless storage of mixed Birds CubeSat values, missing held checksums for "
        "Bilfinger 2025 and TUM FTM, preservation of invalid KU Leuven and Tongji timestamps in undated "
        "partitions, bounded M5BAT batches, and the Zhou loader-to-copy comparison. Every verified repair "
        "also passes source size/checksum checks and processed-part hash/row-count checks, with a "
        "loader spot check per unit. Source checks and spot comparisons are saved in "
        "`source_verification.csv` and `loader_spot_checks.csv`. Raw-after-conversion values are used "
        "without cleaning. Tongji's converted loader inputs are also checked against their committed "
        "conversion sizes and SHA-256 checksums in `converted_source_verification.csv`. Full loader "
        "row-count comparisons for streamed releases are saved in `loader_row_counts.csv`.\n\n"
        "Cell to Pack and RISE ConBat remain no-build releases for the reasons in `progress.csv`. "
        "Changan's fallback and sensor-token fix are committed, but its full copy remains paused at "
        "23 of 300 vehicles and is not verified. Partial output stays on the SSD only. The earlier "
        "verified releases are unchanged and were not revalidated under the new fingerprint.\n\n"
        "Reproduce with `python scripts/checks/layer2_failed_releases.py`. The default excludes Changan, "
        "and explicitly selecting it raises an error before reading or writing any data. "
        "Complete unit manifests are checked and reused on restart only after fresh source verification. "
        "Then run `python scripts/checks/layer2_code_fingerprint_check.py`; it fails if repair manifests "
        "are missing or stale and saves `code_fingerprint_check.csv`.\n",
        encoding="utf-8", newline="\n")
    if any(by_package[package]["result"] == "incomplete" for package in selected):
        raise RuntimeError("Layer 2 repair failures remain. See progress.csv.")


def data_root():
    from fielddata.config import data_root as configured_data_root
    return configured_data_root()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", nargs="+", choices=RELEASES, default=ACTIVE_RELEASES)
    parser.add_argument("--probe-birds", action="store_true",
                        help="inspect mixed source value types through the Birds CubeSat loader only")
    parser.add_argument("--verify-tongji-converted", action="store_true",
                        help="only verify held Tongji conversion inputs against the committed manifest")
    parser.add_argument("--verify-row-counts", action="store_true",
                        help="only compare full loader row counts for the streamed repair releases")
    args = parser.parse_args()
    if args.probe_birds:
        _probe_birds()
    elif args.verify_tongji_converted:
        _verify_tongji_converted_inputs()
    elif args.verify_row_counts:
        for package in args.packages:
            _verify_loader_row_counts(package)
    else:
        run(args.packages)


if __name__ == "__main__":
    main()
