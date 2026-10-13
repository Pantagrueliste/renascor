import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
B = "https://corpusmallorca.es/"   # www. host has a certificate for the apex only
h = Harvest("corpus-mallorca", delay=1.0)
lst = h.get(B + "ajax_documentos.php?grupo=&corpus=&archivo=&provincia=&tipo=&r=1", "files/documentos.html")
docs = re.findall(r'<option value= "([^"]+)">(.*?)</option>', lst, re.S)
print(len(docs), "documents")
fails = []
for did, title in docs:
    try:
        s = h.get(f"{B}documento.php?documento={did}&paleografica=on&critica=on&mayusculas=off&regex=off&selDonde=&busqueda=", f"files/doc/{did}.html")
    except Exception as e:
        fails.append((did, str(e))); continue
    soup = BeautifulSoup(s, "lxml")
    cabs = [td.get_text(" ", strip=True) for td in soup.select("td.cab")]
    date = next((c for c in cabs if re.match(r"\d{4}\b", c)), "")
    y = first_year(date)
    tp = soup.select_one("td.textopaleo")
    if tp is None: fails.append((did, "no paleographic text")); continue
    for sp in tp.select("span.linea"): sp.decompose()
    for a in tp.find_all("a"): a.decompose()
    t = tp.get_text("")
    t = re.sub(r"\[\s*(?:lat|cat|margen|[a-z]{2,6})\.?\s*:\s*", "[", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*([a-záéíóúñ])\s{1}(?=[a-záéíóúñ])", r"\1 ", t) if False else t
    t = t.strip()
    h.add(f"{did}.txt", t, language="Spanish", year=y, source=f"Corpus Mallorca {did}: {html.unescape(title).strip()[:140]}", url=f"{B}documento.php?documento={did}")
rep = h.finish(method="No bulk download. Document list from the site's ajax_documentos.php (all ids), then each documento.php page; kept only the 'transcripcion paleografica' column (diplomatic), dropping facsimile links, line numbers, header block, regesto and the critical presentation.",
  coverage="All %d documents in the corpus (1640-1909 per catalogue); out-of-window years kept in staging." % len(docs) + (f" {len(fails)} failed." if fails else ""),
  problems=["Language tagged 'Spanish' for all; passages in Latin or Catalan inside documents are included, editorial language tags like [lat.:] were stripped to a bracket.",
            "Year = first year in the document's date line; apparatus-free text but word splits at line ends follow the transcription."] + [f"fail {a}: {b}" for a, b in fails[:20]])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
