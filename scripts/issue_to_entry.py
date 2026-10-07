#!/usr/bin/env python3
"""Convert a GitHub issue form submission into a catalogue entry JSON file.

Maintainers use this to process submissions from the 'Propose a new entry'
issue form. The script parses the issue body, maps the form fields to the
entry schema, and writes a JSON file to data/entries/.

Usage:
    python scripts/issue_to_entry.py --issue-file issue.md --output-dir data/entries
    python scripts/issue_to_entry.py --issue-number 42 --repo Pantagrueliste/renascore

The second form requires the GITHUB_TOKEN environment variable.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Map issue form encoding options to schema enum values.
ENCODING_MAP = {
    "tei xml": "tei",
    "html": "html",
    "markdown": "markdown",
    "other": "other",
}

# Map issue form status options to schema enum values.
STATUS_MAP = {
    "active (currently maintained, updated, or accepting contributions)": "active",
    "archived (no longer maintained, but still online)": "archived",
}


def parse_issue_body(body: str) -> dict:
    """Parse a GitHub issue form body into a dictionary of field values."""
    fields = {}
    # GitHub issue forms use ### Field Name headers followed by the value.
    pattern = re.compile(r"^###\s+(.+?)\s*\n+(.+?)(?=\n###|\Z)", re.MULTILINE | re.DOTALL)
    for match in pattern.finditer(body):
        name = match.group(1).strip().lower()
        value = match.group(2).strip()
        # Remove "_No response_" placeholders.
        if value.lower() in ("_no response_", "n/a", ""):
            value = ""
        fields[name] = value
    return fields


def slugify(title: str) -> str:
    """Convert a title to a filename slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    slug = slug.strip("-")
    return slug or "untitled"


def fields_to_entry(fields: dict, submitted_by: str = "") -> dict:
    """Convert parsed issue form fields to a catalogue entry."""
    # Parse languages: comma-separated string to list.
    languages_raw = fields.get("language(s)", "")
    languages = [lang.strip() for lang in languages_raw.split(",") if lang.strip()]

    # Map encoding.
    encoding_raw = fields.get("encoding format", "").lower()
    encoding = ENCODING_MAP.get(encoding_raw, "other")

    # Map status.
    status_raw = fields.get("is the project active?", "").lower()
    status = STATUS_MAP.get(status_raw, "active")
    if "not sure" in status_raw:
        status = "active"  # Default to active if unsure; maintainer can correct.

    # Parse years active.
    years_raw = fields.get("years active", "")
    years_active = None
    if years_raw:
        years_match = re.match(r"(\d{4})\s*[-–]\s*(\d{4}|ongoing)", years_raw, re.IGNORECASE)
        if years_match:
            years_active = {
                "start": int(years_match.group(1)),
                "end": years_match.group(2).lower(),
            }

    # Parse words.
    words_raw = fields.get("approximate size (words)", "")
    words = None
    if words_raw:
        words_match = re.search(r"\d[\d,]*", words_raw)
        if words_match:
            words = int(words_match.group(0).replace(",", ""))

    entry = {
        "title": fields.get("project name", "Untitled"),
        "url": fields.get("url", ""),
        "languages": languages or ["Unknown"],
        "encoding": encoding,
        "status": status,
        "provenance": "submitted",
        "date_added": date.today().isoformat(),
    }

    # Optional fields.
    if fields.get("institution or team"):
        entry["institution"] = fields["institution or team"]
    if fields.get("period covered"):
        entry["period"] = fields["period covered"]
    if fields.get("geographic area"):
        entry["region"] = fields["geographic area"]
    if words is not None:
        entry["words"] = words
    if years_active:
        entry["years_active"] = years_active
    if fields.get("anything else we should know"):
        entry["notes"] = fields["anything else we should know"]

    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-file", type=Path,
                        help="Path to a file containing the issue body")
    parser.add_argument("--issue-number", type=int,
                        help="Issue number (requires GITHUB_TOKEN and --repo)")
    parser.add_argument("--repo", default="Pantagrueliste/renascore",
                        help="Repository in owner/name format")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "data" / "entries",
                        help="Directory to write the entry JSON file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the entry JSON without writing a file")
    args = parser.parse_args()

    if args.issue_file:
        body = args.issue_file.read_text(encoding="utf-8")
    elif args.issue_number:
        import os
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
            return 1
        result = subprocess.run(
            ["gh", "issue", "view", str(args.issue_number), "--repo", args.repo, "--json", "body"],
            capture_output=True, text=True, env={**os.environ, "GH_TOKEN": token},
        )
        if result.returncode != 0:
            print(f"Error fetching issue: {result.stderr}", file=sys.stderr)
            return 1
        body = json.loads(result.stdout)["body"]
    else:
        print("Error: provide --issue-file or --issue-number", file=sys.stderr)
        return 1

    fields = parse_issue_body(body)
    if not fields:
        print("Error: could not parse issue body. Is this a form submission?", file=sys.stderr)
        return 1

    entry = fields_to_entry(fields)

    if args.dry_run:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0

    # Generate filename from title.
    slug = slugify(entry["title"])
    out_path = args.output_dir / f"{slug}.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    out_path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote entry: {out_path}")
    print(f"  Title: {entry['title']}")
    print(f"  URL: {entry['url']}")
    print(f"  Languages: {', '.join(entry['languages'])}")
    print(f"  Encoding: {entry['encoding']}, Status: {entry['status']}")
    print()
    print("Next steps:")
    print(f"  1. Validate: python scripts/validate_entry.py {out_path} --check-url")
    print(f"  2. Review and edit the file as needed")
    print(f"  3. Rebuild site: python scripts/build_site.py")
    print(f"  4. Commit and close the issue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
