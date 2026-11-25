"""li2026_evfault candidate loader on synthetic archive members shaped like the release (libarchive cannot write RAR)."""
from fielddata.registry import CANDIDATES, PACKAGES


def _members():
    header = ",".join(f"V {i}" for i in range(1, 15))
    rows = [",".join(f"{4100.0 + s + c}" for c in range(14)) for s in range(50)]
    data = (header + "\n" + "\n".join(rows) + "\n").encode()
    label0 = ("0\n" + "\n".join(["0.0"] * 13 + ["1.0"]) + "\n").encode()
    label1 = ("0\n" + "\n".join(["0.0"] * 3 + ["4.0"] + ["0.0"] * 10) + "\n").encode()
    return {"Data & Code/Data/0.csv": data, "Data & Code/Data/1.csv": data,
            "Data & Code/Label/0.csv": label0, "Data & Code/Label/1.csv": label1}


def test_li2026_evfault_reads_snapshots_and_labels(monkeypatch):
    from fielddata.loaders import li2026_evfault as ev

    fake = _members()
    monkeypatch.setattr(ev, "members", lambda prefix="": {k: v for k, v in fake.items() if k.startswith("Data & Code/" + prefix)})

    frame = ev.load()
    assert frame.shape == (100, 16) and list(frame.columns[:3]) == ["window", "sample", "V 1"]
    assert frame["V 1"].iloc[0] == 4100.0 and frame["V 14"].iloc[49] == 4100.0 + 49 + 13  # mV as released

    lab = ev.labels()
    assert len(lab) == 28 and set(lab["header"]) == {"0"}  # first line is the header, 14 values follow
    assert lab.query("window == 0 and cell == 14")["label"].item() == "EI"
    assert lab.query("window == 1 and cell == 4")["label"].item() == "ISC"

    units = ev.systems()
    assert units["faulty_cells"].tolist() == [1, 1] and units["codes"].tolist() == ["14:1", "4:4"]


def test_li2026_evfault_was_admitted_in_v13():
    assert "li2026_evfault" in PACKAGES and "li2026_evfault" not in CANDIDATES and "li2026" in PACKAGES
    assert "status" not in PACKAGES["li2026_evfault"]
