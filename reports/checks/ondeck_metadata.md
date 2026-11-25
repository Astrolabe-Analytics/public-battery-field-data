# On-deck metadata intake

This is an Explore-tier, metadata-only intake. Nothing was downloaded or admitted
to the collection. There are no new measured data facts, loaders or headline
totals. The registry, [screening roster](../../SCREENING.md) and private
dashboard's On deck section describe the same candidates. The public dashboard
keeps its existing visibility gate.

## Sources and limits

- **RWTH commercial fleet**, [record 979878](https://publications.rwth-aachen.de/record/979878),
  DOI 10.18154/RWTH-2024-01907. The publisher's
  [DOI deposit](https://api.datacite.org/dois/10.18154/RWTH-2024-01907)
  confirms the title, nine geriatric-care fleet EVs, field operation during
  2014 to 2016 and periodic chassis-dynamometer capacity tests. This is
  candidate SOX truth data alongside rwth-home, not yet validated capacity
  ground truth in this collection.
- Direct RWTH record and file-page requests failed or returned a browser
  challenge. Indexed publisher metadata lists
  `Electric_Vehicle_and_Battery_Data.zip` at 82.0 MB. Exact bytes and checksum
  could not be confirmed. The DOI deposit contains no rights field.
  **CC BY 4.0 was supplied at intake but is not independently confirmed.**
  The maintainer explicitly approved keeping the candidate on deck with
  license unconfirmed. The registry's license source points to the publisher
  record, not to a presumed Creative Commons license. No redistribution
  permission is asserted.
- **Cornejo/STABL**, [Zenodo record 22281621](https://zenodo.org/records/22281621),
  title *BatteryRecursiveGPs.jl*, version v0.1.0. The
  [publisher API](https://zenodo.org/api/records/22281621) confirms MIT,
  concept DOI 10.5281/zenodo.22281620 and version DOI 10.5281/zenodo.22281621.
  It lists `martincornejo/BatteryRecursiveGPs.jl-v0.1.0.zip`,
  19,516,459 bytes, MD5 `3c8b7980e24692039e9f61f83e4d780f`.
  This is a publisher reference, not verification of a local ZIP.
- The versioned author README describes a second-life field system with
  27 modules and 324 cells. These are retained as logical analysis channels,
  not a physical-cell census or an admitted count. Its file tree lists cycle
  CSVs, validation parquet logs dated 2026-01-31 and 2026-02-01, and reference
  OCV under `yuasa/data/`. The author's `yuasa/scripts/main.jl` selects
  2025-12-10T14:00:20 to 2025-12-11T02:30:20, roughly thirteen hours.
  The supplied STABL Energy MMC, 2P GS Yuasa LEV50N LMO and 20 s context
  remains explicitly unverified at this metadata-only stage. A short window
  embedded in a code release is not long-term second-life aging evidence.

## Reproduce

```console
python scripts/checks/ondeck_metadata.py
python scripts/checks/ondeck_metadata.py --saved
python scripts/make_dashboard.py --private
python -m pytest tests/test_ondeck.py tests/test_totals.py::test_dashboard_kpi_tiles_follow_totals_json tests/test_totals.py::test_public_dashboard_has_no_ondeck_until_published
```

The metadata command writes [the selected publisher metadata](ondeck_metadata.json)
and exits with an error on a mismatched title, version, license, file reference
or expected author file listing. It never fetches an archive or data file.
The saved mode needs no network. Registry/dashboard tests cover admission
separation, the unresolved RWTH license, publisher file references, roster and
dashboard presence, and preservation of the public dashboard visibility rule.

Result: the live publisher-metadata check and saved-metadata check both passed.
The private dashboard regenerated successfully. All ten selected registry and
dashboard tests passed. RWTH license, exact bytes and checksum remain
unconfirmed, rather than being silently treated as verified. The editor's test
tool did not discover tests, so the repository's pytest runner was used with
the explicit selectors above. No loader or standard-layer tests were run.
