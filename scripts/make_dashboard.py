"""Write the static release dashboard, docs/dashboard/index.html.

What it does: builds one self-contained HTML page (inline CSS and JavaScript, no external files except the
preview images in docs/dashboard/img/) that lists every release in one sortable, filterable table and
gives each release a card: a two-sentence description, how to download it, three lines of code to load it,
and whether its loader was verified on the full holdings.

The On deck section lists candidate releases (fielddata.registry.CANDIDATES) below the collection. They are not
in the totals. Their status comes from docs/dashboard/ondeck_status.json, written by scripts/checks/ondeck_facts.py.
Below it, collapsible lists give every other screened dataset (adjacent, not openly accessible, out of scope) with its
link and reason, read from SCREENING.md, so the page and that file cannot disagree.

Reads: docs/descriptor/TABLE1_sources.md and TABLE2_packages.md (the paper's tables, so the page shows the
same values), fielddata/registry.py, docs/descriptor/citations.csv, the download plans in fielddata/fetch.py,
the quick-start arguments in fielddata/quickstart.py, and docs/dashboard/status.json from
scripts/dashboard_status.py. It reads no data files.
Writes: docs/dashboard/index.html, the public page. With --private it writes docs/dashboard/private.html instead,
which adds the On deck and Screened sections. scripts/export_release.py leaves private.html out of the public
release. When the on-deck releases are published (v1.2), set ONDECK_PUBLIC = True so index.html carries both sections.

Run:
    python scripts/make_dashboard.py              # public page
    python scripts/make_dashboard.py --private    # local page with On deck and Screened
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import html
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fielddata import fetch, quickstart
from fielddata.registry import CANDIDATES, PACKAGES

# On deck and Screened stay out of the public page until v1.2 is published. Set True at that release.
ONDECK_PUBLIC = False

DESCRIPTOR = ROOT / "docs" / "descriptor"
OUT = ROOT / "docs" / "dashboard"
REPO = "https://github.com/Astrolabe-Analytics/public-battery-field-data/blob/main"

NOUNS = {  # service class -> (singular, plural)
    "passenger EV": ("passenger electric vehicle", "passenger electric vehicles"),
    "bus": ("electric bus", "electric buses"),
    "distributed storage": ("home or building storage system", "home or building storage systems"),
    "grid-scale storage": ("grid-scale storage unit", "grid-scale storage units"),
    "consumer electronics": ("mobile phone", "mobile phones"),
    "light electric mobility": ("light electric vehicle pack", "light electric vehicle packs"),
    "industrial and robotics": ("automated guided vehicle pack", "automated guided vehicle packs"),
}


UNIT_NOUNS = {  # releases whose units are parts of one installation
    "cloverleaf": ("second-life battery pack of one building storage system", "second-life battery packs of one building storage system"),
    "shenzhen_charging": ("charging session", "charging sessions"),  # no vehicle identifier (Table 2 shows sessions)
}


def markdown_table(path: Path) -> list[dict]:
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    return [dict(zip(header, [c.strip() for c in l.strip("|").split("|")])) for l in lines[2:]]


def faults_by_release() -> dict[str, str]:
    """Faults per release as counted in the paper's Table 3: the Fault count section of TABLE3_faults.md, which
    scripts/totals.py reads for totals.json. A release whose batteries are not identified (shenzhen_charging) shows its
    count with "(sessions)". Releases not in the section have no counted faults."""
    section = (DESCRIPTOR / "TABLE3_faults.md").read_text(encoding="utf-8").split("## Fault count", 1)[1]
    counts = {}
    for line in section.splitlines():
        cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[1].replace(",", "").isdigit() or cells[0] in {"Package", "Total"}:
            continue
        counts[cells[0]] = cells[1] if cells[2].replace(",", "").isdigit() else f"{cells[1]} (sessions)"
    return counts


def link(cell: str) -> tuple[str, str | None]:
    """'[text](url)' -> (text, url); plain text -> (text, None)."""
    match = re.fullmatch(r"\[(.+?)\]\((.+?)\)", cell)
    return (match.group(1), match.group(2)) if match else (cell, None)


def number(text: str) -> float | None:
    match = re.search(r"\d[\d,]*\.?\d*", text)
    return float(match.group(0).replace(",", "")) if match and not text.startswith("not") else None


def manual_steps(package: str) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        fetch.print_manual(fetch.plan_package(package, to="data"))
    return buffer.getvalue().replace("\\", "/").rstrip()


def partly_manual_steps(package: str) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        fetch.print_partly_manual(fetch.plan_package(package, to="data"))
    return buffer.getvalue().rstrip()


def load_code(package: str, status: dict) -> str:
    args = dict(status.get("load_args") or quickstart.EXAMPLES[package])
    chunked = "chunksize" in args
    if package in quickstart.PREVIEW:
        module = package.replace("-", "_")
        call = f"{module}.preview({', '.join(f'{k}={v!r}' for k, v in args.items())})"
        return f"from fielddata.loaders import {module}\nframe = {call}\nframe.head()"
    call = ", ".join([repr(package)] + [f"{k}={v!r}" for k, v in args.items()])
    load = f"next(fielddata.load({call}))" if chunked else f"fielddata.load({call})"
    return f"import fielddata\nframe = {load}\nframe.head()"


def describe(row: dict) -> str:
    units = int(number(row["Units"]) or 0)
    singular, plural = UNIT_NOUNS.get(row["release"]) or NOUNS.get(row["Service class"], ("unit", "units"))
    where = f"in {row['Country']}" if row["Country"] != "not stated" else "(country not stated)"
    chemistry = f" with {row['Chemistry']} cells" if row["Chemistry"] != "not stated" else ""
    reference = row["reference_text"]
    source = reference
    first = f"Field data from {units:,} {singular if units == 1 else plural} {where}{chemistry}, released with {source}."
    service = row["Service time"]
    energy = row["Energy, MWh (basis)"]
    match = re.fullmatch(r"(\S+) \((\w+)\)", energy)
    energy_text = f" and about {match.group(1)} MWh of battery energy ({match.group(2)})" if match else ""
    if service == "no timestamps":
        return f"{first} The release has no timestamps, so the time it covers is not known{energy_text.replace(' and about', '; it holds about')}."
    return f"{first} The release covers {service} of operation{energy_text}."


def rows() -> list[dict]:
    table1 = {r["Release"]: r for r in markdown_table(DESCRIPTOR / "TABLE1_sources.md")}
    table2 = {r["Package"]: r for r in markdown_table(DESCRIPTOR / "TABLE2_packages.md")}
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8")) if (OUT / "status.json").exists() else {}
    faults = faults_by_release()
    out = []
    for name, t1 in table1.items():
        row = {**t1, **table2[name], "release": name}
        row["reference_text"], row["reference_url"] = link(t1["Reference"])
        row["data_text"], row["data_url"] = link(t1["Data"])
        row["code_text"], row["code_url"] = link(t1["Code"])
        row["title"] = PACKAGES[name]["title"]
        row["Faults"] = faults.get(name, "0")
        plan = fetch.plan_package(name, to="data")
        row["automatic"] = plan.automatic
        row["route"] = fetch.route(name)
        row["download"] = (f"python -m fielddata.fetch {name}" if plan.automatic else manual_steps(name))
        row["partly_manual"] = partly_manual_steps(name) if row["route"] == "partly manual" else ""
        row["source_kind"] = plan.source_kind
        row["status"] = status.get(name, {})
        row["code"] = load_code(name, row["status"])
        row["description"] = describe(row)
        out.append(row)
    return out


def e(text) -> str:
    return html.escape(str(text), quote=True)


def a(text: str, url: str | None) -> str:
    return f'<a href="{e(url)}" rel="noopener">{e(text)}</a>' if url else e(text)


def table_html(data: list[dict]) -> str:
    columns = [("Year", "Year"), ("Reference", None), ("Release", "release"), ("Application", "Service class"),
               ("Country", "Country"), ("Chemistry", "Chemistry"), ("Units", "Units"), ("Cells", "Cells"),
               ("Service time", "Service time"), ("Energy, MWh", "Energy, MWh (basis)"), ("Faults", "Faults"), ("Size, GB", "Size, GB"),
               ("License", "License"), ("Download", "route"), ("Data", None), ("Code", None)]
    head = "".join(f'<th scope="col" data-col="{i}"><button type="button">{e(label)}</button></th>' for i, (label, _) in enumerate(columns))
    body = []
    for r in data:
        cells = []
        for label, key in columns:
            if label == "Reference":
                text, cell = r["reference_text"], a(r["reference_text"], r["reference_url"])
            elif label == "Data":
                text, cell = r["data_text"], a(r["data_text"], r["data_url"])
            elif label == "Code":
                text, cell = r["code_text"], a(r["code_text"], r["code_url"])
            elif label == "Release":
                text, cell = r["release"], f'<a href="#{e(r["release"])}">{e(r["release"])}</a>'
            else:
                text, cell = r[key], e(r[key])
            value = number(text) if label in {"Year", "Units", "Cells", "Service time", "Energy, MWh", "Faults", "Size, GB"} else None
            if label == "Size, GB" and text.startswith("<"):
                value = 0.0
            if label == "Service time" and text.endswith(" h"):
                value = (value or 0) / 8766  # sort hours with unit-years
            sort = "" if value is None else f' data-sort="{value}"'
            cells.append(f"<td{sort}>{cell}</td>")
        body.append(f'<tr data-app="{e(r["Service class"])}" data-lic="{e(license_group(r["License"]))}">' + "".join(cells) + "</tr>")
    return f'<table id="releases"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def license_group(text: str) -> str:
    return "unstated" if text.endswith("**") else "non-commercial" if text.endswith("*") else "open"


def preview_license(license_text: str) -> str:
    """Caption sentence for a preview derived from a release with restrictive or no license terms."""
    if "unstated" in license_text.lower():
        return "The authors state no license for this data; the figure and CSV are shown for orientation only."
    return f"The figure and CSV are derived from this release and carry its license, {license_text}, for non-commercial use only."


IN_DEPTH = {  # release -> notebook worked through in depth
    "cao": "notebooks/cao_in_depth.ipynb",
}


def in_depth(release: str) -> str:
    if release not in IN_DEPTH:
        return ""
    return (f'<p><a href="{REPO}/{IN_DEPTH[release]}" rel="noopener">In-depth notebook</a>: '
            "a worked example of a release published without column names, units or timestamps.</p>")


def related_html(release: str) -> str:
    """For a release without a paper, its related source (maintainer, 2026-10-16), as a line under the description."""
    urls = PACKAGES[release]["urls"]
    paper = urls.get("paper")
    if (paper and paper.startswith("http")) or not urls.get("context"):
        return ""
    return f'<p class="muted">No paper. Related: {a(paper or "source", urls["context"])}</p>'


def card_html(r: dict) -> str:
    s = r["status"]
    if s.get("status") == "ok":
        badge = f'<span class="badge ok">Loader verified {e(s["date"])}</span> <span class="muted">{s["rows"]:,} rows, {len(s["columns"])} columns in the sample slice</span>'
    elif s.get("status") == "failed":
        badge = f'<span class="badge bad">Loader failed {e(s["date"])}</span> <span class="muted">{e(s["error"])}</span>'
    else:
        badge = '<span class="badge">Loader not yet checked</span>'
    if s.get("preview"):
        figure = (f'<figure><img src="{e(s["preview"])}" alt="{e(s["preview_title"])}" loading="lazy" width="704" height="286">'
                  f'<figcaption>{e(s["preview_title"])}. One unit, quick-start slice'
                  + (f', one point in every {s["preview_step"]:,} drawn' if s.get("preview_step", 1) > 1 else "")
                  + f'. <a href="{e(s["preview_data"])}">Plotted data (CSV)</a>.'
                  + (f' {preview_license(s["preview_license"])}' if s.get("preview_license") else '')
                  + '</figcaption></figure>')
    elif s.get("preview_withheld"):
        reason = s["preview_withheld"] if isinstance(s["preview_withheld"], str) else "Preview withheld pending license decision."
        figure = f'<p class="withheld">{e(reason)}</p>'
    else:
        figure = ""
    if r["route"] == "partly manual":
        download = (f'<p><strong>Partly manual</strong> (as of {e(fetch.ROUTE_DATE)}). One command downloads the files on {e(r["data_text"])}:</p>'
                    f'<pre><code>{e(r["download"])}</code></pre><p>The command then prints the manual step for the rest:</p>'
                    f'<pre><code>{e(r["partly_manual"])}</code></pre>')
    elif r["automatic"]:
        download = f'<p><strong>One command</strong> (as of {e(fetch.ROUTE_DATE)}), from {e(r["data_text"])}:</p><pre><code>{e(r["download"])}</code></pre>'
        if r["release"] in fetch.FETCH_NOTES:
            download += f'<p class="muted">{e(fetch.FETCH_NOTES[r["release"]])}</p>'
    else:
        download = f'<p><strong>Manual, in a web browser</strong> (as of {e(fetch.ROUTE_DATE)}), from {e(r["data_text"])}. The fetch command prints these steps:</p><pre><code>{e(r["download"])}</code></pre>'
    return f'''<article class="card" id="{e(r["release"])}" data-app="{e(r["Service class"])}" data-lic="{e(license_group(r["License"]))}">
<header><h3>{e(r["release"])}</h3><p class="muted">{e(r["title"])}</p></header>
<p>{e(r["description"])}</p>{related_html(r["release"])}
<div class="status">{badge}</div>
<h4>Download</h4>{download}
<h4>Load a first slice</h4><pre><code>{e(r["code"])}</code></pre>{in_depth(r["release"])}
{figure}
</article>'''


CSS = """
:root{--bg:#ffffff;--fg:#1f2328;--muted:#59636e;--line:#d1d9e0;--soft:#f6f8fa;--accent:#1f6feb;--ok:#1a7f37;--bad:#cf222e}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#9198a1;--line:#30363d;--soft:#161b22;--accent:#4493f8;--ok:#3fb950;--bad:#f85149}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:min(95vw,1800px);margin:0 auto;padding:24px 16px 64px}
h1{font-size:1.9rem;line-height:1.2;margin:.2em 0 .4em}h2{margin-top:2.2em;font-size:1.35rem}h3{margin:0;font-size:1.15rem}h4{margin:1.1em 0 .3em;font-size:.95rem}
a{color:var(--accent)}.muted{color:var(--muted)}
.lede{font-size:1.08rem}
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin:.6rem 0 1.2rem}
@media (max-width:860px){.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:420px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
.kpi{border:1px solid var(--line);border-radius:10px;padding:12px 10px;background:var(--soft);text-align:center;min-width:0}
.kpi-figure{font-size:1.6rem;font-weight:700;line-height:1.15;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.kpi-label{font-size:.82rem;color:var(--muted);margin-top:4px}
details.getstarted{border:1px solid var(--line);border-radius:8px;padding:8px 14px;margin:1.6em 0 0}
details.getstarted>summary{cursor:pointer;font-size:1.35rem;font-weight:600}
details.getstarted[open]>summary{margin-bottom:.4em}
ol.steps{padding-left:1.3em}ol.steps li{margin:.35em 0}
code,pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.86rem}
pre{background:var(--soft);border:1px solid var(--line);border-radius:6px;padding:10px 12px;overflow-x:auto;white-space:pre}
p code{background:var(--soft);padding:1px 4px;border-radius:4px}
.controls{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin:12px 0}
.controls input,.controls select{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);min-width:0}
.controls input{flex:1 1 220px}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:.88rem}
th,td{padding:6px 7px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
td[data-sort]{font-variant-numeric:tabular-nums}
th{background:var(--soft);position:sticky;top:0;white-space:nowrap}
th button{all:unset;cursor:pointer;font-weight:600}th button:focus-visible{outline:2px solid var(--accent)}
th[aria-sort=ascending] button::after{content:" \\25B2";font-size:.7em}th[aria-sort=descending] button::after{content:" \\25BC";font-size:.7em}
tbody tr:hover{background:var(--soft)}
.note{font-size:.85rem;color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,520px),1fr));gap:16px}
.card{border:1px solid var(--line);border-radius:10px;padding:16px;min-width:0}
.card header p{margin:.2em 0 0;font-size:.9rem}
.badge{display:inline-block;font-size:.8rem;font-weight:600;padding:2px 8px;border-radius:999px;border:1px solid var(--line)}
.badge.ok{color:var(--ok);border-color:var(--ok)}.badge.bad{color:var(--bad);border-color:var(--bad)}
.status{margin:.6em 0;font-size:.9rem}
figure{margin:12px 0 0}figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff}
figcaption{font-size:.82rem;color:var(--muted)}
.ondeck{margin-top:2.2em}
.screened{border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0}
.screened summary{cursor:pointer;font-weight:600}.screened .tablewrap{margin:.5em 0 .2em}
.withheld{font-size:.9rem;color:var(--muted);border:1px dashed var(--line);border-radius:6px;padding:10px;margin-top:12px}
"""

JS = """
(function(){
  const table=document.getElementById('releases'), tbody=table.tBodies[0];
  const q=document.getElementById('q'), app=document.getElementById('app'), lic=document.getElementById('lic'), count=document.getElementById('count');
  function apply(){
    const term=q.value.trim().toLowerCase(); let shown=0;
    for(const row of tbody.rows){
      const ok=(!term||row.textContent.toLowerCase().includes(term))&&(!app.value||row.dataset.app===app.value)&&(!lic.value||row.dataset.lic===lic.value);
      row.hidden=!ok; if(ok) shown++;
      const card=document.getElementById(row.cells[2].textContent.trim()); if(card) card.hidden=!ok;
    }
    count.textContent=shown+' of '+tbody.rows.length+' releases shown';
  }
  [q,app,lic].forEach(el=>el.addEventListener('input',apply));
  table.tHead.querySelectorAll('th').forEach((th,i)=>th.querySelector('button').addEventListener('click',()=>{
    const dir=th.getAttribute('aria-sort')==='ascending'?'descending':'ascending';
    table.tHead.querySelectorAll('th').forEach(h=>h.removeAttribute('aria-sort')); th.setAttribute('aria-sort',dir);
    const rows=[...tbody.rows], sign=dir==='ascending'?1:-1;
    rows.sort((a,b)=>{const x=a.cells[i],y=b.cells[i];
      if(x.dataset.sort!==undefined||y.dataset.sort!==undefined){const p=x.dataset.sort===undefined?Infinity:+x.dataset.sort,r=y.dataset.sort===undefined?Infinity:+y.dataset.sort;return (p-r)*sign||0;}
      return x.textContent.localeCompare(y.textContent)*sign;});
    rows.forEach(r=>tbody.appendChild(r));
  }));
  apply();
})();
"""


ONDECK_STATUS = OUT / "ondeck_status.json"


SCREENED_SECTIONS = ["Adjacent, maybe later", "Not openly accessible", "Out of scope for now"]


def screening_sections() -> dict[str, list[dict]]:
    """The tables of SCREENING.md by section heading: one dict per row, keyed by the table's column names."""
    sections, current, columns = {}, None, None
    for line in (ROOT / "SCREENING.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current, columns = line[3:].strip(), None
            sections[current] = []
        elif current and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if columns is None:
                columns = cells
            elif not set(line) <= set("|-: "):
                sections[current].append(dict(zip(columns, cells)))
    return sections


def screened_html() -> str:
    """Three compact tables of the datasets screened but not on deck, one per SCREENING.md section, each collapsed."""
    sections = screening_sections()
    blocks = []
    for name in SCREENED_SECTIONS:
        rows = sections.get(name, [])
        tagged = any("Tag" in row for row in rows)
        head = "<th scope=\"col\">Dataset</th>" + ("<th scope=\"col\">Tag</th>" if tagged else "") + "<th scope=\"col\">Reason</th>"
        body = []
        for row in rows:
            _, url = link(row.get("Link", ""))
            cells = [a(row["Dataset"], url)] + ([e(row.get("Tag", ""))] if tagged else []) + [e(row.get("Why", ""))]
            body.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        blocks.append(f'<details class="screened"><summary>{e(name)} ({len(rows)})</summary>'
                      f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div></details>')
    return "".join(blocks)


def paper_cell(urls: dict) -> str:
    """A paper link, or for a release without a paper "no paper" and its related source (maintainer, 2026-10-16)."""
    paper = urls.get("paper")
    if paper and paper.startswith("http"):
        return a("paper", paper)
    if urls.get("context"):
        return f'no paper; related: {a(paper or "source", urls["context"])}'
    return "no paper"


def ondeck_html() -> str:
    """The On deck table: candidate releases, kept apart from the collection and out of its totals."""
    status = json.loads(ONDECK_STATUS.read_text(encoding="utf-8")) if ONDECK_STATUS.exists() else {}
    head = "".join(f"<th scope=\"col\">{e(c)}</th>" for c in
                   ("Release", "Application", "Chemistry", "Units", "Span", "License", "Paper", "Data", "Status"))
    body = []
    for name, entry in CANDIDATES.items():
        if not entry.get("status"):
            continue
        cat = entry.get("catalog", {})
        urls = entry["urls"]
        cells = [e(name), e(cat.get("application") or "not stated"), e(cat.get("chemistry") or "not stated"),
                 e(cat.get("units") if cat.get("units") is not None else "not stated"), e(cat.get("span") or "not stated"),
                 e(entry["license"]), paper_cell(urls),
                 a("record", urls.get("data")), e(status.get(name, {}).get("status", "not downloaded"))]
        body.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return (f'<table id="ondeck"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>')


def kpis(count: int) -> list[tuple[str, str]]:
    """The headline totals from reports/totals.json, rounded as in the paper: (figure, label) per tile."""
    t = json.loads((ROOT / "reports" / "totals.json").read_text(encoding="utf-8"))
    if t["loader_count"] != count:
        raise SystemExit(f"reports/totals.json counts {t['loader_count']} releases, the registry {count}: run scripts/totals.py")
    return [(f"{count}", "Releases"), (f"{t['released_units_total']:,.0f}", "Systems"), (f"{t['unit_years']:,.0f}", "Unit-years"),
            (f"{t['energy_total_mwh']:,.1f} MWh", "Energy"), (f"{t['size_gb']:,.0f} GB", "Data"), (f"{t['faults']:,}", "Faults")]


def kpi_html(count: int) -> str:
    tiles = "".join(f'<div class="kpi"><div class="kpi-figure">{e(figure)}</div><div class="kpi-label">{e(label)}</div></div>'
                    for figure, label in kpis(count))
    return f'<div class="kpis" aria-label="Collection totals">{tiles}</div>'



def ondeck_sections(count: int) -> str:
    """On deck and Screened: in the private page now, and in the public page once ONDECK_PUBLIC is set at v1.2."""
    ondeck = ondeck_html()
    ondeck_block = "" if "<tbody></tbody>" in ondeck else f"""<section class="ondeck">
<h2>On deck</h2>
<p class="note">Releases we plan to add. They are not part of the {count} releases above and are not counted in the totals. Status says how far each one has got: downloaded, verified against the publisher's checksums, and whether its loader is written.</p>
<div class="tablewrap">{ondeck}</div>
</section>
"""
    return ondeck_block + f"""<details class="getstarted screened-section"><summary>Screened</summary>
<p class="note">Datasets we looked at and did not put on deck, with the reason, from SCREENING.md. Lab-tested packs and modules may be added later. Lab-tested cells are out of scope and tagged with what they were cycled for.</p>
{screened_html()}
</details>
"""


def page(data: list[dict], private: bool = False) -> str:
    applications = sorted({r["Service class"] for r in data})
    options = "".join(f'<option value="{e(x)}">{e(x)}</option>' for x in applications)
    checked = [r for r in data if r["status"].get("status")]
    verified = sum(r["status"].get("status") == "ok" for r in data)
    dates = sorted({r["status"]["date"] for r in checked})
    status_line = (f"{verified} of {len(data)} loaders loaded their quick-start slice on the full holdings ({', '.join(dates)})."
                   if checked else "Loader checks have not been run yet.")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Battery Field Data Releases</title>
<meta name="description" content="{len(data)} public battery field-data releases: what they contain, how to download them, and how to load them.">
<style>{CSS}</style></head>
<body><main>
<h1>Public battery field data</h1>
{kpi_html(len(data))}
<p class="lede">{len(data)} public releases of battery data recorded in real use: cars, buses, light electric vehicles, home and grid storage, phones and factory robots. Each was published by its authors with a paper or data record. This collection does not copy their files. It tells you where to download each release and gives one Python loader per release, so every release can be read the same way.</p>
<details class="getstarted"><summary>Get started</summary>
<ol class="steps">
<li>Install Python 3.12 or newer from <a href="https://www.python.org/downloads/">python.org</a>. The Python that comes with macOS is too old.</li>
<li>Get the code, make a virtual environment and install:<pre><code>git clone https://github.com/Astrolabe-Analytics/public-battery-field-data.git
cd public-battery-field-data
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
python -m pip install -e .</code></pre>On a Mac, the first <code>git</code> command may offer to install Apple's command line tools, which takes several minutes. To skip git, use Code &gt; Download ZIP on the GitHub page and unzip it.</li>
<li>Choose where the data goes. Copy the example settings file:<pre><code>cp config/local.example.toml config/local.toml      # on Windows: copy config\\local.example.toml config\\local.toml</code></pre>Then open <code>config/local.toml</code> and replace the whole placeholder path <code>PATH_TO_PUBLIC_BATTERY_DATA_HOLDINGS</code> with your folder, keeping the quotes, for example <code>data_root = "~/battery-data"</code>. If you skip this, downloads go to a <code>data</code> folder inside the repository.</li>
<li>Download one release (each card below says how), then check it by name:<pre><code>python -m fielddata.doctor tsukuba</code></pre>Without a name, doctor checks all {len(data)} releases and lists every one you have not downloaded.</li>
<li>Open the quick-start notebook and run it from the top. It is set to cloverleaf, a second-life storage battery whose one 8 MB file downloads with one command; change <code>RELEASE</code> to the one you downloaded. If that release is not downloaded yet, the notebook prints the fetch command.<pre><code>jupyter lab notebooks/quickstart.ipynb</code></pre>In JupyterLab, choose Run &gt; Restart Kernel and Run All Cells (or the double-arrow button in the notebook toolbar).</li>
</ol>
</details>
<h2>Releases at a glance</h2>
<p class="note">Values are the paper's Tables 1 and 2, generated from the repository. Licenses marked * restrict commercial use; ** state no license. Service time is unit-years where the release has timestamps, otherwise a lower bound in hours. Where a release's count differs from its paper, the paper's count is in brackets. Download says how each release downloads as of {e(fetch.ROUTE_DATE)}: one command, manual in a web browser, or partly manual (ppl, whose cell-level data is on a Box share). Faults are the labeled or reported faults counted in the paper's Table 3. Units are each release's gross count. † marks a release that shares some units with another release. The totals at the top count each unit once.</p>
<div class="controls"><input id="q" type="search" placeholder="Search releases, countries, chemistries" aria-label="Search releases">
<select id="app" aria-label="Application"><option value="">All applications</option>{options}</select>
<select id="lic" aria-label="License"><option value="">All licenses</option><option value="open">Open licenses</option><option value="non-commercial">Non-commercial (*)</option><option value="unstated">No license stated (**)</option></select>
<span id="count" class="note" aria-live="polite"></span></div>
<div class="tablewrap">{table_html(data)}</div>
{ondeck_sections(len(data)) if private or ONDECK_PUBLIC else ""}<h2>Release by release</h2>
<p class="note">{e(status_line)} Each preview is drawn from the release by its loader. Where a release restricts commercial use or states no license, the preview says so.</p>
<div class="cards">{"".join(card_html(r) for r in data)}</div>
<p class="note">Found an error, or know a public battery field dataset we missed? Please open an issue: <a href="https://github.com/Astrolabe-Analytics/public-battery-field-data/issues">https://github.com/Astrolabe-Analytics/public-battery-field-data/issues</a></p>
<p class="note">Generated by <code>scripts/make_dashboard.py</code> from the repository; loader status from <code>scripts/dashboard_status.py</code>.</p>
</main><script>{JS}</script></body></html>
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write the release dashboard.")
    parser.add_argument("--private", action="store_true",
                        help="write docs/dashboard/private.html with the On deck and Screened sections (left out of the public release)")
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / ("private.html" if args.private else "index.html")
    target.write_text(page(rows(), private=args.private), encoding="utf-8", newline="\n")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
