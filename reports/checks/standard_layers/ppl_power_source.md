# PPL power source check

Reproduce with `python scripts/checks/standard_layers.py ppl-power-source`.

The held paper, Section III, PDF page 5, describes logged AC real and reactive power separately from DC voltage and current. This targeted reread corroborates the AC-side designation in the standard view. It is source evidence, not an independent instrument-boundary data check. The schema's conservative audit-only flag identifies that lack of independent data corroboration. The held sign check is recorded separately in `charge_periods.csv` and the prior PPL audit.
