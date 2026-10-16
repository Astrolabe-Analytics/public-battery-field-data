"""Loader for the bilfinger2025 mediaTUM release (low-power AC charges of 12 vehicles for a standard state-of-health
measurement procedure, plus four C/50 laboratory reference curves of the VW cell).

Raw by default. `clean=True` changes nothing: no placeholder or out-of-range codes have been documented for this
release (see bilfinger2025_SCHEMA.md). Feather files only, read straight from the unextracted data.zip.
"""
from __future__ import annotations

from fielddata.loaders import _bilfinger

_PACKAGE = "bilfinger2025"


def systems():
    """One row per released recording file, with its kind (vehicle or laboratory cell) and vehicle."""
    return _bilfinger.systems(_PACKAGE)


def load(unit, clean=False):
    """Load one recording by file stem, as released."""
    return _bilfinger.load(_PACKAGE, unit, clean=clean)
