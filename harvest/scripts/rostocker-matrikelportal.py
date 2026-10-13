import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, slug
h = Harvest("rostocker-matrikelportal")
B = "http://matrikel.uni-rostock.de"
per = []
for blk in ("1419", "1450", "1500", "1550", "1600", "1650"):
    pg = h.get(f"{B}/semlist.action?nav=stud_matrikel1419_{blk}", f"files/semlist_{blk}.html")
    for pid in re.findall(r"/periode/([0-9]{4}(?:Ost|Mich))", pg):
        if pid not in per: per.append(pid)
per = [p for p in per if 1450 <= int(p[:4]) <= 1700]
problems = []; empty = []
def cell(td):
    td = re.sub(r'<span class="light">.*?</span>', "", td, flags=re.S)   # editor's normalised forms
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", td))).strip()
nent = 0
for pid in per:
    try: pg = h.get(f"{B}/periode/{pid}", f"files/periode_{pid}.html")
    except Exception as e: problems.append(f"{pid}: {e}"); continue
    y = int(pid[:4])
    rows = re.findall(r"<tr onclick=\"window.location.href='/id/(\d+)'\">(.*?)</tr>", pg, re.S)
    if not rows: empty.append(pid)
    for eid, row in rows:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(tds) < 4: continue
        txt = " ".join(x for x in (cell(tds[1]), cell(tds[2]), cell(tds[3])) if x and x != "-")
        if not txt: continue
        h.add(f"{eid}.txt", txt, language="Latin", year=y, source="Rostocker Matrikelportal, Immatrikulationen 1419-1831", url=f"{B}/id/{eid}", semester=pid)
if empty: problems.append(f"{len(empty)} semester pages without entries (e.g. semesters with 0 matriculations): {empty[:10]}")
problems += ["Each record is a short matriculation entry (forename, surname, origin in the original Latin/Latinised spelling; editor's bracketed normalised forms removed), not running text; only the 3 transcription columns on the semester list pages were taken (the per-entry pages, 33,000+ requests, exceed the request cap and add only date, number and user comments).",
 "Entries are labelled Latin although some names/origins are German or Low German; year = year of the semester start (Easter/Michaelis).",
 "Faculty books (Dekanbuecher, c. 7,500 entries), the Buetzow matriculation and years after 1700 were not harvested."]
print(h.finish(method="Semester list pages (semlist.action blocks 1419-1650 -> /periode/<year><Ost|Mich>); one record per matriculation row, columns Vorname/Nachname/Herkunft (transcription) kept.",
 coverage=f"{len(h.records)} entries from {len(per)} semesters, summer 1450 to winter 1699/1700 of the Immatrikulationen 1419-1831 database.", problems=problems))
