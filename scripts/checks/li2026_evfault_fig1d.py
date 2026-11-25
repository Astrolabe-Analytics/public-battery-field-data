"""li2026_evfault: vehicle-level fault counts read from the paper's Fig. 1D.

The release has no vehicle identifiers. The journal paper (Li et al., Energy Storage Materials 92 (2026) 105638, p. 3,
Fig. 1D, "Display of EV battery fault types") shows one column per EV (#1 to #99) and one row per label (FF, EI, ASD,
ACD, ISC), dark for true, and prints the per-label vehicle counts beside it: 99, 62, 42, 44 and 23 EVs.

What it does: takes the figure image from page 3 of the held journal PDF (the paper/ folder beside the release's data/
folder; no data files are read), finds the grid's column span from the always-true FF row, reads each of the 99 columns
in each row as dark or light, and checks that the per-row totals reproduce the printed counts. It then counts the EVs
with at least one fault label and the number of fault types per EV.
Reads: paper/Li2026_ESM_105638.pdf. Writes: reports/candidates/li2026_evfault/fig1d_counts.csv (one row per EV) and
fig1d_summary.txt.

Run: python scripts/checks/li2026_evfault_fig1d.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata.loaders._base import directory  # noqa: E402

OUT = ROOT / "reports" / "candidates" / "li2026_evfault"
PRINTED = {"FF": 99, "EI": 62, "ASD": 42, "ACD": 44, "ISC": 23}  # the counts printed beside the grid
ROW_Y = {"FF": 50, "EI": 105, "ASD": 165, "ACD": 222, "ISC": 280}  # row centres in the 2000 x 1024 figure image
FAULTS = ["EI", "ASD", "ACD", "ISC"]


def main() -> None:
    pdf = directory("li2026_evfault").parent / "paper" / "Li2026_ESM_105638.pdf"
    image = PdfReader(str(pdf)).pages[2].images[0].image.convert("RGB")
    if image.size != (2000, 1024):
        raise SystemExit(f"unexpected figure size {image.size}")
    px = np.asarray(image).astype(int)
    dark_ff = (px[40:60, 1100:1860].sum(axis=2) < 300).mean(axis=0) > 0.5
    cols = np.flatnonzero(dark_ff) + 1100
    blocks = np.split(cols, np.flatnonzero(np.diff(cols) > 4) + 1)
    grid = max(blocks, key=len)
    x0, x1 = int(grid[0]), int(grid[-1])
    width = (x1 - x0 + 1) / 99
    rows = {}
    for label, y in ROW_Y.items():
        rows[label] = [bool(px[y - 8:y + 8, int(x0 + (c + 0.5) * width) - 1:int(x0 + (c + 0.5) * width) + 2].reshape(-1, 3).mean(axis=0).sum() < 400)
                       for c in range(99)]
    table = pd.DataFrame(rows)
    table.insert(0, "ev", range(1, 100))
    counts = {label: int(table[label].sum()) for label in PRINTED}
    if counts != PRINTED:
        raise SystemExit(f"grid reading {counts} does not reproduce the printed counts {PRINTED}")
    per_ev = table[FAULTS].sum(axis=1)
    table["fault_types"] = per_ev
    OUT.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT / "fig1d_counts.csv", index=False, lineterminator="\n")
    lines = [f"Fig. 1D grid columns x {x0} to {x1} ({width:.2f} px per EV); per-label counts reproduce the printed ones: {counts}",
             f"vehicle-level faults (EV and fault type): {int(per_ev.sum())}",
             f"EVs with at least one fault label: {int((per_ev > 0).sum())} of 99; fault-free only: {int((per_ev == 0).sum())}",
             f"EVs by number of fault types (0 to 4): {np.bincount(per_ev, minlength=5).tolist()}"]
    (OUT / "fig1d_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
