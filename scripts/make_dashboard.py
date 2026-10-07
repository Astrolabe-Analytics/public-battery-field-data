"""Write the static release dashboard, docs/dashboard/index.html.

What it does: builds one self-contained HTML page (inline CSS and JavaScript, no external files except the
preview images in docs/dashboard/img/) that lists every release in one sortable, filterable table and
gives each release a card: a two-sentence description, how to download it, three lines of code to load it,
and whether its loader was verified on the full holdings.

Reads: docs/descriptor/TABLE1_sources.md and TABLE2_packages.md (the paper's tables, so the page shows the
same values), fielddata/registry.py, docs/descriptor/citations.csv, the download plans in fielddata/fetch.py,
the quick-start arguments in fielddata/quickstart.py, and docs/dashboard/status.json from
scripts/dashboard_status.py. It reads no data files.
Writes: docs/dashboard/index.html.

Run:
    python scripts/make_dashboard.py
"""
from __future__ import annotations

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
from fielddata.registry import PACKAGES

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
}


def markdown_table(path: Path) -> list[dict]:
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    return [dict(zip(header, [c.strip() for c in l.strip("|").split("|")])) for l in lines[2:]]


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
    source = "a public data record" if reference == "data record only" else reference
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
    out = []
    for name, t1 in table1.items():
        row = {**t1, **table2[name], "release": name}
        row["reference_text"], row["reference_url"] = link(t1["Reference"])
        row["data_text"], row["data_url"] = link(t1["Data"])
        row["code_text"], row["code_url"] = link(t1["Code"])
        row["title"] = PACKAGES[name]["title"]
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
               ("Service time", "Service time"), ("Energy, MWh", "Energy, MWh (basis)"), ("Size, GB", "Size, GB"),
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
            value = number(text) if label in {"Year", "Units", "Cells", "Service time", "Energy, MWh", "Size, GB"} else None
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
        figure = '<p class="withheld">Preview withheld pending license decision.</p>'
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
<p>{e(r["description"])}</p>
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
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:1.9rem;line-height:1.2;margin:.2em 0 .4em}h2{margin-top:2.2em;font-size:1.35rem}h3{margin:0;font-size:1.15rem}h4{margin:1.1em 0 .3em;font-size:.95rem}
a{color:var(--accent)}.muted{color:var(--muted)}
.lede{font-size:1.08rem;max-width:62ch}
.totals{font-size:1.15rem;font-weight:600;margin:.2rem 0 .8rem}
ol.steps{padding-left:1.3em;max-width:70ch}ol.steps li{margin:.35em 0}
code,pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.86rem}
pre{background:var(--soft);border:1px solid var(--line);border-radius:6px;padding:10px 12px;overflow-x:auto;white-space:pre}
p code{background:var(--soft);padding:1px 4px;border-radius:4px}
.controls{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin:12px 0}
.controls input,.controls select{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);min-width:0}
.controls input{flex:1 1 220px}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:.88rem}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
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


def totals_line(count: int) -> str:
    """The headline totals from reports/totals.json, rounded as in the paper."""
    t = json.loads((ROOT / "reports" / "totals.json").read_text(encoding="utf-8"))
    if t["loader_count"] != count:
        raise SystemExit(f"reports/totals.json counts {t['loader_count']} releases, the registry {count}: run scripts/totals.py")
    parts = [f"{count} releases", f"{t['released_units_total']:,.0f} systems", f"{t['unit_years']:,.0f} unit-years",
             f"{t['energy_total_mwh']:,.1f} MWh", f"{t['size_gb']:,.0f} GB", f"{t['faults']:,} faults"]
    return " · ".join(parts)


def page(data: list[dict]) -> str:
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
<p class="totals">{e(totals_line(len(data)))}</p>
<p class="lede">{len(data)} public releases of battery data recorded in real use: cars, buses, light electric vehicles, home and grid storage, phones and factory robots. Each was published by its authors with a paper or data record. This collection does not copy their files. It tells you where to download each release and gives one Python loader per release, so every release can be read the same way.</p>
<h2>Get started</h2>
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
<h2>All releases</h2>
<p class="note">Values are the paper's Tables 1 and 2, generated from the repository. Licenses marked * restrict commercial use; ** state no license. Service time is unit-years where the release has timestamps, otherwise a lower bound in hours. Where a release's count differs from its paper, the paper's count is in brackets. Download says how each release downloads as of {e(fetch.ROUTE_DATE)}: one command, manual in a web browser, or partly manual (ppl, whose cell-level data is on a Box share).</p>
<div class="controls"><input id="q" type="search" placeholder="Search releases, countries, chemistries" aria-label="Search releases">
<select id="app" aria-label="Application"><option value="">All applications</option>{options}</select>
<select id="lic" aria-label="License"><option value="">All licenses</option><option value="open">Open licenses</option><option value="non-commercial">Non-commercial (*)</option><option value="unstated">No license stated (**)</option></select>
<span id="count" class="note" aria-live="polite"></span></div>
<div class="tablewrap">{table_html(data)}</div>
<h2>Release by release</h2>
<p class="note">{e(status_line)} Each preview is drawn from the release by its loader. Where a release restricts commercial use or states no license, the preview says so.</p>
<div class="cards">{"".join(card_html(r) for r in data)}</div>
<p class="note">Generated by <code>scripts/make_dashboard.py</code> from the repository; loader status from <code>scripts/dashboard_status.py</code>.</p>
</main><script>{JS}</script></body></html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page(rows()), encoding="utf-8", newline="\n")
    print(f"wrote {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
