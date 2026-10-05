"""Source-audit follow-up tests for m5bat-2023-04 (synthetic data, no data folder needed).

The evaluation report (pp. 6-7) gives DateAndTime as UTC, so the loader returns a UTC index; systems() carries
the report's p. 3 unit table.
"""
import zipfile

import pandas as pd
import pytest

import fielddata
from fielddata.loaders import _base


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    return tmp_path


def _release(package_directory):
    d = package_directory("m5bat-2023-04")
    unit = "DateAndTime;P_AC;SOC;I_DC_Batt;U_DC_Batt;interpolated\n2023-04-01 00:00:01;-5;431;-80;6011;0\n2023-04-01 00:00:00;-4;430;-70;6010;0\n"
    bess = "DateAndTime;M5BAT_P;Grid_frequency;Temperature;SOC;interpolated\n2023-04-01 00:00:00;-2;49990;104;37;0\n"
    with zipfile.ZipFile(d / "M5BAT_04-2023_RAW.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("Batt1", "Batt9", "Batt10"):
            z.writestr(f"{name}.csv", unit)
        z.writestr("BESS.csv", bess)


def test_index_is_utc(root, package_directory):
    _release(package_directory)
    frame = fielddata.load("m5bat-2023-04", unit="Batt9")
    assert str(frame.index.tz) == "UTC"
    assert frame.index[0] == pd.Timestamp("2023-04-01 00:00:00", tz="UTC")
    assert frame["U_DC_Batt"].tolist() == [6010, 6011]  # released integers, not rescaled
    bess = fielddata.load("m5bat-2023-04", unit="BESS")
    assert str(bess.index.tz) == "UTC" and bess["Grid_frequency"].iloc[0] == 49990


def test_systems_carry_report_unit_table(root, package_directory):
    _release(package_directory)
    s = fielddata.systems("m5bat-2023-04").set_index("unit")
    assert s.index.tolist() == ["Batt1", "Batt9", "Batt10", "BESS"]
    assert s.loc["Batt1", "abbreviation"] == "Pb1" and s.loc["Batt1", "wiring"] == "300s1p"
    assert s.loc["Batt9", "abbreviation"] == "LFP" and s.loc["Batt9", "wiring"] == "240s10p"
    assert s.loc["Batt10", "abbreviation"] == "LTO" and s.loc["Batt10", "nominal_energy_kwh"] == 230
    assert pd.isna(s.loc["BESS", "abbreviation"]) and s.loc["BESS", "kind"] == "plant connection point"
    from fielddata.counting import units
    assert units("m5bat-2023-04") == 3
