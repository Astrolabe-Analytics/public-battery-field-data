# Table 3. Released and paper-defined fault labels

This table includes only fault or abnormality kinds that can be traced to a released label file or to a named paper page. Counts are direct counts from the released label tables on 2026-09-29. A fault-onset timestamp means an explicit timestamp attached to the fault label, not ordinary telemetry time.

| Package | Authors' name for fault or abnormality | How observed | Released count | Source | Fault onset timestamp in release |
|---|---|---|---:|---|---|
| xie | MSC (micro-short circuit), label 1 | Released per-cell label | 24 cells | `DataForPub.rar/predefinedDataset/processedData/predefined_device_cell_level.csv`; released author-code `code/dataProcess.ipynb`, “Abnormal Conditions” | no |
| xie | LowCapacity, label 2 | Released per-cell label | 28 cells | `DataForPub.rar/predefinedDataset/processedData/predefined_device_cell_level.csv`; released author-code `code/dataProcess.ipynb`, “Abnormal Conditions” | no |
| xie | HighSOC, label 3 | Released per-cell label | 35 cells | `DataForPub.rar/predefinedDataset/processedData/predefined_device_cell_level.csv`; released author-code `code/dataProcess.ipynb`, “Abnormal Conditions” | no |
| xie | LowSOC, label 4 | Released per-cell label | 29 cells | `DataForPub.rar/predefinedDataset/processedData/predefined_device_cell_level.csv`; released author-code `code/dataProcess.ipynb`, “Abnormal Conditions” | no |
| cao | Faulty, label 1; subtype not released | Released per-vehicle binary label | 61 vehicles: 3 DTI and 58 QAS | `DTI.zip/DTI/Labels.xls` and `QAS_5.zip/Labels.xls` | no |
| cao | TR (thermal runaway) | Paper diagnosis class; no released subtype labels | — | [Cao et al. (2025), p. 3, Fig. 2c](https://doi.org/10.1038/s41467-025-56832-8) | no |
| cao | EL (electrolyte leakage) | Paper diagnosis class; no released subtype labels | — | [Cao et al. (2025), p. 3, Fig. 2c](https://doi.org/10.1038/s41467-025-56832-8) | no |
| cao | ISC (internal short circuit) | Paper diagnosis class; no released subtype labels | — | [Cao et al. (2025), p. 3, Fig. 2c](https://doi.org/10.1038/s41467-025-56832-8) | no |
| cao | EA (excessive aging) | Paper diagnosis class; no released subtype labels | — | [Cao et al. (2025), p. 3, Fig. 2c](https://doi.org/10.1038/s41467-025-56832-8) | no |
| zhang2023 | Abnormal, label 1; mechanism not released | Released per-vehicle binary label | 55 vehicles: 30 brand 1, 16 brand 2, 9 brand 3 | `battery_brand1.tar.gz/battery_brand1/label/{train_label.csv,test_label.csv}`; `battery_brand2.tar.gz/battery_brand2/label/{train_label.csv,test_label.csv}`; `battery_brand3.tar.gz/battery_brand3/label/all_label.csv` | no |
| evbattery | Abnormal, label 1; mechanism not released | Released per-vehicle binary label | 48 vehicles: 31 dataset 1, 1 dataset 2, 16 dataset 3 | `battery_dataset{1,2,3}.tar.gz/.../label/label.csv` (read through `fielddata.systems('evbattery')`) | no |
| schaeffer | Battery systems returned for warranty claims | Reported in paper; not released as a fault label | 28 released systems; paper discusses 29 analyzed systems | [Schaeffer et al. (2024), p. 3](https://doi.org/10.1016/j.xcrp.2024.102258) | no |
| aitio | Capacity loss, diagnosed by the operator at repair (lead-acid) | Released per-battery repair label (STILL_ALIVE = FALSE, with the repair date) | 491 batteries; the authors chose a roughly balanced 491 failed / 536 healthy set, so the split is not a fleet failure rate | `meta_data.csv`; [Aitio and Howey (2021), accepted manuscript p. 22, step 3](https://doi.org/10.1016/j.joule.2021.11.006) | no (repair date, not onset) |
| m5bat-pbacid | Defective cell with elevated internal resistance, recurring protection shutdowns, and cell bypass on 10 August 2023 | Reported in paper; not released as a fault label | One cell bypassed; string changed from 300S to 299S | [Zurmühlen, Koltermann and Sauer (2026), pp. 4 and 10](https://doi.org/10.3390/en19174141) | no |
| ppl | Planned precautionary outages following prior incidents or for construction personnel safety | Reported in paper; not released as an event label | — | [Kyeremeh et al. (2026), p. 8](https://doi.org/10.1109/ACCESS.2026.3693606) | no |
| ppl | Unplanned outages associated with thermal management, power conversion, and BMS failure modes | Reported in paper; not released as event labels | — | [Kyeremeh et al. (2026), p. 12](https://doi.org/10.1109/ACCESS.2026.3693606) | no |
| m5bat-2023-04 | Pb3 cell-voltage measurement problems; inspection found no defective cell | Reported in operating report; not released as an event label | 8–18 April 2023 | [M5BAT Evaluation Operation Report 04/2023, p. 5](https://doi.org/10.18154/RWTH-2024-04895) | no |
| m5bat-2023-04 | Pb3 inverter error | Reported in operating report; not released as an event label | 17 April 2023 | [M5BAT Evaluation Operation Report 04/2023, p. 5](https://doi.org/10.18154/RWTH-2024-04895) | no |
| m5bat-2023-04 | Transformer shutdown causing unavailable frequency measurement | Reported in operating report; not released as an event label | 6 April 2023, 06:33:48–07:11:00 | [M5BAT Evaluation Operation Report 04/2023, p. 5](https://doi.org/10.18154/RWTH-2024-04895) | no |
| tsukuba | SOC recorded as 0%; removed from the authors' cleaned data | Reported in paper; not released as a fault label | One reported occurrence | [Vink, Ankyu and Koyama (2019), p. 7](https://doi.org/10.1038/sdata.2019.20) | no |
| tsukuba | SOC jumps and multi-day constant-SOC behavior | Reported in paper; not released as fault labels | 3.95-point jump on 24 February 2017; constant behavior ending with a second jump on 17 March 2017 | [Vink, Ankyu and Koyama (2019), p. 7](https://doi.org/10.1038/sdata.2019.20) | no |
| zhou2026 | Cell aging knee and accelerated degradation beyond approximately 240,000 km | Reported in paper; not released as a fault label | Demonstrated EV cell and fleet-level weakest-cell trends | [Zhou et al. (2026), pp. 4–6](https://doi.org/10.1038/s41560-026-02131-5) | no |
| tumftm | Company vehicle intentionally discharged until shutdown for experimental purposes | Reported in paper; not released as an event label | Repeated events for vehicle ID1 | [Schreiber et al. (2025), p. 10](https://doi.org/10.1016/j.etran.2025.100518) | no |
| li2026 | Internal short circuit, external short circuit, poor connection, self-discharge, and inconsistency faults | Reported in paper as laboratory-emulated fault classes; not released as labels in the held field-data archive | Five fault types, each graded at three severity levels | [Li et al. (2026), p. 4 and Supplementary Table S2](https://doi.org/10.1016/j.xcrp.2026.103210) | no |

## Label-file audit notes

- The Xie processed cell table contains 5,248 rows: 5,132 label 5 rows plus the 116 fault-labeled cells above. The released `dataProcess.ipynb` maps cases 1–4 to the four named fault classes and case 5 to normal. Label 5 is the non-fault reference class and is not a fault-kind row.
- The Cao sheets contain 473 binary-labeled vehicles: 61 label 1 and 412 label 0. The release does not map those binary labels to TR, EL, ISC, or EA.
- The Zhang label CSVs contain 348 rows: 55 label 1 and 293 label 0. One labeled car (battery_brand2 car 230, label 0) has no snippets, so 347 vehicles carry data, which is the released unit count in `fielddata/package_facts.csv` and the paper's count. The publisher removed abnormal data at or near battery failures (https://doi.org/10.1038/s41467-023-41226-5, p. 3), so abnormal vehicles hold only pre-failure history.
- None of these label tables contains an onset-time field. Ordinary telemetry indices or timestamps do not constitute a fault-onset annotation.
- The EVBattery label tables list 465 cars: 48 label 1 and 417 label 0, among the 464 cars with snippets. Dataset 3 is the same fleet as zhang2023 brand 2. All 49 vehicles are matched by content (`reports/facts/_cache/zhang2023_evbattery_pairs.json`: 44 by identical snippets, 5 by tolerance matching with agreeing charging-session numbers), and labels agree for all 49: the 16 abnormal vehicles in each release are the same 16 vehicles.

## Fault count

Faults are counted per faulty cell where the release labels cells (xie) and per battery otherwise; each battery (vehicle, device or system) is counted once.

| Package | Faults | Batteries | Basis |
|---|---:|---:|---|
| xie | 116 | 83 | Cells with a fault label (24 micro-short circuit, 28 low capacity, 35 high SOC, 29 low SOC) in 83 devices with a fault device label. |
| cao | 61 | 61 | Vehicles labeled faulty. |
| zhang2023 | 55 | 55 | Vehicles labeled abnormal. |
| evbattery | 32 | 32 | 48 vehicles labeled abnormal, less the 16 that are the same vehicles as zhang2023 brand 2. |
| schaeffer | 28 | 28 | Systems returned to the manufacturer under warranty (all released systems). |
| m5bat-pbacid | 1 | 1 | The string with the defective cell bypassed on 10 August 2023. |
| aitio | 491 | 491 | Batteries that entered repair for capacity loss, diagnosed by the operator at repair (lead-acid). The authors chose the roughly balanced 491/536 split; it is not a fleet failure rate. |
| **Total** | **784** | **751** | 755 faults in 722 batteries from released labels, 29 reported by the authors. |

Not counted, because they are temporary events, data or measurement artifacts, or not faults of a battery:

- ppl: planned precautionary outages, and unplanned outages from thermal management, power conversion and BMS faults. The system returned to service each time, so these are temporary system faults.
- m5bat-2023-04: Pb3 cell-voltage measurement problems (inspection found no defective cell), a Pb3 inverter error and a transformer shutdown. All temporary, and none a battery fault.
- tsukuba: SOC recorded as 0 percent, SOC jumps and constant-SOC periods. Measurement artifacts.
- tumftm: a vehicle discharged to shutdown on purpose. An experiment, not a fault.
- zhou2026: an aging knee beyond about 240,000 km. Degradation, not a fault.
- li2026: five fault types emulated in the laboratory. Not field faults, and not labeled in the released data.
