"""Build Changan through its loader using 7-Zip when the native libarchive DLL is absent.

Reads held Changan split-archive data through fielddata.load. Writes temporary RAR streams under the SSD
processed root, the processed copy, and the existing Layer 2 repair reports.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata import processed

_BLOCK_SIZE = 1 << 20


def _seven_zip() -> str:
    executable = shutil.which("7z.exe") or shutil.which("7z")
    if executable:
        return executable
    fallback = Path(r"C:\Program Files\7-Zip\7z.exe")
    if fallback.is_file():
        return str(fallback)
    raise FileNotFoundError("Changan Windows fallback requires 7z.exe")


class _Entry:
    def __init__(self, reader: _SevenZipReader, pathname: str):
        self.reader = reader
        self.pathname = pathname

    def get_blocks(self):
        yield from self.reader.blocks()


class _SevenZipReader:
    def __init__(self, raw):
        self.raw = raw
        self.archive_path: Path | None = None
        self.member: str | None = None
        self.process: subprocess.Popen | None = None
        self.entry: _Entry | None = None

    def __enter__(self):
        root = processed.cache_root()
        root.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(dir=root, suffix=".rar", delete=False) as handle:
                self.archive_path = Path(handle.name)
                shutil.copyfileobj(self.raw, handle, _BLOCK_SIZE)
            listing = subprocess.run(
                [_seven_zip(), "l", "-slt", "-bd", str(self.archive_path)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            members = [
                line.removeprefix("Path = ").strip()
                for line in listing.stdout.splitlines()
                if line.startswith("Path = ") and line.lower().endswith(".csv")
            ]
            if len(members) != 1:
                raise ValueError(f"expected one CSV in Changan vehicle RAR, found {len(members)}")
            self.member = members[0]
            self.entry = _Entry(self, self.member)
            return self
        except Exception:
            self.close()
            raise

    def __iter__(self):
        if self.entry is None:
            raise RuntimeError("Changan RAR reader has not been entered")
        yield self.entry

    def blocks(self):
        if self.archive_path is None or self.member is None:
            raise RuntimeError("Changan RAR reader is not ready")
        self.process = subprocess.Popen(
            [_seven_zip(), "x", "-so", "-bd", "-bb0", "-y", str(self.archive_path), self.member],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if self.process.stdout is None or self.process.stderr is None:
            raise RuntimeError("7-Zip process did not provide its configured pipes")
        try:
            while block := self.process.stdout.read(_BLOCK_SIZE):
                yield block
            error = self.process.stderr.read().decode("utf-8", errors="replace")
            returncode = self.process.wait()
            if returncode:
                raise RuntimeError(f"7-Zip failed to extract Changan CSV: {error[-2000:]}")
        finally:
            self._stop_process()

    def _stop_process(self):
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
        if self.process.stdout is not None:
            self.process.stdout.close()
        if self.process.stderr is not None:
            self.process.stderr.close()
        self.process = None

    def close(self):
        self._stop_process()
        if self.archive_path is not None:
            self.archive_path.unlink(missing_ok=True)
            self.archive_path = None
        self.raw.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _stream_reader(raw):
    return _SevenZipReader(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="read five rows from vin1 through the Changan loader")
    args = parser.parse_args()

    shim = types.ModuleType("libarchive")
    shim.stream_reader = _stream_reader
    sys.modules["libarchive"] = shim

    import fielddata

    if args.smoke:
        frame = fielddata.load("changan", unit="vin1", nrows=5)
        print(f"Changan loader smoke check: rows={len(frame)}, columns={len(frame.columns)}")
        return

    from scripts.checks.layer2_failed_releases import run

    run(["changan"])


if __name__ == "__main__":
    main()
