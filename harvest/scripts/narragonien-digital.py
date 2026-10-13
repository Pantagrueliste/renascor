import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
import re, html, urllib.parse
h = Harvest("narragonien-digital")
base = "https://www.narragonien-digital.de/exist/materialien/"
page = h.get(base + "downloads.html", "files/downloads.html")
links = re.findall(r'href="(\.\./(?:data/GW|resources/xml)/[^"]+\.xml)"[^>]*>([^<]*)', page)
T = "{http://www.tei-c.org/ns/1.0}"
LANG = {"GW5053": "Low German", "GW5054": "Latin", "GW5061lt": "Latin", "GW5062": "Latin", "GW5058": "French",
        "GW5065": "French", "GW5066": "Dutch"}
def splice(el, replacement_text):
    par = el.getparent(); tail = el.tail or ""
    prev = el.getprevious()
    if prev is not None: prev.tail = (prev.tail or "") + replacement_text + tail
    else: par.text = (par.text or "") + replacement_text + tail
    par.remove(el)
probs = []
for href, label in links:
    url = urllib.parse.urljoin(base, href)
    name = href.rsplit("/", 1)[1][:-4]
    raw = h.get(url, f"files/{name}.xml")
    root = etree.fromstring(raw.encode("utf-8"), parser=etree.XMLParser(recover=True, huge_tree=True))
    body = root.find(f"{T}text/{T}body")
    for r in list(body.iter(T + "reg")):
        r.getparent().remove(r) if False else splice(r, "")
    for ap in list(body.iter(T + "app")):
        lem = ap.find(T + "lem")
        splice(ap, "".join(lem.itertext()) if lem is not None else "")
    for f in list(body.iter(T + "figure")):
        splice(f, "")
    ed = " ".join("".join(root.find(f"{T}teiHeader/{T}fileDesc/{T}editionStmt/{T}edition").itertext()).split())
    y = first_year(html.unescape(label)) or first_year(ed)
    h.add(f"{name}.xml", "<text>" + etree.tostring(body, encoding="unicode") + "</text>", language=LANG.get(name, "German"), year=y,
          source=html.unescape(label), url=url, title=html.unescape(label))
print(h.finish(method="Downloads page parsed for the 12 TEI files; per file the <text><body>, with <choice> reduced to diplomatic <orig> (normalised <reg> dropped) and <app> to its first reading <lem>.",
 coverage="all 12 downloadable TEI files", problems=probs))
