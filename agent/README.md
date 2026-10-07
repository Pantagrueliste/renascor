# Discovery agent

This directory contains the system prompt for the weekly discovery agent.

## How it works

1. **Schedule.** A GitHub Action (`.github/workflows/discover.yml`) runs every Monday at 06:00 UTC, and can be triggered manually.

2. **Prompt.** The script `scripts/discover.py` reads `discovery_prompt.md` and injects the list of existing catalogue entries (URLs and titles) into the `{EXISTING_ENTRIES}` placeholder. This tells the agent what is already catalogued, so it does not search for or return known projects.

3. **API call.** The script calls the Mistral API (`mistral-small-latest`) with the `web_search` tool enabled. The agent searches Zenodo, DARIAH, re3data, GitHub, and the general web.

4. **Output.** The agent returns a JSON array of candidates in the catalogue schema. The script validates each candidate against `schema/entry.schema.json`.

5. **Human review.** Candidates are **never** merged automatically. The script opens a GitHub issue labelled `discovered` containing the proposed entries. A human reviews each candidate before it enters the catalogue.

## Cost control

- **Model:** `mistral-small-latest` ($0.10/M input tokens, $0.30/M output tokens).
- **Hard cap:** 1 API call per run (enforced in `scripts/discover.py`).
- **Expected cost:** under $0.01 per run.
- **Token logging:** The script logs input/output token counts and estimated cost to the workflow log.

## Editing the prompt

Edit `discovery_prompt.md` directly. No code changes are needed. The prompt defines:

- the project context
- relevance criteria (digital edition, Renaissance-era, stable URL, not already catalogued)
- where to search
- the output format (exact JSON schema)
- how to report uncertainty

## Secrets

The workflow requires two secrets:

- `MISTRAL_API_KEY`: your Mistral API key.
- `GITHUB_TOKEN`: automatically provided by GitHub Actions (used to open issues).

Set `MISTRAL_API_KEY` in the repository settings under Settings > Secrets and variables > Actions.
