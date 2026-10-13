import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, subprocess
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
B = "https://www.human.ula.ve/linguisticahispanica/investigacion/"
h = Harvest("ula-corpus-documentos-coloniales-merida")
page = h.get(B + "corpus_cdc.php", "files/corpus_cdc.html")
titles = {}
for n, t in re.findall(r"(?<!\d)(\d{1,2})\s*\.\s*(?:&nbsp;)?\s*\*?\s*([^<\n]{10,})", re.sub(r"</?(?:br|p|li|a)[^>]*>", "\n", page)):
    titles.setdefault(int(n), re.sub(r"&\w+;", " ", t).strip())
def clean(txt):
    paras = re.split(r"\n\s*\n", txt.replace("\f", "\n\n"))
    # drop title block and archive reference block (header editorial)
    head = []
    out = []
    for i, p in enumerate(paras):
        if re.fullmatch(r"\s*\d+\s*", p): continue
        out.append(p)
    # remove header: leading paragraphs up to first '(fol.' marker paragraph or archival line
    k = 0
    for i, p in enumerate(out[:6]):
        if re.search(r"\(fol\.|\bfol\b", p): k = i; break
        if re.search(r"Archivo|A\.G\.I|AGI|Biblioteca|ff?\.\s*\d", p) or i == 0: k = i + 1
    out = out[k:]
    lines = []
    for ln in "\n".join(out).split("\n"):
        ln = re.sub(r"^\s*\d{1,3}\s{2,}", "", ln)   # margin line numbers
        ln = re.sub(r"^\s*\d{1,3}$", "", ln)
        ln = ln.strip()
        if re.fullmatch(r"\(?\s*fol\.[^)]*\)?|\(?\s*fols?\.\s*[\w\- ]+\)?", ln): continue
        lines.append(ln)
    t = " ".join(l for l in lines if l)
    t = re.sub(r"\[(?:sic|en blanco|rúbrica|dirección|al margen)[^\]]*\]", " ", t)
    return re.sub(r"\s+", " ", t).strip()
for n in range(1, 38):
    f = f"{n:02d}.pdf"
    data = h.get(B + f"documentos/{f}", f"files/{f}", binary=True)
    txt = subprocess.run(["pdftotext", "-layout", str(h.dir / "files" / f), "-"], capture_output=True, text=True).stdout
    title = titles.get(n, "")
    y = first_year(re.sub(r"^.*\(", "", title)) or first_year(txt[:600])
    raw = clean(txt)
    print(n, y, len(raw.split()), title[:60])
    h.add(f"cdc_{n:02d}.txt", raw, language="Spanish", year=y, source="Corpus de Documentos Coloniales de Mérida: " + title, url=B + f"documentos/{f}")
print(h.finish(method="Downloaded the 37 per-document PDFs listed on corpus_cdc.php and extracted the text layer with pdftotext -layout; removed title/archive-reference header, margin line numbers, page numbers, folio markers and bracketed editorial notes ([sic], [en blanco], [rúbrica]...); year = last year in the document title/date line",
  coverage="All 37 documents (1564-1657 per catalogue). Combined corpus PDF and historical survey (resena_historica.pdf) not taken.",
  problems=["Header stripping is heuristic; some editorial footnotes may remain", "Documents with two dates use the first (e.g. doc 19: 1621 and 1622)"]))
