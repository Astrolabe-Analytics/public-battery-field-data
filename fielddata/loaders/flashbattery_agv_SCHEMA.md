# flashbattery-agv schema

Source file: `dataset.csv`, 57,880 rows for ten AGV battery packs (`battery` FB-0 to FB-9), 2019-12-16 to 2022-02-07.

Sources: the authors' `README.adoc` shipped with the Zenodo record (field table and sample entry), and the paper (Zarfati and Bedogni, CCNC 2023, doi 10.1109/CCNC51644.2023.10060391), Table I (p. 2) and Sections IV and V (pp. 3-4).

`systems()` gives each pack's row count and first and last date. `load(unit=None)` returns the rows for one, several or all packs, indexed by `date` (a calendar day, no time of day; time zone not stated), with `battery` renamed to `unit`.

What a row is. The packs' parameters are "aggregated at the end of each operating cycle, whose start occurs as the operating mode changes" (paper p. 1). The fleet data have four modes (paper Table I: partial discharge, full charge, partial charge, balance charge). The release holds only partial-discharge observations: README.adoc, "Each entry of the dataset provides summary information of subsequent partial discharge cycles". There is no mode column. Consistent with this, `counter` mostly steps by 2 between consecutive rows of one pack (56,882 of 57,870 steps are larger than 1, median 2; raw data, checked 2026-10-04), so the other modes' observations were left out.

| column | unit | role |
|---|---|---|
| counter | - | "Monotonically increasing observation counter" (README.adoc, paper Table I), counting every operating-mode segment, charge and balance included; not a charge-cycle count (raw range 8,591 to 24,443). |
| cycletime | s | "Operating time" of the observation (README.adoc: integer, s). The paper's Table I gives the unit as minutes and the range as [1, ∞); the released values are seconds: all are multiples of 60, the maximum is 14,400 s (240 min, the span of the paper's Fig. 4 axis in minutes), and read as seconds they give average discharge currents of 2.3 to 7.5 A (5th to 95th percentile) where minutes would give 0.04 to 0.13 A. One row (FB-0, 2021-05-11, counter 18,905) has cycletime 0, outside the paper's stated range (raw data, checked 2026-10-04). |
| date | day | "Date at the beginning of the observation cycle" (README.adoc). |
| totaldischarge | Ah | "Totally cumulated discharge at the end of the observation cycle", integer (README.adoc, paper Table I) (raw range 31,620 to 87,873). |
| mintemperature, maxtemperature | °C | Minimum and maximum temperature among all cells over the observation, integer (paper Table I). README.adoc's descriptions of these two are swapped ("mintemperature: Maximum temperature among all cells"); the column names are right: maxtemperature ≥ mintemperature in every row (raw data). Raw range 10 to 48. |

The release has no voltage or current series and no cell data. `clean=True` changes nothing.

Fleet context. The paper's method is supported by "a real dataset of more than 2000 batteries provided by Flash Battery" (p. 1); the release is "a subset" of it (README.adoc, Acknowledgement; paper p. 5). The paper's Fig. 6 compares "10 batteries operating on the same application in the same location" and says one battery "underwent failure"; the sources do not say whether those are the ten released packs or which pack failed. The paper's Table II pack (400 Ah, 8S2P) is an idealised simulation example, not the released packs.

Processing and sentinels. The paper (Sec. IV, p. 3) names invalid values in the fleet data, "the reset date 1st January 2000 and the extreme temperatures of -40 °C and 215 °C", and says the data were filtered and "missing values properly imputed" before analysis. Whether the release was filtered or imputed is not stated. The release contains none of those sentinels and no missing values (dates 2019-12-16 to 2022-02-07, temperatures 10 to 48 °C; raw data, checked 2026-10-04). Imputed values, if any, cannot be identified: 8.8 percent of rows have the same totaldischarge step as the next row and 12.8 percent of consecutive rows repeat both temperatures, which integer values alone can explain.
