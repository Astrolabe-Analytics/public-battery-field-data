"""Facts for li2026_evfault (admitted in v1.3, 2026-11-24, counts approved by the maintainer 2026-11-20), and its profile.

What it does: reads the snapshots and labels through fielddata.loaders.li2026_evfault (raw values) and writes, per
window, the samples, the raw voltage range, the sample at which the 14-cell median voltage peaks (where charging
ends, by inference) and the labelled cells, then the proposed facts. Layout and code-meaning checks are in
scripts/checks/li2026_evfault_codes.py.
Reads: the archive through the loader (Windows: set the LIBARCHIVE variable to the archive DLL, as for xie).
Writes: reports/candidates/li2026_evfault/li2026_evfault_profile.csv, reports/facts/li2026_evfault.json through scripts/facts/_common.py measure().

Run: python scripts/facts/li2026_evfault.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import fact  # noqa: E402
from _v13 import CANDIDATE_OUT  # noqa: E402

from fielddata.loaders import li2026_evfault as ev  # noqa: E402

SCRIPT = "scripts/facts/li2026_evfault.py"
OUT = CANDIDATE_OUT / "li2026_evfault"
PAPER = "https://doi.org/10.1016/j.ensm.2026.105638 (read in arXiv 2608.10825)"
SAMPLE_S = 10  # 0.1 Hz, paper p. 3


def collect() -> tuple[dict, dict]:
    """The release's facts and extra facts, for scripts/facts/_common.measure (via _v13.apply)."""
    OUT.mkdir(parents=True, exist_ok=True)
    data = ev.load()
    systems = ev.systems()
    ids = systems["window"].to_numpy()
    volts = data[ev.CELLS].to_numpy().reshape(len(ids), 50, 14)
    median = np.median(volts, axis=2)
    profile = systems.assign(v_min_raw=volts.min(axis=(1, 2)), v_max_raw=volts.max(axis=(1, 2)),
                             median_v_peak_sample=median.argmax(axis=1))
    profile.to_csv(OUT / "li2026_evfault_profile.csv", index=False, lineterminator="\n")
    lab = ev.labels()
    labelled = lab[lab["code"] > 0]
    windows = len(ids)
    hours = windows * 50 * SAMPLE_S / 3600

    facts = {}
    facts["units_released"] = fact(99, "stated", f"release readme ('real-world data from 99 in-service EVs') and {PAPER}, p. 3 and Supplementary Note 1",
                                   "Counted as stated (maintainer, 2026-11-20). Vehicle identifiers are not released, and snapshots cannot be linked to vehicles reliably "
                                   "(scripts/checks/li2026_evfault_link.py, reports/candidates/li2026_evfault/LINKING.md), so the files cannot rebuild the 99. "
                                   "Observation time is counted as system-hours from the snapshots.")
    facts["application"] = fact("passenger EV", "derived", "classification mapping required by the facts audit brief",
                                "In-service EVs (readme; paper Note S1). The vehicle type is not disclosed.")
    facts["chemistry"] = fact("NMC (ternary)", "stated", f"{PAPER}, Supplementary Note 1 ('14 series-connected ternary cells') and Discussion ('ternary chemistries')")
    facts["cells_liion"] = fact(99 * 14, "stated", f"release readme ('99 in-service EVs') and {PAPER}, Supplementary Note 1 (each pack 14 series-connected cells)",
                                "Follows the 99 stated vehicles: 99 x 14. No parallel count is stated (ledger C1). Not measurable from the files.")
    facts["cell_channels_measured"] = fact(14, "measured", f"{SCRIPT}: V 1 to V 14 in every snapshot",
                                           "14 channels per snapshot. Which vehicle a snapshot comes from is not released.")
    facts["energy_mwh"] = fact(None, "not_in_release", note="No rating, capacity or current is released.")
    facts["energy_basis"] = fact("none", "derived", "energy_mwh is not available")
    facts["span_unit_years"] = fact(None, "not_in_release", note="The release has no timestamps.")
    facts["obs_hours"] = fact(hours, "derived", f"{windows:,} snapshots x 50 samples x 10 s (0.1 Hz, {PAPER}, p. 3) / 3600",
                              "System-hours from the windows, counted (maintainer, 2026-11-20): snapshot time only, assuming snapshots do not overlap (each is aligned to the end of a different charge, paper p. 6). Not the vehicles' service time.")
    facts["fault_onset_timestamp"] = fact("no", "stated", f"{ev.__name__}: labels per snapshot and cell, no time; {PAPER}, Note S1 (terminal thermal-runaway stage excluded)")
    extra = {
        "snapshots": fact(windows, "measured", f"{SCRIPT}: Data/0.csv to Data/{windows - 1}.csv, none missing",
                          "The readme says 3,408 labelled segments. The paper's 47,968 labelled samples compare with 3,407 x 14 = 47,698 cell-snapshots (digits transposed, probably)."),
        "fault_label_cell_snapshots": fact(int(len(labelled)), "measured", f"{SCRIPT} via labels()",
                                           "Cell-snapshots with a non-zero code: " + ", ".join(f"{ev.CODES[int(c)]} {n:,}" for c, n in labelled["code"].value_counts().sort_index().items())
                                           + f". {int((systems['faulty_cells'] > 0).sum()):,} snapshots have at least one labelled cell. Cell 14 carries {int((labelled['cell'] == 14).sum()):,} of them."),
        "snapshot_fault_labels": fact(int((systems["faulty_cells"] > 0).sum()), "measured", f"{SCRIPT} via systems(); scripts/checks/li2026_evfault_link.py",
                                "Snapshots with at least one labelled cell. Not the fault count (maintainer, 2026-11-24, ledger V1): Table 3 uses the paper's vehicle-level faults (faults_stated). Snapshots cannot be linked to vehicles, "
                                "so each labelled snapshot is standalone. This overstates the number of faulty cells, since one faulty cell appears in many snapshots (paper Fig. 3F: 32 snapshots of one EV). "
                                f"Counted per labelled cell-snapshot it would be {int(len(labelled)):,}."),
        "faults_stated": fact(171, "stated", f"{PAPER}, p. 3, Fig. 1D (EI 62, ASD 42, ACD 44, ISC 23 EVs); ACD's 44 EVs also on p. 8",
                              "Vehicle-level faults, once per vehicle and fault type (maintainer, 2026-11-24, ledger V1). The grid reading in scripts/checks/li2026_evfault_fig1d.py reproduces the printed counts."),
        "fault_batteries_stated": fact(87, "derived", "scripts/checks/li2026_evfault_fig1d.py -> reports/candidates/li2026_evfault/fig1d_summary.txt (read from the grid of the paper's Fig. 1D)",
                                       "87 of the 99 EVs carry at least one fault label; 12 are labelled fault-free only. Counted from the figure, not printed in the paper."),
        "charge_end_sample": fact(int(np.median(profile["median_v_peak_sample"])), "measured", f"{SCRIPT} -> li2026_evfault_profile.csv",
                                  f"Median over snapshots of the sample at which the 14-cell median voltage peaks (inference for the end of charging; interquartile range {int(profile['median_v_peak_sample'].quantile(0.25))} to {int(profile['median_v_peak_sample'].quantile(0.75))})."),
    }
    return facts, extra


if __name__ == "__main__":
    from _common import run
    run("li2026_evfault")
