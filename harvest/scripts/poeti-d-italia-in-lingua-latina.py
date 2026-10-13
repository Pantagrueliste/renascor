import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html, time, json
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, slug
from bs4 import BeautifulSoup
B = "https://www.poetiditalia.it"
h = Harvest("poeti-d-italia-in-lingua-latina")

def post(url, data, rel):
    p = h.dir / rel
    if p.exists(): return p.read_text(encoding="utf-8")
    wait = h.delay - (time.time() - h._last)
    if wait > 0: time.sleep(wait)
    r = h.s.post(url, data=data, timeout=60)
    h._last = time.time()
    r.raise_for_status()
    r.encoding = "utf-8"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(r.text, encoding="utf-8")
    return r.text

idx = h.get(B + "/indici/autori/tipo/chrono", "files/chrono.html")
sp = BeautifulSoup(idx, "html.parser")
authors, section = [], None
for tr in sp.select("table.HI tr"):
    td = tr.find("td")
    if td is None: continue
    if "aetas" in (td.get("class") or []):
        section = td.get_text(" ", strip=True); continue
    if not re.match(r"authors\d+", tr.get("id", "")): continue
    b = td.find("b") or td.find("i")
    name = b.get_text(" ", strip=True) if b else td.get_text(" ", strip=True)
    dat = td.find("span", class_="data")
    authors.append((int(tr["id"][7:]), name, dat.get_text(" ", strip=True) if dat else "", section))
sel = [a for a in authors if a[3] and (a[3].startswith("Umanisti") or a[3].startswith("Prima"))]
print(len(authors), len(sel), file=sys.stderr)

def approx_year(d, section):
    d = html.unescape(d).replace("\x86", "+")
    ys = [int(y) for y in re.findall(r"(?<!\d)(1[3-7]\d\d)(?!\d)", d)]
    low = d.lower()
    m = re.search(r"saec\.\s*(XIV|XV|XVI|XVII)\b\s*(in|ex|med|1|2)?", d)
    if len(ys) >= 2: return (min(ys) + 20 + max(ys)) // 2, "floruit midpoint (birth+20 .. death)"
    if len(ys) == 1:
        return ys[0] - (10 if ("+" in d or "†" in d or "ante" in low) else 0), "single date in author record"
    if m:
        base = {"XIV": 1300, "XV": 1400, "XVI": 1500, "XVII": 1600}[m.group(1)]
        off = {"in": 10, "1": 25, "med": 50, "2": 75, "ex": 90, None: 50}[m.group(2)]
        return base + off, "century in author record"
    return None, "no date in author record"

probs = []
nwork = 0
for aid, name, dat, sec in sel:
    try:
        s = post(f"{B}/indici/autori/idautori/{aid}", {"tipo": "chrono", "lettera": "A"}, f"files/author_{aid}.html")
    except Exception as e:
        probs.append(f"author {aid} {name}: {e}"); continue
    sa = BeautifulSoup(s, "html.parser")
    box = sa.select_one("#div_opere")
    if not box: probs.append(f"author {aid} {name}: no work list"); continue
    y, basis = approx_year(dat, sec)
    for a in box.select("a.opera"):
        href = a.get("href", "")
        code = href.split("/codice/", 1)[-1]
        if not code or code == href: continue
        title = a.get_text(" ", strip=True)
        ed = a.find_next("span", class_="edizione")
        ed = ed.get_text(" ", strip=True) if ed else ""
        rel = "files/text_" + slug(code) + ".html"
        try:
            t = h.get(B + href.replace("|", "%7C"), rel)
        except Exception as e:
            probs.append(f"text {code}: {e}"); continue
        st = BeautifulSoup(t, "html.parser")
        d = st.select_one("#div-text-MQDQ")
        if not d: probs.append(f"text {code}: no text div"); continue
        lines = []
        for p in d.find_all("p"):
            c = " ".join(p.get("class") or [])
            if c in ("c_n", "blank", "c_t", "titolo", "c_tit") : continue
            tx = p.get_text(" ", strip=True).replace("\xa0", " ")
            tx = re.sub(r"\s+", " ", tx).strip()
            if tx: lines.append(tx)
        raw = "\n".join(lines)
        if not raw.strip(): probs.append(f"text {code}: empty"); continue
        wy, wbasis = y, basis
        if y is None or name.lower() == "carmina libraria":
            m = re.findall(r"(?<!\d)(1[3-7]\d\d)(?!\d)", title + " " + ed)
            if m: wy, wbasis = int(m[-1]), "print year in the edition note of the work (carmina libraria)"
        h.add(slug(code) + ".txt", raw, language="Latin", year=wy, source=f"Poeti d'Italia in lingua latina: {name}, {title} {ed}".strip(),
              url=B + href, author=name, author_dates=dat, year_basis=wbasis)
        nwork += 1
nody = len([r for r in h.records if r["year"] is None])
if nody: probs.append(f"{nody} texts have no date in the author record (year=None, not counted)")
probs.append("Resource gives no per-work dates except print years in the edition notes of the 'carmina libraria' (book paratexts), which are used for those; for all others the year is an approximation from the author's dates (midpoint of birth+20..death, or century). Texts of authors who lived mostly before 1450 may be miscounted as in-window and vice versa; treat counts as approximate.")
probs.append("Texts are modern critical editions (edition named on each text page) of poems that survive in manuscripts and prints, not diplomatic transcriptions. Verse numbers, poem numbers/titles (c_t) and editorial elements dropped.")
probs.append(f"Only the sections 'Umanisti del Quattrocento' and 'Prima meta del Cinquecento' of the chronological index were harvested ({len(sel)} of {len(authors)} index entries); 'Da Dante a Petrarca' (1250-1374) skipped as pre-window.")
rep = h.finish(method="Chronological author index; per-author work list obtained by the site's own POST (indici/autori/idautori/N); text pages /testo/testo/codice/<code> parsed from div#div-text-MQDQ",
               coverage=f"{nwork} works by {len(sel)} index entries of the Quattrocento and early Cinquecento sections (all works listed)", problems=probs)
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")})
