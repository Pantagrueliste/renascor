import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("alciato-memorial-web-edition")
U = "https://web.archive.org/web/20221003174128/http://www.mun.ca/alciato/ltext.html"
s = h.get(U, "files/ltext.html")
i = s.find("<body")
s = s[i:]
s = re.sub(r"<script.*?</script>|<!--.*?-->", "", s, flags=re.S)
s = re.sub(r"<br\s*/?>|</p>|<p>", "\n", s, flags=re.I)
s = re.sub(r"<[^>]+>", "", s)
s = html.unescape(s).replace("\xa0", " ")
lines = [l.strip() for l in s.split("\n")]
# drop the intro up to the preface heading
start = next(k for k, l in enumerate(lines) if l.startswith("Andreae Alciati in librum"))
lines = lines[start:]
blocks, cur, name = [], [], None
for l in lines:
    m = re.match(r"^Emblema ([IVXLC]+)\s*$", l)
    if m or l.startswith("Andreae Alciati in librum"):
        if name: blocks.append((name, cur))
        name, cur = (m.group(1) if m else "praefatio"), ([] if m else [l])
        continue
    if l: cur.append(l)
if name: blocks.append((name, cur))
probs = []
seen = {}
for name, ls in blocks:
    seen[name] = seen.get(name, 0) + 1
    if seen[name] > 1:
        probs.append(f"heading Emblema {name} occurs {seen[name]} times in the source; later one suffixed")
        name = f"{name}-{seen[name]}"
    txt = "\n".join(ls)
    txt = re.sub(r"\s*\n\s*", "\n", txt).strip()
    h.add(f"alciato-{name}.txt", txt, language="Latin", year=1621, source="Alciato's Book of Emblems: Memorial Web Edition (Latin text of the 1621 edition)", url=U)
n_emb = len([b for b in blocks if b[0] != "praefatio"])
if n_emb != 212: probs.append(f"{n_emb} emblems found (expected 212)")
probs.append("Wayback copy of 3 Oct 2022; year=1621 is the edition the Latin text is taken from (emblems first printed from 1531). Includes mottos and titles; English text and commentaries not used. Preface counted as one extra text.")
rep = h.finish(method="Archived ltext.html (complete Latin text) split at 'Emblema N' headings", coverage=f"all: preface + {n_emb} emblems from the complete Latin text file", problems=probs)
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")})
