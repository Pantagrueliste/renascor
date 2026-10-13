import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, subprocess
sys.path.insert(0, HARVEST_DIR + "")
from bs4 import BeautifulSoup
from hlib import Harvest
B = "https://www.ehu.eus/monumenta/lazarraga/"
h = Harvest("lazarraga-manuscript")
toc = h.get(B + "testua.html", "files/testua.html")
LANG = "Basque"
def html_text(html):
    s = BeautifulSoup(html, "lxml")
    cell = s.find("div", class_="capaPoema")
    if cell is None: return ""
    for t in cell.find_all(["script", "style"]): t.decompose()
    for t in cell.find_all("h3"): t.decompose()                       # folio markers
    for t in cell.find_all(class_=["numbertso", "numnotalpie", "notalpie", "tablanotas"]): t.decompose()
    for t in cell.find_all("table", class_="tablanotas"): t.decompose()
    for t in cell.find_all("br"): t.replace_with("\n")
    txt = cell.get_text().replace("\xa0", " ")
    txt = re.sub(r"\[\.\.\.\]", " ", txt)
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in txt.split("\n")]
    return "\n".join(l for l in lines if l)
def pdf_text(path):
    out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    keep = []
    started = False
    for ln in out.split("\n"):
        if re.match(r"\s*[\[<]\d{3,4}[rv]\s*[\]>]", ln): started = True
        if not started: continue
        if re.search(r"G\. BILBAO|LAZARRAGA ESKUIZKRIBUA|Creative Commons|OHAR PALEOGRAFIKOAK", ln): continue
        if "G. BILBAO" in ln or "\f" in ln and not ln.strip("\f").strip(): continue
        if re.match(r"\S", ln) and not re.match(r"[\[<]\d{3,4}[rv]", ln): continue   # footnotes start at column 0
        if re.match(r"\s{1,4}\S", ln): continue                                    # footnote continuation lines
        ln = re.sub(r"[\[<]\d{3,4}[rv]\s*[\]>]", " ", ln)
        ln = re.sub(r"\s{4,}\d{1,3}\s*$", "", ln)                                  # line numbers at right margin
        ln = re.sub(r"(?<=[^\W\d_])\d{1,3}(?=\W|$)", "", ln)                      # footnote call numbers glued to words
        ln = re.sub(r"(?<=[;,.:?!…’”)])\d{1,3}(?=\s|$)", "", ln)
        if ln.strip(): keep.append(re.sub(r"\s+", " ", ln).strip())
    return "\n".join(keep)
# Text A: web pages
n_a = 0
al = h.get(B + "testua/artzainliburua.html", "files/artzainliburua.html")
h.add("AL.txt", html_text(al), language=LANG, year=None, dateless_in_window=True, source="Lazarraga manuscript, Artzain-liburua (text A, web edition)", url=B + "testua/artzainliburua.html")
for num, page in re.findall(r'class="numcol">(A\d+)</td>\s*<td[^>]*><a href="testua/frameset\.html\?(poema_\d+\.html)', toc):
    html = h.get(B + "testua/" + page, f"files/{page}")
    h.add(f"{num}.txt", html_text(html), language=LANG, year=None, dateless_in_window=True, source=f"Lazarraga manuscript, {num} (text A, web edition)", url=B + "testua/" + page)
# Text B: PDFs (eu = original spelling)
for n in re.findall(r"dokumentuak/eu/20/B/(B\d+)-2\.0-eu\.pdf", toc):
    rel = f"files/{n}-2.0-eu.pdf"
    h.get(B + f"dokumentuak/eu/20/B/{n}-2.0-eu.pdf", rel, binary=True)
    h.add(f"{n}.txt", pdf_text(str(h.dir / rel)), language=LANG, year=None, dateless_in_window=True, source=f"Lazarraga manuscript, {n} (text B, PDF 'eu' transcription)", url=B + f"dokumentuak/eu/20/B/{n}-2.0-eu.pdf")
for r in h.records: print(r["filename"], len(r["raw"].split()))
print(h.finish(method="Text A (Artzain-liburua + A1-A29): HTML poem pages (testua/poema_NNNN.html), keeping only the transcription cell (original spelling 'eu'), removing intro, footnote call-outs, line numbers and folio markers. Text B (B1-B34): the 'eu' PDF per piece (pdftotext -layout), keeping the indented poem lines after the first folio marker and dropping introductions, footnotes, line numbers and note numbers. Modernised-spelling (gg) and Spanish (es) versions not fetched.",
  coverage="64 of 65 catalogued items: AL, A1-A29, B1-B34. Text C (signatures, monograms, loose words) has no working link on the site (C_testua_osorik_2.0.pdf returns 404), so it is missing.",
  problems=["Text C not harvested: PDF link is broken (404)", "B pieces extracted from PDF layout by heuristics; stray footnote fragments or lost digits possible", "Undated: manuscript c. 1564-1602, treated as dateless_in_window", "Text AL pages contain lacunae brackets (e.g. 'bero e[') kept as in the edition", "robots.txt of www.ehu.eus does not disallow /monumenta/"]))
