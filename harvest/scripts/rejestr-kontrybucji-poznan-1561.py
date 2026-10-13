import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from lxml import etree
h = Harvest("rejestr-kontrybucji-poznan-1561")
url = "https://exist.lhdb.kul.pl/exist/apps/1561/api/document/spisy_1561.xml"
raw = h.get(url, "files/spisy_1561.xml")
root = etree.fromstring(raw.encode("utf-8"))
ns = {"t": "http://www.tei-c.org/ns/1.0"}
for d in root.xpath("//t:body/t:div[@xml:id]", namespaces=ns):
    i = d.get("{http://www.w3.org/XML/1998/namespace}id")
    h.add(f"{i}.xml", "<text><body>" + etree.tostring(d, encoding="unicode") + "</body></text>", language="Latin", year=1561,
          source="Rejestr kontrybucji diecezji poznanskiej z 1561 r.", url=url)
print(h.finish(method="Downloaded the single TEI file; one record per manuscript div (ASK91, ASK3); the 'notes' div (modern editorial) excluded.",
 coverage="all", problems=["Year 1561 set from the register's date (resource-level), not a per-text header date."]))
