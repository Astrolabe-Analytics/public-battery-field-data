"""Loader for the zhang2023 charging-snippet release (tar.gz archives of torch pickles).

Processed release: the authors removed abnormal data at or near battery failures (paper p. 3), scaled and
shifted the total voltage by a random float, and masked or encoded the metadata (SI Note 2). Values are
returned as released: `volt` is not a physical voltage, current is negative while charging, SOC is the BMS
value and `label` is the metadata string "10" or "00". See zhang2023_SCHEMA.md.
"""
from __future__ import annotations

from fielddata.loaders import _snippets

_PACKAGE = "zhang2023"
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
