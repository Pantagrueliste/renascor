import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
h = Harvest("boyle-workdiaries", delay=10)  # robots.txt Crawl-delay: 10
base = "https://www.livesandletters.ac.uk/wd/view/"
idx = h.get(base + "view.html", "files/view.html")
soup = BeautifulSoup(idx, "html.parser")
titles = {}
for dt in soup.find_all("dt"):
    dd = dt.find_next_sibling("dd")
    m = re.search(r"Workdiary (\d+)", dt.get_text())
    if m and dd:
        titles[int(m.group(1))] = dd.get_text(" ", strip=True).split("Text &")[0].split("Text & Image")[0]
nums = sorted(set(int(n) for n in re.findall(r"text_dip/WD(\d+)_dip\.html", idx)))
for n in nums:
    u = f"{base}text_dip/WD{n}_dip.html"
    page = h.get(u, f"files/WD{n}_dip.html")
    s = BeautifulSoup(page, "html.parser")
    paras = []
    for e in s.select("div.entry"):
        paras.append(e.get_text(" ", strip=True))
    txt = "\n".join(paras)
    t = titles.get(n, "")
    y = first_year(t)
    # fallback: first year of entry text in 1600s
    if not y:
        m = re.search(r"\b(16[4-9]\d)\b", txt)
        y = int(m.group(1)) if m else None
    h.add(f"WD{n}_dip.txt", txt, language="English", year=y, source="The Workdiaries of Robert Boyle", url=u,
          dateless_in_window=True, title=t)
rep = h.finish(method="Crawled the 'text-only diplomatic transcript' page of each workdiary linked from /wd/view/view.html (robots.txt allows /wd/, Crawl-delay 10 respected). Only div.entry text kept; headnotes, folio markers, buttons stripped. Diplomatic version kept, editorial version skipped.",
  coverage="All workdiaries listed on the view page (diplomatic text-only pages).",
  problems=["Mixed English/French/Latin: language set to English (main language)","year taken from the workdiary title or first 164x-169x year in text; if none, year=None and dateless_in_window=True because the whole resource spans 1647-1691","Diplomatic transcript includes editorial brackets such as [unclear]"])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
