#!/usr/bin/env python3
"""Check for probable duplicate entries.

Flags entries that share the same URL, or whose titles are very similar.
Similarity is computed with difflib.SequenceMatcher (stdlib, no dependencies).

Usage:
    python scripts/check_duplicates.py [--entries-dir DIR] [--threshold 0.85]

Exit code 0 = no duplicates, 1 = duplicates found.
"""
from __future__ import annotations

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Deliberately shared pointer: entries for RQ collections with no verifiable
# project site all point to the same frozen release. Not duplicates.
SHARED_FALLBACK_URLS = [
    "https://github.com/pantagrueliste/rq-open-corpus/releases/tag/v2026.06-frozen",
]


def load_entries(entries_dir: Path) -> list[tuple[str, dict]]:
    entries = []
    for path in sorted(entries_dir.glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            entries.append((path.name, entry))
        except json.JSONDecodeError as e:
            print(f"Error: {path.name} is not valid JSON: {e}", file=sys.stderr)
    return entries


def normalise_url(url: str) -> str:
    """Normalise a URL for comparison: lowercase, strip trailing slash, remove www."""
    url = url.lower().strip()
    url = url.rstrip("/")
    url = url.replace("://www.", "://")
    return url


def similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def check_duplicates(
    entries: list[tuple[str, dict]], threshold: float = 0.85
) -> list[str]:
    """Return a list of duplicate warnings."""
    warnings = []

    # Check for identical URLs.
    url_to_files: dict[str, list[str]] = {}
    for filename, entry in entries:
        url = normalise_url(entry.get("url", ""))
        if url:
            url_to_files.setdefault(url, []).append(filename)

    for url, files in url_to_files.items():
        if len(files) > 1 and url not in SHARED_FALLBACK_URLS:
            warnings.append(
                f"Same URL ({url}) in multiple entries: {', '.join(files)}"
            )

    # Check for similar titles.
    titles = [(f, e.get("title", "")) for f, e in entries]
    for i, (file_a, title_a) in enumerate(titles):
        for file_b, title_b in titles[i + 1:]:
            if not title_a or not title_b:
                continue
            ratio = similarity(title_a, title_b)
            if ratio >= threshold:
                warnings.append(
                    f"Similar titles ({ratio:.0%} match): "
                    f"{file_a} ('{title_a}') and {file_b} ('{title_b}')"
                )

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries-dir", type=Path, default=REPO_ROOT / "data" / "entries")
    parser.add_argument("--threshold", type=float, default=0.85,
                        help="Title similarity threshold (0.0 to 1.0, default 0.85)")
    args = parser.parse_args()

    entries = load_entries(args.entries_dir)
    if not entries:
        print(f"Error: no entries found in {args.entries_dir}", file=sys.stderr)
        return 1

    print(f"Checking {len(entries)} entries for duplicates (threshold {args.threshold:.0%})...")

    warnings = check_duplicates(entries, args.threshold)
    if warnings:
        print(f"\nFound {len(warnings)} potential duplicate(s):")
        for w in warnings:
            print(f"  - {w}")
        return 1

    print("  No duplicates found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
