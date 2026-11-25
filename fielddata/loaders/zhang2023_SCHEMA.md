# zhang2023 schema

## Standard view

Source baseline: committed audits as of d447b9eed0206f139d0a9bca6ece5fb0c8c6bc36; not a fresh full reread of paper, supplement and author code.

`fielddata.standard("zhang2023", unit)` has tier `session`, because the vehicle's table is a collection of potentially overlapping charging snippets, not a continuous trajectory. Time is relative because the publisher masked calendar timestamps. Files use `month=undated`.

Native current sign: charge negative in the released charging records; the standard view reverses it. Where GB/T 32960 has a semantic match, standard names follow its vocabulary; columns absent from a release remain absent.

| Authors' column | Our column | Conversion | Meaning and check evidence |
|---|---|---|---|
| `timestamp` | `source_time_s`, `elapsed_time_s` | Keep the publisher clock, and subtract the first clock value in each snippet for elapsed time | Targeted SI Note 2 reread, p. 11; [audit](../../reports/source_audit_2026-10-04/zhang2023.md) and existing column table, raw step check. |
| `current` | `pack_current` | A multiplied by -1, observed native charging-negative sign | Existing column table and audit sign scan; fixed [charge period](../../reports/checks/standard_layers/charge_periods.csv). |
| `soc` | `soc` | Percent unchanged | Targeted paper Fig. 2 reread; existing column table; fixed charge-period rise and held [round trip](../../reports/checks/standard_layers/roundtrip.csv). |
| `max_single_volt`, `min_single_volt` | `cell_v_max`, `cell_v_min` | V unchanged | Existing column table citing SI Note 2; audit [shared-fleet checks](../../scripts/checks/source_audit/evbattery_zhang2023/analyze.py); held round trip. |
| `max_temp`, `min_temp` | `temp_max`, `temp_min` | Degrees Celsius unchanged | Targeted paper Fig. 2 reread; existing column table and audit column-order/range checks; held round trip. |
| `volt` | `source__volt` | Publisher encoding unchanged, never called physical pack voltage | Targeted SI Note 2 reread; audit per-brand scaling checks and existing column table. |
| `snippet`, `charge_segment`, `label`, `mileage` | Same names | Released identifiers, labels and encoded mileage unchanged | Existing column table and audit shared-fleet/label checks. **AUDIT-ONLY MEANING** for fault-report provenance and the interpretation of masked charging/mileage metadata beyond those checks. |

**AUDIT-ONLY MEANING** marks inherited semantics not independently established by a data check. Preservation of a label is not validation of its clinical or engineering provenance.

Native charging polarity is observed in the released charging snippets, not stated by the authors. The source details below explain why `volt` cannot be decoded to physical volts. The paper's Methods calls its voltage response average voltage while SI Note 2 describes total voltage before anonymization. Neither interpretation licenses use of the encoded released column as pack volts. No cell IDs, individual cell channels, dates or new event labels are invented. The raw loader is unchanged.

Source files: battery_brand1.tar.gz, battery_brand2.tar.gz, battery_brand3.tar.gz. Each tar.gz holds one pickle per charging snippet (a (128, 8) array plus a metadata dict), a `column.pkl` with the column names, and label tables of car and label. In brand3 the snippets are under `data/` with one table `label/all_label.csv`; in brands 1 and 2 they are split into `train/` and `test/` with `label/train_label.csv` and `label/test_label.csv` (the authors' train/test split; the loader reads both). brand2's `label/` folder also ships a small script, `label_carplus200.py`, that subtracts 800 from the car numbers in both tables, so the released car numbers (201 to 250, matching the snippet metadata) are not the authors' original ones. The pickles are read with the torch-free reader in `fielddata/_io/torchfree.py`, so PyTorch is not needed.

348 labeled vehicles (198, 50 and 100 per archive) with 700,582 snippets (476,739, 194,245 and 29,598 per archive). One labeled car, battery_brand2 car 230, has no snippets, so 347 vehicles carry data, as the paper states. Each archive is one vehicle model (paper p. 2: "Vehicles in each of our three released datasets are of the same make"; SI Note 2). The archives match the paper's aliases by vehicle count, abnormal count and snippet count (SI Note 2, p. 11): brand1 = Dahu (198 EVs, 30 abnormal, about 470,000 snippets), brand2 = Socea (49 EVs, 16 abnormal, about 195,000), brand3 = Naobop (100 EVs, 9 abnormal, about 29,000). battery_brand2 is the same fleet as evbattery battery_dataset3: all 49 vehicles with data are matched one to one by content under different car numbers (`reports/facts/_cache/zhang2023_evbattery_pairs.json`; 44 by identical snippets, 5 by tolerance matching), and their fault labels agree. The two releases cut that fleet into different snippets (194,245 here, 176,327 in evbattery).

Processing before release. The release is processed data; the raw EV data are not public (paper, Data availability, p. 7). "The abnormal data at or near battery failures are removed so that successful predictive models need to identify battery problems at least days ahead" (paper, Results, p. 3), so abnormal vehicles contain only pre-failure history. Each snippet has 128 samples taken every 10 seconds, and each is "coupled with masked metadata on vehicle number, charging number, encoded mileage and timestamp" (SI Note 2, p. 11). Time zone not stated; the arrays carry no calendar time.

`zhang2023_index.csv` (next to this file) records per vehicle its archive, car id, label and snippet count. `build_index` in `_snippets.py` generates it from the release, one archive at a time (about a minute each). `systems()` reads it.

`load(unit)` takes `"<archive stem>:<car>"` and returns all of that vehicle's snippets as one long table, 128 rows per snippet. A tar.gz can only be read from the start, so loading a vehicle streams its whole archive (tens of seconds). `iter_snippets(archive)` yields `(member, array, metadata)` for every snippet and is the fast way to use a whole archive.

| column | unit | role |
|---|---|---|
| volt | none | Total (pack) voltage, "scaled and shifted by a random float to normalize the value and to remove private information" (SI Note 2, p. 11). Not a physical voltage; use `max_single_volt` and `min_single_volt` for cell voltage. Measured 2026-10-04 on raw data, the transform differs by archive: in brand1 each snippet is standardized on its own (mean 0 in every snippet, standard deviation 1 in each of the first 3,000 snippets checked); in brand2 it is one affine map for the whole archive, `volt` = 0.960 x (evbattery average cell voltage) - 0.499 on the shared fleet (residual standard deviation 0.004); in brand3 `volt` is about 10.7 times the mean of the cell-voltage extremes in every vehicle (per-vehicle factor 10.56 to 10.98, offset near 0). |
| current | A | Pack charging current. Sign not stated by the authors. On raw data charging current is negative: brand3 has only negative values, brand1 has 11,189 positive values among 61 million (0.02 %), brand2 has 5 positive values. In brand2, 70,604 of 194,245 snippets have current 0 throughout. |
| soc | % | BMS SOC (SI Note 2 lists state-of-charge; paper p. 2: models use observational data from existing battery management systems). |
| max_single_volt, min_single_volt | V | Maximum and minimum cell voltage (SI Note 2). |
| max_temp, min_temp | C | Maximum and minimum of the pack's temperature sensors (SI Note 2: "minimum sensor temperature, maximum sensor temperature"). |
| timestamp | s | Relative clock within the snippet; 128 samples at 10 s (SI Note 2). On raw data every step is exactly 10 in all three archives. In brands 1 and 2 the clock starts at 0 in every snippet; in brand 3 it runs on through the charge segment. The calendar timestamp is masked (SI Note 2). |
| snippet | | Pickle file name within the archive. |
| label | code | Metadata string `"10"` (label 1) or `"00"` (label 0); its first character equals the label table's label for every vehicle. The label is a vehicle-level fault label: 1 when a driver's report was confirmed by engineers on lithium plating, low electric range, over-high temperature or unexpected voltage changes (paper p. 2), copied to every snippet of the vehicle; labels are sparse and made at the vehicle level (paper p. 4), with no fault time. Label tables give 30 / 16 / 9 label-1 vehicles per archive. |
| charge_segment | | Masked charging number (SI Note 2). |
| mileage | encoded | Publisher-encoded mileage (SI Note 2), not km. On the shared fleet it is not a constant multiple of evbattery's mileage. |

The column order comes from the `column.pkl` shipped in the zhang2023 archives. evbattery ships none, and its released code (`DyAD/train.py`) uses the same order. `clean=True` changes nothing: no sentinel codes are documented or found.
