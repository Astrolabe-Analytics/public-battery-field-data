"""beijing_ev candidate loader on synthetic workbooks: one per day, read unchanged."""
import pandas as pd

from fielddata.registry import CANDIDATES, PACKAGES


def test_beijing_ev_reads_days_unchanged(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import beijing_ev

    folder = package_directory("beijing_ev")
    rows = {"time": [20180103063058, 20180103063108], "speed": [0.0, 9.1], "mileage": [54945, 54945],
            "voltage": [371.9, 370.4], "current": [0.0, 1.3], "soc": [100, 100]}
    for name, shift in (("2018/2018.1.3.xlsx", 0), ("2019/2019.8.15.xlsx", 10000000000)):
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(rows)
        frame["time"] = frame["time"] + shift
        frame.to_excel(path, index=False)
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    days = beijing_ev.systems()
    assert days["unit"].tolist() == ["2018-01-03", "2019-08-15"]
    assert days["vehicle"].nunique() == 1 and days.loc[0, "first"] == pd.Timestamp("2018-01-03 06:30:58")
    frame = beijing_ev.load(unit="2018-01-03")
    assert list(frame.columns) == beijing_ev.COLUMNS and frame["current"].tolist() == [0.0, 1.3]
    assert frame["time"].tolist() == [20180103063058, 20180103063108]  # as released
    both = beijing_ev.load()
    assert both["unit"].tolist() == ["2018-01-03"] * 2 + ["2019-08-15"] * 2


def test_beijing_ev_is_a_package():
    assert "beijing_ev" in PACKAGES and "beijing_ev" not in CANDIDATES  # admitted in v1.2
