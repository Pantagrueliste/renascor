import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
from bs4 import BeautifulSoup
B = "https://bayle-correspondance.univ-st-etienne.fr/"
h = Harvest("bayle-correspondance", delay=1.0)
sm = h.get(B + "sitemap.xml", "files/sitemap.xml")
urls = [u for u in dict.fromkeys(u for u in re.findall(r"<loc>([^<]+)</loc>", sm) if "?Lettre-" in u)]
probs = []
n_noyear = 0
n_transl = 0
n_interp = 0
recs = []
FR = set('le la les de des du et que qui vous je il est un une pour dans ne pas ce se en au avec mais sur son sa ses mon ma mes votre vos par'.split())
LA = set('et est quod ad cum non in qui quae sed ut aut ab ex de si nec quo hoc esse sunt atque etiam quam'.split())
for u in urls:
    rel = "files/" + slug(u.split("?", 1)[1]) + ".html"
    try:
        s = h.get(u, rel)
    except Exception as e:
        probs.append(f"fetch failed {u}: {e}"); continue
    soup = BeautifulSoup(s, "html.parser")
    t = soup.select_one("h1.titre-article")
    tl = t.get_text(" ", strip=True).replace("\xa0", " ") if t else u
    box = soup.select_one("div.texte_lettre")
    if not box:
        probs.append(f"no texte_lettre {u}"); continue
    for x in box.select("span.spip_note_ref, script, style"):
        x.decompose()
    for br in box.find_all("br"): br.replace_with("\n")
    for blk in box.find_all(["p", "div"]): blk.insert_after("\n")
    txt = box.get_text("").replace("\xa0", " ").replace("*", "")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\s*\n\s*", "\n", txt).strip()
    dtxt = " ".join(d.get_text(" ", strip=True) for d in box.select("div.datedebut, div.datefin"))
    y = first_year(dtxt)
    # translation pages carry a link "Voir aussi [ Texte latin ]": they are modern French translations of Latin letters
    if any("Texte latin" in a.get_text() for a in soup.select("a.lien")):
        n_transl += 1; continue
    lang = "French"
    if "[ Latin ]" in tl:
        low = re.findall(r"[a-zà-ÿ]+", txt.lower())
        fr = sum(w in FR for w in low); la = sum(w in LA for w in low)
        lang = "Latin" if la > fr else "French"
        if lang == "French": probs.append(f"{u}: flagged [ Latin ] on the site but text is mostly French; labelled French")
    m = re.match(r"(?:\[ Latin \] )?Lettre (\d+)", tl)
    recs.append(dict(fn=slug(u.split("?", 1)[1]) + ".txt", raw=tl + "\n" + txt, lang=lang, y=y, u=u, num=int(m.group(1)) if m else None))
# undated letters: letters are numbered chronologically; use the neighbours' year only when they agree
dated = sorted((r["num"], r["y"]) for r in recs if r["y"] and r["num"])
import bisect
nums = [d[0] for d in dated]
for r in recs:
    extra = {}
    y = r["y"]
    if y is None and r["num"]:
        i = bisect.bisect_left(nums, r["num"])
        lo = dated[i-1][1] if i > 0 else None
        hi = dated[i][1] if i < len(dated) else None
        if lo and hi and lo == hi:
            y = lo; extra["year_basis"] = "neighbouring letters in the chronological numbering"
            n_interp += 1
    if y is None: n_noyear += 1
    h.add(r["fn"], r["raw"], language=r["lang"], year=y, source="Correspondance de Pierre Bayle", url=r["u"], dateless_in_window=True, **extra)
if n_interp:
    probs.append(f"{n_interp} letters without a date on the page got the year of their two neighbours in the chronological numbering (both equal)")
if n_noyear:
    probs.append(f"{n_noyear} letters without a parsable or interpolated year: year=None with dateless_in_window=True (the edition covers letters 1-1405, all dated 1662-1698 per the catalogue record)")
probs.append(f"{n_transl} pages that are modern French translations of Latin letters (link 'Texte latin') excluded")
probs.append("Letter pages include the letter text only (notes and footnote markers removed); the title line (letter number, sender, recipient) is kept as the first line.")
rep = h.finish(method="Sitemap.xml lists all letter pages (SPIP); fetched each, extracted div.texte_lettre (letter text), dropped notes, tags and footnote markers, title kept",
          coverage=f"{len(h.records)} letters (pages {len(urls)} in sitemap minus {n_transl} translation pages): letters 1-1405 of the online edition", problems=probs)
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")})
