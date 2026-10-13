"""Rostocker Urgichten 1543-1587 (opendata.uni-halle.de, collection 1981185920/13873).

The repository's file downloads sit behind a bot check, so the 50 TEI files were fetched once in a
browser (files/manual/download_in_browser.js, file list from the open OAI-PMH interface) and saved as
files/manual/rostocker-urgichten.json ({url: TEI}). This script stages them from that file.
"""
import json
import re
import sys
import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest  # noqa: E402

h = Harvest("rostocker-urgichten")
files = json.loads((h.dir / "files/manual/rostocker-urgichten.json").read_text(encoding="utf-8"))
for url, tei in sorted(files.items()):
    name = url.rsplit("/", 1)[-1]
    m = re.match(r"\d+_(\d{4})_", name)
    h.add(name, tei, language="German", year=int(m.group(1)) if m else None,
          source="Rostocker Urgichten 1543-1587", url=url)
rep = h.finish(method="50 TEI files listed by OAI-PMH (ORE records of collection 1981185920/13873), "
                      "downloaded once in a browser because file downloads sit behind a bot check; year from the file name",
               coverage="All 50 transcribed Urgichten (one of the 51 items has no TEI file).",
               problems=["Editorial notes inside <note> are dropped by the counter."])
print(json.dumps({k: rep[k] for k in ("texts_in_window", "words_in_window", "texts_total")}))
