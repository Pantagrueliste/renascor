import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, urllib.parse
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, tei_year, first_year, slug
h = Harvest("h15corpus", delay=0.6)
B = "https://historia15.us.es/H15corpus/xmlfiles/"
idx = h.get(B, "files/index.html")
names = list(dict.fromkeys(re.findall(r'href="([^"?/][^"]*\.xml)"', idx)))
skipped = []
undated = 0
for nm in names:
    dn = urllib.parse.unquote(nm)
    if re.search(r"prueba|test", dn, re.I):
        skipped.append(dn); continue
    raw = h.get(B + nm, "files/" + slug(dn))
    y = tei_year(raw)
    if y is None:
        m = re.search(r'<origDate[^>]*>([^<]*)', raw)
        y = first_year(m.group(1)) if m else None
    if y is None: undated += 1
    t = re.search(r"<title>([^<]+)</title>", raw)
    h.add(dn, raw, language="Spanish", year=y, source="H15corpus: " + (t.group(1)[:120] if t else dn), url=B + nm)
rep = h.finish(method="Listed the Apache index of xmlfiles/ and downloaded each TEI XML file; year from origDate/date in the TEI header.",
  coverage=f"All {len(h.records)} non-test files of the directory ({len(names)} listed; skipped {len(skipped)} files named prueba/test).",
  problems=[f"{undated} documents without a date (year=None, dateless_in_window=False), mostly Bolea collection.",
            "Skipped test files: " + ", ".join(skipped), "Catalogue says 410 documents; directory index lists %d xml files." % len(names)])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], undated)
