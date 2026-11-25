# v1.3 changes from v1.2

Made by `scripts/checks/v13_changes.py`, comparing `reports/totals.json` at `b05cbdc` (v1.2 plus the v1.3 intake as candidates) with the current file. Two releases join: li2026_evfault and giu_ebike. lin_agv stays a candidate until its paper is out.

## Headline numbers

| Measure | v1.2 | v1.3 | Change |
|---|---:|---:|---:|
| Releases | 35 | 37 | +2 |
| Batteries (units) | 3,187 | 3,287 | +100 |
| Li-ion cells | 149,188 | 150,626 | +1,438 |
| Cell-voltage channels | 98,254 | 98,281 | +27 |
| Faults (Table 3) | 6,465 | 957 | -5,508 |
| Batteries with a fault | 752 | 840 | +88 |
| Faults in identified batteries | 785 | 957 | +172 |
| Charging sessions labelled faulty (not counted as faults in v1.3) | 5,680 | 5,680 | 0 |
| Voltage snapshots with a labelled cell (not counted as faults) | - | 2,236 | new |
| Energy (MWh) | 115.60 | 115.60 | +0.00 |
| Energy stated (MWh) | 35.84 | 35.84 | 0 |
| Energy computed (MWh) | 79.7576 | 79.7581 | +0.0005 |
| Unit-years | 3,040.3 | 3,040.3 | +0.0 |
| Observation-hours | 331,704 | 332,177 | +473 |
| Research groups | 27 | 28 | +1 |
| Data held (GB) | 255.54 | 255.57 | +0.02 |
| Files held and verified | 7,205 | 7,209 | +4 |
| Publisher-checksum matches: files | 5,933 | 5,935 | +2 |
| Publisher-checksum matches: archive members | 109 | 109 | 0 |

Units by class:

- light electric mobility: 271 to 272
- passenger EV: 1,653 to 1,752

## New rows in Table 1 (sources)

From `docs/descriptor/TABLE1_sources.md`.

| 2026 | [Nour, Zenodo](https://doi.org/10.5281/zenodo.24138446) | giu_ebike | [Zenodo](https://doi.org/10.5281/zenodo.24138446) | none | CC BY 4.0 |
| 2026 | [Li et al., Energy Storage Materials](https://doi.org/10.1016/j.ensm.2026.105638) | li2026_evfault | [Zenodo](https://doi.org/10.5281/zenodo.23980122) | [Zenodo](https://doi.org/10.5281/zenodo.23980122) | CC BY 4.0 |

## New rows in Table 2 (packages)

From `docs/descriptor/TABLE2_packages.md`.

| giu_ebike | light electric mobility | Egypt | NMC-class | 1 | 52 Li-ion | <0.1 unit-years | <0.001 (computed) | <0.01 |
| li2026_evfault | passenger EV | not stated | NMC | 99 | 1,386 Li-ion | at least 473 h | not available | 0.02 |

## New rows in Table 3 (faults)

From `docs/descriptor/TABLE3_faults.md`.

| li2026_evfault | Excessive inconsistency (EI), code 1 | Released per-cell label in each voltage snapshot; labels by engineers from accident reports, recall logs and teardown ([Li et al. (2026), Supplementary Note 1](https://doi.org/10.1016/j.ensm.2026.105638)) | 1,659 cell-snapshots | `Data & Code.rar/Data & Code/Label/<n>.csv` (read through `fielddata.loaders.li2026_evfault.labels()`); code order from `readme.txt` and the paper's list, checked by `scripts/checks/li2026_evfault_codes.py` | no |
| li2026_evfault | Abnormal self-discharge (ASD), code 2 | Released per-cell label in each voltage snapshot; labels by engineers from accident reports, recall logs and teardown ([Li et al. (2026), Supplementary Note 1](https://doi.org/10.1016/j.ensm.2026.105638)) | 426 cell-snapshots | `Data & Code.rar/Data & Code/Label/<n>.csv` (read through `fielddata.loaders.li2026_evfault.labels()`); code order from `readme.txt` and the paper's list, checked by `scripts/checks/li2026_evfault_codes.py` | no |
| li2026_evfault | Abnormal capacity degradation (ACD), code 3 | Released per-cell label in each voltage snapshot; labels by engineers from accident reports, recall logs and teardown ([Li et al. (2026), Supplementary Note 1](https://doi.org/10.1016/j.ensm.2026.105638)) | 503 cell-snapshots | `Data & Code.rar/Data & Code/Label/<n>.csv` (read through `fielddata.loaders.li2026_evfault.labels()`); code order from `readme.txt` and the paper's list, checked by `scripts/checks/li2026_evfault_codes.py` | no |
| li2026_evfault | Internal short circuit (ISC), code 4 | Released per-cell label in each voltage snapshot; labels by engineers from accident reports, recall logs and teardown ([Li et al. (2026), Supplementary Note 1](https://doi.org/10.1016/j.ensm.2026.105638)) | 308 cell-snapshots | `Data & Code.rar/Data & Code/Label/<n>.csv` (read through `fielddata.loaders.li2026_evfault.labels()`); code order from `readme.txt` and the paper's list, checked by `scripts/checks/li2026_evfault_codes.py` | no |
| giu_ebike | Faulty parallel group (group 8), its four cells replaced on 6 November 2026 | Stated in the release README; the raw log of one ride before the repair is released, no label file | One parallel group of four cells | `ebike-pack-dataset.zip/ebike-pack-dataset/README.md`; `raw/jk_001_before_repair.csv` | no |
| giu_ebike | 1 | 1 | The faulty parallel group 8 of the one pack, replaced on 6 November 2026, reported by the authors in the release README. One fault, because the release names the group, not single cells (maintainer, 2026-11-20). |
| li2026_evfault | 171 | 87 | Vehicle-level faults stated in the paper by fault type: 62 excessive inconsistency, 42 abnormal self-discharge, 44 abnormal capacity degradation, 23 internal short circuit ([Li et al. (2026), p. 3, Fig. 1D](https://doi.org/10.1016/j.ensm.2026.105638)), counted once per vehicle and fault type. 87 of the 99 vehicles carry at least one (read from the same figure, `scripts/checks/li2026_evfault_fig1d.py`). The release has no vehicle identifiers; it holds 2,236 voltage snapshots with a labelled cell, which are not counted as faults (maintainer, 2026-11-24, ledger V1). |

## Judgement calls to check before the descriptor update

- li2026_evfault units and cells are stated, not measured: the release has no vehicle identifiers (ledger V1).
- Fault count definition changed (ledger S1, maintainer, 2026-11-24): shenzhen_charging's 5,680 charging sessions labelled faulty are no longer counted as battery faults. They were 5,680 of v1.2's 6,465. The descriptor should say so, so readers comparing versions are not confused.
- li2026_evfault faults are the paper's vehicle-level counts (Fig. 1D): 171, once per vehicle and fault type, in 87 vehicles. A label can change between fault types as a fault evolves (paper, Supplementary Note 1), so 171 may count one faulty cell under two types; per battery it would be 87 (ledger V1).
- Research groups: li2026_evfault is taken to add no group (its corresponding authors are at RWTH ISEA and Chongqing University, taken as the group of deng and cell_to_pack). giu_ebike adds German International University (Egypt).
- giu_ebike has no paper. Its README names one that was not found in print on 2026-11-20. Its chemistry is inferred (NMC-class) and its energy computed (48 V x 9.44 Ah).
- The repository's docs/descriptor/DESCRIPTOR.md is a v1.1-era template (twenty-three releases). The rebuild refreshed only its filled numbers (DESCRIPTOR_filled.md). The v1.2 Word descriptor is the text to update.
