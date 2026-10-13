import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
import json, re, subprocess, glob, os, requests
H = HARVEST_DIR + "/t/"
h = Harvest("cordiam", delay=1.0)
docs = json.load(open(H + "co_docs_years.json"))
files = {k: v[0] for k, v in docs.items()}
slice_year = {k: v[1] for k, v in docs.items()}
print(len(files), "documents listed", sum(files.values()), "words")
HDR = re.compile(r"^(Nombre|Siglo|Año|Autor|Autógrafo|País actual|Topónimo|Adscripción|Tipo textual|Archivo|Número de|Créditos|Facsimilar|Síntesis|Fecha|Periódico|Título|Lugar|Sección|Páginas?)\b")
import random
probs = []; bad = []; noyear = []; limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
for n, name in enumerate(sorted(files)):
    if limit and n >= limit: break
    rel = f"files/{name}.pdf"
    p = h.dir / rel
    if not p.exists():
        import time
        ok = False
        for attempt in range(6):
            try:
                h.get(f"https://www.cordiam.org/corpus/{name}.pdf", rel, binary=True); ok = True; break
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    bad.append(f"{name}: HTTP 404"); break
                time.sleep(20 * (attempt + 1))
            except requests.RequestException:
                time.sleep(20 * (attempt + 1))
        if not ok:
            if not any(b.startswith(name) for b in bad): bad.append(f"{name}: failed after retries")
            continue
    pages = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout.split("\f")
    head = pages[0]
    body = "\n".join(pages[1:]).strip()
    m = re.search(r"^Año:\s*(\d{4})", head, re.M)
    year = int(m.group(1)) if m else slice_year.get(name)
    if year is None: noyear.append(name)
    if not body:
        # no page break: strip header lines from page 1
        lines = head.splitlines()
        k = max([i for i, l in enumerate(lines) if HDR.match(l.strip())] + [-1])
        body = "\n".join(lines[k + 1:]).strip()
    body = re.sub(r"\{[^}]*\}", " ", body)
    body = re.sub(r"(?<=\s)/\d*(?=\s)", " ", body)
    body = body.replace("<", "[").replace(">", "]")
    body = re.sub(r"(?<=\s)//(?=\s)", " ", body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{2,}", "\n", body)
    h.add(name + ".txt", body, language="Spanish", year=year, source=f"CORDIAM document {name}", url=f"https://www.cordiam.org/corpus/{name}.pdf")
if bad: probs.append(f"{len(bad)} PDFs failed: {bad[:10]}")
if noyear: probs.append(f"{len(noyear)} documents without a year in the metadata: {noyear[:10]}")

probs.append("Document list obtained from the site's own 'Cantidad de palabras' function (POST 20-22/2022.1001?15), queried year by year 1494-1700 (7,340 documents, 8.11M words; the three sub-corpora Documentos and Literatura; Prensa is 18th-19th c. only). Texts downloaded as the per-document PDFs offered by the site ('Mostrar el documento'), page 1 (metadata sheet) dropped, line-break slashes, line numbers and {folio} markers removed. Semi-diplomatic transcriptions with abbreviations expanded (italic in PDF, kept as plain text).")
probs.append("Documents without a year in the metadata (century only) cannot be selected through the year filter and are not included. Language set to Spanish for all (indigenous-language or Latin passages possible).")
rep = h.finish(method="Document list via the site's subcorpus function, then PDF per document (1 s between requests); editorial <tags> in the PDF text such as <cit: ...> or <tach: ...> have their angle brackets replaced by square brackets so that the text is not mistaken for markup.", coverage="All documents with a year 1494-1700 in CORDIAM (Documentos and Literatura subcorpora)." if not limit else "TEST RUN", problems=probs)
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], rep["undated"])
