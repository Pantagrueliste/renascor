import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
B = "https://www.livesandletters.ac.uk/herle/"
h = Harvest("letters-of-william-herle", delay=10.0)  # robots.txt Crawl-delay: 10
idx = h.get(B + "date.html", "files/date.html")
soup = BeautifulSoup(idx, "html.parser")
items = []
for li in soup.select("li.item"):
    a = li.find("a", href=re.compile(r"^letters/\d+\.html"))
    if not a: continue
    d = li.find("strong").get_text(" ", strip=True)
    items.append((a["href"], d))
probs = []
for href, d in items:
    num = re.search(r"(\d+)", href).group(1)
    try:
        s = h.get(B + href, f"files/letters_{num}.html")
    except Exception as e:
        probs.append(f"fetch failed {href}: {e}"); continue
    sp = BeautifulSoup(s, "html.parser")
    parts = []
    for div in sp.select("div.endorse, div.letter"):
        for sup in div.find_all("strong"):
            pass
        parts.append(div.get_text(" ", strip=True))
    txt = "\n".join(parts)
    if not txt.strip():
        probs.append(f"empty transcript {href}"); continue
    y = first_year(d)
    h.add(f"herle-{num}.txt", txt, language="English", year=y, source="Letters of William Herle", url=B + href,
          dateless_in_window=True)
    if y is None: probs.append(f"no year for {href} ({d}); dateless_in_window=True because edition covers 1559-1588 only")
probs.append(f"{len(items)} transcripts listed in date index; endorsements/address leaf included, editorial comments excluded; year = first year in index date (some marked uncertain)")
rep = h.finish(method="date.html index lists all transcripts; fetched letters/NNN.html (crawl-delay 10 s per robots.txt); kept div.letter + div.endorse",
               coverage=f"{len(h.records)} of {len(items)} listed transcripts", problems=probs)
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")})
