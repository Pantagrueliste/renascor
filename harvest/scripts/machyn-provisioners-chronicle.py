import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("machyn-provisioners-chronicle")
problems = ["Live site (quod.lib.umich.edu) is behind a Cloudflare bot challenge for scripts; not attempted. Text read from Internet Archive captures of the fulltext pages (2025 captures) instead."]
cdx = h.get("http://web.archive.org/cdx/search/cdx?url=quod.lib.umich.edu/m/machyn/5076866.0001.001&matchType=prefix&output=txt&fl=original,statuscode,timestamp&filter=statuscode:200&limit=20000", "files/cdx.txt")
cap = {}
for l in cdx.splitlines():
    u, st, ts = l.split()
    m = re.search(r"/1:8\.(\d+)/--london-provisioners-chronicle-1550-1563\?rgn=div2;view=fulltext$", u)
    if m:
        k = int(m.group(1))
        if ts > cap.get(k, ("", ""))[0]: cap[k] = (ts, u)
parts = []; ndiv = 0; missing = []
for k in range(1, 20):
    if k not in cap:
        if k <= 14: missing.append(k)
        continue
    ts, u = cap[k]
    pg = h.get(f"http://web.archive.org/web/{ts}id_/{u}", f"files/section_8.{k}.html")
    for dv in re.findall(r'<div class="textindentlevelx" id="D\d+">(.*?)\n</div>', pg, re.S):
        hd = re.search(r"<h4>(\d{4}-\d\d-\d\d)", dv)
        ps = re.findall(r"<p(?: [^>]*)?>(.*?)</p>", dv, re.S)
        if not ps: continue
        p = ps[0]   # first paragraph = diplomatic transcription; second = modern English rendering
        p = re.sub(r'<span class="add" title="EM[^"]*">.*?</span>', "", p, flags=re.S)  # editorial note
        p = re.sub(r"<br\s*/?>", "\n", p)
        p = html.unescape(re.sub(r"<[^>]+>", "", p))
        p = re.sub(r"[ \t]+", " ", p); p = re.sub(r"\s*\n\s*", "\n", p).strip()
        if p:
            parts.append((hd.group(1) if hd else "") + "\n" + p); ndiv += 1
if missing: problems.append(f"sections 8.{missing} have no usable capture; their entries are missing")
txt = "\n\n".join(parts)
h.add("machyn-diary-1550-1563.txt", txt, language="English", year=1550, source="A London Provisioner's Chronicle, 1550-1563, by Henry Machyn (diplomatic transcription)", url="https://quod.lib.umich.edu/m/machyn/")
problems.append("One record for the whole diary; year = 1550 (start of the diary, entries run 1550-1563).")
print(h.finish(method="CDX listing of Internet Archive captures -> latest capture of each year section (1:8.1-1:8.14, rgn=div2;view=fulltext); from each dated entry only the first paragraph (diplomatic transcription) kept, modern rendering and editorial notes dropped.",
 coverage=f"{ndiv} dated entries from {len(cap)} year sections of the diary (1550-1563); sections missing: {missing or 'none'}.", problems=problems))
