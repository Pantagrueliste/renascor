import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import re, html
from bs4 import BeautifulSoup

h = Harvest("representative-poetry-online", delay=1.0)
problems = []
BASE = "https://rpo.library.utoronto.ca"

# 1. poet index (all pages)
poets = []
for pg in range(0, 40):
    s = h.get(f"{BASE}/poets?page={pg}", f"files/poets_page_{pg}.html")
    l = re.findall(r'<h2 class="field-content"><a href="(/poets/[^"]+)"[^>]*>([^<]*)</a>\s*<small>([^<]*)</small>', s)
    if not l:
        break
    poets += l

# 2. select poets whose texts date from 1450-1700 (author dates on the site)
# Poets without usable dates on the site (0 - 0 / blank) are included only if I could date them from the poet page
# or sources (DATELESS below). Anonymous is excluded: the site gives no date for individual poems.
DATELESS = {  # path: (floruit year used, note)
    "/poets/whitney-isabella": 1570,   # fl. 1567-1573
    "/poets/wever-r": 1550,            # Lusty Juventus, c. 1550
    "/poets/gifford-humphrey": 1580,   # A Posie of Gilloflowers 1580, d. 1589
    "/poets/gray-reading-william": 1545,  # d. 1557, floruit about the 1540s
}
FRENCH = {"/poets/de-ronsard-pierre", "/poets/du-bellay-joachim", "/poets/belleau-r%C3%A9my", "/poets/villon-fran%C3%A7ois",
          "/poets/de-la-fontaine-jean", "/poets/girard-sieur-de-saint-amant-saint-amant", "/poets/lhermite-fran%C3%A7ois-tristan"}
SCOTS = {"/poets/dunbar-william", "/poets/henryson-robert", "/poets/douglas-gavin"}
sel, excluded_late = [], []
for path, name, d in poets:
    nums = [int(x) for x in re.findall(r"\d+", d)]
    name = html.unescape(name).strip()
    if path in DATELESS:
        sel.append((path, name, DATELESS[path], "dateless")); continue
    if len(nums) < 2 or nums[0] == 0:
        continue
    b, dth = nums[0], nums[1]
    if dth == 0 or b < 1420 or dth < 1460:
        continue
    if b > 1680:
        continue
    if dth > 1701:
        if b <= 1665:
            excluded_late.append(f"{name} ({b}-{dth})")
        continue
    flo = round(((b + 25) + min(dth, 1700)) / 2)
    sel.append((path, name, flo, "floruit"))
problems.append("Poets selected by author dates shown on the site: born 1420-1680 and died 1460-1701 (poets dying after 1701 are excluded because their poems cannot be dated by the site; borderline ones left out: " + "; ".join(excluded_late) + "). Anonymous (1100-2010), Mother Goose and poets with blank or 0-0 dates are excluded, except four 16th-century poets dated by hand (Isabella Whitney 1570, R. Wever 1550, Humphrey Gifford 1580, William Gray of Reading 1545).")

# 3. poems of each selected poet
nrec = 0
seen_slugs = set()
for path, name, flo, how in sel:
    try:
        s = h.get(BASE + path, "files/poet_" + slug(path) + ".html")
    except Exception as e:
        problems.append(f"{path}: {e}"); continue
    i = s.find("Index to poems")
    poems = re.findall(r'<a href="(/content/[^"]+)"[^>]*>([^<]*)</a>', s[i:]) if i >= 0 else []
    for ppath, title in poems:
        sl = slug(ppath.split("/content/")[1])
        fn = f"{slug(path.split('/poets/')[1])}__{sl}.txt"
        if fn in seen_slugs:
            continue
        try:
            ps = h.get(BASE + ppath, f"files/poem_{sl}.html")
        except Exception as e:
            problems.append(f"{ppath}: {e}"); continue
        soup = BeautifulSoup(ps, "lxml")
        body = soup.select_one("div.field--name-field-poem-body")
        if not body:
            problems.append(f"{ppath}: no poem body"); continue
        lines = []
        for d in body.select("div.poemline"):
            t = d.select_one("span.line-text")
            lines.append(re.sub(r"\s+", " ", (t.get_text() if t else "").replace("\xa0", " ")).strip())
        raw = "\n".join(lines).strip()
        if not raw:
            body_txt = body.get_text("\n").replace("Toggle Line Numbers", "")
            raw = "\n".join(l.strip() for l in body_txt.splitlines() if l.strip())
        if not raw:
            problems.append(f"{ppath}: empty poem"); continue
        seen_slugs.add(fn)
        lang = "French" if path in FRENCH else ("Scots" if path in SCOTS else "English")
        h.add(fn, raw, language=lang, year=flo, source=f"{name}, {html.unescape(title)} (RPO)", url=BASE + ppath)
        nrec += 1
problems.append("The site gives no date for individual poems (only the poet's birth and death years), so year = floruit midpoint: (birth + 25 + min(death, 1700)) / 2 for dated poets; fixed hand-set values for the four dateless 16th-century poets. Not first publication dates.")
problems.append("Spelling is mixed on the site (normalised in most printed-edition texts, original spelling for some web-only texts); not distinguishable per poem, all kept. Line-number toggles, 'Original Text' citations, editor credits and rhyme/form metadata dropped. French poems (Ronsard, Du Bellay, Belleau, Villon, La Fontaine, Saint-Amant, L'Hermite) are in French.")
rep = h.finish(method="Listed the 749 poets from /poets?page=N (50 per page), selected those with author dates in 1450-1700 (see problems), fetched each poet's poem index and every poem page at 1 s intervals (robots.txt blocks only admin/search paths), extracted the poem lines with BeautifulSoup. One record per poem.",
    coverage="All poems of the selected poets listed on RPO; Anonymous and poets dying after 1701 not harvested; poets with no usable dates not harvested.",
    problems=problems)
print(rep)
