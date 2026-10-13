import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
import re
h = Harvest("religionsfrieden-quellenedition")
base = "https://tueditions.ulb.tu-darmstadt.de/"
idx = h.get(base + "v/pa000001", "files/index.html")
items = re.findall(r'<a href="(pa000001-\d+)"[^>]*>([^<]*)', idx)
src = [(i, l) for i, l in items if l in ("Quellentext", "Deutscher Text", "Französischer Text")]
T = "{http://www.tei-c.org/ns/1.0}"
XML = "{http://www.w3.org/XML/1998/namespace}"
LANG = {"deu": "German", "fra": "French", "lat": "Latin", "ces": "Czech", "cze": "Czech", "ita": "Italian", "eng": "English",
        "pol": "Polish", "nld": "Dutch", "dut": "Dutch", "fre": "French", "ger": "German"}
probs = []
for i, label in src:
    if i == "pa000001-0084":
        probs.append("pa000001-0084 (French/German parallel version of 0083, Toleranzedikt Ludwigs XVI) skipped as duplicate of 0083 containing a German translation")
        continue
    raw = h.get(base + "g/" + i, f"files/{i}.xml")
    root = etree.fromstring(raw.encode("utf-8"), parser=etree.XMLParser(recover=True, huge_tree=True))
    titles = ["".join(t.itertext()) for t in root.find(f"{T}teiHeader/{T}fileDesc/{T}titleStmt").iter(T + "title") if t.get("level") != "s" and "Religiöse Friedenswahrung" not in "".join(t.itertext())]
    title = " ".join(titles[0].split()) if titles else i
    ys = re.findall(r"(?<!\d)(1[4-7]\d\d)(?!\d)", title)
    y = int(ys[-1]) if ys else None
    if y is None:
        probs.append(f"{i}: no year in title '{title}'")
    lg = root.xpath("//t:profileDesc/t:langUsage/t:language/@ident", namespaces={"t": T[1:-1]})
    OVR = {"pa000001-0035": "Italian", "pa000001-0041": "Latin", "pa000001-0049": "Latin", "pa000001-0059": "Dutch"}
    lang = LANG.get(lg[0], lg[0]) if lg else OVR[i]
    if not lg:
        probs.append(f"{i}: no language in header; set to {lang} from the document id/content")
    body = root.find(f"{T}text/{T}body")
    # keep diplomatic <orig>, drop <reg>; editorial notes dropped by the counter
    for r in list(body.iter(T + "reg")):
        par = r.getparent()
        if r.tail:
            prev = r.getprevious()
            if prev is not None: prev.tail = (prev.tail or "") + r.tail
            else: par.text = (par.text or "") + r.tail
        par.remove(r)
    h.add(f"{i}.xml", "<text>" + etree.tostring(body, encoding="unicode") + "</text>", language=lang, year=y,
          source=f"Religionsfrieden-Quellenedition: {title}", url=base + "g/" + i, title=title)
print(h.finish(method="Index page /v/pa000001 parsed for all source-text pages (labels Quellentext / Deutscher Text / Franzoesischer Text; introductions and translations skipped); each TEI from /g/pa000001-NNNN; <choice> reduced to the diplomatic <orig> (modernised <reg> dropped); notes removed by counter.",
 coverage="all source texts listed in the index (some are dated after 1700 and will count out)", problems=probs))
