import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from bs4 import BeautifulSoup
B = "https://magyar-irodalom.elte.hu/gepesk/bbom/"
h = Harvest("balassi-osszes-verse", delay=1.0)
def get(u, rel):
    return h.get(B + u, rel, binary=True).decode("iso-8859-2", "replace")
toc = get("kr98.htm", "files/kr98.htm")
abc = get("abc.htm", "files/abc.htm")
ids = []
for m in re.findall(r'krit/([a-z0-9]+)\.htm', toc + abc, re.I):
    if m not in ids: ids.append(m)
print(len(ids), "pages in contents lists")
fails = []
for pid in ids:
    # frameset ir0237.htm -> text frame r0237.htm ; prose note iproza1 -> rproza1
    rid = "r" + pid[2:] if pid.startswith("ir") else pid[1:] if pid.startswith("i") else pid
    try:
        s = get(f"krit/{rid}.htm", f"files/krit/{rid}.htm")
    except Exception as e:
        fails.append((pid, str(e))); continue
    soup = BeautifulSoup(s, "lxml")
    for t in soup(["script", "sup"]): t.decompose()
    for a in soup.find_all("a"):
        if a.get("name") is not None or (a.get("href") or "").startswith(("r%s" % pid[2:], "#")) and not a.get_text(strip=True).isalpha():
            if a.get_text(strip=True).isdigit() or not a.get_text(strip=True): a.decompose()
    for f in soup.find_all("font"):
        if f.get_text(strip=True).isdigit(): f.decompose()  # verse numbers / footnote numbers
    for br in soup.find_all("br"): br.replace_with("\n")
    for p in soup.find_all("p"): p.insert_after("\n\n")
    txt = (soup.body or soup).get_text()
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r" *\n *", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    title = soup.title.get_text(strip=True) if soup.title else ""
    h.add(f"{rid}.txt", txt, language="Hungarian", year=None, dateless_in_window=True,
          source=f"Balassi Bálint összes verse, {rid}", url=f"{B}krit/{rid}.htm")
rep = h.finish(method="No bulk export. Site is a set of HTML frames: poem list from kr98.htm / abc.htm, text frame of each poem (krit/r<nnnn>.htm), decoded as ISO-8859-2; kept only the critical-text frame (stripped verse and footnote numbers, apparatus/notes frames r*j/m/s/a not fetched).",
  coverage="All %d pages linked from the contents lists (poems, fragments, prose note)." % len(ids) + (f" {len(fails)} failed." if fails else ""),
  problems=["Text is the editor's critical text in modernised Hungarian spelling (original-spelling witnesses BC/FJK appear only in the apparatus, not harvested).",
            "No dates per poem on the site; year=None with dateless_in_window=True because all Balassi poems are from the 1570s-1594 (he died in 1594).",
            "A few prose notes/headings by the editor (e.g. dedication lines, melody indications) are part of the poem frame and kept."] + [f"fail {a}: {b}" for a, b in fails[:20]])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
