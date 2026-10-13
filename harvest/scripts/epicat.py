import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
h = Harvest("epicat")
hist = json.loads(h.get("https://epicat.uab.cat/api?histograma", "files/histograma.json"))
LANG = {"català": "Catalan", "castellà": "Spanish", "espanyol": "Spanish", "llatí": "Latin", "francès": "French", "italià": "Italian"}
empty = []
for x in hist:
    if not (1450 <= x["any"] <= 1700): continue
    cid = x["id_carta"]
    u = f"https://epicat.uab.cat/items/carta/{cid}"
    p = h.get(u, f"files/carta_{cid}.html")
    s = BeautifulSoup(p, "html.parser")
    box = s.select_one("div.alert-warning")
    if not box:
        empty.append(cid); continue
    txt = "\n".join(pp.get_text(" ", strip=True) for pp in box.find_all("p")) or box.get_text("\n", strip=True)
    lang = "Catalan"
    for dt in s.find_all("dt"):
        if dt.get_text(strip=True) == "Idioma":
            v = dt.find_next("dd").get_text(strip=True).lower()
            lang = LANG.get(v, v.capitalize())
    h.add(f"epicat_carta_{cid}.txt", txt, language=lang, year=x["any"], source="EPICAT", url=u)
rep = h.finish(method="Year histogram endpoint (api?histograma) lists every letter id with its year; fetched each letter page dated 1450-1700 and kept the transcription box (div.alert-warning) only; metadata, summaries and apparatus dropped.",
  coverage=f"All {len(h.records)} letters dated 1526-1699 listed by the site histogram; letters after 1700 not fetched.",
  problems=[f"letters without transcription box: {empty}"] if empty else [])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], empty)
