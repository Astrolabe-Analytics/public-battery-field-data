"""giu_ebike candidate loader on a synthetic zip shaped like the release."""
import zipfile

from fielddata.registry import CANDIDATES, PACKAGES

CLEAN_HEADER = ("time,phase,source_file,valid,current_A,current_corr_A,ah_out_corr,pack_V,"
                + ",".join(f"cell{i:02d}" for i in range(1, 14)) + ",t_amb_C,t_edge_C,t_center_C,jk_soc_pct,jk_bal_A\n")
RAW_HEADER = ("utc_time,time_source,uptime_ms,jk_age_ms,pack_V,current_A,charge_Ah,t_pack_C,t_amb_C,jk_t1_C,jk_t2_C,jk_mos_C,"
              "jk_soc_pct,jk_cap_rem_Ah," + ",".join(f"cell{i:02d}" for i in range(1, 14)) + "\n")


def test_giu_ebike_reads_zip_as_released(monkeypatch, tmp_path):
    from fielddata.loaders import giu_ebike as eb

    folder = tmp_path / "d"  # short path for Windows
    folder.mkdir()
    cells = ",".join(["4.0600"] * 13)
    with zipfile.ZipFile(folder / "ebike-pack-dataset.zip", "w") as archive:
        archive.writestr("ebike-pack-dataset/README.md", "# Real-road cell-level dataset\n")
        for name in eb.CLEAN:
            archive.writestr(f"ebike-pack-dataset/{name}.csv", CLEAN_HEADER
                             + f"2026-11-06 21:20:05,rest,jk_011.csv,True,-0.0000,-0.0000,-0.0000,52.7800,{cells},24.25,25.4,25.4,100.0,0.0\n"
                             + f"2026-11-06 21:20:06,ride1,jk_011.csv,False,16.0000,15.0400,0.0040,52.7000,{cells},24.25,25.4,25.4,100.0,-0.593\n")
        archive.writestr("ebike-pack-dataset/raw/jk_001_before_repair.csv", RAW_HEADER
                         + "2026-10-29T23:15:08Z,ntp,8904,133,52.788,-0.000,0.00000,21.44,19.62,21.7,21.7,23.7,96,11.558,"
                         + ",".join(["4.059"] * 7 + ["0.000"] + ["4.060"] * 5) + "\n")
    monkeypatch.setattr(eb, "directory", lambda package: folder)

    assert eb.systems()["cells"].item() == 52 and len(eb.systems()) == 1
    clean = eb.load()
    assert len(clean) == 10 and clean["current_A"].tolist()[:2] == [0.0, 16.0]  # positive in discharge, unchanged
    assert str(clean["time"].dt.tz) == "None" and clean.attrs["masked_value_count"] == 0
    raw = eb.load(eb.RAW)
    assert raw["cell08"].item() == 0.0 and str(raw["utc_time"].dt.tz) == "UTC"  # a 0 V reading is kept
    rec = eb.recordings().set_index("recording")
    assert rec.loc["3_ride_B", "phases"] == "rest;ride1" and rec.loc[eb.RAW, "time_basis"] == "UTC"


def test_giu_ebike_was_admitted_in_v13():
    assert "giu_ebike" in PACKAGES and "giu_ebike" not in CANDIDATES
    assert "status" not in PACKAGES["giu_ebike"]
