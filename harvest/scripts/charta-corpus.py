import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("charta-corpus", delay=1.0)
listing = h.get("https://corpora.uah.es/charta/index.php?action=corpus", "files/listing.html")
rows = re.findall(r"<tr id='' >(.*?)(?=<tr id=|</table>)", listing, re.S)
print(len(rows), "rows")
LAT = set("et in est non ad cum quae quod ut sed qui si nec ab ex vel quam enim etiam sunt esse atque aut dicti dictus domini anno".split())
SPA = set("de la el que y en los las del por con para se su al un una es como dicho dicha non nos vos".split())
fails = []
for r in rows:
    m = re.search(r"action=file&id=([^\"'&]+)\.xml", r)
    if not m: continue
    cid = m.group(1)
    tds = re.findall(r"<td>(.*?)</td>", r, re.S)
    ym = re.search(r"q=cron:([^;']+);'", r)
    y = first_year(ym.group(1)) if ym else None
    if y is None and ym:
        m3 = re.search(r'(?<!\d)(\d{3,4})(?!\d)', ym.group(1)); y = int(m3.group(1)) if m3 else None
    title = re.sub(r"<[^>]+>", "", tds[2]) if len(tds) > 2 else ""
    try:
        raw = h.get(f"https://corpora.uah.es/charta/xmlfiles/{cid}.xml", f"files/xml/{cid}.xml")
    except Exception as e:
        fails.append((cid, str(e))); continue
    if y is None:
        d = re.search(r'<origDate\b[^>]*?(?:when|notBefore|from)="([^"]+)"', raw)
        y = first_year(d.group(1)) if d else None
        if y is None and d:
            m3 = re.search(r'(?<!\d)(\d{3,4})(?!\d)', d.group(1)); y = int(m3.group(1)) if m3 else None
    body = re.search(r"<text\b.*</text>", raw, re.S)
    txt = body.group(0) if body else raw
    ws = re.findall(r"[a-záéíóúñ]+", re.sub(r"<[^>]+>", " ", txt).lower())
    lat = sum(w in LAT for w in ws); spa = sum(w in SPA for w in ws)
    lang = "Latin" if lat > spa else "Spanish"
    h.add(f"{cid}.xml", f"<TEI>{raw[raw.find('<teiHeader'):]}" if False else raw, language=lang, year=y,
          source=f"CHARTA {cid}: {html.unescape(title)[:150]}", url=f"https://corpora.uah.es/charta/xmlfiles/{cid}.xml")
rep = h.finish(method="Per-document TEI XML served at corpora.uah.es/charta/xmlfiles/<id>.xml (no bulk download); ids and years taken from the corpus listing page (all 787 documents).",
  coverage="All documents of the corpus listing (944-1871), out-of-window ones kept in staging with their year." + (f" {len(fails)} failed." if fails else ""),
  problems=["Files are TEITOK-tokenised paleographic transcriptions (one version only); language chosen by a Spanish/Latin stopword heuristic, so some Latin or Catalan passages are labelled with the dominant language only.",
            "Year from listing 'Año' (first year of a range)."] + [f"fail {a}: {b}" for a, b in fails[:20]])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
