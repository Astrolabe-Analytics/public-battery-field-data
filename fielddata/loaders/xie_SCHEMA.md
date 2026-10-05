# xie schema

Source file: `DataForPub.rar`. `predefinedDataset/data/` holds 271 device CSVs (the paper's pilot dataset); `predefinedDataset/processedData/` holds `predefinedFeatures.json`, `predefined_device_records.csv` and `predefined_device_cell_level.csv`; `fullDataset/` holds `fullDataset.json`, `deviceFeature.csv` and `cellFeature.csv`, features for all 131,269 devices but no time series. The record readme names the two tables `device_level_info.csv` and `cell_level_info.csv` and lists only `fullDataset.json` under `fullDataset/`; the archive's names differ. `predefinedFeatures.json` holds the full per-device features. The loader streams the RAR with libarchive (on Windows set `LIBARCHIVE` to a libarchive DLL); `members(prefix)` lists the archive members.

One device is one swappable LFP battery pack of a commercial battery-swapping service provider (paper p. 2: "battery packs designed for swapping services"). E-scooter use is implied, not stated: the paper names "BSSs for e-scooters" only as "A typical example" (p. 2). Packs have 16 to 20 cells in series (paper Table 1, p. 3).

## Labels

`systems()` lists the 271 device files with `device_label` (the code on the device's first row in the device table) and `fault_codes` (every code the table gives the device). `device_labels()` and `cell_labels()` return the two released tables as released.

Codes, from the authors' code (`dataProcess.ipynb`, "Abnormal Conditions"): 1 micro-short circuit (MSC), 2 low capacity, 3 high SOC, 4 low SOC, 5 normal. No released readme or the SI gives this mapping. The cell table's `cell_label` uses the same codes.

- Device table: 291 rows for the 271 files, every row's file released. The authors' `dataReorganization.ipynb` writes one row per fault class of a device, so 18 devices with two or three classes have one row per class (16 with two, 2 with three; class sets 1,4 nine times, 3,4 four, 1,3 two, and 1,2, 1,3,4 and 2,3,4 once each) with identical features. 188 devices are normal only and 83 carry a fault code (paper p. 3: 83 fault devices, "188 normal devices"). Devices per code, a device counted once per code: 1: 22, 2: 27, 3: 26, 4: 28.
- Cell table: 5,248 rows for 5,234 distinct cells. A cell given two classes has two rows with the same features (14 cells; pairs 1,4 ten times, 1,3 twice, 1,2 and 2,4 once). Fault cells per code: 1: 24, 2: 28, 3: 35, 4: 29. Paper Table 1 gives 26, 31, 34 and 18 for the pilot set; the release does not match these counts. For 270 of 271 devices the device codes equal the set of fault codes among their cells; device `9a5a8390…` has device code 1 only but cells with codes 1 and 4.
- Provenance: the pilot set "is labeled based on engineering expertise or on laboratory testing of recalled battery packs", and "samples are intentionally selected by considering hardware alarms, service duration, and other operational factors", so its share of faulty cells is "substantially higher than that in the full-scale dataset" (paper p. 3). Fault prevalence in these 271 devices does not reflect the fleet.
- Meaning: the authors' framework assigns "the dominant failure mode" (paper p. 11); "minor MSCs lacking significant self-discharge signatures" are grouped "into a broad low-SOC category" (p. 12). High and low SOC are SOC imbalance relative to the pack (p. 1), not cell defects.
- Full-scale dataset: "1 full day of data from a single server encompassing 131,269 unique devices"; its labels "are derived from historical records and subsequent feedback from engineers" (paper p. 3 and p. 5).

## Time series

`load(unit)` returns one or more devices indexed by `dateTime` (epoch milliseconds, parsed to UTC).

| column | unit | role |
|---|---|---|
| totalCurrent | A (inferred) | Pack current; positive = charge, negative = discharge (from the data, not documented). |
| batCoreTempCount | count | Number of temperature probes. |
| batCoreVoltage1 ... batCoreVoltage20 | mV | Cell voltages; devices have 16 to 20 cells. |
| batCoreTemp1 ... batCoreTemp5 | C (inferred) | Probe temperatures. |

Units and sign: the record readme says the files hold "timestamp and voltage readings for each cell" and does not mention current or temperature; the paper gives cell voltage in mV ("[2,500 mV, 3,630 mV]", Table 1) and no current unit or sign, and the authors' code uses only the voltages. In the data, when a rest row (|totalCurrent| <= 0.1) is followed within 120 s by a row with current between 2 and 50, the median cell voltage rises in 86 % of 382 steps; with current between -50 and -2 it falls in 95 % of 606 steps. So positive means charge. 122 of 1,857 nonzero currents exceed 100 in magnitude (minimum -4,053, maximum 1,265), implausible in A for these packs and unexplained by the sources; they are kept. Raw temperatures run 0 to 57.

Sampling: rows are cloud records of a selective-reporting protocol, "hardware-triggered uploads occurring every 10–30 s, together with hourly periodic uploads", so the signals are "inherently sparse and irregularly sampled" (paper p. 3). Measured on all 271 devices: 20,780 rows, 10 to 5,543 per device (median 29). Of 20,509 row-to-row intervals, 29.7 % are under 60 s (17.5 % between 10 and 30 s), 41.3 % between 60 s and 2 h (3.8 % between 50 and 70 min) and 28.9 % over 2 h; the pooled median is about 5 minutes, and the median of the per-device medians is 7.0 h. The rows have not been thinned below the cloud upload rate.

Time zone not stated. All rows fall between 16:00:05 UTC on 3 Oct 2024 and 15:59:19 UTC on 10 Oct 2024, which is exactly 4 to 10 Oct 2024 in UTC+8 (China Standard Time); that reading is an inference.

Cell count: 5,241 cell-voltage columns carry a positive value, against 5,234 cells in the paper (Table 1) and in the cell table. The difference is device `d01d1f73…`: it has 20 live cell columns, but seven hold one constant voltage over its 18 rows, and the authors' feature extraction (`dataProcess.ipynb`, `get_device_voltages`) keeps only columns whose sum is at least 1,000 and whose standard deviation is above 0. The authors' rule gives 5,234 cells and matches the cell table on every device.

Zeros: unused cell columns are empty in 35 devices. In 11 devices four unused cell columns are filled with 0, and device `a015793f…` has 3,428 rows with every cell at 0 and no temperature probes. There are 70,164 exact-zero cell voltages in all. 176 of 341,127 positive cell voltages lie outside the paper's 2,500 to 3,630 mV range (raw, minimum 886, maximum 3,772). `clean=True` masks exact-zero cell voltages as NaN, one value at a time.
