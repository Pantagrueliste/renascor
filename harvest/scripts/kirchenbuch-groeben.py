import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
h = Harvest("kirchenbuch-groeben")
B = "http://kirchenbuch-groeben.de/"
todo = ["umschlag-seite-001"]; done = set(); problems = []
def fetch(s):
    return h.get(B + s, f"files/{slug(s)}.html", binary=True).decode("utf-8", errors="replace")
n_pages = 0
while todo:
    s = todo.pop(0).strip("/")
    if s in done: continue
    done.add(s)
    try: pg = fetch(s)
    except Exception as e:
        problems.append(f"{s}: {e}"); continue
    n_pages += 1
    t1 = re.search(r"<h1>(.*?)</h1>", pg, re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", t1.group(1))).strip() if t1 else s
    m = re.search(r'<div id="textbereich">(.*?)</div>\s*(?:<!--|<div id="(?:fuss|footer)|</div>)', pg, re.S)
    if not m: m = re.search(r'<div id="textbereich">(.*)', pg, re.S)
    body = m.group(1) if m else ""
    body = re.sub(r"<h2>.*?</h2>", "\n", body, flags=re.S)
    body = re.sub(r"<br\s*/?>", "\n", body); body = re.sub(r"</p>", "\n", body)
    body = html.unescape(re.sub(r"<[^>]+>", "", body))
    body = re.sub(r"[ \t]+", " ", body); body = re.sub(r"\n\s*\n+", "\n", body).strip()
    nx = re.findall(r'<p class="right"><a href="([^"]+)"', pg)
    if nx:
        nxt = nx[0].strip("/")
        if nxt not in done: todo.append(nxt)
    if not body: 
        problems.append(f"{s}: empty text ({title})"); continue
    y = first_year(title)
    h.add(f"{slug(s)}.txt", body, language="German", year=y, source="Das Kirchenbuch zu Gröben (1578-1769)", url=B + s, title=title)
print(h.finish(method="Followed 'Weiterblättern' links from the first page; text block (#textbereich) of each spread extracted, headings/navigation/images dropped.",
  coverage=f"{len(h.records)} spreads of {n_pages} pages fetched, whole site 1578-1769 (out-of-window years kept in staging). Year = first year in page title (e.g. 'Jahr 1599/1601'). Language labelled German (register mixes German and Latin).", problems=problems[:30]))
