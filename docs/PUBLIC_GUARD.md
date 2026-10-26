# Public boundary guard

This repository is public. Do not copy confidential names, records, results or
private source paths into it. Only rewritten, generic reusable code may be
transferred from private work.

## Install

Run `python scripts/install_hooks.py` after cloning. It sets local
`core.hooksPath` to the tracked `.githooks` directory. Git for Windows runs the
shell hook, which invokes `python` from PATH. The installer refuses to replace
an existing different hooks path.

The policy stays outside this repository. By default the guard reads the sibling
private checkout's `config/public_blocked_terms.txt`. Set `PUBLIC_GUARD_TERMS` to
another private policy file if needed. Missing, unreadable or empty policy is an
error and blocks commits, even with an override.

## Behavior

The hook checks only added lines in the staged zero-context diff, not unstaged
working-tree edits or unchanged historical lines. Deletions are allowed.
Renames are treated as removal plus addition so renamed content is checked.
Matching uses escaped literal terms with case-insensitive word boundaries,
so a term inside a longer word does not match. Every match reports the file,
new-file line number and matching term locally. There are no file exemptions.
Git's text diff is requested even for binary files. Non-text encodings,
compressed and encrypted contents may not expose readable added lines, so the
hook does not replace human review. The tree audit also decodes BOM-marked
UTF-16 files.

Run `python scripts/public_guard.py --tree` to inspect all tracked and
non-ignored untracked current source files. This does not read ignored data,
virtual environments, Git metadata or external data folders. Existing matches
are not deleted and do not block commits unless added in staged lines. Save audit
findings only outside this public repository with `--audit-output PATH`.

## Reviewed exception

Only after reviewing the exact staged match list and obtaining explicit
maintainer approval, set `PUBLIC_GUARD_REVIEWED_OVERRIDE=1` for one commit and
remove it immediately afterward. For example in PowerShell:

```powershell
$env:PUBLIC_GUARD_REVIEWED_OVERRIDE = "1"
try { git commit -m "Approved generic change" }
finally { Remove-Item Env:PUBLIC_GUARD_REVIEWED_OVERRIDE }
```

The hook still prints matches and an override warning. This is not permission
to publish confidential material. Policy-load failures cannot be overridden.
Hooks are local safeguards, not server enforcement. Install them in every clone.

## Test

Run `python -m pytest tests/test_public_guard.py -q`. Tests use isolated local
repositories and synthetic policy markers. One additional test reads a term
from the real external policy and adds it only inside a disposable repository
to demonstrate an actual rejected commit without publishing the term.
Tests also check unchanged historical lines, word boundaries,
staged-versus-unstaged checks, missing-policy failure and override checks.
