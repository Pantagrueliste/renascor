import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
B = "https://grotius.huygens.knaw.nl"
h = Harvest("grotius-correspondence-huygens", delay=0.6)
ys = [str(y) for y in range(1597, 1646)]
# year lists (also an unnumbered '?' list)
ids = []
for y in ys + ["%3F"]:
    try:
        s = h.get(f"{B}/years/{y}/", f"files/years/{y}.html")
    except Exception as e:
        print("year fail", y, e); continue
    for m in re.findall(r'href="/letters/([^"/]+)/?"', s):
        if m not in ids: ids.append(m)
print(len(ids), "letters listed")
SW = {
 "Latin": set("et in est non ad cum quae quod ut sed qui si nec ab ex vel quam enim etiam tibi mihi te me sunt esse atque neque aut".split()),
 "French": set("et le la les de des du un une que qui est pour dans ce il je vous nous en au sur pas se avec mais ne son sa ses".split()),
 "Dutch": set("de het een van en in dat is niet te ik u wij met op voor aan zijn maar ook als dan door bij hebben heeft".split()),
 "German": set("und der die das ist nicht ich zu den mit von ein eine auf für sich dem auch als wie".split()),
 "Italian": set("e il la di che un una per non con sono del della le lo gli ma si come".split()),
 "Greek": set(),
}
def lang(t):
    ws = re.findall(r"[a-zà-ÿ]+", t.lower())
    sc = {k: sum(w in v for w in ws) for k, v in SW.items() if v}
    k = max(sc, key=sc.get)
    return k if sc[k] else "Latin"
fails = []
for lid in ids:
    try:
        s = h.get(f"{B}/letters/{lid}/", f"files/letters/{lid}.html")
    except Exception as e:
        fails.append((lid, str(e))); continue
    soup = BeautifulSoup(s, "lxml")
    lp = soup.find(id="letter_panel")
    if not lp: fails.append((lid, "no panel")); continue
    h1 = lp.find("h1")
    head = h1.get_text(" ", strip=True) if h1 else ""
    for t in lp.select("h1, .annotation_refer_tr, .page_nr, .panelHeadLeft"): t.decompose()
    par = lp.find("span", class_="par") or lp
    txt = re.sub(r"[ \t]+", " ", par.get_text("\n")).strip()
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    mm = re.search(r'\[\s*(1[5-6]\d\d)', head)
    y = int(mm.group(1)) if mm else None
    if y is None and re.match(r'\s*Bijlage', head):
        # appendix to letter N ("Bij no. N"): take the year of letter N
        pm = re.search(r'Bij no\.?\s*(\d+)', head)
        if pm:
            try:
                ps = BeautifulSoup(h.get(f"{B}/letters/{int(pm.group(1)):04d}/", f"files/letters/{int(pm.group(1)):04d}.html"), "lxml")
                ph = ps.find(id="letter_panel").find("h1").get_text(" ", strip=True)
                pm2 = re.search(r'\[\s*(1[5-6]\d\d)', ph); y = int(pm2.group(1)) if pm2 else None
            except Exception: y = None
    elif y is None:
        y = first_year(re.sub(r'^\s*\S+\.\s*', '', head))
    h.add(f"{lid}.txt", txt, language=lang(txt), year=y, source=f"Briefwisseling van Hugo de Groot, letter {lid}",
          url=f"{B}/letters/{lid}/", dateless_in_window=True)
rep = h.finish(method="No bulk export or API (site has no sitemap/robots); read the 49 year lists plus the undated list, then fetched each letter page (/letters/<n>/) and kept only the letter_panel text (Notes panel, editor's heading and page markers removed).",
  coverage="All letters listed on the year lists" + (f"; {len(fails)} failed" if fails else "") + ". Letter text only; Dutch editorial notes, introductions and indices excluded.",
  problems=["Language assigned by stopword heuristic (Latin/French/Dutch/German/Italian); mixed letters get their dominant language.",
            "Year taken from the editor's bracketed year in the letter heading ([1597]); appendices ('Bijlage ... Bij no. N') take the year of letter N; undated letters get year=None with dateless_in_window=True (the edition covers only 1597-1645)."] + [f"fail {a}: {b}" for a, b in fails[:20]])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
