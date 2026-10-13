import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import tarfile, io, re, html
from bs4 import BeautifulSoup

h = Harvest("shakespeare-mit")
problems = []
data = h.get("https://codeload.github.com/TheMITTech/shakespeare/tar.gz/master", "files/shakespeare.tar.gz", binary=True)
tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
files = {}
for m in tf.getmembers():
    if m.isfile():
        files[m.name.split("/", 1)[1]] = tf.extractfile(m).read().decode("latin-1")

PLAYS = {  # dir: (title, approximate composition year as given by Open Source Shakespeare / standard chronology)
 "1henryiv": ("Henry IV, Part 1", 1597), "2henryiv": ("Henry IV, Part 2", 1597), "henryv": ("Henry V", 1599),
 "1henryvi": ("Henry VI, Part 1", 1591), "2henryvi": ("Henry VI, Part 2", 1590), "3henryvi": ("Henry VI, Part 3", 1590),
 "henryviii": ("Henry VIII", 1613), "john": ("King John", 1596), "richardii": ("Richard II", 1595), "richardiii": ("Richard III", 1592),
 "allswell": ("All's Well That Ends Well", 1602), "asyoulikeit": ("As You Like It", 1599), "comedy_errors": ("The Comedy of Errors", 1594),
 "cymbeline": ("Cymbeline", 1610), "lll": ("Love's Labour's Lost", 1595), "measure": ("Measure for Measure", 1604),
 "merry_wives": ("The Merry Wives of Windsor", 1597), "merchant": ("The Merchant of Venice", 1597), "midsummer": ("A Midsummer Night's Dream", 1595),
 "much_ado": ("Much Ado About Nothing", 1598), "pericles": ("Pericles", 1608), "taming_shrew": ("The Taming of the Shrew", 1592),
 "tempest": ("The Tempest", 1611), "troilus_cressida": ("Troilus and Cressida", 1602), "twelfth_night": ("Twelfth Night", 1601),
 "two_gentlemen": ("Two Gentlemen of Verona", 1593), "winters_tale": ("The Winter's Tale", 1610),
 "cleopatra": ("Antony and Cleopatra", 1607), "coriolanus": ("Coriolanus", 1608), "hamlet": ("Hamlet", 1601),
 "julius_caesar": ("Julius Caesar", 1599), "lear": ("King Lear", 1606), "macbeth": ("Macbeth", 1606), "othello": ("Othello", 1604),
 "romeo_juliet": ("Romeo and Juliet", 1595), "timon": ("Timon of Athens", 1607), "titus": ("Titus Andronicus", 1593),
}

def text_of(s):
    return html.unescape(s)

for d, (title, yr) in PLAYS.items():
    key = f"{d}/full.html"
    if key not in files:
        problems.append(f"{d}: full.html missing"); continue
    soup = BeautifulSoup(files[key], "lxml")
    for t in soup.find_all("table"):
        t.decompose()  # navigation tables
    for t in soup(["script", "style", "title"]):
        t.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    body = soup.body.get_text("\n") if soup.body else soup.get_text("\n")
    # drop trailing site footer (links back to the homepage)
    lines = [l.strip() for l in body.splitlines()]
    lines = [l for l in lines if l and not l.lower().startswith(("shakespeare homepage", "next scene", "previous scene")) and l != "<<"]
    raw = "\n".join(lines)
    h.add(f"{d}.txt", raw, language="English", year=yr, source=f"Shakespeare, {title} (MIT Complete Works, Moby text)",
          url=f"https://shakespeare.mit.edu/{d}/full.html")

def strip_html_poem(s):
    soup = BeautifulSoup(s, "lxml")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for t in soup(["title", "script", "style"]):
        t.decompose()
    return "\n".join(l.strip() for l in soup.get_text("\n").splitlines() if l.strip())

# Sonnets, one record per sonnet
sonnets = sorted(k for k in files if re.fullmatch(r"Poetry/sonnet\.[IVXLC]+\.html", k))
roman = lambda r: sum({"I":1,"V":5,"X":10,"L":50,"C":100}[c] * (1 if i == len(r)-1 or {"I":1,"V":5,"X":10,"L":50,"C":100}[c] >= {"I":1,"V":5,"X":10,"L":50,"C":100}[r[i+1]] else -1) for i, c in enumerate(r))
for k in sonnets:
    r = re.search(r"sonnet\.([IVXLC]+)\.html", k).group(1)
    n = roman(r)
    raw = strip_html_poem(files[k])
    h.add(f"sonnet-{n:03d}.txt", raw, language="English", year=1609, source=f"Shakespeare, Sonnet {n} (MIT Complete Works)",
          url=f"https://shakespeare.mit.edu/{k}")
if len(sonnets) != 154:
    problems.append(f"{len(sonnets)} sonnet files found instead of 154")

for f, name, yr, t in [("Poetry/VenusAndAdonis.html", "venus-and-adonis", 1593, "Venus and Adonis"),
                       ("Poetry/RapeOfLucrece.html", "rape-of-lucrece", 1594, "The Rape of Lucrece"),
                       ("Poetry/LoversComplaint.html", "lovers-complaint", 1609, "A Lover's Complaint"),
                       ("Poetry/elegy.html", "funeral-elegy", 1612, "A Funeral Elegy")]:
    s = files[f]
    if name == "funeral-elegy":
        s = re.sub(r"<TITLE>(.*?)</TITLE\s*>", "", s, flags=re.S | re.I)
        s = re.sub(r"<P>W\[illiam\] S\[hakespeare\].*?</P>", "", s, count=1, flags=re.S)  # modern editor's note
        s = re.sub(r"<TD ROWSPAN=\d+ width=\d+%>\d+", "", s)  # line numbers
        s = s.replace("<TR", "<BR><TR")
    raw = strip_html_poem(s)
    h.add(f"{name}.txt", raw, language="English", year=yr, source=f"Shakespeare, {t} (MIT Complete Works)",
          url=f"https://shakespeare.mit.edu/{f}")

various = files.get("Poetry/various", "")
lines = various.splitlines()
def seg(a, b): return "\n".join(l.strip() for l in lines[a:b] if l.strip())
if lines:
    h.add("passionate-pilgrim.txt", seg(0, 283), language="English", year=1599, source="The Passionate Pilgrim (MIT repository file Poetry/various)", url="https://github.com/TheMITTech/shakespeare/blob/master/Poetry/various")
    h.add("sonnets-to-sundry-notes-of-music.txt", seg(283, 550), language="English", year=1599, source="Sonnets to Sundry Notes of Music (MIT repository file Poetry/various)", url="https://github.com/TheMITTech/shakespeare/blob/master/Poetry/various")
    h.add("phoenix-and-turtle.txt", seg(550, len(lines)), language="English", year=1601, source="The Phoenix and the Turtle (MIT repository file Poetry/various)", url="https://github.com/TheMITTech/shakespeare/blob/master/Poetry/various")
    problems.append("Passionate Pilgrim, Sonnets to Sundry Notes of Music and Phoenix and the Turtle come from the plain-text file Poetry/various in the repository, which is not linked from the site's catalogue pages (the site lists only plays, Sonnets, V&A, Lucrece, Lover's Complaint, Funeral Elegy); they can be removed if out of scope.")

problems.append("The site gives no dates. Year = approximate composition date of the plays (standard chronology, +-1-2 years) and first publication date for the poems (Venus 1593, Lucrece 1594, Sonnets and Lover's Complaint 1609, Passionate Pilgrim 1599, Phoenix 1601, Funeral Elegy 1612). Text is the modernised Moby text, accepted.")
problems.append("Sonnets treated as 154 separate texts (one page each); play texts include speaker names, stage directions and scene headings.")
problems.append("Plays are taken from each play's full.html (entire play); individual scene files in the repository are duplicates and not used. The 'Funeral Elegy' attribution to Shakespeare is contested; included as the site lists it.")
rep = h.finish(method="Downloaded the GitHub repository TheMITTech/shakespeare once as a tarball (codeload), parsed the HTML in memory with BeautifulSoup, removed navigation tables and kept scene headings, stage directions, speakers and speeches. One record per play, per sonnet and per poem.",
    coverage="All of the repository's period text: 37 plays, 154 sonnets, Venus and Adonis, Lucrece, Lover's Complaint, Funeral Elegy and the Poetry/various file. Nothing omitted apart from site chrome.",
    problems=problems)
print(rep)
