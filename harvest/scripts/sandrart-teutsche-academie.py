import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, io, tarfile
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from lxml import etree
h = Harvest("sandrart-teutsche-academie")
url = "http://ta.sandrart.net/data/tei-noentities.tgz"
tb = h.get(url, "files/tei-noentities.tgz", binary=True)
xml = tarfile.open(fileobj=io.BytesIO(tb)).extractfile("tei-noentities/tei.xml").read()
ns = {"t": "http://www.tei-c.org/ns/1.0"}
root = etree.fromstring(xml)
texts = root.xpath("/t:TEI/t:text/t:group/t:text", namespaces=ns)
print(len(texts), [t.get("{http://www.w3.org/XML/1998/namespace}id") for t in texts])
YEARS = {"ta1675": 1675, "ta1679": 1679}
for t in texts:
    tid = t.get("{http://www.w3.org/XML/1998/namespace}id") or "text"
    s = etree.tostring(t, encoding="unicode")
    raw = '<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader/>' + s + "</TEI>"
    year = YEARS.get(tid, 1680 if "1680" in tid or "icon" in tid.lower() else None)
    print(tid, year, len(raw))
    h.add(f"{tid}.xml", raw, language="German", year=year, source="Sandrart.net, Teutsche Academie",
          url="https://ta.sandrart.net/de/info/technik/tei-download/")
print(h.finish(method="Downloaded the TEI P5 'without named entities' archive (tei-noentities.tgz, 2013); split the group of three <text> elements into one record each (Teutsche Academie 1675 Part I, 1679 Part II, Iconologia Deorum 1680).",
  coverage="All of the TEI file (three printed parts). Scholarly annotations/commentary are not in this file variant.",
  problems=["Years taken from the xml:id/project description of the three parts (1675, 1679, 1680); check filenames.", "Licence not stated on the site.", "RQ counter gives 648,260 words in <body> (notes dropped) against the catalogue figure of about 426,000; the catalogue count may have used a different method."]))
