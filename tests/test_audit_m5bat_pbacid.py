"""Source-audit follow-up tests for m5bat-pbacid (synthetic data, no data folder needed).

clean=True masks only what the codebook (Description_File.pdf) defines: the BMS communication-error codes
2345/2356 in three BMS columns and 2345 in the SoC, plus the uninitialised BSC AC energy counters (high
register word 0xFFFF, 2017-2021). Counter values that happen to equal 2345 or 2356 are kept.
"""
import zipfile

import pandas as pd
import pytest

from fielddata.loaders import m5bat_pbacid

INDEX = pd.DatetimeIndex(["2020-01-01T00:00:00Z", "2020-01-01T00:00:01Z", "2020-01-01T00:00:02Z"], name="timestamp_utc")


@pytest.fixture
def release(monkeypatch, tmp_path, package_directory):
    directory = package_directory("m5bat-pbacid")
    bms = pd.DataFrame({
        "power_dc_W_bms": [1.0, 2356.0, 3.0],
        "current_A_bms": [2345.0, 3.0, 4.0],
        "voltage_bat_V_bms": [620.0, 621.0, 2345.0],
        "soc_pct_bms": [50.0, 2356.0, 2345.0],
        "energy_charge_Wh_bms": [2344, 2345, 2356],
    }, index=INDEX)
    bsc = pd.DataFrame({
        "power_ac_kW_bsc": [2345.0, 1.0, 2.0],
        "energy_charge_kWh_bsc": [4294967295.0, 0.0, 4294967295.0],
        "energy_discharge_kWh_bsc": [4294902760.0, 2356.0, 7000.0],
    }, index=INDEX)
    with zipfile.ZipFile(directory / "Full_Dataset_M5BAT_Battery_Unit_Pb1.zip", "w") as archive:
        for name, frame in (("Exide1_BMS_2020.parquet", bms), ("Exide1_BSC_2020.parquet", bsc)):
            path = tmp_path / name
            frame.to_parquet(path)
            archive.write(path, name)
    monkeypatch.setattr(m5bat_pbacid, "data_root", lambda: tmp_path)
    return tmp_path


def test_clean_masks_only_codebook_sentinels_in_bms(release):
    raw = m5bat_pbacid.load("bms", years=[2020])
    clean = m5bat_pbacid.load("bms", years=[2020], clean=True)
    assert len(clean) == len(raw) == 3
    assert clean["power_dc_W_bms"].isna().tolist() == [False, True, False]
    assert clean["current_A_bms"].isna().tolist() == [True, False, False]
    assert clean["voltage_bat_V_bms"].isna().tolist() == [False, False, True]
    # SoC: only 2345 is a sentinel per the codebook
    assert clean["soc_pct_bms"].isna().tolist() == [False, False, True]
    # cumulative counter passes through 2345 and 2356 as real values
    assert clean["energy_charge_Wh_bms"].tolist() == [2344, 2345, 2356]
    assert clean.attrs["masked_value_count"] == 4
    assert raw.attrs["masked_value_count"] == 0 and raw["soc_pct_bms"].iloc[2] == 2345


def test_clean_masks_uninitialised_bsc_counters_only(release):
    clean = m5bat_pbacid.load("bsc", years=[2020], clean=True)
    assert clean["power_ac_kW_bsc"].iloc[0] == 2345  # no sentinel defined for BSC columns
    assert clean["energy_charge_kWh_bsc"].isna().tolist() == [True, False, True]
    assert clean["energy_discharge_kWh_bsc"].isna().tolist() == [True, False, False]
    assert clean["energy_discharge_kWh_bsc"].iloc[1] == 2356
    assert clean.attrs["masked_value_count"] == 3


def test_columns_selection_keeps_utc_index(release):
    frame = m5bat_pbacid.load("bsc", years=[2020], columns=["energy_charge_kWh_bsc"])
    assert frame.columns.tolist() == ["energy_charge_kWh_bsc"]
    assert frame.index.name == "timestamp_utc" and str(frame.index.tz) == "UTC"
    assert frame.attrs["columns"] == ["energy_charge_kWh_bsc"]
