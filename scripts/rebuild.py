"""Regenerate public summary reports from committed metadata inputs."""
import json
from html import escape as html_escape
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"
NOTEBOOK_REPORTS = ROOT / "reports" / "notebooks"


def run(script: Path) -> None:
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def collapse_details(notebook: Path, html: Path) -> None:
    """In a notebook's HTML export, put each subsection of a "## N. Details" section in its own <details> block.

    The section heading cell and its text stay visible. Each "### " heading cell becomes the summary of a block,
    closed by default, that holds every cell up to the next "### " or "## " heading, code and outputs included.
    """
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    sources = ["".join(c["source"]) if c["cell_type"] == "markdown" else "" for c in cells]
    heads = [i for i, text in enumerate(sources) if text.startswith("## ")]
    found = [i for i in heads if re.match(r"## \d+\. Details\b", sources[i])]
    if not found:
        return
    later = [i for i in heads if i > found[0]]
    stop = later[0] if later else len(cells)
    subsections = [i for i in range(found[0] + 1, stop) if sources[i].startswith("### ")]
    if not subsections:
        return
    text = html.read_text(encoding="utf-8")

    def cell_start(index: int) -> int:
        if index >= len(cells):
            return text.rindex("</main>")
        position = text.index(f'id="cell-id={cells[index]["id"]}"')
        return text.rindex("<div", 0, position)

    # find every position first, then edit from the last subsection back so earlier positions stay valid
    bounds = [(sources[head].strip().splitlines()[0][4:].strip(), cell_start(head), cell_start(head + 1), cell_start(end_index))
              for head, end_index in zip(subsections, subsections[1:] + [stop])]
    for title, head_start, body_start, end in reversed(bounds):
        title = html_escape(title)
        block = ('<details class="details-section" style="font-family: var(--jp-content-font-family); '
                 'font-size: var(--jp-content-font-size1)"><summary style="margin-left: calc(var(--jp-cell-prompt-width) + 22px)">'
                 f'{title}</summary>\n' + text[body_start:end] + "</details>\n")
        text = text[:head_start] + block + text[end:]
    html.write_text(text, encoding="utf-8")


def export_notebooks() -> None:
    NOTEBOOK_REPORTS.mkdir(parents=True, exist_ok=True)
    notebooks = (path for path in NOTEBOOKS.rglob("*.ipynb") if ".ipynb_checkpoints" not in path.parts)
    for notebook in sorted(notebooks):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "jupyter",
                "nbconvert",
                "--to",
                "html",
                str(notebook),
                "--output-dir",
                str(NOTEBOOK_REPORTS),
            ],
            cwd=ROOT,
            check=True,
        )
        collapse_details(notebook, NOTEBOOK_REPORTS / f"{notebook.stem}.html")


def main() -> None:
    run(ROOT / "scripts" / "totals.py")
    run(ROOT / "scripts" / "table1.py")
    run(ROOT / "scripts" / "tables.py")
    filler = ROOT / "scripts" / "fill_descriptor.py"  # fills the working copy of the paper text, not in the public release
    if filler.exists():
        run(filler)
    export_notebooks()


if __name__ == "__main__":
    main()