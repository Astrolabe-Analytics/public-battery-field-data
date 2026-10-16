"""ved candidate loader on synthetic static workbooks and already-extracted weekly CSVs, read unchanged."""
import pandas as pd

from fielddata.registry import CANDIDATES, PACKAGES


def test_ved_reads_weeks_unchanged(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import ved

    folder = package_directory("ved")
    data = folder / "VED" / "Data"
    data.mkdir(parents=True)
    pd.DataFrame({"VehId": [2, 439], "Vehicle Type": ["ICE", "HEV"]}).to_excel(data / ved.STATIC["ICE&HEV"], index=False)
    pd.DataFrame({"VehId": [9, 10], "EngineType": ["PHEV", "EV"]}).to_excel(data / ved.STATIC["PHEV&EV"], index=False)
    extracted = folder.parent / "extracted"
    extracted.mkdir()
    for i in range(54):  # the loader expects all 54 weeks before it skips extraction
        week = f"17{11 + i // 30:02d}{1 + i % 30:02d}"
        pd.DataFrame({"DayNum": [1.5, 1.6], "VehId": [10, 2], "Trip": [1, 2], "HV Battery SOC[%]": [96.3, None]}).to_csv(
            extracted / f"VED_{week}_week.csv", index=False)
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    vehicles = ved.systems().set_index("unit")
    assert int(vehicles["battery_signals"].sum()) == 2 and vehicles.loc["10", "rated_kwh_stated"] == 24.0
    assert vehicles.loc["439", "Vehicle Type"] == "HEV" and not vehicles.loc["439", "battery_signals"]
    assert len(ved.weeks()) == 54
    rows = ved.load(unit=10, week="171101")
    assert rows["HV Battery SOC[%]"].tolist() == [96.3] and rows["week"].tolist() == ["171101"]
    assert len(ved.load(week=["171101", "171102"])) == 4


def test_ved_is_a_package():
    assert "ved" in PACKAGES and "ved" not in CANDIDATES  # admitted in v1.2
