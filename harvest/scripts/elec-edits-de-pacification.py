import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
h = Harvest("elec-edits-de-pacification")
url = "http://elec.enc.sorbonne.fr/editsdepacification/src/editsdepacification.xml"
raw = h.get(url, "files/editsdepacification.xml")
root = etree.fromstring(raw.encode("utf-8"))
T = "{http://www.tei-c.org/ns/1.0}"
ns = {"t": T[1:-1]}
def unapp(body):
    # keep the lemma (edited text), drop variant readings; remove editorial notes
    for app in list(body.iter(T + "app")):
        lem = app.find(T + "lem")
        par = app.getparent()
        tail = app.tail or ""
        idx = par.index(app)
        new = []
        if lem is not None:
            txt = "".join(lem.itertext())
            new = txt
        else:
            new = ""
        prev = par[idx - 1] if idx > 0 else None
        if prev is not None:
            prev.tail = (prev.tail or "") + new + tail
        else:
            par.text = (par.text or "") + new + tail
        par.remove(app)
for t in root.xpath("//t:group/t:text[t:body]", namespaces=ns):
    tid = t.get("{http://www.w3.org/XML/1998/namespace}id")
    d = t.xpath("./t:front/t:docDate//t:date", namespaces=ns)
    y = first_year(d[0].get("when") or "".join(d[0].itertext())) if d else None
    body = t.find(T + "body")
    unapp(body)
    h.add(f"{tid}.xml", "<text>" + etree.tostring(body, encoding="unicode") + "</text>", language="French", year=y,
          source="Les edits de pacification (ELEC)", url=url + "#" + tid)
print(h.finish(method="Downloaded the complete TEI (src/editsdepacification.xml); one record per <text> (15 edicts/treaties); body only; <app> collapsed to the edited <lem> reading (variants dropped); notes removed by the counter.",
 coverage="all", problems=[]))
