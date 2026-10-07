"""Check my setup: is everything in place to load the releases?

Run ``python -m fielddata.doctor`` to check every release, or name some:
``python -m fielddata.doctor rwth-home tumftm``. It only looks at files; it never
downloads, moves or changes anything. Each problem comes with what to do about it.
A held file whose size or (up to 1 GB) checksum differs from the publisher's is reported as incomplete, and a
release folder kept under another name is found and named, so it can be renamed instead of downloaded again.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import re
import shutil
import sys
from pathlib import Path

from fielddata.config import data_root
from fielddata.fetch import plan_package
from fielddata.registry import PACKAGES

# Files a loader actually needs, where the registry's list also names files this collection derived.
REQUIRED = {
    "changan": ["raw/RAW_DATA.z01", "raw/RAW_DATA.zip"],
    "tumftm": [f"electric-vehicle-uds-dataset/data/uds_data/{v}.parquet" for v in ("CUP1", "CUP2", "CUP3", "CUP4", "CUP5", "ID1", "ID2")],
}
# Releases whose archives are RAR and need libarchive (or, for deng, UnRAR).
NEEDS_RAR = {"deng", "xie", "changan"}
CHECKSUMS = Path(__file__).with_name("reference_checksums.csv")
# The maintainer's verify run on the reference holdings; its "match" rows are files that matched a publisher checksum.
REFERENCE_LOG = Path(__file__).resolve().parents[1] / "reports" / "verify_log.csv"
# Files up to this size are also hashed and compared with the publisher checksum; larger ones get the size check only.
HASH_LIMIT = 1_000_000_000


def expected_files(package: str) -> list[str]:
    """The data files a release should have, with 'A through B' ranges expanded."""
    meta = PACKAGES[package]
    names = REQUIRED.get(package) or list(meta.get("data_files") or meta.get("archives", {}))
    out = []
    for name in names:
        m = re.match(r"(.*?)(\d+)(\D*) through (.*?)(\d+)(\D*)$", name)
        if m and m.group(1) == m.group(4) and m.group(3) == m.group(6):
            width = len(m.group(2)) if m.group(2).startswith("0") else 0
            for i in range(int(m.group(2)), int(m.group(5)) + 1):
                out.append(f"{m.group(1)}{str(i).zfill(width)}{m.group(3)}")
        else:
            out.append(name)
    return out


def reference_files(package: str) -> dict[str, dict]:
    """Publisher-backed size and checksum per data file: {name: {"bytes": int | None, "algorithm": str, "expected": str}}.

    From reference_checksums.csv (publisher values) and the "match" rows of the committed verify log. Files with only
    our own hash are left out: a fresh download of a GitHub repository can differ from the reference copy (line endings).
    """
    out: dict[str, dict] = {}
    for row in csv.DictReader(CHECKSUMS.open(encoding="utf-8")):
        if row["package"] == package and row["file"].startswith("data/"):
            size = int(row["bytes_when_recorded"]) if row.get("bytes_when_recorded", "").isdigit() else None
            out[row["file"].removeprefix("data/")] = {"bytes": size, "algorithm": row["algorithm"], "expected": row["publisher_value"]}
    if REFERENCE_LOG.exists():
        for row in csv.DictReader(REFERENCE_LOG.open(encoding="utf-8")):
            if row["package"] == package and row["status"] == "match" and row["file"].startswith("data/") and row["bytes"].isdigit():
                entry = out.setdefault(row["file"].removeprefix("data/"), {"algorithm": row["algorithm"], "expected": row["expected"]})
                entry["bytes"] = entry.get("bytes") or int(row["bytes"])
    return out


def incomplete(path: Path, ref: dict) -> str | None:
    """Why a held file does not match its publisher reference, or None when it matches (or cannot be checked)."""
    size = path.stat().st_size
    if ref.get("bytes") and size != ref["bytes"]:
        return f"{size:,} bytes, expected {ref['bytes']:,}"
    if ref.get("expected") and ref.get("algorithm") in {"md5", "sha256", "sha512"} and size <= HASH_LIMIT:
        digest = hashlib.new(ref["algorithm"])
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != ref["expected"].lower():
            return f"its {ref['algorithm']} checksum does not match the publisher's"
    return None


def renamed_folder(root: Path, package: str) -> str | None:
    """A folder in the data folder that is probably this release under another name: it holds the release's
    expected files, or its name is close to the expected one. None when nothing fits."""
    if not root.is_dir():
        return None
    expected = Path(PACKAGES[package]["data_directory"])
    top = expected.parts[0]
    claimed = {Path(meta["data_directory"]).parts[0] for meta in PACKAGES.values()}
    candidates = [p for p in root.iterdir() if p.is_dir() and p.name not in claimed and not p.name.startswith(("_", "."))]
    names = [Path(n).name for n in expected_files(package) if not n.endswith("/**")]
    for folder in candidates:
        inner = folder.joinpath(*expected.parts[1:])
        if any((inner / n).is_file() or (folder / "data" / n).is_file() or (folder / n).is_file() for n in names):
            return folder.name
    close = difflib.get_close_matches(top.lower(), [p.name.lower() for p in candidates], n=1, cutoff=0.8)
    if close:
        return next(p.name for p in candidates if p.name.lower() == close[0])
    return None


def rar_tool() -> str | None:
    try:
        import libarchive  # noqa: F401
        return "libarchive"
    except Exception:
        pass
    return "UnRAR" if (shutil.which("unrar") or shutil.which("UnRAR")) else None


def check_package(root: Path, package: str) -> list[str]:
    """Return a list of problems (empty when the release is ready)."""
    plan = plan_package(package, root)
    folder = plan.destination
    if not folder.is_dir():
        top = Path(PACKAGES[package]["data_directory"]).parts[0]
        found = renamed_folder(root, package)
        if found:
            return [f"release folder found under '{found}': rename it to exactly '{top}' (no need to download again)"]
        how = f"run: python -m fielddata.fetch {package}" if plan.automatic else f"run: python -m fielddata.fetch {package} (it prints which files to download by hand and where to put them)"
        return [f"folder not found: {folder}. To get the data, {how}"]
    problems = []
    references = reference_files(package)
    for name in expected_files(package):
        if name.endswith("/**"):
            sub = folder / name[:-3]
            if not (sub.is_dir() and any(sub.iterdir())):
                problems.append(f"missing or empty folder: {sub}")
            continue
        path = folder / name
        if not path.is_file():
            problems.append(f"missing file: {name} (expected in {folder})")
        elif name in references and (why := incomplete(path, references[name])):
            problems.append(f"incomplete: {name} is damaged or only partly downloaded ({why}); delete it and download it again, then run python -m fielddata.verify {package}")
    if package in NEEDS_RAR and rar_tool() is None:
        problems.append("this release is a RAR archive and no RAR reader is installed: run  pip install libarchive-c  (on Windows, installing 7-Zip or WinRAR also works for one release)")
    return problems


def main(argv: list[str] | None = None) -> int:
    packages = (argv if argv is not None else sys.argv[1:]) or list(PACKAGES)
    unknown = [p for p in packages if p not in PACKAGES]
    if unknown:
        print(f"Unknown release name(s): {', '.join(unknown)}. Names are in Table 1, for example: {', '.join(list(PACKAGES)[:4])}")
        return 2
    print(f"Python {sys.version.split()[0]}" + ("" if sys.version_info >= (3, 11) else "  (too old: install Python 3.11 or newer)"))
    try:
        root = data_root()
    except ValueError:
        print("No data folder is set. Copy config/local.example.toml to config/local.toml and set data_root to the folder that will hold the releases.")
        return 1
    if not root.is_dir():
        print("No data downloaded yet. Run python -m fielddata.fetch <release>; it creates the folder."
              f" (Data folder: {root})")
        return 1
    print(f"Data folder: {root}\n")
    ready = 0
    for package in packages:
        problems = check_package(root, package)
        if problems:
            print(f"[{'incomplete' if any(p.startswith('incomplete:') for p in problems) else 'needs attention'}] {package}")
            for p in problems:
                print(f"    - {p}")
        else:
            ready += 1
            print(f"[ready] {package}")
    print(f"\n{ready} of {len(packages)} releases ready to load.")
    return 0 if ready == len(packages) else 1


if __name__ == "__main__":
    raise SystemExit(main())
