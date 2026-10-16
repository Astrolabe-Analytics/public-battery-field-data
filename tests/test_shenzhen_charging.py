"""shenzhen_charging candidate loader on a synthetic workbook: sessions are units, Sheet7 repeats Sheet1."""
import pandas as pd

from fielddata.registry import CANDIDATES, PACKAGES


def test_shenzhen_sessions_counted_once(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import shenzhen_charging as sz

    folder = package_directory("shenzhen_charging")

    def rows(tid, ids, label, owner):
        return pd.DataFrame({"id": ids, "transaction_id": [tid] * len(ids), "begin_time": ["2022-03-03 04:51:08"] * len(ids),
                             "end_time": [f"2022-03-03 04:5{i}:08" for i in range(len(ids))], "total_charging_kwh": 1.0,
                             "total_charging_min": 1, "current_soc": 50, "current_energy_meter_value": 10.0, "chargingv": 400.0,
                             "charginga": 20.0, "out_power": 8.0, "charging_gun_temperature1": 30, "charging_gun_temperature2": 31,
                             "types": 6, "class_judge": owner, "label": label})

    a, b = "44010000100000052203030401089310", "44010000100000052203030401089311"  # text: Excel would round 32-digit numbers
    with pd.ExcelWriter(folder / sz.FILES["processed_data"]) as writer:
        rows(a, [1, 2], 0, 3).to_excel(writer, sheet_name="Sheet1", index=False)
        rows(b, [3], 1, 5).to_excel(writer, sheet_name="Sheet2", index=False)
        rows(a, [1, 2], 0, 3).to_excel(writer, sheet_name="Sheet7", index=False)
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)
    sz._rows.cache_clear()

    sessions = sz.systems().set_index("unit")
    assert len(sessions) == 2 and sessions.loc[str(a), "sheets"] == "Sheet1,Sheet7" and sessions.loc[str(a), "rows"] == 2
    assert sessions.loc[str(b), "label"] == 1 and sessions.loc[str(b), "chemistry"] == "NMC"
    raw = sz.load(unit=str(a))
    assert len(raw) == 4 and raw["sheet"].tolist() == ["Sheet1", "Sheet1", "Sheet7", "Sheet7"]  # as released
    assert raw["chargingv"].tolist() == [400.0] * 4
    sz._rows.cache_clear()


def test_shenzhen_is_a_package():
    assert "shenzhen_charging" in PACKAGES and "shenzhen_charging" not in CANDIDATES  # admitted in v1.2
