import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from bs4 import BeautifulSoup
from hlib import Harvest
B = "https://www.mpiwg-berlin.mpg.de/Galileo_Prototype/"
h = Harvest("galileo-ms-gal-72")
lst = h.get(B + "MAIN/LIST.HTM", "files/LIST.HTM")
folios = []
for m in re.finditer(r'HREF="\.\./HTML/(F[0-9A-Z_]+)/\1\.HTM"', lst, re.I):
    if m.group(1) not in folios: folios.append(m.group(1))
IT = set("il di che è e della dello delle del con dal nel per se si non come sono più ma alla al lo la le gli un una da in a sia tanto quanto tempo moto dunque adunque perché".split())
def lang(t):
    w = re.findall(r"[a-zàèéìòù]+", t.lower())
    it = sum(x in {"il","della","dello","delle","che","è","con","dal","nel","come","sono","più","alla","lo","gli","dunque","adunque","perché","moto","tempo","spazio","se","quanto","tanto"} for x in w)
    la = sum(x in {"est","ad","ab","et","quod","quae","cum","sunt","ex","in","ut","quam","aut","vel","enim","autem","ergo","erit","erunt","igitur","sed","proportio","ratio","ac","atque","quia","itaque"} for x in w)
    return "Italian" if it > la else "Latin"
missing = 0
for f in folios:
    html = h.get(B + f"HTML/{f}/{f}.HTM", f"files/{f}.HTM")
    s = BeautifulSoup(html, "lxml")
    rows = []
    for b in s.find_all("b"):
        if "(final text)" in b.get_text():
            tbl = b.find_parent("table")
            for tr in tbl.find_all("tr", recursive=False) or tbl.find_all("tr"):
                tds = tr.find_all("td", recursive=False)
                if len(tds) >= 2:
                    rows.append(re.sub(r"\s+", " ", tds[1].get_text(" ")).strip())
            break
    raw = "\n".join(r for r in rows if r and r != "In preparation")
    if not raw.strip():
        missing += 1
        continue
    h.add(f"{f}.txt", raw, language=lang(raw), year=None, dateless_in_window=True,
          source=f"Galileo, Ms. Gal. 72, folio {f[1:]} (final text)", url=B + f"HTML/{f}/{f}.HTM")
print(len(folios), "folio pages;", missing, "without transcription")
print(h.finish(method="HTML crawl of each folio overview page listed in MAIN/LIST.HTM (folios 33-196); took only the 'final text' transcription table; text-block detail pages, indices, apparatus and images not fetched",
  coverage="All folio sides with a final-text transcription; empty pages skipped.",
  problems=["Texts are undated: Ms. Gal. 72 documents work c. 1590-1637, treated as dateless_in_window", "Language assigned per folio side by a word-list heuristic (Latin/Italian mixed within pages)", "Entry page requires clicking an 'I accept' notice (copyright notice on images/publication); no login, no bot challenge; pages are plain static HTML", "Licence note: no use for publication or commercial purposes without BNCF permission; staging for counting only", "Includes numbers, formulae and tables as transcribed"]))
