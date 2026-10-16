#!/usr/bin/env bash
# Convert tongji_rest's pickled pandas files to Parquet in a throwaway venv (maintainer's decision, 2026-10-13).
# The venv is separate from the project's .venv, uses network only to install pandas and pyarrow, and convert.py
# blocks network connections before unpickling. Output stays in the local data folder (converted/ beside data/),
# outside git and the export. The manifest with input and output SHA-256 is written to reports/candidates/tongji_rest/.
set -e
ENV=${PICKLE_ENV:-/c/t/pickle-env}
[ -x "$ENV/Scripts/python.exe" ] || { python -m venv "$ENV"; "$ENV/Scripts/python.exe" -m pip install -q pandas pyarrow; }
RELEASE=$(python -c "from fielddata import fetch; print(fetch.plan_package('tongji_rest').destination)")
"$ENV/Scripts/python.exe" "$(dirname "$0")/convert.py" --zip "$RELEASE/data.zip" --out "$RELEASE/../converted" \
  --manifest reports/candidates/tongji_rest/pickle_conversion.csv --prefix data/
