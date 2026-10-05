"""Local configuration for machine-specific paths. Read from config/local.toml, which is gitignored."""
import os
from pathlib import Path
import tomllib


def _load() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "local.toml"
    if not config_path.exists():
        return {}
    with config_path.open("rb") as config_file:
        return tomllib.load(config_file)


def data_root() -> Path:
    """Where the data holdings live. The FIELDDATA_DATA_ROOT environment variable overrides config/local.toml."""
    value = os.environ.get("FIELDDATA_DATA_ROOT") or _load().get("data_root")
    if not value:
        raise ValueError("set FIELDDATA_DATA_ROOT or define data_root in config/local.toml")
    return Path(value).expanduser()


def public_text(text: str) -> str:
    """Text safe to publish: the data root, the repository folder and home folders replaced by placeholders.
    Used for error messages that are saved into committed files."""
    import re
    try:
        text = text.replace(str(data_root()), "<data root>")
    except ValueError:
        pass
    text = text.replace(str(Path(__file__).resolve().parent.parent), "<repository>")
    return re.sub(r"(?:[A-Za-z]:)?[\\/](?:Users|home)[\\/][^\\/\s'\"]+", "<home>", text)
