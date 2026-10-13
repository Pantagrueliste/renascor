import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
import re
h = Harvest("hearth-tax-digital")
base = "https://gams.uni-graz.at"
page = h.get(base + "/archive/objects/context:htx/methods/sdef:Context/get?mode=records", "files/records.html")
pids = list(dict.fromkeys(re.findall(r'href="/(o:htx[^"/]*)/TEI_SOURCE"', page)))
T = "{http://www.tei-c.org/ns/1.0}"
def splice(el, txt=""):
    par = el.getparent(); tail = el.tail or ""
    prev = el.getprevious()
    if prev is not None: prev.tail = (prev.tail or "") + txt + tail
    else: par.text = (par.text or "") + txt + tail
    par.remove(el)
probs = []; fails = []
for pid in pids:
    try:
        raw = h.get(f"{base}/{pid}/TEI_SOURCE", f"files/{pid}.xml")
    except Exception as e:
        fails.append(f"{pid}: {e}"); continue
    root = etree.fromstring(raw.encode("utf-8"), parser=etree.XMLParser(recover=True, huge_tree=True))
    title = " ".join("".join(root.find(f"{T}teiHeader/{T}fileDesc/{T}titleStmt/{T}title").itertext()).split())
    d = root.find(f"{T}teiHeader/{T}fileDesc/{T}titleStmt/{T}title/{T}date")
    y = first_year(d.get("when")) if d is not None and d.get("when") else first_year(title)
    if y is None:
        y = first_year(re.sub(r"\s+", " ", title))
    if y is None: probs.append(f"{pid}: no year in title '{title}'")
    body = root.find(f"{T}text/{T}body")
    for r in list(body.iter(T + "reg")):
        splice(r)  # modern English regularisation/translation of the original
    h.add(f"{pid}.xml", "<text>" + etree.tostring(body, encoding="unicode") + "</text>", language="English", year=y,
          source=f"Hearth Tax Digital: {title}", url=f"{base}/{pid}", title=title)
print(h.finish(method="Records page of context:htx parsed for all TEI_SOURCE links (one TEI per assessment); body kept with <choice> reduced to the original-text <orig> (editorial <reg> translation/regularisation dropped); notes dropped by the counter.",
 coverage="all linked TEI assessments" + (f" except {len(fails)} failures" if fails else ""), problems=probs + fails))
