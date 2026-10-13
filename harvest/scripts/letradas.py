import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest, first_year
from lxml import etree
h = Harvest("letradas")
problems = []
idx = h.get("https://corpora.uah.es/letradas/documentos", "files/documentos.html")
ids = sorted(set(re.findall(r"xmlfiles/(LETRADAS-\d+)\.xml", idx)))
for i in ids:
    try:
        s = h.get(f"https://corpora.uah.es/letradas/xmlfiles/{i}.xml", f"files/{i}.xml")
    except Exception as e:
        problems.append(f"{i}: fetch failed {e}"); continue
    root = etree.fromstring(s.encode("utf-8"))
    od = root.find(".//origDate")
    year = None
    if od is not None:
        for a in ("when", "notBefore", "from"):
            if od.get(a) and first_year(od.get(a)): year = first_year(od.get(a)); break
        if year is None: year = first_year("".join(od.itertext()))
    seg = root.find(".//seg[@type='f']")
    if seg is None:
        seg = root.find(".//text")
        problems.append(f"{i}: no seg f, used whole text")
    for el in list(seg.iter("dtok", "ee")):
        p = el.getparent(); t = el.tail; prev = el.getprevious()
        if t:
            if prev is not None: prev.tail = (prev.tail or "") + t
            else: p.text = (p.text or "") + t
        p.remove(el)
    txt = re.sub(r"\s+", " ", "".join(seg.itertext())).strip()
    raw = "<TEI><text><body><p>" + html.escape(txt, quote=False) + "</p></body></text></TEI>"
    if year is None: problems.append(f"{i}: undated")
    h.add(i + ".xml", raw, language="Spanish", year=year, source="Letradas " + i, url=f"https://corpora.uah.es/letradas/xmlfiles/{i}.xml")
rep = h.finish(method="Listing page /letradas/documentos -> per-document TEITOK XML (xmlfiles/<id>.xml); kept diplomatic seg type=f (token surface form, expansions kept as written), dropped normalised forms (nform/mform) and seg type=m; year from msDesc origDate",
    coverage="All 270 documents of the corpus (1400-1900) staged; those outside 1450-1700 or overlapping are dated by first year of origDate and counted by year.",
    problems=problems[:40] + (["...more"] if len(problems) > 40 else []))
print(json.dumps({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window","undated")}), problems[:5])
