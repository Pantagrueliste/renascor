import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest, first_year
h = Harvest("hooke-folio-online", delay=10.5)   # robots.txt Crawl-delay: 10
B = "https://www.livesandletters.ac.uk/cell/Hooke/"
problems = []
YR = re.compile(r"(?<!\d)(16[5-9]\d)(?!\d)")
last_year = 1661
n_empty = 0
first = h.get(B + "hooke_folio.php?id=1&option=transcript", "files/f1.html")
m = re.search(r'hooke_folio\.php\?id=(\d+)&option=transcript"><img src="\./icons/last', first)
LAST = int(m.group(1)) if m else 679
for i in range(1, LAST + 1):
    try:
        s = h.get(B + f"hooke_folio.php?id={i}&option=transcript", f"files/f{i}.html")
    except Exception as e:
        problems.append(f"id {i}: {e}"); continue
    m = re.search(r'<div id="transcript">(.*?)</div></body>', s, re.S)
    if not m:
        problems.append(f"id {i}: no transcript div"); continue
    t = m.group(1)
    ref = re.search(r"Ref: ([A-Z/_0-9]+)", t)
    t = re.sub(r'<p class="copyright">.*', "", t, flags=re.S)
    t = re.sub(r"<p>\s*\d+\s*</p>", "", t, count=1)   # folio number
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"<img[^>]*>", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    if len(t.split()) < 3:
        n_empty += 1; continue
    ys = YR.findall(t)
    if ys: last_year = int(ys[0])
    raw = "<TEI><text><body><p>" + html.escape(t, quote=False) + "</p></body></text></TEI>"
    h.add(f"id{i:04d}_{re.sub(r'[^A-Za-z0-9_]+','_',ref.group(1)) if ref else 'noref'}.xml", raw, language="English", year=last_year, source=f"Hooke Folio, page id {i}", url=B + f"hooke_folio.php?id={i}&option=transcript")
rep = h.finish(method=f"Crawled hooke_folio.php?id=1..{LAST}&option=transcript (one transcribed page per record), honouring robots.txt Crawl-delay 10; stripped markup, folio number, copyright line, images",
  coverage=f"All {LAST} page ids requested; {n_empty} had no text. One record per transcribed page (folio side).",
  problems=problems + ["Year = first year (165x-169x) mentioned on the page, carried forward from the previous page when absent (the volume covers only 1661-1691); approximate. Deleted passages in the manuscript are kept in the text."])
print(json.dumps({k: rep[k] for k in ("texts_total","words_total","texts_in_window")}))
