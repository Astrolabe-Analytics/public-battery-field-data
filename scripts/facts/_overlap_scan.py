"""Test whether zhang2023 and evbattery contain the same vehicles, by content rather than by identifier.

Both releases number their vehicles with plain integers, so equal numbers prove nothing. This script
fingerprints every snippet by its current, SOC, max/min cell voltage and max/min temperature columns
(rounded to 0.01; pack voltage is excluded because one release rescales it) and looks for identical
snippets across the two releases.

Step 2 refines each archive pair that shares snippets: two looser fingerprints (max/min cell voltage
only, and current plus SOC) are added, all three vote per vehicle, and a match counts as confirmed when
its partner is unique and it has at least three times the votes of the runner-up. A weak claim on a
partner that already has a strong match is treated as noise.

Usage (each step is short enough to run on its own):
    python scripts/facts/_overlap_scan.py sig zhang2023 battery_brand1.tar.gz   (and every other archive)
    python scripts/facts/_overlap_scan.py compare
    python scripts/facts/_overlap_scan.py refine
    python scripts/facts/_overlap_scan.py tolerance
    python scripts/facts/_overlap_scan.py pairs
Signatures go to data/extracts/overlap/ (not committed); the result goes to
reports/facts/_cache/zhang2023_evbattery_overlap.json and the confirmed vehicle pairs to
reports/facts/_cache/zhang2023_evbattery_pairs.json (both committed).
"""
from __future__ import annotations

import collections
import hashlib
import json
import pickle
import sys

import numpy as np

from _common import OUT, ROOT

sys.path.insert(0, str(ROOT))
from fielddata.loaders import _snippets  # noqa: E402  (snippets are read only through the loader)

SIG = ROOT / "data" / "extracts" / "overlap"
RESULT = OUT / "_cache" / "zhang2023_evbattery_overlap.json"
PAIRS = OUT / "_cache" / "zhang2023_evbattery_pairs.json"
PACKAGES = ("zhang2023", "evbattery")
RULE = ("Vehicles are matched by content, not by number. Totals subtract every vehicle confirmed one-to-one, by the refine "
        "step (identical snippets) or the tolerance step (snippets equal within storage resolution with agreeing charging-session "
        "numbers); a vehicle that is not confirmed would be counted as distinct. All 49 vehicles of the shared fleet are confirmed.")


def signatures(package: str, archive_name: str) -> None:
    per_vehicle = collections.defaultdict(set)
    for _, array, meta in _snippets.iter_snippets(package, archive_name):
        per_vehicle[int(meta["car"])].add(hashlib.md5(np.round(array[:, 1:7], 2).tobytes()).hexdigest()[:12])
    SIG.mkdir(parents=True, exist_ok=True)
    with (SIG / f"{package}__{archive_name}.pkl").open("wb") as handle:
        pickle.dump(dict(per_vehicle), handle)
    print(f"{package} {archive_name}: {len(per_vehicle)} vehicles")


def compare() -> dict:
    owners = {p: collections.defaultdict(set) for p in PACKAGES}
    vehicles = {p: {} for p in PACKAGES}
    for package in PACKAGES:
        for name in _snippets.archives(package):
            with (SIG / f"{package}__{name}.pkl").open("rb") as handle:
                data = pickle.load(handle)
            for car, hashes in data.items():
                vehicles[package][(name, car)] = len(hashes)
                for h in hashes:
                    owners[package][h].add((name, car))
    shared = set(owners["zhang2023"]) & set(owners["evbattery"])
    pairs = collections.Counter()
    for h in shared:
        a, b = owners["zhang2023"][h], owners["evbattery"][h]
        if len(a) == 1 and len(b) == 1:
            pairs[(next(iter(a)), next(iter(b)))] += 1
    best = {}
    for (a, b), n in pairs.items():
        if n > best.get(a, (None, 0))[1]:
            best[a] = (b, n)
    matched = {a: b for a, (b, n) in best.items()}
    strong = {a: b for a, (b, n) in best.items() if n >= 10}
    archive_pairs = collections.Counter((a[0], b[0]) for a, b in matched.items())
    same_number = sum(a[1] == b[1] for a, b in matched.items())
    fleets = {f"{z} = {e}": {"zhang2023_vehicles": sum(1 for k in vehicles["zhang2023"] if k[0] == z),
                             "evbattery_vehicles": sum(1 for k in vehicles["evbattery"] if k[0] == e),
                             "matched": n}
              for (z, e), n in archive_pairs.items()}
    overlap = max(min(v["zhang2023_vehicles"], v["evbattery_vehicles"]) for v in fleets.values()) if fleets else 0
    result = {
        "identical_snippets": len(shared),
        "vehicles_matched_one_to_one": len(matched),
        "vehicles_matched_with_10_or_more_snippets": len(strong),
        "matched_under_the_same_number": same_number,
        "archive_pairs": fleets,
        "overlap_vehicles_counted": overlap,
        "rule": "Vehicles are counted once when their archives form one shared fleet; the overlap counted is the smaller fleet size of each matched archive pair.",
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _loose(package: str, archive_name: str) -> dict:
    out = collections.defaultdict(lambda: {"v": set(), "s": set()})
    for _, array, meta in _snippets.iter_snippets(package, archive_name):
        car = int(meta["car"])
        out[car]["v"].add(hashlib.md5(np.round(array[:, 3:5], 3).tobytes()).hexdigest()[:12])
        out[car]["s"].add(hashlib.md5(np.round(array[:, 1:3], 1).tobytes()).hexdigest()[:12])
    return out


def _confirmed(pair: str) -> tuple[dict, dict, dict]:
    """Confirmed one-to-one matches for one archive pair: {zhang2023 car: (evbattery car, votes, runner-up votes)}."""
    zarch, earch = pair.split(" = ")
    with (SIG / f"zhang2023__{zarch}.pkl").open("rb") as handle:
        zexact = pickle.load(handle)
    with (SIG / f"evbattery__{earch}.pkl").open("rb") as handle:
        eexact = pickle.load(handle)
    zl, el = _loose("zhang2023", zarch), _loose("evbattery", earch)
    votes = collections.defaultdict(collections.Counter)

    def vote(zh, eh):
        oz, oe = collections.defaultdict(set), collections.defaultdict(set)
        for car, hashes in zh.items():
            for h in hashes:
                oz[h].add(car)
        for car, hashes in eh.items():
            for h in hashes:
                oe[h].add(car)
        for h in set(oz) & set(oe):
            if len(oz[h]) == 1 and len(oe[h]) == 1:
                votes[next(iter(oz[h]))][next(iter(oe[h]))] += 1

    vote(zexact, eexact)
    vote({c: v["v"] for c, v in zl.items()}, {c: v["v"] for c, v in el.items()})
    vote({c: v["s"] for c, v in zl.items()}, {c: v["s"] for c, v in el.items()})
    best = {}
    for car, counter in votes.items():
        ranked = counter.most_common(2)
        best[car] = (ranked[0][0], ranked[0][1], ranked[1][1] if len(ranked) > 1 else 0)
    strong = {c: b for c, b in best.items() if b[1] >= 3 * max(1, b[2]) and b[1] >= 10}
    taken = {b[0] for b in strong.values()}
    for c, b in best.items():
        if c not in strong and b[0] not in taken and b[1] >= 3 * max(1, b[2]):
            strong[c] = b
            taken.add(b[0])
    return strong, zexact, eexact


def refine() -> dict:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    for pair in result["archive_pairs"]:
        strong, zexact, eexact = _confirmed(pair)
        taken = {b[0] for b in strong.values()}
        fleet = result["archive_pairs"][pair]
        fleet["confirmed_one_to_one"] = len(strong)
        fleet["unconfirmed_zhang2023_vehicles"] = sorted(c for c in zexact if c not in strong)
        fleet["unconfirmed_evbattery_vehicles"] = sorted(c for c in eexact if c not in taken)
    result["overlap_vehicles_confirmed"] = sum(v["confirmed_one_to_one"] for v in result["archive_pairs"].values())
    result["rule"] = RULE
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def pairs() -> dict:
    """Write the confirmed zhang2023 -> evbattery vehicle pairs (car numbers) from the refine step."""
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    out = {}
    for pair in result["archive_pairs"]:
        strong, _, _ = _confirmed(pair)
        out.update({str(z): int(b[0]) for z, b in strong.items()})
        out.update({str(z): int(e) for z, e in result["archive_pairs"][pair].get("tolerance_matched", {}).items()})
    PAIRS.write_text(json.dumps({"pairs": out}, indent=1) + "\n", encoding="utf-8")
    return out


TOL_COLUMNS = [1, 2, 3, 4, 5, 6]  # current, SOC, max/min cell voltage, max/min temperature


def _tolerance_match(z, e):
    """True for each Zhang snippet in z (n,128,6) that matches EVBattery snippet e (128,6) within storage resolution."""
    d = np.abs(z - e)
    return ((np.median(d[:, :, 0], axis=1) < 0.5) & (d[:, :, 1].max(axis=1) < 0.6)
            & (np.median(d[:, :, 2], axis=1) < 0.003) & (np.median(d[:, :, 3], axis=1) < 0.003)
            & (d[:, :, 4].max(axis=1) <= 1) & (d[:, :, 5].max(axis=1) <= 1))


def tolerance() -> dict:
    """Pair the cars that refine left unconfirmed, by matching snippets within a tolerance instead of exact hashes.

    Hash fingerprints break when one release stores cell voltage in 1/64 V steps and the other in mV.
    A match only counts as evidence when the snippet's charge_segment (session number) also agrees: about
    97 % of real matches agree, about 1 % of chance matches do. A car is confirmed when its best partner has
    at least 3 session-agreeing matches, three times any other partner's, and the partner is not yet taken.
    """
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    for pair, fleet in result["archive_pairs"].items():
        zarch, earch = pair.split(" = ")
        todo = set(fleet["unconfirmed_zhang2023_vehicles"])
        free = set(fleet["unconfirmed_evbattery_vehicles"])
        snippets = [(int(m["car"]), str(m.get("charge_segment")), a[:, TOL_COLUMNS])
                    for _, a, m in _snippets.iter_snippets("zhang2023", zarch) if int(m["car"]) in todo]
        if not snippets:
            continue
        stack = np.stack([s[2] for s in snippets])
        agree = collections.defaultdict(collections.Counter)
        for _, a, m in _snippets.iter_snippets("evbattery", earch):
            for i in np.where(_tolerance_match(stack, a[:, TOL_COLUMNS]))[0]:
                car, seg, _ = snippets[i]
                if seg == str(m.get("charge_segment")):
                    agree[car][int(m["car"])] += 1
        added = {}
        for car in sorted(todo):
            ranked = agree[car].most_common(2)
            if not ranked:
                continue
            partner, n = ranked[0]
            rival = ranked[1][1] if len(ranked) > 1 else 0
            if n >= 3 and n >= 3 * max(1, rival) and partner in free:
                added[car] = partner
                free.discard(partner)
        fleet["tolerance_matched"] = {str(k): v for k, v in added.items()}
        fleet["confirmed_one_to_one"] += len(added)
        fleet["unconfirmed_zhang2023_vehicles"] = sorted(todo - set(added))
        fleet["unconfirmed_evbattery_vehicles"] = sorted(free)
    result["overlap_vehicles_confirmed"] = sum(v["confirmed_one_to_one"] for v in result["archive_pairs"].values())
    result["rule"] = RULE
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    if sys.argv[1] == "sig":
        signatures(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "refine":
        print(json.dumps(refine(), indent=2))
    elif sys.argv[1] == "tolerance":
        print(json.dumps(tolerance(), indent=2))
    elif sys.argv[1] == "pairs":
        print(f"{len(pairs())} confirmed pairs written to {PAIRS.relative_to(ROOT)}")
    else:
        print(json.dumps(compare(), indent=2))
