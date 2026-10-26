"""Install the tracked public boundary hook in this checkout.

Reads the hook and Git configuration, and writes only local Git configuration.
The installed hook invokes Python from the committing shell's PATH.
"""
from pathlib import Path
import subprocess


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    hook = root / ".githooks" / "pre-commit"
    if not hook.is_file():
        raise FileNotFoundError(hook)
    configured = subprocess.run(
        ["git", "config", "--local", "--get", "core.hooksPath"],
        cwd=root, capture_output=True, text=True,
    )
    if configured.returncode not in (0, 1):
        configured.check_returncode()
    if configured.returncode == 0 and configured.stdout.strip() != ".githooks":
        raise RuntimeError(
            f"Existing core.hooksPath={configured.stdout.strip()!r}. "
            "Review the existing hooks before replacing them."
        )
    subprocess.run(
        ["git", "config", "--local", "core.hooksPath", ".githooks"],
        cwd=root, check=True,
    )
    hook.chmod(hook.stat().st_mode | 0o111)
    print("Installed core.hooksPath=.githooks. The guard fails closed without its private policy.")


if __name__ == "__main__":
    main()
