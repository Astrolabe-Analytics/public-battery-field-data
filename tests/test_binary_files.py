"""Committed binary files are intact: no newline conversion has touched them.

A PNG whose CRLF signature bytes were turned into LF (89 50 4e 47 0a 1a 0a 00 instead of 89 50 4e 47 0d 0a 1a 0a)
cannot be opened by a browser; a zip-based file (.docx, .xlsx, .zip) damaged the same way fails its checks.
"""
import subprocess
import zipfile
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def tracked(*suffixes):
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
        names = [n for n in out.split("\0") if n]
    except (OSError, subprocess.CalledProcessError):  # not a git checkout (a downloaded ZIP): check the files present
        names = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                 if p.is_file() and not {".git", ".venv", "data"} & set(p.relative_to(ROOT).parts)]
    return sorted(n for n in names if n.lower().endswith(suffixes) and (ROOT / n).is_file())


PNGS = tracked(".png")
ZIPS = tracked(".docx", ".xlsx", ".pptx", ".zip")


def test_there_are_files_to_check():
    assert PNGS


@pytest.mark.parametrize("name", PNGS)
def test_png_signature_and_opens(name):
    path = ROOT / name
    assert path.read_bytes()[:8] == PNG_SIGNATURE, f"{name}: PNG signature damaged (newline conversion?)"
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        image.load()


@pytest.mark.parametrize("name", ZIPS)
def test_zip_based_file_opens(name):
    with zipfile.ZipFile(ROOT / name) as archive:
        assert archive.testzip() is None, f"{name}: a member fails its CRC check"
