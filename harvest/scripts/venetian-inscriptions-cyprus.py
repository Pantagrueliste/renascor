import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
B = "https://venetianinscriptions.cyi.ac.cy"
h = Harvest("venetian-inscriptions-cyprus")
home = h.get(B + "/", "files/home.html")
places = sorted(set(re.findall(r'href="(/place/\d+/)"', home)), key=lambda x: int(re.search(r"\d+", x).group()))
eps = []
for p in places:
    pn = re.search(r"/(\d+)/", p).group(1)
    s = h.get(B + p, f"files/place_{pn}.html")
    for e in re.findall(r'href="(/place/epigraphy/\d+/)"', s):
        if e not in eps: eps.append(e)
CEN = {"beginning": 0, "early": 10, "first half": 25, "middle": 50, "mid": 50, "second half": 75, "late": 85, "end": 90}
def yr(txt):
    if not txt: return None
    y = first_year(txt)
    if y: return y
    m = re.search(r"(\d+)(?:st|nd|rd|th) century", txt)
    if m:
        base = (int(m.group(1)) - 1) * 100
        low = txt.lower()
        for k, v in CEN.items():
            if k in low: return base + v
        return base + 50
    return None
probs = []
for e in eps:
    n = re.search(r"\d+", e.split("epigraphy")[1]).group()
    s = h.get(B + e, f"files/epigraphy_{n}.html")
    sp = BeautifulSoup(s, "html.parser")
    meta = {}
    for tr in sp.select("table tr"):
        tds = tr.find_all("td")
        if len(tds) == 2: meta[tds[0].get_text(strip=True).rstrip(":")] = tds[1].get_text(" ", strip=True)
    ident = (sp.select_one("h5.card-title").get_text(strip=True).replace(" Information", "") if sp.select_one("h5.card-title") else n)
    for x in sp.select("script, style"): x.decompose()
    t = sp.get_text("\n")
    m = re.search(r"Transcription\s*-\s*Diplomatic(.*?)(?:\n\s*Translation\s*\n|\n\s*Apparatus\s*\n)", t, re.S)
    dip = m.group(1) if m else ""
    lines = []
    skip = False
    for l in html.unescape(dip).replace("\xa0", " ").split("\n"):
        l = l.strip()
        if skip:
            if l.endswith(":"): skip = False
            continue
        if re.match(r"^Text (according to|from)\b", l):
            skip = not l.endswith(":"); continue
        if not l or re.match(r"^Column \w+:?$", l, re.I): continue
        if re.match(r"^(Inscription\b|The bibliographical sources)", l) or re.fullmatch(r"\d{1,2}", l): continue
        l = re.sub(r"^\d+\s+", "", l)
        lines.append(l)
    txt = "\n".join(lines)
    lang = meta.get("Language", "Latin")
    y1, y2 = yr(meta.get("Year From")), yr(meta.get("Year To"))
    y = y1 or y2
    if not txt.strip():
        probs.append(f"{ident} ({e}): no diplomatic transcription"); continue
    if y is None: probs.append(f"{ident}: date 'Uncertain' on the site; year=None, not counted (the resource does not say all texts fall in 1450-1700)")
    elif not (meta.get("Year From") or "").strip()[:1].isdigit(): pass
    h.add(f"{ident}.txt", txt, language=lang.split(",")[0].strip() or "Latin", year=y, source="Venetian Inscriptions in Cyprus (La Lettera e il Leone)", url=B + e,
          date_from=meta.get("Year From"), date_to=meta.get("Year To"))
probs.append("Diplomatic transcription (upper case, line numbers, column labels, 'Inscription N' labels and source-attribution lines dropped) used; interpreted transcription, translations, apparatus and descriptions excluded. Year = Year From; verbal dates ('End of 15th century') converted to an approximate year within the century.")
rep = h.finish(method="Place pages /place/N/ list inscription pages /place/epigraphy/N/; fetched each and extracted the diplomatic transcription block",
               coverage=f"{len(h.records)} of {len(eps)} inscription pages on {len(places)} places", problems=probs)
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")}, len(eps))
