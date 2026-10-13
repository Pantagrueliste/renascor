import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
H = HARVEST_DIR + ""
sys.path.insert(0, H)
from hlib import Harvest
from tinc_parse import resolve
B = "http://earlymusictheory.org/Tinctoris/texts/"
h = Harvest("tinctoris-theoretical-works")
dirs = ["denotisetpausis", "deregularivalorenotarum", "deimperfectionenotarum", "dealterationenotarum", "depunctis",
        "deartecontrapuncti", "dearte23", "proportionale1", "proportionale23", "complexus", "deinventioneetusumusice"]
probs = []
for d in dirs:
    js = h.get(f"{B}{d}/combined.js", f"files/{d}_combined.js")
    m = re.search(r"texts\.\w+\.edited = '(.*?)';\s*\n(?=texts\.)", js, re.S)
    if not m:
        probs.append(f"no edited text in {d}"); continue
    raw = m.group(1).replace("\\\n", "\n").replace("\\n\\\n", "\n").replace("\\'", "'").replace("\\n", "\n")
    k = raw.find("<treatise>")
    body = raw[k:] if k >= 0 else raw
    t = resolve(body)
    t = re.sub(r"<example.*?</example>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\*\*.*?\*\*", " ", t, flags=re.S)  # editorial footnotes (**...**)
    t = t.replace("_", "").replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    h.add(f"{d}.txt", t, language="Latin", year=None, dateless_in_window=True, source="Tinctoris Complete Theoretical Works (Early Music Theory)", url=f"{B}{d}/")
probs.append("Year left None with dateless_in_window=True: site dates everything to the 1470s-1480s (not per treatise).")
probs.append("Text is the critical edited text (Latin, manuscript spellings, MS punctuation) rebuilt from the site's combined.js: apparatus {var=...} resolved to the first (base) reading, music examples/labels, tags and **editorial footnotes** removed. Per-manuscript diplomatic transcriptions (V, BU, Br1, G) and the English translation in the same files are NOT used.")
probs.append("Expositio manus, De natura et proprietate tonorum, Diffinitorium musice are placeholders on the site (not online).")
rep = h.finish(method="Per-treatise combined.js (text embedded in script) fetched; edited text extracted and apparatus resolved with the site's own parser rules",
               coverage=f"{len(h.records)} of 11 online treatise pages (all edited texts online)", problems=probs)
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")})
