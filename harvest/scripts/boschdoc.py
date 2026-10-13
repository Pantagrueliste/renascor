import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("boschdoc")
import subprocess, time
def cget(url, rel):
    p = h.dir / rel
    if p.exists(): return p.read_text(encoding="utf-8")
    time.sleep(1.0)
    out = subprocess.run(["curl", "-sfL", "--max-time", "60", url], capture_output=True, check=True).stdout.decode("utf-8")
    p.write_text(out, encoding="utf-8"); return out
h.get = cget
base = "https://boschdoc.huygens.knaw.nl/edition/data/"
cfg = json.loads(h.get(base + "config.json", "files/config.json"))
LAYERS = ["Transcription", "Transcripción", "Transcriptie"]
def clean(t):
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", t).strip()
FR = set("le la les des du est une que qui dans pour avec sur par au aux ses son sa leur et en ne pas".split())
ES = set("el los las del una que por con para su sus como pero muy mas más también es y en se lo".split())
LA = set("et in ad est cum quod non qui ut de sunt per ex sed aut item pro super anno domini".split())
NL = set("die dat ende van den der het een inde mit voer dair dye ghegheven ghegeven sinte jaer so te hem hij zijn sijn by".split())
def lang(txt):
    w = re.findall(r"[a-zA-Zéèáíóúñ]+", txt.lower())
    sc = {n: sum(x in S for x in w) for n, S in (("French", FR), ("Spanish", ES), ("Latin", LA), ("Middle Dutch", NL))}
    return max(sc, key=sc.get) if w and max(sc.values()) else "Middle Dutch"
n_empty = n_nodate = 0
for e in cfg["entries"]:
    fn = e["datafile"]
    d = json.loads(h.get(base + fn, "files/" + fn))
    txt = ""
    for L in LAYERS:
        t = d["paralleltexts"].get(L, {}).get("text", "")
        if clean(t) and not re.match(r"(Unfortunately the transcription|Helaas is van dit document nog geen transcriptie|Lamentablemente|Desgraciadamente)", clean(t)):
            txt = clean(t); break
    if not txt:
        n_empty += 1
        continue
    md = {m["field"]: m["value"] for m in d["metadata"]}
    y = first_year(md.get("Datum")) or first_year(md.get("Boekjaar")) or first_year(md.get("Jaar van publicatie"))
    if not y: n_nodate += 1
    h.add(fn, txt, language=lang(txt), year=y, source="BoschDoc: " + d["name"], url=f"https://boschdoc.huygens.knaw.nl/edition/#/entry/{d['id']}")
print(h.finish(method="Read config.json (939 entries) and each entry's JSON data file; one record per entry = plain text of the Transcription layer (Dutch/Spanish/English-labelled copies are identical; translations, comments and bibliographic notes excluded). Year = metadata Datum, else Boekjaar, else Jaar van publicatie. Language guessed by stopword counts per entry.",
  coverage="All entries with a transcription; entries lacking one are skipped (counted in problems).",
  problems=[f"{n_empty} entries have no transcription and were skipped.", f"{n_nodate} transcribed entries have no usable date (year=None, dateless_in_window=False).", "Language per entry is a heuristic (metadata gives none); Latin/Middle Dutch/French/Spanish confusion possible in short texts. Folio markers kept in text."]))
