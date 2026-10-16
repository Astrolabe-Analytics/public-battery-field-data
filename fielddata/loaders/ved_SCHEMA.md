# ved schema (candidate)

Source: Oh, G., LeBlanc, D. J. and Peng, H., "Vehicle Energy Dataset (VED), A Large-Scale Dataset for Vehicle Energy Consumption Research", IEEE Transactions on Intelligent Transportation Systems 23(4) 3302-3312 (2022), doi:10.1109/TITS.2020.3035596 (arXiv:1905.02081). Data: https://github.com/gsoh/VED, Apache License 2.0. Column meanings from the repository README.

## Files

`VED/Data/`: `VED_DynamicData_Part1.7z` (22 weekly CSVs) and `VED_DynamicData_Part2.7z` (32), weeks `VED_yymmdd_week.csv` from 171101 to 181107, 3,203,555,729 bytes uncompressed. `VED_Static_Data_ICE&HEV.xlsx` and `VED_Static_Data_PHEV&EV.xlsx`. Both archives are solid (one block), so the loader extracts the weekly files once (about 20 s, `py7zr`) into `extracted/` beside the release's `data/` folder, a local copy outside the release and this repository.

## Units

Maintainer's decision (2026-10-13): load the full record, count as units the 27 vehicles of the PHEV and EV workbook (24 PHEV, 3 EV), and note the rest. `systems()` has all 384 vehicles of the two workbooks with `battery_signals` True for those 27. The 357 others (264 ICE, 93 HEV) are held but are not units.

The README says 383 vehicles (264 ICE, 92 HEV, 27 PHEV/EV). The workbooks list 384 (264, 93, 27), and all 384 appear in the weekly data. Vehicle 439, listed as an HEV ("4-GAS/ELECTRIC 2.0L"), carries HV battery signals in 9,946 of its 27,816 rows, from DayNum 241.9 (late June 2018). It is the only vehicle outside the PHEV and EV workbook with battery signals. Not counted as a unit under the rule above.

## Columns (weekly CSVs, as released)

DayNum (README: "elapsed days since a reference date. DayNum 1 = Nov, 1st, 2017, 00:00:00"), VehId, Trip (each VehId and Trip pair is unique), Timestamp(ms) (within the trip), Latitude[deg], Longitude[deg], Vehicle Speed[km/h], MAF[g/sec], Engine RPM[RPM], Absolute Load[%], OAT[DegC], Fuel Rate[L/hr], Air Conditioning Power[kW], Air Conditioning Power[Watts], Heater Power[Watts], HV Battery Current[A], HV Battery SOC[%], HV Battery Voltage[V], four fuel trims. The README lists the outside air temperature as "Outside Air Temperature[DegC]". The files name it `OAT[DegC]`.

HV battery signals (raw, all weeks): current -411.3 to 190.2 A, SOC 0 to 100.0 percent, voltage 0 to 397.9 V. Signals update at different rates, so most rows hold blanks between updates (earlier note: current 1 s, voltage 5 s, SOC 60 s, paper Table II).

## Ratings

README: "There are 3 pure EV vehicles in the dataset. All of them are 2013 Nissan Leaf with an advertised battery capacity of 24 kWh." No rating is stated for the 24 PHEVs.

## Cleaning

None known. `clean=True` masks nothing. Zero voltages and SOC may be logger defaults, and are not masked.
