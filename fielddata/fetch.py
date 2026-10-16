"""Download registered data packages from their original public records."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from fielddata.config import data_root
from fielddata.registry import CANDIDATES, PACKAGES
from fielddata.registry import metadata as registry_metadata

ROOT = Path(__file__).resolve().parent.parent
CHECKSUMS = ROOT / "fielddata" / "reference_checksums.csv"
CHUNK_SIZE = 1024 * 1024


def _ssl_context() -> ssl.SSLContext:
    """The system's certificates plus the certifi bundle.

    Python from the python.org macOS installer ships without certificates until the user runs its
    "Install Certificates" command, so every download would fail with CERTIFICATE_VERIFY_FAILED. Adding
    certifi's bundle (a dependency of this package) makes downloads work without that step.
    """
    context = ssl.create_default_context()
    try:
        import certifi
        context.load_verify_locations(cafile=certifi.where())
    except ImportError:
        pass
    return context


_SSL = _ssl_context()


@dataclass(frozen=True)
class RemoteFile:
    name: str
    url: str
    size: int | None = None
    api_checksum: str | None = None


@dataclass(frozen=True)
class FetchPlan:
    package: str
    title: str
    source_kind: str
    record_url: str
    destination: Path
    expected_files: tuple[str, ...]
    automatic: bool


def default_root() -> Path:
    try:
        return data_root()
    except ValueError:
        print("No data folder is set, so files go to ./data inside this repository. To choose another folder, "
              "copy config/local.example.toml to config/local.toml and set data_root.", file=sys.stderr)
        return Path("data")


def source_kind(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "zenodo.org" in host or "10.5281/zenodo." in url:
        return "zenodo"
    if "figshare" in host or "10.6084/m9.figshare." in url:
        return "figshare"
    if host == "github.com":
        return "github"
    if "data.mendeley.com" in host or "10.17632/" in url:
        return "mendeley"
    if "purl.stanford.edu" in host or "10.25740/" in url:
        return "sdr"
    if "10.14459/" in url or "dataserv.ub.tum.de" in host:
        return "tumdataserv"
    return "manual"


# Download routes added for the on-deck candidates (v1.2 intake, 2026-10-12). Admitted releases on these hosts stay manual
# until the route is checked for them.
CANDIDATE_ONLY_KINDS = {"mendeley", "sdr", "tumdataserv"}
# fei_bus left this list on 2026-10-16: the Mendeley route returns its four held files with the held sizes and SHA-256.
# The bilfinger releases are held as the TUM data server's "Download all" data.zip, which the server builds on each request:
# a fresh copy has the same members (names, sizes, CRCs) but a new top-folder timestamp, so it never matches the held
# file's checksum. They stay manual (checked 2026-10-16 for bilfinger2025).
DOCUMENTED_MANUAL = {"bilfinger2024", "bilfinger2026"}

# one-command releases that are large or slow to download: shown before the download and on the dashboard card
FETCH_NOTES = {"aitio": "2.9 GB, slow host (Oxford ORA), allow ~15 min. Each file prints when it is done."}


def plan_package(package: str, to: str | Path | None = None) -> FetchPlan:
    metadata = registry_metadata(package)
    record_url = metadata["urls"]["data"]
    expected = metadata.get("data_files") or tuple(metadata.get("archives", {}).keys())
    base = Path(to) if to is not None else default_root()
    kind = "direct" if metadata.get("direct_files") else source_kind(record_url)
    if kind in CANDIDATE_ONLY_KINDS and package in DOCUMENTED_MANUAL:
        kind = "manual"  # these releases keep their documented manual route until it is re-verified for them
    return FetchPlan(
        package=package,
        title=metadata["title"],
        source_kind=kind,
        record_url=record_url,
        destination=base / Path(metadata["data_directory"]),
        expected_files=tuple(expected),
        automatic=kind != "manual",
    )


def _json(url: str, *, headers: dict[str, str] | None = None, data: bytes | None = None) -> Any:
    request = Request(url, headers={"User-Agent": "public-battery-field-data/1.0", **(headers or {})}, data=data)
    with urlopen(request, timeout=60, context=_SSL) as response:
        return json.load(response)


def _record_number(url: str) -> str:
    matches = re.findall(r"(?:records/|zenodo\.|figshare\.)(\d+)", url)
    if not matches:
        matches = re.findall(r"/(\d+)(?:$|[/?#])", url)
    if not matches:
        raise ValueError(f"could not find a record number in {url}")
    return matches[-1]


def _zenodo_files(plan: FetchPlan) -> list[RemoteFile]:
    record = _json(f"https://zenodo.org/api/records/{_record_number(plan.record_url)}")
    files = []
    for item in record.get("files", []):
        name = item.get("key") or item.get("filename")
        url = item.get("links", {}).get("content") or item.get("links", {}).get("self")
        if name and url and not _is_paper(name):
            files.append(RemoteFile(name, url, item.get("size"), item.get("checksum")))
    return files


def _figshare_files(plan: FetchPlan) -> list[RemoteFile]:
    article = _json(f"https://api.figshare.com/v2/articles/{_record_number(plan.record_url)}")
    files = []
    for item in article.get("files", []):
        name = item.get("name")
        url = item.get("download_url")
        if name and url and not _is_paper(name):
            checksum = f"md5:{item['supplied_md5']}" if item.get("supplied_md5") else None
            files.append(RemoteFile(name, url, item.get("size"), checksum))
    return files


def _mendeley_id_version(url: str) -> tuple[str, str]:
    match = re.search(r"(?:10\.17632/|datasets/)([a-z0-9]{10})(?:[./](\d+))?", url)
    if not match:
        raise ValueError(f"could not find a Mendeley Data id in {url}")
    return match.group(1), match.group(2) or "1"


def _mendeley_files(plan: FetchPlan) -> list[RemoteFile]:
    """Mendeley Data's public API lists each file with its size, SHA-256 and a direct download link."""
    dataset, version = _mendeley_id_version(plan.record_url)
    api = f"https://data.mendeley.com/public-api/datasets/{dataset}"
    # files in subfolders are not in the root listing; /folders/<version> lists every folder with its parent
    folders = {f["id"]: f for f in _json(f"{api}/folders/{version}")}

    def folder_path(folder_id: str) -> str:
        parts = []
        while folder_id in folders:
            parts.insert(0, folders[folder_id]["name"])
            folder_id = folders[folder_id].get("parent_id") or ""
        return "/".join(parts)

    listing = [("", item) for item in _json(f"{api}/files?folder_id=root&version={version}")]
    for folder_id in folders:
        prefix = folder_path(folder_id)
        listing += [(prefix, item) for item in _json(f"{api}/files?folder_id={folder_id}&version={version}")]
    files = []
    for prefix, item in listing:
        details = item.get("content_details", {})
        name, url = item.get("filename"), details.get("download_url")
        name = f"{prefix}/{name}" if prefix and name else name
        if name and url and not _is_paper(name):
            checksum = f"sha256:{details['sha256_hash']}" if details.get("sha256_hash") else None
            files.append(RemoteFile(name, url, details.get("size"), checksum))
    return files


def _sdr_files(plan: FetchPlan) -> list[RemoteFile]:
    """Stanford Digital Repository: the purl's JSON lists every file with size and MD5; files are served by stacks."""
    druid = re.search(r"([a-z]{2}\d{3}[a-z]{2}\d{4})", plan.record_url).group(1)
    record = _json(f"https://purl.stanford.edu/{druid}.json")
    files = []
    for group in record.get("structural", {}).get("contains", []):
        for item in group.get("structural", {}).get("contains", []):
            name = item["filename"]
            if _is_paper(name) or item.get("access", {}).get("download") not in (None, "world"):
                continue
            digests = {d["type"]: d["digest"] for d in item.get("hasMessageDigests", [])}
            checksum = f"md5:{digests['md5']}" if "md5" in digests else None
            files.append(RemoteFile(name, f"https://stacks.stanford.edu/file/druid:{druid}/{quote(name)}", item.get("size"), checksum))
    return files


def _tum_files(plan: FetchPlan) -> list[RemoteFile]:
    """TUM data server (mediaTUM records): a public Nextcloud share named m<record number>, no password.

    Listing the share needs the session cookie and request token its web page sets. The files themselves download
    with a plain request. The share's own <name>.sha512 file, where present, gives the publisher's SHA-512 per file.
    """
    import http.cookiejar
    from urllib.request import HTTPCookieProcessor, build_opener, HTTPSHandler

    share = "m" + re.search(r"mp(\d+)|/s/m(\d+)", plan.record_url).group(1 if "mp" in plan.record_url else 2)
    base = "https://dataserv.ub.tum.de"
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()), HTTPSHandler(context=_SSL))
    page = opener.open(Request(f"{base}/index.php/s/{share}", headers={"User-Agent": "public-battery-field-data/1.0"}), timeout=60).read().decode()
    token = re.search(r'data-requesttoken="([^"]+)"', page).group(1)
    listing = opener.open(Request(f"{base}/public.php/dav/files/{share}/", method="PROPFIND", headers={
        "Depth": "infinity", "requesttoken": token, "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "public-battery-field-data/1.0"}), timeout=300).read().decode()
    entries = []
    for response in re.findall(r"<d:response>(.*?)</d:response>", listing, re.S):
        size = re.search(r"<d:getcontentlength>(\d+)", response)
        if size:
            href = re.search(r"<d:href>(.*?)</d:href>", response).group(1)
            name = re.sub(r"%([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), href.split(f"/{share}/", 1)[1])
            entries.append((name, f"{base}/public.php/dav/files/{share}/{quote(name)}", int(size.group(1))))
    sums = {}
    for name, url, _ in entries:
        if name.endswith(".sha512"):
            text = urlopen(Request(url, headers={"User-Agent": "public-battery-field-data/1.0"}), timeout=60, context=_SSL).read().decode()
            sums.update({line.split(maxsplit=1)[1].lstrip("*").strip(): line.split()[0] for line in text.splitlines() if line.strip()})
    return [RemoteFile(name, url, size, f"sha512:{sums[name]}" if name in sums else None)
            for name, url, size in entries if not _is_paper(name)]


# GitHub releases whose repository mixes data and code: files matching the pattern are the released data and go
# under data/; every other repository file goes under data/code/, the same layout as the reference holdings.
GITHUB_DATA_FILES = {"deng": r"^#\d+\.rar$"}


def _github_parts(url: str) -> tuple[str, str]:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"invalid GitHub repository URL: {url}")
    return parts[0], parts[1].removesuffix(".git")


def _github_files(plan: FetchPlan) -> list[RemoteFile]:
    owner, repository = _github_parts(plan.record_url)
    info = _json(f"https://api.github.com/repos/{owner}/{repository}")
    branch = info["default_branch"]
    tree = _json(f"https://api.github.com/repos/{owner}/{repository}/git/trees/{quote(branch, safe='')}?recursive=1")
    prefixes = [name[:-3].rstrip("/") for name in plan.expected_files if name.endswith("/**")]
    prefix = prefixes[0] if prefixes else ""
    files = []
    for item in tree.get("tree", []):
        path = item.get("path", "")
        if item.get("type") != "blob" or _is_paper(path):
            continue
        raw = f"https://raw.githubusercontent.com/{owner}/{repository}/{quote(branch, safe='')}/{quote(path)}"
        destination = f"{prefix}/{path}" if prefix else path
        data_pattern = GITHUB_DATA_FILES.get(plan.package)
        if data_pattern and not re.search(data_pattern, path):
            destination = f"code/{path}"   # the repository's own files, kept apart from the released data
        files.append(RemoteFile(destination, raw, item.get("size")))
    return files


def resolve_files(plan: FetchPlan) -> list[RemoteFile]:
    if plan.source_kind == "zenodo":
        return _zenodo_files(plan)
    if plan.source_kind == "figshare":
        return _figshare_files(plan)
    if plan.source_kind == "github":
        return _github_files(plan)
    if plan.source_kind == "mendeley":
        return _mendeley_files(plan)
    if plan.source_kind == "sdr":
        return _sdr_files(plan)
    if plan.source_kind == "tumdataserv":
        return _tum_files(plan)
    if plan.source_kind == "direct":  # a record whose file URLs are listed in the registry
        return [RemoteFile(name, url, size, None) for name, url, size in registry_metadata(plan.package)["direct_files"]]
    return []


def _is_paper(name: str) -> bool:
    path = PurePosixPath(name.lower())
    return path.suffix == ".pdf" or any(part in {"paper", "papers"} for part in path.parts)


def _checksum_rows(package: str) -> list[dict[str, str]]:
    with CHECKSUMS.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row["package"] == package]


def _checksum_for(package: str, remote_name: str) -> tuple[str, str] | None:
    normalized = remote_name.replace("\\", "/").lstrip("/")
    candidates = {normalized, f"data/{normalized}", PurePosixPath(normalized).name}
    for row in _checksum_rows(package):
        recorded = row["file"].replace("\\", "/")
        if " :: " in recorded or "*" in recorded:
            continue
        if recorded in candidates or recorded.removeprefix("data/") in candidates:
            algorithm = row["algorithm"].lower().strip()
            expected = row["publisher_value"].lower().strip()
            if algorithm in hashlib.algorithms_available and re.fullmatch(r"[0-9a-f]+", expected):
                return algorithm, expected
    return None


def _hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(
    url: str,
    destination: Path,
    expected_size: int | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    resume_headers = {"Range": f"bytes={offset}-"} if offset else {}
    request = Request(url, headers={"User-Agent": "public-battery-field-data/1.0", **(headers or {}), **resume_headers})
    try:
        response = urlopen(request, timeout=120, context=_SSL)
    except HTTPError as error:
        if error.code == 416 and expected_size is not None and offset == expected_size:
            partial.replace(destination)
            return
        raise
    status = getattr(response, "status", response.getcode())
    mode = "ab" if offset and status == 206 else "wb"
    with response, partial.open(mode) as handle:
        while chunk := response.read(CHUNK_SIZE):
            handle.write(chunk)
    if expected_size is not None and partial.stat().st_size != expected_size:
        raise OSError(f"downloaded {partial.stat().st_size:,} bytes, expected {expected_size:,}")
    partial.replace(destination)


def _lfs_pointer(path: Path) -> tuple[str, int] | None:
    if path.stat().st_size > 2048:
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("version https://git-lfs.github.com/spec/v1"):
        return None
    oid = re.search(r"oid sha256:([0-9a-f]{64})", text)
    size = re.search(r"size (\d+)", text)
    return (oid.group(1), int(size.group(1))) if oid and size else None


def _resolve_lfs(plan: FetchPlan, remote: RemoteFile, destination: Path) -> None:
    pointer = _lfs_pointer(destination)
    if pointer is None:
        return
    owner, repository = _github_parts(plan.record_url)
    oid, size = pointer
    payload = json.dumps({"operation": "download", "transfers": ["basic"], "objects": [{"oid": oid, "size": size}]}).encode()
    result = _json(
        f"https://github.com/{owner}/{repository}.git/info/lfs/objects/batch",
        headers={"Accept": "application/vnd.git-lfs+json", "Content-Type": "application/vnd.git-lfs+json"},
        data=payload,
    )
    action = result["objects"][0]["actions"]["download"]
    destination.unlink()
    _download(action["href"], destination, size, action.get("header"))


def verify_file(package: str, remote_name: str, path: Path) -> str:
    reference = _checksum_for(package, remote_name)
    if reference is None:
        measured = _hash(path, "sha256")
        recorded = registry_metadata(package).get("own_sha256", {}).get(PurePosixPath(remote_name).name)
        if recorded:  # no publisher checksum, but this collection recorded one when it first fetched the file
            return "matched our recorded sha256 (no publisher checksum)" if measured == recorded else f"MISMATCH (our recorded sha256 {recorded}, measured {measured})"
        return f"own-hash only (sha256 {measured})"
    algorithm, expected = reference
    measured = _hash(path, algorithm)
    return "matched" if measured == expected else f"MISMATCH ({algorithm} expected {expected}, measured {measured})"


def _size_text(value: str) -> str:
    if value.isdigit():
        size = int(value)
        return f"about {size / 1e9:.1f} GB" if size >= 1e8 else f"about {size / 1e6:.1f} MB" if size >= 1e5 else f"{size:,} bytes"
    return value if value else "size not stated"


def _reference_sizes(package: str) -> dict[str, str]:
    """Bytes per data file from the maintainer's verify run on the reference holdings (reports/verify_log.csv)."""
    log = Path(__file__).resolve().parents[1] / "reports" / "verify_log.csv"
    if not log.exists():
        return {}
    with log.open(newline="", encoding="utf-8") as handle:
        return {row["file"].removeprefix("data/"): row["bytes"] for row in csv.DictReader(handle)
                if row["package"] == package and row["file"].startswith("data/") and row["bytes"].isdigit()}


# Host-specific hints for the manual downloads.
MANUAL_NOTES = {
    "bilfinger2024": ["data.zip is the \"Download all\" zip of the mediaTUM data-server share linked from the record."],
    "bilfinger2026": ["data.zip is the \"Download all\" zip of the mediaTUM data-server share linked from the record."],
    "bilfinger2025": ["data.zip is the \"Download all\" zip of the mediaTUM data-server share linked from the record (https://dataserv.ub.tum.de/index.php/s/m1765567, about 306 MB).",
                      "From a script the share's download needs its session cookie; without it the server returns a small stub, so check the size."],
    "ku_leuven_bev": ["the zip is Dataverse's \"Access dataset > Download ZIP\" on the KU Leuven RDR page."],
    "changan": ["the two files are one split zip of about 74 GB (RAW_DATA.z01 51.5 GB, RAW_DATA.zip 22.8 GB); check you have the space first.",
                "save both in a subfolder named raw inside the folder in step 3 (create it), and do not unzip them."],
}


def print_manual(plan: FetchPlan) -> None:
    rows = _checksum_rows(plan.package)
    sizes = _reference_sizes(plan.package)
    sizes.update({row["file"].removeprefix("data/"): row["bytes_when_recorded"] for row in rows if row["bytes_when_recorded"]})
    print(f"{plan.package} requires a manual download.")
    print(f"1. Open {plan.record_url}")
    print("2. Download the data files listed below. Do not download papers.")
    for name in plan.expected_files:
        print(f"   - {name} ({_size_text(sizes.get(name, ''))})")
    for line in MANUAL_NOTES.get(plan.package, []):
        print(f"   Note: {line}")
    if "publications.rwth-aachen.de" in plan.record_url:
        print("   Note: RWTH Publications needs a web browser; its download links do not work from a script.")
    print(f"3. Save the files under {plan.destination}")
    print(f"4. Run python -m fielddata.verify {plan.package} to check the saved files.")


# Releases whose automatic download covers only part of what the publisher released: package -> manual steps
# for the rest, printed after the automatic part. As of October 2026.
PARTLY_MANUAL = {
    "ppl": [
        "The cell-level data (about 66.6 GB, one zip per month from December 2016) is not in the GitHub repository.",
        "The repository's file BESS-Analysis/Cell_Level_Data links to it on a Box share:",
        "https://app.box.com/s/s0ns2o1i4q0f7yxcnn96df7e5px5k0s6",
        "Download the monthly zips in a web browser and save them in a folder named cell_level next to BESS-Analysis.",
        "The ppl loader reads only the GitHub files, so this step is needed only to use the cell-level data yourself.",
    ],
}
ROUTE_DATE = "October 2026"


def route(package: str) -> str:
    """How a release downloads, as of October 2026: "one command", "manual (browser)" or "partly manual"."""
    if not plan_package(package, to="data").automatic:
        return "manual (browser)"
    return "partly manual" if package in PARTLY_MANUAL else "one command"


def print_partly_manual(plan: FetchPlan) -> None:
    print(f"{plan.package} is only partly downloaded by this command. One more step is manual:")
    for line in PARTLY_MANUAL[plan.package]:
        print(f"   {line}")


def fetch(plan: FetchPlan) -> int:
    if not plan.automatic:
        print_manual(plan)
        return 0
    files = resolve_files(plan)
    if not files:
        raise RuntimeError(f"the {plan.source_kind} record returned no data files")
    print(f"Fetching {plan.package}: {len(files)} data file(s) from {plan.record_url}")
    if plan.package in FETCH_NOTES:
        print(f"Note: {FETCH_NOTES[plan.package]}")
    failures = 0
    for index, remote in enumerate(files, start=1):
        destination = plan.destination / Path(*PurePosixPath(remote.name).parts)
        print(f"{index}. {remote.name}")
        if destination.exists() and (remote.size is None or destination.stat().st_size == remote.size):
            print("   already present; checking")
        else:
            _download(remote.url, destination, remote.size)
        if plan.source_kind == "github":
            _resolve_lfs(plan, remote, destination)
        result = verify_file(plan.package, remote.name, destination)
        print(f"   {result}")
        failures += result.startswith("MISMATCH")
    print(f"Saved under {plan.destination}")
    if plan.package in PARTLY_MANUAL:
        print_partly_manual(plan)
    return 1 if failures else 0


def list_packages() -> None:
    for package in PACKAGES:
        plan = plan_package(package)
        how = route(package) + (f" ({plan.source_kind})" if plan.automatic else "")
        print(f"{package:20} {how:28} {plan.record_url}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("package", nargs="?", choices=sorted(PACKAGES) + sorted(CANDIDATES))
    result.add_argument("--to", type=Path, help="download root; defaults to config/local.toml data_root or ./data")
    result.add_argument("--list", action="store_true", help="list packages and download routes")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.list:
        list_packages()
        return 0
    if not args.package:
        parser().error("provide a package or --list")
    try:
        return fetch(plan_package(args.package, args.to))
    except (HTTPError, OSError, RuntimeError, ValueError) as error:
        print(f"Download failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
