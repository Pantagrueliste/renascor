import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, collections
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("hainhofer-grosses-stammbuch")
url = "https://stammbuch.hab.de/cms/uploads/stammbuch-18.xml"
xml = h.get(url, "files/stammbuch-18.xml")
LANG = {"de": "German", "la": "Latin", "fr": "French", "it": "Italian", "es": "Spanish", "he": "Hebrew", "nl": "Dutch", "en": "English", "grc": "Greek", "el": "Greek"}
nodate = 0
for m in re.finditer(r'<div type="Eintrag" xml:id="([^"]+)"[^>]*>(.*?)(?=<div type="Eintrag"|</body>)', xml, re.S):
    xid, body = m.groups()
    t = re.search(r'<div type="Transkription"[^>]*>(.*?)</div>\s*(?=<div type=|$)', body, re.S)
    if not t: continue
    tr = t.group(1)
    tr = re.sub(r"<note\b.*?</note>", "", tr, flags=re.S)
    tr = re.sub(r"<index\b.*?</index>", "", tr, flags=re.S)
    if not re.sub(r"<[^>]+>", "", tr).strip(): continue
    d = re.search(r'<div type="Datierung">(.*?)</div>', body, re.S)
    y = None
    if d:
        dm = re.search(r'<date\b[^>]*?(?:when-iso|notBefore-iso|notAfter-iso|when|notBefore)="(\d{4})', d.group(1))
        y = int(dm.group(1)) if dm else first_year(re.sub(r"<[^>]+>", "", d.group(1)))
    if not y: nodate += 1
    langs = collections.Counter()
    for lm in re.finditer(r'<foreign xml:lang="(\w+)">(.*?)</foreign>', tr, re.S):
        langs[LANG.get(lm.group(1), lm.group(1))] += len(re.sub(r"<[^>]+>", "", lm.group(2)).split())
    tot = len(re.sub(r"<[^>]+>", "", tr).split())
    lang = langs.most_common(1)[0][0] if langs and langs.most_common(1)[0][1] > tot / 2 else "German"
    raw = '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>' + tr + "</body></text></TEI>"
    h.add(xid + ".xml", raw, language=lang, year=y, source="Hainhofer, Das Große Stammbuch", url="https://stammbuch.hab.de/")
print(h.finish(method="Downloaded the TEI P5 export stammbuch-18.xml from the edition's downloads page; one record per page entry (div type=Eintrag) that has a <div type=Transkription>; raw = that transcription with editorial notes (Anmerkung, Übersetzung, Textfeldbeschreibung) and index terms removed. Year from the entry's Datierung.",
  coverage="96 non-empty transcriptions (97 transcription divs, one empty) out of 268 page records (132 blank pages, others only image descriptions: bindings, illustrations).",
  problems=[f"{nodate} transcribed entries without usable year.", "Catalogue counted 136 non-blank pages; only 96 carry a transcription, the rest are pictorial/empty and were not recorded.", "Language per entry: main language by <foreign> word share, German by default."]))
