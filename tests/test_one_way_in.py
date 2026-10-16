"""Released files are read only through fielddata (loaders, fetch, verify). Nothing else may open them.

This test scans scripts, the app, the MCP server and every notebook's code cells for direct data access.
Inventory of file names and sizes (scripts/facts/_common.py) and reading papers (check_citations.py) are the
only exceptions. If this test fails, move the reading into the package loader and call it from there.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECT = re.compile(r"data_root\(|released_directory\(|\bzipfile\b|\btarfile\b|libarchive|torchfree|pyarrow\.parquet|zipfile_deflate64|read_pickle\(|read_feather\(")
ALLOWED = {
    "scripts/facts/_common.py": {"released_directory(", "data_root("},  # file inventory: names and sizes only
    "scripts/facts/check_citations.py": {"data_root("},  # papers and supplementary PDFs, not data
    # on-deck candidates have no loader yet (intake phase 1, 2026-10-13): their quick facts list archives and read
    # headers directly, read-only. Remove this exception once each candidate's loader exists.
    "scripts/checks/ondeck_facts.py": {"zipfile"},
    # screening check of Bilfinger 2025 (on deck, 2026-10-15): reads the screening copy's zip read-only until it has a loader
    "scripts/checks/bilfinger2025_screen.py": {"zipfile", "read_feather("},
    # Maintainer's decision (2026-10-13): pickled releases are converted once in a throwaway environment; this script runs
    # only there (never in the project's .venv) and the loaders read its Parquet copies
    "scripts/checks/convert_pickles/convert.py": {"zipfile", "read_pickle(", "pyarrow.parquet"},  # writes the Parquet copies
}


def _sources():
    for path in [*ROOT.glob("scripts/**/*.py"), *ROOT.glob("app/**/*.py"), *ROOT.glob("mcp_server/**/*.py")]:
        yield path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8")
    for path in ROOT.glob("notebooks/*.ipynb"):
        cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
        yield path.relative_to(ROOT).as_posix(), "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")


def test_released_files_are_read_only_through_loaders():
    problems = []
    for name, text in _sources():
        for number, line in enumerate(text.splitlines(), 1):
            for match in DIRECT.finditer(line):
                if match.group(0) not in ALLOWED.get(name, set()):
                    problems.append(f"{name}:{number}: {line.strip()[:100]}")
    assert not problems, "direct data access outside the loaders:\n" + "\n".join(problems)
