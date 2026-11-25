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


def _folders(package_id):
    """The release's data folder under each data root its loader may read (its own and the shared one in _base);
    empty when no data folder is configured."""
    from fielddata.loaders import _base
    from fielddata.registry import metadata
    folders = []
    for data_root in {getattr(_loader(package_id), "data_root", _base.data_root), _base.data_root}:
        try:
            folders.append(data_root() / metadata(package_id)["data_directory"])
        except ValueError:
            pass
    return folders


def _absent(folders):
    return bool(folders) and all(not f.is_dir() or not any(p.is_file() for p in f.rglob("*")) for f in folders)


def _not_downloaded(package_id, err):
    """The NotDownloaded error to raise in place of ``err``, or None when the data folder does not explain it."""
    folders = _folders(package_id)
    if _absent(folders):
        return NotDownloaded(f"Release {package_id} is not downloaded yet. Run: python -m fielddata.fetch {package_id}")
    missing = Path(err.filename) if isinstance(err, FileNotFoundError) and err.filename else None
    if missing is not None and any(f.resolve() in missing.resolve().parents for f in folders):
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
    if hasattr(result, "__len__") and len(result) == 0 and _absent(_folders(package_id)):
        raise NotDownloaded(f"Release {package_id} is not downloaded yet. Run: python -m fielddata.fetch {package_id}")
    return result


def load(package_id, **kwargs):
    """Load raw data from a registered package."""
    return _call(package_id, "load", **kwargs)


def systems(package_id):
    """Return the released monitored systems in a registered package."""
    return _call(package_id, "systems")


def standard(package_id, unit=None, **kwargs):
    """Load standard values, or stream where the standard interface supports it."""
    loader = _loader(package_id)
    if hasattr(loader, "standard"):
        return _call(package_id, "standard", unit=unit, **kwargs)
    from fielddata._standard import standard as view
    return view(package_id, unit=unit, **kwargs)


def standard_systems(package_id):
    """List units with their standard-view tier and any explicit conversion block."""
    from fielddata._standard import standard_systems as tagged_systems
    return tagged_systems(package_id)


def standardize(package_id, unit, raw):
    """Convert an existing single-unit loader frame without rereading released files."""
    from fielddata._standard import standardize as convert
    return convert(package_id, unit, raw)


def iter_standard(package_id, unit=None, *, archive=None, chunksize=250_000, clean=False,
                  signal="V_pack_bms"):
    """Stream Schaeffer chunks, complete snippets or Stanford sessions."""
    from fielddata._standard import iter_standard as stream
    return stream(package_id, unit, archive=archive, chunksize=chunksize, clean=clean, signal=signal)
