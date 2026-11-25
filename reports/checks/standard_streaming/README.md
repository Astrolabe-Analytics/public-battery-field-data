# Streaming standard interface checks

Reproduce with `python scripts/checks/standard_streaming.py`.

Synthetic tests check lazy, single-pass Schaeffer and snippet archive conversion, raw/standard equivalence, source order and duplicate timestamps, snippet-relative time, unit identity, Xie bulk reads, pure loader-batch conversion and explicit input errors. Existing mapping, raw-loader and processed-copy regressions are included. The test command passed. See tests.txt for its output. No held released data or SSD processed copies were read or written. This does not revalidate or rebuild caches after the producing-code fingerprint change.
