import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html, time
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
h = Harvest("marinelives")
API = "https://www.marinelives.org/api.php"
def call(params, rel):
    p = h.dir / rel
    if p.exists(): return json.loads(p.read_text())
    w = h.delay - (time.time() - h._last)
    if w > 0: time.sleep(w)
    for attempt in range(4):
        try:
            r = h.s.get(API, params=params, timeout=120); h._last = time.time(); r.raise_for_status()
            d = r.json(); break
        except Exception as e:
            time.sleep(5 * (attempt + 1)); d = None
    if d is None: raise RuntimeError("api failed " + rel)
    p.write_text(json.dumps(d)); return d
pages = {}
cont = {"continue": ""}
n = 0
while True:
    params = {"action": "query", "generator": "allpages", "gapnamespace": 0, "gaplimit": 50, "prop": "revisions", "rvprop": "content", "format": "json"}
    params.update(cont)
    d = call(params, f"files/allpages_{n:05d}.json")
    for pg in (d.get("query", {}).get("pages", {}) or {}).values():
        rv = pg.get("revisions")
        if rv: pages[pg["title"]] = rv[0].get("*", "")
    n += 1
    if "continue" not in d: break
    cont = d["continue"]
print("pages", len(pages), "requests", n)
def field(txt, name):
    m = re.search(r"\|\s*" + name + r"\s*=(.*?)(?=\n\|[A-Za-z ]+=|\n\}\})", txt, re.S)
    return m.group(1).strip() if m else None
vols = {}
for t, c in pages.items():
    if "{{PageTranscription" not in c: continue
    tr = field(c.split("{{PageTranscription", 1)[1], "Transcription")
    par = field(c, "Parent volume")
    if not tr or not par: continue
    fol = field(c, "Folio") or ""
    vols.setdefault(par, []).append((t, tr))
def clean(t):
    t = html.unescape(re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), t))
    t = re.sub(r"\[[A-Z0-9 ,.:;'/()-]{3,}\]", " ", t)       # editorial notes in capitals
    t = re.sub(r"\{\{.*?\}\}", " ", t, flags=re.S)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"</?[a-zA-Z][^>]*>", " ", t)
    t = re.sub(r"^\s*\*+\s*$", "", t, flags=re.M)
    return re.sub(r"[ \t]+", " ", t).strip()
def sortkey(x):
    m = re.search(r"f\.(\d+)([rv]?)", x[0]); 
    return (int(m.group(1)) if m else 10**6, m.group(2) if m else "", x[0])
nov = []
for par, items in sorted(vols.items()):
    items.sort(key=sortkey)
    txt = "\n\n".join(clean(tr) for _, tr in items)
    vp = pages.get(par, "")
    sd = field(vp, "Start date") if vp else None
    y = first_year(sd) or first_year(field(vp, "End date") if vp else None)
    if y is None: nov.append(par)
    h.add(slug(par) + ".txt", txt, language="English", year=y, source="MarineLives: " + par, url="https://www.marinelives.org/wiki/" + par.replace(" ", "_"), folios=len(items))
rep = h.finish(method="MediaWiki api.php (allowed by robots.txt): bulk generator=allpages with prop=revisions content, 50 pages per request, namespace 0. For each page with a PageTranscription template the Transcription field was taken, grouped by Parent volume (one record per volume, folios in order). Wiki markup, editorial capitalised notes, templates stripped. Year = volume page 'Start date'.",
  coverage=f"All {len(pages)} main-namespace pages fetched; {sum(len(v) for v in vols.values())} transcribed folio pages in {len(vols)} volumes/records.",
  problems=["Language set to English; some depositions are partly Latin, Spanish, Dutch or French","Volumes whose page lacks Start/End date get year=None, dateless_in_window=False: " + str(nov[:50]),"Texts are transcriptions of manuscripts with the transcribers' editorial conventions; includes some non-deposition series (E 190, C 5 etc.)"])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], len(nov))
