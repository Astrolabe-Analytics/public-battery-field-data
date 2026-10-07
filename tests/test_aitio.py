"""aitio candidate loader on synthetic data: reads .npz members from the shipped zips, unchanged."""
import io
import zipfile

import numpy as np

from fielddata.registry import CANDIDATES, PACKAGES


def _npz(array):
    buffer = io.BytesIO()
    np.savez_compressed(buffer, array)
    return buffer.getvalue()


def test_aitio_reads_npz_from_zips(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import aitio

    directory = package_directory("aitio")
    battery_0 = np.array([[1548934858.0, 0.02, 12.66, 32.2], [1548934918.0, -1.5, 13.1, 32.4]])
    battery_7 = np.array([[1548934800.0, 0.5, 12.5, 30.0], [1548934860.0, 0.5, 0.01, 30.0], [1548934920.0, 0.5, 12.6, 30.0]])
    for name in aitio.ZIPS:
        with zipfile.ZipFile(directory / name, "w") as z:
            if name == "set_0.zip":
                z.writestr("0.npz", _npz(battery_0))
            if name == "set_1.zip":
                z.writestr("7.npz", _npz(battery_7))
    (directory / "meta_data.csv").write_text("ID,ACTIVATED,IN_REPAIR_SYSTEM,STILL_ALIVE,Lifetime\n0,1/31/2019,,TRUE,593\n7,1/1/2019,1/31/2019,FALSE,30\n")
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)
    aitio._members.cache_clear()

    units = aitio.systems()
    assert list(units["unit"]) == ["0", "7"] and list(units["zip"]) == ["set_0.zip", "set_1.zip"]
    frame = aitio.load(unit="0")
    assert list(frame.columns) == aitio.COLUMNS
    assert frame["current_A"].tolist() == [0.02, -1.5]  # negative = charging, kept as released
    assert str(frame.index[0]) == "2019-01-31 11:40:58+00:00"
    assert frame.attrs["masked_value_count"] == 0
    raw, cleaned = aitio.load(unit="7"), aitio.load(unit="7", clean=True)
    assert raw["voltage_V"].tolist() == [12.5, 0.01, 12.6]  # raw keeps the sub-1 V blip
    assert cleaned["voltage_V"].isna().tolist() == [False, True, False] and len(cleaned) == 3
    assert cleaned.attrs["masked_value_count"] == 1
    # battery 7 entered repair on 2019-01-31 (00:00 UTC): its rows from then on are dropped only when asked
    assert len(aitio.load(unit="7", clean=True)) == 3
    cut = aitio.load(unit="7", truncate_at_repair=True)
    assert len(cut) == 0 and cut.attrs["rows_dropped_after_repair"] == 3
    live = aitio.load(unit="0", truncate_at_repair=True)
    assert len(live) == 2 and live.attrs["rows_dropped_after_repair"] == 0  # live batteries unchanged
    aitio._members.cache_clear()


def test_aitio_is_package_23():
    assert "aitio" in PACKAGES and "aitio" not in CANDIDATES
    assert len(PACKAGES["aitio"]["direct_files"]) == 16 and len(PACKAGES["aitio"]["own_sha256"]) == 16
