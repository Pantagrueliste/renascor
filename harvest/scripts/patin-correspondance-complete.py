import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
B = "https://numerabilis.u-paris.fr/editions-critiques/patin/"
h = Harvest("patin-correspondance-complete", delay=0.7)
FR = set("le la les de des du un une que qui est pour dans ce il je vous nous en au sur pas se avec mais ne son sa ses et à".split())
LA = set("et in est non ad cum quae quod ut sed qui si nec ab ex vel quam enim etiam sunt esse atque aut autem ergo quia".split())
import time
def get(url, rel):
    for attempt in range(4):
        try:
            return h.get(url, rel)
        except Exception as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 403) or attempt == 3: raise
            time.sleep(10 * (attempt + 1))
ids, fails = [], []
for y in range(1630, 1674):
    ls = get(f"{B}?annee={y}", f"files/annee/{y}.html")
    for m in re.findall(r'href="\?let=\s*([0-9A-Za-z]+)\s*"', ls):
        if m not in ids: ids.append(m)
print(len(ids), "letters in the year lists")
for cur in ids:
    try:
        s = get(f"{B}index.las?let={cur}", f"files/letters/{cur}.html")
    except Exception as e:
        fails.append((cur, str(e))); continue
    soup = BeautifulSoup(s, "lxml")
    tit = soup.find("td", class_="lettit")
    head = re.sub(r"\s+", " ", tit.get_text(" ", strip=True)) if tit else ""
    l = soup.find("td", class_="let")
    if l is None:
        fails.append((cur, "no text")); continue
    for t in l.select("span.npg, span.ind, span.nfn, a[href*='tnote'], a[href*='do=ind']"): t.decompose()
    for br in l.find_all("br"): br.replace_with("\n")
    for p in l.find_all("p"): p.append("\n")
    txt = l.get_text("").replace("\xa0", " ")
    txt = re.sub(r"[ \t]+", " ", txt); txt = re.sub(r" ?\n ?", "\n", txt); txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    ws = re.findall(r"[a-zàâçéèêëîïôûùü]+", txt.lower())
    lang = "Latin" if sum(w in LA for w in ws) > sum(w in FR for w in ws) else "French"
    h.add(f"{cur}.txt", txt, language=lang, year=first_year(head), source=f"Patin, {head[:150]}", url=f"{B}?do=pg&let={cur}", dateless_in_window=True)
rep = h.finish(method="No bulk export (no sitemap, no download). Read the 44 per-year lists (?annee=YYYY) for the letter ids, then fetched each letter's text frame (index.las?let=NNNN) and kept only the letter body (td.let) without note, index and source-note markers; heading kept out of the text, used for the date.",
  coverage="All %d letters listed in the year indexes (catalogue count: 1,079; the year indexes list 1,611 ids for 1630-1673)." % len(h.records) + (f" Stopped/failed: {fails}" if fails else ""),
  problems=["Language assigned by French/Latin stopword heuristic (letters are in French with Latin passages; a few letters are entirely Latin).",
            "Year = first year in the heading date (letters sent between 1630 and 1673).",
            "The year indexes list more letters than the catalogue count (1,079): they include Latin letters and letters received by Patin; all listed ids were harvested. Writings outside the year indexes, if any, were not harvested."] + [f"fail {a}: {b}" for a, b in fails[:20]])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
