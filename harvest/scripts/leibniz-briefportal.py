import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
import json, re, html
from lxml import html as LH
h = Harvest("leibniz-briefportal")
U = "https://solr.leibniz.sub.uni-goettingen.de/solr/leibniz/select?q=type:brief&rows=200&wt=json&hl=off&sort=id+asc"
d = json.loads(h.get(U, "files/briefe.json"))
docs = d["response"]["docs"]
LANG = {"lat": "Latin", "deu": "German", "dut": "Dutch", "fra": "French"}
probs = []; undated = 0
for doc in docs:
    v = doc.get("volltext", "")
    v = re.sub(r"<span class=\"space\"\s*/>", " ", v); v = re.sub(r"</(p|div|h\d|li)>|<br\s*/?>", lambda m: m.group(0) + "\n", v)
    frag = LH.fromstring("<root>" + v + "</root>")
    for bad in frag.xpath("//div[@style and contains(@style,'display:none')]"):
        bad.getparent().remove(bad)
    for bad in frag.xpath("//script|//style"):
        bad.getparent().remove(bad)
    text = frag.text_content()
    text = re.sub(r"[ \t]+", " ", text).strip()
    gd = doc.get("datum_gregorianisch") or ""
    y = first_year(gd) or first_year(doc.get("datum_anzeige"))
    if y is None: undated += 1
    lang = LANG.get((doc.get("sprache") or ["lat"])[0], "Latin")
    h.add(doc["id"] + ".txt", text, language=lang, year=y, source="Leibniz, Allgemeiner politischer und historischer Briefwechsel III, %s: %s (%s)" % (doc.get("brief_nummer"), doc.get("korrespondenten_anzeige"), doc.get("datum_anzeige")), url="https://leibniz-briefportal.adw-goe.de/" + doc["id"])
if undated: probs.append(f"{undated} letters without a usable date: year=None, dateless_in_window=False")
probs.append("Letters taken from the portal's public Solr index (solr.leibniz.sub.uni-goettingen.de), field volltext (edited text; variants/graphics are separate index documents and left out; maths markup preamble stripped). Footnote/apparatus inside volltext not separately verified.")
rep = h.finish(method="Portal is an Ember app; its public Solr endpoint (found in the page config) queried once for type:brief (188 documents).",
  coverage="All 188 letters of the portal (series III vol. 5-8), including those from 1701 and undated ones (out of window or undated, kept in staging).", problems=probs)
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], rep["language_words"])
