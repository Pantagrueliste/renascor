#!/usr/bin/env python3
"""Count Sefaria's dated source editions independently of the frozen RQ corpus.

Use the live API table of contents and the official export's index metadata.
Fallback to the raw Index API where an export schema is unavailable. Count
individual Hebrew source versions, without content deduplication. Generated
merged copies and translations are excluded. Ambiguous dates stay in the audit.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.sefaria.org/api"
BUCKET = "https://storage.googleapis.com/sefaria-export"
BOOKS = "https://raw.githubusercontent.com/Sefaria/Sefaria-Export/master/books.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Client:
    def __init__(self, cache: Path, refresh: bool = False):
        self.cache = cache
        self.refresh = refresh
        cache.mkdir(parents=True, exist_ok=True)

    def get(self, url: str) -> tuple[object, dict]:
        path = self.cache / (digest(url.encode()) + ".json")
        if path.exists() and not self.refresh:
            raw = path.read_bytes()
        else:
            for attempt in range(4):
                try:
                    with urlopen(Request(url, headers={"User-Agent": "Renascor-catalogue/0.1 (research)",
                                                       "Accept": "application/json"}), timeout=60) as response:
                        raw = response.read()
                    json.loads(raw)  # Never cache an HTML error page.
                    temporary = path.with_suffix(".tmp")
                    temporary.write_bytes(raw)
                    temporary.replace(path)
                    break
                except HTTPError as error:
                    if error.code in (404, 400) or attempt == 3:
                        raise
                    time.sleep(min(30, int(error.headers.get("Retry-After", 2 ** attempt))))
                except (URLError, TimeoutError):
                    if attempt == 3:
                        raise
                    time.sleep(2 ** attempt)
        result = json.loads(raw)
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"{url}: {result['error']}")
        return result, {"url": url, "sha256": digest(raw), "bytes": len(raw),
                        "retrieved": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")}


def titles_in_toc(nodes: list) -> set[str]:
    titles = set()
    for node in nodes:
        if "contents" in node:
            titles.update(titles_in_toc(node["contents"]))
        elif node.get("title") and not node.get("isCollection"):
            titles.add(node["title"])
    return titles


def composition_scope(record: dict, start: int = 1450, end: int = 1700) -> tuple[str, list[int]]:
    """Do not substitute first printing, author lifespan or era for composition."""
    dates = record.get("compDate")
    if not dates:
        return "undated", []
    if not isinstance(dates, list):
        return "invalid-date", []
    if len(dates) not in (1, 2) or any(type(d) is not int for d in dates):
        return "invalid-date", []
    lo, hi = min(dates), max(dates)
    if start <= lo <= hi <= end:
        return "included", dates
    if hi < start or lo > end:
        return "outside", dates
    return "boundary-review", dates


class VisibleText(HTMLParser):
    """Extract text, omitting modern footnotes and their markers."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.stack = [], []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        hidden = tag in ("script", "style") or bool(classes & {"footnote", "footnote-marker"})
        hidden = hidden or (self.stack[-1][1] if self.stack else False)
        if tag not in {"br", "hr", "img", "input", "meta", "link", "wbr"}:
            self.stack.append((tag, hidden))
        if not hidden:
            self.parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break
        if not self.stack or not self.stack[-1][1]:
            self.parts.append(" ")

    def handle_data(self, text):
        if not self.stack or not self.stack[-1][1]:
            self.parts.append(text)


def segments(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from segments(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from segments(child)


def count_version(record: dict) -> int:
    words = 0
    for segment in segments(record.get("text", [])):
        parser = VisibleText()
        parser.feed(segment)
        parser.close()
        words += len("".join(parser.parts).split())
    return words


def source_version(book: dict, record: dict) -> bool:
    return (book.get("versionTitle") != "merged" and book.get("language") == "Hebrew"
            and record.get("isSource") is True)


def audit_index(client: Client, title: str, start: int, end: int) -> dict:
    url = f"{BUCKET}/schemas/{quote(title.replace(' ', '_'), safe='')}.json"
    try:
        record, evidence = client.get(url)
    except HTTPError as error:
        if error.code != 404:
            raise
        record, evidence = client.get(f"{API}/v2/raw/index/{quote(title, safe='')}")
    if record.get("title") != title:
        raise ValueError(f"Index title mismatch: {title}")
    status, dates = composition_scope(record, start, end)
    return {"title": title, "status": status, "compDate": dates,
            "pubDate": record.get("pubDate", []), "hasErrorMargin": record.get("hasErrorMargin", False),
            "source": evidence}


def audit_version(client: Client, book: dict) -> dict:
    record, evidence = client.get(book["json_url"])
    if record.get("title") != book["title"]:
        raise ValueError(f"Version title mismatch: {book['title']}")
    source = source_version(book, record)
    return {"title": book["title"], "version": record.get("versionTitle"),
            "status": "counted" if source else "non-source-version",
            "words": count_version(record) if source else 0,
            "license": record.get("license") or "Not stated",
            "language": record.get("actualLanguage") or record.get("language"),
            "source": evidence}


def parallel_audit(items: list, action, workers: int, label: str) -> list:
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(action, item): item for item in items}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                results.append(future.result())
            except Exception as error:
                errors.append(f"{futures[future]}: {error}")
            if i % 250 == 0 or i == len(items):
                print(f"{label}: {i}/{len(items)}; errors={len(errors)}", flush=True)
    if errors:
        raise RuntimeError("Incomplete harvest; catalogue was not updated.\n" + "\n".join(errors))
    return results


def update_entry(path: Path, audit: dict) -> None:
    if audit["scope"] != [1450, 1700] or not audit["texts"]:
        raise ValueError("Only a completed, nonempty 1450–1700 audit can update the catalogue")
    entry = json.loads(path.read_text())
    note = (f"Counted {audit['texts']:,} individual Hebrew source versions of {audit['works']:,} works "
            "whose entire recorded composition-date range lies within 1450–1700. "
            "Includes repeated content across editions; excludes generated merged files and translations. "
            "Undated and boundary-crossing works require review. "
            f"Official export dated {audit['export_generated'][:10]}, checked {audit.get('audited', audit['retrieved'])}.")
    entry.update(words=audit["words"], texts=audit["texts"], count_basis="sefaria-source-versions",
                 resource_statistics={"url": "https://github.com/Pantagrueliste/renascor/blob/main/data/sefaria_statistics.json",
                                      "date": audit.get("audited", audit["retrieved"]), "note": note})
    counted_titles = {row["title"] for row in audit["versions"] if row["status"] == "counted" and row["words"]}
    years = [year for row in audit["indexes"] if row["title"] in counted_titles for year in row["compDate"]]
    entry["period"] = f"{min(years)}-{max(years)}"
    entry["notes"] = ("Official bulk exports provide JSON and TXT downloads; the developer documentation "
                      "describes the REST API. "
                      "Corpus statistics (text, word and language counts, period) derived from the "
                      "Renascor Corpus snapshot v2026.06 (in-core, after corpus deduplication).")
    # The original corpus_statistics object is preserved; never import into the RQ database.
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/sefaria")
    parser.add_argument("--out", type=Path, default=ROOT / "data/sefaria_statistics.json")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--refresh", action="store_true", help="Fetch fresh source data instead of replaying the cached snapshot")
    parser.add_argument("--start", type=int, default=1450)
    parser.add_argument("--end", type=int, default=1700)
    parser.add_argument("--update-entry", action="store_true", help="Apply the completed audit to the Sefaria card")
    args = parser.parse_args()
    client = Client(args.cache, args.refresh)
    toc, toc_source = client.get(API + "/index")
    books, books_source = client.get(BOOKS)
    titles = sorted(titles_in_toc(toc))
    print(f"API inventory: {len(titles)} titles; export generated {books['generated_at']}", flush=True)
    indexes = parallel_audit(titles, lambda title: audit_index(client, title, args.start, args.end),
                             args.workers, "Composition metadata")
    included = {row["title"] for row in indexes if row["status"] == "included"}
    candidates = [book for book in books["books"] if book["title"] in included
                  and book.get("language") == "Hebrew" and book.get("versionTitle") != "merged"]
    # The export index may repeat a download URL. It is one file, counted once.
    candidates = list({book["json_url"]: book for book in candidates}.values())
    versions = parallel_audit(candidates, lambda book: audit_version(client, book), args.workers, "Source versions")
    counted = [row for row in versions if row["status"] == "counted" and row["words"] > 0]
    retrieved = max(source["retrieved"] for source in
                    [toc_source, books_source] + [row["source"] for row in indexes + versions])[:10]
    audit = {"retrieved": retrieved, "audited": datetime.now(timezone.utc).date().isoformat(),
             "export_generated": books["generated_at"], "scope": [args.start, args.end],
             "selection": "Entire composition-date range within scope; Hebrew source versions. No content deduplication; generated merged files and translations excluded. Unknown and boundary-crossing dates require review.",
             "word_method": "Whitespace-separated tokens of visible text, excluding HTML tags, footnotes and footnote markers.",
             "sources": {"toc": toc_source, "export_index": books_source},
             "words": sum(row["words"] for row in counted), "texts": len(counted),
             "works": len({row["title"] for row in counted}),
             "licenses": dict(sorted(Counter(row["license"] for row in counted).items())),
             "date_statuses": dict(sorted(Counter(row["status"] for row in indexes).items())),
             "dated_titles_without_counted_source_version": sorted(included - {row["title"] for row in counted}),
             "indexes": sorted(indexes, key=lambda row: row["title"]),
             "versions": sorted(versions, key=lambda row: (row["title"], row["version"] or ""))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    if args.update_entry:
        update_entry(ROOT / "data/entries/sefaria.json", audit)
    print(json.dumps({key: audit[key] for key in ["words", "texts", "works", "date_statuses", "licenses"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
