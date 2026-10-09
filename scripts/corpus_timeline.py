#!/usr/bin/env python3
"""Export text-free chronological word counts from the frozen working corpus.

Each retained, deduplicated text contributes once, at its recorded harvest year.
Undated texts are counted separately; resource totals are never spread over years.
"""
from __future__ import annotations

import argparse
import copy
import json
import sqlite3
from pathlib import Path

try:
    from .rq_statistics import checksum, project_collections
except ImportError:
    from rq_statistics import checksum, project_collections

ROOT = Path(__file__).resolve().parents[1]
SCOPE = [1450, 1700]
DECADES = list(range(1450, 1700, 10))


def count_years(db: Path) -> tuple[dict, dict]:
    collections, confidence = {}, {}
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        for name, year, words, basis in con.execute(
            "SELECT collection, year, wordcount, date_confidence FROM texts "
            "WHERE in_core = 1 AND is_dup = 0"
        ):
            words = words or 0
            if not isinstance(words, int) or words < 0:
                raise ValueError(f"Invalid word count in {name}")
            c = collections.setdefault(name, {"words": 0, "texts": 0,
                "decade_words": [0] * len(DECADES), "undated_words": 0})
            c["words"] += words
            c["texts"] += 1
            if year is None:
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
        c = collections.setdefault(name, {"words": 0, "texts": 0,
            "decade_words": [0] * len(DECADES), "undated_words": 0})
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
                      "not a uniform chronology of composition or publication. Undated words are separate.",
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
