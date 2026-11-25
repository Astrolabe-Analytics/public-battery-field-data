# Standard view and processed copy

The standard view is a second entry point. `fielddata.load` and each release's raw loader retain their existing behavior. Every registered release has a `standard_systems` inventory and a release-specific section in its loader's `_SCHEMA.md` note. Supported units are mapped only where a source interpretation is established; unresolved, non-field or non-time-series units are explicitly blocked or retained under source names. Cao GIS, rise_conbat and cell_to_pack remain blocked.

```python
import fielddata

units = fielddata.standard_systems("cao")
frame = fielddata.standard("cao", "QAS:0")
frame = fielddata.standard("schaeffer", "3")
frame = fielddata.standard("ppl", "E_W_Brown_BESS", years=[2022])
```

## Contract

Current is in A, **charge positive and discharge negative**. Voltage is in V, SOC in percent and temperature in degrees Celsius. `ac_power` is kW, also charge positive, and is not DC pack power. Names use the GB/T 32960 signal vocabulary where there is a physical match, rather than claiming that this DataFrame is the GB/T binary wire format. In particular, `pack_voltage`, `pack_current`, `soc`, `cell_v_max`, `cell_v_min`, `temp_max` and `temp_min` correspond to its total voltage, total current, SOC and extreme-value signals.

The usual GB/T 32960 current convention is discharge positive and charge negative, opposite to this project's approved convention. The [official 2016 catalogue entry](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=674DE45C0AD3DE2CD75B9C4CD8ED57C1) marks that edition withdrawn and no longer supplies readable text. The polarity description is supported by [public GB/T commentary](https://wenku.baidu.com/view/a66215d4730abb68a98271fe910ef12d2af9a9d8.html), not a newly checked official clause. This mapping is not a certification of GB/T compliance.

No missing measurement is filled, inferred from another signal, resampled or gap-filled. Extrema are mapped only where released, not computed from individual cells. `cell_v_001` and `temp_001` identify released sensor positions. Additional author columns remain as `source__<author name>`. Snippet identifiers, labels, charging numbers, encoded mileage and capacity labels keep their existing names. These labels are not newly inferred events.

`unit` is the release-local unit identifier, not a deduplicated cross-release identity. Existing counting and overlap rules are unchanged. `data_tier` is `per-cell`, `max-min`, `pack-only` or `session`. Snippet and session-oriented releases retain `session` even where their unit inventory identifies a vehicle. PPL's tier varies by annual schema, from max-min to pack-only. Its separate cell-level share is outside this standard view. Cao GIS remains explicitly blocked with an unverified tier rather than a guessed classification.

PPL's standard view converts each annual input separately before concatenation, as the builder does. Its row tags therefore retain each input schema's tier, even in an all-year view. Tier is not inferred from a missing value or a timestamp. A mixed-tier frame has a `data_tiers` list in its attributes instead of a misleading single `data_tier` attribute.

Standard views default to raw values after documented conversion. `clean=True` explicitly requests the existing loader's cleaning. Raw sentinel values are otherwise kept and can change numerically under unit/sign conversion. Cao's existing inferred-name loader preserves its documented SOC sentinel codes when converting fractions to percent.

## Time

Calendar `time` preserves the source's basis. Xie and Aitio use released UNIX epochs, parsed as UTC. Schaeffer and PPL use timezone-naive wall clocks because their sources give no timezone. Beijing EV, Tongji, Shenzhen, Bilfinger and Zhou timestamps also remain timezone-naive where the source gives no zone. The unsupported UTC tag applied by the raw PPL loader is removed without shifting wall-clock values.

Cao has no released timestamps. Its `frame_index` preserves row position, and `elapsed_time_s` is frame index times the paper's assumed frame spacing. This is not measured observation time and must not be used to infer gaps.

Zhang and EVBattery retain `source_time_s` as the publisher's relative clock. `elapsed_time_s` subtracts the first timestamp within each snippet. A snippet is a separate record and overlapping snippets remain separate. Timestamp masking, and EVBattery's reported shifting/scaling, prohibit recovery of calendar dates or an assumption of independent, nonoverlapping observation time.

For Stanford, `iter_standard("stanford_ev", "EV1", signal="V_cell_bms")` streams one selected signal per session. Signals have different sampling rates and must not be aligned by row position. The processed builder currently stores the default `V_pack_bms` signal; use the signal-specific iterator when another channel is needed. Session filenames provide local start times, and the released `t` values provide seconds from that start; no timezone is assigned.

Changan, PNNL/EPRI and CubeSat records retain their released relative time in seconds where available. Li 2026 preserves the publisher's sample index because no sample interval is stated. Undated sources remain in `month=undated`; no calendar dates or sampling intervals are invented.

## Streaming and conversion of existing loader batches

These interfaces read only and never write released files or processed copies. Exceptions during streaming are raised when the iterator is consumed.

```python
# One Schaeffer source-order pass, not the timestamp-sorted whole-system view.
for frame in fielddata.standard("schaeffer", "3", chunksize=250_000):
    consume(frame)
# Equivalent explicit streaming entry point.
for frame in fielddata.iter_standard("schaeffer", "3", chunksize=250_000):
    consume(frame)

# One archive pass across all vehicles, yielding one complete snippet per frame.
for frame in fielddata.iter_standard("zhang2023", archive="battery_brand1.tar.gz"):
    consume(frame)
for frame in fielddata.iter_standard("evbattery", archive="battery_dataset1.tar.gz"):
    consume(frame)
for frame in fielddata.iter_standard("stanford_ev", "EV1", signal="V_cell_bms"):
    consume(frame)

# One Xie raw-loader call and RAR scan for the selected units.
frame = fielddata.standard("xie", ["device_id_a", "device_id_b"])

# Convert an already loaded batch without additional I/O.
raw = fielddata.load("xie", unit=["device_id_a", "device_id_b"])
for unit, batch in raw.groupby("unit", sort=False):
    frame = fielddata.standardize("xie", unit, batch)
    consume(frame)
```

`standardize(package_id, unit, raw)` uses exactly the standard view's mapping and never mutates its input. Pass one unit only. A conflicting `unit` column raises an error rather than silently relabeling rows. Xie bulk views preserve requested unit order and each unit's raw-loader row order. They are a bulk read, not a bounded-memory stream.

For Schaeffer, existing raw chunks can be passed directly to `standardize`. For PPL, convert each annual loader frame separately before concatenation, not an all-year union frame. For Cao, pass a complete inferred-name `vin_2` unit frame, not a row slice, because frame indices start at zero. For snippet releases, use complete snippets, not slices that would reset elapsed time mid-snippet. The archive iterator ensures this boundary and retains vehicle, snippet and charging-segment identities. Its `chunksize` does not split or combine snippets, each yielded frame is one complete snippet. Stanford's iterator yields one selected signal per field session because the source signals have different rates. `clean` follows existing loaders, including no-op cleaning for these snippet releases.

The API addition changes the conservative producing-code fingerprint. Previously built processed copies therefore require the normal rebuild before processed reads will accept them. This streaming follow-up does not rewrite SSD copies. Consumers can use these read-only standard interfaces immediately, independently of the processed cache.

## Processed storage

```console
python -m fielddata.processed cao schaeffer ppl xie zhang2023 evbattery aitio
python -m fielddata.processed RELEASE
python -m fielddata.processed cao --unit QAS:0
```

The destination is `<data root>/_processed/<release>/unit=<escaped id>/month=<YYYY-MM or undated>/`. The recipe never downloads data. On Windows, Xie needs the existing libarchive DLL configured with `LIBARCHIVE`, as described by its raw loader.

The builder streams Schaeffer CSV chunks, snippets by archive, Changan batches, RWTH Home month partitions, TUM FTM Parquet batches, Zhou partitions and Stanford sessions rather than rescanning whole releases for each unit. A global row budget bounds snippet buffering. PPL annual schemas are written separately, so an absent annual channel is absent from that part's Parquet schema. A combined pandas read across epochs naturally takes the union of columns, as the raw loader does.

Each unit manifest records the Git revision, a content fingerprint of producing Python code and schema notes, format version, pandas version, source sizes and SHA-256 checksums, and each part's columns, time basis, row count and output checksum. The source checksum is freshly compared against publisher references or committed holding hashes before every build. Unknown checksums are errors, not successful verification. The builder checks for source changes during conversion.

Completed manifests are replaced only after that unit is fully written. Restart skips only verified completed units. A killed run may leave unreferenced parts, which are not read and are removed on a successful rebuild of that unit. Known GIS blocks and label-only empty units are reported, while unexpected read or conversion failures are recorded and raised. A local incremental `build_summary.csv` makes interrupted work inspectable.

```python
from fielddata import processed

frame = processed.load("ppl", "E_W_Brown_BESS", month="2022-06")
manifest = processed.validate("cao", "QAS:0")
```

Normal reads check code, source size/modification signatures and output checksums without reparsing or rehashing the full original archives. `processed.validate` or `processed.load(..., verify_sources_now=True)` freshly hashes originals as well. Use this stronger check after copying files or when size and modification time cannot be trusted. This distinction is explicit because full archive hashing is not a seconds-scale query.

Parts preserve source order, including duplicate or out-of-order timestamps. The ordinary Schaeffer raw loader sorts timestamps while its streaming reader preserves source order. Sort a processed frame stably by time if comparing with the ordinary sorted loader. The processed copy does not silently deduplicate either representation.

## Reused work and verification

This implementation reuses the analysis repository's `docs/DESIGN_ANALYSIS_LAYERS.md` contract, with the maintainer's newer sign and partition decisions overriding the proposal. It reuses the existing loader mappings, source-audit notes, inferred Cao layout and SOC conversion, Schaeffer streaming reader, snippet index and iterator, torch-free parser, registry, checksum references, committed holding snapshots and counting ledger.

The maintainer approved the committed audits and schema notes at `d447b9eed0206f139d0a9bca6ece5fb0c8c6bc36` as the source baseline, with targeted rereads and held-data checks rather than a fresh full reread. Each mapping row cites its evidence. `AUDIT-ONLY MEANING` flags semantics without independent data corroboration. A new data-versus-audit disagreement requires a full source reread and an entry in `docs/DECISIONS.md`. The numerical checks found no such new disagreement. PPL's separate cell-level share is explicitly excluded by the approved pilot scope.

The sandbox `reproductions/_schema/reproduction-record.schema.json` was checked in the held working copies. It describes method-reproduction evidence, not telemetry. Its provenance principles, code revision, reproducibility and explicit blocked status, informed the manifests. Its JSON shape was not substituted for a telemetry schema. No earlier implemented common telemetry view was found in this repository or the analysis repository.

Run `python scripts/checks/standard_layers.py test`, `verify`, `check` and `build`. The script saves check outputs, per-unit build status, known charge windows and three DejaVu Sans pilot previews under `reports/checks/standard_layers/`. These are mapping checks, not layer-3 health estimates or new fault labels.
