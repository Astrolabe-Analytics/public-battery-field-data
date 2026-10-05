"""Additional measurements added 2026-09-30: chemistry inferred from cell voltage, rwth-home metadata,
xie per-device spans and channels, ku_leuven_bev spans, zhang2023 observation-hours.

Chemistry rule (applied only where the release does not name the chemistry): a lithium-iron-phosphate
cell rarely exceeds about 3.65 V and sits near 3.2 to 3.4 V over most of its range, while NMC, NCA and
LMO cells reach 4.0 to 4.2 V when full. The 99th percentile of released cell voltage decides:
below 3.70 V -> LFP, above 3.95 V -> NMC-class (NMC, NCA and LMO cannot be told apart by voltage),
otherwise undetermined. Where only pack voltage is released, the ratio of pack voltage at 80-90 percent
state of charge to 20-30 percent decides: below 1.04 -> LFP (flat curve), above 1.08 -> NMC-class.
Every inferred value is recorded with basis "derived" and this rule as its source.
"""
from __future__ import annotations

import collections
import io
import re

import numpy as np
import pandas as pd

import json

from _common import OUT, ROOT, fact
from fielddata.loaders import _bilfinger as _bilfinger_loader

OUT_CACHE = OUT / "_cache"

RULE_CELL = "scripts/facts/_extra.py chemistry rule: 99th percentile of released cell voltage (<3.70 V LFP, >3.95 V NMC-class)"
RULE_PACK = "scripts/facts/_extra.py chemistry rule: pack-voltage ratio between 80-90 and 20-30 percent SOC (<1.04 LFP, >1.08 NMC-class)"


def chemistry_from_cells(p99: float) -> str | None:
    if p99 < 3.70:
        return "LFP"
    if p99 > 3.95:
        return "NMC-class"
    return None


def chemistry_from_pack_ratio(ratio: float) -> str | None:
    if ratio < 1.04:
        return "LFP"
    if ratio > 1.08:
        return "NMC-class"
    return None


def cloverleaf(facts, script):
    # Energy is not stated anywhere checkable, so it is computed from the data: coulomb counting over the
    # largest SOC swing of the "typical day" sheet (172 s averages) gives the present capacity of one pack;
    # dividing by that sheet's SOH gives nominal capacity; times the mean pack voltage over the swing and the
    # three HV packs gives nominal energy.
    from fielddata.loaders import cloverleaf as loader
    day = loader.load("typical day")[["SOH", "SOC", "Vpack", "Ipack"]].dropna()
    t = day.index.to_series()
    ah = (day["Ipack"] * t.diff().dt.total_seconds().fillna(0) / 3600).cumsum().to_numpy()
    soc = day["SOC"].to_numpy()
    best = max(((soc[j] - soc[i], i, j) for i in range(len(soc)) for j in range(i + 10, len(soc))), key=lambda x: abs(x[0]))
    dsoc, i, j = best
    capacity = (ah[j] - ah[i]) / (dsoc / 100)
    soh = day["SOH"].iloc[0] / 100
    volts = day["Vpack"].iloc[i:j].mean()
    energy = 3 * capacity / soh * volts / 1e6
    facts["energy_mwh"] = fact(round(energy, 4), "derived", script,
        f"Computed from the data: {capacity:.1f} Ah over a {dsoc:.0f} percent SOC swing (coulomb counting, typical-day sheet), divided by SOH {soh:.2f}, times mean pack voltage {volts:.0f} V, times 3 HV packs. An 84 kWh figure used earlier, attributed to a trade-press article (pv-magazine, 21 January 2022) that was not checked, agrees within about 5 percent. Assumes the released SOC and SOH are accurate BMS estimates and that the three packs are identical; no source states the pack rating (the Zenodo record 10.5281/zenodo.6373656 description defines no columns).")
    facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from the released data")
    vmax, spans, packs = [], 0.0, 0
    for name in loader.systems().query("kind == 'pack'")["unit"]:
        frame = loader.load(name)
        packs += 1
        spans += (frame.index.max() - frame.index.min()).total_seconds() / 31557600
        vmax.extend(frame["Vcmax"].dropna().tolist())
    p99 = float(np.percentile(vmax, 99))
    chem = chemistry_from_cells(p99)
    facts["chemistry"] = fact(chem, "derived", RULE_CELL, f"Released pack-summary Vcmax, 99th percentile {p99:.3f} V over {packs} packs.") if chem else fact(None, "open", note=f"Vcmax 99th percentile {p99:.3f} V is between the rule thresholds.")
    facts["span_unit_years"] = fact(spans, "measured", script,
                                    f"First to last workbook timestamp of each HV pack sheet, summed over {packs} packs (each pack is a unit).")


def rwth_home(facts, script):
    from fielddata.loaders import rwth_home as loader
    meta = loader.metadata()
    source = "Metadata_and_Code.zip/00_Data/00_Metadata/Metadata_Systems.xlsx (released with the data)"
    counts = meta["Chemistry"].value_counts()
    # Chemistry_detail calls the six LMO systems an LMO/NMC blend, and two NMC systems high-nickel
    label = {"LMO": "LMO/NMC blend", "NMC": "NMC"}
    chem = "; ".join(f"{label.get(name, name)} ({counts[name]} systems{', two high-nickel' if name == 'NMC' else ''})" for name in sorted(counts.index))
    facts["chemistry"] = fact(chem, "stated", source + ", Chemistry_detail; https://doi.org/10.1038/s41560-024-01620-9, p. 1439 and SI Note 1")
    facts["cells_liion"] = fact(int(meta["Cell_number"].sum()), "stated", source, "Sum of Cell_number over 21 systems.")
    facts["cell_channels_measured"] = fact(None, "not_in_release", note="Monthly CSVs carry pack voltage, current, power and temperatures only.")
    systems = loader.systems()
    spans = 0.0
    for row in systems.itertuples():
        start = pd.Timestamp(row.first_month + "-01")
        end = pd.Timestamp(row.last_month + "-01") + pd.offsets.MonthEnd(1)
        spans += (end - start).total_seconds() / 31557600
    facts["span_unit_years"] = fact(spans, "measured", script, "First to last monthly file per system (from the file names), summed over 21 systems. First-to-last includes data gaps; the paper states about 106 system-years.")
    facts["files"]["note"] = (facts["files"].get("note", "") + " 1,269 monthly CSVs held vs 1,270 stated (SI Note 2, p. 3).").strip()


def ku_leuven_bev(facts, script):
    from fielddata.loaders import ku_leuven_bev as loader
    systems = loader.systems()
    span = sum(((r.last_session - r.first_session).days + 1) / 365.25 for r in systems.itertuples())
    facts["span_unit_years"] = fact(span, "measured", script, "First to last session date per vehicle, from session file names.")
    chems, per_vehicle = [], []
    for bev in systems["unit"]:
        slow = loader.load(bev, session_type="slow charging")
        first40 = slow[slow["session"].isin(sorted(slow["session"].unique())[:40])]
        frame = first40[["BattVoltage132", "RawBattCurrent132", "SOCave292"]].dropna()
        frame = frame[frame["RawBattCurrent132"].abs() < 40]
        low = frame[(frame.SOCave292 > 20) & (frame.SOCave292 <= 30)].BattVoltage132.median()
        high = frame[(frame.SOCave292 > 80) & (frame.SOCave292 <= 90)].BattVoltage132.median()
        chem = chemistry_from_pack_ratio(high / low)
        chems.append(f"{bev}: {chem or 'undetermined'} (ratio {high / low:.3f})")
        # Energy from the vehicle's own charge counter: energy charged per 100 percent SOC over slow-charging
        # sessions that span at least 40 percent SOC (median per vehicle).
        values = []
        for _, d in slow.groupby("session", sort=True):
            d = d[["SOCave292", "TotalChargeKWh3D2"]].dropna()
            if len(d) < 10:
                continue
            dsoc = d.SOCave292.iloc[-1] - d.SOCave292.iloc[0]
            dkwh = d.TotalChargeKWh3D2.iloc[-1] - d.TotalChargeKWh3D2.iloc[0]
            if dsoc >= 40 and dkwh > 0:
                values.append(dkwh / (dsoc / 100))
        if values:
            per_vehicle.append((bev, float(np.median(values)), len(values)))
    facts["chemistry"] = fact("LFP, NCA", "stated", "https://doi.org/10.1038/s41597-025-06148-5, Table 3 (p. 4) and p. 9",
        "Stated: BEV1 Tesla Model Y SR LFP, BEV2 Model Y LR NCA. The voltage-ratio rule agrees but cannot tell NCA from NMC: " + "; ".join(chems) + ".")
    facts["energy_mwh"] = fact(round((60.5 + 78.8) / 1000, 4), "stated", "https://doi.org/10.1038/s41597-025-06148-5, p. 3 and Table 3 (60.5 kWh BEV1, 78.8 kWh BEV2)",
        "Cross-check computed from the data: " + "; ".join(f"{b} {v:.1f} kWh (median of {n} slow charges spanning at least 40 percent SOC, TotalChargeKWh counter per 100 percent SOC)" for b, v, n in per_vehicle) + ".")
    facts["energy_basis"] = fact("stated", "derived", "energy_mwh uses the stated basis")
    facts["span_unit_years"]["note"] += (" BEV1 files run to 2025-05-27, past the paper's end of 2025-02-18, after a three-month gap; "
        "with the paper's periods the span is 1.55 vehicle-years (source audit 2026-10-04).")
    facts["sentinels_documented"]["note"] = "Odometer3B6 = 4294967.295 (0xFFFFFFFF x 0.001) observed in 13,498 rows, not documented; masked by clean=True."
    facts["cells_liion"] = fact(None, "not_in_release", note="Released CAN signals give pack voltage only; pack topology is not stated.")
    facts["cell_channels_measured"] = fact(None, "not_in_release", note="No individual cell-voltage signals are released.")


def xie(facts, script):
    import fielddata
    units = fielddata.systems("xie")["unit"].tolist()
    frame = fielddata.load("xie", unit=units)
    span, populated = 0.0, 0
    for _, device in frame.groupby("unit"):
        times = device.index.dropna()
        if len(times):
            span += (times.max() - times.min()).total_seconds() / 31557600
        cells = [c for c in device.columns if c.startswith("batCoreVoltage")]
        populated += int(sum(device[c].notna().any() and (device[c] > 0).any() for c in cells))
    facts["span_unit_years"] = fact(span, "measured", script, f"Sum of first-to-last dateTime over {len(units)} device files in predefinedDataset/data.")
    facts["cell_channels_measured"] = fact(populated, "measured", script, f"Cell-voltage columns with at least one positive value, summed over {len(units)} device files.")
    xie_cells(facts)


def _snippet_totals(package):
    """Aggregate the per-archive caches written by _snippet_scan.py (scanning any archive not yet cached)."""
    import json
    import _snippet_scan
    from fielddata.loaders import _snippets
    results = []
    for name in _snippets.archives(package):
        cache = _snippet_scan.CACHE / f"{package}__{name}.json"
        results.append(json.loads(cache.read_text(encoding="utf-8")) if cache.is_file() else _snippet_scan.scan(package, name))
    return results


def _snippet_facts(package, facts, script):
    results = _snippet_totals(package)
    lower = sum(r["observation_seconds_union"] for r in results) / 3600
    upper = sum(r["observation_seconds_sum"] for r in results) / 3600
    p99 = max(r["vmax_p99"] for r in results)
    chem = chemistry_from_cells(p99)
    detail = ", ".join(f"{r['archive']} {r['vmax_p99']:.3f} V" for r in results)
    facts["chemistry"] = fact(chem, "derived", RULE_CELL, f"Snippet maximum cell voltage, 99th percentile per archive: {detail}.") if chem else fact(None, "open", note=f"p99 {p99:.3f} V between thresholds.")
    facts["cell_channels_measured"] = fact(None, "not_in_release", note="Snippets carry only the maximum and minimum cell voltage, not individual cells.")
    # Units are vehicles with at least one snippet, from the loader index (fielddata/loaders/<package>_index.csv,
    # built by scanning every snippet); a labeled car with no snippets is not a released unit.
    import fielddata
    index = fielddata.systems(package)
    empty = index[index["snippets"] == 0]
    facts["units_released"] = fact(int((index["snippets"] > 0).sum()), "measured", f"fielddata/loaders/{package}_index.csv",
        f"Vehicles with at least one snippet; the label tables list {len(index)} cars, and "
        + ", ".join(f"{r.archive} car {r.car}" for r in empty.itertuples()) + " has no snippets.")
    return lower, upper


def zhang2023(facts, script):
    facts.pop("overlap_identifiers", None)  # overlap is tested by content in _overlap_scan.py and recorded on evbattery
    lower, upper = _snippet_facts("zhang2023", facts, script)
    facts["obs_hours"] = fact(lower, "measured", "scripts/facts/_snippet_scan.py (cached in reports/facts/_cache/)",
        f"Lower bound: union of snippet time ranges per vehicle and charge segment. In brand 3 snippet clocks run through the segment, so the union is exact; in brands 1 and 2 each snippet's clock restarts at zero, so overlapping snippets count once per segment. The plain sum of snippet durations is {upper:,.0f} h, an upper bound.")


def evbattery(facts, script):
    import json
    import _overlap_scan
    lower, upper = _snippet_facts("evbattery", facts, script)
    overlap = json.loads(_overlap_scan.RESULT.read_text(encoding="utf-8"))
    shared_archives = {pair.split(" = ")[1] for pair in overlap["archive_pairs"]}
    kept = [r for r in _snippet_totals("evbattery") if r["archive"] not in shared_archives]
    hours = sum(r["observation_seconds_union"] for r in kept) / 3600
    facts["overlap_identifiers"] = fact(overlap["overlap_vehicles_confirmed"], "measured", "scripts/facts/_overlap_scan.py -> reports/facts/_cache/zhang2023_evbattery_overlap.json",
        f"Content match, not vehicle numbers: {overlap['overlap_vehicles_confirmed']} vehicles confirmed one-to-one between zhang2023 battery_brand2 and evbattery battery_dataset3 (all vehicles with data in each archive; 44 by identical snippets, 5 by tolerance matching with agreeing charging-session numbers); no snippets shared between any other archives; none matched under the same number. The confirmed vehicles count once in the unit total.")
    facts["obs_hours"] = fact(hours, "measured", "scripts/facts/_snippet_scan.py (cached in reports/facts/_cache/)",
        f"Lower bound over {', '.join(r['archive'] for r in kept)}; {', '.join(sorted(shared_archives))} is left out because it is the same fleet as zhang2023 brand 2. Each snippet's clock restarts at zero, so overlapping snippets count once per charge segment. Snippet clocks step by exactly 10 in every archive. The paper (arXiv:2201.12358v3, Sec. 3) says timestamps were randomly shifted and scaled for anonymization, but on the shared fleet the charge per snippet agrees with zhang2023, whose 10 s sampling is stated (SI Note 2, p. 11), to a median ratio of 0.9994, so hours are counted at 10 s per step.")


def tumftm(facts, script):
    source = "https://doi.org/10.1016/j.etran.2025.100518, p. 3, Section 2.2 (seven vehicles, 108s2p NMC pouch cells, 58 kWh net)"
    facts["chemistry"] = fact("NMC", "stated", source)
    facts["cells_liion"] = fact(7 * 216, "derived", source + "; 7 vehicles x 216 cells")
    facts["energy_mwh"] = fact(7 * 58 / 1000, "stated", source + "; 7 vehicles x 58 kWh net")
    facts["energy_basis"] = fact("stated", "derived", "energy_mwh uses the stated basis")


def ppl(facts, script):
    source = "https://doi.org/10.1109/ACCESS.2026.3693606, Section II (20 racks x 17 modules x 14 Li-ion cells)"
    if facts["cells_liion"]["value"] in (None, ""):
        facts["cells_liion"] = fact(20 * 17 * 14, "derived", source)
    facts["cell_channels_measured"] = fact(4760, "measured", "scripts/checks/source_audit/tsukuba_tumftm_ppl/check_ppl_audit.py (RARD logs in cell_level/20180701-0731.zip, 15 Jul 2018, and 20250101_0131.zip, 15 Jan 2025, read through fielddata.loaders.ppl.cell_level_preview)",
        "Individual voltages for all 4,760 cells (238 per rack row, 20 racks), each logged every 100 s, are in the RARD logs of the publisher's cell-level share linked from the repository's Cell_Level_Data file; the annual ESS CSVs hold only system-level averages and extremes. Two days checked.")


def _monotonic_segments(soc, min_rows=200, tolerance=1.0):
    """Contiguous index ranges where SOC moves mostly one way (same rule as the earlier cao capacity check)."""
    segments, start, direction, extreme = [], 0, 0, soc[0]
    for i in range(1, len(soc)):
        step = soc[i] - soc[i - 1]
        this_dir = 1 if step > 0 else (-1 if step < 0 else 0)
        if direction == 0 and this_dir != 0:
            direction = this_dir
        elif direction != 0 and this_dir not in (0, direction):
            if (direction == 1 and soc[i] < extreme - tolerance) or (direction == -1 and soc[i] > extreme + tolerance):
                segments.append((start, i))
                start, direction, extreme = i, 0, soc[i]
        if direction == 1:
            extreme = max(extreme, soc[i])
        elif direction == -1:
            extreme = min(extreme, soc[i])
    segments.append((start, len(soc)))
    return [(a, b) for a, b in segments if b - a >= min_rows]


def cao(facts, script):
    # The release has no timestamps, but the authors state the rows are one frame every 30 s
    # (Supplementary Note S5, p. 24). With that spacing: observation-hours = rows x 30 s, and pack energy by
    # coulomb counting over long one-directional SOC runs, times mean pack voltage (sum of the series cell
    # voltages), median per vehicle. GIS is excluded because its channel layout is unresolved.
    import fielddata
    dt = 30.0
    source = "https://doi.org/10.1038/s41467-025-56832-8, Supplementary Information, Note S5, p. 24 (one frame every 30 s)"
    import time
    systems = fielddata.systems("cao")
    cache = OUT_CACHE / "cao_energy_per_vehicle.csv"  # resumable: one row per vehicle already measured
    done = pd.read_csv(cache, dtype={"vehicle": str}) if cache.is_file() else pd.DataFrame(columns=["brand", "vehicle", "rows", "kwh"])
    seen = set(zip(done["brand"], done["vehicle"].astype(str)))
    started, new_rows = time.time(), []
    for row in systems.itertuples():
        if (row.brand, str(row.vehicle)) in seen:
            continue
        if time.time() - started > 120:
            break
        if row.brand == "GIS":
            new_rows.append({"brand": "GIS", "vehicle": str(row.vehicle), "rows": len(fielddata.load("cao", brand="GIS", vehicle=row.vehicle)), "kwh": None})
            continue
        # clean=True masks the loader's documented impossible values (|current| > 1000 A, out-of-range cells)
        frame = fielddata.load("cao", brand=row.brand, vehicle=row.vehicle, names="inferred", clean=True)
        cells = [c for c in frame.columns if c.startswith("cell_v_")]
        pack_v = frame[cells].sum(axis=1).to_numpy()
        if np.nanmedian(frame[cells].to_numpy()) > 100:  # DTI cell voltages are in mV
            pack_v = pack_v / 1000
        # soc_pct is in percent for both brands (the loader converts QAS from a fraction)
        soc, current = frame["soc_pct"].to_numpy(float), frame["current_A"].to_numpy(float)
        keep = ~np.isnan(current) & ~np.isnan(soc)
        soc, current, pack_v = soc[keep], current[keep], pack_v[keep]
        values = []
        for a, b in _monotonic_segments(soc):
            dsoc = soc[b - 1] - soc[a]
            if abs(dsoc) < 20:
                continue
            ah = abs(current[a:b].sum()) * dt / 3600 / (abs(dsoc) / 100)
            values.append(ah * np.nanmean(pack_v[a:b]) / 1000)
        new_rows.append({"brand": row.brand, "vehicle": str(row.vehicle), "rows": len(frame), "kwh": float(np.median(values)) if values else None})
    if new_rows:
        done = pd.concat([done, pd.DataFrame(new_rows)], ignore_index=True)
        OUT_CACHE.mkdir(parents=True, exist_ok=True)
        done.to_csv(cache, index=False, lineterminator="\n")
    if len(done) < len(systems):
        raise RuntimeError(f"cao energy: {len(done)} of {len(systems)} vehicles measured; run again to continue")
    per_vehicle = {(r.brand, r.vehicle): r.kwh for r in done.itertuples() if r.brand != "GIS" and pd.notna(r.kwh)}
    rows_total = int(done["rows"].sum())
    facts["obs_hours"] = fact(rows_total * dt / 3600, "derived", source,
        f"All released rows (DTI, QAS and GIS) times the stated 30 s frame spacing; the release itself has no timestamps.")
    totals, parts = 0.0, []
    for brand in ("DTI", "QAS"):
        values = [v for (b, _), v in per_vehicle.items() if b == brand]
        count = int((systems["brand"] == brand).sum())
        median = float(np.median(values))
        totals += median * count
        parts.append(f"{brand} {median:.1f} kWh per vehicle (median of {len(values)} of {count} vehicles with a usable charge or discharge of at least 20 percent SOC), times {count} vehicles")
    facts["energy_mwh"] = fact(round(totals / 1000, 3), "derived", source,
        "Estimate by coulomb counting at the stated 30 s spacing, times mean pack voltage (sum of series cell voltages): " + "; ".join(parts)
        + ". GIS (41 vehicles) excluded because its channel layout is unresolved. Present usable energy, not the nameplate rating.")
    facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from the released data")


def changan(facts, script):
    import fielddata
    from fielddata.loaders import changan as loader
    counts = {}
    for unit in loader.systems()["unit"]:
        count = 0
        for rows in (200, 5000):
            head = loader.load(unit, nrows=rows)
            live = head[head["totalvoltage"] > 0]
            if len(live):
                count = int(live["batteryvoltage"].astype(str).str.count("~").max()) + 1
            if count > 1:
                break
        counts[unit] = count or None
    values = collections.Counter(counts.values())
    facts["cell_channels_measured"] = fact(sum(v for v in counts.values() if v), "measured", script,
        f"Entries in the batteryvoltage field of the first rows with a live pack voltage, per vehicle file in the split RAW_DATA archive: {dict(values)}.")
    fleet = loader.fleet()
    facts["span_unit_years"] = fact(fleet["span_days"].sum() / 365.25, "derived",
        "fielddata.loaders.changan.fleet() (data/fleet_meta.csv, per-vehicle first-to-last terminaltime, made by this collection from the raw files)",
        "About 3.25 years per vehicle, consistent with the paper's three years; not re-measured from the split archive for v1.0. "
        "Timestamps were adjusted into seconds by the publisher for privacy (SI Note 2); this assumes the adjustment preserves durations.")


def _bilfinger_vehicle_files(package):
    import fielddata
    systems = fielddata.systems(package)
    for row in systems[systems["kind"] == "vehicle"].itertuples():
        yield row.member, fielddata.load(package, unit=row.unit)


def _bilfinger(package, facts, script):
    import hashlib
    source = {
        "bilfinger2024": "https://doi.org/10.1016/j.etran.2024.100356, Sec. 3.1 and Appendix A Table 1: VW ID.3 108s2p NMC pouch (216 cells), Tesla Model 3 SR+ 106s1p LFP (106 cells)",
        "bilfinger2026": "https://doi.org/10.1016/j.etran.2026.100589, p. 3, Sec. 2.1 and p. 12, Table 1: CUPRA Born and VW ID.3 108s2p NMC pouch (216 cells each), Tesla Model 3 SR+ 106s1p LFP (106 cells)",
    }[package]
    topology = {"Tesla Model 3 SR+": 106}
    channels, spans, fingerprints = {}, {}, {}
    for name, frame in _bilfinger_vehicle_files(package):
        key = _bilfinger_loader.vehicle(name)
        if key is None:
            continue
        cells = [c for c in frame.columns if re.match(r"cell_voltage_\d+$", str(c))]
        channels[key] = max(channels.get(key, 0), len(cells))
        if cells:
            fingerprints.setdefault(key, set()).add(hashlib.md5(pd.util.hash_pandas_object(frame[sorted(cells)].round(3), index=False).values.tobytes()).hexdigest())
        if "date" in frame.columns:
            dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
            if len(dates):
                lo, hi = spans.get(key, (dates.min(), dates.max()))
                spans[key] = (min(lo, dates.min()), max(hi, dates.max()))
    keep = sorted(channels)
    facts["cells_liion"] = fact(sum(topology.get(k, 216) for k in keep), "derived", source + f"; vehicles counted: {', '.join(keep)}")
    facts["cell_channels_measured"] = fact(sum(channels[k] for k in keep), "measured", script, f"Cell-voltage columns per vehicle: {', '.join(f'{k} {channels[k]}' for k in keep)}.")
    timed = [k for k in keep if k in spans]
    facts["span_unit_years"] = fact(sum((spans[k][1] - spans[k][0]).total_seconds() / 31557600 for k in timed), "measured", script,
        f"First to last measurement date per vehicle ({', '.join(f'{k} {spans[k][0].date()} to {spans[k][1].date()}' for k in timed)}); Tesla files carry no timestamps and are left out. "
        "This is the calendar span between discrete charge tests, not continuous telemetry.")
    return fingerprints, spans, channels


def bilfinger2024(facts, script):
    _bilfinger("bilfinger2024", facts, script)
    facts["span_unit_years"]["note"] += (" Paper Table 2 (https://doi.org/10.1016/j.etran.2024.100356, p. 12) dates the measurements 2021-02-08 to 2024-05-22; "
        "the 2024 file is the paper's ID.Software 3.2 charge (59.44 kWh charged in the data, 59.40 kWh in Sec. 4.5) but is dated 2024-04-22 to 04-24 in the data.")


def bilfinger2026(facts, script):
    # The row counts all seven released vehicles. Two of them (a VW ID.3 and the Tesla) are also in bilfinger2024;
    # the overlap_* facts give what totals must subtract so that each vehicle counts once.
    first, first_spans, first_channels = _bilfinger("bilfinger2024", {k: dict(v) for k, v in facts.items()}, script)
    second, second_spans, _ = _bilfinger("bilfinger2026", facts, script)
    shared = sorted(k for k in second if k in first and first[k] & second[k])
    energy_kwh = {"Tesla Model 3 SR+": 52.5}
    doubled, parts = 0.0, []
    for key in shared:
        if key in second_spans and key in first_spans:
            (a0, a1), (b0, b1) = first_spans[key], second_spans[key]
            both = max((min(a1, b1) - max(a0, b0)).total_seconds(), 0.0) / 31557600
            doubled += both
            parts.append(f"{key} {both:.4f} years")
    note = (f"Vehicles also in bilfinger2024, shown by identical cell-voltage recordings: {', '.join(shared)}. "
            "The bilfinger2026 row counts all seven vehicles; totals subtract the shared vehicles once.")
    facts["overlap_identifiers"] = fact(len(shared), "measured", script, note)
    facts["overlap_cells_liion"] = fact(sum(106 if k == "Tesla Model 3 SR+" else 216 for k in shared), "derived", "https://doi.org/10.1016/j.etran.2024.100356, Appendix A Table 1", note)
    facts["overlap_cell_channels_measured"] = fact(sum(first_channels[k] for k in shared), "measured", script, note)
    facts["overlap_energy_mwh"] = fact(round(sum(energy_kwh.get(k, 58.0) for k in shared) / 1000, 4), "stated", "https://doi.org/10.1016/j.etran.2024.100356, vehicle descriptions (VW ID.3 58 kWh, Tesla Model 3 SR+ 52.5 kWh net)", note)
    facts["overlap_span_unit_years"] = fact(doubled, "measured", script, "Time inside both releases' date ranges for the shared vehicles: " + ("; ".join(parts) or "none") + ".")


def zhou2026(facts, script):
    import fielddata
    first, last, cells, frames = {}, {}, {}, []
    for vin in fielddata.systems("zhou2026")["unit"]:
        table = fielddata.load("zhou2026", unit=vin, columns=["TotalCells", "ChargingStatus", "TotalVoltage", "TotalCurrent", "SOC"])
        stamps = table.index.dropna()
        first[vin], last[vin] = stamps.min(), stamps.max()
        cells[vin] = int(table["TotalCells"].max())
        charge = table[table["ChargingStatus"] == 1][["vin", "TotalVoltage", "TotalCurrent", "SOC"]].copy()
        charge["t"] = charge.index
        frames.append(charge.reset_index(drop=True))
        del table
    vins = sorted(first)
    detail = "; ".join(f"{v}: {first[v]} to {last[v]}, {cells[v]} cells" for v in vins)
    facts["span_unit_years"] = fact(sum((last[v] - first[v]).total_seconds() / 31557600 for v in vins), "measured", script, f"First to last Timestamp per vin ({detail}); this is not the paper fleet.")
    facts["cell_channels_measured"] = fact(sum(cells.values()), "measured", script, "Maximum TotalCells per vin; CellVoltages carries one value per cell.")
    facts["cells_liion"] = fact(sum(cells.values()), "derived", "one cell per released cell-voltage channel (TotalCells per vin)")
    # Energy by coulomb counting over charging segments (ChargingStatus 1, no gap over 300 s) spanning at
    # least 40 percent SOC: ampere-hours per 100 percent SOC times mean pack voltage, median per vehicle.
    charge = pd.concat(frames)
    charge = charge.dropna().sort_values(["vin", "t"])
    per_vehicle = []
    for vin, g in charge.groupby("vin"):
        seg = (g["t"].diff().dt.total_seconds().fillna(1e9) > 300).cumsum()
        values = []
        for _, x in g.groupby(seg):
            dsoc = x["SOC"].iloc[-1] - x["SOC"].iloc[0]
            if len(x) < 20 or abs(dsoc) < 40:
                continue
            dt = x["t"].diff().dt.total_seconds().fillna(0).clip(upper=60)
            ah = abs((x["TotalCurrent"] * dt / 3600).sum()) / (abs(dsoc) / 100)
            values.append(ah * x["TotalVoltage"].mean() / 1000)
        if values:
            per_vehicle.append((vin, float(np.median(values)), len(values)))
    facts["energy_mwh"] = fact(round((2 * 52 + 105) / 1000, 4), "stated", "https://doi.org/10.1038/s41560-026-02131-5, SI Note 1 p. 5 and Supplementary Table 1 p. 16",
        "Nominal pack energies 52 kWh (NMC car, 1P95S, two cars) and 105 kWh (LFP bus, 1P156S). Coulomb counting on the data gives "
        + "; ".join(f"{v_} {e:.1f} kWh (median of {n} charges)" for v_, e, n in per_vehicle) + ".")
    facts["energy_basis"] = fact("stated", "derived", "energy_mwh uses the stated basis")


def m5bat_2023_04(facts, script):
    import fielddata
    span, spans = 0.0, []
    units = fielddata.systems("m5bat-2023-04")
    for name in sorted(units.loc[units["kind"] == "battery unit", "unit"] + ".csv"):
        frame = fielddata.load("m5bat-2023-04", unit=name.removesuffix(".csv"))
        t0, t1 = frame.index.min(), frame.index.max()
        del frame
        span += (t1 - t0).total_seconds() / 31557600
        spans.append(f"{name} {t0} to {t1}")
    facts["span_unit_years"] = fact(span, "measured", script, "First to last DateAndTime per battery unit CSV (BESS.csv, the grid connection point, excluded): " + "; ".join(spans) + ".")
    # Unit Pb1 (Batt1.csv, flooded OCSM lead-acid, 1,066 kWh) is the string released on its own as m5bat-pbacid (2017-2025).
    # Its April 2023 month lies inside that span, so it counts once as a unit, in energy and in time.
    report = "https://doi.org/10.18154/RWTH-2024-04895, p. 3 table (Pb1 630 kW / 1066 kWh; overall M5BAT 6.19 MW / 7.78 MWh)"
    batt1 = next(x for x in spans if x.startswith("Batt1.csv"))
    t0, t1 = [pd.Timestamp(v) for v in batt1.replace("Batt1.csv ", "").split(" to ")]
    facts["span_unit_years"] = fact(span - (t1 - t0).total_seconds() / 31557600, "measured", script,
        facts["span_unit_years"]["note"] + " Batt1 (Pb1) is subtracted because it is package m5bat-pbacid, whose span already covers April 2023.")
    facts["energy_mwh"] = fact(round(7.78 - 1.066, 3), "derived", report + "; 7.78 MWh overall stated minus Pb1's stated 1.066 MWh, which is counted under m5bat-pbacid")
    facts["energy_basis"] = fact("stated", "derived", "energy_mwh is the report's stated overall rating minus Pb1's stated rating (both stated values)")
    facts["overlap_identifiers"] = fact(1, "measured", "scripts/facts/m5bat-2023-04.py (identity check in reports/facts/_cache/m5bat_pb1_identity.json)",
        "Unit Pb1 of the M5BAT plant is the string released separately as m5bat-pbacid; the data confirm it (see the identity check). It is counted once.")
    # Cell counts from the report's wiring column (Pb1 excluded: it is counted under m5bat-pbacid)
    facts["cells_liion"] = fact(4 * 192 * 16 + 240 * 10 + 312 * 32, "derived", report.replace("(Pb1 630 kW / 1066 kWh; overall M5BAT 6.19 MW / 7.78 MWh)", "wiring: LMO 4 x 192s16p, LFP 240s10p, LTO 312s32p"))
    facts["cells_leadacid"] = fact(300 + 308 * 2 + 306, "derived", report.replace("(Pb1 630 kW / 1066 kWh; overall M5BAT 6.19 MW / 7.78 MWh)", "wiring: Pb2 300s1p, Pb3 308s2p, Pb4 306s1p"), "Pb1 (300s1p) excluded; it is counted under m5bat-pbacid.")
    facts["cell_channels_measured"] = fact(None, "not_in_release", note="Unit CSVs carry unit-level voltage, current, power and SOC only.")
    identity = _pb1_identity()
    facts["overlap_identifiers"]["note"] += f" Batt1 voltage correlates {identity['batt1_voltage_corr']:.3f} with m5bat-pbacid's string voltage on {identity['day']} (Batt2: {identity['batt2_voltage_corr']:.3f})."


def deng(facts, script):
    facts["chemistry"] = fact("NMC", "stated", 'https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles, README, section \'battery pack information update\' ("equipped with CATL NCM batteries")',
        "Stated by the data record (CATL NCM). The paper does not name it.")


def tsukuba(facts, script):
    facts["cells_leadacid"] = fact(None, "not_in_release", note="The paper gives the battery as 326 kWh rated capacity and 90 kW maximum (p. 3) but no cell count; the release has system-level signals only.")


def xie_cells(facts):
    channels = facts["cell_channels_measured"]["value"]
    facts["cells_liion"] = fact(channels, "derived", "one cell per measured cell-voltage channel in the released device files",
                                "5,241 released cell-voltage channels. The paper's 5,234 (https://doi.org/10.1016/j.xcrp.2026.103154, Table 1, p. 3) is the authors' feature-extraction count: "
                                "dataProcess.ipynb get_device_voltages keeps columns with sum >= 1,000 and std > 0, which drops 7 constant-voltage cells of device d01d1f73; "
                                "the released cell table holds 5,234 distinct cells in 5,248 rows (14 cells carry two labels).")


def _pb1_identity() -> dict:
    """Show from the data that m5bat-2023-04 Batt1 is the m5bat-pbacid string: correlate one day of voltage."""
    import fielddata
    from fielddata.loaders import m5bat_pbacid
    cache = OUT_CACHE / "m5bat_pb1_identity.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    day0, day1 = pd.Timestamp("2023-04-10", tz="UTC"), pd.Timestamp("2023-04-11", tz="UTC")
    pb = m5bat_pbacid.load(source="bms", years=[2023])[["voltage_bat_V_bms"]]
    pb = pb[(pb.index >= day0) & (pb.index < day1)]
    pb = pb[~pb.index.duplicated()]
    out = {"day": "2023-04-10 (UTC)"}
    for name in ("Batt1", "Batt2"):
        unit = fielddata.load("m5bat-2023-04", unit=name)[["U_DC_Batt"]]
        unit.index = unit.index.tz_convert("UTC")
        joined = pb.join(unit[~unit.index.duplicated()], how="inner").dropna()
        out[f"{name.lower()}_voltage_corr"] = float(np.corrcoef(joined["voltage_bat_V_bms"], joined["U_DC_Batt"])[0, 1])
    OUT_CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def li2026(facts, script):
    """Energy from the stated cell rating times the measured channel count (data over paper: 240, not 200)."""
    channels = int(float(facts["cell_channels_measured"]["value"]))
    energy = channels * 200 * 3.25 / 1_000_000
    facts["energy_mwh"] = fact(round(energy, 4), "derived",
        f"{channels} measured cell channels x 200 Ah x 3.25 V / 1,000,000; cell rating from "
        "https://doi.org/10.1016/j.xcrp.2026.103210, supplemental Table S1 (mmc1 p. 2, energy storage station column)",
        note="The paper states 200 cells, which would give 0.130 MWh; the release holds 240 cell channels, so 240 is used.")
    facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from stated configuration")
    facts["cells_liion"] = fact(channels, "derived", "one cell per measured cell channel in the release",
        note="The paper states 200 cells; the release holds 240 cell channels, and the release value is used in every total.")


def rwth_android(facts, script):
    # Energy from each device's own nominal_capacity field (Ah, per the data paper's variable table, p. 4)
    # times its median cell voltage. Where nominal_capacity is 0, the charge counter at 95 percent SOC or more,
    # scaled to 100 percent, is used instead.
    import fielddata
    total_wh, from_counter = 0.0, 0
    for unit in fielddata.systems("rwth-android")["unit"]:
        frame = fielddata.load("rwth-android", unit=unit)
        ah = float(frame["nominal_capacity"].median())
        if not ah > 0:
            full = frame[frame["state_of_charge"] >= 95]
            ah = float((full["charge_counter"] / (full["state_of_charge"] / 100)).median()) if len(full) else float("nan")
            from_counter += 1
        if ah > 0:
            total_wh += ah * float(frame["voltage_cell"].median())
    facts["energy_mwh"] = fact(round(total_wh / 1e6, 6), "derived", script,
        f"Sum over 33 devices of nominal_capacity (Ah, data paper p. 4) times median cell voltage; for {from_counter} devices without a usable nominal_capacity (7 report 0 and 3 leave it empty), the charge counter near full charge is used.")
    facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from the released data")


EXTRA = {"cloverleaf": cloverleaf, "rwth-home": rwth_home, "ku_leuven_bev": ku_leuven_bev, "xie": xie,
         "zhang2023": zhang2023, "evbattery": evbattery, "cao": cao, "tumftm": tumftm, "ppl": ppl, "changan": changan, "bilfinger2024": bilfinger2024, "bilfinger2026": bilfinger2026, "zhou2026": zhou2026, "m5bat-2023-04": m5bat_2023_04, "deng": deng, "tsukuba": tsukuba, "li2026": li2026, "rwth-android": rwth_android}


def apply(package, facts, script):
    if package in EXTRA:
        EXTRA[package](facts, script)
