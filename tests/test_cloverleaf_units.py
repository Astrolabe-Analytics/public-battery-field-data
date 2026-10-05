"""cloverleaf: systems() lists the three packs only (Table 2 and the dashboard say 3); the typical-day sheet stays loadable."""
import pandas as pd

from fielddata.loaders import cloverleaf


def _sheet(note, rows):
    header = [["epoch_ms", note] + [None] * 8, cloverleaf._PACK_COLUMNS, [None, None, "%", "%", "Volt", "Volt", "Volt", "Volt", "Volt", "Ampere"]]
    body = [[1.63e12 + i, f"2021-09-01 0{i}:00:00", 90, 50, 0.01, 3.6, 3.7, 3.5, 360, 1.0] for i in range(rows)]
    return pd.DataFrame(header + body)


def test_systems_lists_only_the_packs_and_typical_day_still_loads(monkeypatch):
    sheets = {name: _sheet("All values are average values over 20000 seconds", 3)
              for name in ("SNAM HV - 2100173", "SNAM HV - 2100177", "SNAM HV - 2100179")}
    sheets["typical day"] = _sheet("All values are average values over 172 seconds", 4)
    monkeypatch.setattr(cloverleaf, "_sheets", lambda: sheets)
    units = cloverleaf.systems()
    assert list(units["unit"]) == ["SNAM HV - 2100173", "SNAM HV - 2100177", "SNAM HV - 2100179"]
    assert set(units["kind"]) == {"pack"}
    assert len(cloverleaf.typical_day()) == 4
    assert len(cloverleaf.load("typical day")) == 4
