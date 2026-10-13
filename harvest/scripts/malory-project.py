import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from bs4 import BeautifulSoup
B = "http://www.maloryproject.com/"
h = Harvest("malory-project")
def clean(html):
    sp = BeautifulSoup(html, "html.parser")
    for x in sp.find_all("script"): x.decompose()
    for sel in ("span.teiHeader", "span.page_break", "span.page_images", "span.winchester_note", "span.caxton_note",
                "span.milestone_title", "span.div_title", "span.ie_reg", "span.ie_deletion", "a.zoom", "#win_full_note", "div.signature"):
        for x in sp.select(sel): x.decompose()
    for x in sp.select("div.winchester_div[number=intro]"): x.decompose()
    for br in sp.find_all("br"): br.replace_with("\n")
    t = sp.get_text("")
    t = t.replace("\xa0", " ").replace("͵", "").replace("ʹ", "")
    t = re.sub(r"//\s*", "", t)   # line-end word breaks
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t).strip()
    return t
probs = []
for key, fn, yr, lab in (("winchester", "win_xml_loader.php", 1470, "Winchester Manuscript (BL Add. MS 59678), Roman War episode fols 71r-96r"),
                         ("caxton", "caxton_xml_loader.php", 1485, "Caxton's Morte Darthur 1485, Book V (sig. h7v-k3r) with Preface/Table/Book XXI parts where transcribed")):
    html = h.get(B + "includes/" + fn, f"files/{fn}.html")
    t = clean(html)
    if key == "winchester":
        m = re.search(r"Explycit the noble tale.*?of Rome", t, re.S)
        if m: t = t[:m.end()]   # drop the palaeography key (scribal sign legend) that follows the text
        else: probs.append("Winchester end marker not found; trailing legend not trimmed")
    h.add(f"{key}.txt", t, language="Middle English", year=yr, source="The Malory Project: " + lab, url=B + "includes/" + fn)
probs.append("Text taken from the full-text loaders used by the site's own 'Full Text' buttons (includes/win_xml_loader.php, caxton_xml_loader.php); regularised readings, deleted text, notes, milestone/div titles and page-break labels dropped; original (orig/sic) readings kept; line-end '//' joins merged; scribal punctuation marks U+0375/U+02B9 removed.")
probs.append("Year of Winchester set to 1470 (MS written c. 1470-83; Malory completed the work 1469-70); Caxton 1485 (printed).")
probs.append("Only the transcribed parts are online (Roman War episode in Winchester; Caxton Book V and some other leaves); the rest of the Morte Darthur is not transcribed. Div/headings given in the page navigation (editorial) are excluded.")
rep = h.finish(method="Site's own full-text endpoints fetched (2 requests); HTML cleaned with BeautifulSoup", coverage="all transcribed text online: 2 witnesses (Winchester Roman War episode; Caxton transcribed parts); not the whole Morte Darthur", problems=probs)
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")})
