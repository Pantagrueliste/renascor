import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
import xml.etree.ElementTree as ET
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("urfehdebuecher-basel-x")
U = "https://gams.uni-graz.at/o:ufbas.1563/TEI_SOURCE"
src = h.get(U, "files/ufbas.1563.xml")
NS = "{http://www.tei-c.org/ns/1.0}"
root = ET.fromstring(src.encode("utf-8"))
body = root.find(f"{NS}text/{NS}body")
cur = 1563
n = 0
undated = 0
def walk(el):
    global cur, n, undated
    for ch in el:
        if ch.tag in (NS + "div", NS + "p") and ch.get("ana") == "#uf_Eintrag":
            ds = [d.get("when") for d in ch.iter(NS + "date") if d.get("when")]
            ud = [d.get("when") for d in ch.iter(NS + "date") if d.get("ana") == "#uf_DatumUrfehde" and d.get("when")]
            y = first_year((ud or [None])[0]) or cur
            xs = ET.tostring(ch, encoding="unicode")
            xs = re.sub(r' xmlns(:\w+)?="[^"]+"', "", xs)
            xs = re.sub(r"\bns\d+:", "", xs)
            raw = f'<TEI><teiHeader/><text><body>{xs}</body></text></TEI>'
            n += 1
            h.add(f"{ch.get('{http://www.w3.org/XML/1998/namespace}id')}.xml", raw, language="German", year=y,
                  source="Urfehdebuch X (Basel, StABS Ratsbücher O 10)", url=U)
        else:
            if ch.tag == NS + "head":
                for d in ch.iter(NS + "date"):
                    if d.get("when") and first_year(d.get("when")): cur = first_year(d.get("when"))
            walk(ch)
walk(body)
rep = h.finish(method="Downloaded the single TEI_SOURCE file from GAMS and split it into one record per Urfehde entry (div ana=#uf_Eintrag); year from the entry's Urfehde date, else the year heading.",
  coverage="All entries of Urfehdebuch X (1563-1569).",
  problems=["Entry count %d (catalogue says 626; the file has 625 uf_Eintrag ids, one being a p nested in another entry); year-heading fallback used where an entry has no dated Urfehde." % n,
            "Record raw includes entry text and marginal notes; page-break/year headings outside entries are not included."])
print(n, rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
