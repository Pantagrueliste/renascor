import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
import re
h = Harvest("st-galler-missiven")
base = "https://missiven.stadtarchiv.ch/"
lst = h.get(base + "api/collection?per-page=1000", "files/collection.html")
ids = re.findall(r'href="missiven/(stasg_missiv_\d+)"', lst)
ids = list(dict.fromkeys(ids))
dates = {}
for m in re.finditer(r'href="missiven/(stasg_missiv_\d+)"[^>]*>[^<]*</a>\s*<div class="tei-profileDesc tei-profileDesc1">([^<]*)</div>', lst):
    dates[m.group(1)] = m.group(2)
probs = []
fails = []
for i in ids:
    try:
        raw = h.get(base + "api/document/" + i, f"files/{i}.xml")
    except Exception as e:
        fails.append(f"{i}: {e}"); continue
    y = None
    m = re.search(r'<correspAction type="sent".*?</correspAction>', raw, re.S)
    if m:
        d = re.search(r"<date\b[^>]*>([^<]*)</date>", m.group(0))
        if d: y = first_year(d.group(1))
    if y is None: y = first_year(dates.get(i))
    if y is None:
        d = re.search(r'<origDate\b[^>]*when="([^"]+)"', raw)
        if d: y = first_year(d.group(1))
    if y is None: probs.append(f"{i}: no date")
    h.add(f"{i}.xml", raw, language="German", year=y, source="Briefverkehr der Stadt St. Gallen (Missiven)", url=base + "api/document/" + i)
print(h.finish(method="Collection listing (api/collection?per-page=1000, all 808 on one page) parsed for ids; each TEI fetched from /api/document/<id>; year from correspAction type=sent date, fallback listing date.",
 coverage="all documents in the listing" + (f" except {len(fails)} fetch failures" if fails else ""), problems=probs + fails))
