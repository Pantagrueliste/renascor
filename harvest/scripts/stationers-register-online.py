import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, collections
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("stationers-register-online")
s = h.get("https://stationersregister.online/api/allEntries", "files/allEntries.xml")
es = re.findall(r"<entry>.*?</entry>", s, re.S)
rows = []
for x in es:
    i = int(re.search(r"<docid>SRO(\d+)", x).group(1))
    rows.append((i, x))
rows.sort()
prev = None
NOTE = re.compile(r'<note\b[^>]*resp="#arber"[^>]*>.*?</note>', re.S)
n_est = 0
n_empty = 0
pvol = None
for i, x in rows:
    mi = re.search(r"<items>(.*?)</items>", x, re.S)
    items = mi.group(1) if mi else ""
    if not items.strip():
        n_empty += 1
    vol = re.sub(r"\s+", " ", re.search(r"<from>\s*<title>(.*?)</title>", x, re.S).group(1))
    if vol != pvol:
        prev = None; pvol = vol
        lo, hi = {"A": (1554, 1596), "B": (1576, 1595), "C": (1595, 1620), "V": (1618, 1640)}[("V" if "Volume 4" in vol else vol.split("Register ")[-1][0] if "Register A" in vol else "B" if "Liber [Register] B" in vol else "C")]
    body = NOTE.sub("", items)
    ys = [int(m) for m in re.findall(r'<date\b[^>]*\bwhen="(\d{4})', x[x.find("<date"):].replace("<date/>", "")) ]
    y = None
    for c in ys:
        if lo <= c <= hi and (prev is None or -1 <= c - prev <= 10):
            y = c; break
    if y is None:
        y = prev if prev is not None else lo
        n_est += 1
    prev = y
    raw = '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>' + body + "</body></text></TEI>"
    h.add(f"SRO{i}.xml", raw, language="English", year=y, source="Stationers' Register Online", url=f"https://stationersregister.online/api/allEntries#SRO{i}", register=vol)
print(h.finish(method="Downloaded the full TEI XML from /api/allEntries (33 MB, 10,453 entries); one record per entry (docid SRO<n>), raw = entry <items> text only (people metadata and Arber's editorial notes removed). Year = first dated element in the entry consistent with the running chronology, else carried forward from the previous entry (entries are in chronological order by docid).",
  coverage="All 10,453 entries (Registers A, B, C and Arber vol. 4 transcript; 1554-1640).",
  problems=[f"{n_empty} entries have empty <items> (kept as empty records). ", f"{n_est} entries have no usable own date: year carried forward from the preceding entry (approximate; all fall in 1554-1640 anyway).", "Dates inside titles of printed works (not the entry date) may occasionally mislead; guarded by a non-decreasing-chronology check (-1..+10 years vs the running year).", "Eyre and Rivington series (1640-1708) not present in the API data."]))
