"""brazil_star candidate loader on a synthetic zip of daily CSVs, read unchanged."""
import zipfile

from fielddata.registry import CANDIDATES, PACKAGES


def test_brazil_star_reads_zip_members_unchanged(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import brazil_star

    folder = package_directory("brazil_star")
    header = "Time,Current,AmpereHours,SOC,NumChargeCycles,NumFullDischarge,Voltage,Power,DischargeEnergy,ChargeEnergy\r\n"
    with zipfile.ZipFile(folder / brazil_star.ARCHIVE, "w") as archive:
        archive.writestr("MonitoringDataReadMe.txt", "readme")
        archive.writestr("2018-06-08_STAR-A_Battery.csv", header + "2018-06-08 11:13:38,-500,-100,950,1,0,24207,-12,2,64939\r\n"
                         "1969-12-31 20:00:00,64356,0,-5,1,0,24207,0,2,64939\r\n")
        archive.writestr("2018-06-09_STAR-A_Battery.csv", header + "2018-06-09 11:13:38,300,200,1000,1,0,25100,8,2,64940\r\n")
        archive.writestr("2018-06-09_STAR-A_PV.csv", "Time,Panel_voltage,Panel_power,Energy_generated,Battery_state\r\n2018-06-09 12:00:00,103970,459,159,3\r\n")
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    units = brazil_star.systems().set_index("unit")
    assert list(units.index) == brazil_star.UNITS
    assert units.loc["STAR-A", "battery_days"] == 2 and units.loc["STAR-A", "pv_days"] == 1
    assert str(units.loc["STAR-A", "first"]) == "2018-06-08 11:13:38" and units.loc["STAR-A", "battery_time_invalid"] == 1
    raw = brazil_star.load(unit="STAR-A")
    assert raw["Current"].tolist() == [-500, 64356, 300] and raw["SOC"].tolist() == [950, -5, 1000]
    assert raw["file"].iloc[0] == "2018-06-08_STAR-A_Battery.csv"
    clean = brazil_star.load(unit="STAR-A", clean=True)
    assert clean.attrs["masked_value_count"] == 2 and clean["Time"].isna().sum() == 1 and clean["SOC"].isna().sum() == 1
    assert clean["Current"].tolist() == [-500, 64356, 300]  # the wrapped current is kept
    assert brazil_star.load(unit="STAR-A", system="PV")["Panel_voltage"].tolist() == [103970]


def test_brazil_star_is_a_package():
    assert "brazil_star" in PACKAGES and "brazil_star" not in CANDIDATES  # admitted in v1.2
