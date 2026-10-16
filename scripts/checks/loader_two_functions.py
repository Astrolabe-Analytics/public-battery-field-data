"""Do fielddata.systems(r) and fielddata.load(r, <unit keyword>=u) work as "the same two functions" for every release?

What it does: for each registered release, reads the loader's signatures (the first parameter of load is the unit
keyword; any other parameter without a default is an extra required argument), then makes one small real call in a
separate process with a time limit: systems(r), takes the first listed unit, and loads it through fielddata.load with
that keyword. Raw data, nothing cleaned. Releases whose one-unit load is large are run by signature only (SKIP_CALL).

Reads: every release through fielddata. Writes: reports/checks/v12/loader_two_functions.csv.

Run:
    python scripts/checks/loader_two_functions.py
"""
from __future__ import annotations

import csv
import importlib
import inspect
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata.registry import PACKAGES  # noqa: E402

OUT = ROOT / "reports" / "checks" / "v12" / "loader_two_functions.csv"
SKIP_CALL = {"changan": "one vehicle streams from a 74 GB split zip", "ppl": "one call loads years of a 67 GB release",
             "cao": "signature already needs brand and vehicle"}
UNIT_COLUMNS = ("unit", "system", "pack", "vehicle", "session", "id", "name")

CHILD = r"""
import json, sys, time
sys.path.insert(0, ROOT)
import fielddata
name, key = sys.argv[1], sys.argv[2]
s = fielddata.systems(name)
col = next((c for c in COLS if c in s.columns), s.columns[0])
u = s[col].iloc[0]
u = u.item() if hasattr(u, "item") else u
t = time.time()
try:
    d = fielddata.load(name, **{key: u})
    out = {"ok": True, "unit_column": col, "unit": str(u), "rows": int(len(d)) if hasattr(d, "__len__") else None, "seconds": round(time.time() - t, 1)}
except Exception as e:
    out = {"ok": False, "unit_column": col, "unit": str(u), "error": f"{type(e).__name__}: {str(e)[:160]}"}
print(json.dumps(out))
"""


def main() -> int:
    rows = []
    only = sys.argv[sys.argv.index("--only") + 1:] if "--only" in sys.argv else None
    timeout = 900 if only else 180  # --only reruns slow releases with a longer limit and merges them into the CSV
    for name in sorted(PACKAGES):
        if only and name not in only:
            continue
        mod = importlib.import_module("fielddata.loaders." + name.replace("-", "_"))
        params = list(inspect.signature(mod.load).parameters.values())
        key = params[0].name
        required = [p.name for p in params if p.default is inspect.Parameter.empty and p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)]
        extra = [p for p in required if p != key]
        row = {"release": name, "load_signature": str(inspect.signature(mod.load)), "unit_keyword": key,
               "extra_required": " ".join(extra), "call": ""}
        if name in SKIP_CALL:
            row["call"] = "not run: " + SKIP_CALL[name]
        else:
            code = CHILD.replace("ROOT", repr(str(ROOT))).replace("COLS", repr(UNIT_COLUMNS))
            try:
                done = subprocess.run([sys.executable, "-c", code, name, key], capture_output=True, text=True, timeout=timeout, cwd=ROOT)
                line = (done.stdout.strip().splitlines() or ["{}"])[-1]
                res = json.loads(line) if line.startswith("{") else {"ok": False, "error": done.stderr.strip().splitlines()[-1][:160] if done.stderr.strip() else f"no output, exit {done.returncode}"}
            except subprocess.TimeoutExpired:
                res = {"ok": False, "error": f"over {timeout} s"}
            row["call"] = (f"ok: systems()['{res.get('unit_column')}'][0] = {res.get('unit')}, {res.get('rows')} rows, {res.get('seconds')} s"
                           if res.get("ok") else f"failed: {res.get('error')} (unit {res.get('unit')!s} from column {res.get('unit_column')})")
        rows.append(row)
        print(f"{name:18} key={key:8} extra={row['extra_required'] or '-':14} {row['call'][:150]}", flush=True)
    if only and OUT.exists():  # merge the reruns into the earlier full run
        with OUT.open(encoding="utf-8") as f:
            earlier = {r["release"]: r for r in csv.DictReader(f)}
        earlier.update({r["release"]: r for r in rows})
        rows = [earlier[k] for k in sorted(earlier)]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
