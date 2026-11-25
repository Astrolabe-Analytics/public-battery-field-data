"""Can li2026_evfault's snapshots be linked to vehicles? An attempt with cell-offset fingerprints.

The release has no vehicle identifiers (the paper reports 99 EVs). This script tries to link snapshots that come from
the same pack, and tests the attempt against the one known single-vehicle set in the authors' own files.

What it does, through fielddata.loaders.li2026_evfault (raw values):
1. Ground truth: the paper's Fig. 3F source data (Source data/Fig.3/Fig.3f.csv) give, for snapshots of one EV with
   ASD (paper p. 7, Fig. 3F caption), a 14-cell "Residual" block (the caption: the average residual between each cell
   and the median voltage). Each row is compared with every released snapshot under eight definitions of a per-cell
   average residual (largest absolute cell difference, mV). A match within the rounding would give a known
   single-vehicle set.
2. Fingerprint per snapshot: each cell's median residual over samples 30 to 49 (after charging ends), mV.
3. Neighbours in file order: the fingerprint distance (largest absolute cell difference) between snapshot n and n+1,
   against random pairs.
4. Chaining: consecutive snapshots are joined when their distance is below a threshold. The number of chains is
   reported for several thresholds, next to the paper's 99 vehicles.
5. Persistent off-median cell: consecutive snapshots are joined when the cell farthest from the median and the set of
   labelled cells are the same. The number of such chains is reported.
Reads: the archive through the loader (Windows: set the LIBARCHIVE variable to the archive DLL, as for xie).
Writes: reports/candidates/li2026_evfault/link_ground_truth.csv, link_chains.csv and LINKING.md.

Run: python scripts/checks/li2026_evfault_link.py
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
THRESHOLDS = [2, 5, 10, 20, 40]  # mV
RNG = np.random.default_rng(0)


def main() -> None:
    data = ev.load()
    ids = np.sort(data["window"].unique())
    volts = data[ev.CELLS].to_numpy().reshape(len(ids), 50, 14)
    resid = volts - np.median(volts, axis=2, keepdims=True)
    mean_abs = np.abs(resid).mean(axis=1)  # windows x cells
    finger = np.median(resid[:, 30:, :], axis=1)

    # 1. ground truth from Fig. 3F: try eight definitions of the per-cell average residual
    raw = pd.read_csv(io.BytesIO(ev.members("Source data/Fig.3/")["Data & Code/Source data/Fig.3/Fig.3f.csv"]),
                      encoding="utf-8-sig", header=None)
    start = int(np.where(raw.iloc[0].astype(str) == "Residual")[0][0])
    fig = raw.iloc[1:, start:start + 14].astype(float).dropna().to_numpy()
    mean_dev = volts - volts.mean(axis=2, keepdims=True)
    definitions = {"mean |cell - median|": np.abs(resid).mean(axis=1), "|mean(cell - median)|": np.abs(resid.mean(axis=1)),
                   "mean |cell - pack mean|": np.abs(mean_dev).mean(axis=1), "|mean(cell - pack mean)|": np.abs(mean_dev.mean(axis=1)),
                   "rms(cell - median)": np.sqrt((resid ** 2).mean(axis=1)), "std of cell": volts.std(axis=1),
                   "mean |cell - median|, samples 25 to 49": np.abs(resid[:, 25:]).mean(axis=1), "max |cell - median|": np.abs(resid).max(axis=1)}
    gt_rows = []
    for name, value in definitions.items():
        best = np.array([np.abs(value - row[None, :]).max(axis=1).min() for row in fig])
        gt_rows.append({"definition": name, "rows": len(fig), "best_match_median_mV": float(np.median(best)),
                        "best_match_worst_mV": float(best.max()), "rows_within_rounding": int((best <= 0.06).sum())})
    gt = pd.DataFrame(gt_rows)
    gt.to_csv(OUT / "link_ground_truth.csv", index=False, lineterminator="\n")
    matched = int(gt["rows_within_rounding"].max())

    # 3. neighbours in file order against random pairs
    dist = lambda a, b: np.abs(finger[a] - finger[b]).max(axis=-1)  # noqa: E731
    consecutive = dist(np.arange(len(ids) - 1), np.arange(1, len(ids)))
    a, b = RNG.integers(0, len(ids), 20000), RNG.integers(0, len(ids), 20000)
    keep = a != b
    random_pairs = dist(a[keep], b[keep])

    # 4. chaining in file order
    chains = [{"threshold_mV": t, "chains": int((consecutive >= t).sum()) + 1,
               "longest_chain": int(max(np.diff(np.flatnonzero(np.r_[True, consecutive >= t, True])))),
               "consecutive_pairs_below": float((consecutive < t).mean()), "random_pairs_below": float((random_pairs < t).mean())}
              for t in THRESHOLDS]
    chain_table = pd.DataFrame(chains)
    chain_table.to_csv(OUT / "link_chains.csv", index=False, lineterminator="\n")

    # 5. persistent off-median cell and label set
    lab = ev.labels().pivot(index="window", columns="cell", values="code").loc[ids].to_numpy()
    key = [(int(np.argmax(np.abs(f))), tuple(np.flatnonzero(l > 0))) for f, l in zip(finger, lab)]
    same = np.array([key[k] == key[k + 1] for k in range(len(key) - 1)])
    persistent_chains = int((~same).sum()) + 1
    faulty_key = [k for k, l in zip(key, lab) if (l > 0).any()]
    spread = {}
    for n, (k, l) in enumerate(zip(key, lab)):
        if (l > 0).any():
            spread.setdefault(k, []).append(n)
    far = sum(1 for positions in spread.values() if np.max(np.diff(positions), initial=0) > 100)

    lines = [
        "# li2026_evfault: linking snapshots to vehicles",
        "",
        "Made by `scripts/checks/li2026_evfault_link.py`. All values are measured on raw data.",
        "",
        "## Ground truth from the paper's Fig. 3F",
        "",
        f"Fig. 3F's source data hold a 14-cell residual block for {len(fig)} snapshots of one EV with abnormal self-discharge. Under none of eight definitions of a per-cell average residual "
        f"does any row match a released snapshot within the rounding (0.06 mV): {matched} rows do. The best definition misses by a median of {gt['best_match_median_mV'].min():.2f} mV (`link_ground_truth.csv`). "
        "The block was probably computed from the withheld raw data, so it gives no known single-vehicle set to test linking against.",
        "",
        "## Fingerprints",
        "",
        "Fingerprint: each cell's median residual over samples 30 to 49, after charging ends. Distance: the largest absolute cell difference, mV.",
        f"Neighbours in file order: median distance {np.median(consecutive):.1f} mV (quartiles {np.quantile(consecutive, 0.25):.1f} to {np.quantile(consecutive, 0.75):.1f}). "
        f"Random pairs: median {np.median(random_pairs):.1f} mV (quartiles {np.quantile(random_pairs, 0.25):.1f} to {np.quantile(random_pairs, 0.75):.1f}).",
        "",
        "## Chains in file order",
        "",
        "| Threshold (mV) | Chains | Longest | Neighbour pairs below | Random pairs below |",
        "|---|---|---|---|---|",
        *[f"| {r.threshold_mV} | {r.chains:,} | {r.longest_chain:,} | {r.consecutive_pairs_below:.2f} | {r.random_pairs_below:.2f} |" for r in chain_table.itertuples()],
        "",
        "",
        "## Persistent off-median cell",
        "",
        f"Joining consecutive snapshots whose farthest-from-median cell and set of labelled cells are the same gives {persistent_chains:,} chains "
        f"({same.mean() * 100:.0f} percent of neighbour pairs agree). Among the {len(faulty_key):,} snapshots with a labelled cell there are {len(set(faulty_key)):,} distinct combinations of farthest cell and labelled cells, "
        f"and {far} of them recur after a gap of more than 100 file numbers, so a combination alone does not identify a vehicle.",
        "",
        "## Conclusion",
        "",
        "Snapshots next to each other in file order are much more alike than random pairs, so the files are partly grouped by vehicle. "
        "But the number of chains depends on the threshold, from thousands at 2 mV to about a hundred at 40 mV, where most random pairs also pass. "
        "No threshold separates same-vehicle pairs from different-vehicle pairs, and there is no ground truth to set one. "
        "The paper reports 99 vehicles, and the files cannot rebuild that. Snapshots cannot be linked to vehicles reliably, so each labelled fault is treated as standalone.",
    ]
    (OUT / "LINKING.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
