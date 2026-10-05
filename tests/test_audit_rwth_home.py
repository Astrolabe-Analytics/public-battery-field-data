"""Source audit 2026-10-04: rwth-home members() lists every archive member, months() keeps only the monthly
CSVs (the deposit holds 1,269, not the stated 1,270), and raw values (positive charging current, NaN outliers, Interpolated flag) pass through. Synthetic data only."""
import zipfile

import pandas as pd
import pytest

import fielddata
from fielddata.loaders import _base, rwth_home


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    return tmp_path


def _release(package_directory):
    d = package_directory("rwth-home")
    body = ("Time,P_in_W,V_in_V,I_in_A,T_Bat_in_C,T_Room_in_C,Interpolated\n"
            "25-Mar-2018 01:59:59,500.0,50.0,10.0,25.0,20.0,0\n"
            "25-Mar-2018 02:00:00,,50.1,,25.0,20.0,1\n")
    with zipfile.ZipFile(d / "Data_ID_01.zip", "w") as z:
        z.writestr("01/2018_03_System_ID_01.csv", body)
        z.writestr("01/notes.txt", "x")


def test_members_and_months(root, package_directory):
    _release(package_directory)
    assert sorted(rwth_home.members(1)) == ["01/2018_03_System_ID_01.csv", "01/notes.txt"]
    assert rwth_home.months(1) == [("2018-03", "01/2018_03_System_ID_01.csv")]


def test_raw_values_and_naive_clock(root, package_directory):
    _release(package_directory)
    frame = fielddata.load("rwth-home", unit=1, month="2018-03")
    assert frame.index.tz is None
    assert frame.index[1] == pd.Timestamp("2018-03-25 02:00:00")  # no DST gap applied
    assert frame["I_in_A"].iloc[0] == 10.0 and pd.isna(frame["I_in_A"].iloc[1])
    assert frame["Interpolated"].tolist() == [0, 1]
    assert fielddata.load("rwth-home", unit=1, month="2018-03", clean=True).attrs["masked_value_count"] == 0
