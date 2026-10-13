import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
h = Harvest("zwingli-briefe")
W = "http://web.archive.org/web/2011id_/http://www.irg.uzh.ch/static/zwingli-briefe/index.php?n="
problems = ["The live site (irg.uzh.ch) answers 403 Forbidden to scripted requests although its robots.txt allows everything; the letter pages were fetched once in a browser (zwingli-briefe.download.js)."]
ov = h.get(W + "Main.Overview", "files/overview.html")
items = re.findall(r"n=Brief\.([A-Za-z0-9_.-]+)'>(.*?)</a>", ov)
seen = {}
for k, t in items: seen.setdefault(k, html.unescape(t))
DE = set("und der die das nicht ist ein eine mit von zu den dem auch wir ich dich dir mir sich für auf wie aber oder haben hat wird werden sind uns euch ewer unser dass daß ouch vnd wil mich nit".split())
LA = set("et est in non quod ad cum ut sed qui quae quam de ex esse sunt tibi te nos vel si enim autem etiam per quo".split())
def lang(t):
    ws = re.findall(r"[a-zäöüß]+", t.lower())
    d = sum(w in DE for w in ws); l = sum(w in LA for w in ws)
    return "German" if d > l else "Latin"
miss = []
cap = {}
_cdx = HARVEST_DIR + "/t6/cdx_z2.txt"  # Wayback capture list, only needed for the fallback
for l in (open(_cdx) if _os.path.exists(_cdx) else []):
    u, st, ts = l.split()
    m = re.search(r"n=Brief\.([A-Za-z0-9]+)$", u)
    if m and st == "200" and ts > cap.get(m.group(1), ("", ""))[0]: cap[m.group(1)] = (ts, u)
n_cap = len(cap); n_all = len(seen)
# The live pages (all letters), fetched once in a browser with zwingli-briefe.download.js because the server
# refuses scripted clients (robots.txt allows everything). Internet Archive copies are the fallback.
import json as _json
_manual = h.dir / "files/manual/zwingli-briefe.json"
live = _json.loads(_manual.read_text(encoding="utf-8")) if _manual.exists() else {}
LIVE = "https://www.irg.uzh.ch/static/zwingli-briefe/index.php?n=Brief."
for k, title in seen.items():
    pg = live.get(LIVE + k)
    if not pg:
        if k not in cap: miss.append(k); continue
        ts, u = cap[k]
        try:
            pg = h.get(f"http://web.archive.org/web/{ts}id_/{u}", f"files/Brief.{k}.html")
        except Exception as e:
            miss.append(k); continue
    m = re.search(r"<hr />(.*?)</div>\s*</div>", pg, re.S)
    if not m: miss.append(k); continue
    body = m.group(1)
    body = re.sub(r"<p class='vspace'\s+style='text-align: right;'>\s*--[^<]*?--\s*</p>", " ", body)
    body = re.sub(r"<br\s*/?>", "\n", body)
    body = re.sub(r"</p>", "\n", body)
    body = html.unescape(re.sub(r"<[^>]+>", "", body))
    body = re.sub(r"[ \t]+", " ", body); body = re.sub(r"\n\s*\n+", "\n", body).strip()
    dm = re.search(r"Datierung:</em>(.*?)</h4>", pg, re.S)
    ds = re.sub(r"<[^>]+>", "", dm.group(1)) if dm else title
    y = first_year(ds) or first_year(title)
    h.add(f"Brief.{k}.txt", body, language=lang(body), year=y, source="Huldrych Zwingli Briefe: Digitale Texte (Zwinglis Werke vol. 7-9)", url="https://www.irg.uzh.ch/static/zwingli-briefe/index.php?n=Brief." + k, title=title)
if miss: problems.append(f"{len(miss)} of {n_all} letter pages could not be read or parsed (not harvested)")
print(h.finish(method="Overview list from the Wayback copy; letter pages from the live site, fetched once in a browser (Wayback copies as fallback); letter text taken after the header block, page markers/markup removed, apparatus is absent on the site. Language by stopword heuristic.",
  coverage=f"{len(h.records)} of {len(seen)} letter pages (Brief.1-790 range, vols 7-9, 1510-1528).", problems=problems))
