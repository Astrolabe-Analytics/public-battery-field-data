"""Check every release's quick-start loader and save a small preview for the dashboard.

What it does: for each release in the registry, runs fielddata.quickstart.sample() (one unit, a small slice) and
records whether it worked, how many rows and which columns came back, and the error text if it failed.
For every release it also draws the quick-start signal with
fielddata.quickstart.plot(), restyles it (DejaVu Sans, one highlighted series, a short title stating the
range, no legend) and saves the PNG plus the plotted points as a CSV. Long slices are thinned to at most 4,000 evenly spaced points for
the picture and the CSV; the title's range is taken over the whole slice. For releases under non-commercial terms or
with no stated license, the record also carries the release's license, which the dashboard prints under the preview
(decided by the maintainer 2026-10-02: this repository is non-commercial use, and previews of all releases are published).

Reads: the released files on the configured data root, only through the fielddata loaders.
Writes: docs/dashboard/status.json, docs/dashboard/img/<release>.png and docs/dashboard/img/<release>.csv.
Results are saved after each release; a rerun skips releases already recorded unless --force is given.

Run:
    python scripts/dashboard_status.py [release ...] [--force]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fielddata import quickstart
from fielddata.config import public_text as _public_text
from fielddata.registry import PACKAGES

OUT = ROOT / "docs" / "dashboard"
STATUS = OUT / "status.json"
IMG = OUT / "img"
ACCENT, MUTED = "#1f6feb", "#6e7781"
MAX_POINTS = 4000


def _style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": MUTED, "axes.labelcolor": "#24292f", "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
    })


def _preview(package: str, frame: pd.DataFrame, basis: str) -> dict:
    _style()
    fig, ax = plt.subplots(figsize=(6.4, 2.6), dpi=110)
    quickstart.plot(package, frame, ax=ax)
    line = ax.get_lines()[0]
    line.set(color=ACCENT, linewidth=1.0)
    for other in ax.get_lines()[1:]:
        other.set(color=MUTED, alpha=0.4)
    x, y = line.get_xdata(orig=True), np.asarray(line.get_ydata(orig=True), dtype=float)
    finite = y[np.isfinite(y)]
    signal = quickstart.PLOT[package][0]
    title = f"{signal} stays between {finite.min():.4g} and {finite.max():.4g} ({basis} data)" if finite.size else f"{signal}: no finite values in this slice"
    ax.set_title(title)
    step = max(1, -(-len(y) // MAX_POINTS))  # thin long slices so the PNG and its CSV stay small
    x, y = x[::step], y[::step]
    line.set_data(x, y)
    if pd.api.types.is_datetime64_any_dtype(pd.Series(x)):
        import matplotlib.dates as mdates
        locator = mdates.AutoDateLocator(maxticks=6)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    else:
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(6))
    if ax.get_legend():
        ax.get_legend().remove()
    fig.tight_layout()
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / f"{package}.png")
    plt.close(fig)
    pd.DataFrame({ax.get_xlabel() or "x": x, signal: y}).to_csv(IMG / f"{package}.csv", index=False, lineterminator="\n")
    return {"preview": f"img/{package}.png", "preview_data": f"img/{package}.csv", "preview_title": title,
            "preview_points": int(len(y)), "preview_step": int(step)}


def check(package: str) -> dict:
    args = quickstart.example_args(package)
    record = {"date": dt.date.today().isoformat(), "load_args": {k: v for k, v in args.items()}}
    try:
        frame = quickstart.sample(package)
        record.update(status="ok", rows=int(len(frame)), columns=[str(c) for c in frame.columns])
    except Exception as error:
        detail = traceback.format_exception_only(type(error), error)[-1].strip()
        record.update(status="failed", error=_public_text(detail))
        return record
    try:
        record.update(_preview(package, frame, "cleaned" if args.get("clean") else "raw"))
    except Exception as error:
        record["preview_error"] = _public_text(traceback.format_exception_only(type(error), error)[-1].strip())
    if PACKAGES[package].get("derived_outputs") != "may publish":
        record["preview_license"] = PACKAGES[package]["license"]
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packages", nargs="*")
    parser.add_argument("--force", action="store_true")
    options = parser.parse_args()
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    for package in options.packages or sorted(quickstart.EXAMPLES):
        if package in status and not options.force and not options.packages:
            continue
        print(f"{package}: ", end="", flush=True)
        status[package] = check(package)
        row = status[package]
        print(row["status"], row.get("rows", row.get("error", "")), flush=True)
        OUT.mkdir(parents=True, exist_ok=True)
        STATUS.write_text(json.dumps(dict(sorted(status.items())), indent=1, default=str) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
