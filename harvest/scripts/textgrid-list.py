import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0,HARVEST_DIR + "")
from hlib import Harvest
P="TGPR-372fe6dc-57f2-6cd4-01b5-2c4bbefcfd3c"
B="https://textgridlab.org/1.0/tgsearch-public/search"
h=Harvest("textgrid-repository")
start=0
while True:
    u=f"{B}?q=*&limit=5000&start={start}&filter=project.id:{P}&filter=format:text/tg.work%2Bxml"
    x=h.get(u,f"lists/works_{start:06d}.xml")
    n=x.count("<tgs:result")
    print(start,n,flush=True)
    if n<5000: break
    start+=5000
