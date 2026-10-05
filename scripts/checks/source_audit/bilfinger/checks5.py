"""Per-vehicle date spans (first to last `date`, years of 365.25 d) for bilfinger2024 and bilfinger2026 vehicle files (loader, raw). Writes nothing."""
import pandas as pd
from fielddata.loaders import bilfinger2024 as A, bilfinger2026 as B
for mod, rel in [(A, "bilfinger2024"), (B, "bilfinger2026")]:
    s = mod.systems(); s = s[s.kind == "vehicle"]
    span = {}
    for r in s.itertuples():
        d = mod.load(r.unit)
        if "date" not in d:
            span.setdefault(r.vehicle, [None, None, 0]); continue
        lo, hi, n = span.get(r.vehicle, [None, None, 0])
        lo = d.date.min() if lo is None else min(lo, d.date.min()); hi = d.date.max() if hi is None else max(hi, d.date.max())
        span[r.vehicle] = [lo, hi, n + 1]
    tot = 0
    for v, (lo, hi, n) in span.items():
        y = (hi - lo).total_seconds() / 86400 / 365.25 if lo is not None else 0.0
        tot += y
        print(rel, v, "files with date:", n, lo, hi, "years %.4f" % y)
    print(rel, "sum of per-vehicle spans %.4f years" % tot, "vehicles", len(span))
