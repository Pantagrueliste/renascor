import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("dipko-schwarzenhorn-1649")
ids = ["rb", "fr", "gb", "i.481217", "ni.481217"] + [f"l.{d}" for d in """490117 490119 490120 490205 490222 490226 490304 490322 490328 490402 490408 490415 490418 490428 490430 490501 490508 490510 490521 490531 490602 490701 490805 490813 490915 490917""".split()]
nodate = []
for oid in ids:
    url = f"https://gams.uni-graz.at/o:dipko.{oid}/TEI_SOURCE"
    xml = h.get(url, f"files/{oid}.xml")
    y = None
    m = re.search(r"<origDate\b[^>]*>(.*?)</origDate>", xml, re.S)
    if m: y = first_year(re.sub(r"<[^>]+>", "", m.group(0)))
    if not y and m: y = first_year(m.group(0))
    if not y:
        m = re.search(r'<date\b[^>]*\bwhen="(\d{4})', xml[xml.find("<text"):])
        y = int(m.group(1)) if m else None
    if not y:
        mm = re.search(r"\.(\d\d)\d{4}$", oid)
        if mm: y = 1600 + int(mm.group(1))  # id encodes yymmdd
    if oid == "rb": y = 1650
    if oid in ("i.481217", "ni.481217"): y = 1648
    tx = xml[xml.find("<text"):]
    tx = re.sub(r"<figDesc\b.*?</figDesc>", "", tx, flags=re.S)
    tx = re.sub(r"<note\b.*?</note>", "", tx, flags=re.S)
    raw = '<TEI xmlns="http://www.tei-c.org/ns/1.0">' + tx
    h.add(f"dipko.{oid}.xml", raw, language="German", year=y, source="DIPKO Schwarzenhorn Internuntiatur 1649", url=url)
print([ (r["filename"], r["year"]) for r in h.records])
print(h.finish(method="Fetched /o:dipko.<id>/TEI_SOURCE for the 31 objects (travel diary rb, instruction i, secondary instruction ni, 26 letters l.*, final report fr, secret report gb), listed from the context pages; raw = <text> with notes and figure descriptions removed. Year from origDate (diary: date of the 1650 fair copy) else first body date else the yymmdd in the object id.",
  coverage="All 31 texts (registers, introductions and commentary objects excluded).",
  problems=["Ids of fr/gb identified from the navigation (o:dipko.fr, o:dipko.gb); check that they are the final and the secret report."]))
