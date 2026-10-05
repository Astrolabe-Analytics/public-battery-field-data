# reference_checksums.csv

Publisher-supplied checksums for the held data files, one row per file, with where each value came from.
This is the "expected" side of fetch-and-verify. `verify.py` computes the "measured" side from the local
copy and compares.

Columns: package, file (relative to the package folder), algorithm, publisher_value, bytes_when_recorded,
publisher_url, provenance.

Coverage as of 2026-09-10:
- Publisher value on file: cao, xie, zhang2023, evbattery, rwth-home, m5bat-2023-04, schaeffer, li2026,
  cloverleaf (md5); tumftm (git LFS sha256).
- Added 2026-09-10 from public records: tsukuba (Figshare API), flashbattery-agv (Zenodo).
- bilfinger2024 ships checksums.sha512 inside its archive (publisher reference, zip-internal); bilfinger2026
  probably the same. verify.py to compare extracted files against it.
- Checked manually 2026-09-10: ku_leuven_bev has md5 per inner file (zip-internal, recorded);
  fei_bus (Mendeley) and m5bat-pbacid (RWTH Publications) publish no checksum, sizes consistent with ours.
  Every package now has a publisher reference recorded or a documented reason there is none.
- GitHub-hosted, reference is the commit hash, not a file checksum: deng, ppl (ppl data was on Box; only our
  own sha1 snapshot exists).
- No publisher checksum possible: zhou2026 (OneDrive), changan (company site), rwth-android (lab site).
  For these, verify.py records our own hash and marks the row "own hash, no publisher reference".

Do not hand-edit publisher_value. Add rows with a provenance line that says where the value was read and when.
