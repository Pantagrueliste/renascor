import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, copy
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from lxml import etree
h = Harvest("vasto-varchi-storia-fiorentina")
T = "http://www.tei-c.org/ns/1.0"
x = h.get("https://raw.githubusercontent.com/dharc-org/progetto-vasto/master/evt2beta2/data/text/pilot_proemio.xml", "files/pilot_proemio.xml")
root = etree.fromstring(x.encode("utf-8"))
body = copy.deepcopy(root.find(".//{%s}body" % T))
def drop(el):
    p = el.getparent(); prev = el.getprevious()
    if el.tail:
        if prev is not None: prev.tail = (prev.tail or "") + el.tail
        else: p.text = (p.text or "") + el.tail
    p.remove(el)
for tag in ("corr", "reg", "rdg"):
    for el in list(body.iter("{%s}%s" % (T, tag))):
        drop(el)
# the RQ counter drops <app>; unwrap each apparatus entry to its lemma so the base reading is counted
for app in list(body.iter("{%s}app" % T)):
    lem = app.find("{%s}lem" % T)
    p = app.getparent()
    idx = list(p).index(app)
    txt = "".join(lem.itertext()) if lem is not None else ""
    new = etree.Element("{%s}seg" % T); new.text = txt; new.tail = app.tail
    p.replace(app, new)
raw = f'<TEI xmlns="{T}"><teiHeader/><text>' + etree.tostring(body, encoding="unicode") + "</text></TEI>"
h.add("pilot_proemio.xml", raw, language="Italian", year=None, dateless_in_window=True,
      source="Varchi, Storia fiorentina, Proemio (Cors. 1352)", url="https://github.com/dharc-org/progetto-vasto/blob/master/evt2beta2/data/text/pilot_proemio.xml")
print(h.finish(method="raw.githubusercontent.com pilot_proemio.xml (single TEI file); body only; diplomatic layer kept (<orig>, <sic>, <lem>, additions), critical/normalised layer (<corr>, <reg>, <rdg>) removed; deleted/struck passages (<del>) kept as part of the diplomatic transcription.",
  coverage="All that is published: the Proemio (cc. 8r-13r of Cors. 1352).",
  problems=["No date of composition in the file; year=None with dateless_in_window=True because the catalogue documents it as a 16th-century text (Varchi died 1565).", "Word count (3.0k) is below the catalogue figure (3.9k): the RQ counter drops some editorial elements and the apparatus is reduced to its lemma.", "Diplomatic and critical layers share one file; only the diplomatic one was kept."]))
