import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
from bs4 import BeautifulSoup

h = Harvest("poly-olbion-project")
problems = []
for n in range(1, 31):
    url = f"https://poly-olbion.exeter.ac.uk/the-text/full-text/song-{n}/"
    try:
        html = h.get(url, f"files/song-{n}.html")
    except Exception as e:
        problems.append(f"song {n}: {e}")
        continue
    soup = BeautifulSoup(html, "lxml")
    ec = soup.select_one("div.entry-content")
    if not ec:
        problems.append(f"song {n}: no entry-content")
        continue
    for t in ec.select("td.header, td.page_number, .hi-note, input, script"):
        t.decompose()
    for br in ec.find_all("br"):
        br.replace_with("\n")
    lines = []
    for tr in ec.select("#pages table tr"):
        for td in tr.find_all("td", recursive=False):
            txt = td.get_text()
            txt = "\n".join(l.strip() for l in txt.splitlines() if l.strip())
            if txt:
                lines.append(txt)
    raw = "\n".join(lines)
    year = 1612 if n <= 18 else 1622
    h.add(f"song-{n}.txt", raw, language="English", year=year,
          source=f"Drayton, Poly-Olbion, Song {n}", url=url)
rep = h.finish(
    method="Fetched the 30 full-text song pages (WordPress HTML, original spelling) at 1 s intervals; extracted verse, argument, headings and printed marginal notes with BeautifulSoup; dropped page numbers, running headers, note-reference letters and navigation. One record per song; songs 1-18 dated 1612, 19-30 dated 1622.",
    coverage="All 30 songs of Poly-Olbion (both parts, 1612 and 1622). Selden's Illustrations, the modernised extracts and the word list are not on the full-text pages and were not harvested." if not problems else "Partial; see problems.",
    problems=problems + ["Marginal notes (printed glosses by Drayton) are kept inline after the verse of their row; some editorial marginal marks may remain."])
print(rep)
