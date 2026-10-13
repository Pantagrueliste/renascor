import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest, first_year
from lxml import html as LH
h = Harvest("dietrich-klostertagebuch")
B = "https://www.dietrich-edition.unibe.ch"
problems = []
VOLS = {"06": "1687-1688", "13": "1688-1690", "15": "1693-1694", "17": "1697-1698"}
total_pages = skipped = 0
for v in VOLS:
    toc = h.get(f"{B}/band_{v}/inhaltsverzeichnis.html", f"files/band_{v}/inhaltsverzeichnis.html")
    link = re.search(r'href="\./([a-z]+_\d+\.html)"', toc).group(1)
    first = h.get(f"{B}/band_{v}/{link}", f"files/band_{v}/{link}")
    pages = re.findall(r'<option value="([a-z]+_\d+\.html)"', first)
    pages = list(dict.fromkeys(pages))
    parts = []
    years = []
    for p in pages:
        try:
            s = h.get(f"{B}/band_{v}/{p}", f"files/band_{v}/{p}")
        except Exception as e:
            problems.append(f"band {v} {p}: {e}"); continue
        doc = LH.fromstring(s)
        meta = doc.xpath('string(//div[@class="title-meta"])')
        y = first_year(meta)
        total_pages += 1
        main = doc.xpath('//div[@id="main-text"]')
        if not main: skipped += 1; continue
        lines = []
        for lt in main[0].xpath('.//div[contains(@class,"line-text")]'):
            t = re.sub(r"\s+", " ", lt.text_content()).strip()
            if t: lines.append(t)
        marg = []
        for r in doc.xpath('//div[@id="pf-marginalia"]//div[contains(@class,"marginal-row")]'):
            for b in r.xpath('.//span[@class="bpag"]'): b.getparent().remove(b)
            t = re.sub(r"\s+", " ", r.text_content()).strip()
            if t: marg.append(t)
        if y is None and not lines:
            skipped += 1; continue
        if y: years.append(y)
        parts.append("\n".join(lines) + ("\n" + "\n".join(marg) if marg else ""))
    raw = "<TEI><text><body>" + "".join(f"<p>{html.escape(t.strip(), quote=False)}</p>" for t in parts if t.strip()) + "</body></text></TEI>"
    yr = min(years) if years else None
    h.add(f"band_{v}.xml", raw, language="German", year=yr, source=f"Dietrich, Klostertagebuch Einsiedeln, Band {int(v)} ({VOLS[v]})", url=f"{B}/band_{v}/inhaltsverzeichnis.html")
rep = h.finish(method="Crawled every scan page (einsiedeln_NNN.html, page list from the page selector) of the four published volumes; kept the diplomatic transcription (#main-text lines) and the author's marginalia text (#pf-marginalia), dropped navigation, Latin translations (tooltip attributes / marginalia translation boxes), registers and covers",
  coverage=f"All four published volumes (Band 6, 13, 15, 17), one record per volume; {total_pages} pages fetched, {skipped} without text. The other 14 volumes are unpublished.",
  problems=problems + ["Text is mixed German/Latin; labelled German (main language). Year = earliest year seen in the volume's page headers; volumes span two to three years."])
print(json.dumps({k: rep[k] for k in ("texts_total","words_total","texts_in_window","words_in_window")}))
