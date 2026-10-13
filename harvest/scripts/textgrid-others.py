import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,collections
sys.path.insert(0,HARVEST_DIR + "")
from hlib import Harvest
H=Harvest("textgrid-repository",delay=0.6)
PS="TGPR-13b65bd8-2b52-4c43-175b-68dcf7a01c06 TGPR-d862e14d-4df7-052b-00fe-661cb242231c TGPR-45581d1b-1326-48e5-e607-69d5da02b3f3 TGPR-99d098e9-b60f-98fd-cda3-6448e07e619d TGPR-3962a083-ef64-06c1-bd38-628cac289f7e TGPR-2ba9cb1b-9602-202d-71ce-67e63a29de55 TGPR-e4123902-183d-2f76-9b8f-2abbc96391d9 TGPR-adf9b705-1533-b0ef-491b-674878350ecb TGPR-4b8bf6c0-e82e-285f-9f69-66bee06b5e2f".split()
for P in PS:
    start=0; cnt=collections.Counter(); name=None; auth=collections.Counter()
    while True:
        x=H.get(f"https://textgridlab.org/1.0/tgsearch-public/search?q=*&limit=5000&start={start}&filter=project.id:{P}&filter=format:text/tg.work%2Bxml",f"lists/other/{P}_{start}.xml")
        rs=re.findall(r"<tgs:result.*?</tgs:result>",x,re.S)
        for r in rs:
            if not name: name=re.search(r'<project id="[^"]*">([^<]*)<',r).group(1)
            d=re.search(r"<dateOfCreation([^>]*)>([^<]*)<",r)
            ys=[int(y) for y in re.findall(r'(?:notBefore|notAfter|when)="(-?\d{4})',d.group(1))] if d else []
            if not ys: cnt["undated"]+=1; continue
            lo,hi=min(ys),max(ys)
            if lo>=1450 and hi<=1700:
                cnt["in"]+=1; a=re.search(r'<agent role="author"[^>]*>([^<]*)<',r); auth[a.group(1) if a else "?"]+=1
            elif lo>1700 or hi<1450: cnt["out"]+=1
            else: cnt["straddle"]+=1
        if len(rs)<5000: break
        start+=5000
    print(P,name,dict(cnt),auth.most_common(4),flush=True)
