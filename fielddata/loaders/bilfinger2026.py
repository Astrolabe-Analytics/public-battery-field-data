"""Loader for the bilfinger2026 mediaTUM release (vehicle-level charging, discharging and rest recordings plus laboratory reference cells).

Raw by default. `clean=True` masks two out-of-range values found only in `VW_ID3_FTM_8A_CEE7_Balancing`:
pack voltage `U` == 1023.5 V (157 rows; the 108s pack tops out near 454 V) and current `I` == 166272.14 A
(65 rows). Both come in runs of one to four rows between normal readings and cannot be measurements. Other
single-row spikes in that file (a cell voltage of 5.094 V, `SOC` 101.6 %, `pack_temp_0` 87.0 or 87.5 C)
are left as released and are described in bilfinger2026_SCHEMA.md.
"""
from __future__ import annotations

from fielddata.loaders import _bilfinger

_PACKAGE = "bilfinger2026"

_CLEAN_RULES = {
    "U": lambda s: s == 1023.5,
    "I": lambda s: s == 166272.14,
}


def systems():
    """One row per released recording file, with its kind (vehicle, laboratory cell or half-cell) and vehicle."""
    return _bilfinger.systems(_PACKAGE)


def load(unit, clean=False):
    """Load one recording by file stem, as released; clean=True masks U == 1023.5 V and I == 166272.14 A (see module docstring)."""
    return _bilfinger.load(_PACKAGE, unit, clean=clean, rules=_CLEAN_RULES)
