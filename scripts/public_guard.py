"""Check added staged lines, or audit the Git-visible tree, against private policy.

Reads the staged zero-context diff by default. --tree reads tracked and non-ignored untracked files,
without following symlinks. It never reads external data folders. An optional
--audit-output writes findings only to an explicitly supplied external path.
The policy is external and must never be copied into this repository.
"""
from __future__ import annotations

import argparse
from collections import Counter
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TERMS = ROOT.parent / "battery-field-analysis" / "config" / "public_blocked_terms.txt"


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True,
    ).stdout


def terms() -> list[str]:
    path = Path(os.environ.get("PUBLIC_GUARD_TERMS", str(DEFAULT_TERMS)))
    values = [
        line.strip().casefold()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not values:
        raise ValueError("The private policy is empty.")
    return list(dict.fromkeys(values))


def matches(raw: bytes, policy: list[str]) -> list[tuple[int, str]]:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig", errors="surrogateescape")
    patterns = [(term, re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)) for term in policy]
    return [
        (number, term)
        for number, line in enumerate(text.splitlines(), 1)
        for term, pattern in patterns
        if pattern.search(line)
    ]


def added_lines(relative: str, policy: list[str]) -> list[tuple[int, str]]:
    patch = git(
        "diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-color",
        "--no-renames", "--text", "--unified=0", "--", relative,
    ).decode("utf-8", errors="surrogateescape")
    findings = []
    number = None
    for line in patch.splitlines():
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk:
            number = int(hunk[1])
        elif number is not None and line.startswith("+"):
            findings.extend((number, term) for _, term in matches(line[1:].encode(
                "utf-8", errors="surrogateescape"), policy))
            number += 1
        elif number is not None and line.startswith(" "):
            number += 1
    return findings


def scan(tree: bool, policy: list[str]) -> tuple[int, list[tuple[str, int, str]]]:
    if tree:
        names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    else:
        names = git("diff", "--cached", "--no-renames", "--name-only", "--diff-filter=ACMT", "-z")
    findings: list[tuple[str, int, str]] = []
    count = 0
    for name in sorted(set(names.split(b"\0")) - {b""}):
        relative = os.fsdecode(name)
        if tree:
            path = ROOT / relative
            if path.is_symlink():
                raise ValueError(f"Refusing to follow working-tree symlink: {relative}")
            if not path.exists():
                continue
            if not path.is_file():
                raise ValueError(f"Not a regular source file: {relative}")
            raw = path.read_bytes()
        count += 1
        found = matches(raw, policy) if tree else added_lines(relative, policy)
        findings.extend((relative, number, term) for number, term in found)
    return count, findings


def audit(path: Path, count: int, findings: list[tuple[str, int, str]]) -> None:
    path = path.resolve()
    if path.is_relative_to(ROOT):
        raise ValueError("Audit findings must be written outside this public repository.")
    lines = [
        "# Public repository boundary audit", "",
        "Reproduce from the public checkout with "
        "`python scripts/public_guard.py --tree --audit-output "
        r"..\battery-field-analysis\docs\PUBLIC_REPO_AUDIT.md`.", "",
        "Scope: all tracked and non-ignored untracked current working-tree files, "
        "including binary files. Git metadata, ignored data, virtual environments "
        "and generated caches are outside this source-tree audit. No external "
        "data folders were read. Matches use case-insensitive word boundaries, "
        "not proof that a source is confidential. Nothing was deleted.", "",
        f"Files inspected: {count}. Matching file/line/term occurrences: {len(findings)}. "
        f"Files with matches: {len({name for name, _, _ in findings})}.", "",
        "## Terms", "", "| Term | Occurrences |", "|---|---:|",
    ]
    for term, total in sorted(Counter(term for _, _, term in findings).items()):
        lines.append(f"| {term} | {total} |")
    lines += ["", "## Existing matches", "", "| File | Line | Term |", "|---|---:|---|"]
    for name, number, term in findings:
        escaped = name.replace("|", r"\|")
        lines.append(f"| {escaped} | {number} | {term} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", action="store_true", help="Audit the Git-visible source tree.")
    parser.add_argument("--audit-output", type=Path, help="Save an audit outside this repository.")
    args = parser.parse_args()
    if args.audit_output and not args.tree:
        parser.error("--audit-output requires --tree.")
    try:
        policy = terms()
        count, findings = scan(args.tree, policy)
        if args.audit_output:
            audit(args.audit_output, count, findings)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Public guard failed closed: {error}", file=sys.stderr)
        return 2
    for name, number, term in findings:
        print(f"{name}:{number}: blocked term {term!r}")
    print(f"Public guard: scanned {count} files; {len(findings)} matches.")
    if findings and not args.tree and os.environ.get("PUBLIC_GUARD_REVIEWED_OVERRIDE") == "1":
        print("WARNING: reviewed override enabled; matched staged content is being permitted.", file=sys.stderr)
        return 0
    if findings:
        if not args.tree:
            print("Commit blocked. Remove the staged content or obtain a reviewed override.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
