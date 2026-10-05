"""Audit data checks for bilfinger2024 and bilfinger2026 (source audit 2026-10-04).

Reads every vehicle recording through the loaders (raw, clean=False) and prints, per file:
sampling (time step statistics, share of rows that lie on a straight line with their neighbours),
voltage quantization (share of U on the 0.25 V grid), the current sign while U rises,
Q against the trapezoid integral of I over time_h, date range, and charged energy/charge between
the authors' fixed voltage bounds (VW 370-450 V, Tesla 340-380 V, as in the authors' ReadFeather).
Writes nothing; output is printed (redirected to checks_out.txt in the scratch folder).
"""
import numpy as np
import pandas as pd


def ctz(y, x, initial=0):
    """Cumulative trapezoid integral (same as scipy cumulative_trapezoid with initial=0)."""
    y = np.asarray(y, float); x = np.asarray(x, float)
    return np.concatenate([[initial], initial + np.cumsum((y[1:] + y[:-1]) / 2 * np.diff(x))])

from fielddata.loaders import bilfinger2024 as A, bilfinger2026 as B


def linear_share(t, y, tol):
    """Share of interior rows whose value equals the straight line through both neighbours (within tol)."""
    t = np.asarray(t, float); y = np.asarray(y, float)
    ok = np.isfinite(y)
    t, y = t[ok], y[ok]
    if len(y) < 3:
        return np.nan
    pred = y[:-2] + (y[2:] - y[:-2]) * (t[1:-1] - t[:-2]) / np.where(t[2:] - t[:-2] == 0, np.nan, t[2:] - t[:-2])
    return float(np.nanmean(np.abs(y[1:-1] - pred) < tol))


def window_eval(d, lo, hi):
    """Authors' method (ReadPickle.extract_between_voltages + calc_E_from_I): rows with lo<=U<=hi, E and Q reset at first row."""
    E = ctz(d["I"] * d["U"] / 1000, d["time_h"], initial=0)
    sel = (d["U"] >= lo) & (d["U"] <= hi)
    if sel.sum() == 0:
        return np.nan, np.nan
    e = E[sel.values]; q = d["Q"].values[sel.values]
    return float(np.max(e - e[0])), float(np.max(q - q[0]))


def per_file(mod, rel):
    rows = []
    for r in mod.systems().itertuples():
        if not r.kind.startswith("vehicle"):
            continue
        d = mod.load(r.unit)
        out = {"release": rel, "unit": r.unit, "kind": r.kind, "rows": len(d)}
        if r.kind == "vehicle raw log":
            tcol = "TIMESTAMP" if "TIMESTAMP" in d else "time"
            dt = np.diff(d[tcol].astype(float).values)
            out.update(dt_median=float(np.median(dt)), dt_p05=float(np.percentile(dt, 5)), dt_p95=float(np.percentile(dt, 95)),
                       U_lin=linear_share(d[tcol], d["hv_battery_voltage"], 1e-6),
                       U_grid025=float(np.mean(np.isclose((d["hv_battery_voltage"].dropna() * 4) % 1, 0, atol=1e-6) | np.isclose((d["hv_battery_voltage"].dropna() * 4) % 1, 1, atol=1e-6))))
            if tcol == "time":
                out["start_utc"] = str(pd.to_datetime(d["time"].min(), unit="s"))
                out["end_utc"] = str(pd.to_datetime(d["time"].max(), unit="s"))
            rows.append(out); continue
        t = d["time_s"].astype(float).values
        dt = np.diff(t)
        U = d["U"].astype(float); I = d["I"].astype(float)
        out.update(dt_median=float(np.median(dt)), dt_p05=float(np.percentile(dt, 5)), dt_p95=float(np.percentile(dt, 95)),
                   dt_const=float(np.mean(np.isclose(dt, np.median(dt), atol=1e-6))),
                   U_lin=linear_share(t, U, 1e-6), U_repeat=float(np.mean(np.diff(U.values) == 0)),
                   U_grid025=float(np.mean(np.isclose((U * 4) % 1, 0, atol=1e-6) | np.isclose((U * 4) % 1, 1, atol=1e-6))),
                   I_pos=float(np.mean(I > 0)), I_neg=float(np.mean(I < 0)), I_min=float(I.min()), I_max=float(I.max()),
                   U_first=float(U.iloc[0]), U_last=float(U.iloc[-1]), U_min=float(U.min()), U_max=float(U.max()))
        # sign of I while U rises: median I over rows where a 1 % window shows U rising by more than 1 V
        w = max(3, len(U) // 100)
        dU = U.shift(-w) - U
        rising = dU > 1.0; falling = dU < -1.0
        out["I_med_rising"] = float(I[rising].median()) if rising.any() else np.nan
        out["I_med_falling"] = float(I[falling].median()) if falling.any() else np.nan
        # Q against the integral of I
        qi = ctz(I, d["time_h"].astype(float), initial=0)
        res = d["Q"].values - qi
        out.update(Q_end=float(d["Q"].iloc[-1]), Qint_end=float(qi[-1]), Q_res_maxabs=float(np.nanmax(np.abs(res - res[0]))), Q_res0=float(res[0]))
        # moving-mean test (authors' 1 % forward filter): residual of Q against a filtered integral
        win = int(np.ceil(0.01 * len(d)) // 2 * 2 + 1)
        qf = pd.Series(qi).rolling(win, min_periods=1).mean().values
        out["Q_res_vs_filtered_maxabs"] = float(np.nanmax(np.abs(d["Q"].values - qf - (d["Q"].values[0] - qf[0]))))
        if "date" in d:
            out["date_min"] = str(d["date"].min()); out["date_max"] = str(d["date"].max())
        lo, hi = (340, 380) if r.unit.startswith("Tesla") else (370, 450)
        out["E_kWh_window"], out["Q_Ah_window"] = window_eval(d, lo, hi)
        if "cell_voltage_0" in d or "cell_voltage_1" in d:
            c = "cell_voltage_0" if "cell_voltage_0" in d else "cell_voltage_1"
            out["cellV_lin"] = linear_share(t, d[c], 1e-6)
            out["cellV_repeat"] = float(np.mean(np.diff(d[c].values) == 0))
        rows.append(out)
    return rows


if __name__ == "__main__":
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60); pd.set_option("display.max_rows", 200)
    frame = pd.DataFrame(per_file(A, "bilfinger2024") + per_file(B, "bilfinger2026"))
    for col in frame.columns:
        if col in ("release", "unit", "kind"):
            continue
        print("\n##", col)
        print(frame[["release", "unit", col]].to_string(index=False))
    frame.to_csv(__file__.replace("checks.py", "checks_out.csv"), index=False)
