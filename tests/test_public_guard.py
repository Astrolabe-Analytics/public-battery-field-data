"""Test the boundary guard with synthetic files and the external policy only.

Creates disposable Git repositories inside this checkout's Git metadata.
Reads the guard and hook scripts, and removes all test files afterward.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

import pytest


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def repository():
    with tempfile.TemporaryDirectory(prefix="guard-test-", dir=ROOT / ".git") as folder:
        root = Path(folder)
        (root / "scripts").mkdir()
        (root / ".githooks").mkdir()
        for relative in ("scripts/public_guard.py", "scripts/install_hooks.py", ".githooks/pre-commit"):
            shutil.copyfile(ROOT / relative, root / relative)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        for key, value in (("user.name", "Guard Test"), ("user.email", "guard@example.invalid"),
                           ("commit.gpgsign", "false")):
            subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
        policy = root / ".git" / "private-policy.txt"
        policy.write_text("sensitive-example\nsecond marker\n", encoding="utf-8")
        environment = dict(os.environ, PUBLIC_GUARD_TERMS=str(policy))
        environment.pop("PUBLIC_GUARD_REVIEWED_OVERRIDE", None)

        def run(*args, env=None):
            return subprocess.run(
                args, cwd=root, env=environment if env is None else env,
                capture_output=True, text=True, encoding="utf-8",
            )

        installed = run("python", "scripts/install_hooks.py")
        assert installed.returncode == 0, installed.stderr
        yield root, policy, environment, run


def stage(root, run, text, name="example.txt"):
    (root / name).write_text(text, encoding="utf-8")
    result = run("git", "add", "--", name)
    assert result.returncode == 0, result.stderr


def test_real_commit_is_blocked(repository):
    root, _, _, run = repository
    stage(root, run, "ordinary\nSENSITIVE-EXAMPLE\n")
    result = run("git", "commit", "-m", "Synthetic blocked guard test")
    print("\nBlocked test commit:\n" + result.stdout + result.stderr)
    assert result.returncode != 0
    assert "example.txt:2:" in result.stdout + result.stderr
    assert "Commit blocked" in result.stderr
    assert run("git", "rev-parse", "--verify", "HEAD").returncode != 0


def test_index_not_working_tree(repository):
    root, _, _, run = repository
    stage(root, run, "SENSITIVE-EXAMPLE\n")
    (root / "example.txt").write_text("safe\n", encoding="utf-8")
    assert run("python", "scripts/public_guard.py").returncode == 1
    stage(root, run, "safe\n")
    (root / "example.txt").write_text("SENSITIVE-EXAMPLE\n", encoding="utf-8")
    assert run("python", "scripts/public_guard.py").returncode == 0


def test_word_boundaries_and_multiple_lines(repository):
    root, _, _, run = repository
    stage(root, run, "prefixSensitive-exampleSuffix\nSECOND MARKER\n")
    result = run("python", "scripts/public_guard.py")
    assert result.returncode == 1
    assert "example.txt:1:" not in result.stdout and "example.txt:2:" in result.stdout


def test_unchanged_historical_match_is_allowed(repository):
    root, _, environment, run = repository
    stage(root, run, "SENSITIVE-EXAMPLE\noriginal\n")
    result = run(
        "git", "commit", "-m", "Synthetic historical fixture",
        env=dict(environment, PUBLIC_GUARD_REVIEWED_OVERRIDE="1"),
    )
    assert result.returncode == 0, result.stderr
    stage(root, run, "SENSITIVE-EXAMPLE\nnew safe line\n")
    result = run("git", "commit", "-m", "Change only safe lines")
    assert result.returncode == 0, result.stderr


def test_real_private_policy_blocks_commit(repository):
    root, _, environment, run = repository
    policy = Path(os.environ.get(
        "PUBLIC_GUARD_TERMS",
        str(ROOT.parent / "battery-field-analysis" / "config" / "public_blocked_terms.txt"),
    )).resolve()
    real_term = next(
        line.strip() for line in policy.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    stage(root, run, "ordinary\n" + real_term.upper() + "\n")
    result = run(
        "git", "commit", "-m", "Real external policy blocked test",
        env=dict(environment, PUBLIC_GUARD_TERMS=str(policy)),
    )
    print("\nReal-policy blocked test commit:\n" + result.stdout + result.stderr)
    assert result.returncode != 0
    assert "example.txt:2:" in result.stdout + result.stderr
    assert "Commit blocked" in result.stderr
    assert run("git", "rev-parse", "--verify", "HEAD").returncode != 0


def test_real_policy_terms_inside_longer_words_do_not_match(repository):
    root, _, environment, run = repository
    policy = Path(os.environ.get(
        "PUBLIC_GUARD_TERMS",
        str(ROOT.parent / "battery-field-analysis" / "config" / "public_blocked_terms.txt"),
    )).resolve()
    values = [
        line.strip() for line in policy.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    stage(root, run, "\n".join("prefix" + term + "suffix" for term in values) + "\n")
    result = run(
        "python", "scripts/public_guard.py",
        env=dict(environment, PUBLIC_GUARD_TERMS=str(policy)),
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("mode", ["missing", "empty"])
def test_policy_fails_closed_even_with_override(repository, mode):
    root, policy, environment, run = repository
    stage(root, run, "safe\n")
    if mode == "missing":
        policy.unlink()
    else:
        policy.write_text("# no policy\n", encoding="utf-8")
    result = run(
        "python", "scripts/public_guard.py",
        env=dict(environment, PUBLIC_GUARD_REVIEWED_OVERRIDE="1"),
    )
    assert result.returncode == 2
    assert "failed closed" in result.stderr


def test_override_is_explicit_and_visible(repository):
    root, _, environment, run = repository
    stage(root, run, "SENSITIVE-EXAMPLE\n")
    assert run(
        "python", "scripts/public_guard.py",
        env=dict(environment, PUBLIC_GUARD_REVIEWED_OVERRIDE="true"),
    ).returncode == 1
    result = run(
        "python", "scripts/public_guard.py",
        env=dict(environment, PUBLIC_GUARD_REVIEWED_OVERRIDE="1"),
    )
    assert result.returncode == 0
    assert "example.txt:1:" in result.stdout and "WARNING" in result.stderr


def test_binary_added_lines_and_utf16_tree_are_scanned(repository):
    root, _, _, run = repository
    (root / "binary.bin").write_bytes(b"\0first\nSENSITIVE-EXAMPLE\0")
    (root / "wide.txt").write_bytes("first\nSECOND MARKER\n".encode("utf-16"))
    assert run("git", "add", "--", "binary.bin", "wide.txt").returncode == 0
    result = run("python", "scripts/public_guard.py")
    assert result.returncode == 1
    assert "binary.bin:2:" in result.stdout
    tree = run("python", "scripts/public_guard.py", "--tree")
    assert tree.returncode == 1 and "wide.txt:2:" in tree.stdout


def test_tree_includes_untracked_and_audit_stays_external(repository):
    root, _, _, run = repository
    (root / "untracked.txt").write_text("SECOND MARKER\n", encoding="utf-8")
    result = run("python", "scripts/public_guard.py", "--tree")
    assert result.returncode == 1 and "untracked.txt:1:" in result.stdout
    result = run(
        "python", "scripts/public_guard.py", "--tree", "--audit-output", str(root / "audit.md"),
    )
    assert result.returncode == 2
    assert not (root / "audit.md").exists()


def test_safe_commit_and_deleted_file(repository):
    root, _, _, run = repository
    stage(root, run, "safe\n")
    result = run("git", "commit", "-m", "Safe synthetic fixture")
    assert result.returncode == 0, result.stderr
    assert run("git", "rm", "--", "example.txt").returncode == 0
    assert run("python", "scripts/public_guard.py").returncode == 0


def test_renamed_content_is_checked(repository):
    root, _, environment, run = repository
    stage(root, run, "SENSITIVE-EXAMPLE\n")
    assert run(
        "git", "commit", "-m", "Synthetic rename fixture",
        env=dict(environment, PUBLIC_GUARD_REVIEWED_OVERRIDE="1"),
    ).returncode == 0
    assert run("git", "mv", "example.txt", "renamed.txt").returncode == 0
    result = run("python", "scripts/public_guard.py")
    assert result.returncode == 1
    assert "renamed.txt:1:" in result.stdout


def test_installer_preserves_existing_hook_configuration(repository):
    _, _, _, run = repository
    assert run("git", "config", "--local", "core.hooksPath", "other-hooks").returncode == 0
    result = run("python", "scripts/install_hooks.py")
    assert result.returncode != 0
    assert run("git", "config", "--local", "--get", "core.hooksPath").stdout.strip() == "other-hooks"
