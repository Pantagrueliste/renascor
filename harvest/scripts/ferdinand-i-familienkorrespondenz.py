import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
import requests
h = Harvest("ferdinand-i-familienkorrespondenz")
base = "https://ferdinand-korrespondenz.acdh.oeaw.ac.at/"
idx = h.get(base + "letters.html", "files/letters.html")
ids = sorted(set(re.findall(r'href="(A\d+[a-z]?)\.html"', idx)), key=lambda s: (int(re.sub(r"\D", "", s)), s))
print(len(ids), "letters listed")
T = "http://www.tei-c.org/ns/1.0"
STOP = {
 "Latin": set("et est in non ad quod cum sed ut quae qui de ex esse sunt per enim etiam vestra serenitas nostra".split()),
 "German": set("und der die das ist nicht mit den von zu ein eine auch sich dem dasz wie auf ich euch dir mir".split()),
 "French": set("et le la les de des que est pour dans un une qui par sur ne pas en du vous je nous".split()),
 "Spanish": set("y el la los de que en por con un una se no es para su del muy como".split()),
 "Italian": set("e il la di che per con un una non del della sono si".split()),
}
def lang(t):
    w = re.findall(r"[a-zA-Z]+", t.lower())
    sc = {k: sum(x in s for x in w) for k, s in STOP.items()}
    return max(sc, key=sc.get)
miss = []
noyear = 0
for i in ids:
    try:
        xml = h.get(f"{base}data/dtabf_id/band_001/{i}.xml", f"files/{i}.xml")
    except requests.HTTPError:
        miss.append(i); continue
    root = etree.fromstring(xml.encode("utf-8"))
    letters = root.xpath("//t:div[@type='letter']", namespaces={"t": T})
    if not letters:
        miss.append(i); continue
    body = letters[0]
    # drop footnote call marks like <hi sup>a</hi>)
    for el in list(body.iter("{%s}hi" % T)):
        if el.get("rendition") == "#sup" and re.fullmatch(r"[a-z0-9]{1,2}", "".join(el.itertext()).strip()) and (el.tail or "").startswith(")"):
            el.tail = el.tail[1:]
            p = el.getparent(); prev = el.getprevious()
            if prev is not None: prev.tail = (prev.tail or "") + (el.tail or "")
            else: p.text = (p.text or "") + (el.tail or "")
            p.remove(el)
    raw_txt = " ".join(body.itertext())
    if len(raw_txt.split()) < 3:
        miss.append(i); continue
    d = root.xpath("//t:correspAction[@type='sent']/t:date", namespaces={"t": T})
    yr = None
    if d:
        yr = first_year(d[0].get("when") or "".join(d[0].itertext()))
    if yr is None:
        t = root.xpath("string(//t:title[@type='sub'])", namespaces={"t": T}); yr = first_year(t)
    noyear += yr is None
    raw = f'<TEI xmlns="{T}"><teiHeader/><text><body>' + etree.tostring(body, encoding="unicode") + "</body></text></TEI>"
    h.add(f"{i}.xml", raw, language=lang(raw_txt), year=yr, source="Ferdinand I Familienkorrespondenz Bd. 1", url=f"{base}{i}.html")
print(h.finish(
  method="Letter list from letters.html; TEI file per letter from data/dtabf_id/band_001/<id>.xml (cached). Only the div[@type=letter] (transcription) kept; German/English summaries, archive notes, commentary and footnotes dropped. Year from correspAction[sent]/date; language by stopword heuristic.",
  coverage=f"All letter records listed ({len(ids)}); {len(ids)-len(miss)} have transcribed text and were harvested; {len(miss)} without transcription/XML skipped: {', '.join(miss[:80])}",
  problems=["Language assigned by heuristic (Latin/German/French/Spanish/Italian mix).", f"{noyear} letters without usable year."]))
