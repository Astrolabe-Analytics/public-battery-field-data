"""Source-audit data checks for the ppl release (reports/source_audit_2026-10-04/ppl.md).

What it does, through the ppl loader only (raw values, clean=False):
  1. Grid: rows, duplicate and missing minutes per annual file, and the rows around the 2018-2025 daylight
     saving changes (US, second Sunday of March and first Sunday of November).
  2. Time zone: (a) hour of the daily maximum of Container1.Temp and Container2.Temp in July; (b) hour-of-day
     profile of the PSmoothing (PV smoothing) mode in June-July and in December-January, which follows the sun;
     (c) start times of full-power discharges from at least 85 % to at most 15 % AvgSOC (the paper's reference
     tests discharge "after sunset", Section VII), compared with sunset at Burgin, Kentucky (37.75 N, 84.77 W),
     computed with the NOAA solar-position formulas; (d) the last rows of 2021 and the first rows of 2022.
  3. Zeros and outages: per year, rows with SOH, AvgSOC, CellVoltAvg equal to 0 and with Running equal to 0,
     the longest runs of SOH == 0 and of Running == 0 (start, end, days), and the longest runs of unchanged
     AvgSOC; plus the share of minutes on a straight line between neighbours (linear fill).
  4. Sign: correlation of PowerReal with the next-minute change of AvgSOC (2018-2020), and of DCCurrent with
     PowerReal and with the AvgSOC change (2022-2025).
  5. Cell-level share (not read by load()): the zips held, and in one day of July 2018 and one day of 2025 the
     log types, the RARD log columns, the (bank, rack) pairs it covers and its time step.
Reads: the ppl release through fielddata (nine annual CSVs, about 4.3 million rows; two cell-level zips).
Writes: nothing; prints the results.
Run from the repo root: .venv/Scripts/python.exe <path to this file>
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))  # run from the repo root

import numpy as np
import pandas as pd

import fielddata
from fielddata.loaders import ppl

LAT, LON = 37.75, -84.77


def naive(frame):
    """load() tags the index UTC without a stated basis; checks use the released wall-clock values."""
    out = frame.copy()
    out.index = out.index.tz_localize(None) if out.index.tz is not None else out.index
    return out


def sunset_utc(dates):
    """Sunset time (UTC hours) at Burgin, KY, NOAA approximation, for an array of dates."""
    d = pd.DatetimeIndex(dates)
    n = d.dayofyear.values
    g = 2 * np.pi / 365 * (n - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = 0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g)
    lat = np.radians(LAT)
    ha = np.degrees(np.arccos(np.cos(np.radians(90.833)) / (np.cos(lat) * np.cos(decl)) - np.tan(lat) * np.tan(decl)))
    minutes = 720 - 4 * (LON - ha) - eqtime
    return minutes / 60


def runs(mask):
    """Start, end and length (rows) of each run of True in a boolean Series with a time index."""
    m = mask.to_numpy()
    if not m.any():
        return pd.DataFrame(columns=["start", "end", "rows"])
    edges = np.diff(np.concatenate([[0], m.astype(int), [0]]))
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0] - 1
    return pd.DataFrame({"start": mask.index[starts], "end": mask.index[ends], "rows": ends - starts + 1})


def grid(frames):
    print("[1 grid] per annual file")
    for year, f in frames.items():
        idx = f.index
        steps = pd.Series(idx[1:] - idx[:-1])
        print(f"  {year}: rows {len(f)}, first {idx.min()}, last {idx.max()}, duplicate stamps {int(idx.duplicated().sum())}, "
              f"steps != 60 s {int((steps != pd.Timedelta(minutes=1)).sum())}, NaT {int(idx.isna().sum())}")
    print("  rows in the 02:00-02:59 hour on spring-forward days, and rows in 01:00-01:59 on fall-back days:")
    for year in range(2018, 2026):
        f = frames[year]
        sundays_mar = pd.date_range(f"{year}-03-01", f"{year}-03-31", freq="W-SUN")
        sundays_nov = pd.date_range(f"{year}-11-01", f"{year}-11-30", freq="W-SUN")
        spring, fall = sundays_mar[1], sundays_nov[0]
        n_spring = len(f.loc[f"{spring.date()} 02:00":f"{spring.date()} 02:59"])
        n_fall = len(f.loc[f"{fall.date()} 01:00":f"{fall.date()} 01:59"])
        print(f"    {year}: {spring.date()} 02:xx rows {n_spring}; {fall.date()} 01:xx rows {n_fall}")


def linear_share(frames):
    print("\n[3b linear fill] share of minutes whose value lies on the straight line between its neighbours while the value changes")
    for year, f in frames.items():
        out = []
        for col in ["AvgSOC", "CellVoltAvg", "Container1.Temp"]:
            v = f[col].astype(float)
            d1 = v.diff()
            d2 = d1.diff()
            moving = d1.abs() > 0
            linear = moving & (d2.abs() < 1e-6) & moving.shift(1, fill_value=False)
            out.append(f"{col} {linear.sum() / max(moving.sum(), 1):.2f}")
        print(f"  {year}: " + ", ".join(out))


def timezone(frames):
    print("\n[2a] hour of the daily maximum container temperature, July days, median and quartiles")
    for year in range(2018, 2026):
        f = frames[year]
        jul = f.loc[f"{year}-07-01":f"{year}-07-31"]
        for col in ["Container1.Temp", "Container2.Temp"]:
            daily = jul[col].groupby(jul.index.date).idxmax().dropna()
            hours = pd.Series([t.hour + t.minute / 60 for t in daily])
            print(f"  {year} {col}: days {len(hours)}, median hour {hours.median():.1f}, quartiles {hours.quantile(.25):.1f}-{hours.quantile(.75):.1f}")
    print("\n[2b] PSmoothing (PV smoothing) minutes by hour of day, summed over years: first and last hour with at least 1 % of the busiest hour, and the weighted mean hour")
    all_ = pd.concat([frames[y] for y in range(2018, 2026)])
    ps = all_[all_["Mode"] == "PSmoothing"]
    for label, months in (("Jun-Jul", [6, 7]), ("Dec-Jan", [12, 1])):
        s = ps[ps.index.month.isin(months)]
        h = s.index.hour.value_counts().sort_index().reindex(range(24), fill_value=0)
        active = h[h >= 0.01 * h.max()].index
        mean_hour = np.average(np.arange(24) + 0.5, weights=h.values) if h.sum() else np.nan
        print(f"  {label}: minutes {int(h.sum())}, active hours {active.min()} to {active.max()}, mean hour {mean_hour:.2f}")
    sun = sunset_utc(pd.to_datetime(["2020-06-21", "2020-12-21"]))
    print(f"  reference: solar noon at Burgin about {12 + 84.77 / 15:.2f} UTC = {12 + 84.77 / 15 - 5:.2f} EST = {12 + 84.77 / 15 - 4:.2f} EDT; "
          f"sunset UTC {sun[0]:.2f} (21 Jun), {sun[1]:.2f} (21 Dec)")

    print("\n[2c] full-power discharges from >= 85 % to <= 15 % AvgSOC, start time vs sunset")
    rows = []
    for year in range(2018, 2026):
        f = frames[year]
        soc, p = f["AvgSOC"].astype(float), f["PowerReal"].astype(float)
        for sign in (1, -1):
            big = (sign * p) > 700
            for _, r in runs(big).iterrows():
                if r["rows"] < 60:
                    continue
                s0, s1 = soc.loc[r["start"]], soc.loc[r["end"]]
                if s0 >= 85 and s1 <= 15:
                    rows.append({"year": year, "power_sign": sign, "start": r["start"], "end": r["end"], "minutes": r["rows"], "soc_start": s0, "soc_end": s1})
    found = pd.DataFrame(rows)
    if found.empty:
        print("  none found")
    else:
        found["sunset_utc_h"] = sunset_utc(found["start"].dt.normalize())
        found["start_h"] = found["start"].dt.hour + found["start"].dt.minute / 60
        dst = found["start"].apply(lambda t: pd.Timestamp(t).tz_localize("America/New_York", ambiguous=True, nonexistent="shift_forward").utcoffset().total_seconds() / 3600)
        found["sunset_local_h"] = found["sunset_utc_h"] + dst
        found["after_sunset_if_local"] = found["start_h"] >= found["sunset_local_h"]
        found["after_sunset_if_utc"] = found["start_h"] >= found["sunset_utc_h"]
        print(found.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
        print(f"  discharges {len(found)}; start after sunset if timestamps are local: {int(found['after_sunset_if_local'].sum())}; "
              f"if UTC: {int(found['after_sunset_if_utc'].sum())}")

    print("\n[2d] last rows of 2021 and first rows of 2022")
    cols = ["AvgSOC", "SOH", "PowerReal", "Mode", "Running", "CellVoltAvg", "Container1.Temp"]
    print(frames[2021][cols].tail(3).to_string())
    print(frames[2022][cols].head(3).to_string())


def zeros(frames):
    print("\n[3a zeros and outages] per year (raw)")
    for year, f in frames.items():
        line = [f"rows {len(f)}"]
        for col in ["SOH", "AvgSOC", "CellVoltAvg", "Container1.Temp", "ModuleTempMax", "DCVoltage"]:
            if col in f:
                line.append(f"{col}==0 {int((f[col] == 0).sum())}")
        line.append(f"Running==0 {int((f['Running'] == 0).sum())}")
        line.append(f"Running NaN {int(f['Running'].isna().sum())}")
        line.append(f"blank AvgSOC {int(f['AvgSOC'].isna().sum())}")
        print(f"  {year}: " + ", ".join(line))
    allf = pd.concat(list(frames.values()))
    allf = allf[~allf.index.duplicated()]
    for label, mask in (("SOH == 0", allf["SOH"] == 0), ("CellVoltAvg == 0", allf["CellVoltAvg"] == 0), ("Running == 0", allf["Running"] == 0)):
        r = runs(mask)
        r["days"] = r["rows"] / 1440
        print(f"  longest runs of {label} (rows, all years):")
        print(r.sort_values("rows", ascending=False).head(8).to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    print("  longest runs of unchanged AvgSOC (non-zero), all years:")
    soc = allf["AvgSOC"]
    same = (soc.diff() == 0) & (soc != 0)
    r = runs(same)
    r["days"] = r["rows"] / 1440
    r["value"] = [soc.loc[s] for s in r["start"]]
    print(r.sort_values("rows", ascending=False).head(8).to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("  rows with Running == 0 while |PowerReal| > 50 kW:", int(((allf["Running"] == 0) & (allf["PowerReal"].abs() > 50)).sum()))


def sign(frames):
    print("\n[4 sign]")
    old = pd.concat([frames[y] for y in (2018, 2019, 2020)])
    dsoc = old["AvgSOC"].shift(-1) - old["AvgSOC"]
    ok = (old["PowerReal"].abs() > 50) & dsoc.notna() & (dsoc != 0)
    agree = np.sign(old.loc[ok, "PowerReal"]) == np.sign(dsoc[ok])
    print(f"  2018-2020: minutes with |PowerReal| > 50 kW and SOC moving {int(ok.sum())}; corr(PowerReal, dSOC) {old.loc[ok, 'PowerReal'].corr(dsoc[ok]):.3f}; "
          f"share with sign(PowerReal) == sign(dSOC) {agree.mean():.3f}")
    new = pd.concat([frames[y] for y in (2022, 2023, 2024, 2025)])
    dsoc = new["AvgSOC"].shift(-1) - new["AvgSOC"]
    ok = (new["PowerReal"].abs() > 50) & dsoc.notna() & (dsoc != 0)
    print(f"  2022-2025: corr(PowerReal, dSOC) {new.loc[ok, 'PowerReal'].corr(dsoc[ok]):.3f}; corr(DCCurrent, dSOC) {new.loc[ok, 'DCCurrent'].corr(dsoc[ok]):.3f}; "
          f"corr(PowerReal, DCCurrent) {new.loc[ok, 'PowerReal'].corr(new.loc[ok, 'DCCurrent']):.3f}; "
          f"share sign(PowerReal) == sign(dSOC) {(np.sign(new.loc[ok, 'PowerReal']) == np.sign(dsoc[ok])).mean():.3f}")


def cell_level():
    print("\n[5 cell-level share]")
    files = ppl.cell_level_files()
    print(f"  zips held: {len(files)}, {files['bytes'].sum() / 1e9:.1f} GB, first {files['file'].iloc[0]}, last {files['file'].iloc[-1]}")
    for zname, day in (("20180701-0731.zip", "20180715"), ("20250101_0131.zip", "20250115")):
        if zname not in set(files["file"]):
            print(f"  {zname} not held")
            continue
        members = ppl.cell_level_members(zname)
        kinds = members["member"].str.extract(r"JXB_BSC_([A-Za-z0-9_]+?)_\d{8}")[0].value_counts()
        print(f"  {zname}: {len(members)} members; log types {kinds.to_dict()}")
        rard = [m for m in members["member"] if re.search(rf"RARD_{day}(_\d+)?\.csv$", m, re.I)]
        if not rard:
            print(f"  no RARD log for {day}")
            continue
        frame = ppl.cell_level_preview(zname, rard[0], rows=None)
        if any("Cell Voltage" in str(c) for c in frame.columns):  # one header row ([Module#n]field names)
            names, body = [str(c) for c in frame.columns], frame
        else:  # two header rows: module labels, then field names (returned as the first data row)
            names, body = frame.iloc[0].astype(str).tolist(), frame.iloc[1:]
        n_cellv = sum(1 for n in names if re.sub(r"^\[Module#\d+\]", "", n).startswith("Cell Voltage"))
        n_temp = sum(1 for n in names if re.sub(r"^\[Module#\d+\]", "", n).startswith("Temperature"))
        pairs = body.iloc[:, [2, 3]].astype(int).drop_duplicates()
        times = pd.to_datetime(body.iloc[:, 1])
        per_rack = body.assign(t=times).groupby([body.iloc[:, 2], body.iloc[:, 3]])["t"].apply(lambda s: s.diff().dt.total_seconds().median())
        print(f"  {rard[0]}: rows {len(body)}, columns {len(names)}, cell-voltage columns {n_cellv}, temperature columns {n_temp}, "
              f"(bank, rack) pairs {len(pairs)}, time step between rows {times.diff().dt.total_seconds().median():.0f} s, "
              f"median revisit per rack {per_rack.median():.0f} s, first {times.min()}, last {times.max()}")


if __name__ == "__main__":
    frames = {y: naive(fielddata.load("ppl", years=[y])) for y in range(2017, 2026)}
    grid(frames)
    timezone(frames)
    zeros(frames)
    linear_share(frames)
    sign(frames)
    cell_level()
