import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import re, subprocess

B = "https://henslowe-alleyn.org.uk"
h = Harvest("henslowe-alleyn-digitisation-project", delay=10)   # robots.txt crawl-delay: 10
problems = []

# (page slug, label, year of the source text, pdf path)
ITEMS = {
    "mss-1-article-9": ("MSS 1 Article 9: letter from Edward Alleyn to his wife Joan, 2 May 1593", 1593),
    "mss-1-article-11": ("MSS 1 Article 11", None),
    "mss-2-article-5": ("MSS 2 Article 5: draft royal patent for the Mastership of the Game, 24 Nov 1604", 1604),
    "mss-19": ("MSS 19: Platt of The Second Part of the Seven Deadly Sins", 1590),
    "mss1-article-16": ("Muniment 16: Deed of Partnership in the Rose Playhouse, 10 Jan 1587", 1587),
    "mss1-article-22": ("Muniment 22: Contract for the Fortune Playhouse, 1600", 1600),
    "muniments-series-3-group-584": ("Muniment 584: Foundation Deed of God's Gift College, 1619", 1619),
}
YEARS_FILE = _os.path.join(HARVEST_DIR, "scripts", "_hen_years.txt")  # not used; years are in ITEMS


def pdf_text(pdf_bytes_path):
    return subprocess.run(["pdftotext", "-layout", pdf_bytes_path, "-"], capture_output=True, text=True).stdout


def fetch_pdf(path, rel):
    h.get(B + path, rel, binary=True)
    return str(h.dir / rel)


for slug_, (label, year) in ITEMS.items():
    try:
        page = h.get(f"{B}/transcriptions/{slug_}/", f"files/page_{slug_}.html")
        pdfs = re.findall(r'href="(/documents/[^"]+\.pdf)"', page)
        if not pdfs:
            problems.append(f"{slug_}: no PDF link"); continue
        p = fetch_pdf(pdfs[0], f"files/{slug(slug_)}.pdf")
        txt = pdf_text(p)
        y = year if year else first_year(txt[:3000])
        h.add(f"{slug_}.txt", txt, language="English", year=y, source="Henslowe-Alleyn: " + label, url=B + pdfs[0])
    except Exception as e:
        problems.append(f"{slug_}: {e}")

# MSS 9: Alleyn's diary and account book: one transcript PDF per page, listed on the catalogue page
cat = h.get(f"{B}/catalogue/mss-9/", "files/cat_catalogue_mss-9.html")
pdfs = list(dict.fromkeys(re.findall(r'href="(/documents/[^"]+\.pdf)"', cat)))
parts = []
for i, pth in enumerate(pdfs):
    try:
        p = fetch_pdf(pth, f"files/mss9/{i:03d}_{slug(pth.split('/')[-1])}")
        parts.append(f"[{pth.split('/')[-1]}]\n" + pdf_text(p))
    except Exception as e:
        problems.append(f"mss9 {pth}: {e}")
if parts:
    h.add("mss-9-alleyn-diary.txt", "\n\n".join(parts), language="English", year=1617,
          source="Henslowe-Alleyn: MSS 9, Diary and Account Book of Edward Alleyn (page transcripts, Grace Ioppolo)", url=B + "/catalogue/mss-9/")
n_in_catalogue = len(pdfs)

rep = h.finish(
    method="Read /transcriptions/ and each transcription page (10 s crawl-delay observed); downloaded the transcript PDFs and extracted the text layer with pdftotext -layout. Alleyn's diary (MSS 9) has one PDF per page image, linked from the catalogue listing; its pages were concatenated into one record. Introduction and glossary PDFs by Ioppolo (modern) and the site essays were excluded.",
    coverage=f"All 7 individually transcribed documents plus the {n_in_catalogue} page transcripts of MSS 9 (Alleyn's diary). Everything else in the catalogue (including Henslowe's own diary, MSS 7) is images only, with no transcription on the site.",
    problems=problems + [
        "Henslowe's Diary (MSS 7) is NOT transcribed on the site, despite the catalogue note; only Alleyn's diary (MSS 9) has page transcripts.",
        "PDF text is editorial transcription with possible modern editorial apparatus (square brackets, folio markers, headers) that could not be fully separated.",
        "The editorial footnotes of the Ioppolo transcripts are mixed into the PDF text layer and could not be separated. The Platt (MSS 19) is dated c. 1590 (the catalogue dates the paper 1612-1626).",
        "Diary year is set to 1617 (start of Alleyn's diary, 1617-1622); individual year given where documents are dated.",
    ])
print(rep)
