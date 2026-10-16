"""birds_cubesat candidate loader on synthetic workbooks: one sheet per download, columns named by position."""
import pandas as pd

from fielddata.registry import CANDIDATES, PACKAGES


def test_birds_cubesat_reads_sheets_unchanged(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import birds_cubesat

    folder = package_directory("birds_cubesat")
    header = ["Time Stamp"] + [f"c{i}" for i in range(1, 37)]
    for unit in birds_cubesat.UNITS:
        with pd.ExcelWriter(folder / f"{unit}.xlsx") as writer:
            pd.DataFrame([[0] + [1.0] * 36, [5] + [2.0] * 36], columns=header).to_excel(writer, sheet_name="9 Nov 2020", index=False)
            if unit == "TSURU":
                pd.DataFrame([[0] + [3.0] * 36, [10] + [4.0] * 36], columns=["Time stamp"] + header[1:]).to_excel(writer, sheet_name="March 28", index=False)
                pd.DataFrame([[0] + [0.0] * 36], columns=header).to_excel(writer, sheet_name="Test1 w batt", index=False)
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    sheets = birds_cubesat.sheets().set_index(["unit", "sheet"])
    assert sheets.loc[("TSURU", "March 28"), "date"] == pd.Timestamp("2021-03-28")
    assert sheets.loc[("TSURU", "Test1 w batt"), "kind"] == "test"
    units = birds_cubesat.systems().set_index("unit")
    assert units.loc["TSURU", "downloads"] == 2 and units.loc["TSURU", "test_sheets"] == 1
    assert units.loc["NEPALISAT", "pack_nominal_Wh"] == 14.4
    frame = birds_cubesat.load(unit="TSURU")
    assert list(frame.columns) == ["sheet", *birds_cubesat.COLUMNS]
    assert frame["time_s"].tolist() == [0, 5, 0, 10, 0]
    assert frame["Vbat_V"].tolist() == [1.0, 2.0, 3.0, 4.0, 0.0]


def test_birds_cubesat_is_a_package():
    assert "birds_cubesat" in PACKAGES and "birds_cubesat" not in CANDIDATES  # admitted in v1.2
