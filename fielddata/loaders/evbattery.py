"""Loader for the evbattery charging-snippet release (tar.gz archives of torch pickles).

The publisher perturbed and interpolated average cell voltage, current and temperature, and randomly shifted
and scaled timestamps and mileage before release (paper arXiv:2201.12358v3, Sec. 3). Values are returned as
released: current is negative while charging, SOC is the BMS estimate, `capacity` is an engineers' label
(0 where unlabeled) and `label` is the metadata string "10" or "00". See evbattery_SCHEMA.md.
"""
from __future__ import annotations

from fielddata.loaders import _snippets

_PACKAGE = "evbattery"
COLUMNS = _snippets.COLUMNS


def systems():
    """One row per released vehicle: archive, car id, label and snippet count (from the committed index)."""
    return _snippets.systems(_PACKAGE)


def iter_snippets(archive):
    """Yield (member, array, metadata) for every snippet in one archive; the fast way to use the whole release."""
    return _snippets.iter_snippets(_PACKAGE, archive)


def load(unit, clean=False):
    """Load all snippets of one vehicle ("<archive stem>:<car>"); streams its archive. ``clean`` has no effect."""
    return _snippets.load(_PACKAGE, unit, clean=clean)
