import pickle
import shutil
import zipfile

import numpy as np
import pytest
import pandas as pd
import pandas.testing as pdt


def assert_one_value_masked(raw, clean, column, row=1):
    assert raw.shape == clean.shape
    assert pd.isna(clean.iloc[row][column])
    unchanged = raw.copy()
    unchanged.iloc[row, unchanged.columns.get_loc(column)] = np.nan
    pdt.assert_frame_equal(clean, unchanged, check_dtype=False, check_freq=False)


def test_cao_raw_and_clean(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import cao

    directory = package_directory("cao")
    values = np.array([
        [1, 2, 3.5, 3.6, 0.0, 0.1, 25, 0.5, 10],
        [65535, 2, 3.5, 3.6, 0.0, 0.1, 25, 0.5, 10],
    ], dtype=float)
    with zipfile.ZipFile(directory / "DTI.zip", "w") as archive:
        archive.writestr("DTI/0/vin_2.pkl", pickle.dumps(values))
    monkeypatch.setattr(cao, "data_root", lambda: tmp_path)

    raw = cao.load("DTI", "0", names="inferred")
    clean = cao.load("DTI", "0", names="inferred", clean=True)

    assert raw.iloc[1, 0] == 65535
    assert not clean.pop("current_invalid").any()  # clean=True adds the flag column
    assert_one_value_masked(raw, clean, "pack_state_a")
    assert list(raw.columns[[2, 4, 6, 7, 8]]) == ["cell_v_001", "cell_dU_001", "temperature_degC", "soc_pct", "current_A"]
    assert raw.iloc[0]["soc_pct"] == 0.5  # DTI state of charge is released in percent and kept as released


def test_cao_qas_soc_in_percent(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import cao

    directory = package_directory("cao")
    for name in ["DTI", "GIS", "QAS_2", "QAS_3", "QAS_4", "QAS_5"]:
        zipfile.ZipFile(directory / f"{name}.zip", "w").close()
    values = np.array([[1, 2, 3.3, 3.4, 0.0, 0.1, 25, 0.42, 10],
                       [1, 2, 3.3, 3.4, 0.0, 0.1, 25, -1000.0, 10]], dtype=float)
    with zipfile.ZipFile(directory / "QAS_1.zip", "w") as archive:
        archive.writestr("QAS_1/7/vin_2.pkl", pickle.dumps(values))
    monkeypatch.setattr(cao, "data_root", lambda: tmp_path)

    inferred = cao.load("QAS", "7", names="inferred")
    generic = cao.load("QAS", "7")
    assert inferred["soc_pct"].tolist() == pytest.approx([42.0, -1000.0])  # fraction to percent, placeholder code untouched
    assert generic["col_07"].tolist() == [0.42, -1000.0]  # generic names return the released values


def test_cao_qas_bad_current_masked_and_flagged(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import cao

    directory = package_directory("cao")
    for name in ["DTI", "GIS", "QAS_2", "QAS_3", "QAS_4", "QAS_5"]:
        zipfile.ZipFile(directory / f"{name}.zip", "w").close()
    values = np.array([[1, 2, 3.3, 3.4, 0.0, 0.1, 25, 0.42, 10.0],
                       [1, 2, 3.3, 3.4, 0.0, 0.1, 25, 0.42, -995.0],
                       [1, 2, 3.3, 3.4, 0.0, 0.1, 25, 0.42, -86.7]], dtype=float)
    with zipfile.ZipFile(directory / "QAS_1.zip", "w") as archive:
        archive.writestr("QAS_1/7/vin_2.pkl", pickle.dumps(values))
    monkeypatch.setattr(cao, "data_root", lambda: tmp_path)

    raw = cao.load("QAS", "7", names="inferred")
    clean = cao.load("QAS", "7", names="inferred", clean=True)
    assert "current_invalid" not in raw.columns
    assert raw["current_A"].tolist() == [10.0, -995.0, -86.7]
    assert clean["current_A"].isna().tolist() == [False, True, False]  # -995 A is the placeholder stretch, -86.7 A is charging
    assert clean["current_invalid"].tolist() == [False, True, False]
    assert clean.attrs["masked_value_count"] == 1


def test_cao_vin3_inferred_names():
    from fielddata.loaders import cao

    names = cao._inferred_columns(2 + 2 + 2 + 4, "vin_3")
    assert names == ["pack_state_a", "pack_state_b", "cell_soc_001", "cell_soc_002", "cell_dsoc_001", "cell_dsoc_002",
                     "temperature_degC", "soc_pct", "extra", "current_A"]


def test_cao_labels_apply_across_a_brands_archives(monkeypatch, tmp_path, package_directory):
    # The QAS label sheet is only in QAS_5.zip but covers vehicles in every QAS archive.
    from fielddata.loaders import cao

    directory = package_directory("cao")
    for name in ["DTI", "QAS_2", "QAS_3", "QAS_4"]:  # every registered archive must exist
        zipfile.ZipFile(directory / f"{name}.zip", "w").close()
    with zipfile.ZipFile(directory / "QAS_1.zip", "w") as archive:
        archive.writestr("QAS_1/0/vin_2.pkl", b"x")
    with zipfile.ZipFile(directory / "QAS_5.zip", "w") as archive:
        archive.writestr("QAS_5/1/vin_2.pkl", b"x")
        archive.writestr("QAS_5/Labels.xls", b"sheet")
    with zipfile.ZipFile(directory / "GIS.zip", "w") as archive:
        archive.writestr("GIS/0/vin_2.pkl", b"x")
    monkeypatch.setattr(cao, "data_root", lambda: tmp_path)
    monkeypatch.setattr(cao, "_labels", lambda archive: {"0": 1, "1": 0} if any(m.endswith("Labels.xls") for m in archive.namelist()) else {})

    units = cao.systems().set_index(["brand", "vehicle"])["label"]

    assert units[("QAS", "0")] == 1  # labelled from the sheet in another archive
    assert units[("QAS", "1")] == 0
    assert pd.isna(units[("GIS", "0")])  # no sheet for GIS, and QAS labels do not leak across brands


def test_deng_raw_and_clean(monkeypatch, tmp_path, package_directory, fixture_dir):
    from fielddata.loaders import deng

    directory = package_directory("deng")
    (directory / "#1.rar").write_bytes(b"synthetic-rar-placeholder")
    monkeypatch.setattr(deng, "data_root", lambda: tmp_path)
    monkeypatch.setattr(deng, "_unrar", lambda: "synthetic-unrar")

    def extract(_command, check):
        assert check is True
        target = pd.io.common.stringify_path(_command[-1]).rstrip("\\/")
        shutil.copyfile(fixture_dir / "deng_pack.csv", f"{target}/pack.csv")

    monkeypatch.setattr(deng.subprocess, "run", extract)
    raw = deng.load("#1")
    clean = deng.load("#1", clean=True)

    assert raw.iloc[1]["available_energy"] == 1_000_001
    assert_one_value_masked(raw, clean, "available_energy")


def test_m5bat_raw_and_clean(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import m5bat_pbacid

    directory = package_directory("m5bat-pbacid")
    frame = pd.DataFrame(
        {"power_dc_W_bms": [1.0, 2345.0], "current_A_bms": [2.0, 3.0]},
        index=pd.DatetimeIndex(["2020-01-01T00:00:00Z", "2020-01-01T00:00:01Z"], name="timestamp_utc"),
    )
    parquet = tmp_path / "Exide1_BMS_2020.parquet"
    frame.to_parquet(parquet)
    with zipfile.ZipFile(directory / "Full_Dataset_M5BAT_Battery_Unit_Pb1.zip", "w") as archive:
        archive.write(parquet, parquet.name)
    monkeypatch.setattr(m5bat_pbacid, "data_root", lambda: tmp_path)

    raw = m5bat_pbacid.load("bms", years=[2020])
    clean = m5bat_pbacid.load("bms", years=[2020], clean=True)

    assert raw.iloc[1]["power_dc_W_bms"] == 2345
    assert_one_value_masked(raw, clean, "power_dc_W_bms")


def test_ppl_raw_and_clean(monkeypatch, tmp_path, package_directory, fixture_dir):
    from fielddata.loaders import ppl

    directory = package_directory("ppl") / "BESS-Analysis"
    directory.mkdir()
    shutil.copyfile(fixture_dir / "ppl_ess.csv", directory / "ESS_2020.csv")
    monkeypatch.setattr(ppl, "data_root", lambda: tmp_path)

    raw = ppl.load(years=[2020])
    clean = ppl.load(years=[2020], clean=True)

    assert raw.iloc[1]["PowerReal"] == 1_000_001
    assert_one_value_masked(raw, clean, "PowerReal")


def test_schaeffer_raw_and_clean(monkeypatch, tmp_path, package_directory, fixture_dir):
    from fielddata.loaders import schaeffer

    directory = package_directory("schaeffer")
    with zipfile.ZipFile(directory / "field_data.zip", "w") as archive:
        archive.write(fixture_dir / "schaeffer_system.csv", "field_data/data_sys_1.csv")
    monkeypatch.setattr(schaeffer, "data_root", lambda: tmp_path)

    raw = schaeffer.load(1)
    clean = schaeffer.load(1, clean=True)

    assert raw.iloc[1]["U_Cell_1"] == 0
    assert_one_value_masked(raw, clean, "U_Cell_1")
