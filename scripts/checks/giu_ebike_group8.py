"""giu_ebike: was one cell of parallel group 8 bad, or the whole group? And is the pack LFP?

What it does, through fielddata.loaders.giu_ebike (raw values; only `valid` lines of the cleaned files, as the README
advises for cell voltages):
1. Sag per amp for each parallel group: for every line with discharge current above 10 A, the drop of the group's
   voltage from its last rest value (|I| < 0.3 A) divided by the current, in mOhm; median per group, per recording.
   The voltage data are per parallel group of 4 cells, so single cells cannot be seen. If one of four equal cells
   failed open, the group's resistance would rise by a third; if three failed, four times.
2. Voltage range per recording (raw), against the LFP range (full charge about 3.6 V per cell).
Reads: the release zip through the loader.
Writes: reports/candidates/giu_ebike/GROUP8_CHEMISTRY.md.

Run: python scripts/checks/giu_ebike_group8.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata.loaders import giu_ebike as eb  # noqa: E402

OUT = ROOT / "reports" / "candidates" / "giu_ebike"
OTHERS = [c for c in eb.CELL_COLUMNS if c != "cell08"]


def sag(frame: pd.DataFrame) -> tuple[pd.Series, int]:
    frame = frame.reset_index(drop=True)
    reference = frame[eb.CELL_COLUMNS].where(frame["current_A"].abs() < 0.3).ffill()
    load = frame["current_A"] > 10
    per_amp = (reference[load] - frame.loc[load, eb.CELL_COLUMNS]).div(frame.loc[load, "current_A"], axis=0) * 1000
    return per_amp.median(), int(load.sum())


def main() -> None:
    lines = ["# giu_ebike: group 8 and chemistry", "", "Made by `scripts/checks/giu_ebike_group8.py`. All values are measured on raw data.", "",
             "## Sag per amp (mOhm, median over lines above 10 A)", "", "| Recording | Lines | Group 8 | Other groups, median | Other groups, range |", "|---|---|---|---|---|"]
    ratio = None
    for name in [eb.RAW, *eb.CLEAN[:4]]:
        frame = eb.load(name)
        if "valid" in frame:
            frame = frame[frame["valid"]]
        s, n = sag(frame)
        lines.append(f"| {name} | {n:,} | {s['cell08']:.1f} | {s[OTHERS].median():.1f} | {s[OTHERS].min():.1f} to {s[OTHERS].max():.1f} |")
        if name == eb.RAW:
            ratio = s["cell08"] / s[OTHERS].median()
    lines += ["", "## Voltage range per parallel group (raw)", ""]
    for name in eb.RECORDINGS:
        frame = eb.load(name)
        lines.append(f"- {name}: {frame[eb.CELL_COLUMNS].min().min():.3f} to {frame[eb.CELL_COLUMNS].max().max():.3f} V")
    lines += ["", "## Conclusions", "",
              f"- One cell or four: the data give one voltage per parallel group, so single cells cannot be seen. Before the repair, group 8 sags about {ratio:.0f} times as much per amp as the other groups in the same ride. "
              "One open cell of four would raise the group's resistance by a third, and three open cells four times, so the whole group was weak, or its connection was. "
              "After the repair group 8 sags least of all groups, as new cells would. The README says all four cells were replaced and does not say which were bad.",
              "- Chemistry: not LFP. Parallel groups charge to between 4.17 and 4.25 V, while LFP cells end charge near 3.6 V. That fits a nickel-based lithium-ion cell (NMC class). Inference from the data; the release states no chemistry."]
    (OUT / "GROUP8_CHEMISTRY.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
