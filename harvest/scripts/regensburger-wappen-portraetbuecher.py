import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("regensburger-wappen-portraetbuecher")
url = "https://gams.uni-graz.at/o:rpb-06-text/TEI_SOURCE"
xml = h.get(url, "files/rpb-06-text.xml")
tx = xml[xml.find("<text"):]
tx = re.sub(r"<ab>\s*<ref\b.*?</ab>", "", tx, count=1, flags=re.S)
cut = tx.find('<div2 corresp="info:fedora/o:rpb-06-087r_s"')
assert cut > 0
head, tail = tx[:cut], tx[cut:]
# close/open divisions around the cut so each part is well-formed enough for the counter
raw1 = '<TEI xmlns="http://www.tei-c.org/ns/1.0">' + head + "</div1></body></text></TEI>"
raw2 = '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div1 type="text">' + tail
h.add("rpb-06-text_part1_to-1700.xml", raw1, language="German", year=1649, source="Regensburger Wappen- und Porträtbuch Band 06 (Vormundamt)", url=url)
h.add("rpb-06-text_part2_from-1701.xml", raw2, language="German", year=1701, source="Regensburger Wappen- und Porträtbuch Band 06 (Vormundamt)", url=url)
print(h.finish(method="Fetched the TEI source of o:rpb-06-text; split the single text at folio 087r into the part up to the folio dated 1700 (preface of 1649, decree of 1537, list of officials 1537-1700) and the later continuation (1701-1787), following the catalogue's in-period rule (folios whose first year is 1700 or earlier).",
  coverage="The whole edited text of Band 06; the other eleven volumes have only page images (no text).",
  problems=["The volume is one text; it was split in two records only so that the post-1700 continuation is counted out. Year of part 1 set to 1649 (date of the preface); the list entries within it start 1537."]))
