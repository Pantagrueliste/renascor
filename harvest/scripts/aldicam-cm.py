import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
import json, re
from lxml import html as LH
h = Harvest("aldicam-cm")
B = "https://aldicam.corpuscodea.es/"
inv = json.loads(h.get(B + "inventario2.php", "files/inventario2.json"))
LAT = set("et est quod cum qui quae sunt ab ex sicut etiam autem nostri nostra dei domini anno sit esse tamen vel nec ac".split())
SIGLO = {"XIII": 1250, "XIV": 1350, "XV": 1450, "XVI": 1550, "XVII": 1650, "XVIII": 1750, "XIX": 1850}
probs = []; nolang = 0; ndate_fallback = 0; undated = 0; lat = 0; empty = []
for rec in inv:
    did = re.search(r"title=\"([^\"]+)\"", rec["docID"]).group(1)
    page = h.get(B + f"documento.php?documento={did}&loc=&paleografica=off&abreviaturas=off&mayusculas=off&busqueda=", f"files/{did}.html")
    t = LH.fromstring(page)
    cells = t.xpath("//td[@class='textopaleo']")
    parts = []
    for td in cells:
        for bad in td.xpath(".//span[@class='linea']|.//a[@class='facsimil']|.//img"):
            bad.tail = " " + (bad.tail or "")
            bad.drop_tree()
        parts.append(re.sub(r"[ \t\r\n]+", " ", td.text_content()).strip())
    text = "\n".join(p for p in parts if p)
    if not text:
        empty.append(did)
        continue
    y = first_year(rec["fecha"])
    if y is None:
        hdr = t.xpath("//li[b[contains(text(),'Fecha')]]")
        y = first_year(hdr[0].text_content()) if hdr else None
        if y: ndate_fallback += 1
    if y is None:
        undated += 1
    toks = re.findall(r"[a-z]+", text.lower())
    isl = toks and sum(w in LAT for w in toks) / len(toks) > 0.08
    lang = "Latin" if isl else "Spanish"
    lat += bool(isl)
    h.add(did + ".txt", text, language=lang, year=y, source=f"ALDICAM-CM {did}: {rec['regesto']} ({rec['archivo']}, {rec['fecha']})", url=B + f"documento.php?documento={did}")
if empty: probs.append(f"{len(empty)} documents without paleographic text, skipped: {empty[:20]}")
if undated: probs.append(f"{undated} documents without a year: year=None, dateless_in_window=False")
if ndate_fallback: probs.append(f"{ndate_fallback} documents dated from the document header (inventory gave no year)")
probs.append(f"Language not in the metadata: Spanish assumed, Latin guessed by function-word frequency for {lat} documents.")
probs.append("Paleographic transcription kept (critical text dropped); editorial brackets/marginal remarks and expanded-abbreviation italics stay inside the text; line numbers and facsimile labels removed.")
rep = h.finish(method="Inventory JSON (inventario2.php, all 866 documents) then documento.php per document, paleographic column only.",
  coverage="All 866 documents of the corpus (13th-19th c.); those outside 1450-1700 kept in staging with their year.", problems=probs)
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], rep["undated"])
