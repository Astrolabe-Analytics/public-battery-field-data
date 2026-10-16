"""tongji_rest candidate loader on synthetic converted segments and a synthetic feature workbook."""
import io
import zipfile

import pandas as pd

from fielddata.registry import CANDIDATES, PACKAGES


def test_tongji_reads_converted_segments_unchanged(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import tongji_rest

    folder = package_directory("tongji_rest")
    book = io.BytesIO()
    pd.DataFrame({"seg_num": [97], "soc_start": [19], "soc_end": [97]}).to_excel(book, index=False)
    with zipfile.ZipFile(folder / "data.zip", "w") as archive:
        archive.writestr("data/data_train/LFP01_01_fast_feature.xlsx", book.getvalue())
        archive.writestr("data/data_train/Lab101_fast_feature.xlsx", book.getvalue())
    raw = folder.parent / "converted" / "data" / "raw_test"
    for unit in tongji_rest.FIELD:
        for kind in ("charge_segment", "rest_segment"):
            (raw / f"{kind}_{unit}").mkdir(parents=True)
            frame = pd.DataFrame({"reqDate": pd.to_datetime(["2021-09-18 00:52:19", "2021-09-18 00:52:29"]),
                                  "totalVoltage": [391.0, 392.0], "totalCurrent": [-46.0, -46.0], "soc": [97.0, 97.0]},
                                 index=[950617, 950618])
            frame.to_parquet(raw / f"{kind}_{unit}" / "ch_seg_1.pkl.parquet")
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    units = tongji_rest.systems().set_index("unit")
    assert (units["kind"] == "field vehicle").sum() == 4
    assert units.loc["LFP01_01", "kind"] == "feature only" and units.loc["Lab101", "kind"] == "laboratory cell"
    frame = tongji_rest.load(unit="NMC02", kind="rest")
    assert frame["index"].tolist() == [950617, 950618] and frame["totalVoltage"].tolist() == [391.0, 392.0]
    assert frame["segment"].tolist() == ["ch_seg_1", "ch_seg_1"]
    assert tongji_rest.features("LFP01_01_fast_feature.xlsx")["soc_end"].tolist() == [97]


def test_tongji_is_a_package():
    assert "tongji_rest" in PACKAGES and "tongji_rest" not in CANDIDATES  # admitted in v1.2
