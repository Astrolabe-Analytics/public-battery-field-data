"""Source audit 2026-10-04 (changan): clean=True masks the 0 V values and the -1000 A fill current, one value at a time."""
import pandas as pd

from fielddata.loaders import changan
from fielddata.loaders._base import mask_values


def test_changan_clean_masks_zero_voltage_and_minus1000_current():
    frame = pd.DataFrame({
        "chargestatus": [3, 255, 0, 1],
        "totalvoltage": [349.4, 0.0, 0.0, 380.0],
        "totalcurrent": [1.3, -1000.0, 0.0, -50.0],
        "minvoltagebattery": [3.634, 0.0, 0.0, 3.9],
        "maxvoltagebattery": [3.644, 0.0, 0.0, 3.95],
        "soc": [34, 4, 0, 74],
        "maxtemperaturevalue": [34, -40, 0, 30],
    })
    masked = mask_values(frame, changan._ZERO_RULES)
    assert masked == 7
    assert frame["totalcurrent"].isna().tolist() == [False, True, False, False]
    assert frame["totalvoltage"].isna().tolist() == [False, True, True, False]
    # rows are kept and other columns are left as released
    assert len(frame) == 4
    assert frame["soc"].tolist() == [34, 4, 0, 74]
    assert frame["maxtemperaturevalue"].tolist() == [34, -40, 0, 30]
    # a legitimate charging current and a zero current are untouched
    assert frame.loc[3, "totalcurrent"] == -50.0 and frame.loc[2, "totalcurrent"] == 0.0
