import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from lxml import etree
h = Harvest("guicciardini-storia-italia")
T = "http://www.tei-c.org/ns/1.0"
x = h.get("https://guicciardini-storia-italia.huma-num.fr/files/SI_Ms_30_3juillet2019H.xml", "files/SI_Ms_30_3juillet2019H.xml")
x = re.sub(r"<!DOCTYPE[^>]*>", "", x)
root = etree.fromstring(x.encode("utf-8"))
def drop(el, keep_tail=True):
    p = el.getparent(); prev = el.getprevious()
    if el.tail and keep_tail:
        if prev is not None: prev.tail = (prev.tail or "") + el.tail
        else: p.text = (p.text or "") + el.tail
    p.remove(el)
n = 0
for d in root.xpath("//t:body/t:div[@subtype='edition_text']", namespaces={"t": T}):
    did = d.get("{http://www.w3.org/XML/1998/namespace}id")
    if d.get("n", "").startswith("Ed01"):
        continue   # 1919 printed edition
    import copy
    d = copy.deepcopy(d)
    for tag in ("reg", "metamark"):      # cancelled words, editorial regularisation, insertion marks
        for el in list(d.iter("{%s}%s" % (T, tag))):
            if el.getparent() is not None: drop(el)
    raw = f'<TEI xmlns="{T}"><teiHeader/><text><body>' + etree.tostring(d, encoding="unicode") + "</body></text></TEI>"
    h.add(f"{did}.xml", raw, language="Italian", year=None, dateless_in_window=True,
          source="Guicciardini, Storia d'Italia, exordium, " + d.get("n", ""), url="https://guicciardini-storia-italia.huma-num.fr/files/SI_Ms_30_3juillet2019H.xml")
    n += 1
print(h.finish(method="Downloaded the TEI file; one record per transcribed section (div[@subtype=edition_text]) of the manuscripts (Ms01-Ms08); editorial <reg> and insertion marks removed, cancelled words (<del>) and additions both kept as in a diplomatic transcription; the Gherardi 1919 printed edition (Ed01) excluded.",
  coverage="All 14 manuscript transcription sections in the TEI file.",
  problems=["The file carries no dates for the manuscripts; year=None with dateless_in_window=True because the catalogue documents the drafts as 1537-1540 (exordium of the Storia d'Italia, written c.1537-1540).", "Successive drafts of the same opening passage overlap heavily (not duplicates in the strict sense: different redactions)."]))
