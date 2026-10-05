"""Synthetic-data tests for the ppl loader changes from the 2026-10-04 source audit."""
import zipfile

import pandas as pd
import pytest

import fielddata
from fielddata.loaders import ppl


@pytest.fixture
def ppl_root(monkeypatch, tmp_path, package_directory):
    monkeypatch.setattr(ppl, "data_root", lambda: tmp_path)
    d = package_directory("ppl")
    (d / "BESS-Analysis").mkdir()
    return d


def test_clean_masks_outage_zeros_only(ppl_root):
    frame = pd.DataFrame({
        "Timestamp": ["2019-07-05 13:39:00", "2019-07-05 13:40:00", "2019-07-05 13:41:00"],
        "AvgSOC": [0.0, 0.0, 50.0], "SOH": [0.0, 90.0, 90.0], "PowerReal": [0.0, 0.0, 0.0], "Mode": ["Idle"] * 3,
        "Running": [0, 1, 1], "CellVoltAvg": [0.0, 3.7, 3.7], "CellVoltMax": [0.0, 3.71, 3.71], "CellVoltMin": [0.0, 3.69, 3.69],
        "ModuleTempMax": [0.0, 0.0, 20.0], "ModuleTempMin": [0.0, 0.0, 18.0], "Container1.Temp": [0.0, 15.0, 15.0]})
    frame.to_csv(ppl_root / "BESS-Analysis" / "ESS_2019.csv", index=False)
    raw = fielddata.load("ppl", years=[2019])
    clean = fielddata.load("ppl", years=[2019], clean=True)
    assert raw["SOH"].iloc[0] == 0 and raw.attrs["masked_value_count"] == 0
    # Row 0 is an outage placeholder: SOH, cell voltages, SOC and module temperatures are masked.
    assert clean.iloc[0][["AvgSOC", "SOH", "CellVoltAvg", "CellVoltMax", "CellVoltMin", "ModuleTempMax", "ModuleTempMin"]].isna().all()
    # Row 1 has real cell voltages, so its 0 SOC and 0 module temperatures are kept; power and container zeros are kept everywhere.
    assert clean["AvgSOC"].iloc[1] == 0 and clean["ModuleTempMax"].iloc[1] == 0
    assert (clean["PowerReal"] == 0).all() and clean["Container1.Temp"].iloc[0] == 0 and len(clean) == 3
    assert clean.attrs["masked_value_count"] == 7


def test_cell_level_listing_and_preview(ppl_root):
    (ppl_root / "cell_level").mkdir()
    body = "# JXB BSC - Bank Logging Data\n# Bank Id: 1\n\nCounter,Time,SOC[%]\n1,2018-07-15 0:00:00,6.5\n2,2018-07-15 0:00:01,6.5\n"
    with zipfile.ZipFile(ppl_root / "cell_level" / "20180701-0731.zip", "w") as z:
        z.writestr("20180715/JXB_BSC_Bank1_20180715.csv", body)
    assert ppl.cell_level_files()["file"].tolist() == ["20180701-0731.zip"]
    assert ppl.cell_level_members("20180701-0731.zip")["member"].tolist() == ["20180715/JXB_BSC_Bank1_20180715.csv"]
    frame = ppl.cell_level_preview("20180701-0731.zip", "20180715/JXB_BSC_Bank1_20180715.csv")
    assert list(frame.columns) == ["Counter", "Time", "SOC[%]"] and len(frame) == 2
    assert frame.attrs["comments"] == ["# JXB BSC - Bank Logging Data", "# Bank Id: 1"]
