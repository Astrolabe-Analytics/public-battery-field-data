"""Check the automatic download of the three largest automatic releases without downloading them again.

What it does: for cao (Zenodo), ppl (GitHub) and rwth-home (Zenodo), asks the publisher for the file list
that `python -m fielddata.fetch <release>` would download, and compares each file's name and size with the
copy held in the data folder. Then it downloads the smallest planned file of each release into a temporary
scratch folder through the same fetch code (`fielddata.fetch` with `--to`), checks it against the
publisher's checksum where one exists and against the held copy's SHA-256, and deletes the scratch copy.

Reads: the publisher records over the internet, and the held files' names, sizes and (for three files)
contents in the data folder, found through fielddata.fetch.plan_package.
Writes: reports/checks/large_fetch_check.txt. The scratch downloads are deleted when the script ends.

Run:
    python scripts/checks/large_fetch_check.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fielddata import fetch

PACKAGES = ["cao", "ppl", "rwth-home"]
OUT = ROOT / "reports" / "checks" / "large_fetch_check.txt"


def held_files(destination: Path) -> dict[str, int]:
    return {p.relative_to(destination).as_posix(): p.stat().st_size
            for p in destination.rglob("*") if p.is_file() and ".git" not in p.parts}


def check(package: str) -> list[str]:
    plan = fetch.plan_package(package)
    remote = fetch.resolve_files(plan)
    held = held_files(plan.destination)
    planned = {r.name: r for r in remote}
    sizes = {n: r.size for n, r in planned.items()}
    line_endings = []
    if plan.source_kind == "github":
        # The GitHub tree gives the size of a Git LFS pointer, not of the file behind it: read each small
        # file and take the real size from its pointer. A small text file held with Windows line endings
        # (see docs/VERIFICATION.md) is reported apart from a real size difference.
        for name, r in planned.items():
            if r.size is not None and r.size < 2048:
                with urlopen(Request(r.url, headers={"User-Agent": "public-battery-field-data/1.0"}), timeout=60) as response:
                    raw = response.read()
                if raw.startswith(b"version https://git-lfs.github.com/spec/v1"):
                    sizes[name] = int(raw.split(b"size ")[1].split()[0])
                elif name in held and held[name] != len(raw):
                    text = (plan.destination / Path(*PurePosixPath(name).parts)).read_bytes()
                    if text.replace(b"\r\n", b"\n") == raw:
                        line_endings.append(name)
    missing = sorted(n for n in planned if n not in held)
    wrong_size = sorted(n for n in planned if n in held and sizes[n] is not None and held[n] != sizes[n] and n not in line_endings)
    no_size = sorted(n for n, r in planned.items() if r.size is None)
    extra = sorted(n for n in held if n not in planned)
    planned_bytes = sum(v or 0 for v in sizes.values())
    lines = [f"{package} ({plan.source_kind}, {plan.record_url})",
             f"  planned: {len(remote)} files, {planned_bytes / 1e9:.3f} GB; held: {len(held)} files, {sum(held.values()) / 1e9:.3f} GB",
             f"  planned files missing from the holdings: {len(missing)}" + (f" ({', '.join(missing[:5])})" if missing else ""),
             f"  planned files held with a different size: {len(wrong_size)}" + (f" ({', '.join(wrong_size[:5])})" if wrong_size else ""),
             f"  planned text files held with Windows line endings only: {len(line_endings)}" + (f" ({', '.join(line_endings)})" if line_endings else ""),
             f"  planned files with no size from the publisher: {len(no_size)}",
             f"  held files the fetch would not download: {len(extra)}" + (f" (for example {', '.join(extra[:3])})" if extra else "")]
    smallest = min((r for r in remote if r.size), key=lambda r: r.size)
    scratch = Path(tempfile.mkdtemp(prefix="large-fetch-check-"))
    try:
        target = scratch / Path(*PurePosixPath(smallest.name).parts)
        fetch._download(smallest.url, target, smallest.size)
        if plan.source_kind == "github":
            fetch._resolve_lfs(plan, smallest, target)
        publisher = fetch.verify_file(package, smallest.name, target)
        held_path = plan.destination / Path(*PurePosixPath(smallest.name).parts)
        same = held_path.is_file() and fetch._hash(target, "sha256") == fetch._hash(held_path, "sha256")
        if not same and held_path.is_file() and held_path.read_bytes().replace(b"\r\n", b"\n") == target.read_bytes():
            verdict = "yes apart from Windows line endings in the held copy"
        else:
            verdict = "yes" if same else "NO"
        lines.append(f"  smallest planned file downloaded to a scratch folder: {smallest.name} ({smallest.size:,} bytes)")
        lines.append(f"    publisher checksum: {publisher.split(' (sha256')[0]}")
        lines.append(f"    identical to the held copy (SHA-256): {verdict}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    lines.append(f"    scratch copy deleted: {'yes' if not scratch.exists() else 'NO'}")
    return lines


def main() -> None:
    lines = []
    for package in PACKAGES:
        lines += check(package)
        print(f"{package}: checked", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
