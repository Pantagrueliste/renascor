import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest
from lxml import html as LH
h = Harvest("cervantes-la-entretenida")
B = "https://entretenida.outofthewings.org/text/entretenida/princeps/"
problems = []
first = h.get(B + "I-1.html", "files/I-1.html")
pages = re.findall(r'<option value="([^"]+)"', first.split('id="selScene"')[1].split("</select>")[0])
parts = []
for p in pages:
    s = h.get(B + p + ".html", f"files/{p}.html")
    doc = LH.fromstring(s)
    nodes = doc.xpath('//div[contains(@class,"text") and contains(@class,"entretenida")]')
    if not nodes:
        problems.append(f"{p}: no text div"); continue
    n = nodes[0]
    for bad in n.xpath('.//span[@class="nmb"] | .//sup | .//span[@class="sz"] | .//script | .//select | .//form | .//span[@class="printOnly"]'):
        par = bad.getparent()
        if par is not None:
            if bad.tail:
                prev = bad.getprevious()
                if prev is not None: prev.tail = (prev.tail or "") + bad.tail
                else: par.text = (par.text or "") + bad.tail
            par.remove(bad)
    for br in n.xpath('.//br'):
        br.tail = "\n" + (br.tail or "")
    for blk in n.xpath('.//p | .//h1 | .//h2 | .//h3 | .//div[@class="speech"]'):
        blk.tail = "\n" + (blk.tail or "")
    txt = re.sub(r"[ \t\r\f]+", " ", n.text_content())
    txt = re.sub(r"\n\s*\n+", "\n", txt).strip()
    parts.append(txt)
raw = "<TEI><text><body>" + "\n".join(f"<p>{html.escape(t, quote=False)}</p>" for t in parts) + "</body></text></TEI>"
h.add("la-entretenida-1615.xml", raw, language="Spanish", year=1615, source="Cervantes, La entretenida (Ocho comedias y ocho entremeses, 1615), first-edition text in modern spelling", url=B + "title.html")
rep = h.finish(method="Crawled the 'princeps' (1st edition, modern spelling) HTML pages linked from the scene selector (front matter + 20 scenes), extracted the .text.entretenida div only",
  coverage="All of the Spanish first-edition text (front matter, prologue, dedication, cast, three acts). Not included: ed. O'Neill and unpunctuated duplicates, facsimile, English translation, indices.",
  problems=problems + ["Only the modern-spelling transcription of the 1615 edition is online as text (the facsimile is images), so it stands as the original-spelling text. Check line numbers/speaker tags in raw."])
print(rep["words_total"], len(pages)); print(raw[:800]); print(raw[40000:41000])
