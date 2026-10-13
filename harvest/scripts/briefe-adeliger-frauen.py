import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
h = Harvest("briefe-adeliger-frauen")
B = "https://frauenbriefe.univie.ac.at/"
def fetch(p): return h.get(B + p, f"files/{p}", binary=True).decode("latin-1")
lst = fetch("briefliste2.htm")
pages = sorted({x.split("#")[0] for x in re.findall(r'href="([^"]+)"', lst)} - {"institut1.htm"})
SPLIT = re.compile(r"(?:Einzelbrief|Brief)\s*:(?:&nbsp;|\s)*(\d+[a-z]?)")
def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s); s = re.sub(r"</p>|<p>", "\n", s, flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s); return re.sub(r"\n\s*\n+", "\n", s).strip()
problems = []; n_no_text = 0; n_nodate = 0
for p in pages:
    t = fetch(p)
    body = re.sub(r"Brief (\d+):", r"Brief:\1", t[t.find("<body"):])
    pieces = SPLIT.split(body)  # [pre, num, text, num, text...]
    for k in range(1, len(pieces), 2):
        num, sec = pieces[k], pieces[k + 1]
        sec = re.split(r"<hr WIDTH=\"100%\">\s*<br><b>(?:Einzelbrief|Brief)", sec)[0]
        if p.startswith("blueml"):
            # transcription-only pages: whole section minus the editorial header up to the first blank line
            txt = clean(sec)
            if p == "blueml3.htm":
                txt = txt.split("\n", 4)  # header lines (regest) precede the text
                txt = "\n".join(txt[4:]) if len(txt) > 4 else ""
            head = clean(sec)[:300]
        else:
            its = re.findall(r"<i>(.*?)</i>", sec, re.S | re.I)
            txt = "\n".join(clean(i) for i in its)
            head = clean(sec)[:300]
        m = re.search(r"\b\d{1,2}\.\s?\d{1,2}\.\s?(1[4-7]\d\d)\b", head) 
        y = int(m.group(1)) if m else first_year(head)
        if len(txt.split()) < 5:
            n_no_text += 1; continue
        if y is None: n_nodate += 1
        h.add(f"{p[:-4]}_{k//2+1:03d}_n{num}.txt", txt, language="German", year=y, source="Briefe adeliger Frauen (16.-18. Jh.)", url=B + p, title=head[:120].replace("\n", " "))
if n_no_text: problems.append(f"{n_no_text} letter entries have only a modern summary (no transcription or quoted original) and were skipped")
if n_nodate: problems.append(f"{n_nodate} letters without a parsable year (year=None, not in window)")
problems.append("Letters with a transcription are kept as the transcribed (italic) original text; where only quoted fragments exist (italic quotations inside a regest) only those fragments are kept. Some letters (e.g. Judith Sabina von Starhemberg, Helena von Schallenberg) appear both in the regest pages and in the Bluemelhuber transcription pages (blueml1/3) and may be partly duplicated.")
print(h.finish(method="Letter list page briefliste2.htm -> 17 letter pages; split at 'Einzelbrief:N'; italic text (transcription/quotations) kept, modern regests/headers dropped; blueml pages are transcription-only.",
  coverage=f"{len(h.records)} letters with period text from 17 pages; letter inventories beyond these pages (c. 2,900 letters listed) are not transcribed on the site.", problems=problems))
