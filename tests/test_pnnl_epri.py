"""pnnl_epri candidate loader on synthetic data: one long .feather per system, read unchanged."""
import pandas as pd

from fielddata.registry import CANDIDATES, PACKAGES


def _release(rows):
    from fielddata.loaders import pnnl_epri

    frame = pd.DataFrame(rows)
    for column in pnnl_epri.COLUMNS:
        if column not in frame:
            frame[column] = pd.NA if column in ("CycleIndex", "Use") else float("nan")
    frame["QualityFlag"] = frame["QualityFlag"].astype("boolean").fillna(False).astype(bool)
    frame["CycleIndex"] = frame["CycleIndex"].astype("string")
    frame["Use"] = frame["Use"].astype("boolean")
    return frame[pnnl_epri.COLUMNS]


def test_pnnl_epri_reads_feather_unchanged(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import pnnl_epri

    directory = package_directory("pnnl_epri")
    for unit in pnnl_epri.SYSTEMS:
        _release([{"HoursElapsed": 0.0, "DayNumber": 0, "Meter": "PGCP", "Power": 0.0}]).to_feather(directory / f"{unit}.feather")
    rows = [
        {"HoursElapsed": 0.0, "DayNumber": 0, "Meter": "PDC1", "Power": 0.25, "Current": 0.24, "Voltage": 3.31, "SOC": 0.5},
        {"HoursElapsed": 0.0, "DayNumber": 0, "Meter": "PGCP", "Power": 0.26, "SOC": 0.5, "QualityFlag": True},
        {"HoursElapsed": 1 / 360, "DayNumber": 0, "Meter": "PDC1", "Power": -0.5, "Current": -0.49, "Voltage": 3.40, "SOC": 0.51},
        {"HoursElapsed": 1 / 360, "DayNumber": 0, "Meter": "PGCP", "Power": -0.52, "SOC": 0.51},
    ]
    _release(rows).to_feather(directory / "ENW.feather")
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    units = pnnl_epri.systems()
    assert len(units) == 12 and units["unit"].is_unique
    assert units.set_index("unit").loc["EPRI_VRF1", "chemistry"] == "vanadium flow"
    assert units.set_index("unit").loc["EPRI_VRF1", "cell_count"] == "not applicable"
    assert pnnl_epri.meters("ENW") == ["PDC1", "PGCP"]

    frame = pnnl_epri.load(unit="ENW")
    assert list(frame.columns) == pnnl_epri.COLUMNS and len(frame) == 4
    assert frame["Power"].tolist() == [0.25, 0.26, -0.5, -0.52]  # positive = discharge, C-rate, as released
    assert frame["QualityFlag"].tolist() == [False, True, False, False]
    dc = pnnl_epri.load(unit="ENW", meter="PDC1", columns=["Current"])
    assert list(dc.columns) == ["HoursElapsed", "Meter", "Current"] and dc["Current"].tolist() == [0.24, -0.49]
    assert pnnl_epri.load(unit="ENW", clean=True).attrs["masked_value_count"] == 0
    both = pnnl_epri.load(unit=["ENW", "PSE"], meter="PGCP")
    assert both["unit"].tolist() == ["ENW", "ENW", "PSE"]


def test_pnnl_epri_is_a_package():
    assert "pnnl_epri" in PACKAGES and "pnnl_epri" not in CANDIDATES  # admitted in v1.2
    files = PACKAGES["pnnl_epri"]["data_files"]
    assert len(files) == 26 and sum(f.endswith(".feather") for f in files) == 12
    assert "EPRI_VRF1.feather" in files
