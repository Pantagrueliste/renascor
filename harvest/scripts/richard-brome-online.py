import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from bs4 import BeautifulSoup
from hlib import Harvest
B = "https://www.dhi.ac.uk/brome/"
h = Harvest("richard-brome-online", delay=2.0)  # robots.txt Crawl-delay: 2
home = h.get(B + "home.jsp", "files/home.html")
plays = re.findall(r"viewTranscripts\.jsp\?play=(\w+)&act=1&type=BOTH", home)
names = dict(re.findall(r'<option\s+value="(\w\w)">([^<]+)</option>', h.get(B + "viewTranscripts.jsp?play=AN&act=1&type=BOTH", "files/AN_wrap.html")))
for p in plays:
    wrap = h.get(B + f"viewTranscripts.jsp?play={p}&act=1&type=BOTH", f"files/{p}_wrap.html")
    acts = sorted({int(a) for a in re.findall(r"act=(\d+)", wrap)})
    bodies = []
    for a in acts:
        html = h.get(B + f"viewInFrame.jsp?view=dual&play={p}&act={a}&type=ORIG", f"files/{p}_act{a}.html")
        s = BeautifulSoup(html, "lxml")
        bodies.append(s.find("div", class_="pagewidth") or s.body)
    body = bodies[0]
    for b in bodies[1:]:
        body.append(b)
    front = " ".join(d.get_text(" ") for d in bodies[0].find_all("div", class_="frontispiece"))
    yrs = [int(y) for y in re.findall(r"(?<!\d)(1[5-6]\d\d)(?!\d)", front)]
    for t in body.find_all(["script", "style"]): t.decompose()
    for t in body.find_all(class_=["linenumber", "whitelinenumber", "vlink", "fw", "fwsig_cent"]): t.decompose()
    for t in body.find_all("br"): t.replace_with("\n")
    txt = body.get_text()
    txt = re.sub(r"[ \t\xa0]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt).strip()
    y = yrs[-1] if yrs else {"MC": 1653}.get(p)  # MC: no title page transcribed; printed in Five New Playes, 1653
    print(p, names.get(p), yrs, len(txt.split()))
    h.add(f"{p}.txt", txt, language="English", year=y, source=f"Richard Brome Online: {names.get(p, p)} (original quarto/octavo text)", url=B + f"viewTranscripts.jsp?play={p}&act=1&type=BOTH")
print(h.finish(method="HTML crawl of viewInFrame.jsp (original-spelling frame, one request per act; modern-spelling frame, notes, essays, glossary not fetched); removed line numbers, signatures and catchwords, '[Link]' markers; robots.txt Crawl-delay 2 respected; year = last year in the imprint on the title page",
  coverage="All 16 plays, all acts, original quarto/octavo text including title page, dedications, prologues/epilogues and dramatis personae.",
  problems=["A Mad Couple Well Matched has no transcribed imprint: year 1653 (Five New Playes) set by hand", "Original long-s kept as in source", "Year is the printing date from the transcribed imprint (plays composed earlier)"]))
