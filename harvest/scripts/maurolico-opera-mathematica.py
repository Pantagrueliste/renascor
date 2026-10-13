import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html, posixpath
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest
h = Harvest("maurolico-opera-mathematica")
B = "https://people.dm.unipi.it/maurolic/"
problems = []
links = json.load(open(HD + "/tmp/mauro_links.json"))
pages = set()
for k, v in links.items():
    for l in v:
        if not l.startswith("edizioni/") or not l.endswith(".htm"): continue
        name = posixpath.basename(l)
        if name.startswith("intro") : continue
        if re.search(r"[0-9][fv]\.htm$", name): continue     # apparatus / variant pages
        pages.add(l)
for k in links:   # text pages that are themselves entry points (astro02 etc.)
    name = posixpath.basename(k)
    if not name.startswith("intro") and not re.search(r"[0-9][fv]\.htm$", name): pages.add(k)
pages = sorted(pages)
print(len(pages), file=sys.stderr)
ITAL = {'che','il','della','delle','gli','sono','nel','dal','questo','quella','del','dei','alla','molto','come','perche'}
byw = {}
for p in pages:
    try:
        s = h.get(B + p, "files/" + p)
    except Exception as e:
        problems.append(f"{p}: {e}"); continue
    a = s.find("<!-- corps")
    b = s.find("<!-- /corps")
    if a < 0:
        problems.append(f"{p}: no corps marker"); continue
    t = s[a:b if b > 0 else None]
    t = re.sub(r"<sup>.*?</sup>", "", t, flags=re.S | re.I)
    t = re.sub(r"<font[^>]*color=(?:maroon|green)[^>]*>.*?</font>", "", t, flags=re.S | re.I)
    t = re.sub(r"<font size=-1>\s*\[[^\]]*\]\s*</font>", "", t, flags=re.I)
    t = re.sub(r"<center>\s*\[[IVXLC0-9]+\]\s*</center>", "", t, flags=re.I)
    t = re.sub(r"<img[^>]*>", "", t, flags=re.I)
    t = re.sub(r"<(br|/p|/tr|/center|/h\d|/div)[^>]*>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    if t:
        byw.setdefault(posixpath.dirname(p), []).append((p, t))
for d, items in sorted(byw.items()):
    raw = "<TEI><text><body>" + "".join(f"<p>{html.escape(t, quote=False)}</p>" for _, t in items) + "</body></text></TEI>"
    alltxt = " ".join(t for _, t in items).lower()
    ws = re.findall(r"[a-zàèéìòù']+", alltxt)
    it = sum(1 for w in ws if w in ITAL)
    lang = "Italian" if ws and it / len(ws) > 0.02 else "Latin"
    if lang == "Italian": problems.append(f"{d}: detected as Italian ({it/len(ws):.1%} Italian marker words)")
    h.add(d.replace("/", "__") + ".xml", raw, language=lang, year=None, dateless_in_window=True,
          source="Maurolico, " + d, url=B + d + "/intro.htm")
rep = h.finish(method="Site map (pianta.htm) -> every edizioni/**/intro.htm -> text pages (<work>-N.htm, edition text 'livello 0'); extracted the <!-- corps --> block, removing paragraph numbers, folio markers, variant-reading superscripts, figure captions, images. Variant (-Nv.htm) and apparatus (-Nf.htm) pages and the Italian/French/English introductions skipped. One record per work directory.",
  coverage=f"{len(pages)} text pages fetched, grouped into {len(byw)} works/sections. Not included: 'Instrumenta Maurolyciana' (catalogues, bibliography, biography), source-image sites (login), apparatus pages.",
  problems=problems[:30] + ["No per-text dates online: all works are by Maurolico (1494-1575), so year=None with dateless_in_window=True. Some sections are Maurolico's Latin versions/restorations of ancient mathematicians (Euclid, Archimedes, Apollonius, Menelaus, Theodosius, Serenus) which still count as his 16th-century Latin text; the sections of the site are frames-based HTML so a few cross-listed pages may belong to a different work group."])
print(json.dumps({k: rep[k] for k in ("texts_total","words_total","texts_in_window","words_in_window")}))
