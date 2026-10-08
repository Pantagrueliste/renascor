#!/usr/bin/env python3
"""Weekly discovery: call a Mistral agent to find new digital edition projects.

The agent searches the web (Zenodo, DARIAH, re3data, GitHub, general web) for
new digital editions of Renaissance-era texts that are not yet in the catalogue.
Candidates are never merged automatically. This script opens a pull request
containing the proposed entries (one JSON file per candidate in data/entries/),
labelled 'discovered', for human review and merge.

Usage:
    python scripts/discover.py --api-key $MISTRAL_API_KEY
    python scripts/discover.py --dry-run   # print candidates without opening a PR

Requires:
    - MISTRAL_API_KEY environment variable (or --api-key)
    - GITHUB_TOKEN environment variable (for opening the PR; optional with --dry-run)
    - git and gh CLI available
    - jsonschema Python package (for candidate validation)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
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


def collect_text_chunks(node) -> list:
    """Deep-collect the text chunks of an Agents-API response."""
    texts = []
    stack = [node]
    while stack:
        n = stack.pop(0)  # FIFO: text chunks are joined in document order
        if isinstance(n, dict):
            if n.get("type") == "text" and isinstance(n.get("text"), str):
                texts.append(n["text"])
            stack.extend(n.values())
        elif isinstance(n, list):
            stack.extend(n)
    return texts


def collect_usage(node) -> dict:
    """First usage object found in the response (token counts)."""
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            u = n.get("usage")
            if isinstance(u, dict):
                return {
                    "input_tokens": u.get("prompt_tokens", 0) or 0,
                    "output_tokens": u.get("completion_tokens", 0) or 0,
                }
            stack.extend(n.values())
        elif isinstance(n, list):
            stack.extend(n)
    return {"input_tokens": 0, "output_tokens": 0}


def mistral_post(path: str, body: dict, api_key: str) -> dict:
    """POST a JSON body to the Mistral API and return the parsed response."""
    req = urllib.request.Request(
        f"https://api.mistral.ai{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "renascor-discovery/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Mistral API error {e.code} on {path}: {e.read()[:300]}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Mistral API request failed ({path}): {e}", file=sys.stderr)
        sys.exit(3)


def call_agent(api_key: str, system_prompt: str, max_calls: int = MAX_API_CALLS) -> tuple[list[dict], dict]:
    """Run one discovery conversation with web search enabled.

    The web_search tool lives on the Agents/Conversations API (it is
    rejected by /v1/chat/completions). We create a one-off agent carrying
    the system prompt, run a single conversation, extract the text chunks,
    and delete the agent afterwards.
    """
    agent = mistral_post("/v1/agents", {
        "model": MODEL,
        "name": "renascor-discovery",
        "description": "Weekly discovery of digital edition projects for the "
                       "Renascor catalogue.",
        "instructions": system_prompt,
        "tools": [{"type": "web_search"}],
        "completion_args": {"temperature": 0.3, "max_tokens": 8192},
    }, api_key)
    agent_id = agent.get("id") or agent.get("agent_id")

    conversation = mistral_post("/v1/conversations", {
        "agent_id": agent_id,
        "inputs": [{
            "role": "user",
            "content": (
                "Run your weekly discovery search. Search Zenodo, DARIAH, re3data, "
                "GitHub, and the general web for new digital edition projects of "
                "Renaissance-era texts (1450-1700) that are not in the catalogue. "
                "Return up to 10 candidates in the exact JSON format specified in "
                "your instructions. If you find nothing new, return an empty array."
            ),
        }],
    }, api_key)

    # Clean up the one-off agent (best effort).
    try:
        del_req = urllib.request.Request(
            f"https://api.mistral.ai/v1/agents/{agent_id}",
            headers={"Authorization": f"Bearer {api_key}",
                     "User-Agent": "renascor-discovery/1.0"},
            method="DELETE",
        )
        urllib.request.urlopen(del_req, timeout=60)
    except Exception:
        pass

    usage = collect_usage(conversation)
    content = "".join(collect_text_chunks(conversation))
    if not content.strip():
        return [], usage

    # Strip markdown code blocks if present (agents sometimes wrap JSON).
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


def slugify(name: str) -> str:
    """File name (without .json) for an entry, from its title."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def normalize_url(url: str) -> str:
    """Loose canonical form of a URL, for duplicate detection."""
    url = (url or "").strip().lower().rstrip("/")
    return re.sub(r"^https?://", "", url)


def deduplicate(candidates: list[dict], existing: list[dict]) -> tuple[list[dict], list[str]]:
    """Drop candidates whose URL is already in the catalogue. Returns (kept, dropped)."""
    known = {normalize_url(e.get("url", "")) for e in existing}
    kept, dropped = [], []
    for c in candidates:
        if normalize_url(c.get("url", "")) in known:
            dropped.append(c.get("title", "?"))
        else:
            kept.append(c)
    return kept, dropped


def build_pr_body(entries: list[dict], cost: float, usage: dict) -> str:
    lines = [
        "## Discovered candidates",
        "",
        f"The weekly discovery agent found **{len(entries)}** new candidate(s).",
        "",
        f"**Estimated cost:** ${cost:.4f} "
        f"({usage['input_tokens']:,} input tokens, {usage['output_tokens']:,} output tokens)",
        "",
        "These candidates are **not yet in the catalogue**. Merging this pull "
        "request adds the candidate JSON files to `data/entries/`; every "
        "candidate should be reviewed first.",
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
            f"- **Encoding:** {entry.get('encoding', 'other')}",
            f"- **Status:** {entry.get('status', 'active')}",
            f"- **File:** `data/entries/{entry.get('_file')}`",
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
        lines.append("")

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
        "To accept a candidate: merge the pull request. To reject one: delete "
        "its JSON file from the branch and commit (or edit it in place).",
    ])

    return "\n".join(lines)


def ensure_labels(labels: list[str], token: str) -> None:
    """Create the triage labels if they do not exist yet (idempotent)."""
    colors = {"discovered": "0e8a16", "status:needs-review": "fbca04"}
    for label in labels:
        result = subprocess.run(
            ["gh", "label", "create", label,
             "--color", colors.get(label, "ededed")],
            capture_output=True,
            text=True,
            env={**os.environ, "GH_TOKEN": token},
        )
        if result.returncode != 0 and "already exists" not in result.stderr + result.stdout:
            print(f"Warning: could not create label '{label}': "
                  f"{result.stderr.strip()}", file=sys.stderr)


def open_pull_request(entries: list[dict], cost: float, usage: dict) -> str | None:
    """Commit the candidate entries on a branch and open a pull request.

    Returns the PR URL, or None on failure.
    """
    if not entries:
        return None

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set; cannot open pull request", file=sys.stderr)
        return None

    repo = os.environ.get("GITHUB_REPOSITORY", "Pantagrueliste/renascor")
    branch = f"discovered/{date.today().isoformat()}"
    today = date.today().isoformat()
    title = f"[discovered] {len(entries)} new candidate(s) — {today}"
    body = build_pr_body(entries, cost, usage)

    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], capture_output=True, text=True,
                                env={**os.environ})
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
        return result.stdout.strip()

    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("checkout", "-B", branch)

    files = []
    for entry in entries:
        slug = entry.pop("_file", None) or slugify(entry["title"])
        path = ENTRIES_DIR / f"{slug}.json"
        path.write_text(
            json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        files.append("data/entries/" + f"{slug}.json")

    git("add", *files)
    git("commit", "-m", f"Add {len(entries)} candidate edition(s) discovered on {today}")

    remote = f"https://x-access-token:{token}@github.com/{repo}.git"
    try:
        git("push", remote, branch)
    except RuntimeError as e:
        if "already exists" not in str(e):
            raise
        # Branch already on the remote (prior run today): pick a fresh name.
        import datetime as _dt
        branch = (f"discovered/{today}-"
                  f"{_dt.datetime.now().strftime('%H%M')}")
        git("checkout", "-B", branch)
        git("push", remote, branch)

    ensure_labels(["discovered", "status:needs-review"], token)
    result = subprocess.run(
        [
            "gh", "pr", "create",
            "--repo", repo,
            "--base", "main",
            "--head", branch,
            "--title", title,
            "--body", body,
            "--label", "discovered,status:needs-review",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "GH_TOKEN": token},
    )
    if result.returncode != 0:
        print(f"Error creating pull request: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=os.environ.get("MISTRAL_API_KEY"),
                        help="Mistral API key (or set MISTRAL_API_KEY)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print candidates without opening a pull request")
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

    # Drop candidates whose URL is already catalogued.
    valid_entries, known_dropped = deduplicate(valid_entries, existing)
    for title in known_dropped:
        print(f"Dropped as duplicate URL of an existing entry: {title}")
    if not valid_entries:
        print("No new candidates after duplicate check.")
        return 0

    # Give each entry its target file name, shown in the PR body.
    for entry in valid_entries:
        entry["_file"] = slugify(entry["title"]) + ".json"

    # Dry run: print and exit.
    if args.dry_run:
        print("\n--- DRY RUN: candidates ---")
        for entry in valid_entries:
            print(json.dumps({k: v for k, v in entry.items() if k != '_file'},
                             indent=2, ensure_ascii=False))
            print()
        return 0

    # Open a pull request with the candidates.
    print("\nOpening pull request with candidates...")
    pr_url = open_pull_request(valid_entries, cost, usage)
    if pr_url:
        print(f"Pull request created: {pr_url}")
    else:
        print("Failed to create pull request. Candidates were:")
        for entry in valid_entries:
            print(json.dumps({k: v for k, v in entry.items() if k != '_file'},
                             indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
