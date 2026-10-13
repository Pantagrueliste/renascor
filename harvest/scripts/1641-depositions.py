import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("1641-depositions")
rep = h.finish(method="Checked https://1641.tcd.ie/ (home page, robots.txt, sitemap.xml) and searched for a bulk deposit (GitHub/Zenodo/Dataverse/OAI): none found.",
  coverage="Nothing harvested (0 of 6,932 depositions).",
  problems=["The site answers every request, including the home page, robots.txt and sitemap.xml, with a Google reCAPTCHA challenge page; per the harvest rules no attempt was made to get past it.","No public bulk download (TEI/XML, SQL, PDF) or repository deposit located.","A TCD/library contact would be needed for the TEI files."])
print(rep)
