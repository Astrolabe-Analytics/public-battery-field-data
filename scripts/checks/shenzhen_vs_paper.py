"""shenzhen_charging against its paper (Yang et al. 2025, Nat Commun, doi:10.1038/s41467-025-67703-7).

What it does, on raw data read through the loader, for both released workbooks (processed_data and
processed_data_longer_than_30):
  - label: is it per session or per row (sessions whose rows mix labels), and how many sessions and rows carry label 1;
  - sessions: distinct transaction_id, distinct (sheet, transaction_id) and rows, against the paper's 21,175 charging
    records with 1,547,432 sampling points;
  - owners: the 8 sheets (sequences, faulty sequences, points, LFP and NMC faults per sheet) and class_judge (the Readme's
    "data owner index", 27 codes) per sheet, sessions, label-1 sessions and fault ratio per owner,
    against the paper's 40, 16, 6 and 50 fault samples for owners 2, 5, 6 and 8 and owner 5's 4,114 sequences at 0.39 %;
  - battery type shares by session and by row, against the paper's LFP 62.02 %, NMC 36.51 %, LMO 1.21 %, LCO 0.19 %,
    LiPo 0.07 %;
  - vehicle hints: columns that could identify a vehicle, the maximum charging voltage per session, and an apparent pack
    energy (total_charging_kwh over the SOC gained, for sessions gaining at least 30 SOC points), grouped by owner and type.
Counts and evidence only. No unit or fault count is changed.

Reads: shenzhen_charging through fielddata.load(..., file=...).
Writes: reports/checks/v12/shenzhen_vs_paper_owners.csv, shenzhen_vs_paper_sheets.csv, shenzhen_vs_paper_types.csv, shenzhen_vs_paper_hints.csv, and
prints the summary.

Run:
    python scripts/checks/shenzhen_vs_paper.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fielddata  # noqa: E402

OUT = ROOT / "reports" / "checks" / "v12"
TYPES = {3: "LFP", 6: "NMC", 4: "LMO", 5: "LCO", 7: "LP"}
FILES = ("processed_data", "processed_data_longer_than_30")


def main() -> int:
    owners, types, hints, sheets = [], [], [], []
    for file in FILES:
        rows = fielddata.load("shenzhen_charging", file=file)
        print(f"\n=== {file}: {len(rows):,} rows; columns {list(rows.columns)}")
        distinct = rows.drop_duplicates(subset=["transaction_id", "id"])
        print(f"distinct (transaction_id, id) rows {len(distinct):,}; distinct transaction_id {rows['transaction_id'].nunique():,}; "
              f"distinct (sheet, transaction_id) {rows[['sheet', 'transaction_id']].drop_duplicates().shape[0]:,}; distinct id {rows['id'].nunique():,}")
        per = rows.groupby("transaction_id")["label"].agg(["min", "max", "size"])
        print(f"label: sessions with label 1 {int((per['max'] == 1).sum()):,}; sessions mixing 0 and 1 {int((per['min'] != per['max']).sum()):,}; "
              f"rows with label 1 {int((rows['label'] == 1).sum()):,} (distinct {int((distinct['label'] == 1).sum()):,})")
        sheet_owner = rows.groupby("sheet")["class_judge"].agg(lambda s: sorted(s.unique().tolist()))
        print("class_judge per sheet:", sheet_owner.to_dict())
        s = rows.groupby("transaction_id").agg(owner=("class_judge", "first"), owners=("class_judge", "nunique"), sheets=("sheet", "nunique"),
                                               type=("types", "first"), label=("label", "max"), points=("id", "nunique"),
                                               vmax=("chargingv", "max"), soc0=("current_soc", "min"), soc1=("current_soc", "max"),
                                               kwh=("total_charging_kwh", "max"), begin=("begin_time", "first"))
        print(f"sessions with more than one owner code {int((s['owners'] > 1).sum())}, in more than one sheet {int((s['sheets'] > 1).sum())}")
        sheet = rows.groupby(["sheet", "transaction_id"]).agg(label=("label", "max"), points=("id", "size"), type=("types", "first")).reset_index()
        sh = sheet.groupby("sheet").agg(sequences=("label", "size"), fault_sequences=("label", "sum"), points=("points", "sum"),
                                         lfp_faults=("label", lambda x: int(x[sheet.loc[x.index, "type"] == 3].sum())),
                                         nmc_faults=("label", lambda x: int(x[sheet.loc[x.index, "type"] == 6].sum())))
        sh["fault_ratio_pct"] = (sh["fault_sequences"] / sh["sequences"] * 100).round(2)
        print("per sheet (the paper's 8 data owners?):")
        print(sh.to_string())
        print(f"all sheets: {int(sh['sequences'].sum()):,} sequences, {int(sh['fault_sequences'].sum()):,} faulty, {int(sh['points'].sum()):,} points")
        sh.insert(0, "file", file)
        sheets.append(sh.reset_index())
        o = s.groupby("owner").agg(sessions=("label", "size"), fault_sessions=("label", "sum"))
        o["fault_ratio_pct"] = (o["fault_sessions"] / o["sessions"] * 100).round(2)
        o.insert(0, "file", file)
        owners.append(o.reset_index())
        print(o.to_string())
        t = pd.DataFrame({"sessions": s["type"].map(TYPES).value_counts(), "rows": distinct["types"].map(TYPES).value_counts()})
        t["sessions_pct"] = (t["sessions"] / t["sessions"].sum() * 100).round(2)
        t["rows_pct"] = (t["rows"] / t["rows"].sum() * 100).round(2)
        t.insert(0, "file", file)
        types.append(t.rename_axis("type").reset_index())
        print(t.to_string())
        # vehicle hints: apparent pack energy for sessions gaining at least 30 SOC points, and the top charging voltage
        g = s[(s["soc1"] - s["soc0"]) >= 30].copy()
        g["pack_kwh"] = g["kwh"] / (g["soc1"] - g["soc0"]) * 100
        g["type"] = g["type"].map(TYPES)
        h = g.groupby(["owner", "type"]).agg(sessions=("pack_kwh", "size"), pack_kwh_median=("pack_kwh", "median"),
                                             pack_kwh_p10=("pack_kwh", lambda x: x.quantile(0.1)), pack_kwh_p90=("pack_kwh", lambda x: x.quantile(0.9)),
                                             distinct_pack_kwh_rounded=("pack_kwh", lambda x: int(np.round(x).nunique())),
                                             vmax_median=("vmax", "median"), distinct_vmax_rounded=("vmax", lambda x: int(np.round(x).nunique())))
        h.insert(0, "file", file)
        hints.append(h.reset_index())
        print(f"sessions gaining >= 30 SOC points: {len(g):,} of {len(s):,}")
        # same-vehicle signature: identical (owner, type, rounded pack kWh, rounded max voltage) across sessions
        key = g.assign(k=np.round(g["pack_kwh"]), v=np.round(g["vmax"])).groupby(["owner", "type", "k", "v"]).size()
        print(f"distinct (owner, type, pack kWh, max V) signatures: {len(key):,}; signatures shared by 2 or more sessions: {int((key > 1).sum()):,}, "
              f"covering {int(key[key > 1].sum()):,} sessions")
    pd.concat(owners).to_csv(OUT / "shenzhen_vs_paper_owners.csv", index=False, lineterminator="\n")
    pd.concat(sheets).to_csv(OUT / "shenzhen_vs_paper_sheets.csv", index=False, lineterminator="\n")
    pd.concat(types).to_csv(OUT / "shenzhen_vs_paper_types.csv", index=False, lineterminator="\n")
    pd.concat(hints).round(3).to_csv(OUT / "shenzhen_vs_paper_hints.csv", index=False, lineterminator="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
