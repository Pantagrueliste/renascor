import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, subprocess, urllib.parse
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
BASE = "https://www.unav.edu"
h = Harvest("unav-documentos-privados-antiguos")
page = h.get(BASE + "/web/facultad-de-filosofia-y-letras/documentos-privados-antiguos", "files/page.html")
links = []
for a in re.findall(r'href="(/documents/[^"#]+\.pdf[^"]*)"', page):
    if a not in links: links.append(a)
nopt = 0
for a in links:
    fname = urllib.parse.unquote(a.split("/")[4]) if a.count("/") >= 4 else a
    rel = "files/" + slug(fname)
    try:
        h.get(BASE + a, rel, binary=True)
    except Exception as e:
        print("FAIL", a, e); continue
    txt = subprocess.run(["pdftotext", "-layout", str(h.dir / rel), "-"], capture_output=True, text=True).stdout
    head = txt[:700]
    m = re.search(r"TRANSCRIPCI[ÓO]N PALEOGR[ÁA]FICA(.*?)(?:PRESENTACI[ÓO]N CR[ÍI]TICA|$)", txt, re.S)
    if not m:
        nopt += 1; print("no transcription:", fname); continue
    body = m.group(1)
    body = re.sub(r"\{[^}]*\}", " ", body)
    body = re.sub(r"\[(?:roto|mano|signo|rúbrica)[^\]]*\]", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    lines = [l for l in head.split("\n") if l.strip()]
    y = first_year(lines[1]) if len(lines) > 1 else None
    y = y or first_year(fname)
    lang = "Basque" if re.search(r"\b(eta|gaitz|dut|zuen|baita)\b", body) and len(re.findall(r"\b(eta|dut|zuen|da)\b", body)) > 20 else "Spanish"
    title = " | ".join(lines[:4])
    h.add(slug(fname).replace(".pdf", "") + ".txt", body, language=lang, year=y, source="Documentos privados antiguos (Universidad de Navarra): " + title, url=BASE + a)
print(len(links), "pdfs;", nopt, "without transcription block")
print(h.finish(method="Downloaded all PDFs linked from the collection page (105) and extracted the 'TRANSCRIPCIÓN PALEOGRÁFICA' section with pdftotext; dropped the metadata header, the 'PRESENTACIÓN CRÍTICA' version, {folio/line} markers and bracketed editorial notes; year from the date line of the header",
  coverage="All 105 documents of the page (1550-1900); about 8 fall in 1450-1700, the rest are kept in staging with their year. robots.txt does not disallow /documents/29062.",
  problems=["Paleographic transcription keeps scribal abbreviations in <...> expansions, as transcribed", "Language is a heuristic (Spanish unless Basque function words are frequent)"]))
