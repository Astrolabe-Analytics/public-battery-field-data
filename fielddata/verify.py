"""Checksum verification for locally held public-data files.

Run ``python -m fielddata.verify`` to check every release, or name some: ``python -m fielddata.verify rwth-home tumftm``.
Each run hashes the files afresh and replaces that release's rows in reports/local/verify_log.csv; pass ``--resume`` to
reuse logged rows for files whose size has not changed (useful when a long run was interrupted). reports/local/ is not
tracked by git, so running verify never changes the repository. The committed reports/verify_log.csv is the
maintainer's record of the full run on the reference holdings; after such a run, copy reports/local/verify_log.csv over it.
A release with no files in its data folder is reported as an error, and the command then exits with status 1.
"""
import csv
from hashlib import md5, sha256, sha512
from pathlib import Path
from threading import Event, Thread
from time import perf_counter
from datetime import datetime, timezone
import zipfile

import pandas as pd

from fielddata.config import data_root
from fielddata.registry import PACKAGES

_ROOT = Path(__file__).parent.parent
_REFERENCES = _ROOT / "fielddata" / "reference_checksums.csv"
_LOG = _ROOT / "reports" / "local" / "verify_log.csv"
_PROGRESS = _ROOT / "reports" / "local" / "verify_progress.txt"
_FIELDS = ["package", "file", "algorithm", "expected", "measured", "bytes", "status", "seconds"]


def _references():
    with _REFERENCES.open(newline="", encoding="utf-8") as reference_file:
        return {(row["package"], row["file"]): row for row in csv.DictReader(reference_file)}


def _completed():
    if not _LOG.exists():
        return {}
    with _LOG.open(newline="", encoding="utf-8") as log_file:
        return {(row["package"], row["file"], int(row["bytes"])): row for row in csv.DictReader(log_file)}


def _replace_package_rows(package_id):
    if not _LOG.exists():
        return
    with _LOG.open(newline="", encoding="utf-8") as log_file:
        rows = [row for row in csv.DictReader(log_file) if row["package"] != package_id]
    with _LOG.open("w", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(log_file, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _digest(path, algorithm):
    digest = {"md5": md5, "sha256": sha256, "sha512": sha512}[algorithm]()
    with path.open("rb") as data_file:
        for chunk in iter(lambda: data_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _member_digest(archive, member, algorithm):
    digest = {"md5": md5, "sha256": sha256, "sha512": sha512}[algorithm]()
    with archive.open(member) as data_file:
        for chunk in iter(lambda: data_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append(row):
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    new_file = not _LOG.exists()
    with _LOG.open("a", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(log_file, fieldnames=_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def _progress_checkpoint():
    completed = list(_completed().values())
    byte_count = sum(int(row["bytes"]) for row in completed)
    _PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    with _PROGRESS.open("a", encoding="utf-8") as progress_file:
        progress_file.write(f"{datetime.now(timezone.utc).isoformat()} files={len(completed)} GB={byte_count / 1_000_000_000:.3f}\n")


class _ProgressReporter:
    def __init__(self, interval_seconds=1800):
        self._stop = Event()
        self._interval_seconds = interval_seconds
        self._thread = Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.wait(self._interval_seconds):
            _progress_checkpoint()

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join()


def _files(directory):
    return sorted(path for path in directory.rglob("*") if path.is_file() and ".git" not in path.parts)


def _extra_dirs(package_id):
    """Sibling paper/ and supplementary/ folders next to a package's data/ directory, if held."""
    parent = (data_root() / PACKAGES[package_id]["data_directory"]).parent
    return [(label, parent / label) for label in ("paper", "supplementary") if (parent / label).is_dir()]


def _record(package_id, file_name, algorithm, expected, measured, size, started):
    status = "match" if expected and measured == expected else "MISMATCH" if expected else "publisher value pending"
    row = {"package": package_id, "file": file_name, "algorithm": algorithm, "expected": expected, "measured": measured, "bytes": size, "status": status, "seconds": f"{perf_counter() - started:.3f}"}
    _append(row)
    print(f"{package_id}: {file_name}: {status}", flush=True)
    return row


def _zip_references(package_id, directory, references):
    rows = []
    for (reference_package, file_name), reference in references.items():
        if reference_package != package_id or " :: " not in file_name or reference["algorithm"] == "none":
            continue
        outer, inner = file_name.removeprefix("data/").split(" :: ", 1)
        archive_path = directory / outer
        with zipfile.ZipFile(archive_path) as archive:
            info = archive.getinfo(inner)
            started = perf_counter()
            measured = _member_digest(archive, info, reference["algorithm"])
            rows.append(_record(package_id, file_name, reference["algorithm"], reference["publisher_value"], measured, info.file_size, started))
    return rows


def _sha512_manifest_rows(package_id, directory, references):
    rows = []
    for (reference_package, file_name), reference in references.items():
        if reference_package != package_id or reference["algorithm"] != "sha512" or "*" not in file_name:
            continue
        outer = next(path for path in directory.glob("*.zip") if path.name == "data.zip")
        with zipfile.ZipFile(outer) as archive:
            manifest = next(name for name in archive.namelist() if name.lower().endswith("checksums.sha512"))
            prefix = str(Path(manifest).parent).replace(".", "").replace("\\", "/").strip("/")
            for line in archive.read(manifest).decode("utf-8").splitlines():
                expected, member = line.split(maxsplit=1)
                member = member.lstrip("*").replace("\\", "/")
                archive_member = f"{prefix}/{member}" if prefix else member
                try:
                    info = archive.getinfo(archive_member)
                except KeyError:
                    continue
                started = perf_counter()
                measured = _member_digest(archive, info, "sha512")
                rows.append(_record(package_id, f"data/data.zip :: {archive_member}", "sha512", expected, measured, info.file_size, started))
    return rows


def verify(package_id, resume=False):
    """Verify every held file for one package. With resume=True, reuse logged rows for files of unchanged size.

    Covers the data/ directory (against publisher checksums where known) plus any sibling
    paper/ and supplementary/ folders (own hash only; publishers don't checksum those).
    """
    if not resume:
        _replace_package_rows(package_id)
    references = _references()
    completed = _completed() if resume else {}
    directory = data_root() / PACKAGES[package_id]["data_directory"]
    if not directory.is_dir() or not _files(directory):
        row = {"package": package_id, "file": "<package>", "algorithm": "", "expected": "", "bytes": 0, "seconds": "0.000",
               "measured": f"no files in the data folder; download the release first with python -m fielddata.fetch {package_id}",
               "status": "ERROR: no files"}
        _append(row)
        print(f"{package_id}: no files found in its data folder. Download it first: python -m fielddata.fetch {package_id}", flush=True)
        return pd.DataFrame([row], columns=_FIELDS)
    rows = _zip_references(package_id, directory, references)
    rows.extend(_sha512_manifest_rows(package_id, directory, references))
    labeled_dirs = [("data", directory), *_extra_dirs(package_id)]
    for label, label_directory in labeled_dirs:
        for path in _files(label_directory):
            relative = path.relative_to(label_directory).as_posix()
            file_name = f"{label}/{relative}"
            try:
                size = path.stat().st_size
            except OSError as error:
                row = {"package": package_id, "file": file_name, "algorithm": "", "expected": "", "measured": str(error), "bytes": 0, "status": f"ERROR: {type(error).__name__}", "seconds": "0.000"}
                _append(row)
                rows.append(row)
                print(f"{package_id}: {relative}: {row['status']}", flush=True)
                continue
            prior = completed.get((package_id, file_name, size))
            if prior:
                rows.append(prior)
                continue
            reference = references.get((package_id, file_name)) if label == "data" else None
            if reference and (" :: " in reference["file"] or "*" in reference["file"]):
                continue
            algorithm = reference["algorithm"] if reference else "md5+sha256"
            expected = reference["publisher_value"] if reference else ""
            started = perf_counter()
            try:
                if reference and algorithm == "none":  # the publisher posts no checksum for this file: record our own hash
                    algorithm, expected = "md5+sha256", ""
                    measured = f"md5:{_digest(path, 'md5')} sha256:{_digest(path, 'sha256')}"
                    status = "no publisher checksum"
                elif reference:
                    measured = _digest(path, algorithm)
                    status = "match" if expected and measured == expected else "MISMATCH" if expected else "publisher value pending"
                else:
                    measured = f"md5:{_digest(path, 'md5')} sha256:{_digest(path, 'sha256')}"
                    status = "own hash, no publisher reference"
            except OSError as error:
                measured = str(error)
                status = f"ERROR: {type(error).__name__}"
            row = {"package": package_id, "file": file_name, "algorithm": algorithm, "expected": expected, "measured": measured, "bytes": size, "status": status, "seconds": f"{perf_counter() - started:.3f}"}
            _append(row)
            rows.append(row)
            print(f"{package_id}: {file_name}: {status}", flush=True)
    return pd.DataFrame(rows, columns=_FIELDS)


def verify_all(packages=None, resume=False):
    """Verify the named packages (default: all), writing a progress line to reports/verify_progress.txt every 30 minutes."""
    reporter = _ProgressReporter()
    reporter.start()
    try:
        results = {}
        for package_id in packages or sorted(PACKAGES):
            try:
                results[package_id] = verify(package_id, resume=resume)
            except Exception as error:
                row = {"package": package_id, "file": "<package>", "algorithm": "", "expected": "", "measured": str(error), "bytes": 0, "status": f"ERROR: {type(error).__name__}", "seconds": "0.000"}
                _append(row)
                results[package_id] = pd.DataFrame([row], columns=_FIELDS)
                print(f"{package_id}: {row['status']}: {error}", flush=True)
        return results
    finally:
        reporter.stop()


def summary(statuses, problems: int) -> str:
    """One line for the end of a run. Where the host publishes no checksums, say so rather than "0 match"."""
    own = statuses.isin(["no publisher checksum", "own hash, no publisher reference"]).sum()
    matched = (statuses == "match").sum()
    if own and own == len(statuses) - problems:
        return f"{len(statuses)} files checked: host publishes no checksums; our SHA-256 recorded. {problems} mismatches or errors."
    extra = f", {own} with no publisher checksum (our SHA-256 recorded)" if own else ""
    return f"{len(statuses)} files checked: {matched} match a publisher checksum{extra}, {problems} mismatches or errors."


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="python -m fielddata.verify", description="Hash held files and compare them with publisher checksums.")
    parser.add_argument("packages", nargs="*", help="release names (default: all)")
    parser.add_argument("--resume", action="store_true", help="reuse logged rows for files whose size has not changed")
    args = parser.parse_args(argv)
    unknown = [p for p in args.packages if p not in PACKAGES]
    if unknown:
        parser.error(f"unknown release(s): {', '.join(unknown)}")
    results = verify_all(args.packages or None, resume=args.resume)
    rows = pd.concat(results.values(), ignore_index=True) if results else pd.DataFrame(columns=_FIELDS)
    bad = rows[rows["status"].str.startswith(("MISMATCH", "ERROR"))]
    empty = rows[rows["status"] == "ERROR: no files"]
    files = rows[rows["status"] != "ERROR: no files"]
    if len(files):
        print("\n" + summary(files["status"], len(bad) - len(empty)))
    if len(empty):
        print(("\n" if not len(files) else "") + f"No files found for {', '.join(empty['package'])}: nothing to check there.")
    return 1 if len(bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
