"""PPL E.W. Brown: plant-wide cell max minus min at rest, monthly, 2018 to 2021, plus the June 2023 check from the
one-second archive. Plot only (no title, no words): transparent PNG for the editable slide; words are text boxes.

Rest = |AC power| under 5 kW for the trailing 30 minutes, plant Running == 1, CellVoltMax above 2.5 V.
Spread = CellVoltMax minus CellVoltMin across all 4,760 cells (one-minute export, 2017 to 2021).
June 2023: Bank 1 (10 racks, 2,380 cells) from the 1 s archive; median 27 mV, p95 29 mV, max 61 mV (bar = median to p95).
Lines break where a month has no rest samples (2019 offline after McMicken, summer 2021).

Inputs : ../figs/ppl_rest_spread_monthly.csv   (median, p05, p95, n per month)
Output : ppl_spread_plot_notext.png, .svg; ppl_rest_spread_monthly_plotted.csv (the series as drawn)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
BLUE, BAND, GRAY, RED, INK = "#3757A6", "#D2D9EE", "#9A9A9A", "#B91C1C", "#333333"
plt.rcParams.update({"font.family": "DejaVu Sans"})

m = pd.read_csv(HERE.parent / "figs" / "ppl_rest_spread_monthly.csv", index_col=0, parse_dates=True)
m = m.reindex(pd.date_range("2018-01-01", "2021-12-01", freq="MS"))      # NaN where a month is missing -> line breaks
jun23 = pd.Timestamp("2023-06-15")
J_MED, J_P95 = 27, 29                                                      # Bank 1, 10 racks, 1 s archive extract

fig, ax = plt.subplots(figsize=(10.0, 4.6))
fig.patch.set_alpha(0); ax.set_facecolor("none")
ax.fill_between(m.index, m.p05, m.p95, color=BAND, lw=0, zorder=1)
ax.plot(m.index, m["median"], color=BLUE, lw=2.6, zorder=3)
ax.axhline(300, color=RED, lw=1.4, ls=(0, (6, 5)), zorder=0)
ax.errorbar([jun23], [J_MED], yerr=[[0], [J_P95 - J_MED]], fmt="o", color=BLUE, ms=8, capsize=4, lw=2, zorder=4)

ax.set_xlim(pd.Timestamp("2018-01-01"), pd.Timestamp("2023-12-31"))
ax.set_ylim(0, 360)
ax.set_yticks([0, 100, 200, 300])
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color(GRAY)
ax.tick_params(labelsize=17, length=4, color=GRAY, labelcolor=INK)
fig.subplots_adjust(left=0.08, right=0.99, bottom=0.11, top=0.99)
fig.savefig(HERE / "ppl_spread_plot_notext.png", dpi=200, transparent=True)
fig.savefig(HERE / "ppl_spread_plot_notext.svg", transparent=True)

out = m.copy(); out.index.name = "month"
out.loc[jun23.normalize(), ["median", "p95"]] = [J_MED, J_P95]
out.to_csv(HERE / "ppl_rest_spread_monthly_plotted.csv")
print("done")
