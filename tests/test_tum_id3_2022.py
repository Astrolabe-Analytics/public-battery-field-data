"""tum_id3_2022 candidate loader on synthetic track CSVs: one vehicle, drives read unchanged."""
import pandas as pd

from fielddata.registry import CANDIDATES, PACKAGES


def test_tum_id3_reads_tracks_unchanged(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import tum_id3_2022 as tum

    tracks = package_directory("tum_id3_2022") / "Data" / "Tracks"
    tracks.mkdir(parents=True)
    pd.DataFrame({"hv_battery_current": [-1.11, -1.11], "hv_soc": [95.6, 95.6], "time": [1613030450000, 1613030450100]}).to_csv(
        tracks / "track_0.csv", index=False)
    pd.DataFrame({"cell_voltage_1": [3.9], "time": [1638972860900]}).to_csv(tracks / "track_147.csv", index=False)
    (tracks.parent / "value_definitions.csv").write_text(
        '"Note",,,,,,\n,,,,,,\nRequest_ID,Value_ID,Name_en,Variable_name,Unit,Source (UDS request),Description\n,,SOC,hv_soc,%,,SOC\n',
        encoding="latin-1")
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    vehicle = tum.systems()
    assert len(vehicle) == 1 and vehicle.loc[0, "same_as"] == "tumftm ID1" and vehicle.loc[0, "tracks"] == 2
    assert vehicle.loc[0, "first"] == pd.Timestamp("2021-02-11 08:00:50")
    frame = tum.load(track=0)
    assert frame["hv_battery_current"].tolist() == [-1.11, -1.11] and frame["track"].tolist() == [0, 0]
    assert list(tum.load(track=147, columns=["cell_voltage_1", "hv_soc"]).columns) == ["track", "cell_voltage_1", "time"]
    assert tum.definitions()["Variable_name"].tolist() == ["hv_soc"]


def test_tum_id3_is_a_package():
    assert "tum_id3_2022" in PACKAGES and "tum_id3_2022" not in CANDIDATES  # admitted in v1.2
