"""Facts for giu_ebike (admitted in v1.3, 2026-11-24, counts approved by the maintainer 2026-11-20), and its profile.

What it does: reads the six recordings through fielddata.loaders.giu_ebike (raw values) and writes, per recording,
rows, first and last time, duration, steps longer than 5 s, repeated timestamps, the share of lines flagged valid and
whether the flag matches the README's rule (13 cells sum to pack voltage within 0.03 V), and raw ranges of cell
voltage, pack voltage, current and temperatures. For the raw pre-repair log it measures parallel group 8 (cell08):
its minimum, seconds below 2.5 V, readings of exactly 0 V, the lowest other group at those times and the current
then, and the current sign against the logged charge counter. Then it writes the proposed facts.
Reads: the release zip through the loader.
Writes: reports/candidates/giu_ebike/giu_ebike_profile.csv, group8.txt, reports/facts/giu_ebike.json through scripts/facts/_common.py measure().

Run: python scripts/facts/giu_ebike.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import fact  # noqa: E402
from _v13 import CANDIDATE_OUT  # noqa: E402

from fielddata.loaders import giu_ebike as eb  # noqa: E402

SCRIPT = "scripts/facts/giu_ebike.py"
OUT = CANDIDATE_OUT / "giu_ebike"
README = "ebike-pack-dataset.zip/ebike-pack-dataset/README.md (https://doi.org/10.5281/zenodo.24138446)"
LOCAL_UTC_OFFSET = pd.Timedelta(hours=2)  # README: cleaned files are local time, UTC+2


def collect() -> tuple[dict, dict]:
    """The release's facts, for scripts/facts/_common.measure (via _v13.apply). Also writes the profile and group8.txt."""
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in eb.RECORDINGS:
        frame = eb.load(name)
        raw = name == eb.RAW
        t = frame["utc_time"].dt.tz_localize(None) if raw else frame["time"] - LOCAL_UTC_OFFSET  # UTC, naive
        step = t.diff().dt.total_seconds()
        cells = frame[eb.CELL_COLUMNS]
        row = {"recording": name, "rows": len(frame), "first_utc": t.min(), "last_utc": t.max(),
               "hours": (t.max() - t.min()).total_seconds() / 3600, "steps_over_5s": int((step > 5).sum()),
               "longest_step_s": float(step.max()), "repeated_times": int(t.duplicated().sum()),
               "cell_v_min_raw": float(cells.min().min()), "cell_v_max_raw": float(cells.max().max()),
               "pack_v_min_raw": float(frame["pack_V"].min()), "pack_v_max_raw": float(frame["pack_V"].max()),
               "current_min_raw": float(frame["current_A"].min()), "current_max_raw": float(frame["current_A"].max()),
               "missing_values": int(frame.drop(columns=["recording"]).isna().sum().sum()),
               "missing_by_column": ";".join(f"{c}:{n}" for c, n in frame.isna().sum().items() if n)}
        if not raw:
            rule = (cells.sum(axis=1) - frame["pack_V"]).abs() <= 0.03
            row.update({"valid_share": float(frame["valid"].mean()), "valid_flag_matches_rule": float((rule == frame["valid"]).mean()),
                        "t_center_max_raw": float(frame["t_center_C"].max())})
        else:
            row["t_center_max_raw"] = float(frame["t_pack_C"].max())
        rows.append(row)
    profile = pd.DataFrame(rows)
    profile.to_csv(OUT / "giu_ebike_profile.csv", index=False, lineterminator="\n")

    raw = eb.load(eb.RAW)
    others = raw[[c for c in eb.CELL_COLUMNS if c != "cell08"]]
    low = raw["cell08"] < 2.5
    sign = np.corrcoef(raw["current_A"].iloc[1:], raw["charge_Ah"].diff().iloc[1:])[0, 1]
    group8 = [f"raw pre-repair log, {len(raw)} lines, {raw['utc_time'].min()} to {raw['utc_time'].max()}",
              f"cell08 minimum (raw): {raw['cell08'].min():.3f} V; lines below 2.5 V: {int(low.sum())}; lines at exactly 0 V: {int((raw['cell08'] == 0).sum())}",
              f"while cell08 < 2.5 V: lowest other group {others[low].min().min():.3f} V, current {raw.loc[low, 'current_A'].min():.2f} to {raw.loc[low, 'current_A'].max():.2f} A (raw)",
              f"seconds below 2.5 V by time stamps: {int(low.sum())} lines at about 1 s each",
              f"correlation of current_A with the change in charge_Ah: {sign:.3f} (positive: current is positive in discharge in the raw file too)",
              f"cell08 at the start and end of the log: {raw['cell08'].iloc[0]:.3f} V and {raw['cell08'].iloc[-1]:.3f} V; others median {others.iloc[-1].median():.3f} V at the end"]
    (OUT / "group8.txt").write_text("\n".join(group8) + "\n", encoding="utf-8", newline="\n")

    span_days = (profile["last_utc"].max() - profile["first_utc"].min()).total_seconds() / 86400
    facts = {}
    facts["application"] = fact("light electric mobility", "derived", "classification mapping required by the facts audit brief", "E-bike pack (README).")
    facts["chemistry"] = fact("NMC-class", "derived", "scripts/checks/giu_ebike_group8.py -> GROUP8_CHEMISTRY.md (parallel groups charge to 4.17 to 4.25 V, raw)",
                              "Inferred from the charge voltage, as the _extra.py rule (above 3.95 V: NMC-class): groups charge to 4.17 to 4.25 V, while LFP ends charge near 3.6 V. Not LFP. The README names the cell (Samsung INR18650-30Q) but not its chemistry.")
    facts["cells_liion"] = fact(52, "stated", f"{README} ('52 Samsung INR18650-30Q cells, 13S4P')",
                                "The four cells of group 8 were replaced on 6 November 2026 (README). The four replacement cells are not added: the pack holds 52 cells at any time.")
    facts["cell_channels_measured"] = fact(13, "measured", f"{SCRIPT}: cell01 to cell13, one per parallel group of 4 cells")
    facts["energy_mwh"] = fact(48.0 * 9.44 / 1e6, "derived", f"{README}: 48 V nominal x 9.44 Ah usable capacity from BMS cutoff to full charge",
                               "Computed from the README's stated nominal voltage and its stated usable capacity (which the authors measured). No pack rating in kWh is stated. The cell maker's 3.0 Ah rating would give 13 x 4 x 3.0 Ah x 3.6 V = 0.56 kWh, but it is not in the release.")
    facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from stated configuration")
    facts["span_unit_years"] = fact(span_days / 365.25, "measured", f"{SCRIPT} -> giu_ebike_profile.csv (first to last time over all recordings, cleaned files shifted from UTC+2 to UTC)",
                                    f"One pack, {span_days:.1f} days from the raw log of 29 October 2026 to the last cleaned file on 9 November 2026. Recorded time is {profile['hours'].sum():.1f} h.")
    facts["obs_hours"] = fact(None, "not_in_release", note="Calendar spans are measurable, so observation-hours are not used.")
    extra = {"faults_counted": fact(1, "stated", f"{README} ('before a faulty parallel group (group 8) was replaced'; 'The four cells of group 8 were replaced on 6 November 2026')",
                                     "One faulty parallel group (4 cells in parallel, one voltage channel), labelled by the release. Under ledger F1 (once per faulty cell where a release labels cells) the release labels the group, not single cells, so 1 (maintainer, 2026-11-20). Recorded in Table 3.")}
    return facts, extra


if __name__ == "__main__":
    from _common import run
    run("giu_ebike")
