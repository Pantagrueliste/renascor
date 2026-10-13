import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html, json
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
from bs4 import BeautifulSoup
import urllib.parse
h = Harvest("digital-renaissance-editions")
U = "https://digitalrenaissance.uvic.ca/"
plays = h.get(U + "Foyer/plays/index.html", "files/plays.html")
works = sorted(set(re.findall(r'\.\./\.\./((?:Annex|Library)/Texts/[^/]+)/index\.html', plays)))
docs = {}   # id -> (label, workpage)
for w in works:
    p = h.get(U + w + "/index.html", "files/" + slug(w) + ".html")
    s = BeautifulSoup(p, "html.parser")
    for a in s.find_all("a", href=re.compile(r"/m/doc/[^/]+/")):
        m = re.search(r"/m/doc/([^/]+)/", a["href"])
        lab = a.get_text(" ", strip=True)
        if re.search(r"old-spelling|diplomatic|transcription|facsimile", lab, re.I) and not re.search(r"modern", lab, re.I):
            docs[m.group(1)] = (lab, w)
def line_text(div):
    for a in div.select("a.milestone"): a.decompose()
    for e in div.select(".note, .annotation, .gloss"): e.decompose()
    return re.sub(r"\s+", " ", div.get_text("")).strip()
def page_lines(p):
    s = BeautifulSoup(p, "html.parser")
    body = s.find(id="text-body")
    if not body: return None
    return [t for t in (line_text(d) for d in body.select("div.line")) if t]
miss = []
for did, (lab, w) in docs.items():
    base = f"{U}m/doc/{did}/"
    try: root = h.get(base + "index.html", f"files/{did}/index.html")
    except Exception: miss.append((did, "404")); continue
    s = BeautifulSoup(root, "html.parser")
    urls = {base + "index.html"}
    for a in s.find_all("a", href=True):
        m = re.match(r"(?:\.\./)?scene/([^/]+)/index\.html", a["href"])
        if m: urls.add(f"{base}scene/{m.group(1)}/index.html")
    for o in s.find_all("option"):
        m = re.search(r"/m/doc/[^/]+/(?:scene|act|page|part)/([^/]+)/", o.get("value", ""))
        if m: urls.add(f"{base}{o['value'].split('/m/doc/'+did+'/')[1]}index.html")
    lines = []
    for u in sorted(urls, key=lambda x: (x != base + "index.html", x)):
        rel = "files/" + did + "/" + slug(u.replace(base, "")) 
        try: p = h.get(u, rel)
        except Exception: continue
        pl = page_lines(p)
        if pl and not any("forthcoming" in x for x in pl[:3]): lines += pl
    txt = "\n".join(lines)
    if len(txt.split()) < 50: miss.append((did, len(txt.split()))); continue
    y = first_year(lab)
    h.add(f"{did}.txt", txt, language="English", year=y, source="Digital Renaissance Editions: " + lab, url=base, work=w)
rep = h.finish(method="Foyer/plays page -> each work page (Library/Annex) -> old-spelling/diplomatic document ids (/m/doc/<id>/) -> each scene page; kept only div.line text of #text-body (line-number milestones removed). Modern-spelling editions, introductions, notes skipped. robots.txt disallows /exist/ only (not used).",
  coverage=f"{len(works)} work pages, {len(docs)} old-spelling documents found; {len(h.records)} harvested with text; the rest show 'Text forthcoming' (text database no longer served): {miss}",
  problems=["Many Annex documents have no text served on the live site (Text forthcoming)", "Documents whose title has no year get year=None and dateless_in_window=False","Documents may include stage directions and speaker prefixes"])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], len(docs), miss)
