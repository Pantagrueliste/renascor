import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
B = "https://quellen.perspectivia.net/de/russische_relationen/"
h = Harvest("relationen-vom-russischen-hof")
idx = json.loads(h.get(B + "indices/index_of_documents.json", "files/index_of_documents.json"))["data"]
probs = []
rows = [r for r in idx if r.get("14") == "Ja"]
for r in rows:
    did = re.sub(r"<[^>]+>", "", r["0"]).strip()
    try:
        s = h.get(B + did, f"files/{did}.html")
    except Exception as e:
        probs.append(f"fetch failed {did}: {e}"); continue
    sp = BeautifulSoup(s, "html.parser")
    meta = {}
    for tr in sp.select("table.mapping tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td: meta[th.get_text(" ", strip=True)] = td.get_text(" ", strip=True)
    src = sp.select_one("article.source")
    if not src:
        probs.append(f"no source article {did}"); continue
    for x in src.select("small.note, meta, a.note, span.non-source.note"):
        x.decompose()
    txt = src.get_text("\n", strip=True)
    txt = re.sub(r"[ \t]+\n", "\n", txt)
    y = None
    for k in ("Absendedatum", "Absendedatum gregor.", "Absendedatum julian.", "Empfängerdatum"):
        y = first_year(meta.get(k)) or y
        if y: break
    if not y:
        y = first_year(meta.get("Fundort"))
        if y: probs.append(f"{did}: year {y} taken from Fundort (no date)")
    if not y:
        probs.append(f"{did}: no year found")
    h.add(f"{did}.txt", txt, language="German", year=y, source="Relationen vom russischen Hof", url=B + did)
probs.append("Transcripts include editorial expansions (<ins>) of abbreviations as text; editorial notes and metadata table dropped. Most documents (1725-1728) are outside the window and kept in staging with their year.")
rep = h.finish(method="index_of_documents.json lists items with 'Transkript verfügbar? = Ja'; fetched each document page; kept article.source text minus notes/meta",
               coverage=f"{len(h.records)} of {len(rows)} transcribed documents (whole edition, 1690-1728); the in-window share is 1690-1696",
               problems=probs)
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")})
