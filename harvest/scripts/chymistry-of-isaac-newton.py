import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("chymistry-of-isaac-newton")
rep = h.finish(method="Not harvested. Looked for a bulk route: no XML/TEI download link on the site; GitHub repos IUBLibTech/newton_chymistry and IUBLibTech/newton_lsa checked via the API tree listing: they hold only site code (XProc, XSLT, Solr config, DTDs, fonts, figures), no manuscript TEI; no Zenodo deposit found.",
  coverage="Nothing harvested (0 of 73 manuscripts).",
  problems=["webapp1.dlib.indiana.edu/robots.txt (User-agent: *) disallows /newton/mss (the manuscript text pages) and /newton/search (the browse pager), so crawling the transcriptions is not permitted; stopped there.",
            "The TEI XML is not published (neither on the site nor in the project's GitHub repositories). Permission or a data copy from the project team would be needed."])
print(rep["texts_total"])
