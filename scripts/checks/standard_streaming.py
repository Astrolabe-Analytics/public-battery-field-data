"""Check public streaming standard interfaces with synthetic loader inputs.

Reads source code and synthetic fixtures only, never released data or SSD copies.
Writes regression output and a plain-language note under reports/checks/standard_streaming.
"""
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "reports" / "checks" / "standard_streaming"
    output.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_standard.py", "tests/test_processed.py",
         "tests/test_loaders.py", "tests/test_loaders_all.py::test_snippets", "tests/test_aitio.py",
         "tests/test_binary_files.py", "-q"],
        cwd=root, capture_output=True, text=True,
    )
    (output / "tests.txt").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    (output / "README.md").write_text(
        "# Streaming standard interface checks\n\n"
        "Reproduce with `python scripts/checks/standard_streaming.py`.\n\n"
        "Synthetic tests check lazy, single-pass Schaeffer and snippet archive conversion, "
        "raw/standard equivalence, source order and duplicate timestamps, snippet-relative time, "
        "unit identity, Xie bulk reads, pure loader-batch conversion and explicit input errors. "
        "Existing mapping, raw-loader and processed-copy regressions are included. "
        f"The test command {'passed' if result.returncode == 0 else 'failed'}. "
        "See tests.txt for its output. No held released data or SSD processed copies were read or written. "
        "This does not revalidate or rebuild caches after the producing-code fingerprint change.\n",
        encoding="utf-8", newline="\n",
    )
    print(result.stdout, result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
