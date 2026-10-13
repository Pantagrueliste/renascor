import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from bs4 import BeautifulSoup
from hlib import Harvest
B = "https://magyar-irodalom.elte.hu/gepesk/rimay/"
h = Harvest("rimay-janos-ifjukori-versgyujtemenye")
idx = h.get(B + "kr99.htm", "files/kr99.htm")
links = []
for m in re.findall(r'href="(krit/[a-z0-9]+\.htm)"', idx, re.I):
    if m not in links: links.append(m)
for lk in links:
    name = lk.split("/")[1][:-4]
    fr = h.get(B + lk, f"files/{name}.htm")
    src = re.search(r'FRAME SRC="([^"]+)" NAME="2"', fr, re.I).group(1)
    html = h.get(B + "krit/" + src, f"files/{src}")
    s = BeautifulSoup(html, "lxml")
    for t in s.find_all(["script", "style"]): t.decompose()
    for t in s.find_all("sup"): t.decompose()
    for t in s.find_all("font"):
        if re.fullmatch(r"\s*\d+\s*", t.get_text()): t.decompose()
    for t in s.find_all(["br", "p"]): t.insert_after("\n")
    txt = s.get_text().replace("\xa0", " ")
    txt = "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in txt.split("\n"))
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    print(name, len(txt.split()), txt[:50].replace("\n", " "))
    h.add(f"{name}.txt", txt, language="Hungarian", year=None, dateless_in_window=True,
          source=f"Rimay János ifjúkori versgyűjteménye, critical text {name}", url=B + "krit/" + src)
print(h.finish(method="HTML crawl of the 30 critical-text pages linked from kr99.htm (each in a nested frameset: frame 'r<N>.htm' holds the poem); removed line numbers and footnote markers; commentary frames (r<N>j.htm), source transcriptions and repertory not fetched",
  coverage="All 30 critical-text pages (poems and the title page of the cycle).",
  problems=["Undated: edition of poems composed c. 1590-1610 (catalogue notes), treated as dateless_in_window", "The page for the opening title/heading (ir0) may be a title rather than a poem", "Critical text, edited by Tóth Tünde, not a witness transcription", "Space-separated words/encoding: pages declared UTF-8 but numeric entities used; decoded via requests"]))
