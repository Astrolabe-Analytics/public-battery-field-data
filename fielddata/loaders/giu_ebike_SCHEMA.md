# giu_ebike schema (admitted in v1.3)

Source: Nour, J., "Real-road cell-level dataset of a 13S4P e-bike battery pack", Zenodo, published 2026-11-11, doi:10.5281/zenodo.24138446 (CC BY 4.0). Data for the paper "Low-Cost Cell-Level Monitoring of an E-Bike Battery Pack: State-of-Charge Estimation and Fault Detection from Real-Road Data" (J. A. Nour and M. H. Darweesh, German International University, Egypt), not found in print at intake (2026-11-20). The record has no code or related identifiers. Column meanings below come from the README inside the zip (`ebike-pack-dataset/README.md`), which the record description repeats in part.

Measurements: `scripts/facts/giu_ebike.py` (per-recording profile in `reports/candidates/giu_ebike/giu_ebike_profile.csv`, group 8 in `group8.txt`).

## Pack and logger (README)

- 52 Samsung INR18650-30Q cells, 13S4P, 48 V nominal, JK-BMS (JK_BD6A20S6P).
- An ESP32 reads the BMS over Bluetooth Low Energy, one line per second, plus one DS18B20 for ambient temperature.
- Recorded on 29 October and 6 to 9 November 2026, New Cairo, Egypt.
- Usable capacity from BMS cutoff (cell undervoltage protection 3.00 V) to full charge: 9.44 Ah.
- The four cells of group 8 were replaced on 6 November 2026. All files except the raw one are after the repair.
- Chemistry is not stated. The cell model is named, nothing more.

## Files (`recordings()`)

| Recording | Content (README) | Rows | UTC span (measured) |
|---|---|---|---|
| `1_capacity_test` | charge, 1 h rest, five ~25 min rides with 1 h rests until BMS cutoff, 1 h rest | 31,757 | 2026-11-06 19:20 to 11-07 04:15 |
| `2_charge_and_ride_A` | charge from cutoff to full, rest, ride A, rest | 30,853 | 2026-11-07 09:35 to 18:10 |
| `3_ride_B` | rest, ride B (noon, from mid charge), rest | 8,983 | 2026-11-08 10:00 to 12:30 |
| `4_ride_C` | rest, ride C (evening, from low charge), rest | 5,202 | 2026-11-08 16:25 to 17:52 |
| `5_charge_after_rides` | charge from 3.47 V per cell back to full, rest | 23,873 | 2026-11-08 21:19 to 11-09 03:57 |
| `raw/jk_001_before_repair` | raw log of a ride on 29 October 2026, before group 8 was replaced | 1,305 | 2026-10-29 23:15 to 23:36 |

Each cleaned file also has an overview PNG (not read by the loader).

## Cleaned files: columns (README)

| Column | Unit | Meaning |
|---|---|---|
| `time` | local time, UTC+2 | rebuilt from the logger's clock and the test log where network time was unavailable. Parsed timezone-naive, values unchanged |
| `phase` | | `charge`, `rest`, `ride1` to `ride5`, `ride_A`, `ride_B`, `ride_C`, `motor_check` |
| `source_file` | | raw logger file the line came from |
| `valid` | bool | True if the 13 cell voltages sum to the pack voltage within 0.03 V. Use only valid lines for cell voltages |
| `current_A` | A | BMS current, **positive = discharge** |
| `current_corr_A` | A | the same, with discharge current multiplied by 0.94 (the BMS reads about 6 percent high in discharge) |
| `ah_out_corr` | Ah | charge removed since the start of the file, from `current_corr_A` |
| `pack_V` | V | pack voltage reported by the BMS |
| `cell01` to `cell13` | V | parallel-group voltages (4 cells each) |
| `t_amb_C`, `t_edge_C`, `t_center_C` | degC | ambient air, pack edge and pack centre |
| `jk_soc_pct` | % | the BMS's own SOC (README: not accurate, for comparison only) |
| `jk_bal_A` | A | balancer current |

Checked: the `valid` flag matches the README's rule on every line of all five files. Valid shares: 92.0, 97.5, 91.8, 90.6 and 100 percent. Missing values are only in `t_amb_C` (59, 35, 15, 2 and 0 lines). One-second steps throughout, with two longer steps in the capacity test and no repeated timestamps.

## Raw pre-repair file

Columns: `utc_time` (ISO 8601, Z, parsed as UTC), `time_source` (`ntp` here), `uptime_ms`, `jk_age_ms`, `pack_V`, `current_A`, `charge_Ah`, `t_pack_C`, `t_amb_C`, `jk_t1_C`, `jk_t2_C`, `jk_mos_C`, `jk_soc_pct`, `jk_cap_rem_Ah`, `cell01` to `cell13`. The README defines only the cleaned files' columns. Meanings here are from the names. Current is positive in discharge here too: it correlates at 0.92 with the step in `charge_Ah` (inference). Missing values: `t_pack_C` 32 and `t_amb_C` 25 lines.

Group 8 (`cell08`), raw: it starts at 4.080 V, the highest group at full charge. Under load up to 16.07 A it falls below 2.5 V on 64 lines (about 64 s) while every other group stays at or above 3.775 V. It reads exactly 0.000 V on 2 lines. It ends the log at 3.938 V against a median of 3.976 V for the others. The loader keeps all of these values: low cell voltage can be real fault data.

Group 8 and chemistry (`scripts/checks/giu_ebike_group8.py`): before the repair group 8 sags about 21 times as much per amp as the other groups, more than any single open cell could cause, so the whole group was weak. Full charge reaches 4.17 to 4.25 V per group, so the cells are not LFP (nickel-based, NMC class, by inference).

## Cleaning

None. `clean=True` masks nothing. The README's advice to use only `valid` lines for cell voltages is left to the caller.

## Standard view

Not mapped (explicit block, v1.3 admission 2026-11-24). `fielddata.standard_systems("giu_ebike")` lists the one pack with `standard_status = "blocked"`: its cleaned recordings (local time, `current_A` positive in discharge) and its raw pre-repair log (UTC, different columns) need separate mappings, which are not yet established. Use `load()` directly. The release is not built into the processed copy.
