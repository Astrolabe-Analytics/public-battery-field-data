"""Figure 1: when each release in the collection became public, colored by service class.

Inputs: docs/descriptor/figure1_releases.csv (year and its source, per package) and
fielddata/package_facts.csv (service class). Outputs: docs/descriptor/figures/figure1_release_timeline.{png,pdf}
and figure1_release_timeline_data.csv (the plotted rows).
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
YEARS = ROOT / "docs" / "descriptor" / "figure1_releases.csv"
FACTS = ROOT / "fielddata" / "package_facts.csv"
OUT = ROOT / "docs" / "descriptor" / "figures"
# Fixed categorical order; palette checked for color-blind separation on the light surface #fcfcfb. Every marker is also labeled by name.
CLASSES = ["passenger EV", "bus", "light electric mobility", "grid-scale storage", "distributed storage",
           "consumer electronics", "industrial and robotics"]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
INK, MUTED, SURFACE = "#1f1f1e", "#6b6a63", "#fcfcfb"


def main() -> None:
    # a release with units in more than one class ("passenger EV, bus") is placed by its first class
    service = {r["package"]: r["value"].split(",")[0].strip() for r in csv.DictReader(FACTS.open(encoding="utf-8")) if r["field"] == "application"}
    rows = list(csv.DictReader(YEARS.open(encoding="utf-8")))
    missing = sorted(set(service) - {r["package"] for r in rows})
    if missing:
        raise SystemExit(f"no year for: {missing}")
    rows.sort(key=lambda r: (int(r["year"]), CLASSES.index(service[r["package"]]), r["package"]))
    stack: dict[int, int] = {}
    plotted = []
    for r in rows:
        year = int(r["year"])
        level = stack.get(year, 0)
        stack[year] = level + 1
        plotted.append({"package": r["package"], "year": year, "level": level, "service_class": service[r["package"]], "year_source": r["year_source"]})

    years = list(range(min(stack), max(stack) + 1))
    fig, ax = plt.subplots(figsize=(9.0, 3.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for p in plotted:
        x, y = p["year"], p["level"]
        ax.scatter([x - 0.44], [y], s=36, color=COLORS[CLASSES.index(p["service_class"])], edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.text(x - 0.37, y, p["package"], va="center", ha="left", fontsize=7, color=INK)
    ax.set_xlim(min(years) - 0.5, max(years) + 0.5)
    ax.set_ylim(-0.6, max(stack.values()) - 0.3)
    ax.set_xticks(years)
    ax.set_xticklabels([f"{y}\n{stack[y]} release{'s' if stack[y] > 1 else ''}" if y in stack else str(y) for y in years], fontsize=8, color=INK)
    ax.set_xticks([y + 0.5 for y in years[:-1]], minor=True)
    ax.tick_params(axis="x", which="major", length=0)
    ax.tick_params(axis="x", which="minor", length=4, colors=MUTED)
    ax.set_yticks([])
    for side in ("left", "right", "top"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    handles = [plt.Line2D([], [], marker="o", linestyle="", markersize=6, color=c, label=k) for k, c in zip(CLASSES, COLORS)
               if any(p["service_class"] == k for p in plotted)]
    ax.legend(handles=handles, loc="upper left", fontsize=7, frameon=False, labelcolor=INK, handletextpad=0.2, borderaxespad=0.2)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"figure1_release_timeline.{ext}", facecolor=SURFACE, metadata={"CreationDate": None} if ext == "pdf" else None)
    with (OUT / "figure1_release_timeline_data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(plotted[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(plotted)
    print(f"wrote {OUT.relative_to(ROOT)}/figure1_release_timeline.png/.pdf and _data.csv ({len(plotted)} releases)")


if __name__ == "__main__":
    main()
