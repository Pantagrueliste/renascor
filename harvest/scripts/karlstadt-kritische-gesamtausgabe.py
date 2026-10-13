import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
B = "http://diglib.hab.de/edoc/ed000216/"
h = Harvest("karlstadt-kritische-gesamtausgabe", delay=1.0)
mets = h.get(B + "mets.xml", "files/mets.xml")
ids = sorted(set(re.findall(r'texts/([^/"]+)/\1_transcript\.xml', mets)))
# probe numbers missing from the METS (the notes count 74 transcripts, METS lists %d)
cand = [f"{n:03d}" for n in range(1, 90)]
fails = []
files = {}
for i in ids + [c for c in cand if c not in ids]:
    rel = f"files/xml/{i}_transcript.xml"
    try:
        files[i] = h.get(f"{B}texts/{i}/{i}_transcript.xml", rel)
    except Exception as e:
        if i in ids: fails.append((i, str(e)))
print(len(ids), "in METS;", len(files), "fetched")
from lxml import etree
T = "{http://www.tei-c.org/ns/1.0}"
def drop(el):
    tail = el.tail
    p = el.getparent(); prev = el.getprevious()
    if tail:
        if prev is not None: prev.tail = (prev.tail or "") + tail
        else: p.text = (p.text or "") + tail
    p.remove(el)
LAT = set("et in est non ad cum quae quod ut sed qui si nec ab ex vel quam enim etiam sunt esse atque aut autem ergo quia ita sicut".split())
GER = set("und der die das ist nicht ich zu den mit von ein eine auf fur für sich dem auch als wie es er sie wir ihr dass daß so aber dy vnd yn wan wen mir mich dir".split())
nfoot = 0
for i, raw in sorted(files.items()):
    root = etree.fromstring(raw.encode("utf-8"))
    hdr = root.find(T + "teiHeader")
    titles = " ".join("".join(t.itertext()) for t in hdr.iter(T + "title"))
    y = first_year(re.sub(r"\s+", " ", titles))
    for n in list(root.iter(T + "note")):
        if n.get("type") in ("footnote", "crit_app", "comment"):
            drop(n); nfoot += 1
    for tag in ("corr", "reg", "expan"):  # keep original spelling (sic/orig/abbr); drop editorial regularisation
        pass
    for el in list(root.iter(T + "corr", T + "reg")):
        drop(el)
    text = root.find(T + "text")
    for b in text.findall(T + "back"):
        text.remove(b)
    body = etree.tostring(text, encoding="unicode")
    body = re.sub(r"\sxmlns(:\w+)?=\"[^\"]+\"", "", body)
    ws = re.findall(r"[a-zäöüß]+", re.sub(r"<[^>]+>", " ", body).lower())
    lat = sum(w in LAT for w in ws); ger = sum(w in GER for w in ws)
    lang = "Latin" if lat > ger else "German"
    h.add(f"{i}_transcript.xml", f"<TEI>{body}</TEI>", language=lang, year=y,
          source=f"Karlstadt Kritische Gesamtausgabe, text {i}: " + re.sub(r"\s+", " ", "".join(next(hdr.iter(T + "title")).itertext()))[:120],
          url=f"{B}texts/{i}/{i}_transcript.xml", dateless_in_window=False)
rep = h.finish(method="Per-text TEI transcripts fetched one by one (texts/<id>/<id>_transcript.xml; list from mets.xml, plus probing 001-089); no bulk export exists. Kept <text> without <back>; removed editorial footnotes, critical-apparatus notes and comments, and <corr>/<reg> (original spellings and marginal notes kept); header, introductions, translations and registers not fetched.",
  coverage="All %d transcript files found (METS lists %d; catalogue says 74)." % (len(files), len(ids)) + (f" Failed: {fails}" if fails else ""),
  problems=["Language chosen per text by Latin/German stopword heuristic (many items mix Latin and German).",
            "Year from the date in the title (first year when a span, e.g. 'zwischen 1516 ... 1517').",
            "A few 'Verschollen' (lost) letters are only stubs with little or no text.",
            "HAB terms allow private scholarly use, forbid commercial use or republication."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
