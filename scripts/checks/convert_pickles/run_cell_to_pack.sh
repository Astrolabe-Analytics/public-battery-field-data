#!/usr/bin/env bash
# Convert cell_to_pack's pickled pandas files to Parquet in a throwaway venv (maintainer's decision, 2026-10-13).
# Same environment and safeguards as run_tongji.sh. One run per zip (20 zips). Output in converted/ beside data/,
# outside git and the export. Manifest with input and output SHA-256: reports/candidates/cell_to_pack/pickle_conversion.csv.
# Rerunning skips members already converted without error.
set -e
ENV=${PICKLE_ENV:-/c/t/pickle-env}
[ -x "$ENV/Scripts/python.exe" ] || { python -m venv "$ENV"; "$ENV/Scripts/python.exe" -m pip install -q pandas pyarrow; }
RELEASE=$(python -c "from fielddata import fetch; print(fetch.plan_package('cell_to_pack').destination)")
for ZIP in "$RELEASE"/*.zip; do
  NAME=$(basename "$ZIP" .zip)
  echo "$NAME"
  "$ENV/Scripts/python.exe" "$(dirname "$0")/convert.py" --zip "$ZIP" --out "$RELEASE/../converted/$NAME" \
    --manifest reports/candidates/cell_to_pack/pickle_conversion.csv
done
