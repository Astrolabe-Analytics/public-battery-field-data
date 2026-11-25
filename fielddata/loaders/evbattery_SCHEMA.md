# evbattery schema

## Standard view

Source baseline: committed audits as of d447b9eed0206f139d0a9bca6ece5fb0c8c6bc36; not a fresh full reread of paper, supplement and author code.

`fielddata.standard("evbattery", unit)` has tier `session`. It retains overlapping charging snippets as separate records. The publisher shifted and scaled timestamps, so the clock cannot establish calendar dates or guaranteed physical elapsed seconds. Processed files use `month=undated`.

Native current sign: charge negative in the released charging records; the standard view reverses it. Where GB/T 32960 has a semantic match, standard names follow its vocabulary; columns absent from a release remain absent.

| Authors' column | Our column | Conversion | Meaning and check evidence |
|---|---|---|---|
| `timestamp` | `source_time_s`, `elapsed_time_s` | Keep the publisher clock, and subtract the first clock value within each snippet | Targeted paper Section 3 reread, anonymization; [audit](../../reports/source_audit_2026-10-04/evbattery.md) and existing column table, raw step check. |
| `current` | `pack_current` | A multiplied by -1, observed native charging-negative sign | Existing column table and audit sign scan; fixed [charge period](../../reports/checks/standard_layers/charge_periods.csv). |
| `volt` | `cell_v_mean` | V unchanged, publisher-perturbed average cell voltage, not pack voltage | Targeted paper Section 3 reread; existing column table, voltage/extrema cross-check; held [round trip](../../reports/checks/standard_layers/roundtrip.csv). |
| `soc` | `soc` | Percent unchanged | Existing column table citing paper Sections 1 and 3; audit column-order check and fixed charge-period rise. |
| `max_single_volt`, `min_single_volt` | `cell_v_max`, `cell_v_min` | V unchanged | Targeted paper Section 3 reread; existing column table and audit voltage/extrema cross-check; held round trip. |
| `max_temp`, `min_temp` | `temp_max`, `temp_min` | Degrees Celsius unchanged | Targeted paper Section 3 reread; existing column table, audit column-order/range checks; held round trip. |
| `snippet`, `charge_segment`, `label`, `mileage`, `capacity` | Same names | Released metadata unchanged, including zero for an absent capacity label | Existing column table and audit shared-fleet/label checks; targeted `capacity_dataset.py` reread establishes zero as no label. **AUDIT-ONLY MEANING** for fault-report and engineers' capacity-test provenance beyond numerical label checks. |

**AUDIT-ONLY MEANING** marks inherited semantics without an independent data check of the stated provenance. Label preservation does not independently validate that provenance.

Native current polarity comes from the released charging records, not an explicit author declaration. The paper's publisher processing and capacity-label meaning are described below. No physical pack voltage, individual cell channels, calendar times or new operating-state labels are invented. The raw loader is unchanged.

Source files: battery_dataset1.tar.gz, battery_dataset2.tar.gz, battery_dataset3.tar.gz. Each tar.gz holds one pickle per charging snippet (`data/<n>.pkl`, a (128, 8) array plus a metadata dict) and a label table (`label/label.csv`: car and label). The pickles are read with the torch-free reader in `fielddata/_io/torchfree.py`, so PyTorch is not needed.

465 labeled vehicles (217, 198 and 50 per archive) with 1,278,277 snippets. One labeled car, battery_dataset3 car 545, has no snippets, so 464 vehicles carry data, as the paper states. battery_dataset3 is the same fleet as zhang2023 battery_brand2: all 49 vehicles with data in each archive are matched one to one by content under different car numbers (`reports/facts/_cache/zhang2023_evbattery_pairs.json`; 44 by identical snippets, 5 by tolerance matching), and their fault labels agree. The two releases cut that fleet into different snippets: battery_dataset3 has 176,327 snippets and zhang2023 battery_brand2 194,245, every zhang2023 charge segment of the fleet is also in battery_dataset3, and battery_dataset3 has 37 more (checked 2026-10-04).

Processing before release. The data come from EV charging stations working with the authors' group, from vehicles of three manufacturers (paper arXiv:2201.12358v3, Sec. 3). Charging records were cut into snippets of 128 samples with fixed-length sliding windows (Sec. 3, "Data format"), so snippets of one charge can overlap; do not sum snippet durations. For anonymization the publisher "perturbed and interpolated the original average voltage, current, and temperature values" and "randomly shifted and scaled the timestamps and mileages" (Sec. 3, "Data Anonymization"; Appendix C says the public release is anonymized at the data providers' request). Voltage, current and temperature are therefore not the raw measurements, and `mileage` is not in km. Time zone not stated; the arrays carry no calendar time.

`evbattery_index.csv` (next to this file) records per vehicle its archive, car id, label and snippet count. `build_index` in `_snippets.py` generates it from the release, one archive at a time (about a minute each). `systems()` reads it.

`load(unit)` takes `"<archive stem>:<car>"` and returns all of that vehicle's snippets as one long table, 128 rows per snippet. A tar.gz can only be read from the start, so loading a vehicle streams its whole archive (tens of seconds). `iter_snippets(archive)` yields `(member, array, metadata)` for every snippet and is the fast way to use a whole archive.

| column | unit | role |
|---|---|---|
| volt | V | Average cell voltage (paper Sec. 3: "The dataset only includes the average cell voltage"), perturbed and interpolated by the publisher. Measured 2026-10-04 on raw data: the snippet mean of `volt` is within 0.1 V of the snippet mean of (`max_single_volt` + `min_single_volt`) / 2 in 99.6 % or more of snippets of every archive. |
| current | A | Pack charging current, perturbed and interpolated by the publisher. Negative during charging: on raw data every non-zero value in all three archives is negative (no positive values). The paper does not state the sign in words. In battery_dataset3, 70,439 of 176,327 snippets have current 0 throughout. |
| soc | % | BMS-estimated SOC (paper Sec. 1: "estimated SOC during charging"). |
| max_single_volt, min_single_volt | V | Maximum and minimum cell voltage (paper Sec. 3). |
| max_temp, min_temp | C | Maximum and minimum cell temperature (paper Sec. 3), perturbed and interpolated by the publisher. |
| timestamp | s (nominal) | The snippet's own relative clock, not calendar time. It starts at 0 in every snippet and steps by exactly 10 (0 to 1,270) in all three archives. The paper says timestamps were randomly shifted and scaled; the 10 s step agrees with the 10 s sampling the same group states for the shared fleet (zhang2023 SI Note 2), and the charge per snippet agrees with zhang2023 within 0.1 % (median) on the shared fleet. |
| snippet | | Pickle file name within the archive. |
| label | code | Metadata string `"10"` (label 1) or `"00"` (label 0); its first character equals the label table's label for every vehicle. The label is a vehicle-level health label, 1 for a fire incident or lithium-plating report up to the collection date, copied to every snippet of the vehicle (paper Sec. 3, Sec. 4, Table 1: 31 / 1 / 16 anomaly vehicles); it carries no fault time. |
| charge_segment | | Charge number of the snippet within the vehicle (metadata "index of the snippet", paper Sec. 3). |
| mileage | encoded | Mileage randomly shifted and scaled by the publisher (paper Sec. 3); not km. |
| capacity | Ah | Capacity label from manufacturer engineers: charge stored while charging from 3.77 V to 4.05 V at 35 A (paper Sec. 3 and Sec. 4), between 24.3 and 46.2 in the release. Only some snippets are labeled (paper Table 1): 349,741 / 203,207 / 32,974 per archive on raw data, the paper's counts. Unlabeled snippets carry 0, which the authors' code treats as "no label" (`capacity_estimation/capacity_dataset.py`). A derived label, not a measurement in the snippet. |

The column order comes from the `column.pkl` shipped in the zhang2023 archives. evbattery ships none, and its released code (`DyAD/train.py`) uses the same order. The paper's Sec. 3 lists the columns in another order; on raw data column 2 lies in 0 to 100 and does not fall within a snippet in 98 % or more of snippets of every archive, and columns 5 and 6 lie between -39 and 53, so the code's order holds. `clean=True` changes nothing: no sentinel codes are documented or found.
