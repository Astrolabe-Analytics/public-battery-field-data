"""Synthetic-data tests for the loaders added in v1.0: each builds a tiny release in the real layout."""
import io
import pickle
import tarfile
import zipfile

import numpy as np
import pandas as pd
import pytest

import fielddata
from fielddata.loaders import _base


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    return tmp_path


def test_fei_bus(root, package_directory):
    d = package_directory("fei_bus")
    pd.DataFrame({"SOH": [0.9, 0.8], "SOH(OCV)": [0.95, 0.85], "mileage": [10.0, 20.0]}).to_csv(d / "vin1.csv", index=False)
    assert fielddata.systems("fei_bus")["unit"].tolist() == ["vin1"]
    frame = fielddata.load("fei_bus", unit="vin1")
    assert frame["SOH"].tolist() == [0.9, 0.8] and frame.attrs["package"] == "fei_bus"
    with pytest.raises(ValueError):
        fielddata.load("fei_bus", unit="vin2")


def test_flashbattery(root, package_directory):
    d = package_directory("flashbattery-agv")
    pd.DataFrame({"counter": [1, 2, 3], "date": ["2020-01-02", "2020-01-01", "2020-01-01"], "cycletime": [10, 20, 30],
                  "totaldischarge": [1, 2, 3], "mintemperature": [20, 21, 22], "maxtemperature": [25, 26, 27],
                  "battery": ["FB-1", "FB-1", "FB-2"]}).to_csv(d / "dataset.csv", index=False)
    frame = fielddata.load("flashbattery-agv", unit="FB-1")
    assert frame.index.is_monotonic_increasing and frame["counter"].tolist() == [2, 1]
    assert fielddata.systems("flashbattery-agv")["cycles"].tolist() == [2, 1]


def test_li2026(root, package_directory):
    d = package_directory("li2026")
    part = pd.DataFrame({**{f"vol_{i}": [3.2, 3.3] for i in range(1, 9)}, **{f"temp_{i}": [30.0, 31.0] for i in range(1, 9)}, "cur": [1.0, -1.0]})
    with zipfile.ZipFile(d / "BatteryData.zip", "w") as z:
        z.writestr("BatteryData/p1/battery_02_cells_009-016_t_00002-00003.csv", part.to_csv(index=False))
        z.writestr("BatteryData/p1/battery_02_cells_009-016_t_00000-00001.csv", part.to_csv(index=False))
    frame = fielddata.load("li2026", unit="p1/battery_02")
    assert frame.index.tolist() == [0, 1, 2, 3] and "cell_009_V" in frame and "cell_016_T" in frame


def test_m5bat_2023_04(root, package_directory):
    d = package_directory("m5bat-2023-04")
    text = "DateAndTime;SOC;interpolated\n2023-04-01 00:00:01;431;0\n2023-04-01 00:00:00;430;0\n"
    with zipfile.ZipFile(d / "M5BAT_04-2023_RAW.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Batt2.csv", text)
        z.writestr("BESS.csv", text)
    assert fielddata.systems("m5bat-2023-04")["unit"].tolist() == ["Batt2", "BESS"]
    frame = fielddata.load("m5bat-2023-04")
    assert frame["unit"].unique().tolist() == ["Batt2"] and frame["SOC"].tolist() == [430, 431]


def test_tumftm_clean_masks_sentinel_time(root, package_directory):
    import pyarrow as pa
    import pyarrow.parquet as pq
    d = package_directory("tumftm") / "electric-vehicle-uds-dataset" / "data"
    (d / "uds_data").mkdir(parents=True)
    pd.DataFrame({"value_id": [1200], "name_de": ["x"], "name_en": ["pack voltage"], "variable_name": ["hv_battery_voltage"],
                  "unit": ["V"], "min_val": [0], "max_val": [1000], "sampling_interval_ms": [200]}).to_csv(d / "value_overview.csv", index=False)
    table = pd.DataFrame({"vehicle_id": ["CUP1", "CUP1"], "time": pd.to_datetime(["2087-03-07", "2022-01-01"]),
                          "value_id": [1200, 1200], "value": [400.0, 401.0]})
    pq.write_table(pa.Table.from_pandas(table), d / "uds_data" / "CUP1.parquet")
    raw = fielddata.load("tumftm", unit="CUP1")
    clean = fielddata.load("tumftm", unit="CUP1", clean=True)
    assert raw["time"].dt.year.max() == 2087 and clean["time"].isna().sum() == 1 and len(clean) == 2
    assert clean.attrs["masked_value_count"] == 1 and clean["variable_name"].iloc[0] == "hv_battery_voltage"


def test_rwth_home(root, package_directory):
    d = package_directory("rwth-home")
    body = "Time,P_in_W,V_in_V,I_in_A,T_Bat_in_C,T_Room_in_C,Interpolated\n17-Jul-2015 10:54:36,0.0,163.8,0.0,27.5,23.9,0\n"
    with zipfile.ZipFile(d / "Data_ID_01.zip", "w") as z:
        z.writestr("01/2015_07_System_ID_01.csv", body)
        z.writestr("01/2015_08_System_ID_01.csv", body.replace("Jul", "Aug"))
    assert fielddata.systems("rwth-home")["months"].tolist() == [2]
    frame = fielddata.load("rwth-home", unit=1, month="2015-08")
    assert frame.index[0] == pd.Timestamp("2015-08-17 10:54:36")


def test_ku_leuven_bev(root, package_directory):
    d = package_directory("ku_leuven_bev")
    session = "Timestamp,SOCave292\n2024-05-16 13:46:22+00:00,78.2\n"
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("BEV energy dynamic data_V2/driving sessions/BEV1_2024-05-16_drive.csv", session)
        z.writestr("BEV energy dynamic data_V2/parking sessions/BEV1_2024-12_12_park.csv", session)
    with zipfile.ZipFile(d / "doi-10.48804-8kpdtw.zip", "w") as z:
        z.writestr("BEV energy dynamic data_V2.zip", inner.getvalue())
    systems = fielddata.systems("ku_leuven_bev")
    assert systems.loc[0, "last_session"] == pd.Timestamp("2024-12-12")
    frame = fielddata.load("ku_leuven_bev", unit="BEV1", session_type="driving")
    assert len(frame) == 1 and frame["session_type"].iloc[0] == "driving"


def test_bilfinger_feather(root, package_directory):
    d = package_directory("bilfinger2026")
    buf = io.BytesIO()
    pd.DataFrame({"U": [400.0], "cell_voltage_0": [3.7]}).to_feather(buf)
    with zipfile.ZipFile(d / "data.zip", "w") as z:
        z.writestr("DVA_robustness/data/Cupra/Cupra_204_JB_8A_CEE7_C45.feather", buf.getvalue())
        z.writestr("DVA_robustness/data/VW/cell/VW_LG_78Ah_NMC_20deg_CC_C50.feather", buf.getvalue())
    systems = fielddata.systems("bilfinger2026").set_index("unit")
    assert systems.loc["Cupra_204_JB_8A_CEE7_C45", "vehicle"] == "Cupra 204"
    assert pd.isna(systems.loc["VW_LG_78Ah_NMC_20deg_CC_C50", "vehicle"])
    assert fielddata.load("bilfinger2026", unit="Cupra_204_JB_8A_CEE7_C45")["U"].iloc[0] == 400.0


def test_tsukuba_header_and_range(root, package_directory):
    from fielddata.loaders import tsukuba
    d = package_directory("tsukuba")
    header = "#,蓄電池　ＳＯＣ値\n#,12152\n#,%\n".encode("cp932")
    rows = b"'2016/03/01 23:59:59,95\n'2016/03/02 00:00:00,94\n"
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("20160301-20160312SecCsv.csv", header + rows)
    with zipfile.ZipFile(d / tsukuba.PACKAGES["tsukuba"]["data_files"][0], "w") as z:
        z.writestr("1 Raw_data_per_second.zip", inner.getvalue())
        z.writestr("2 Cleaned_data_per_second.zip", inner.getvalue())
    frame = fielddata.load("tsukuba", start="2016-03-01", end="2016-03-01")
    assert frame["battery_soc"].tolist() == [95] and frame.attrs["signals"]["battery_soc"]["unit"] == "%"


def test_snippets(root, package_directory, monkeypatch):
    from fielddata.loaders import _snippets
    d = package_directory("zhang2023")
    monkeypatch.setattr(_snippets, "index_path", lambda package: root / f"{package}_index.csv")
    with tarfile.open(d / "battery_brand3.tar.gz", "w:gz") as tar:
        for name, data in [("battery_brand3/label/all_label.csv", b"car,label\n401,0\n402,1\n"),
                           ("battery_brand3/data/1.pkl", pickle.dumps((np.ones((128, 8)), {"car": 401, "label": "00", "charge_segment": "1", "mileage": 5.0})))]:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    index = _snippets.build_index("zhang2023", "battery_brand3.tar.gz")
    assert index.set_index("car")["snippets"].to_dict() == {401: 1, 402: 0}
    frame = fielddata.load("zhang2023", unit="battery_brand3:401")
    assert frame.shape[0] == 128 and frame["charge_segment"].iloc[0] == "1"


def test_changan_expand_and_zhou_expand():
    from fielddata.loaders import changan, zhou2026
    assert changan.expand(pd.DataFrame({"batteryvoltage": ["3.1~3.2"]})).iloc[0].tolist() == [3.1, 3.2]
    assert zhou2026.expand_cells(pd.DataFrame({"CellVoltages": ["1:3378_3375"]})).iloc[0].tolist() == [3378, 3375]
