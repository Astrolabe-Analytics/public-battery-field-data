"""Load public battery-field data packages."""
from importlib import import_module


def _loader(package_id):
    return import_module(f"fielddata.loaders.{package_id.replace('-', '_')}")


def load(package_id, **kwargs):
    """Load raw data from a registered package."""
    return _loader(package_id).load(**kwargs)


def systems(package_id):
    """Return the released monitored systems in a registered package."""
    return _loader(package_id).systems()