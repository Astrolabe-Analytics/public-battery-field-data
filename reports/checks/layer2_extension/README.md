# Layer 2 rebuild and extension check

The release status table is checkpointed after each package. The check builds or reuses every supported unit, verifies source files against committed checksums or holding snapshots, validates manifest and Parquet hashes, and compares selected rows from the standard loader with the processed copy.

Reproduce with `python scripts/checks/layer2_extension.py` (set `LIBARCHIVE` to the installed DLL for Xie and Changan on Windows). To rerun selected releases without discarding other checkpoints, add `--packages <release> [<release> ...]`. Results are in `release_status.csv`; `sequence.json` records the processing order. Blocked or unverified releases are stated in the CSV rather than reported as successful.
