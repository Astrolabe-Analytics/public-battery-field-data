"""Checks the li2026_evfault release's layout and which fault each label code means.

What it does, through fielddata.loaders.li2026_evfault (raw values):
1. Layout: window numbers present and missing, samples and cells per window, the label files' first line and number
   of values, and the codes used.
2. Code meaning: the paper's Fig. 5D to 5G source data (Source data/Fig.5/Fig.5D.csv to Fig.5G.csv in the archive) give
   the 50-sample residual (cell voltage minus the 14-cell median, mV) of one sample each, named by the caption
   (paper p. 11, Fig. 5: D ACD, E FF, F EI, G ASD). The script finds the released window and cell whose residual matches
   each series (largest absolute difference, mV) and reports its label code. A match within the source data's rounding
   ties that code to the named fault in the authors' own files.
3. Per-label residual summary: for each code, the median over labelled cell-windows of the cell's median residual, in
   the first and last 20 samples (raw, mV), and the number of cell-windows.
Reads: the archive through the loader. Writes: reports/candidates/li2026_evfault/layout.txt, code_matches.csv and
label_residuals.csv.

Run (Windows: set the LIBARCHIVE variable to the archive DLL, as for xie): python scripts/checks/li2026_evfault_codes.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata.loaders import li2026_evfault as ev  # noqa: E402

OUT = ROOT / "reports" / "candidates" / "li2026_evfault"
CAPTION = {"Fig.5D.csv": "ACD", "Fig.5E.csv": "FF", "Fig.5F.csv": "EI", "Fig.5G.csv": "ASD"}  # paper p. 11, Fig. 5 caption


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = ev.load()
    lab = ev.labels()
    ids = sorted(data["window"].unique())
    missing = sorted(set(range(ids[0], ids[-1] + 1)) - set(ids))
    shape = data.groupby("window").size()
    lines = [f"windows: {len(ids)} (numbers {ids[0]} to {ids[-1]}, missing {missing})",
             f"samples per window: {sorted(shape.unique().tolist())}; cell columns: {[c for c in data.columns if c.startswith('V ')]}",
             f"label first lines: {sorted(lab['header'].unique().tolist())}; values per label file: {sorted(lab.groupby('window').size().unique().tolist())}",
             f"label codes (cell-windows): {lab['code'].value_counts().sort_index().to_dict()}",
             f"windows with any non-zero label: {int((lab.groupby('window')['code'].max() > 0).sum())}",
             f"raw voltage range: {data[ev.CELLS].min().min():g} to {data[ev.CELLS].max().max():g} mV; missing values: {int(data[ev.CELLS].isna().sum().sum())}",
             f"labelled cell-windows by cell: {lab[lab['code'] > 0].groupby('cell').size().to_dict()}"]

    volts = data[ev.CELLS].to_numpy().reshape(len(ids), 50, 14)
    resid = volts - np.median(volts, axis=2, keepdims=True)  # windows x samples x cells
    by = lab.set_index(["window", "cell"])["code"]
    rows = []
    for name, fault in CAPTION.items():
        series = pd.read_csv(io.BytesIO(ev.members("Source data/Fig.5/")[f"Data & Code/Source data/Fig.5/{name}"]), encoding="utf-8-sig")["Residual"].to_numpy()
        diff = np.abs(resid - series[None, :, None]).max(axis=1)  # windows x cells
        k = np.unravel_index(np.argmin(diff), diff.shape)
        window, cell = int(ids[k[0]]), int(k[1]) + 1
        tied = int((diff <= diff[k] + 1e-9).sum())
        rows.append({"figure": name, "caption_fault": fault, "window": window, "cell": cell, "max_abs_diff_mV": float(diff[k]),
                     "matches_at_that_diff": tied, "label_code": float(by[(window, cell)]), "code_by_readme_order": [c for c, f in ev.CODES.items() if f == fault][0]})
    matches = pd.DataFrame(rows)
    matches.to_csv(OUT / "code_matches.csv", index=False, lineterminator="\n")

    cell_med_first = np.median(resid[:, :20, :], axis=1)
    cell_med_last = np.median(resid[:, -20:, :], axis=1)
    summary = []
    for code in sorted(lab["code"].unique()):
        mask = np.zeros((len(ids), 14), dtype=bool)
        sel = lab[lab["code"] == code]
        pos = {w: i for i, w in enumerate(ids)}
        mask[[pos[w] for w in sel["window"]], (sel["cell"] - 1).to_numpy()] = True
        summary.append({"code": code, "label": ev.CODES.get(int(code)), "cell_windows": int(mask.sum()),
                        "median_residual_first20_mV": float(np.median(cell_med_first[mask])),
                        "median_residual_last20_mV": float(np.median(cell_med_last[mask])),
                        "max_abs_residual_mV": float(np.abs(resid.transpose(0, 2, 1)[mask]).max())})
    pd.DataFrame(summary).to_csv(OUT / "label_residuals.csv", index=False, lineterminator="\n")
    unlabelled = np.abs(resid.transpose(0, 2, 1)[(lab.pivot(index="window", columns="cell", values="code").loc[ids].to_numpy() == 0)])
    lines.append(f"unlabelled cells: largest |residual| {unlabelled.max():g} mV (raw)")
    (OUT / "layout.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    print(matches.to_string(index=False))
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
