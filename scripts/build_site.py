#!/usr/bin/env python3
"""Build the public site from the catalogue entries.

Reads every JSON file in data/entries/, validates it against the schema and writes:

  docs/data.json      {meta, entries, derived}: the entries exactly as stored (file-name
                      order), a parallel array of display-only fields (parsed periods,
                      cleaned notes, link labels...), and the catalogue metadata and figures.
  docs/renascor.csv   the whole catalogue, one row per edition, every field (UTF-8, CRLF).
  docs/renascor.json  the whole catalogue as JSON, every field.
  docs/index.html     the catalogue figures, the numbers of the methodology section and its
                      share chart are written into the page (data-stat, data-href and data-if
                      attributes, and the build: regions), so they are right without JavaScript.

The entries are never modified. A second build of the same commit changes nothing.

Usage:
    python scripts/build_site.py [--entries-dir DIR] [--out-dir DIR] [--index FILE]

With an --out-dir other than docs/, the page template (--index, default docs/index.html)
and docs/app.js are copied into that directory first, so a scratch build never touches docs/.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import statistics
import subprocess
import sys
import unicodedata
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "entry.schema.json"
COUNTRIES_PATH = REPO_ROOT / "schema" / "countries.json"
CITATION_PATH = REPO_ROOT / "CITATION.cff"
DOCS_DIR = REPO_ROOT / "docs"
REPO_URL = "https://github.com/Pantagrueliste/renascor"

SITE_TITLE = "Renascor"
SITE_DESCRIPTION = "An open catalogue of digital editions of Renaissance-era written documents"

SCOPE = (1450, 1700)
SNAPSHOTS = {"v2026.06": {"frozen": "2026-06-26"}}      # add a line for each new RQ snapshot
SNAPSHOT_NAME = "Renascor Corpus"
SNAPSHOT_SCOPE = "in-core harvested subsets, including retained duplicates"
PSEUDO_LANGUAGES = {"Multilingual", "Romance (other)"}
ENCODING_ORDER = ["tei", "xml", "json", "html", "wikitext", "plain-text", "markdown", "other"]
STATUS_ORDER = ["active", "archived", "discontinued"]
SIZE_BANDS = [(10_000_000, "10m-plus"), (1_000_000, "1m-10m"), (100_000, "100k-1m"),
              (10_000, "10k-100k"), (0, "under-10k")]
PREFERRED_FIELDS = ["title", "url", "doi", "data_url", "data_format", "data_formats", "api_url", "institution", "languages", "period",
                    "words", "texts", "corpus_statistics", "count_basis", "resource_statistics", "encoding", "license",
                    "license_url", "license_note", "status", "region", "countries", "years_active",
                    "author", "date", "last_modified", "provenance", "date_added", "notes"]
# Section ids of the page: an entry file may not take one of these names (its permalink #id
# would point at the section instead of the record).
RESERVED_IDS = {"main", "catalogue", "results", "search", "q", "filters", "facets", "about", "method",
                "figures", "languages", "definitions", "download", "cite", "contribute", "top",
                "timeline"}
ID_RE = re.compile(r"^[a-z0-9-]+$")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
DECADE_STARTS = list(range(SCOPE[0], SCOPE[1], 10))      # 1450 ... 1690 (the last bin ends in 1700)


class BuildError(Exception):
    """A guard failed: the message says what to fix."""


# --- Loading and validation ---------------------------------------------------------------

def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_entries(entries_dir: Path) -> list[tuple[str, dict]]:
    """Load entries. Returns a list of (filename, entry) tuples, sorted by file name."""
    entries = []
    for path in sorted(entries_dir.glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            entries.append((path.name, entry))
        except json.JSONDecodeError as e:
            print(f"Warning: {path.name} is not valid JSON: {e}", file=sys.stderr)
    return entries


def validate_entries(entries: list[tuple[str, dict]], schema: dict) -> list[str]:
    """Validate entries against the schema. Returns a list of error messages."""
    try:
        import jsonschema
    except ImportError:
        print("Warning: jsonschema not installed; skipping validation", file=sys.stderr)
        return []

    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for filename, entry in entries:
        for error in validator.iter_errors(entry):
            path = "/".join(str(p) for p in error.absolute_path) or "(root)"
            errors.append(f"{filename}: {path}: {error.message}")
    return errors


def entry_id(filename: str) -> str:
    return filename[:-5] if filename.endswith(".json") else filename


def check_entries(entries: list[tuple[str, dict]]) -> None:
    """Guards on file names and links (section 9.2). Raises BuildError."""
    problems = []
    for filename, entry in entries:
        eid = entry_id(filename)
        if not ID_RE.match(eid):
            problems.append(f"{filename}: the file name may use only a-z, 0-9 and hyphens")
        elif eid in RESERVED_IDS:
            problems.append(f"{filename}: '{eid}' is a section id of the page; rename the file")
        for key in ("url", "data_url"):
            if "rq-open-corpus" in str(entry.get(key) or "").lower():
                problems.append(f"{filename}: {key} points to the RQ Open Corpus repository, "
                                "which the catalogue does not link to")
    if problems:
        raise BuildError("\n".join(problems))


# --- Periods ------------------------------------------------------------------------------

DASH = r"\s*[-–—]\s*"
APPROX = r"(?:(?P<approx>c\.|ca\.|circa)\s*)?"
ORD = r"(?:st|nd|rd|th)"
P_RANGE = re.compile(rf"^{APPROX}(?P<a>\d{{3,4}}){DASH}(?P<b>\d{{3,4}})$", re.I)
P_YEAR = re.compile(rf"^{APPROX}(?P<a>\d{{3,4}})$", re.I)
P_CENT = re.compile(rf"^(?P<a>\d{{1,2}}){ORD}(?:{DASH}(?P<b>\d{{1,2}}){ORD})?\s+centur(?:y|ies)$", re.I)
P_NOTE = re.compile(r"^(?P<main>.*?)\s*\((?P<note>[^()]*)\)\s*$")


def en_dash_years(s: str) -> str:
    """'1450-1700' -> '1450–1700' inside any text (digits on both sides only)."""
    return re.sub(r"(?<=\d)\s*-\s*(?=\d)", "–", s)


def parse_period(value):
    """Parse a period as recorded. None when there is no period.

    kind: 'range' | 'year' | 'century' | 'text' (given in words: no years, not matched by
    the period filter). A trailing parenthetical comment is not part of the label.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    raw = " ".join(value.split())
    main, note = raw, None
    m = P_NOTE.match(raw)
    if m and m.group("main"):
        main, note = m.group("main").strip(), m.group("note").strip()
    approx, kind, start, end = False, "text", None, None
    m = P_RANGE.match(main) or P_YEAR.match(main)
    if m:
        start = int(m.group("a"))
        end = int(m.group("b")) if m.groupdict().get("b") else start
        if start > end:
            start, end = end, start
        approx = bool(m.group("approx"))
        kind = "year" if start == end else "range"
        label = ("c. " if approx else "") + (str(start) if start == end else f"{start}–{end}")
    else:
        m = P_CENT.match(main)
        if m:
            first, last = int(m.group("a")), int(m.group("b") or m.group("a"))
            start, end, approx, kind = (first - 1) * 100, last * 100 - 1, True, "century"
            label = en_dash_years(re.sub(DASH, "–", main))
        else:
            label, note = en_dash_years(raw), None
    return {"raw": value, "label": label, "start": start, "end": end, "approx": approx,
            "kind": kind, "note": note,
            "beyond_scope": start is not None and (start < SCOPE[0] or end > SCOPE[1])}


# --- Notes --------------------------------------------------------------------------------

RQ_SENTENCE = re.compile(r"Corpus statistics \(text, word and language counts, period\) derived from the "
                         r"(?:Renascor Corpus|RQ Open Corpus) snapshot (?P<version>v[\w.]+) \((?P<scope>[^)]*)\)\.?")
DISCOVERY_TAIL = re.compile(r"\n\s*\n\s*(?:Justification:|Found at:)[\s\S]*$")
CLEANUPS = [
    # 'Origin verbatim' labels are harvest bookkeeping: quoted form first, else to the end.
    (re.compile(r"\s*Origin verbatim:\s*(?:'[^']*'|‘[^’]*’)\.?(?=\s|$)"), ""),
    (re.compile(r"\s*Origin verbatim:[^\n]*$"), ""),
    (re.compile(r"\s*The original harvest reference is given below\.?"), ""),
    (re.compile(r"\s*\([^()]*\b(?:rebuild|data/raw|scripts)/[^()]*\)"), ""),
    # Link-check codes ('live 200', '(verified live)', '(000)' ...).
    (re.compile(r"\s*\((?:site |repo |also )?(?:live|verified)(?: live)?(?: \(?(?:200|000)\)?)?\)"), ""),
    (re.compile(r"\s*\([^(),;]*\blive 200\)"), ""),
    (re.compile(r"\s*\(verified (?:200|live)[^()]*\)"), ""),
    (re.compile(r",\s*(?:live|verified) 200(?=[,)])"), ""),
    (re.compile(r",\s*verified live(?=\))"), ""),
    (re.compile(r"\s+(?:live|verified) 200(?=[,;)])"), ""),
    (re.compile(r",\s*(?:200|000)\)"), ")"),
    (re.compile(r"\s*\((?:200|000)\)"), ""),
    (re.compile(r"(?:(?<=\s)|^)Site live\.\s*"), ""),
]
TIDY = [(re.compile(r"\(\s*\)"), ""), (re.compile(r"\(\s+"), "("), (re.compile(r"[ \t]{2,}"), " ")]


def split_notes(notes):
    """Return (notes_display, snapshot version or None). Display only: data are never modified.

    Removes the discovery agent's reviewer paragraph, the RQ methodology sentence and the
    reference list that follows it (public URLs and internal pipeline paths), harvest
    bookkeeping and link-check codes.
    """
    text = DISCOVERY_TAIL.sub("", (notes or "").strip()).strip()
    version = None
    m = RQ_SENTENCE.search(text)
    if m:
        version = m.group("version")
        text = text[: m.start()].strip()     # the reference list after the sentence is not displayed
    for pat, rep in CLEANUPS + TIDY:
        text = pat.sub(rep, text)
    return re.sub(r"\s*\n\s*\n\s*", "\n\n", text).strip(), version


# --- Other display fields -----------------------------------------------------------------

def sort_title(title: str) -> str:
    """Filing title: folded, an initial 'The', 'A' or 'An' and leading punctuation dropped."""
    s = unicodedata.normalize("NFKD", title or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().strip()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    return re.sub(r"^[\W_]+", "", s)


WAYBACK = re.compile(r"^/web/(\d{4})(\d{2})(\d{2})\d*[a-z_]*/(?:https?://)?([^/]+)")


def url_parts(url: str):
    """-> (host, url_display, archived_copy). 'https://www.abu.cnam.fr/' -> 'abu.cnam.fr'."""
    p = urlsplit(url or "")
    host = (p.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if host == "web.archive.org":
        m = WAYBACK.match(p.path)
        if m:
            site = m.group(4).lower().split(":")[0]
            site = site[4:] if site.startswith("www.") else site
            archived = {"site": site, "date": f"{m.group(1)}-{m.group(2)}-{m.group(3)}"}
            return host, f"Archived copy of {site}, {archived['date']}", archived
    return host, host + p.path.rstrip("/"), None


def is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def size_band(words):
    if not is_int(words):
        return None
    for floor, key in SIZE_BANDS:
        if words >= floor:
            return key
    return None


def chart_label(title: str) -> str:
    """The title if at most 32 characters, else the part before ' — ', else before ' (', else the title."""
    if len(title) <= 32:
        return title
    for sep in (" — ", " ("):
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title


def derive_entry(eid: str, entry: dict) -> dict:
    """Display-only fields of one entry (nothing here is catalogue data)."""
    notes_display, version = split_notes(entry.get("notes"))
    host, display, archived = url_parts(entry.get("url", ""))
    has_counts = is_int(entry.get("words")) or is_int(entry.get("texts"))
    return {
        "id": eid,
        "sort_title": sort_title(entry.get("title", "")),
        "host": host,
        "url_display": display,
        "archived_copy": archived,
        "data_display": url_parts(entry["data_url"])[1] if entry.get("data_url") else None,
        "period": parse_period(entry.get("period")),
        "size_band": size_band(entry.get("words")),
        "figures": "rq" if version and not entry.get("resource_statistics") else ("other" if has_counts else "none"),
        "snapshot": version,
        "notes_display": notes_display,
    }


# --- Formatting ---------------------------------------------------------------------------

def fmt_int(n: int) -> str:
    return f"{n:,}"


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{fmt_int(n)} {one if n == 1 else (many or one + 's')}"


def join_and(items: list[str]) -> str:
    """'a', 'a and b', 'a, b and c' (no Oxford comma)."""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def long_date(iso: str | None) -> str:
    if not iso or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso):
        return iso or ""
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS[m - 1]} {y}"


def month_year(iso: str | None) -> str:
    if not iso or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso):
        return iso or ""
    y, m, _ = (int(x) for x in iso.split("-"))
    return f"{MONTHS[m - 1]} {y}"


def compact_words(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1e9:.2f} billion"
    if n >= 1_000_000:
        return f"{n / 1e6:.1f} million"
    return fmt_int(n)


def pct(num: int, den: int, decimals: int = 0) -> str:
    """Percentage of exact counts, rounded half up: pct(1, 3) -> '33%', pct(1, 3, 1) -> '33.3%'."""
    if not den:
        return "0%"
    q = Decimal(1).scaleb(-decimals)
    return f"{(Decimal(num) * 100 / Decimal(den)).quantize(q, rounding=ROUND_HALF_UP)}%"


def median_int(values):
    if not values:
        return None
    return int(Decimal(str(statistics.median(values))).quantize(Decimal(1), rounding=ROUND_HALF_UP))


# --- Repository metadata ------------------------------------------------------------------

def git_data_commit(entries_dir: Path):
    """(YYYY-MM-DD, full sha) of the last main-line commit that changed the entries, or (None, None).

    Same selection as `git -C REPO_ROOT log -1 --first-parent -- data/entries`: deletions
    and merges count. Needs the full history (the Pages workflow checks out with fetch-depth 0).
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(entries_dir), "log", "-1", "--first-parent", "--format=%cs %H", "--", "."],
            capture_output=True, text=True, timeout=30, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None, None
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) ([0-9a-f]{40})", out)
    return (m.group(1), m.group(2)) if m else (None, None)


def read_citation(path: Path = CITATION_PATH) -> dict:
    """title, version, date-released, url and the first author from CITATION.cff (no YAML library)."""
    out = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    for key in ("title", "version", "date-released", "url"):
        m = re.search(rf"^{key}:\s*[\"']?(.*?)[\"']?\s*$", text, re.M)
        if m:
            out[key] = m.group(1)
    fam = re.search(r"family-names:\s*[\"']?(.*?)[\"']?\s*$", text, re.M)
    giv = re.search(r"given-names:\s*[\"']?(.*?)[\"']?\s*$", text, re.M)
    out["author"] = f"{fam.group(1)}, {giv.group(1)}" if fam and giv else (fam.group(1) if fam else "")
    return out


def load_countries(path: Path = COUNTRIES_PATH):
    """-> ({code: {name, area}}, [areas in order]) from schema/countries.json, or (None, None)."""
    if not path.exists():
        return None, None
    data = json.loads(path.read_text(encoding="utf-8"))
    countries = {code: {"name": c.get("name", code), "area": c.get("area")}
                 for code, c in data.get("countries", {}).items()}
    return countries, list(data.get("areas", []))


def snapshot_versions(derived: list[dict]) -> list[str]:
    """RQ snapshot versions found in the notes, oldest first. Raises BuildError on an unknown one."""
    versions = sorted({d["snapshot"] for d in derived if d["snapshot"]})
    unknown = [v for v in versions if v not in SNAPSHOTS]
    if unknown:
        raise BuildError("\n".join(f"Unknown RQ snapshot version {v}: add its freeze date to "
                                   "SNAPSHOTS in build_site.py" for v in unknown))
    return versions


# --- Exports ------------------------------------------------------------------------------

def export_fields(schema: dict) -> list[str]:
    """Export columns: id, the schema's properties in the preferred order, any other property, notes last."""
    props = list(schema.get("properties", {}))
    ordered = [f for f in PREFERRED_FIELDS if f in props and f != "notes"]
    extra = [f for f in props if f not in PREFERRED_FIELDS]
    return ["id"] + ordered + extra + (["notes"] if "notes" in props else [])


def csv_columns(fields: list[str]) -> list[str]:
    cols = []
    for f in fields:
        cols += ["years_active_start", "years_active_end"] if f == "years_active" else [f]
    return cols


def csv_value(v) -> str:
    """One CSV value; the page's export (app.js csvValue) does exactly the same."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "; ".join(csv_value(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return str(v)


def csv_row(eid: str, entry: dict, fields: list[str]) -> list[str]:
    row = []
    for f in fields:
        if f == "id":
            row.append(eid)
        elif f == "years_active":
            ya = entry.get("years_active") or {}
            row += [csv_value(ya.get("start")), csv_value(ya.get("end"))]
        else:
            row.append(csv_value(entry.get(f)))
    return row


def csv_cell(value: str) -> str:
    """Quote only fields holding a comma, a double quote, CR or LF; double the quotes."""
    if any(c in value for c in ',"\r\n'):
        return '"' + value.replace('"', '""') + '"'
    return value


def csv_text(columns: list[str], rows: list[list[str]]) -> str:
    """CSV with a CRLF after every row, including the last."""
    return "".join(",".join(csv_cell(v) for v in row) + "\r\n" for row in [columns] + rows)


def default_order(derived: list[dict]) -> list[int]:
    """Indices in the page's default sort (title A to Z): sort_title, then id, by code point."""
    return sorted(range(len(derived)), key=lambda i: (derived[i]["sort_title"], derived[i]["id"]))


def export_entry(eid: str, entry: dict, fields: list[str]) -> dict:
    return {"id": eid, **{f: entry[f] for f in fields[1:] if f in entry}}


# --- Catalogue figures --------------------------------------------------------------------

def compute_stats(entries: list[tuple[str, dict]], derived: list[dict]) -> dict:
    data = [e for _, e in entries]
    labels = Counter(l for e in data for l in e.get("languages", []))
    real = [l for l in labels if l not in PSEUDO_LANGUAGES]
    words = [e["words"] for e in data if is_int(e.get("words"))]
    texts = [e["texts"] for e in data if is_int(e.get("texts"))]
    total_words = sum(words)

    def numeric(d):
        return d["period"] is not None and d["period"]["start"] is not None

    by_words = sorted(((e["words"], e, d) for e, d in zip(data, derived) if is_int(e.get("words"))),
                      key=lambda t: (-t[0], t[2]["id"]))
    top = [{"id": d["id"], "label": chart_label(e["title"]), "words": w,
            "share": round(w / total_words, 4) if total_words else 0} for w, e, d in by_words[:5]]
    largest = None
    if by_words:
        w, e, d = by_words[0]
        largest = {"id": d["id"], "title": e["title"], "words": w,
                   "share": round(w / total_words, 4) if total_words else 0}
    fig = Counter(d["figures"] for d in derived)
    return {
        "editions": len(data),
        "language_labels": len(labels),
        "languages": len(real),
        "pseudo_languages": sorted(l for l in labels if l in PSEUDO_LANGUAGES),
        "single_language": sum(1 for e in data
                               if len([l for l in e.get("languages", []) if l not in PSEUDO_LANGUAGES]) <= 1),
        "language_counts": [[l, n] for l, n in sorted(labels.items(), key=lambda kv: (-kv[1], kv[0]))],
        "texts": sum(texts),
        "words": total_words,
        "with_texts": len(texts),
        "with_words": len(words),
        "median_words": median_int(words),
        "median_texts": median_int(texts),
        "period": {"numeric": sum(1 for d in derived if numeric(d)),
                   "in_words": sum(1 for d in derived if d["period"] and d["period"]["start"] is None),
                   "missing": sum(1 for d in derived if not d["period"])},
        "figures": {"rq": fig["rq"], "other": fig["other"], "none": fig["none"],
                    "other_titles": [e["title"] for e, d in zip(data, derived) if d["figures"] == "other"],
                    "none_titles": [e["title"] for e, d in zip(data, derived) if d["figures"] == "none"]},
        "largest": largest,
        "top_by_words": top,
        "status": {k: sum(1 for e in data if e.get("status") == k) for k in STATUS_ORDER},
        "encoding": {k: sum(1 for e in data if e.get("encoding") == k) for k in ENCODING_ORDER},
        "data_format": {k: sum(1 for e in data if e.get("data_url") and e.get("data_format") == k)
                        for k in ENCODING_ORDER},
        "provenance": dict(sorted(Counter(e.get("provenance") for e in data).items())),
        "with_last_modified": sum(1 for e in data if e.get("last_modified")),
        "with_data_url": sum(1 for e in data if e.get("data_url")),
        "with_region": sum(1 for e in data if e.get("region")),
        "with_countries": sum(1 for e in data if e.get("countries")),
    }


def load_corpus_statistics(path: Path, snapshot: str | None) -> dict | None:
    """Count the complete audited corpus, independently of catalogue rows and resource censuses."""
    if not snapshot or not path.is_file():
        return None
    audit = json.loads(path.read_text(encoding="utf-8"))
    if audit.get("snapshot") != snapshot or audit.get("scope") != list(SCOPE):
        raise BuildError("Corpus audit must match the working snapshot and 1450–1700 scope")
    collections = audit.get("collections", {})
    if not collections:
        raise BuildError("Corpus audit has no collections")
    for collection in collections.values():
        for key in ("words", "texts"):
            count = collection.get("corpus_" + key)
            resource_count = collection.get(key)
            if not is_int(count) or count < 0 or not is_int(resource_count) or count > resource_count:
                raise BuildError("Corpus audit has invalid deduplicated counts")
    return {"name": SNAPSHOT_NAME, "snapshot": snapshot, "frozen": SNAPSHOTS[snapshot]["frozen"],
            "scope": list(SCOPE), "words": sum(c["corpus_words"] for c in collections.values()),
            "texts": sum(c["corpus_texts"] for c in collections.values()),
            "basis": "After the corpus duplicate filter; complete working snapshot, before catalogue grouping",
            "source": f"{REPO_URL}/blob/main/data/rq_statistics.json",
            "database_sha256": audit.get("database_sha256")}


def load_period_words(path: Path, corpus: dict | None, derived: list[dict]) -> dict | None:
    """Attach recorded years and explicitly separate estimates from per-text evidence."""
    for d in derived:
        d["period_words"] = None
    if not corpus or not path.is_file():
        return None
    audit = json.loads(path.read_text(encoding="utf-8"))
    if (audit.get("snapshot") != corpus["snapshot"] or audit.get("scope") != list(SCOPE)
            or audit.get("database_sha256") != corpus["database_sha256"]
            or audit.get("decade_starts") != DECADE_STARTS):
        raise BuildError("Period word counts must match the corpus snapshot, database and scope")
    family_hash = hashlib.sha256((REPO_ROOT / "scripts/rq_families.json").read_bytes()).hexdigest()
    if audit.get("families_sha256") != family_hash:
        raise BuildError("Regenerate period word counts after changing the collection family map")
    source = json.loads((path.parent / "rq_statistics.json").read_text(encoding="utf-8"))["collections"]
    collections = audit.get("collections", {})
    if set(collections) != set(source):
        raise BuildError("Period word counts must cover every audited source collection")
    by_entry = {d["id"]: d for d in derived}
    unlisted_words = 0
    for name, c in collections.items():
        bins = c.get("decade_words", [])
        estimates = c.get("estimated_decade_words", [])
        counts = [c.get("words"), c.get("texts"), c.get("undated_words"), *bins, *estimates]
        if (len(bins) != len(DECADE_STARTS) or len(estimates) != len(DECADE_STARTS)
                or any(not is_int(n) or n < 0 for n in counts)):
            raise BuildError(f"Invalid period word counts: {name}")
        if (c["words"] != source[name]["corpus_words"] or c["texts"] != source[name]["corpus_texts"]
                or sum(bins) + sum(estimates) + c["undated_words"] != c["words"]):
            raise BuildError(f"Period word counts disagree with the corpus audit: {name}")
        ranges = [e for e in c.get("date_estimates", []) if e.get("status") == "estimated"]
        for e in ranges:
            span = e.get("range", [])
            if (len(span) != 2 or any(not is_int(y) for y in span)
                    or not SCOPE[0] <= span[0] <= span[1] <= SCOPE[1]
                    or not is_int(e.get("words")) or e["words"] < 0):
                raise BuildError(f"Invalid date estimate: {name}")
        if sum(e["words"] for e in ranges) != sum(estimates):
            raise BuildError(f"Date estimates disagree with allocated words: {name}")
        d = by_entry.get(c.get("entry"))
        if d is None:
            unlisted_words += c["words"]
            continue
        if d["period_words"] is None:
            d["period_words"] = {"decades": [0] * len(DECADE_STARTS),
                                 "estimated": [0] * len(DECADE_STARTS), "undated": 0,
                                 "estimated_range": None}
        p = d["period_words"]
        p["decades"] = [a + b for a, b in zip(p["decades"], bins)]
        p["estimated"] = [a + b for a, b in zip(p["estimated"], estimates)]
        p["undated"] += c["undated_words"]
        if ranges:
            spans = [e["range"] for e in ranges] + ([p["estimated_range"]] if p["estimated_range"] else [])
            p["estimated_range"] = [min(s[0] for s in spans), max(s[1] for s in spans)]
    # Keep cards and date filtering consistent with the graph's approximate coverage.
    for d in derived:
        p = d["period_words"]
        if not p or not p["estimated_range"]:
            continue
        lo, hi = p["estimated_range"]
        original = d.get("period")
        if original and original["start"] is not None:
            lo, hi = min(lo, original["start"]), max(hi, original["end"])
        period = parse_period(f"c. {lo}-{hi}")
        period["raw"] = original["raw"] if original else None
        period["note"] = original["note"] if original else None
        period["estimate_note"] = "Includes broad author-lifespan estimates for texts without a recorded year."
        d["period"] = period
    mapped = [d["period_words"] for d in derived if d["period_words"] is not None]
    return {"snapshot": corpus["snapshot"], "frozen": corpus["frozen"],
            "decade_words": [sum(p["decades"][i] + p["estimated"][i] for p in mapped) for i in range(len(DECADE_STARTS))],
            "estimated_words": sum(sum(p["estimated"]) for p in mapped),
            "undated_words": sum(p["undated"] for p in mapped), "unlisted_words": unlisted_words,
            "basis": audit["basis"], "date_basis": audit["date_basis"],
            "source": f"{REPO_URL}/blob/main/data/period_word_counts.json"}


def display_strings(stats: dict, *, updated: str, sha: str | None, citation: dict,
                    snapshot: str | None, areas: list[str] | None, corpus: dict | None = None,
                    timeline: dict | None = None) -> dict:
    """Every figure and sentence the build writes into index.html (the page never formats these)."""
    s = stats
    n = s["editions"]
    version = citation.get("version", "")
    frozen = SNAPSHOTS.get(snapshot, {}).get("frozen") if snapshot else None

    note = (f"Corpus totals exclude duplicate texts ({month_year(corpus['frozen'])} working count). "
            "Individual collection sizes include overlaps and may be partial." if corpus else
            "No deduplicated corpus total recorded. Individual collection sizes include overlaps and may be partial.")

    timeline_bits = []
    if timeline:
        timeline_bits.append(f"Deduplicated corpus words ({month_year(timeline['frozen'])}); dates include estimates.")
        if timeline["estimated_words"]:
            timeline_bits.append(f"{plural(timeline['estimated_words'], 'word')} allocated from author-lifespan estimates.")
        if timeline["undated_words"]:
            timeline_bits.append(f"{plural(timeline['undated_words'], 'word')} without a usable date omitted.")
        timeline_bits.append("Collections without dated corpus counts are omitted.")
    else:
        timeline_bits.append("No chronological corpus word counts recorded for this catalogue.")

    other_bits = []
    if s["figures"]["other"]:
        names = join_and([chart_label(t) for t in s["figures"]["other_titles"]])
        other_bits.append(f"For {plural(s['figures']['other'], 'edition')} the counts come from "
                          f"other sources: {names}.")
    if s["figures"]["none"]:
        k = s["figures"]["none"]
        other_bits.append(f"{plural(k, 'edition')} {'has' if k == 1 else 'have'} no word or text count.")

    missing = n - s["with_words"]
    if missing:
        share_note = (f"Shares of the {fmt_int(s['words'])} words recorded for {plural(s['with_words'], 'edition')}; "
                      f"{plural(missing, 'edition')} {'has' if missing == 1 else 'have'} no word count.")
    else:
        share_note = f"Shares of the {fmt_int(s['words'])} words recorded for all {plural(n, 'edition')}."

    share_note += " Collection totals include overlapping texts."
    disc = s["provenance"].get("discovered", 0)
    discovered_sentence = (f"{fmt_int(disc)} of the {plural(n, 'record')} "
                           f"{'was' if disc == 1 else 'were'} proposed this way")

    year = (citation.get("date-released") or updated or "")[:4]
    display = {
        "editions": fmt_int(n),
        "editions_label": plural(n, "edition"),
        "languages": fmt_int(s["languages"]),
        "language_labels": fmt_int(s["language_labels"]),
        "texts": fmt_int(s["texts"]),
        "words": fmt_int(s["words"]),
        "words_compact": compact_words(s["words"]),
        "corpus_texts": fmt_int(corpus["texts"]) if corpus else "—",
        "corpus_words": fmt_int(corpus["words"]) if corpus else "—",
        "corpus_words_compact": compact_words(corpus["words"]) if corpus else "—",
        "with_words": fmt_int(s["with_words"]),
        "with_words_editions": plural(s["with_words"], "edition"),
        "without_words": fmt_int(missing),
        "figures_rq": fmt_int(s["figures"]["rq"]),
        "discovered": fmt_int(disc),
        "discovered_sentence": discovered_sentence,
        "single_language": fmt_int(s["single_language"]),
        "median_words": fmt_int(s["median_words"] or 0),
        "median_texts": fmt_int(s["median_texts"] or 0),
        "updated_long": long_date(updated),
        "updated_iso": updated,
        "version": version,
        "data_commit_short": sha[:7] if sha else "",
        "data_commit_url": f"{REPO_URL}/commit/{sha}" if sha else REPO_URL,
        "header_note": note,
        "timeline_note": " ".join(timeline_bits),
        "snapshot_version": snapshot or "",
        "snapshot_frozen_long": long_date(frozen) if frozen else "",
        "snapshot_month": month_year(frozen) if frozen else "",
        "figures_other_sentence": " ".join(other_bits),
        "largest_share": pct(s["largest"]["words"], s["words"]) if s["largest"] and s["words"] else "0%",
        "share_note": share_note,
        "with_last_modified": plural(s["with_last_modified"], "edition"),
        "with_data_url": plural(s["with_data_url"], "edition") if s["with_data_url"] else "",
        "with_countries": plural(s["with_countries"], "edition") if s["with_countries"] else "",
        "areas_list": join_and(areas or []),
        "citation_author_year": f"{citation.get('author', '')} ({year}).",
        "citation_title": citation.get("title", ""),
        "citation_tail": f"(Version {version}) [Data set]. {citation.get('url', '')}".rstrip(),
    }
    for k in STATUS_ORDER:
        c = s["status"][k]
        display[f"status_{k}"] = plural(c, "edition") + "." if c else "None at present."
    for k in ENCODING_ORDER:
        c = s["encoding"][k]
        display[f"encoding_{k.replace('-', '_')}"] = plural(c, "edition") + "." if c else "None at present."
    return display


# --- Build-rendered charts (methodology section) -----------------------------------------

def share_chart(stats: dict) -> str:
    """Share of all recorded words: the five largest editions, then all the others (section 6.4)."""
    s = stats
    total = s["words"]
    if not total or not s["top_by_words"]:
        return '<p class="chart-empty">No word counts are recorded yet.</p>'

    def row(label_html: str, words: int, cls: str = "") -> str:
        return (f'<tr{cls}><th scope="row">{label_html}</th>'
                f'<td class="bar" aria-hidden="true"><span style="width:{words / total * 100:.2f}%"></span></td>'
                f'<td class="num">{pct(words, total, 1)}</td><td class="num">{fmt_int(words)}</td></tr>')

    rows = [row(f'<a href="#{html.escape(t["id"])}">{html.escape(t["label"])}</a>', t["words"])
            for t in s["top_by_words"]]
    rest_words = total - sum(t["words"] for t in s["top_by_words"])
    rest_n = s["with_words"] - len(s["top_by_words"])
    if rest_n > 0:
        rows.append(row(html.escape(plural(rest_n, "other edition")), rest_words, ' class="rest"'))
    return ('<table class="sharet"><caption>Share of recorded collection words, including overlaps</caption>'
            '<thead><tr><th scope="col">Edition</th><th scope="col"><span class="sr-only">Share, as a bar</span></th>'
            '<th scope="col" class="num">Share</th><th scope="col" class="num">Words</th></tr></thead>'
            '<tbody>' + "".join(rows) + '</tbody></table>')


# --- Writing index.html -------------------------------------------------------------------

STAT_RE = re.compile(r'(<(?P<tag>[a-z0-9]+)\b[^>]*\sdata-stat="(?P<key>[a-z0-9_]+)"[^>]*>)(?P<inner>[^<]*)(</(?P=tag)>)')
ANY_STAT_RE = re.compile(r'\sdata-stat="([^"]*)"')
OPEN_TAG_RE = re.compile(r'<(?P<tag>[a-z][a-z0-9]*)\b(?P<attrs>[^<>]*)>')
HREF_ATTR_RE = re.compile(r'\shref="[^"]*"')
HIDDEN_ATTR_RE = re.compile(r'\shidden(?:="[^"]*")?(?=[\s/]|$)')


def inject(page: str, display: dict, regions: dict) -> str:
    """Write display values and build regions into the page. Idempotent; raises BuildError.

    - <el data-stat="key">text</el>: the text becomes display[key] (HTML-escaped);
    - <a data-href="key" href="...">: the href becomes display[key];
    - <el data-if="key">: the element is hidden when display[key] is empty;
    - <!-- build:name -->...<!-- /build:name -->: the contents become regions[name].
    """
    def known(key: str) -> str:
        if key not in display:
            raise BuildError(f"index.html: unknown data key '{key}' (no such value in meta.display)")
        return display[key]

    def fix_tag(m: re.Match) -> str:
        attrs = m.group("attrs")
        mh = re.search(r'\sdata-href="([^"]*)"', attrs)
        mi = re.search(r'\sdata-if="([^"]*)"', attrs)
        if not mh and not mi:
            return m.group(0)
        if mh:
            value = html.escape(known(mh.group(1)), quote=True)
            if HREF_ATTR_RE.search(attrs):
                attrs = HREF_ATTR_RE.sub(lambda _: f' href="{value}"', attrs, count=1)
            else:
                attrs += f' href="{value}"'
        if mi:
            show = bool(known(mi.group(1)))
            attrs = HIDDEN_ATTR_RE.sub("", attrs)
            if not show:
                attrs = attrs.rstrip() + " hidden"
        return f"<{m.group('tag')}{attrs}>"

    page = OPEN_TAG_RE.sub(fix_tag, page)

    def fill(m: re.Match) -> str:
        return m.group(1) + html.escape(known(m.group("key")), quote=False) + m.group(5)

    page, filled = STAT_RE.subn(fill, page)
    slots = ANY_STAT_RE.findall(page)
    for key in slots:
        known(key)
    if filled != len(slots):
        raise BuildError("index.html: a data-stat element must contain text only "
                         f"({len(slots)} data-stat attributes, {filled} filled)")

    for name, body in regions.items():
        pat = re.compile(rf"(<!-- build:{re.escape(name)} -->)(.*?)(<!-- /build:{re.escape(name)} -->)", re.S)
        if not pat.search(page):
            raise BuildError(f"index.html: missing region <!-- build:{name} --> ... <!-- /build:{name} -->")
        page = pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(3), page, count=1)
    return page


# --- Build --------------------------------------------------------------------------------

def build_payload(entries: list[tuple[str, dict]], schema: dict, entries_dir: Path):
    """-> (meta, derived). Raises BuildError when a guard fails."""
    check_entries(entries)
    derived = [derive_entry(entry_id(name), e) for name, e in entries]
    versions = snapshot_versions(derived)
    if len(versions) > 1:
        print(f"Warning: several RQ snapshot versions in the notes ({', '.join(versions)}); "
              f"the page names the latest, {versions[-1]}", file=sys.stderr)
    snapshot = versions[-1] if versions else None

    stats = compute_stats(entries, derived)
    updated, sha = git_data_commit(entries_dir)
    if not updated:
        updated = max((e.get("date_added", "") for _, e in entries), default="")
    citation = read_citation()
    countries, areas = load_countries()
    has_countries_prop = "countries" in schema.get("properties", {})
    fields = export_fields(schema)
    corpus = load_corpus_statistics(entries_dir.parent / "rq_statistics.json", snapshot)
    timeline = load_period_words(entries_dir.parent / "period_word_counts.json", corpus, derived)

    meta = {
        "title": SITE_TITLE,
        "description": SITE_DESCRIPTION,
        "source": REPO_URL,
        "licence": {"data": "CC0-1.0", "code": "MIT"},
        "version": citation.get("version", ""),
        "released": citation.get("date-released", ""),
        "updated": updated,
        "data_commit": {"sha": sha, "short": sha[:7]} if sha else None,
        "scope": {"from": SCOPE[0], "to": SCOPE[1]},
        "snapshot": {"name": SNAPSHOT_NAME, "version": snapshot,
                     "frozen": SNAPSHOTS.get(snapshot, {}).get("frozen") if snapshot else None,
                     "scope": SNAPSHOT_SCOPE},
        "snapshots": {v: {"frozen": SNAPSHOTS[v]["frozen"], "month": month_year(SNAPSHOTS[v]["frozen"])}
                      for v in versions},
        "fields": fields,
        "csv_columns": csv_columns(fields),
        "stats": stats,
        "corpus_statistics": corpus,
        "timeline": timeline,
        "display": display_strings(stats, updated=updated, sha=sha, citation=citation, snapshot=snapshot,
                                   areas=areas if (countries is not None and has_countries_prop) else None,
                                   corpus=corpus, timeline=timeline),
    }
    if countries is not None and has_countries_prop:
        meta["countries"] = countries
        meta["areas"] = areas
    return meta, derived


def write_if_changed(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def public_json(entries, derived, meta) -> dict:
    order = default_order(derived)
    fields = meta["fields"]
    return {
        "meta": {
            "title": SITE_TITLE,
            "source": REPO_URL,
            "licence": "CC0-1.0",
            "version": meta["version"],
            "data_updated": meta["updated"],
            "data_commit": meta["data_commit"]["sha"] if meta["data_commit"] else None,
            "corpus_statistics": meta.get("corpus_statistics"),
            "records": len(entries),
            "fields": fields,
            "sort": "title-asc",
            "selection": None,
        },
        "entries": [export_entry(derived[i]["id"], entries[i][1], fields) for i in order],
    }


def write_outputs(entries, derived, meta, out_dir: Path, index_template: Path) -> list[str]:
    """Write the four outputs; returns the names of the files that changed."""
    changed = []
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "entries": [e for _, e in entries], "derived": derived}
    files = {
        "data.json": json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
        "renascor.csv": csv_text(meta["csv_columns"],
                                 [csv_row(derived[i]["id"], entries[i][1], meta["fields"])
                                  for i in default_order(derived)]),
        "renascor.json": json.dumps(public_json(entries, derived, meta), ensure_ascii=False, indent=2) + "\n",
    }
    for name, text in files.items():
        if write_if_changed(out_dir / name, text.encode("utf-8")):
            changed.append(name)

    target = out_dir / "index.html"
    if out_dir.resolve() != index_template.resolve().parent:
        # Scratch build: copy the script next to the page, so the copy is a working site.
        app = DOCS_DIR / "app.js"
        if app.exists() and write_if_changed(out_dir / "app.js", app.read_bytes()):
            changed.append("app.js")
    page = index_template.read_text(encoding="utf-8")
    page = inject(page, meta["display"], {"share-chart": share_chart(meta["stats"])})
    if write_if_changed(target, page.encode("utf-8")):
        changed.append("index.html")
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--entries-dir", type=Path, default=REPO_ROOT / "data" / "entries")
    parser.add_argument("--out-dir", type=Path, default=DOCS_DIR)
    parser.add_argument("--index", type=Path, default=DOCS_DIR / "index.html",
                        help="page template holding the data-stat slots (default docs/index.html)")
    args = parser.parse_args(argv)

    schema = load_schema()
    entries = load_entries(args.entries_dir)
    if not entries:
        print(f"Error: no entries found in {args.entries_dir}", file=sys.stderr)
        return 1

    errors = validate_entries(entries, schema)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    try:
        meta, derived = build_payload(entries, schema, args.entries_dir)
        changed = write_outputs(entries, derived, meta, args.out_dir, args.index)
    except BuildError as e:
        print(f"Build failed:\n{e}", file=sys.stderr)
        return 1

    s = meta["stats"]
    try:
        where = args.out_dir.resolve().relative_to(REPO_ROOT)
    except ValueError:
        where = args.out_dir
    print(f"Built site: {len(entries)} entries -> {where} ({s['languages']} languages, "
          f"{s['language_labels']} labels; figures rq={s['figures']['rq']} other={s['figures']['other']} "
          f"none={s['figures']['none']}; updated {meta['updated']})")
    print(f"Changed: {', '.join(changed)}" if changed else "No file changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
