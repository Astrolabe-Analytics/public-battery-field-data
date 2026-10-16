# birds_cubesat schema (candidate)

Source: Jara and Lepcha, Mendeley Data, doi:10.17632/8kp25ycf63.1 (CC BY 4.0), described in Jara, Lepcha, Kim, Masui, Yamauchi, Maeda and Cho, "On-orbit electrical power system dataset of 1U CubeSat constellation", Data in Brief 45, 108697 (2022), doi:10.1016/j.dib.2022.108697 (read through Europe PMC, PMC9679683).

## Files and units

One workbook per satellite: NEPALISAT, RAAVANA, TSURU, UGUISU. One battery each, so 4 units (`fielddata.counting.CANDIDATE_RULES`). Each sheet is one high-sampling data collection over one orbit (paper: "the satellites collect the EPS data during one orbit (~92.6 min)"), named for its download date. TSURU's sheets from March to December 2021 give no year. The two January sheets say 2022, so the loader takes 2021 for the others. TSURU also has "Test1 w batt" and "Test2 wo batt", which are not downloads and which the paper does not describe. `sheets()` marks them `kind = "test"`.

| satellite | downloads | first | last | observed hours (sum of sheet spans) |
|---|---:|---|---|---:|
| NEPALISAT | 3 | 2020-11-09 | 2021-04-10 | 4.2 |
| RAAVANA | 2 | 2021-02-13 | 2021-03-11 | 3.0 |
| TSURU | 40 | 2021-03-28 | 2022-01-24 | 65.8 |
| UGUISU | 3 | 2020-10-23 | 2021-04-10 | 4.5 |

## Battery (paper Section 2 and Table 2)

Six Eneloop NiMH cells (BK-3MCCE), 3 in series and 2 in parallel. Cell rated capacity 2000 mAh and nominal 1.2 V (Table 2). The text gives "a minimum capacity of 1900 mAh per battery". Pack nominal energy on the rated basis: 3 x 1.2 V x 2 x 2.0 Ah = 14.4 Wh per satellite.

## Columns

All 50 sheets have the same 37 columns in the same order. Header spelling varies between sheets ("Time Stamp" or "Time stamp", "Tbatt raw)", "Ibatt(raw)"), so `load()` names them by position (`COLUMNS`) and changes no value:

- `time_s`: seconds from the start of the collection (paper Table 1: "the time in seconds in which the data sample was generated"). The median step is 5 s for NEPALISAT, RAAVANA and UGUISU and 10 to 11.3 s for TSURU. The paper says 90 s nominal or 10 s in fast mode.
- Five solar panels (py, px, mz, mx, pz), each with temperature, voltage and current, as a raw hexadecimal reading and a calibrated value (degC, mV, mA).
- Battery: `Vbat_raw`, `Vbat_V` (V), `Ibatt_raw`, `Ibatt_mA` (mA), `Tbatt_raw`, `Tbatt_C` (degC). TSURU raw ranges: 0 to 4.22 V, -653 to 1,200 mA, -22.7 to 24.4 degC. Current sign convention is not stated.

## Paper and data disagree

- The paper says each sample was classified as normal or anomaly. The workbooks have no label column.
- The paper says sampling is every 90 s, or 10 s in fast mode. The sheets step every 5 s or about 10 s.
- The record says the files run "since their deployment into orbit until the end of its life". Three satellites have only 2 or 3 downloads, months apart.

## Cleaning

None known. `clean=True` masks nothing.
