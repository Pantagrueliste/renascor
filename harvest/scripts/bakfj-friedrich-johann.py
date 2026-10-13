import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest, first_year
h = Harvest("bakfj-friedrich-johann")
B = "https://bakfj.saw-leipzig.de"
problems = []
LANG = {"deutsch": "German", "lateinisch": "Latin", "französisch": "French", "niederdeutsch": "Low German", "italienisch": "Italian", "tschechisch": "Czech"}
import subprocess, time, os
def fetch_print(n):
    """/print/<n> redirects to /doc/./<id>; requests normalises that to a 404, so use curl (-L) with the same delay."""
    rel = h.dir / f"files/doc/{n}.html"
    if rel.exists(): return rel.read_text(encoding="utf-8")
    wait = h.delay - (time.time() - h._last)
    if wait > 0: time.sleep(wait)
    r = subprocess.run(["curl", "-sL", "-m", "60", "-A", "Renascor-harvest/0.1 (+https://pantagrueliste.github.io/renascor/)", "-w", "\n%{http_code}", f"{B}/print/{n}"], capture_output=True)
    h._last = time.time()
    body, _, code = r.stdout.rpartition(b"\n")
    if code.strip() != b"200": raise RuntimeError(f"HTTP {code.decode()}")
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_bytes(body)
    return body.decode("utf-8", errors="replace")
# 1. listing (cookie session kept by requests session)
items = {}
npages = 170
for p in range(1, npages + 1):
    s = h.get(f"{B}/doc/search?page={p}", f"files/list/{p}.html")
    for m in re.finditer(r'<a href="/browse/\d+/[0-9a-f]+" class="list-group-item">(.*?)</a>', s, re.S):
        blk = m.group(1)
        no = re.search(r'No\. (\d+)', blk)
        if not no: continue
        done = "Editing completed" in blk
        items[int(no.group(1))] = done
print(len(items), sum(items.values()), file=sys.stderr)
todo = sorted(n for n, d in items.items() if d)
# spot-check sample of non-completed docs
nc = sorted(n for n, d in items.items() if not d)
sample = nc[::max(1, len(nc) // 12)]
nsum_only = 0
sample_with_text = []
for n in todo + sample:
    try:
        s = fetch_print(n)
    except Exception as e:
        problems.append(f"print/{n}: {e}"); continue
    i = s.find('<div id="text">')
    if i < 0:
        problems.append(f"print/{n}: no text div"); continue
    j = s.find('id="letter-extension"', i)
    t = s[i + len('<div id="text">'): j if j > 0 else None]
    t = t.rsplit("</div>", 2)[0] if "</div>" in t else t
    k = t.find("<br><br>")
    if k < 0:
        nsum_only += 1; continue
    if n in sample: sample_with_text.append(n)
    src = t[k + 8:]
    src = re.sub(r"<br\s*/?>", "\n", src)
    src = re.sub(r"<[^>]+>", "", src)
    src = html.unescape(src)
    src = re.sub(r"[ \t\xa0]+", " ", src)
    src = re.sub(r"\n\s*\n+", "\n", src).strip()
    md = re.search(r'<div id="metadata">\s*(.*?)\s*(?:<div id="collapse|$)', s, re.S)
    meta = re.sub(r"<[^>]+>", "", md.group(1)) if md else ""
    meta = html.unescape(meta)
    year = first_year(meta)
    lang = "German"
    for k2, v in LANG.items():
        if re.search(r"·\s*" + k2, meta): lang = v
    if year is None: problems.append(f"Nr {n}: no year in '{meta[:60]}'")
    if len(src.split()) < 5: continue
    raw = "<TEI><text><body><p>" + html.escape(src, quote=False) + "</p></body></text></TEI>"
    h.add(f"{n}.xml", raw, language=lang, year=year, source=f"BAKFJ Nr. {n}", url=f"{B}/print/{n}")
rep = h.finish(method="Listing pages /doc/search?page=1..170 (session cookie) to get all 3385 document numbers and the 'Editing completed' flag; then /print/<Nr> for each completed document; kept the part of #text after the German summary (the edited source text), dropped the Regest, metadata, indices and apparatus tabs",
  coverage=f"Fetched all {len(todo)} documents flagged 'Editing completed'; {nsum_only} of them (plus sample) show only the summary and are not staged. Not fetched: {len(nc)} metadata-only documents (a sample of {len(sample)} was checked; {len(sample_with_text)} of the sample had source text). 'Kabinettstuecke' pages not included.",
  problems=problems[:30])
print(json.dumps({k: rep[k] for k in ("texts_total","words_total","texts_in_window","words_in_window","undated")}), sample_with_text)
