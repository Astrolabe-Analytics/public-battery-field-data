"""bilfinger2025 loader on a synthetic data.zip with the release's file names: kinds, vehicles and the unit rule."""
import io
import zipfile

import pandas as pd
import pytest

import fielddata
from fielddata import counting
from fielddata.loaders import _base

NAMES = [
    "Cupra/Cupra_Born_204_JB_8A_CEE7_CS_2024", "Cupra/Cupra_Born_213_JB_8A_CEE7_CS_2024", "Cupra/Cupra_Born_288_JB_8A_CEE7_CS_2024",
    "Cupra/Cupra_Born_349_JB_8A_CEE7_CS_2024", "Cupra/Cupra_Born_397_JB_8A_CEE7_CS_2024",
    "Taycan/Porsche_Taycan_JB_10A_CEE7_AMS_2024", "Taycan/Porsche_Taycan_JB_10A_CEE7_FTM_2023",
    "Tesla/Tesla_Model_3_JB_6A_CEE7_FTM_2021", "Tesla/Tesla_Model_3_JB_6A_CEE7_FTM_2025",
    "Tesla/Tesla_Model_Y_JB_8A_CEE7_MI_2025", "Tesla/Tesla_Model_Y_JB_8A_CEE7_TW_2024",
    "VW/VW_ID3_FTM_JB_8A_CEE7_FTM_2024_balanced", "VW/VW_ID3_FTM_JB_8A_CEE7_FTM_2024_imbalanced",
    "VW/VW_ID3_JB_8A_CEE7_FTM_2021", "VW/VW_ID3_JB_8A_CEE7_FTM_2023", "VW/VW_ID3_JB_8A_CEE7_FTM_2024",
    "VW/VW_ID3_JB_8A_CEE7_GB_2024_cell_defect", "VW/cell/VW_LG_78Ah_NMC_20deg_CC_C50",
]


@pytest.fixture
def held(monkeypatch, tmp_path, package_directory):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    buf = io.BytesIO()
    pd.DataFrame({"U": [400.0, 401.0], "I": [10.0, 10.0], "cell_voltage_1": [3.7, 3.71]}).to_feather(buf)
    with zipfile.ZipFile(package_directory("bilfinger2025") / "data.zip", "w") as z:
        for name in NAMES:
            z.writestr(f"m1765567/data/{name}.feather", buf.getvalue())
        z.writestr("m1765567/data/font/Arial.ttf", b"font")
        z.writestr("m1765567/checksums.sha512", b"")
    return tmp_path


def test_systems_kinds_and_vehicles(held):
    s = fielddata.systems("bilfinger2025").set_index("unit")
    assert len(s) == len(NAMES)  # fonts and the checksum list are not recordings
    assert s.loc["VW_LG_78Ah_NMC_20deg_CC_C50", "kind"] == "laboratory cell" and pd.isna(s.loc["VW_LG_78Ah_NMC_20deg_CC_C50", "vehicle"])
    assert s.loc["Cupra_Born_204_JB_8A_CEE7_CS_2024", "vehicle"] == "Cupra 204"  # the same name as in bilfinger2026
    assert s.loc["VW_ID3_JB_8A_CEE7_FTM_2021", "vehicle"] == "VW ID.3" and s.loc["Tesla_Model_3_JB_6A_CEE7_FTM_2025", "vehicle"] == "Tesla Model 3 SR+"
    assert s.loc["VW_ID3_JB_8A_CEE7_GB_2024_cell_defect", "vehicle"] == "VW ID.3 (GB, defective cell)"
    assert {s.loc["Porsche_Taycan_JB_10A_CEE7_AMS_2024", "vehicle"], s.loc["Porsche_Taycan_JB_10A_CEE7_FTM_2023", "vehicle"]} == {"Porsche Taycan (AMS)", "Porsche Taycan (FTM)"}
    assert s["vehicle"].dropna().nunique() == 12


def test_units_count_only_vehicles_not_already_held(held):
    rule, _ = counting.RULES["bilfinger2025"]
    assert rule(fielddata.systems("bilfinger2025")) == 5  # GB ID.3, two Taycans, two Model Y


def test_load_returns_released_values(held):
    frame = fielddata.load("bilfinger2025", unit="Tesla_Model_Y_JB_8A_CEE7_MI_2025")
    assert frame["U"].tolist() == [400.0, 401.0] and frame.attrs["masked_value_count"] == 0
    assert fielddata.load("bilfinger2025", unit="Tesla_Model_Y_JB_8A_CEE7_MI_2025", clean=True)["U"].tolist() == [400.0, 401.0]


def test_existing_bilfinger_names_unchanged():
    from fielddata.loaders._bilfinger import vehicle
    assert vehicle("DVA_robustness/data/Cupra/Cupra_204_JB_8A_CEE7_C45.feather") == "Cupra 204"
    assert vehicle("DVA_robustness/data/Tesla/Tesla_JB_6A_CEE7_C57_2022_w_cv.feather") == "Tesla Model 3 SR+"
    assert vehicle("m1737452/data/VW/vehicle/VW_ID3_JB_8A_C40_2024.feather") == "VW ID.3"
