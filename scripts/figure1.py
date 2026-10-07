"""Figure 1: releases in the collection by the year they first appeared, stacked by application.

Inputs: docs/descriptor/figure1_releases.csv (year and its source, per package) and fielddata/package_facts.csv
(application class). Outputs: docs/descriptor/figures/figure1_release_timeline.{png,pdf} and
figure1_release_timeline_data.csv (the plotted rows: package, year_first_appeared, application).

Design (the v1.1 paper's figure): one stacked bar per year from the first year to the last, one segment per
release, colored by application with the Okabe-Ito palette and marked with a white symbol so classes stay apart
in grayscale; the count above each bar; a legend on the right; "to Oct." under the current, partial year;
DejaVu Sans; no title (the caption carries it). 13 x 3.3 in at 220 dpi. A release with units in more than one
class ("passenger EV, bus") is placed by its first class.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
YEARS = ROOT / "docs" / "descriptor" / "figure1_releases.csv"
FACTS = ROOT / "fielddata" / "package_facts.csv"
OUT = ROOT / "docs" / "descriptor" / "figures"
PARTIAL_YEAR, PARTIAL_NOTE = 2026, "to Oct."
# application class: (legend label, Okabe-Ito color, white marker), in stacking and legend order
CLASSES = {
    "passenger EV": ("Passenger EV", "#0072B2", "o"),
    "bus": ("Bus", "#D55E00", "s"),
    "light electric mobility": ("Light electric mobility", "#009E73", "^"),
    "grid-scale storage": ("Grid-scale storage", "#E69F00", "D"),
    "distributed storage": ("Distributed storage", "#CC79A7", "v"),
    "consumer electronics": ("Consumer electronics", "#56B4E9", "h"),
    "industrial and robotics": ("Industrial and robotics", "#000000", "P"),
}
INK, GRID, MUTED = "#000000", "#dddddd", "#555555"


def rows() -> list[dict]:
    application = {r["package"]: r["value"].split(",")[0].strip()
                   for r in csv.DictReader(FACTS.open(encoding="utf-8")) if r["field"] == "application"}
    years = {r["package"]: int(r["year"]) for r in csv.DictReader(YEARS.open(encoding="utf-8"))}
    missing = sorted(set(application) - set(years))
    if missing:
        raise SystemExit(f"no year for: {missing}")
    order = list(CLASSES)
    plotted = [{"package": p, "year_first_appeared": years[p], "application": CLASSES[application[p]][0]} for p in application]
    plotted.sort(key=lambda r: (r["year_first_appeared"], order.index(next(k for k, v in CLASSES.items() if v[0] == r["application"])), r["package"]))
    return plotted


def main() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    plotted = rows()
    label_to_key = {v[0]: k for k, v in CLASSES.items()}
    first, last = min(r["year_first_appeared"] for r in plotted), max(r["year_first_appeared"] for r in plotted)
    years = list(range(first, last + 1))
    fig, ax = plt.subplots(figsize=(13.0, 3.3), dpi=220)
    width = 0.62
    for year in years:
        stack = [r for r in plotted if r["year_first_appeared"] == year]
        for level, r in enumerate(stack):
            _, color, marker = CLASSES[label_to_key[r["application"]]]
            ax.bar(year, 1, bottom=level, width=width, color=color, edgecolor="white", linewidth=1.5, zorder=2)
            ax.plot(year, level + 0.5, marker=marker, color="white", markersize=7, markeredgewidth=0, zorder=3)
        if stack:
            ax.text(year, len(stack) + 0.18, str(len(stack)), ha="center", va="bottom", fontsize=13, fontweight="bold", color=INK)
    top = max(sum(r["year_first_appeared"] == y for r in plotted) for y in years)
    ax.set_ylim(0, 2 * ((top + 2) // 2))
    ax.set_xlim(first - 0.5, last + 0.5)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=12, color=INK)
    ax.tick_params(axis="x", length=0, pad=7)
    ax.set_yticks(range(0, int(ax.get_ylim()[1]) + 1, 2))
    ax.tick_params(axis="y", length=0, labelsize=12, colors=INK)
    ax.set_ylabel("Releases", fontsize=12, color=INK)
    ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for side in ("left", "right", "top"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK)
    if PARTIAL_YEAR in years:
        ax.annotate(PARTIAL_NOTE, xy=(PARTIAL_YEAR, 0), xycoords=("data", "axes fraction"), xytext=(0, -27), textcoords="offset points",
                    ha="center", va="top", fontsize=9.5, color=MUTED)
    shown = [k for k in CLASSES if any(label_to_key[r["application"]] == k for r in plotted)]
    handles = [Line2D([], [], linestyle="", marker=CLASSES[k][2], color=CLASSES[k][1], markersize=9, label=CLASSES[k][0]) for k in shown]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.03, 0.55), frameon=False, fontsize=12, handletextpad=0.8, labelspacing=0.5, borderaxespad=0)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"figure1_release_timeline.{ext}", facecolor="white", metadata={"CreationDate": None} if ext == "pdf" else None)
    with (OUT / "figure1_release_timeline_data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["package", "year_first_appeared", "application"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(plotted)
    print(f"wrote {OUT.relative_to(ROOT)}/figure1_release_timeline.png/.pdf and _data.csv ({len(plotted)} releases)")


if __name__ == "__main__":
    main()
