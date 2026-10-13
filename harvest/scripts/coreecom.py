import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("coreecom")
B = "https://www.iifilologicas.unam.mx/coreecom/"
lst = h.get(B + "index.php?page=lista-de-documentos1&men=3", "files/lista.html")
cls = sorted(set(int(x) for x in re.findall(r"page=documento1&(?:amp;)?cl=(\d+)", lst)))
def clean(t):
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"<letra\s*\d*>", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"[ \t]+", " ", html.unescape(t)).strip()
miss = []
for cl in cls:
    u = f"{B}index.php?page=documento1&cl={cl}&men=3"
    p = h.get(u, f"files/doc_{cl}.html")
    m = re.search(r"Edici&oacute;n paleogr.*?</thead>\s*<tbody>.*?<td[^>]*>(.*?)</td>", p, re.S) or re.search(r"Edición paleográfica.*?</thead>\s*<tbody>.*?<td[^>]*>(.*?)</td>", p, re.S)
    if not m:
        miss.append(cl); continue
    raw = clean(m.group(1))
    f = re.search(r"Fecha:\s*<strong>(.*?)</strong>", p, re.S)
    per = re.search(r"Periodo:\s*<strong>(.*?)</strong>", p, re.S)
    sig = re.search(r"Corpus documental</?[^>]*>.*?(\d\.\d\.[A-Z]\.\d+\.[A-Z]-\d+)", p, re.S)
    y = first_year(f.group(1)) if f else None
    if y is None and per: y = first_year(per.group(1))
    h.add(f"coreecom_{cl}.txt", raw, language="Spanish", year=y, source="COREECOM", url=u,
          dateless_in_window=True, periodo=per.group(1) if per else None)
rep = h.finish(method="Document list page -> each documento1 page; extracted only the paleographic edition (first column); critical edition, summary, description skipped.",
  coverage=f"{len(cls)} documents listed; {len(h.records)} harvested.",
  problems=([f"no paleographic edition found for cl={miss}"] if miss else []) + ["Year from 'Fecha' field, else from 'Periodo' (start year); all documents are within 1500-1599 per the catalogue"])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], miss)
