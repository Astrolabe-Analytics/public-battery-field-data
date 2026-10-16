"""cell_to_pack candidate loader on synthetic converted Parquet and a synthetic pack zip."""
import zipfile

import pandas as pd

from fielddata.registry import CANDIDATES, PACKAGES


def test_cell_to_pack_reads_converted_data(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import cell_to_pack

    folder = package_directory("cell_to_pack")
    converted = folder.parent / "converted"
    for unit in cell_to_pack.FIELD:
        (converted / unit).mkdir(parents=True)
        pd.DataFrame({"item": [0, 1], "cycle": [1, 2], "rate_capacity (Ah)": [302, 302], "SOH": [1.02, 0.99]}).to_parquet(
            converted / unit / f"{unit}.pkl.constant_metadata.parquet")
        pd.DataFrame({"item": [0, 0], "time(s)": [0.0, 18.0], "current(A)": [-63.3, -63.4], "Vpack": [1265.0, 1269.7],
                      "V1": [3.086, 3.096], "V2": [3.08, 3.09]}).to_parquet(converted / unit / f"{unit}.pkl.timeseries_data.parquet")
        number = unit.split("#")[1]
        with zipfile.ZipFile(folder / f"{unit}.zip", "w") as archive:
            archive.writestr(f"pack_capacity_#{number}.csv", "EFC,Pack_Capacity\n1.9,304.2\n609.8,276.2\n")
    cells = converted / "ESSH1" / "ESSH1" / "cells"
    cells.mkdir(parents=True)
    pd.DataFrame({"item": [0], "rate_capacity (Ah)": [280.0], "cycle": [1], "SOH": [1.0]}).to_parquet(cells / "Cell#31.pkl.constant_metadata.parquet")
    pd.DataFrame({"item": [0], "voltage(V)": [3.3]}).to_parquet(cells / "Cell#31.pkl.timeseries_data.parquet")
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    units = cell_to_pack.systems().set_index("unit")
    assert (units["kind"] == "field pack").sum() == 16 and units.loc["ESSH1/Cell#31", "kind"] == "laboratory cell"
    assert units.loc["Pack_field#1", "cells_in_series"] == 2 and units.loc["Pack_field#1", "efc_last"] == 609.8
    series = cell_to_pack.load("Pack_field#3")
    assert series["current(A)"].tolist() == [-63.3, -63.4] and cell_to_pack.cell_columns(series) == ["V1", "V2"]
    assert cell_to_pack.load("ESSH1/Cell#31", part="metadata")["SOH"].tolist() == [1.0]
    assert cell_to_pack.matrix("Pack_field#2")["Pack_Capacity"].tolist() == [304.2, 276.2]


def test_cell_to_pack_is_a_package():
    assert "cell_to_pack" in PACKAGES and "cell_to_pack" not in CANDIDATES  # admitted in v1.2
