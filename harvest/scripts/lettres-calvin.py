import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, io, re, tarfile
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
h = Harvest("lettres-calvin")
T = "http://www.tei-c.org/ns/1.0"
tb = h.get("https://codeload.github.com/pippaJeanne/lettres-calvin/tar.gz/main", "files/lettres-calvin-main.tar.gz", binary=True)
tf = tarfile.open(fileobj=io.BytesIO(tb))
probs = []
for m in sorted(tf.getmembers(), key=lambda m: m.name):
    mm = re.fullmatch(r"[^/]+/src/lib/xml/([^/]+\.xml)", m.name)
    if not mm: continue
    root = etree.fromstring(tf.extractfile(m).read())
    for el in list(root.iter("{%s}reg" % T)):   # modernised readings
        p = el.getparent(); prev = el.getprevious()
        if el.tail:
            if prev is not None: prev.tail = (prev.tail or "") + el.tail
            else: p.text = (p.text or "") + el.tail
        p.remove(el)
    d = root.xpath("//t:correspAction[@type='sent']/t:date", namespaces={"t": T})
    yr = first_year(d[0].get("when") or "".join(d[0].itertext())) if d else None
    if yr is None:
        yr = first_year(mm.group(1)); probs.append(f"{mm.group(1)}: year from file name")
    h.add(mm.group(1), etree.tostring(root, encoding="unicode"), language="French", year=yr,
          source="Lettres de Calvin (Bonnet 1854 base text)", url="https://github.com/pippaJeanne/lettres-calvin/blob/main/src/lib/xml/" + mm.group(1))
probs.append("Spanish translations (src/lib/xmles) and the modernised French (<reg> readings) excluded; footnotes are <note> and dropped by the counter. The base text is Bonnet's 1854 edition of 16th-century letters (spelling as in Bonnet).")
print(h.finish(method="GitHub tarball (codeload) of pippaJeanne/lettres-calvin main; src/lib/xml/*.xml; <reg> removed, <orig> kept; year from correspAction[sent]/date.",
  coverage="All 27 French TEI letters in the repository (the planned corpus has 120).", problems=probs))
