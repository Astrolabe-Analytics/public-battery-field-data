"""Quantization of U, I, SOC, cell voltage per vehicle file (share of values on the stated resolution grid), bilfinger2024/2026 via loaders (raw).
Grid: U 0.25 V, I 0.01 A, SOC 0.4 %% (VW) / 0.1 %% (Tesla), cell voltage 0.001 V. On-grid values are logged samples or held copies; off-grid values were computed (interpolated or averaged). Writes nothing."""
import numpy as np
from fielddata.loaders import bilfinger2024 as A, bilfinger2026 as B

def on_grid(x, step):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    r = np.abs(x / step - np.round(x / step))
    return float(np.mean(r < 1e-4))

for mod, rel in [(A, "2024"), (B, "2026")]:
    for r in mod.systems().itertuples():
        if r.kind != "vehicle":
            continue
        d = mod.load(r.unit)
        tesla = r.unit.startswith("Tesla")
        cv = d["cell_voltage_0" if "cell_voltage_0" in d else "cell_voltage_1"]
        print(rel, r.unit, "U@0.25 %.3f" % on_grid(d.U, 0.25), "U@0.1 %.3f" % on_grid(d.U, 0.1), "I@0.01 %.3f" % on_grid(d.I, 0.01),
              "SOC@%s %.3f" % ("0.1" if tesla else "0.4", on_grid(d.SOC, 0.1 if tesla else 0.4)), "cellV@0.001 %.3f" % on_grid(cv, 0.001))
