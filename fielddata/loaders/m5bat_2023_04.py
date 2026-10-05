"""Loader for the M5BAT evaluation-operation month 04/2023 (RWTH Publications 985923).

Sources: the evaluation report ``Report_04-2023.pdf`` (doi:10.18154/RWTH-2024-04895), p. 3 (unit table), p. 5
(events), p. 6 (BESS columns) and p. 7 (battery-unit columns).
"""
from __future__ import annotations

import pandas as pd
from fielddata._deflate64 import zipfile  # members are deflate64-compressed

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "m5bat-2023-04"
_ARCHIVE = "M5BAT_04-2023_RAW.zip"

# Report p. 3, "Overview of technologies and parameters": number; abbreviation, technology, wiring and
# nominal power / energy. BattN is unit number N (confirmed by the string voltages, see the schema note).
_UNITS = {
    1: ("Pb1", "lead-acid (OCSM)", "300s1p", 630, 1066),
    2: ("Pb2", "lead-acid (OCSM)", "300s1p", 630, 1066),
    3: ("Pb3", "lead-acid gel (OPzV)", "308s2p", 630, 843),
    4: ("Pb4", "lead-acid gel (OPzV)", "306s1p", 522, 740),
    5: ("LMO1", "lithium manganese oxide (LMO)", "192s16p", 630, 774),
    6: ("LMO2", "lithium manganese oxide (LMO)", "192s16p", 630, 774),
    7: ("LMO3", "lithium manganese oxide (LMO)", "192s16p", 630, 774),
    8: ("LMO4", "lithium manganese oxide (LMO)", "192s16p", 630, 774),
    9: ("LFP", "lithium iron phosphate (LFP)", "240s10p", 630, 738),
    10: ("LTO", "lithium titanate oxide (LTO)", "312s32p", 630, 230),
}


def _members():
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        return {info.filename.removesuffix(".csv"): info for info in z.infolist() if info.filename.endswith(".csv")}


def systems():
    """One row per CSV: ten battery units Batt1 to Batt10 and BESS, the plant connection point.

    ``abbreviation``, ``technology``, ``wiring``, ``nominal_power_kw`` and ``nominal_energy_kwh`` are as stated
    in the report's p. 3 table (the LFP unit's 738 kWh is its usable energy; 923 kWh is installed).
    Batt1 is the Pb1 lead-acid string, which is also released on its own as m5bat-pbacid.
    """
    rows = []
    for name, info in sorted(_members().items(), key=lambda kv: (kv[0] == "BESS", int(kv[0][4:]) if kv[0] != "BESS" else 0)):
        number = int(name[4:]) if name.startswith("Batt") and name[4:].isdigit() else None
        abbreviation, technology, wiring, power, energy = _UNITS.get(number, (None, None, None, None, None))
        rows.append({"unit": name, "kind": "plant connection point" if name == "BESS" else "battery unit",
                     "abbreviation": abbreviation, "technology": technology, "wiring": wiring,
                     "nominal_power_kw": power, "nominal_energy_kwh": energy,
                     "file": info.filename, "bytes": info.file_size,
                     "note": "also released as m5bat-pbacid" if name == "Batt1" else ""})
    return pd.DataFrame(rows)


def load(unit=None, clean=False):
    """Load one or more unit CSVs, indexed by ``DateAndTime`` (1 s rows), localized to UTC.

    The report (pp. 6-7) gives DateAndTime as "UTC Timezone"; a lag test against m5bat-pbacid (UTC) peaks at
    lag 0. Values are the integers as released, not rescaled. Units per the report: P_AC, P_AC_Set kW and
    Q_AC, Q_AC_Set kVAr (power negative = charging, positive = discharging); SOC 0.1 % (BMS value);
    I_DC_Batt 0.1 A; U_DC_Batt 0.1 V. Plant (BESS): powers kW, M5BAT_Q kVAr, Grid_frequency mHz,
    Temperature 0.1 degC (site ambient), SOC % (calculated). ``interpolated`` is True where the publisher
    linearly interpolated a value (report pp. 6-7). ``clean`` has no effect.
    """
    members = _members()
    frames = []
    for item in as_list(unit, [m for m in members if m != "BESS"]):
        name = check_unit(item, list(members), _PACKAGE)
        with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z, z.open(members[name].filename) as f:
            frame = pd.read_csv(f, sep=";")
        frame["DateAndTime"] = pd.to_datetime(frame["DateAndTime"]).dt.tz_localize("UTC")
        frame["unit"] = name
        frames.append(finish(frame.set_index("DateAndTime").sort_index(kind="stable"), _PACKAGE, clean, 0, unit=name))
    return concat(frames, _PACKAGE, clean)
