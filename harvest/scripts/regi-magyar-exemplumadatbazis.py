import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import re, time, html
from bs4 import BeautifulSoup

h = Harvest("regi-magyar-exemplumadatbazis", delay=1.0)
problems = []
BASE = "https://sermones.elte.hu/exemplumadatbazis/"

def post(rel, data):
    p = h.dir / rel
    if p.exists():
        return p.read_text(encoding="utf-8")
    wait = h.delay - (time.time() - h._last)
    if wait > 0:
        time.sleep(wait)
    r = h.s.post(BASE + "kereso.php", data=data, timeout=120)
    h._last = time.time()
    r.raise_for_status()
    r.encoding = "utf-8"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(r.text, encoding="utf-8")
    return r.text

def ids_of(page):
    page = page[page.find("<div id='talalatok'>"):] if "<div id='talalatok'>" in page else ""
    return re.findall(r"id='(\d{4}[a-z]?)'href", page)

# 1. list all record ids: one broad search (word 'és'), cross-checked by one search per source codex
ids = {}
page = post("files/search_es.html", {"exempl_szovege": "és", "submit": "Keresés"})
for i in ids_of(page):
    ids[i] = True
n_es = len(ids)
form = h.get(BASE + "kereso.php", "files/kereso.html")
codices = re.findall(r'<option value="([^"]+)">', form)
codices = codices[:codices.index("prédikáció")]
extra = 0
for c in codices:
    pg = post(f"files/search_codex_{slug(c)}.html", {"forraskodex[]": c, "submit": "Keresés"})
    for i in ids_of(pg):
        if i not in ids:
            ids[i] = True
            extra += 1
if extra:
    problems.append(f"{extra} record ids found only through the per-codex searches (not by word search 'és').")

# approximate date of each source codex (copy), from standard dating of the Old Hungarian codices; the site gives none
YEAR = {"Bod-kódex": 1525, "Cornides-kódex": 1517, "Debreceni kódex": 1519, "Domonkos-kódex": 1524, "Érdy-kódex": 1526,
        "Érsekújvári kódex": 1530, "Gömöry-kódex": 1516, "Guary-kódex": 1495, "Horvát-kódex": 1522, "Kazinczy-kódex": 1534,
        "Könyvecse az szent apostoloknak méltóságokról": 1525, "Lázár Zelma-kódex": 1510, "Lobkowitz-kódex": 1514,
        "Margit-legenda": 1510, "Nádor-kódex": 1508, "Nagyszombati kódex": 1512, "Példák könyve": 1510, "Sándor-kódex": 1512,
        "Simor-kódex": 1519, "Székelyudvarhelyi kódex": 1527, "Teleki-kódex": 1528, "Tihanyi kódex": 1530,
        "Virginia-kódex": 1514, "Winkler-kódex": 1506}

nodate = 0
for rid in sorted(ids):
    try:
        pg = h.get(f"{BASE}display.php/{rid}", f"files/display_{rid}.html")
    except Exception as e:
        problems.append(f"{rid}: {e}")
        continue
    soup = BeautifulSoup(pg, "lxml")
    p = soup.find("p", id="exempl_szovege")
    txt = p.get_text("\n").strip() if p else ""
    if not txt:
        problems.append(f"{rid}: empty exemplum text")
        continue
    codex = ""
    for d in soup.select("div.block_a"):
        sp = d.find("span", class_="res_cat")
        if sp and sp.get_text(strip=True).startswith("Forráskódex"):
            codex = re.sub(r"\s+", " ", d.get_text(" ").replace(sp.get_text(), "")).strip()
            break
    year = next((y for k, y in YEAR.items() if codex.startswith(k)), None)
    if year is None:
        nodate += 1
    h.add(f"RMEx_{rid}.txt", txt, language="Hungarian", year=year, source=f"RMEx {rid}: {codex}",
          url=f"{BASE}display.php/{rid}")
if nodate:
    problems.append(f"{nodate} records without a codex date mapping (year=None, counted out).")
problems.append("The site gives no codex dates; year = approximate date of the codex copy (midpoint where a range) from standard dating of the Old Hungarian codices, set per codex by me; all 16th century (Guary-kódex 1495). Kazinczy-kódex set to 1534 (parts finished 1526, 1527, 1541); Bod-kódex, Könyvecse az szent apostoloknak méltóságokról and Lázár Zelma-kódex dates are least certain.")
problems.append("Text field 'Exemplum szövege' only (modernised reading from the Nyelvemléktár editions, accepted); summaries, keywords, Latin sources and parallels excluded. The search list has 475 hits for 462 distinct ids (4 found only via codex searches), matching the 462 records and about 130,000 words in the catalogue notes.")
rep = h.finish(method="One POST search on the site's search form (word 'és') plus one search per source codex listed in the form to list record ids, then one GET of each record page display.php/<id> at 1 s intervals (no robots.txt exists, only a redirect to an error page); extracted the exemplum text field.",
    coverage="All records returned by the search interface (ids 0001-0386 and lettered variants); records without text excluded.",
    problems=problems)
print(rep)
