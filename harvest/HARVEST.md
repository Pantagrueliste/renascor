# Renascor harvest, October 2026: instructions for harvest agents

Goal: download the period texts of each assigned catalogue resource so that they can be counted and
deduplicated with the same tools as the Renascor Corpus (RQ). You produce staging files; you do NOT
ingest anything into any database.

Paths
- Harvest dir (helpers, scripts): this directory (harvest/ in the Renascor repository)
- Output: $RQ_ROOT/data/raw/renascor_2026-10/<id>/ (created by hlib.Harvest; RQ_ROOT defaults to ../RQ next to this repository)
- Catalogue record of each resource: data/entries/<id>.json (read its notes first: they describe scope, files and counts)

Rules
1. Write one Python script per resource at harvest/scripts/<id>.py, using `from hlib import Harvest, tei_year, first_year, slug`
   (add the harvest dir to sys.path). Run it with python3. Re-runs must be cheap: hlib.get caches files when given `rel`.
2. Read-only everywhere else. Never write inside the Renascor or RQ git trees except under $RQ_ROOT/data/raw/renascor_2026-10/<id>/.
   Never touch any .sqlite file. Do not delete anything outside your own resource directories.
3. Be polite: use Harvest.get (1 s between requests by default; do not lower it below 0.5 s). Prefer bulk downloads
   (repository zip, GitHub tarball, Zenodo files, OAI-PMH, published TEI exports) over page crawling. For GitHub use
   https://codeload.github.com/<owner>/<repo>/tar.gz/<branch> once rather than per-file requests. Cap: 3 GB and about
   20,000 requests per resource; if a resource needs more, stop and report.
4. One record per text (letter, play, document, inscription, diary entry...) as the resource itself divides them.
   `raw` = the source file content (TEI/XML is fine: RQ's counter keeps only the <text>/<body>), or extracted plain text
   for HTML pages (strip navigation, headers, footers, apparatus, editorial introductions, commentary and modern translations).
5. Only period text counts. Exclude modern introductions, commentary, notes, translations and indexes. When the resource
   gives both a diplomatic and a normalised/modernised version of the same text, keep ONE (the diplomatic/original-spelling one).
6. `year` = date of the source text (not of the digital file), from the TEI header (`tei_year`) or the resource's metadata.
   Keep out-of-window texts in staging with their year (they will be counted out). Use year=None with
   dateless_in_window=True only when the resource documents that all its texts fall within 1450-1700;
   otherwise year=None and dateless_in_window=False, and say so in problems.
7. `language` = human-readable language of the text (e.g. "Latin", "Early New High German" -> "German").
   Multilingual texts: the main language.
8. Call h.finish(method=..., coverage=..., problems=[...]) at the end. `coverage` says what share of the resource was
   harvested (all / which part) and why anything is missing. Be honest: a partial harvest with a clear coverage note is fine.
9. If a resource cannot be harvested (offline, login, bot wall, no period text), still create the directory via
   Harvest(id) and call finish with texts=0 and the reason in problems.

Final answer: a compact JSON array, one object per resource:
{"id", "texts_in_window", "words_in_window", "texts_total", "coverage", "problems"}
(the numbers copied from report.json). No other prose.
