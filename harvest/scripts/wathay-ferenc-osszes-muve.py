import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
import re
from lxml import html as LH
h = Harvest("wathay-ferenc-osszes-muve")
B = "https://magyar-irodalom.elte.hu/gepesk/wathay/"
def fetch(rel, cache):
    p = h.dir / cache
    if not p.exists():
        raw = h.get(B + rel, cache + ".raw", binary=True)
        (h.dir / (cache + ".raw")).unlink(missing_ok=True)
        p.write_text(raw.decode("cp1250", errors="replace"), encoding="utf-8")
    return p.read_text(encoding="utf-8")
tart = fetch("tart.htm", "files/tart.html")
ids = ["cim", "eloszo"] + [f"{i:02d}" for i in range(1, 29)]
found = set(re.findall(r"versek\\bhu\\(\w+)\.htm", tart))
probs = []
if found != set(ids): probs.append(f"TOC mismatch: {sorted(found ^ set(ids))}")
names = {"cim": "title page", "eloszo": "preface"}
for i in ids:
    page = fetch(f"versek/bhu/{i}.htm", f"files/{i}.html")
    t = LH.fromstring(page)
    paras = []
    for p in t.xpath("//body//p"):
        s = re.sub(r"\s+", " ", p.text_content().replace("\xa0", " ")).strip()
        if s: paras.append(s)
    h.add(f"{i}.txt", "\n".join(paras), language="Hungarian", year=1604, source=f"Wathay Ferenc, Enekes könyv, {names.get(i, 'song ' + i)}", url=B + f"versek/bhu/{i}.htm")
probs.append("Year 1604 (date on the title page 'Anno 1604'); the catalogue gives writing years 1603-1606. Records are title page, preface and 28 songs (catalogue counts the songbook as 1 text). Only the letter-faithful transcription pages (bhu) kept; afterword (utoszo) and facsimile pages left out. robots.txt returns an error page (none).")
rep = h.finish(method="Crawled tart.htm and the 30 transcription pages versek/bhu/*.htm (windows-1250 HTML).", coverage="All: title page, preface and songs 1-28.", problems=probs)
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
