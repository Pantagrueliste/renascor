import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html, time
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest
h = Harvest("apw-acta-pacis-westphalicae")
B = "https://apw.digitale-sammlungen.de"
home = h.get(B + "/search/query.html?start=0&rows=10", "files/list/home.html")
vols = []
for m in re.findall(r'query\.html\?titleAPW_str=([^"&]*)', home):
    v = html.unescape(m).replace("+", " ")
    if v not in vols: vols.append(v)
print(len(vols), vols)
import urllib.parse
out = {}
for v in vols:
    recs = []
    start = 0
    total = None
    while total is None or start < total:
        url = f"{B}/search/query.html?" + urllib.parse.urlencode({"titleAPW_str": v, "start": start, "rows": 100})
        rel = f"files/list/{re.sub(r'[^A-Za-z0-9]+','_',v)}_{start}.html"
        for attempt in range(12):
            try:
                s = h.get(url, rel); break
            except Exception as e:
                print("retry", v, start, e, file=sys.stderr); time.sleep(20)
        else:
            raise SystemExit("failed " + v)
        if total is None:
            total = int(re.search(r"ergab (\d+) Dokument", s).group(1))
        for li in re.finditer(r'<li id="record\.([^"]+)" class="record".*?</li>', s, re.S):
            blk = li.group(1), li.group(0)
            txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", li.group(0))))
            recs.append({"id": li.group(1), "txt": txt[:300]})
        start += 100
    out[v] = {"total": total, "recs": recs}
    print(v, total, len(recs))
json.dump(out, open(HD + "/tmp/apw_list.json", "w"), ensure_ascii=False)
