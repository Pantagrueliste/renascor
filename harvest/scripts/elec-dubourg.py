import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
import re
h = Harvest("elec-dubourg")
url = "http://elec.enc.sorbonne.fr/dubourg/src/dubourg.xml"
raw = h.get(url, "files/dubourg.xml")
root = etree.fromstring(raw.encode("utf-8"))
ns = {"t": "http://www.tei-c.org/ns/1.0"}
texts = root.xpath("//t:group//t:text[t:body]", namespaces=ns)
for t in texts:
    tid = t.get("{http://www.w3.org/XML/1998/namespace}id")
    d = t.xpath("./t:front/t:docDate//t:date", namespaces=ns)
    y = None
    if d:
        y = first_year(d[0].get("when") or "".join(d[0].itertext()))
    if y is None:
        fd = "".join(t.xpath("./t:front/t:docDate", namespaces=ns)[0].itertext()) if t.xpath("./t:front/t:docDate", namespaces=ns) else ""
        y = first_year(fd)
    # keep only body (transcription); drop front
    body = t.xpath("./t:body", namespaces=ns)[0]
    s = etree.tostring(body, encoding="unicode")
    h.add(f"{tid}.xml", "<text>" + s + "</text>", language="French", year=y, source="La correspondance du chancelier Antoine Du Bourg (ELEC)", url=url + "#" + tid)
print(h.finish(method="Downloaded the complete TEI file and split it into its <text> units (letters + Great Bible inquiry); body only, front matter (summary, tradition) excluded.",
 coverage="all", problems=[]))
