import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from lxml import etree
import tarfile, io, re
h = Harvest("wandering-jews-chronicle")
tgz = h.get("https://codeload.github.com/gbergel/WJC/tar.gz/master", "files/WJC-master.tar.gz", binary=True)
xml = None
with tarfile.open(fileobj=io.BytesIO(tgz)) as tf:
    for m in tf.getmembers():
        if m.name.endswith("WJC/WJC.xml"):
            xml = tf.extractfile(m).read()
(h.dir / "files" / "WJC.xml").write_bytes(xml)
root = etree.fromstring(xml)
T = "{http://www.tei-c.org/ns/1.0}"
wits = [w.get("{http://www.w3.org/XML/1998/namespace}id") for w in root.iter(T + "witness")]
body = root.find(f"{T}text/{T}body")
def render(el, wit):
    out = []
    if el.text: out.append(el.text)
    for c in el:
        name = etree.QName(c).localname
        if name == "app":
            for r in c.findall(T + "rdg"):
                if "#" + wit in r.get("wit", "").split():
                    out.append(render(r, wit))
        elif name in ("pb", "note"):
            pass
        else:
            out.append(render(c, wit))
        if c.tail: out.append(c.tail)
    return "".join(out)
years = {"A.2.a": 1634, "C.1.a": 1680, "C.2.a": 1680, "C.3.a": 1680, "J.1.2.a": 1830}
for w in wits:
    lines = []
    for l in body.iter(T + "l"):
        s = " ".join(render(l, w).split())
        if s: lines.append(s)
    y = years.get(w, 1750)
    h.add(f"WJC_{w}.txt", "\n".join(lines), language="English", year=y,
          source="The Wandering Jew's Chronicle", url="https://github.com/gbergel/WJC")
print(h.finish(method="GitHub tarball of gbergel/WJC; parallel-segmentation TEI (WJC/WJC.xml) reduced to one plain-text reading per witness by selecting the <rdg> of each witness in every <app>; bibliographic header/front excluded.",
 coverage="all 15 copies reconstructed (4 pre-1700 witnesses A.2.a, C.1.a, C.2.a, C.3.a are the in-window ones)",
 problems=["Witness dates are not in the TEI: years are approximate placeholders (A.2.a=1634 per resource period start; C.1-3=1680 'Charles II versions, before 1700'; 18th-century copies=1750; J.1.2.a=1830 19th century) taken from the resource description, not exact imprint dates."]))
