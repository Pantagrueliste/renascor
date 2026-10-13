import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html, subprocess, time
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("van-der-goes-ystroom")
base = "https://deystroom.huygens.knaw.nl/edition/data/"
def cget(rel_url):
    p = h.dir / "files" / rel_url
    if p.exists(): return p.read_text(encoding="utf-8")
    time.sleep(1.0)
    out = subprocess.run(["curl", "-sfL", "--max-time", "60", base + rel_url], capture_output=True, check=True).stdout.decode("utf-8")
    p.write_text(out, encoding="utf-8"); return out
cfg = json.loads(cget("config.json"))
parts = []
for e in cfg["entries"]:
    d = json.loads(cget(e["datafile"]))
    md = {m["field"]: m["value"] for m in d["metadata"]}
    t = d["paralleltexts"].get("Diplomatic", {}).get("text", "")
    t = re.sub(r"<sup\b.*?</sup>", "", t, flags=re.S)  # note markers
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ").strip()
    parts.append((int(md.get("Volgorde") or 0), e["datafile"], t))
parts.sort()
raw = "\n\n".join(t for _, _, t in parts if t)
h.add("ystroom-1671-diplomatic.txt", raw, language="Dutch", year=1671, source="De Ystroom (Antonides van der Goes, Amsterdam 1671)", url="https://deystroom.huygens.knaw.nl/")
print(h.finish(method="Read config.json (177 entries) and each entry's JSON file via curl (Python's TLS stack is rejected by the server); concatenated the 'Diplomatic' layer in 'Volgorde' order, stripped annotation markers and footnote numbers; modern Dutch translation and editors' notes excluded.",
  coverage="All 177 entries (preliminaries and the poem), as one record for the one 1671 edition.", problems=["Entries sorted by the Volgorde metadata field; entries with empty diplomatic layer skipped."]))
