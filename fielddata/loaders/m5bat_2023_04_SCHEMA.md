# m5bat-2023-04 schema

Source file: `M5BAT_04-2023_RAW.zip` (deflate64), with `Batt1.csv` to `Batt10.csv` and `BESS.csv`. Each CSV is semicolon-separated with one row per second for April 2023, 2,592,000 rows (2023-04-01 00:00:00 to 2023-04-30 23:59:59 UTC). The columns are described in the evaluation report `Report_04-2023.pdf` (doi:10.18154/RWTH-2024-04895), "Data Explanation Table BESS" (p. 6) and "Data Explanation Table Battery unit" (p. 7). Page numbers below are the report's slide numbers.

`systems()` lists the ten battery units and `BESS`, the plant's point of interconnection, which is not a battery and is not counted as a unit. `load(unit=None)` reads one, several or all ten battery units (pass `"BESS"` explicitly for the plant file).

## Time

`DateAndTime` is UTC: the report gives its unit as "UTC Timezone ('yyyy-MM-dd HH:mm:ss')" (pp. 6 and 7). The loader localizes the index to UTC. A data check agrees: BESS `Grid_frequency` against the m5bat-pbacid frequency (whose index is UTC) over April 2023 gives r = 1.0000 at lag 0 and |r| < 0.05 at lags of 1 and 2 h. Times in the report's event list (p. 5) are partly given in MESZ (CEST, UTC+2), for example "Maintenance work between 8:00 and 16:00 MESZ".

## Units

`unit`, `abbreviation`, `technology`, `wiring` and the nominal ratings in `systems()` follow the report's p. 3 table. `BattN` is the report's unit number N. The median string voltage per file agrees with that numbering (data check: Batt1-2 about 626 V for 300 OCSM cells, Batt3 653 V for 308 OPzV cells, Batt4 642 V for 306 OPzV cells, Batt5-8 about 697 V for 192 LMO cells of 3.7 V, Batt9 788 V for 240 LFP cells of 3.2 V, Batt10 731 V for 312 LTO cells of 2.3 V).

| unit | abbreviation | technology (report p. 3) | wiring | nominal power / energy |
|---|---|---|---|---|
| Batt1 | Pb1 | lead-acid (OCSM) | 300s1p | 630 kW / 1066 kWh |
| Batt2 | Pb2 | lead-acid (OCSM) | 300s1p | 630 kW / 1066 kWh |
| Batt3 | Pb3 | lead-acid gel (OPzV) | 308s2p | 630 kW / 843 kWh |
| Batt4 | Pb4 | lead-acid gel (OPzV) | 306s1p | 522 kW / 740 kWh |
| Batt5 to Batt8 | LMO1 to LMO4 | lithium manganese oxide (LMO) | 192s16p | 630 kW / 774 kWh each |
| Batt9 | LFP | lithium iron phosphate (LFP) | 240s10p | 630 kW / 738 kWh (923 kWh) |
| Batt10 | LTO | lithium titanate oxide (LTO) | 312s32p | 630 kW / 230 kWh |

The report calls the lithium units 5 to 8 "LMO". An earlier M5BAT paper (Energies 15 (2022) 1342, doi:10.3390/en15041342, Sec. 2.1.2 and Table 2) describes the same units as a blend cell chemistry of LMO and NMC. The facts and Table 2 follow that paper and give their chemistry as LMO/NMC (source: Jacqué, K. et al., Energies 15, 1342 (2022), Sec. 2.1.2). `Batt1` is the Pb1 string, also released on its own as m5bat-pbacid. The overall plant is "6,19 MW / 7,78 MWh" (p. 3).

## Columns

Values are integers as released. They are scaled integers per the report (pp. 6-7); the loader does not rescale. Power sign: negative = charging, positive = discharging (report pp. 6-7, for `P_AC_Set`, `P_AC`, `M5BAT_P`, `FCR_P`, `SPA_ask_P`, `SPA_exec_P`). The report does not state the sign of `I_DC_Batt`. In the data, positive `I_DC_Batt` goes with positive `P_AC` (discharge) in 94 % (Batt10) to 99.95 % (Batt9) of rows with |`P_AC`| > 10 kW, so positive current is discharge (inference from the data).

Battery-unit files (report p. 7):

| column | meaning (report) | unit as released |
|---|---|---|
| `P_AC_Set` | setpoint for active power after the inverter | kW |
| `Q_AC_Set` | setpoint for reactive power after the inverter | kVAr |
| `P_AC` | active power after the inverter | kW |
| `Q_AC` | reactive power after the inverter | kVAr |
| `SOC` | state of charge, "BMS value" (a BMS estimate, not a measurement) | 0.1 % |
| `I_DC_Batt` | current measured at the battery unit | 0.1 A |
| `U_DC_Batt` | voltage measured at the battery unit | 0.1 V |
| `Mode_PQ` | inverter mode "Power output" | True/False as 1/0 |
| `Mode_Stop` | inverter mode "Stop" | 1/0 |
| `Mode_Silent` | inverter mode "Silent" | 1/0 |
| `Mode_Wait` | inverter mode "Switching" | 1/0 |
| `interpolated` | "True = Value linear interpolated" | 1/0 |

Plant file `BESS.csv` (report p. 6):

| column | meaning (report) | unit as released |
|---|---|---|
| `M5BAT_P` | active power measured at the network node (10 kV connection point) | kW |
| `M5BAT_Q` | reactive power measured at the network node | kVAr |
| `Grid_frequency` | grid frequency measured at the network node | mHz |
| `Temperature` | ambient temperature at the M5BAT site (not a battery temperature) | 0.1 °C |
| `FCR_activated` | "True = FCR activated" | 1/0 |
| `FCR_P` | active power for FCR, a calculation by the operator | kW |
| `FCR_control` | control band for FCR | kW |
| `SPA_ask_P` | request for active power for setpoint adjustment | kW |
| `SPA_exec_P` | active power for setpoint adjustment | kW |
| `SOC` | state of charge for M5BAT, "calculated" (an estimate) | % |
| `interpolated` | "True = Value linear interpolated" | 1/0 |

Raw ranges (data check, all of April): battery `SOC` 0 to 1000 (Batt4 to 690, Batt5-8 to about 873, Batt9 31 to 1000, Batt10 199 to 711); `U_DC_Batt` 5,597 (Batt2) to 8,206 (Batt9); `P_AC` within ±634 kW; BESS `Grid_frequency` 0 to 50,121 (0 only in the frequency outage of 2023-04-03, see Events; 0 is not a measurement there), `Temperature` -10 to 214, `SOC` 0 to 78.

`interpolated` is 0 in every row of all eleven files (data check), so no row in this release is flagged as linearly interpolated. The report does not say which gaps were filled. The rows are complete: every file has one row per second with no missing or repeated timestamps.

## Events (report p. 5)

- 2023-04-01: LFP (Batt9) overvoltage error; p. 8 records an LFP outage that day due to a voltage limit violation.
- 2023-04-03: maintenance between 8:00 and 16:00 MESZ (06:00 to 14:00 UTC), including the fire detection and extinguishing system; "06:33:48 till 07:11:00 no frequency measurement available due to transformer shutdown" (no zone on this line; in the data `Grid_frequency` is 0 in exactly 2,233 rows, 2023-04-03 06:33:48 to 07:11:00 UTC, so these times are UTC, i.e. 08:33 to 09:11 MESZ, inside the maintenance window). No FCR delivery that day (p. 9).
- 2023-04-08 to 2023-04-18: Pb3 (Batt3) problems with cell voltage measurement, no cell defects found; 2023-04-17 Pb3 inverter error (p. 8 dates the Pb3 outage to 18 April).
- 2023-04-28: full cycle Pb1 (Batt1). 2023-04-29: full cycle Pb3 (Batt3).

M5BAT delivered FCR 99.08 % of the time in April 2023 (p. 9). `clean=True` changes nothing.
