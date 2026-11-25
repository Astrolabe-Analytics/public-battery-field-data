"""Rebuildable layer 2 storage, with content-verified inputs and per-unit manifests.

Run ``python -m fielddata.processed [release ...]``. All data stays on the configured SSD.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from numbers import Integral
import subprocess
import uuid
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import fielddata
from fielddata._standard import PACKAGES, canonical_unit, from_raw, raw_frame
from fielddata.config import data_root
from fielddata.loaders import _snippets
from fielddata.registry import metadata

ROOT = Path(__file__).resolve().parents[1]
FORMAT_VERSION = 1


class StaleProcessed(ValueError):
    """A processed copy does not match its source files, code or output checksums."""


def cache_root() -> Path:
    return data_root() / "_processed"


def unit_directory(package: str, unit) -> Path:
    canonical_unit(package, unit)
    return cache_root() / package / f"unit={quote(str(unit), safe='')}"


def code_version() -> dict:
    files = sorted((ROOT / "fielddata").rglob("*.py"))
    files += sorted((ROOT / "fielddata" / "loaders").glob("*_SCHEMA.md"))
    files += sorted((ROOT / "fielddata" / "loaders").glob("*.csv"))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    return {"revision": revision, "code_sha256": digest.hexdigest(), "format_version": FORMAT_VERSION,
            "pandas": pd.__version__, "pyarrow": pa.__version__}


def _hashes(path: Path, algorithms=("sha256",)) -> dict[str, str]:
    hashes = {name: hashlib.new(name) for name in algorithms}
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            for digest in hashes.values():
                digest.update(block)
    return {name: digest.hexdigest() for name, digest in hashes.items()}


def source_paths(package: str) -> list[Path]:
    """Only actual loader inputs, not other releases, weather or the separate PPL cell-level share."""
    directory = data_root() / metadata(package)["data_directory"]
    if package == "cao":
        names = metadata(package)["archives"]
    elif package == "schaeffer":
        names = ["field_data.zip"]
    elif package == "ppl":
        from fielddata.loaders.ppl import _ess_files
        return [path for _, path in _ess_files()]
    elif package == "xie":
        names = ["DataForPub.rar"]
    elif package in {"zhang2023", "evbattery"}:
        names = [f"battery_{'brand' if package == 'zhang2023' else 'dataset'}{i}.tar.gz" for i in (1, 2, 3)]
    elif package == "aitio":
        from fielddata.loaders.aitio import ZIPS
        names = [*ZIPS, "meta_data.csv"]
    elif package == "deng":
        names = [f"#{number}.rar" for number in range(1, 21)]
    elif package == "rwth-home":
        names = [f"Data_ID_{number:02d}.zip" for number in range(1, 22)]
    elif package == "tumftm":
        root = directory / "electric-vehicle-uds-dataset" / "data"
        names = ["electric-vehicle-uds-dataset/data/value_overview.csv"]
        names.extend(path.relative_to(directory).as_posix() for path in (root / "uds_data").glob("*.parquet"))
    elif package == "shenzhen_charging":
        names = ["processed_data.xlsx"]
    elif package == "zhou2026":
        names = ["Vehicle data.zip"]
    elif package == "cell_to_pack":
        names = [f"Pack_field#{number}.zip" for number in range(1, 17)] + [
            "ESSH1.zip", "ESSL1.zip", "ESSL2.zip", "PBSL1.zip"]
    elif package == "stanford_ev":
        from fielddata.loaders import stanford_ev
        return sorted(stanford_ev._field_files().values())
    else:
        patterns = metadata(package).get("data_files", [])
        if not patterns:
            raise ValueError(f"{package}: registry does not declare loader input files")
        names = []
        for pattern in patterns:
            if " through " in pattern:
                if package == "deng":
                    names.extend(f"#{number}.rar" for number in range(1, 21))
                else:
                    raise ValueError(f"{package}: unsupported data-file range {pattern!r}")
                continue
            for path in directory.glob(pattern):
                if path.is_file() and ".git" not in path.parts:
                    names.append(path.relative_to(directory).as_posix())
    paths = [directory / name for name in names if (directory / name).is_file()]
    if package == "tumftm":
        paths = [path for path in paths if path.suffix.lower() == ".parquet"
                 or path.name == "value_overview.csv"]
    elif package == "pnnl_epri":
        paths = [path for path in paths if path.suffix.lower() == ".feather"]
    elif package == "rise_conbat":
        paths = [path for path in paths if path.suffix.lower() == ".zip"]
    elif package == "cell_to_pack":
        paths = [path for path in paths if path.suffix.lower() == ".zip"]
    if not paths:
        raise FileNotFoundError(f"{package}: no loader input files held")
    return sorted(dict.fromkeys(paths))


def verify_sources(package: str) -> list[dict]:
    """Fresh hashes and sizes compared with publisher references or committed holding snapshots."""
    paths = source_paths(package)
    if not paths:
        raise FileNotFoundError(f"{package}: no loader input files held")
    directory = data_root() / metadata(package)["data_directory"]
    with (ROOT / "fielddata" / "reference_checksums.csv").open(encoding="utf-8", newline="") as handle:
        references = {row["file"]: row for row in csv.DictReader(handle) if row["package"] == package}
    with (ROOT / "reports" / "verify_log.csv").open(encoding="utf-8", newline="") as handle:
        snapshots = {row["file"]: row for row in csv.DictReader(handle) if row["package"] == package}
    result = []
    for path in paths:
        name = "data/" + path.relative_to(directory).as_posix()
        reference = references.get(name, {})
        snapshot = snapshots.get(name, {})
        expected = {}
        algorithm = reference.get("algorithm")
        if algorithm in hashlib.algorithms_available and reference.get("publisher_value"):
            expected[algorithm] = reference["publisher_value"]
        own_sha256 = metadata(package).get("own_sha256", {}).get(path.relative_to(directory).as_posix())
        if not expected and own_sha256:
            expected["sha256"] = own_sha256
        if not expected:
            for item in snapshot.get("measured", "").split():
                if ":" in item:
                    key, value = item.split(":", 1)
                    if key in hashlib.algorithms_available:
                        expected[key] = value
            if not expected and snapshot.get("algorithm") in hashlib.algorithms_available:
                expected[snapshot["algorithm"]] = snapshot["measured"]
        if not expected:
            raise ValueError(f"{package} {name}: no committed checksum to verify against")
        before = path.stat()
        size = reference.get("bytes_when_recorded")
        try:
            expected_size = int(size) if size else None
        except (TypeError, ValueError):
            expected_size = None
        if expected_size is None and snapshot.get("bytes"):
            expected_size = int(snapshot["bytes"])
        if expected_size and before.st_size != expected_size:
            raise ValueError(f"{package} {name}: size mismatch, expected {expected_size}, found {before.st_size}")
        measured = _hashes(path, sorted({"sha256", *expected}))
        if any(measured[key] != value for key, value in expected.items()):
            raise ValueError(f"{package} {name}: checksum mismatch")
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"{package} {name}: source changed while hashing")
        result.append({"file": name, "bytes": after.st_size, "sha256": measured["sha256"],
                       "mtime_ns": after.st_mtime_ns, "reference": "publisher" if reference.get("publisher_value") else "held snapshot"})
    return result


def _source_content(sources: list[dict]) -> list[dict]:
    return [{key: row[key] for key in ("file", "bytes", "sha256")} for row in sources]


def _same_code(left: dict, right: dict) -> bool:
    return all(left.get(key) == right.get(key) for key in ("code_sha256", "format_version", "pandas", "pyarrow"))


def _read_manifest(package: str, unit) -> dict:
    path = unit_directory(package, unit) / "manifest.json"
    if not path.exists():
        raise StaleProcessed(f"{package} {unit}: no processed manifest, run python -m fielddata.processed {package}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate(package: str, unit, *, sources=None, version=None) -> dict:
    """Validate fresh source content, producing code and every saved output part."""
    manifest = _read_manifest(package, unit)
    sources = verify_sources(package) if sources is None else sources
    version = code_version() if version is None else version
    if manifest["package"] != package or manifest["unit"] != str(unit):
        raise StaleProcessed(f"{package} {unit}: manifest identity mismatch")
    if not _same_code(manifest["code_version"], version):
        raise StaleProcessed(f"{package} {unit}: producing code changed")
    if _source_content(manifest["sources"]) != _source_content(sources):
        raise StaleProcessed(f"{package} {unit}: source content changed")
    directory = unit_directory(package, unit)
    if not manifest["parts"]:
        raise StaleProcessed(f"{package} {unit}: manifest has no output parts")
    for part in manifest["parts"]:
        path = directory / part["file"]
        if not path.resolve().is_relative_to(directory.resolve()):
            raise StaleProcessed(f"{package} {unit}: invalid part path")
        if not path.is_file() or path.stat().st_size != part["bytes"] or _hashes(path)["sha256"] != part["sha256"]:
            raise StaleProcessed(f"{package} {unit}: missing or damaged part {part['file']}")
        parquet = pq.read_metadata(path)
        if parquet.num_rows != part["rows"] or parquet.schema.names != part["columns"]:
            raise StaleProcessed(f"{package} {unit}: part shape disagrees with manifest")
    if sum(part["rows"] for part in manifest["parts"]) != manifest["rows"]:
        raise StaleProcessed(f"{package} {unit}: total rows disagree with manifest")
    return manifest


def load(package: str, unit, *, month: str | None = None, verify_sources_now=False) -> pd.DataFrame:
    """Read a processed unit, checking code, input stat signatures and output hashes.

    ``verify_sources_now=True`` also rehashes original files. Builds always rehash them.
    """
    manifest = _read_manifest(package, unit)
    if verify_sources_now:
        manifest = validate(package, unit)
    else:
        _assert_unchanged(package, manifest["sources"])
        manifest = validate(package, unit, sources=manifest["sources"])
    directory = unit_directory(package, unit)
    frames = [pd.read_parquet(directory / part["file"]) for part in manifest["parts"]
              if month is None or part["month"] == month]
    if not frames:
        raise ValueError(f"{package} {unit}: no processed partition {month}")
    result = pd.concat(frames, ignore_index=True)
    result.attrs = {"package": package, "unit": str(unit), "processed_manifest": manifest}
    return result


class _Writer:
    def __init__(self, package: str, unit: str, sources: list[dict], version: dict):
        self.package, self.unit = package, unit
        self.directory = unit_directory(package, unit)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.sources, self.version = sources, version
        self.parts: list[dict] = []
        self.rows = 0
        self.generation = uuid.uuid4().hex

    def append(self, frame: pd.DataFrame):
        if frame.empty:
            return
        frame = frame.copy()
        encodings = dict(frame.attrs.get("source_value_encodings", {}))
        for column in frame.select_dtypes(include="object").columns:
            values = frame[column].dropna()
            types = {type(value).__name__ for value in values}
            if len(types) <= 1:
                continue
            if types <= {"int", "str"}:
                def encode(value):
                    if pd.isna(value):
                        return None
                    if isinstance(value, str):
                        return json.dumps({"type": "str", "value": value}, ensure_ascii=False)
                    if isinstance(value, Integral):
                        return json.dumps({"type": "int", "value": int(value)})
                    raise TypeError(f"{column}: unsupported mixed source value {type(value).__name__}")

                frame[column] = frame[column].map(encode).astype("string")
                encodings[column] = "JSON tagged int/string values; decode each non-null string to restore value and type"
        if encodings:
            frame.attrs["source_value_encodings"] = encodings
        invalid_time_rows = 0
        if "time" in frame:
            invalid_time_rows = int(frame["time"].isna().sum())
            months = frame["time"].dt.strftime("%Y-%m").fillna("undated")
        else:
            months = pd.Series("undated", index=frame.index)
        # Consecutive runs preserve original order, even with out-of-order source timestamps.
        runs = months.ne(months.shift()).cumsum()
        for _, chunk in frame.groupby(runs, sort=False):
            month = months.loc[chunk.index[0]]
            relative = f"month={month}/part-{self.generation}-{len(self.parts):06d}.parquet"
            path = self.directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            chunk.to_parquet(path, index=False, compression="zstd")
            self.parts.append({"file": relative, "month": month, "rows": len(chunk),
                               "bytes": path.stat().st_size, "sha256": _hashes(path)["sha256"],
                               "columns": list(chunk.columns), "attrs": frame.attrs,
                               "invalid_time_rows": int(chunk["time"].isna().sum()) if "time" in chunk else 0})
            self.rows += len(chunk)
        if invalid_time_rows:
            self.invalid_time_rows = getattr(self, "invalid_time_rows", 0) + invalid_time_rows

    def finish(self) -> dict:
        if not self.parts:
            raise ValueError(f"{self.package} {self.unit}: no data, processed copy not created")
        manifest = {"package": self.package, "unit": self.unit, "rows": self.rows, "clean": False,
                    "code_version": self.version, "sources": self.sources, "parts": self.parts,
                    "invalid_time_rows": getattr(self, "invalid_time_rows", 0)}
        temporary = self.directory / f"manifest-{self.generation}.tmp"
        temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
        temporary.replace(self.directory / "manifest.json")
        keep = {part["file"] for part in self.parts}
        for path in self.directory.glob("month=*/part-*.parquet"):
            if path.relative_to(self.directory).as_posix() not in keep:
                path.unlink()
        return manifest


def _assert_unchanged(package: str, sources: list[dict]):
    directory = data_root() / metadata(package)["data_directory"]
    for source in sources:
        stat = (directory / source["file"].removeprefix("data/")).stat()
        if (stat.st_size, stat.st_mtime_ns) != (source["bytes"], source["mtime_ns"]):
            raise ValueError(f"{package} {source['file']}: source changed during build")


def _append_summary(row: dict):
    path = cache_root() / "build_summary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("package", "unit", "status", "rows", "reason"))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def build(package: str, *, units=None, force=False, chunksize=250_000) -> pd.DataFrame:
    """Build all supported units, skipping content-verified complete units on restart.

    Known blocks and label-only units are reported and skipped. Unexpected errors are reported and raised.
    """
    table = fielddata.standard_systems(package)
    if units is not None:
        requested = {str(unit) for unit in units}
        missing = requested - set(table["unit"])
        if missing:
            raise ValueError(f"{package}: unknown units {sorted(missing)}")
        table = table[table["unit"].isin(requested)]
    rows, pending = [], []

    def record(unit, status, count=0, reason=""):
        row = {"package": package, "unit": unit, "status": status, "rows": count, "reason": reason}
        rows.append(row)
        _append_summary(row)
        print(f"{package} {unit}: {status} {reason}", flush=True)

    for row in table.itertuples():
        if row.standard_status != "supported":
            record(row.unit, row.standard_status, reason=row.standard_reason)
            continue
        pending.append(row.unit)
    if not pending:
        return pd.DataFrame(rows)
    sources = verify_sources(package)
    version = code_version()
    pending = []
    for row in table.itertuples():
        if row.standard_status != "supported":
            continue
        if not force:
            try:
                manifest = validate(package, row.unit, sources=sources, version=version)
            except StaleProcessed:
                pass
            else:
                record(row.unit, "reused", manifest["rows"])
                continue
        pending.append(row.unit)
    if package in {"zhang2023", "evbattery"}:
        for archive in table["archive"].unique():
            active = {unit for unit in pending if unit.startswith(archive.removesuffix(".tar.gz") + ":")}
            if not active:
                continue
            writers = {unit: _Writer(package, unit, sources, version) for unit in active}
            buffers = {unit: [] for unit in active}
            buffered_rows = 0

            def flush():
                for name, records in buffers.items():
                    if records:
                        raw = _snippets.snippet_batch(records)
                        writers[name].append(from_raw(package, name, raw))
                        records.clear()

            try:
                for member, array, meta in _snippets.iter_snippets(package, archive):
                    unit = f"{archive.removesuffix('.tar.gz')}:{int(meta['car'])}"
                    if unit not in active:
                        continue
                    buffers[unit].append((member, array, meta))
                    buffered_rows += len(array)
                    if buffered_rows >= chunksize:
                        flush()
                        buffered_rows = 0
                flush()
                _assert_unchanged(package, sources)
                for unit in sorted(active):
                    manifest = writers[unit].finish()
                    record(unit, "built", manifest["rows"])
            except Exception as error:
                record(archive, "failed", reason=str(error))
                raise
    elif package == "shenzhen_charging":
        active = set(pending)
        seen = set()
        try:
            raw = fielddata.load(package)
            for unit, batch in raw.groupby("transaction_id", sort=False):
                name = str(unit)
                if name not in active:
                    continue
                writer = _Writer(package, name, sources, version)
                writer.append(from_raw(package, name, batch))
                manifest = writer.finish()
                _assert_unchanged(package, sources)
                seen.add(name)
                record(name, "built", manifest["rows"])
            missing = active - seen
            if missing:
                raise ValueError(f"{package}: loader omitted pending sessions {sorted(missing)[:5]}")
        except Exception as error:
            record(package, "failed", reason=str(error))
            raise
    else:
        for unit in pending:
            try:
                writer = _Writer(package, unit, sources, version)
                standardized = False
                if package == "schaeffer":
                    frames = fielddata.load(package, system=int(unit), chunksize=chunksize)
                elif package == "ppl":
                    from fielddata.loaders.ppl import _ess_files
                    frames = (fielddata.load(package, years=[year]) for year, _ in _ess_files())
                elif package == "changan":
                    frames = fielddata.load(package, unit=unit, chunksize=min(chunksize, 25_000))
                elif package == "rwth-home":
                    from fielddata.loaders import rwth_home
                    frames = (fielddata.load(package, unit=unit, month=month)
                              for month, _ in rwth_home.months(unit))
                elif package == "tumftm":
                    from fielddata.loaders import tumftm
                    frames = tumftm.iter_load(unit, chunksize=chunksize)
                elif package == "m5bat-pbacid":
                    from fielddata.loaders import m5bat_pbacid
                    source = unit.rsplit(":", 1)[1]
                    frames = m5bat_pbacid.iter_load(source=source, chunksize=chunksize)
                elif package == "zhou2026":
                    part_count = int(table.loc[table["unit"] == unit, "partitions"].iloc[0])
                    frames = (fielddata.load(package, unit=unit, part=part)
                              for part in range(part_count))
                elif package == "stanford_ev":
                    frames = fielddata.iter_standard(package, unit, signal="V_pack_bms")
                    standardized = True
                else:
                    frames = [raw_frame(package, unit)]
                for raw in frames:
                    writer.append(raw if standardized else from_raw(package, unit, raw))
                _assert_unchanged(package, sources)
                manifest = writer.finish()
                record(unit, "built", manifest["rows"])
            except Exception as error:
                record(unit, "failed", reason=str(error))
                raise
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", nargs="*", choices=PACKAGES)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--unit", action="append", help="Limit a single-release build to named units")
    args = parser.parse_args()
    packages = args.packages or PACKAGES
    if args.unit and len(packages) != 1:
        parser.error("--unit requires exactly one release")
    for package in packages:
        build(package, units=args.unit, force=args.force)


if __name__ == "__main__":
    main()
