"""Loader for the bilfinger2024 mediaTUM release (vehicle-level charging recordings, three VW logs and laboratory reference cells).

Raw by default. `clean` has no effect: no out-of-range or code values were found in this release
(audit 2026-10-04, see bilfinger2024_SCHEMA.md).
"""
from __future__ import annotations

from fielddata.loaders import _bilfinger

_PACKAGE = "bilfinger2024"


def systems():
    """One row per released recording file, with its kind (vehicle, vehicle raw log, laboratory cell or half-cell) and vehicle."""
    return _bilfinger.systems(_PACKAGE)


def load(unit, clean=False):
    """Load one recording by file stem, as released. clean has no effect."""
    return _bilfinger.load(_PACKAGE, unit, clean=clean)
