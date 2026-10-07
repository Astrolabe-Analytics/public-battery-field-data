"""Load public battery-field data packages."""
from importlib import import_module
from pathlib import Path


class NotDownloaded(FileNotFoundError):
    """A release, or a file in it, is not in the data folder. The message says which fetch command to run.

    In Jupyter it is shown as its message alone, without a traceback."""

    def _render_traceback_(self):
        return [str(self)]


def _loader(package_id):
    return import_module(f"fielddata.loaders.{package_id.replace('-', '_')}")


def _folder(package_id):
    """The release's data folder, or None when no data folder is configured."""
    from fielddata.config import data_root
    from fielddata.registry import metadata
    try:
        return data_root() / metadata(package_id)["data_directory"]
    except ValueError:
        return None


def _absent(folder):
    return folder is not None and (not folder.is_dir() or not any(p.is_file() for p in folder.rglob("*")))


def _not_downloaded(package_id, err):
    """The NotDownloaded error to raise in place of ``err``, or None when the data folder does not explain it."""
    folder = _folder(package_id)
    if _absent(folder):
        return NotDownloaded(f"Release {package_id} is not downloaded yet. Run: python -m fielddata.fetch {package_id}")
    missing = Path(err.filename) if isinstance(err, FileNotFoundError) and err.filename else None
    if folder is not None and missing is not None and folder.resolve() in missing.resolve().parents:
        return NotDownloaded(f"Release {package_id} is missing {missing.name}. Run: python -m fielddata.fetch {package_id}, "
                             f"then python -m fielddata.doctor {package_id}")
    return None


def _call(package_id, name, **kwargs):
    """Call a loader function. If it fails, or finds nothing, because the release is not in the data folder,
    raise NotDownloaded with the fetch command instead of the loader's own error."""
    try:
        result = getattr(_loader(package_id), name)(**kwargs)
    except NotDownloaded:
        raise
    except Exception as err:
        replacement = _not_downloaded(package_id, err)
        if replacement is None:
            raise
        raise replacement from err
    if hasattr(result, "__len__") and len(result) == 0 and _absent(_folder(package_id)):
        raise NotDownloaded(f"Release {package_id} is not downloaded yet. Run: python -m fielddata.fetch {package_id}")
    return result


def load(package_id, **kwargs):
    """Load raw data from a registered package."""
    return _call(package_id, "load", **kwargs)


def systems(package_id):
    """Return the released monitored systems in a registered package."""
    return _call(package_id, "systems")
