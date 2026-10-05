"""Synthetic-data tests for the tsukuba loader changes from the 2026-10-04 source audit."""
import io
import zipfile

import pandas as pd
import pytest

import fielddata
from fielddata.loaders import _base

HEADER = "#,蓄電池　有効電力,蓄電池　直流電流,蓄電池　ＳＯＣ値\n#,10101,10106,12152\n#,kW,A,%\n".encode("cp932")


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    return tmp_path


def _release(package_directory, raw, cleaned=None):
    from fielddata.loaders import tsukuba
    d = package_directory("tsukuba")

    def inner(members):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for name, body in members.items():
                z.writestr(name, body)
        return buffer.getvalue()

    with zipfile.ZipFile(d / tsukuba.PACKAGES["tsukuba"]["data_files"][0], "w") as z:
        z.writestr("1 Raw_data_per_second.zip", inner(raw))
        z.writestr("2 Cleaned_data_per_second.zip", inner(cleaned if cleaned is not None else raw))


def test_clean_masks_only_the_error_code(root, package_directory):
    rows = b"'2015/11/14 00:00:00,-999999,5,-999999\n'2015/11/14 00:00:01,1.5,-999999,95\n'2015/11/14 00:00:02,2.0,-500,96\n"
    _release(package_directory, {"20151113-20151124SecCsv.csv": HEADER + rows})
    raw = fielddata.load("tsukuba", start="2015-11-14", end="2015-11-14")
    clean = fielddata.load("tsukuba", start="2015-11-14", end="2015-11-14", clean=True)
    assert (raw == -999999).sum().sum() == 3 and raw.attrs["masked_value_count"] == 0
    assert len(clean) == 3 and clean.isna().sum().sum() == 3 and clean.attrs["masked_value_count"] == 3
    assert clean["battery_dc_current"].iloc[2] == -500  # out-of-range current is left to version="cleaned"


def test_misnamed_member_and_empty_range(root, package_directory):
    from fielddata.loaders import tsukuba
    rows = b"'2015/07/12 23:59:59,1,2,50\n"
    _release(package_directory, {"20150701-20160712SecCsv.csv": HEADER + rows})
    table = tsukuba.files("raw")
    assert table["last_day"].iloc[0] == pd.Timestamp("2015-07-12")
    assert len(fielddata.load("tsukuba", start="2015-07-12", end="2015-07-12")) == 1
    empty = fielddata.load("tsukuba", start="2016-01-01", end="2016-01-02")
    assert empty.empty and "battery_soc" in empty.columns


def test_seconds_lost_in_cleaned_rows_are_restored(root, package_directory):
    rows_a = b"'2015/11/14 20:13:36,1,2,3\n2015/11/14 20:13,4,5,6\n'2015/11/14 20:13:38,7,8,9\n"
    rows_b = b"2017/3/13 0:00,1,2,3\n'2017/03/13 00:00:01,4,5,6\n"
    _release(package_directory, {"20151113-20151124SecCsv.csv": HEADER + rows_a, "20170313-20170324SecCsv.csv": HEADER + rows_b})
    a = fielddata.load("tsukuba", start="2015-11-14", end="2015-11-14", version="cleaned")
    b = fielddata.load("tsukuba", start="2017-03-13", end="2017-03-13", version="cleaned")
    assert list(a.index.strftime("%H:%M:%S")) == ["20:13:36", "20:13:37", "20:13:38"]
    assert list(b.index.strftime("%H:%M:%S")) == ["00:00:00", "00:00:01"]


def test_trailing_empty_fields_are_dropped(root, package_directory):
    header = "#,蓄電池　ＳＯＣ値,,\n#,12152,,\n#,%,,\n".encode("cp932")
    rows = b"'2018/04/01 00:00:00,96.75,,\n'2018/04/01 00:00:01,96.75,,\n"
    _release(package_directory, {"20180401-20180412SecCsv.csv": header + rows})
    frame = fielddata.load("tsukuba", start="2018-04-01", end="2018-04-01", version="cleaned")
    assert list(frame.columns) == ["battery_soc"] and list(frame.attrs["signals"]) == ["battery_soc"]
