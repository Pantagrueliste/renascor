#!/usr/bin/env python3
"""Weekly discovery: call a Mistral agent to find new digital edition projects.

The agent searches the web (Zenodo, DARIAH, re3data, GitHub, general web) for
new digital editions of Renaissance-era texts that are not yet in the catalogue.
Candidates are never merged automatically. This script opens a GitHub issue
containing the proposed entries, labelled 'discovered', for human review.

Usage:
    python scripts/discover.py --api-key $MISTRAL_API_KEY
    python scripts/discover.py --dry-run   # print candidates without opening an issue

Requires:
    - MISTRAL_API_KEY environment variable (or --api-key)
    - GITHUB_TOKEN environment variable (for opening issues; optional with --dry-run)
    - mistralai Python package: pip install mistralai
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "agent" / "discovery_prompt.md"
ENTRIES_DIR = REPO_ROOT / "data" / "entries"
SCHEMA_PATH = REPO_ROOT / "schema" / "entry.schema.json"

# Hard cap on API calls per run (cost control).
MAX_API_CALLS = 1

# Model choice: Mistral Large 4 (v26.10, public preview, ID mistral-large-4-0).
# Web search is a built-in tool, so no extra cost for the tool itself.
# Pricing is the current preview rate (list price: $1.36/M input, $4.18/M output).
MODEL = "mistral-large-4-0"

# Approximate pricing (USD per million tokens) for cost logging.
PRICING = {
    "input_per_million": 0.68,
    "output_per_million": 2.09,
}


def load_existing_entries(entries_dir: Path) -> list[dict]:
    """Load all existing entries to pass to the agent (URLs and titles)."""
    entries = []
    for path in sorted(entries_dir.glob("*.json")):
        try:
            entries.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return entries


def format_existing_for_prompt(entries: list[dict]) -> str:
    """Format existing entries as a list for the prompt."""
    lines = []
    for e in entries:
        lines.append(f"- {e.get('title', '?')} — {e.get('url', '?')}")
    return "\n".join(lines) if lines else "(none yet)"


def load_prompt(existing_entries: list[dict]) -> str:
    """Load the discovery prompt and inject the list of existing entries."""
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    existing = format_existing_for_prompt(existing_entries)
    return prompt.replace("{EXISTING_ENTRIES}", existing)


def call_agent(api_key: str, system_prompt: str, max_calls: int = MAX_API_CALLS) -> tuple[list[dict], dict]:
    """Call the Mistral API with web search tool. Returns (candidates, usage)."""
    try:
        from mistralai import Mistral
    except ImportError:
        print("Error: mistralai not installed. Run: pip install mistralai", file=sys.stderr)
        sys.exit(2)

    client = Mistral(api_key=api_key)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Run your weekly discovery search. Search Zenodo, DARIAH, re3data, "
                "GitHub, and the general web for new digital edition projects of "
                "Renaissance-era texts (1450-1700) that are not in the catalogue. "
                "Return up to 10 candidates in the exact JSON format specified in "
                "your instructions. If you find nothing new, return an empty array."
            ),
        },
    ]

    response = client.chat.complete(
        model=MODEL,
        messages=messages,
        tools=[{"type": "web_search"}],
        max_tokens=8192,
        temperature=0.3,
    )

    # Extract usage for cost logging.
    usage = {
        "input_tokens": response.usage.prompt_tokens if response.usage else 0,
        "output_tokens": response.usage.completion_tokens if response.usage else 0,
    }

    # Parse the response content as JSON.
    content = response.choices[0].message.content
    if not content:
        return [], usage

    # Strip markdown code blocks if present (agent sometimes wraps JSON).
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    try:
        candidates = json.loads(content)
        if not isinstance(candidates, list):
            print(f"Warning: agent returned non-array JSON: {type(candidates)}", file=sys.stderr)
            return [], usage
        return candidates, usage
    except json.JSONDecodeError as e:
        print(f"Warning: could not parse agent response as JSON: {e}", file=sys.stderr)
        print(f"Raw response (first 500 chars): {content[:500]}", file=sys.stderr)
        return [], usage


def estimate_cost(usage: dict) -> float:
    """Estimate cost in USD from token usage."""
    input_cost = usage["input_tokens"] / 1_000_000 * PRICING["input_per_million"]
    output_cost = usage["output_tokens"] / 1_000_000 * PRICING["output_per_million"]
    return input_cost + output_cost


def candidate_to_entry(candidate: dict) -> dict:
    """Convert an agent candidate to a catalogue entry (add provenance and date)."""
    entry = {
        "title": candidate.get("title", "Untitled"),
        "url": candidate.get("url", ""),
        "languages": candidate.get("languages", ["Unknown"]),
        "encoding": candidate.get("encoding", "other"),
        "status": candidate.get("status", "active"),
        "provenance": "discovered",
        "date_added": date.today().isoformat(),
    }
    # Optional fields.
    for field in ["institution", "period", "region", "words", "years_active", "notes"]:
        if candidate.get(field) is not None:
            entry[field] = candidate[field]
    # Store the justification and source URL in notes if not already present.
    extra = []
    if candidate.get("justification"):
        extra.append(f"Justification: {candidate['justification']}")
    if candidate.get("source_url"):
        extra.append(f"Found at: {candidate['source_url']}")
    if extra:
        existing_notes = entry.get("notes", "")
        entry["notes"] = (existing_notes + "\n\n" + "\n".join(extra)).strip()
    return entry


def validate_candidates(candidates: list[dict], schema_path: Path) -> tuple[list[dict], list[str]]:
    """Validate candidates against the schema. Returns (valid_entries, errors)."""
    try:
        import jsonschema
    except ImportError:
        print("Warning: jsonschema not installed; skipping validation", file=sys.stderr)
        return [candidate_to_entry(c) for c in candidates], []

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    valid = []
    errors = []
    for i, candidate in enumerate(candidates):
        entry = candidate_to_entry(candidate)
        errs = list(validator.iter_errors(entry))
        if errs:
            for e in errs:
                path = "/".join(str(p) for p in e.absolute_path) or "(root)"
                errors.append(f"Candidate {i} ({entry.get('title', '?')}): {path}: {e.message}")
        else:
            valid.append(entry)
    return valid, errors


def open_issue(entries: list[dict], cost: float, usage: dict) -> str | None:
    """Open a GitHub issue with the proposed entries. Returns the issue URL."""
    if not entries:
        return None

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set; cannot open issue", file=sys.stderr)
        return None

    # Build the issue body.
    lines = [
        "## Discovered candidates",
        "",
        f"The weekly discovery agent found **{len(entries)}** new candidate(s).",
        "",
        f"**Estimated cost:** ${cost:.4f} "
        f"({usage['input_tokens']:,} input tokens, {usage['output_tokens']:,} output tokens)",
        "",
        "These candidates are **not yet in the catalogue**. A human must review each one.",
        "",
        "---",
        "",
    ]
    for i, entry in enumerate(entries, 1):
        lines.extend([
            f"### {i}. {entry['title']}",
            "",
            f"- **URL:** {entry['url']}",
            f"- **Languages:** {', '.join(entry.get('languages', []))}",
            f"- **Encoding:** {entry['encoding']}",
            f"- **Status:** {entry['status']}",
        ])
        if entry.get("institution"):
            lines.append(f"- **Institution:** {entry['institution']}")
        if entry.get("period"):
            lines.append(f"- **Period:** {entry['period']}")
        if entry.get("region"):
            lines.append(f"- **Region:** {entry['region']}")
        if entry.get("words"):
            lines.append(f"- **Words:** {entry['words']:,}")
        if entry.get("notes"):
            lines.append(f"- **Notes:** {entry['notes']}")
        lines.extend([
            "",
            "**Proposed entry JSON:**",
            "",
            "```json",
            json.dumps(entry, indent=2, ensure_ascii=False),
            "```",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## Review checklist",
        "",
        "For each candidate:",
        "- [ ] The URL resolves and leads to a real project",
        "- [ ] The project provides digital editions (not just page images)",
        "- [ ] The source material is roughly 1450-1700",
        "- [ ] The entry is not a duplicate of an existing catalogue entry",
        "- [ ] The metadata (languages, encoding, status) is accurate",
        "",
        "To accept a candidate: add the JSON to `data/entries/` as a new file, "
        "run `python scripts/build_site.py`, and commit.",
    ])

    body = "\n".join(lines)
    title = f"[discovered] {len(entries)} new candidate(s) — {date.today().isoformat()}"

    # Use gh CLI to create the issue.
    result = subprocess.run(
        [
            "gh", "issue", "create",
            "--title", title,
            "--body", body,
            "--label", "discovered,status:needs-review",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "GH_TOKEN": token},
    )
    if result.returncode != 0:
        print(f"Error creating issue: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=os.environ.get("MISTRAL_API_KEY"),
                        help="Mistral API key (or set MISTRAL_API_KEY)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print candidates without opening an issue")
    parser.add_argument("--max-calls", type=int, default=MAX_API_CALLS,
                        help=f"Maximum API calls per run (default: {MAX_API_CALLS})")
    args = parser.parse_args()

    if not args.api_key:
        print("Error: MISTRAL_API_KEY not set. Provide --api-key or set the environment variable.",
              file=sys.stderr)
        return 1

    # Load existing entries.
    existing = load_existing_entries(ENTRIES_DIR)
    print(f"Loaded {len(existing)} existing entries.")

    # Build the prompt.
    system_prompt = load_prompt(existing)

    # Call the agent.
    print(f"Calling Mistral agent (model: {MODEL}, max calls: {args.max_calls})...")
    candidates, usage = call_agent(args.api_key, system_prompt, args.max_calls)

    cost = estimate_cost(usage)
    print(f"\nAgent returned {len(candidates)} candidate(s).")
    print(f"Usage: {usage['input_tokens']:,} input tokens, "
          f"{usage['output_tokens']:,} output tokens")
    print(f"Estimated cost: ${cost:.4f}")

    if not candidates:
        print("No new candidates found.")
        return 0

    # Validate candidates.
    print("\nValidating candidates against schema...")
    valid_entries, errors = validate_candidates(candidates, SCHEMA_PATH)
    if errors:
        print(f"Validation errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    print(f"Valid candidates: {len(valid_entries)} / {len(candidates)}")

    if not valid_entries:
        print("No valid candidates after validation.")
        return 1

    # Dry run: print and exit.
    if args.dry_run:
        print("\n--- DRY RUN: candidates ---")
        for entry in valid_entries:
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            print()
        return 0

    # Open an issue with the candidates.
    print("\nOpening GitHub issue with candidates...")
    issue_url = open_issue(valid_entries, cost, usage)
    if issue_url:
        print(f"Issue created: {issue_url}")
    else:
        print("Failed to create issue. Candidates were:")
        for entry in valid_entries:
            print(json.dumps(entry, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
