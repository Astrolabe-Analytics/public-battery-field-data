# stanford_ev schema (candidate)

Source: Lanubile, A., Marini, G., Bosoni, P., Colombo, A., Paxton, W. and Onori, S., "Dataset - Feedback control bounds variability in large-scale electrochemical systems", Stanford Digital Repository, version 4 (2026-06-08), doi:10.25740/yx490wc6642. No paper yet. Context: the group's companion paper on what appears to be the same vehicle, arXiv:2603.29107.

## License

CC BY-NC-ND 4.0. Maintainer's decision (2026-10-13): the loader reads the original files only. No converted or derived data files from this release go into the repository or the export, and it gets no preview image. `systems()` repeats this in its `license` column.

## Files

- `Field Dataset/Charging/` (1,094 files) and `Field Dataset/Driving/` (4,322): one MATLAB v5 file per session, named by start time `yyyymmdd_hhmmss`, from 2021-09-21 23:45:39 to 2025-04-09 16:35:21.
- `Laboratory Dataset/First Laboratory Campaign/` (48 files, 5 of them empty, 0 bytes, as released) and `Second Laboratory Campaign/` (52): one file per module (`Module_01` to `Module_36`), in test folders `Additional HPPC/15 Celsius`, `25 Celsius`, `35 Celsius`, `Pack Diagnosis` and `GITT`.

Reading needs scipy (`scipy.io.loadmat`).

## Unit

One vehicle, so 1 unit. The record does not name it. The companion paper's "95 kWh battery pack from an all-electric Audi e-tron ... driven in the San Francisco Bay Area, CA, from September 2021" matches the 36 modules, 108 cell voltages and start date. But the paper says that car was driven until January 2024 and its pack then taken apart, while this release shows one pack in use to April 2025: the odometer rises without a break and the pattern of cell-voltage offsets stays the same (scripts/checks/stanford_ev_timeline.py). So the vehicle is not taken to be the paper's, and cells are counted as the 108 cell-voltage channels.

Some sessions release `Mileage_bms` as NaN (1 of 58 sampled); `mileage()` returns None for them.

## Field signals (as released)

Each signal is a struct with `data` and `t` (`time` for T_pack_bms): t is seconds from the session start, and each signal has its own rate (in one driving session: pack signals every 0.01 s, cell voltages every 0.1 s, pack temperature every 0.5 s, module temperatures every 1 s). `load(session, signal)` returns `t` and the data.

| signal | columns | meaning (from the names) |
|---|---|---|
| I_pack_bms | 1 | pack current |
| V_pack_bms | 1 | pack voltage |
| SOC_pack_bms | 1 | pack SOC |
| V_cell_bms | 108 | cell voltages (V) |
| T_module_bms | 72 | module temperatures, 2 per module (degC) |
| T_pack_bms | 1 | pack temperature (uint8) |

Each file also holds `Mileage_bms` (an integer, 4,748 in the first session and 85,815 in the last, units not stated, likely km), `Datetime_start_bms` and `Datetime_end_bms` (MATLAB datetime objects that scipy reads only as opaque, so the session start comes from the file name), and `unavailable_signals`.

## Laboratory signals

time_lab, I_module_lab, V_module_lab, V_Cell_lab (3 cells) and T_module_lab (3 sensors), one module per file. `load_lab(path)` returns them as columns.

## Cleaning

None known. `clean=True` masks nothing.
