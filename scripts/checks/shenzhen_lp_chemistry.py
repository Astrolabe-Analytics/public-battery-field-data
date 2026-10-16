"""shenzhen_charging: is battery type code 07 ("LP" in Readme.txt) LFP? Evidence from charging-voltage shape.

What it does: reads every charging session of processed_data.xlsx through fielddata.loaders.shenzhen_charging (Sheet7's
repeats of Sheet1 counted once) and, per session, takes the charger's voltage (chargingv) against SOC (current_soc).
The pack's series cell count is not released, so absolute voltage cannot be compared across packs. Each session's
voltage is divided by its own voltage at 55 percent SOC (median of the samples at 54 to 56 percent), so curves are
compared by shape only. Per session it computes, on raw data:
  - mid-SOC slope: (V at 80 percent - V at 30 percent) / V at 55 percent / 50, in percent of V55 per SOC point;
    LFP's plateau gives a small slope, LCO and NMC a steady rise;
  - plateau spread: (max - min) of normalised voltage between 30 and 80 percent SOC;
  - end-of-charge step: (V at 98 to 100 percent - V at 90 percent) / V at 55 percent; LFP rises sharply at the top.
Sessions need samples at 28 to 32, 54 to 56 and 78 to 82 percent SOC; the end step also needs 89 to 91 and 98 to 100.
It compares the distributions per type code (03 LFP, 06 NMC, 04 LMO, 05 LCO, 07 LP) and plots the median normalised
curve per code with its interquartile band, and the mid-SOC slope per code.

Reads: shenzhen_charging through its loader.
Writes: reports/checks/v12/shenzhen_lp_sessions.csv (one row per qualifying session), shenzhen_lp_summary.csv,
shenzhen_lp_curves.csv (the plotted medians and quartiles) and shenzhen_lp_curves.png; with --wide,
shenzhen_lp_wide.csv (the plotted slopes), shenzhen_lp_wide_summary.csv and shenzhen_lp_slopes.png.

Run:
    python scripts/checks/shenzhen_lp_chemistry.py           # the 30/55/80 percent test and the plots
    python scripts/checks/shenzhen_lp_chemistry.py --wide    # fitted slope over any 20-point span (more LP sessions)
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fielddata  # noqa: E402

OUT = ROOT / "reports" / "checks" / "v12"
NAMES = {3: "03 LFP", 6: "06 NMC", 4: "04 LMO", 5: "05 LCO", 7: "07 LP"}
BINS = np.arange(10, 101, 5)


def window(frame, lo, hi):
    part = frame[(frame["current_soc"] >= lo) & (frame["current_soc"] <= hi)]["chargingv"]
    return float(part.median()) if len(part) else np.nan


def main() -> int:
    rows = fielddata.load("shenzhen_charging")
    rows = rows.drop_duplicates(subset=["transaction_id", "id"])  # Sheet7 repeats Sheet1
    sessions, curves = [], []
    for tid, s in rows.groupby("transaction_id", sort=False):
        s = s[(s["chargingv"] > 0) & s["current_soc"].between(0, 100)]
        v55 = window(s, 54, 56)
        v30, v80 = window(s, 28, 32), window(s, 78, 82)
        if not (np.isfinite(v55) and np.isfinite(v30) and np.isfinite(v80)) or v55 <= 0:
            continue
        mid = s[s["current_soc"].between(30, 80)]["chargingv"] / v55
        v90, vtop = window(s, 89, 91), window(s, 98, 100)
        code = int(s["types"].iloc[0])
        sessions.append({"transaction_id": tid, "code": code, "type": NAMES.get(code, str(code)), "rows": len(s),
                         "mid_slope_pct_per_soc": (v80 - v30) / v55 / 50 * 100,
                         "plateau_spread": float(mid.max() - mid.min()),
                         "end_step": (vtop - v90) / v55 if np.isfinite(v90) and np.isfinite(vtop) else np.nan})
        binned = s.assign(bin=pd.cut(s["current_soc"], BINS, labels=BINS[:-1] + 2.5)).groupby("bin", observed=True)["chargingv"].median() / v55
        curves.append(binned.rename(tid).to_frame().T.assign(code=code))
    table = pd.DataFrame(sessions)
    table.to_csv(OUT / "shenzhen_lp_sessions.csv", index=False, lineterminator="\n")
    summary = table.groupby("type").agg(sessions=("transaction_id", "size"),
                                        mid_slope_median=("mid_slope_pct_per_soc", "median"),
                                        mid_slope_q25=("mid_slope_pct_per_soc", lambda x: x.quantile(0.25)),
                                        mid_slope_q75=("mid_slope_pct_per_soc", lambda x: x.quantile(0.75)),
                                        plateau_spread_median=("plateau_spread", "median"),
                                        end_step_median=("end_step", "median"),
                                        end_step_sessions=("end_step", "count"))
    summary.to_csv(OUT / "shenzhen_lp_summary.csv", lineterminator="\n")
    print(summary.to_string())

    curve = pd.concat(curves)
    out_rows = []
    fig, ax = plt.subplots(figsize=(7, 4))
    for code, part in curve.groupby("code"):
        values = part.drop(columns="code")
        med, q1, q3 = values.median(), values.quantile(0.25), values.quantile(0.75)
        x = np.asarray(med.index, dtype=float)
        ax.plot(x, med.values, label=f"{NAMES.get(code, code)} (n={len(values)})")
        ax.fill_between(x, q1.values, q3.values, alpha=0.15)
        for soc, m, a, b in zip(x, med.values, q1.values, q3.values):
            out_rows.append({"type": NAMES.get(code, code), "soc_bin_mid": soc, "median": m, "q25": a, "q75": b, "sessions": len(values)})
    ax.set_xlabel("SOC (%)")
    ax.set_ylabel("charging voltage / voltage at 55 % SOC")
    ax.set_title("Shenzhen charging sessions: voltage shape by battery type code")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "shenzhen_lp_curves.png", dpi=120)
    pd.DataFrame(out_rows).to_csv(OUT / "shenzhen_lp_curves.csv", index=False, lineterminator="\n")

    return 0


if __name__ == "__main__" and "--wide" not in sys.argv:
    raise SystemExit(main())


def wide_slopes() -> pd.DataFrame:
    """A wider test for codes with few sessions: per session with at least a 20-point SOC span inside 20 to 90 percent,
    the least-squares slope of V/V(median over that span) against SOC, in percent per SOC point. Same for every code."""
    rows = fielddata.load("shenzhen_charging").drop_duplicates(subset=["transaction_id", "id"])
    out = []
    for tid, s in rows.groupby("transaction_id", sort=False):
        s = s[(s["chargingv"] > 0) & s["current_soc"].between(20, 90)]
        if len(s) < 5 or s["current_soc"].max() - s["current_soc"].min() < 20:
            continue
        v = s["chargingv"] / s["chargingv"].median()
        slope = np.polyfit(s["current_soc"].astype(float), v.astype(float), 1)[0] * 100
        out.append({"transaction_id": tid, "type": NAMES.get(int(s["types"].iloc[0])), "soc_span": int(s["current_soc"].max() - s["current_soc"].min()),
                    "fit_slope_pct_per_soc": slope})
    table = pd.DataFrame(out)
    table.to_csv(OUT / "shenzhen_lp_wide.csv", index=False, lineterminator="\n")
    summary = table.groupby("type")["fit_slope_pct_per_soc"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9])
    summary.to_csv(OUT / "shenzhen_lp_wide_summary.csv", lineterminator="\n")
    print(summary.to_string())
    lp = table[table["type"] == "07 LP"]["fit_slope_pct_per_soc"]
    lfp = table[table["type"] == "03 LFP"]["fit_slope_pct_per_soc"]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    order = [n for n in NAMES.values() if n in set(table["type"])]
    ax.boxplot([table.loc[table["type"] == n, "fit_slope_pct_per_soc"] for n in order], showfliers=False)
    ax.set_xticks(range(1, len(order) + 1), [f"{n}\n(n={int((table['type'] == n).sum())})" for n in order])
    ax.set_ylabel("voltage slope, 20 to 90 % SOC\n(% of median voltage per SOC point)")
    ax.set_title("Charging-voltage slope by battery type code")
    fig.tight_layout()
    fig.savefig(OUT / "shenzhen_lp_slopes.png", dpi=120)
    print(f"LP sessions below the LFP 90th percentile ({lfp.quantile(0.9):.3f}): {int((lp < lfp.quantile(0.9)).sum())} of {len(lp)}")
    return table


if __name__ == "__main__" and "--wide" in sys.argv:
    wide_slopes()
