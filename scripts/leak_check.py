"""Fail when tracked text contains private paths, identities, or coordination terms."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAFE_EMAILS = {"data@astrolabe-analytics.com"}
ALLOWLIST = {
    "AGENTS.md": {"coordination-rule"},
    "SHIP.md": {"coordination-record"},
    "notebooks/deng.ipynb": {"saved-output-debt"},
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def allowed(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in ALLOWLIST)


def scan() -> tuple[list[str], list[str]]:
    forbidden = [
        ("maintainer username", re.compile("rc" + "mas", re.I)),
        ("drive-letter data path", re.compile(r"(?<![A-Z0-9_])(?:G|D):(?:\\)+[A-Z]", re.I)),
        ("shared-drive path", re.compile("Shared " + "drives", re.I)),
        ("internal archive term", re.compile("at" + "tic", re.I)),
        ("internal collaboration term", re.compile("cow" + "ork", re.I)),
        ("internal coordination term", re.compile(r"\b" + "la" + r"ne\b", re.I)),
    ]
    email = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
    # base64 image data in notebooks and their HTML exports can spell a term by chance
    image_data = re.compile(r'(?:"image/png": "|data:image/png;base64,)[A-Za-z0-9+/=]+')
    hits: list[str] = []
    allowlisted: list[str] = []
    for file_path in tracked_files():
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(ROOT).as_posix()
        try:
            raw = file_path.read_bytes()
            if b"\0" in raw:
                continue
            lines = raw.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            line = image_data.sub("", line)
            findings = [label for label, pattern in forbidden if pattern.search(line)]
            findings.extend("personal email" for value in email.findall(line) if value.lower() not in SAFE_EMAILS)
            for finding in findings:
                item = f"{relative}:{number}: {finding}: {line.strip()}"
                (allowlisted if allowed(relative) else hits).append(item)
    return hits, allowlisted


def main() -> int:
    hits, allowlisted = scan()
    for item in allowlisted:
        print(f"ALLOWLISTED {item}")
    for item in hits:
        print(f"LEAK {item}")
    print(f"leaks={len(hits)} allowlisted={len(allowlisted)}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
