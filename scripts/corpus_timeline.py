#!/usr/bin/env python3
"""Export text-free chronological word counts from the frozen working corpus.

Each retained, deduplicated text contributes once, at its recorded harvest year.
Missing years can use explicitly labelled author-lifespan estimates. Collection
totals are never spread over a collection's date span.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sqlite3
from pathlib import Path

try:
    from .rq_statistics import checksum, project_collections
except ImportError:
    from rq_statistics import checksum, project_collections

ROOT = Path(__file__).resolve().parents[1]
SCOPE = [1450, 1700]
DECADES = list(range(1450, 1700, 10))


def empty_counts() -> dict:
    return {"words": 0, "texts": 0, "decade_words": [0] * len(DECADES),
            "estimated_decade_words": [0] * len(DECADES), "undated_words": 0,
            "date_estimates": []}


def allocate_range(words: int, start: int, end: int) -> list[int]:
    """Display convention: equal weight per possible year, with integer conservation.

    This is an estimated distribution, not evidence of equal production over time.
    Largest remainders preserve the exact text word count, including the 1700 boundary.
    """
    if words < 0 or not SCOPE[0] <= start <= end <= SCOPE[1]:
        raise ValueError("Range allocation must stay within 1450–1700 with nonnegative words")
    width = end - start + 1
    weights = [max(0, min(end, 1700 if i == 24 else y + 9) - max(start, y) + 1)
               for i, y in enumerate(DECADES)]
    bins = [words * n // width for n in weights]
    for i in sorted(range(len(bins)), key=lambda i: (-(words * weights[i] % width), i))[:words - sum(bins)]:
        bins[i] += 1
    return bins


def lifespan_estimate(collection: str, filename: str, origin: str, basis: str) -> dict | None:
    """Use the saved Gutenberg author metadata only, never an ebook release date.

    A lifespan is a broad proxy for the underlying work, not a publication date.
    Do not clip a range crossing the scope: those works need individual review.
    """
    if not collection.startswith("Gutenberg") or not re.fullmatch(r"author_death_\d{4}", basis or ""):
        return None
    parts = (origin or "").split(" — ")
    author = parts[1] if len(parts) >= 3 else ""
    spans = re.findall(r"(?<!\d)(1[3-7]\d\d)\??\s*[-–]\s*(1[4-7]\d\d)\??(?!\d)", author)
    pg = re.fullmatch(r"pg(\d+)\.txt", filename or "")
    out = {"filename": filename, "evidence": author, "basis": "author-lifespan proxy",
           "source": f"https://www.gutenberg.org/ebooks/{pg[1]}" if pg else None}
    if len(spans) != 1:
        return {**out, "status": "review", "reason": "No single complete author lifespan in saved metadata"}
    start, end = map(int, spans[0])
    out["range"] = [start, end]
    if not SCOPE[0] <= start <= end <= SCOPE[1]:
        return {**out, "status": "review", "reason": "Lifespan is invalid or crosses 1450–1700"}
    if end != int(basis.rsplit("_", 1)[1]):
        return {**out, "status": "review", "reason": "Lifespan disagrees with the harvest's selected author"}
    return {**out, "status": "estimated"}


def count_years(db: Path) -> tuple[dict, dict]:
    collections, confidence = {}, {}
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        for name, year, words, basis, filename, origin in con.execute(
            "SELECT collection, year, wordcount, date_confidence, filename, origin FROM texts "
            "WHERE in_core = 1 AND is_dup = 0"
        ):
            words = words or 0
            if not isinstance(words, int) or words < 0:
                raise ValueError(f"Invalid word count in {name}")
            c = collections.setdefault(name, empty_counts())
            c["words"] += words
            c["texts"] += 1
            if year is None:
                estimate = lifespan_estimate(name, filename, origin, basis)
                if estimate:
                    c["date_estimates"].append({**estimate, "words": words})
                if estimate and estimate["status"] == "estimated":
                    bins = allocate_range(words, *estimate["range"])
                    c["estimated_decade_words"] = [a + b for a, b in zip(c["estimated_decade_words"], bins)]
                else:
                    c["undated_words"] += words
            else:
                if not isinstance(year, int) or not SCOPE[0] <= year <= SCOPE[1]:
                    raise ValueError(f"Retained date outside 1450–1700 in {name}: {year}")
                c["decade_words"][min((year - SCOPE[0]) // 10, len(DECADES) - 1)] += words
            b = confidence.setdefault(basis or "not recorded", {"words": 0, "texts": 0})
            b["words"] += words
            b["texts"] += 1
    finally:
        con.close()
    return collections, confidence


def make_audit(db: Path, corpus_audit: dict, families: dict) -> dict:
    digest = checksum(db)
    if digest != corpus_audit.get("database_sha256") or corpus_audit.get("scope") != SCOPE:
        raise ValueError("Use the exact database and scope recorded in rq_statistics.json")
    collections, confidence = count_years(db)
    # A source census can replace a card's size without changing its June corpus history.
    mapping = copy.deepcopy(families)
    for group in mapping["groups"]:
        group.pop("merge_stats", None)
    projects = project_collections(corpus_audit["collections"], mapping)
    entries = {name: entry for entry, members in projects.items() for name in members}
    for name, counts in corpus_audit["collections"].items():
        c = collections.setdefault(name, empty_counts())
        if (c["words"], c["texts"]) != (counts["corpus_words"], counts["corpus_texts"]):
            raise ValueError(f"Chronological counts disagree with the corpus audit: {name}")
        c["entry"] = entries.get(name)
    if set(collections) != set(corpus_audit["collections"]):
        raise ValueError("Database has collections absent from the corpus audit")
    return {
        "snapshot": corpus_audit["snapshot"], "scope": SCOPE,
        "database_sha256": digest, "decade_starts": DECADES,
        "basis": "Retained in-core texts after the corpus duplicate filter. Each text is counted once.",
        "date_basis": "Recorded harvest years, including inferred dates and author-lifespan proxies; "
                      "not a uniform chronology of composition or publication. Missing years with a complete "
                      "in-scope Gutenberg author lifespan use a separate estimated distribution, weighted "
                      "equally per year across that lifespan. This is a display convention, not evidence of "
                      "equal production. Other missing years remain unallocated.",
        "date_confidence": dict(sorted(confidence.items())),
        "collections": dict(sorted(collections.items())),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    args = parser.parse_args()
    corpus = json.loads((ROOT / "data/rq_statistics.json").read_text())
    families_path = ROOT / "scripts/rq_families.json"
    audit = make_audit(args.db, corpus, json.loads(families_path.read_text()))
    audit["families_sha256"] = checksum(families_path)
    target = ROOT / "data/period_word_counts.json"
    target.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target.name}: {sum(c['words'] for c in audit['collections'].values()):,} corpus words")


if __name__ == "__main__":
    main()
