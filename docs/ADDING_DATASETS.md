# Adding a dataset

How a screened release becomes a package in this repository. The v1.2 admissions (the eleven on-deck releases and bilfinger2025) followed these steps. Counting conventions are in `docs/descriptor/DESCRIPTOR.md` sections 3.4 to 3.7 and in the docstring of `fielddata/counting.py`.

1. Screen it against `SCREENING.md` and the rules in `reports/screening_decisions_2026-10-13.md`.
2. Hold the release as published, in its own folder on the data drive: `data/` (files as downloaded, archives not extracted), plus `paper/`, `record/` and `code/` where available.
3. Add the registry entry (`fielddata/registry.py`), the publisher checksums (`fielddata/reference_checksums.csv`) and a download route (`fielddata/fetch.py`), or a documented manual route.
4. Write the loader, its schema note and a test on synthetic data.
5. Add the unit rule to `fielddata/counting.py`. If some units or cells are already counted under another release, choose one home release and follow the dedup rule in that module's docstring.
6. Measure the facts (`scripts/facts/<package>.py`), then rebuild the facts table, totals, tables, figure and dashboards.

## Verification

- Verify held data from local checksums and member lists: `python -m fielddata.verify <package>` compares every held file, and every archive member that has a publisher checksum, against `fielddata/reference_checksums.csv` and any checksum file inside the archive.
- Never re-download a release to verify it. A second download proves nothing about the held copy, and it costs the host bandwidth.
- mediaTUM (TUM data server) records: the "Download all" zip is rebuilt on each request, so its own hash changes every time while its contents do not. Compare the member names and sizes (and the release's own `checksums.sha512`, where it ships one), not the zip hash. Checked 2026-10-16: two downloads of bilfinger2025's data.zip had the same members, sizes and CRCs, and differed only in the top folder's timestamp.
- A new file that is not part of the release, such as a paper or a record page, may be downloaded once. Record its SHA-256 in the package's Drive manifest (`MANIFEST.sha256`).
