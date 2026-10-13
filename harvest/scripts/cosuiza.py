import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
h = Harvest("cosuiza")
B = "https://grafila.unil.ch/cosuiza/"
ids = []
for start in (0, 30, 60, 90, 120):
    pg = h.get(B + f"index.php?action=stats&start={start}", f"files/stats_{start}.html")
    ids += re.findall(r"cid=([^'\"&>]+?\.xml)", pg)
ids = sorted(set(ids))
print(len(ids), "documents in stats")
P = etree.XMLParser(recover=True, huge_tree=True)
probs = []
undated = 0
for i in ids:
    i = i[:-4]
    try:
        x = h.get(B + f"xmlfiles/{i}.xml", f"files/{i}.xml")
    except Exception as e:
        probs.append(f"{i}: {e}"); continue
    root = etree.fromstring(x.encode("utf-8"), P)
    yr = None
    for od in root.iter("origDate"):
        for a in ("when", "notBefore", "from", "notAfter", "to"):
            if od.get(a) and first_year(od.get(a)):
                yr = first_year(od.get(a)); break
        if yr is None:
            yr = first_year("".join(od.itertext()))
        if yr: break
    undated += yr is None
    toks = []
    for t in root.iter("tok"):
        if any(a.tag == "tok" for a in t.iterancestors()):
            continue
        s = "".join(c for c in t.xpath("descendant-or-self::*[not(self::lb) and not(self::figure) and not(self::dtok)]/text()"))
        s = re.sub(r"\s+", "", s) if False else s.strip()
        if s: toks.append(s)
    txt = " ".join(toks)
    h.add(f"{i}.xml", txt, language="Spanish", year=yr, source="COSUIZA", url=B + f"xmlfiles/{i}.xml")
probs.append(f"{undated} of {len(ids)} documents have no date in the TEI header: year=None, dateless_in_window=False, so not counted in window (the corpus covers 1483-1951; some undated ones may be in window).")
probs.append("Text reconstructed from the TEITOK <tok> elements (abbreviation expansions <ex> included); some documents may be in languages other than Spanish (not checked).")
print(h.finish(method="Document ids from the stats pages (action=stats&start=...), raw TEITOK XML from /cosuiza/xmlfiles/<id>.xml; plain text built from <tok> contents (transcription with expansions), without facsimile coordinates, lemmas or annotations; year from origDate.",
  coverage=f"All {len(ids)} documents listed on the statistics pages (catalogue: 123).", problems=probs))
