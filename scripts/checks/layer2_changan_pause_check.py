"""Check the stopped Changan build and record free space.

Reads the Windows process table and free-space metadata for the requested drive.
Writes a reproducible pause-check report under reports/checks/layer2_failed_releases/.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--drive", default="D:\\")
    args = parser.parse_args()

    process_check = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            f"$p = Get-Process -Id {args.pid} -ErrorAction SilentlyContinue; "
            "if ($null -eq $p) { 'STOPPED' } else { 'RUNNING' }",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    process_status = process_check.stdout.strip()
    free_bytes = shutil.disk_usage(args.drive).free
    report = (
        f"Changan build process PID {args.pid}: {process_status}\n"
        f"Free space on {args.drive}: {free_bytes} bytes\n"
    )

    output = Path("reports/checks/layer2_failed_releases/changan_pause_check.txt")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(report)
    print(report, end="")


if __name__ == "__main__":
    main()
