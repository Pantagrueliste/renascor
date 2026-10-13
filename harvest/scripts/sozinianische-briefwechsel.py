import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("sozinianische-briefwechsel")
URL = "https://sozinianer.mni.thm.de/graphql"
LANG = {"lat":"Latin","fre":"French","fra":"French","ger":"German","deu":"German","pol":"Polish","dut":"Dutch","nld":"Dutch","ita":"Italian","eng":"English","grc":"Greek","gre":"Greek","heb":"Hebrew","spa":"Spanish","cze":"Czech","ces":"Czech","hun":"Hungarian","swe":"Swedish","niederländisch":"Dutch","deutsch":"German","lateinisch":"Latin","französisch":"French","polnisch":"Polish","italienisch":"Italian"}
import time, os
def gql(q, rel):
    p = h.dir / rel
    if p.exists():
        return json.loads(p.read_text())
    w = h.delay - (time.time() - h._last)
    if w > 0: time.sleep(w)
    r = h.s.post(URL, json={"query": q}, timeout=120); h._last = time.time(); r.raise_for_status()
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(r.text)
    return r.json()
lst = gql("{ communications { guid dateStart sentBy attached{guid} } }", "files/communications.json")["data"]["communications"]
ids = [c["guid"] for c in lst]
dates = {c["guid"]: c["dateStart"] for c in lst}
for c in lst:
    for a in (c.get("attached") or []):
        if a["guid"] not in dates: ids.append(a["guid"]); dates[a["guid"]] = c["dateStart"]
ids = list(dict.fromkeys(ids))
F = "guid dateStart letter{guid label doctype variants{guid label metadataLanguage metadataTextType metadataTextGenre metadataIsReference text}}"
B = 25
for i in range(0, len(ids), B):
    chunk = ids[i:i+B]
    q = "{ " + " ".join(f'a{j}: communication(id:"{g}"){{ {F} }}' for j, g in enumerate(chunk)) + " }"
    d = gql(q, f"files/batch_{i:05d}.json")
    for j, g in enumerate(chunk):
        c = (d.get("data") or {}).get(f"a{j}")
        if not c or not c.get("letter"): continue
        L = c["letter"]
        y = first_year(c.get("dateStart") or dates.get(g))
        for v in (L.get("variants") or []):
            t = (v.get("text") or "").strip()
            if not t: continue
            lang = LANG.get((v.get("metadataLanguage") or "").lower(), v.get("metadataLanguage") or "Latin")
            h.add(f"{g}__{v['guid']}.txt", t, language=lang, year=y, source="Die sozinianischen Briefwechsel",
                  url=f"https://sozinianer.mni.thm.de/", label=L.get("label"), text_type=v.get("metadataTextType"))
rep = h.finish(method="Public GraphQL service of the site (https://sozinianer.mni.thm.de/graphql): list of communications, then letter variants with plain text, 25 per request. The GitLab csv-data-dump repository was not used because its robots.txt disallows archive/raw/API downloads.",
  coverage="All transcribed text versions (variants) of all communications returned by the service, one record per version; dates from dateStart; out-of-window (post-1700 or pre-1450) kept with year.",
  problems=["Letters without date have year=None and dateless_in_window=False","Letters with several versions are counted once per version"])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
