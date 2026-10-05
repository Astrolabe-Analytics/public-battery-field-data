# rwth-android schema

Source file: `Dataset_from_Mobile_Battery_Data_Explorer_2026-04.zip`, 33 parquet files, one per device, named by an anonymised hash. The archive is an export from the Mobile Battery Data Explorer portal, which "is updated daily" (data paper Sec. 2, p. 2). It is not the RWTH Publications section that the data paper describes ("data from 33 mobile devices for the period between the 14.01.2026 and 15.04.2026", Sec. 1, p. 2; "Data collection began on 14. January 2026", abstract): the export holds 33 devices, but its timestamps run from 2025-10-24 to 2026-03-31 (raw data, source-audit check 2026-10-04). Five devices have rows before 2026-01-14 (214,351 rows): a Pixel 5 and a Pixel 8 Pro from 2025-10-24 (1,746 and 209,116 rows) and three devices from the evening of 2026-01-13 (98 to 1,795 rows). No row is later than 2026-03-31. The data were logged by the RWTHapp, versions 2.46.0 to 2.48.1 (Sec. 1).

`systems()` gives each device's manufacturer, model, battery technology (27 Li-ion, 5 Li-poly, 1 Unknown, as reported by the phone), row count and first and last timestamp. Devices are 11 Google, 11 samsung, 5 OnePlus, 4 Xiaomi, 1 HUAWEI and 1 Sony.

`load(unit=None)` returns one, several or all devices indexed by `timestamp`, with the released columns. Timestamps are naive; the time zone is not stated.

## Columns

Units and codes are from the data paper, Table 1 (p. 4), which takes the definitions from the Android `BatteryManager` reference. The Android API itself reports millivolts and milliamperes (Schimpe 2023, Table 1, p. 3); the released values are already in V, A and Ah (measured device medians: `voltage_cell` 3.84 to 4.42 V, |`current`| 0.00 to 0.52 A, `charge_counter` 1.9 to 8.3 Ah).

| column | unit | meaning |
|---|---|---|
| timestamp | | Index, naive, zone not stated. |
| battery_technology, manufacturer, model, operating_system, os_version, android_sdk_version | | Device description as reported by the phone. |
| charge_counter | Ah | "Battery charge counter" (fuel-gauge value). |
| nominal_capacity | Ah | "Nominal battery capacity". 0 on every row of 7 devices (all Google Pixel models) and missing on every row of 3 others (two Google, one samsung); treat 0 as missing. The publisher defines no placeholder. |
| state_of_charge | % | SOC from the phone's on-board estimation, not a measurement (Schimpe 2023, Sec. 2, p. 3). |
| current | A | "Instantaneous battery current. Positive values indicate net current entering the battery from a charge source ... Definition may differ between manufacturers." See the sign note below. |
| current_avg | A | Average current, same sign definition; "the time period over which the average is computed may depend on the fuel gauge hardware". -2147.483648 (Integer.MIN_VALUE x 1e-6) on every row of 10 devices (all 5 OnePlus, 3 of 4 Xiaomi, the HUAWEI and the Sony), which do not provide it. |
| plugged | code | 1 AC, 2 USB, 4 wireless, 8 dock (0 = unplugged, not listed in Table 1). |
| temperature_cell | C | Battery temperature. |
| voltage_cell | V | Battery voltage. |
| cycle_count | | Charging cycle count reported by the OS. |
| status | code | 1 unknown, 2 charging, 3 discharging, 4 not charging, 5 full. |
| health | code | 1 unknown, 2 good, 3 overheat, 4 dead, 5 over voltage, 6 unspecified failure, 7 cold. Reported by the OS. |
| cell_id | | "Hashed cell ID". One value per file, equal to the file hash, not shared between files (measured). |

Current sign: the data paper says positive = charging, but warns the definition may differ between manufacturers. Measured on raw data with `status`: 22 devices have a positive median `current` while charging and 23 a negative one while discharging, as defined. All 5 OnePlus and all 4 Xiaomi devices report the opposite: positive while discharging, and negative while charging (one OnePlus file has no charging rows). Check the sign per device before integrating current. One Xiaomi device (2406APNFAG) reports `current_avg` with a discharging median of +9.0 A, which is not a plausible phone current.

Cells: 33, assuming one cell per device; the data paper says "Most mobile devices have a single cell" (abstract).

Cadence: not stated by the authors. The median step is 10 to 11 s on 30 devices, 17.5 s and 300 s on the two OnePlus OPD2415 tablets, and 3,600 s on one samsung (SM-M356B, 110 rows); long gaps occur (95th percentile up to 5,404 s). No data are recorded while a phone is off (Schimpe 2023, Sec. 2, p. 4, for the same kind of logging).

`clean=True` masks only the value -2147.483648 in `current`, `current_avg` and `charge_counter` (it cannot be a phone current or charge); `nominal_capacity` 0 is left as released.
