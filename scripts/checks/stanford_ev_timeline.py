"""stanford_ev: does the field record show the same pack after January 2024?

Why: the companion paper (Marini et al. 2026, OJPEL, doi:10.1109/OJPEL.2026.3691252, p. 1716) says its Audi e-tron was
driven from September 2021 through January 2024 and its pack then taken apart, while this release's field sessions run
to April 2025. If the release is that car and the pack was removed, the later sessions would be from another pack.

What it does, on raw data through the loader (a sample is enough, so it reads about 110 of the 5,416 files):
  1. sessions per month, by kind, and gaps over 14 days between sessions;
  2. Mileage_bms of the first session of each month and of the 10 sessions either side of 2024-01-01: steps and any reset;
  3. a pack fingerprint for 25 charging sessions spread evenly before 2024-01-01 and 25 after: each of the 108 series
     cells' median offset from the pack's mean cell voltage over the session (mV). A pack keeps its pattern of weak and
     strong cells, so sessions from the same pack correlate with each other; a different pack would not. The baseline
     is the early pre-2024 sample against the late pre-2024 sample.

Reads: stanford_ev through fielddata.loaders.stanford_ev (sessions, mileage, V_cell_bms).
Writes: reports/checks/v12/stanford_ev_timeline_sessions.csv (one row per sampled charging session: r with the pre-2024 mean, spread in mV) and
stanford_ev_timeline_months.csv, and prints the summary.

Run:
    python scripts/checks/stanford_ev_timeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata.loaders import stanford_ev  # noqa: E402

OUT = ROOT / "reports" / "checks" / "v12"
CUT = pd.Timestamp("2024-01-01")


def fingerprint(session: str) -> np.ndarray | None:
    v = stanford_ev.load(session, "V_cell_bms")
    cells = v[[c for c in v.columns if c.startswith("V_cell_bms_")]].to_numpy(float)
    if cells.shape[0] < 10 or cells.shape[1] != 108:
        return None
    ok = (cells > 2.5).all(axis=1) & (cells < 4.5).all(axis=1)
    cells = cells[ok]
    if len(cells) < 10:
        return None
    return np.median(cells - cells.mean(axis=1, keepdims=True), axis=0) * 1000


def main() -> int:
    s = stanford_ev.sessions()
    s["month"] = s["start"].dt.to_period("M").astype(str)
    months = s.pivot_table(index="month", columns="kind", values="session", aggfunc="count", fill_value=0)
    months.to_csv(OUT / "stanford_ev_timeline_months.csv", lineterminator="\n")
    print(months.loc["2023-09":"2024-06"].to_string())

    gaps = s["start"].diff()
    big = s.loc[gaps > pd.Timedelta(days=14), ["start"]].assign(gap_days=gaps[gaps > pd.Timedelta(days=14)].dt.days)
    print("\ngaps over 14 days between sessions:"); print(big.to_string(index=False) if len(big) else "none")

    # mileage on a sample: the first session of each month, and the 10 sessions either side of the cut
    pick = set(s.groupby("month")["session"].first())
    i = int((s["start"] < CUT).sum())
    pick |= set(s["session"].iloc[max(i - 10, 0):i + 10])
    m = s[s["session"].isin(pick)].copy()
    m["mileage"] = pd.to_numeric([stanford_ev.mileage(x) for x in m["session"]])
    print(f"\nmileage sample: {len(m)} sessions, {int(m['mileage'].isna().sum())} NaN as released")
    mm = m.dropna(subset=["mileage"])
    steps = mm["mileage"].diff()
    print(f"mileage {mm['mileage'].iloc[0]:.0f} to {mm['mileage'].iloc[-1]:.0f}; decreases {int((steps < 0).sum())}")
    print(m[(m["start"] >= "2023-12-15") & (m["start"] < "2024-02-15")][["start", "kind", "mileage"]].to_string(index=False))
    print(m.groupby("month")["mileage"].first().to_string())

    # pack fingerprint on a sample: 25 charging sessions evenly spread before the cut and 25 after
    c = s[s["kind"] == "Charging"]
    early, late = c[c["start"] < CUT], c[c["start"] >= CUT]
    take = lambda d: d.iloc[np.linspace(0, len(d) - 1, min(25, len(d))).round().astype(int)]
    fps = {x: f for x in pd.concat([take(early), take(late)])["session"] if (f := fingerprint(x)) is not None}
    starts = s.set_index("session")["start"]
    pre = [x for x in fps if starts[x] < CUT]
    post = [x for x in fps if starts[x] >= CUT]
    half = len(pre) // 2
    r = lambda a, b: np.corrcoef(np.mean([fps[x] for x in a], axis=0), np.mean([fps[x] for x in b], axis=0))[0, 1]
    print(f"\nfingerprints: {len(pre)} before, {len(post)} after")
    print(f"baseline, early pre-2024 vs late pre-2024 mean: r = {r(pre[:half], pre[half:]):.3f}")
    print(f"late pre-2024 vs post-2024 mean: r = {r(pre[half:], post):.3f}")
    print(f"all pre-2024 vs post-2024 mean: r = {r(pre, post):.3f}")
    ref = np.mean([fps[x] for x in pre], axis=0)
    rows = [{"session": x, "start": starts[x], "r_with_pre_mean": np.corrcoef(fps[x], ref)[0, 1],
             "spread_mv": fps[x].max() - fps[x].min()} for x in fps]
    out = pd.DataFrame(rows).sort_values("start")
    out.to_csv(OUT / "stanford_ev_timeline_sessions.csv", index=False, lineterminator="\n")
    print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
