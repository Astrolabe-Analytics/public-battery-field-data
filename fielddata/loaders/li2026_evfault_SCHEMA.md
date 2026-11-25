# li2026_evfault schema (admitted in v1.3)

Source: Li, J., Che, Y., Onori, S., Li, W. and Hu, X., "Battery fault diagnosis for in-service electric vehicles", Zenodo, published 2026-11-05, doi:10.5281/zenodo.23980122 (CC BY 4.0). Data and code for the paper "Cross-modal topology decodes battery faults from sparse voltage snapshots", Energy Storage Materials (2026), doi:10.1016/j.ensm.2026.105638, read in arXiv 2608.10825 (held in `paper/`). The release's readme and the record call the paper "Decoupling battery faults from sparse voltage snapshots via cross-modal topology". This package is separate from `li2026`, a different release by a different group.

Checks: `scripts/checks/li2026_evfault_codes.py` (layout, code meanings, per-code residuals; outputs in `reports/candidates/li2026_evfault/`) and `scripts/facts/li2026_evfault.py` (per-snapshot profile).

## Archive

One RAR5 archive, `Data & Code.rar` (20,779,637 bytes), with 6,842 files under `Data & Code/`:
- `Data/0.csv` to `Data/3406.csv`: 3,407 voltage snapshots, none missing. The readme says 3,408 labelled segments.
- `Label/0.csv` to `Label/3406.csv`: one label file per snapshot.
- `readme.txt`: 99 in-service EVs, four fault types, 3,408 labelled segments, three operating conditions (charging, driving and rest). The raw vehicle data are withheld for confidentiality.
- `core_model.py`: the model's structure only (PyTorch, 5 classes), with no data reading, feature, training or evaluation code. Its comments are in Chinese.
- `Source data/Fig.3`, `Fig.4`, `Fig.5`: the source data and images of the paper's main figures.

The loader streams the RAR with libarchive. On Windows set `LIBARCHIVE` to a libarchive DLL.

## Snapshots (`load()`)

Columns `V 1` to `V 14`: cell voltages in mV, as released, 50 rows each. The loader adds `window` (the file number) and `sample` (0 to 49). Raw values run from 3,554 to 4,202 mV, with no missing values.
- Cells: each pack has 14 series-connected ternary (NMC) cells with 14 voltage sensors (paper, Supplementary Note 1).
- Sampling: 0.1 Hz (paper p. 3), so a snapshot covers about 500 s (paper: "500-second snapshots", aligned to the end of charging, p. 6).
- In 3,151 of the 3,407 snapshots the 14-cell median voltage peaks at sample 24, and in 212 at sample 23 (raw, `li2026_evfault_profile.csv`), so charging ends about 240 s in. This is inference from the data. After it the vehicle rests or drives (paper Fig. 5 and Supplementary Fig. 3).
- Not released: time, current, temperature, pack voltage and vehicle identifiers (the paper's Note S1 lists these for the withheld raw data). The publisher removed missing and out-of-range values before release (Supplementary Note 2).

## Labels (`labels()`)

Each label file has 15 lines. The first is `0`, written without a decimal point, in every file. The next 14 are `0.0` to `4.0`. The first line is the column header that pandas writes for a column named 0, not a value, so the 14 values are the labels of cells 1 to 14, in the order of `V 1` to `V 14`. (A first look read the file as 15 values with position 0 always 0. The header reading explains why it is always 0 and the only line without a decimal point.)

| Code | Label | Cell-snapshots | Where the meaning comes from |
|---|---|---|---|
| 0 | fault-free (FF) | 44,802 | inference: the most common code, residuals near 0 |
| 1 | excessive inconsistency (EI) | 1,659 | readme and paper list order (first) |
| 2 | abnormal self-discharge (ASD) | 426 | readme and paper list order (second) |
| 3 | abnormal capacity degradation (ACD) | 503 | readme and paper list order (third) |
| 4 | internal short circuit (ISC) | 308 | readme and paper list order (fourth) |

Neither the readme nor the paper numbers the codes. Both list the faults as EI, ASD, ACD, ISC, and the paper's figures order the classes FF, EI, ASD, ACD, ISC (Fig. 3F, Supplementary Fig. 3). The data support this order:
- Per-code median residuals (cell minus 14-cell median, raw, `label_residuals.csv`): code 1 -26 mV early and -30 mV late in the snapshot (a steady offset, as the paper describes EI), code 2 -9 mV then -30 mV (a drop at rest, ASD), code 3 +4.5 mV then -14 mV (high at the end of charge, then low, ACD), code 4 -137 mV then -142 mV (ISC), code 0 0 mV.
- The paper's Fig. 5D to 5G source data each match one released cell exactly (0.0 to 0.5 mV, `code_matches.csv`). Their codes are 1, 2, 3 and 4. The series' own shapes are EI, ASD, ACD and ISC by the paper's descriptions.

**Disagreement:** the arXiv Fig. 5 caption names panels D to H as ACD, FF, EI, ASD and ISC. The source-data files D to G hold cells labelled 1 to 4, whose residuals look like EI, ASD, ACD and ISC. The caption and the source data disagree. The label order above is kept because the readme, the per-code residuals and the source series agree on it.

Labels change between snapshots of the same cell as faults evolve, and the terminal thermal-runaway stage was excluded (Supplementary Note 1). 2,236 snapshots have at least one labelled cell. Cell 14 carries 1,434 of the 2,896 labelled cell-snapshots. The largest raw residual of any unlabelled cell is 80.5 mV.

## Paper and release numbers

- The paper's "47,968 labeled samples" (p. 3) against 3,407 x 14 = 47,698 cell-snapshots in the release: probably transposed digits.
- The readme's 3,408 segments against 3,407 files.
- 99 vehicles and 16.4 million records (paper) describe the withheld raw data. The paper reports 99 vehicles, and the released files cannot rebuild that: they carry no vehicle identifiers.

## Vehicles: linking attempt

`scripts/checks/li2026_evfault_link.py` (report `reports/candidates/li2026_evfault/LINKING.md`) tried to link snapshots of the same vehicle by cell-offset fingerprints (each cell's median residual after charging ends) and by a persistent off-median cell with the same labelled cells. Snapshots next to each other in file order are much more alike than random pairs (median fingerprint distance 4.0 against 28.5 mV, raw), so the files are partly grouped by vehicle. But the number of chains depends on the threshold, from 2,364 at 2 mV to 104 at 40 mV, where 70 percent of random pairs also pass, and 32 of the 74 combinations of farthest cell and labelled cells recur more than 100 files apart. The paper's Fig. 3F source data (one EV) do not match any released snapshot under eight residual definitions, so there is no ground truth. Snapshots cannot be linked to vehicles reliably. Each labelled fault is treated as standalone. The release counts the 99 vehicles as stated by the readme and paper, not measured, and counts observation time as system-hours from the snapshots (maintainer, 2026-11-20).

## Cleaning

None. `clean=True` masks nothing. No sentinel codes are documented or observed.

## Standard view

Not mapped (explicit block, v1.3 admission 2026-11-24). The release holds voltage snapshots without time, current, temperature or vehicle identifiers. `fielddata.standard_systems("li2026_evfault")` lists every snapshot with `standard_status = "blocked"` for that reason. Use `load()` and `labels()` directly. The release is not built into the processed copy.
