# changan schema

Source files: `raw/RAW_DATA.z01` and `raw/RAW_DATA.zip`, a two-volume split zip of 72.3 GB as served.

Manual download: about 74 GB in decimal units (`RAW_DATA.z01` 51,539,607,552 bytes, `RAW_DATA.zip` 22,766,768,603 bytes, from the reference verify log). Save both files, unopened, in a subfolder named `raw` inside the release's `data` folder (`python -m fielddata.fetch changan` prints the full path), then run `python -m fielddata.verify changan`. Its members are `RAW_DATA/vinN.rar`, one RAR per vehicle for 300 vehicles, each holding one CSV. The loader reads the split zip's central directory and streams one vehicle through inflate, un-RAR and CSV parsing, so nothing is unpacked to disk. It needs libarchive (`libarchive-c`).

`systems()` lists the 300 vehicle members with the volume and offset where each starts. `fleet()` returns `fleet_meta.csv`, a per-vehicle summary made by this collection from the raw files, not by the publisher.

`load(unit, nrows=None, chunksize=None)` returns one vehicle's telemetry as released, sampled at 0.1 Hz (paper p. 4: "a sampling frequency of 0.1 Hz"); with `chunksize` it returns an iterator of chunks. A vehicle is up to about 3 GB of text.

Column meanings below follow Supplementary Table 2 of the paper's Supplementary Information (SI Note 2).

| column | unit | role |
|---|---|---|
| terminaltime | s | Relative time stamp in seconds; the publisher adjusted the timestamps "into seconds for privacy protection" (SI Note 2), so the release carries no calendar date and no time zone. The authors state "The raw data is randomly ordered" (SI Note 2, step 2); sort by terminaltime before use. |
| soc | % | BMS-reported state of charge, an estimate. The authors document BMS SOC errors that grow with ageing because "the BMS cannot timely update battery capacity information" (paper p. 5, "SOC estimation error of BMS"; SI Note 2, step 5). |
| speed | km/h | Vehicle driving speed. |
| totalodometer | km | Accumulated travelling mileage. |
| chargestatus | code | Charging state: 1 = charging, 3 = discharging (SI Table 2). Codes 0, 4 and 255 and missing values also occur and are not documented. In vin1 to vin3 (raw data): with code 1, 99.9 percent of rows have negative current; with code 3, 76 to 83 percent have positive current and the rest negative, as expected for regenerative braking while driving (paper p. 4); code 4 (about 0.1 to 2.5 percent of rows) occurs at rest with soc near 97 to 100 percent and small positive current; codes 0 and 255 are the 0 V rows described below. |
| totalvoltage | V | Pack voltage. |
| totalcurrent | A | Pack current, positive when discharging and negative when charging (SI Table 2: "+ for discharging and – for charging"). |
| minvoltagebattery, maxvoltagebattery | V | Minimum and maximum cell voltage. |
| mintemperaturevalue, maxtemperaturevalue | C | Minimum and maximum temperature. |
| batteryvoltage | V | `~`-separated cell voltages. The pack is "96 cells connected in series" with a rated capacity of 155 Ah (paper p. 4); whether a series position holds parallel cells is not stated. Every present string has 96 entries; in 3.8 percent of vin1 rows (143,719 of 3,810,614), 6.8 percent of vin2 and 6.0 percent of vin3 the string is missing altogether, together with probetemperatures (raw data). No present string has an empty entry. Values are in V (vin1 median 3.900 V over all entries). |
| probetemperatures | C | `~`-separated "Temperature collected from sensors" (SI Table 2), at 1 °C resolution (authors' response to Reviewer 2, comment 7, Transparent Peer Review file). The number of probes per pack is not stated; every present string in vin1 has 32 entries (raw data). |

`expand(frame, column)` splits a `~`-separated column into numeric columns.

Sentinels found in the data (raw data, vin1 to vin3 in full, checked 2026-10-04; neither code is documented by the publisher). Rows with a pack voltage of exactly 0 V are of two kinds. Rows with chargestatus 0 have the whole BMS block at zero (soc, current, pack voltage, cell-voltage extremes, maximum temperature) while speed and odometer can carry values: 0 in vin1, 169 in vin2, 421 in vin3. Rows with chargestatus 255 have totalvoltage and cell-voltage extremes 0, totalcurrent exactly -1000 A, soc 4 and maximum temperature -40 °C: 51 in vin1, 55 in vin2, 22 in vin3. A current of -1000 A occurs in no other row of these three vehicles. One further vin2 row (chargestatus 3) has 0 V with soc 99. `clean=True` masks exact-zero `totalvoltage`, `minvoltagebattery` and `maxvoltagebattery`, and `totalcurrent` of exactly -1000, one value at a time. SOC, current and temperature can legitimately be 0 and are left as released; the -40 °C and soc 4 in the chargestatus 255 rows are also left as released.

Gaps and data quality stated by the authors (paper pp. 4-5, "Limited data quality"; SI Note 2, step 4): the field data "lacks idle-time records as the BMS stops recording when the EVs are turned off", so gaps in terminaltime include periods when the vehicle was off; the battery voltage "may suddenly drop to 0" although the battery has no fault (we take the 0 V rows above to be these, which is our inference); single sensors can be missing within a row (in vin1 no present `~` string has an empty entry; what is missing there is the whole batteryvoltage and probetemperatures pair, see the table); and whole data frames can be missing while the vehicle drives or charges. SI Note 2 lists sorting, splitting the `~` columns and interpolating single missing sensor values as preprocessing that users of the raw data must do themselves, so the released files have not had those steps applied.
