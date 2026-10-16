"""Does any pnnl_epri system duplicate the ppl or m5bat releases? (raw data, through the loaders)

What it does: the pnnl_epri files carry elapsed hours, not dates, so a shared system can only be found by its
operating pattern. For each pnnl_epri system with a system-level SOC series, the script builds an hourly SOC series
on its own timeline and slides it along the hourly SOC series of
  - ppl (E.W. Brown BESS, AvgSOC, 2017-11 to 2026-02, 1 min), and
  - m5bat-2023-04 (the ten battery units' SOC, April 2023, 1 s),
recording the best Pearson correlation over all offsets with at least 30 days (ppl) or 7 days (m5bat) of overlap,
the offset it occurs at, and the overlap length. A shared system would give r close to 1 at one offset; unrelated
systems with daily cycling give r well below that. It also records each system's span and row spacing beside the
ppl and m5bat ones.
Reads: the pnnl_epri .feather files, ppl ESS_*.csv, m5bat-2023-04 M5BAT_04-2023_RAW.zip (through fielddata.load).
Then, for every pnnl_epri system whose best ppl match has r of at least 0.6, it aligns the two at that offset on a 5 min
grid and records the correlation of SOC levels, of 5 min SOC changes, the median absolute SOC difference, and the
correlation of cell voltage (ppl CellVoltAvg against the pnnl_epri system meter's VoltageAvg, else Voltage).
Writes: reports/candidates/pnnl_epri/pnnl_epri_overlap.csv (one row per pnnl_epri system and comparison; rows already
recorded are skipped) and reports/candidates/pnnl_epri/pnnl_epri_overlap_confirm.csv.
Rerun: python scripts/checks/pnnl_epri_overlap.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import fielddata  # noqa: E402
from fielddata.loaders import pnnl_epri  # noqa: E402

OUT = ROOT / "reports" / "candidates" / "pnnl_epri" / "pnnl_epri_overlap.csv"
SYSTEM_METERS = ["PGCP", "PDC", "PFDR", "PAC"]


def pnnl_soc(unit: str) -> pd.Series | None:
    """Hourly SOC (fraction) of one system: the system-level meter if it has SOC, else the mean over meters."""
    frame = pnnl_epri.load(unit=unit, columns=["SOC"])
    frame = frame[frame["SOC"].notna()]
    if frame.empty:
        return None
    for m in SYSTEM_METERS:
        if (frame["Meter"] == m).any():
            frame = frame[frame["Meter"] == m]
            break
    hours = np.floor(frame["HoursElapsed"]).astype(int)
    return frame.groupby(hours)["SOC"].mean()


def ppl_soc() -> pd.Series:
    frame = fielddata.load("ppl", clean=True)
    soc = frame["AvgSOC"].dropna() / 100
    soc = soc[soc > 0]
    return soc.resample("1h").mean()


def m5bat_soc() -> dict[str, pd.Series]:
    out = {}
    for unit in [f"Batt{i}" for i in range(1, 11)]:
        frame = fielddata.load("m5bat-2023-04", unit=unit)
        out[unit] = (frame["SOC"] / 1000).resample("1h").mean()  # SOC released in 0.1 %
    return out


def _xcorr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """sum over i of a[i] * b[i + k] for every lag k = -(len(a)-1) .. len(b)-1, via FFT."""
    n = len(a) + len(b) - 1
    size = 1 << (n - 1).bit_length()
    out = np.fft.irfft(np.fft.rfft(a[::-1], size) * np.fft.rfft(b, size), size)[:n]
    return out


def best_match(a: pd.Series, b: pd.Series, min_overlap_h: int) -> tuple[float, int, int]:
    """Best Pearson r of hourly series a (elapsed hours) against b (calendar hours) over all integer offsets, with
    missing hours left out of each overlap (masked cross-correlation). offset k: a's hour 0 sits at b's hour k."""
    av = np.full(int(a.index.max()) + 1, np.nan)
    av[a.index.to_numpy().astype(int)] = a.to_numpy()
    bv = b.to_numpy(dtype=float)
    ma, mb = ~np.isnan(av), ~np.isnan(bv)
    x, y = np.where(ma, av, 0.0), np.where(mb, bv, 0.0)
    n = _xcorr(ma.astype(float), mb.astype(float))
    sx, sy = _xcorr(x, mb.astype(float)), _xcorr(ma.astype(float), y)
    sxx, syy = _xcorr(x * x, mb.astype(float)), _xcorr(ma.astype(float), y * y)
    sxy = _xcorr(x, y)
    n = np.rint(n)
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = sxy - sx * sy / n
        var = (sxx - sx * sx / n) * (syy - sy * sy / n)
        r = cov / np.sqrt(var)
    r[(n < min_overlap_h) | ~(var > 1e-9)] = np.nan
    if np.all(np.isnan(r)):
        return np.nan, 0, 0
    k = int(np.nanargmax(r))
    return float(r[k]), k - (len(av) - 1), int(n[k])


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        done = {(r["unit"], r["against"]) for r in pd.read_csv(OUT).to_dict("records")}
    ppl, m5 = None, None
    for unit in pnnl_epri.SYSTEMS:
        if not (pnnl_epri.directory("pnnl_epri") / f"{unit}.feather").exists():
            print(f"{unit}: not downloaded yet, skipped")
            continue
        targets = ["ppl"] + [f"m5bat-2023-04 Batt{i}" for i in range(1, 11)]
        if all((unit, t) in done for t in targets):
            continue
        soc = pnnl_soc(unit)
        rows = []
        for target in targets:
            if (unit, target) in done:
                continue
            if soc is None:
                rows.append({"unit": unit, "against": target, "best_r": np.nan, "offset_h": "", "overlap_h": 0,
                             "note": "no SOC in release"})
                continue
            if target == "ppl":
                ppl = ppl_soc() if ppl is None else ppl
                b, start, min_h = ppl, ppl.index[0], 24 * 30
            else:
                m5 = m5bat_soc() if m5 is None else m5
                b = m5[target.split()[-1]]
                start, min_h = b.index[0], 24 * 7
            r, offset, n = best_match(soc, b, min_h)
            rows.append({"unit": unit, "against": target, "best_r": r, "offset_h": offset, "overlap_h": n,
                         "note": f"pnnl hour 0 at {start + pd.Timedelta(hours=offset)} of the other clock" if not np.isnan(r) else "no overlap"})
        new = not OUT.exists()
        with OUT.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["unit", "against", "best_r", "offset_h", "overlap_h", "note"],
                                    lineterminator="\n")
            if new:
                writer.writeheader()
            writer.writerows(rows)
        for row in rows:
            print(f"{unit} vs {row['against']}: best r {row['best_r']:.3f} over {row['overlap_h']} h" if row["overlap_h"] else f"{unit} vs {row['against']}: {row['note']}")

CONFIRM = OUT.parent / "pnnl_epri_overlap_confirm.csv"


def confirm() -> None:
    """Five-minute comparison at the best ppl offset for systems with best r >= 0.6."""
    best = pd.read_csv(OUT)
    best = best[(best["against"] == "ppl") & (best["best_r"] >= 0.6)]
    if best.empty:
        return
    ppl = fielddata.load("ppl", clean=True)[["AvgSOC", "CellVoltAvg"]]
    ppl = ppl.resample("5min").mean()
    rows = []
    for r in best.itertuples():
        start = ppl.index[0].floor("h") + pd.Timedelta(hours=int(r.offset_h))
        frame = pnnl_epri.load(unit=r.unit, columns=["SOC", "Voltage", "VoltageAvg"])
        meter = next((m for m in SYSTEM_METERS if (frame["Meter"] == m).any() and frame.loc[frame["Meter"] == m, "SOC"].notna().any()), None)
        x = frame[frame["Meter"] == meter].copy() if meter else frame.groupby("HoursElapsed", as_index=False)[["SOC", "Voltage", "VoltageAvg"]].mean()
        x.index = (start + pd.to_timedelta(x["HoursElapsed"], unit="h")).dt.round("5min")
        x = x.groupby(level=0)[["SOC", "Voltage", "VoltageAvg"]].mean()
        j = x.join(ppl, how="inner")
        j = j[(j["AvgSOC"] > 0) & j["SOC"].notna()]
        soc_a, soc_b = j["SOC"], j["AvgSOC"] / 100
        d_a, d_b = soc_a.diff(), soc_b.diff()
        ok = d_a.notna() & d_b.notna() & ((d_a != 0) | (d_b != 0))
        volt = j["VoltageAvg"] if j["VoltageAvg"].notna().sum() > 1000 else j["Voltage"]
        v_ok = volt.notna() & j["CellVoltAvg"].gt(0)
        rows.append({"unit": r.unit, "meter": meter, "offset_h": int(r.offset_h), "pnnl_hour0_on_ppl_clock": str(start),
                     "rows_5min": len(j), "r_soc": soc_a.corr(soc_b), "r_dsoc_5min": d_a[ok].corr(d_b[ok]),
                     "median_abs_soc_diff": float((soc_a - soc_b).abs().median()),
                     "r_cell_voltage": volt[v_ok].corr(j.loc[v_ok, "CellVoltAvg"]), "voltage_rows": int(v_ok.sum()),
                     "median_abs_cell_voltage_diff_V": float((volt[v_ok] - j.loc[v_ok, "CellVoltAvg"]).abs().median())})
        print(rows[-1])
    pd.DataFrame(rows).to_csv(CONFIRM, index=False, lineterminator="\n")


if __name__ == "__main__":
    main()
    confirm()
