import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
import re, subprocess, tempfile, os
h = Harvest("scudery-artamene-grand-cyrus")
for i in range(1, 11):
    pdf = h.get(f"https://artamene.othone.org/pdfs/cyrus{i}.pdf", f"files/cyrus{i}.pdf", binary=True)
    txt = subprocess.run(["pdftotext", str(h.dir / f"files/cyrus{i}.pdf"), "-"], capture_output=True, text=True).stdout
    lines = txt.splitlines()
    # drop front matter/sommaire: start at first 'Livre premier'
    start = next(k for k, l in enumerate(lines) if l.strip() == "Livre premier")
    out = []
    for l in lines[start:]:
        s = l.strip()
        if s.startswith("file:///") or re.fullmatch(r"Le Grand Cyrus partie \d+", s) or s == "\f":
            continue
        out.append(l.replace("\f", ""))
    raw = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    h.add(f"cyrus{i}.txt", raw, language="French", year=1656, source="Scudéry, Artamène ou le Grand Cyrus, partie %d (Paris, Courbé, 1656; first ed. 1649-1653)" % i, url=f"https://artamene.othone.org/pdfs/cyrus{i}.pdf")
rep = h.finish(method="Downloaded the ten official PDFs (cyrus1-10.pdf) of the text from artamene.othone.org, extracted with pdftotext; cut the table of contents (sommaire) and the page headers/footers.",
  coverage="All: ten parts of the novel, whole text (sequence titles kept as short headings).",
  problems=["PDFs derive from a 2003 HTML version of the text; year set to 1656 (edition reproduced, Courbé), the parts first appeared 1649-1653; all inside window.",
            "No robots.txt (404). TEI on GitHub mentioned by the site but not found."])
print(rep["texts_in_window"], rep["words_in_window"])
