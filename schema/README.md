# Entry schema

`entry.schema.json` defines the format for every catalogue entry in `data/entries/`.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Name of the edition project or collection. |
| `url` | string (URI) | URL where the edition can be found. Must resolve. |
| `languages` | array of strings | Languages of the texts, as human-readable names. At least one. |
| `encoding` | string | Primary encoding format of the edition (see below). |
| `status` | string | One of: `active`, `archived`, `discontinued`. |
| `provenance` | string | One of: `submitted` (human contributor), `discovered` (automated search). |
| `date_added` | string (date) | Date the entry was added, in `YYYY-MM-DD` format. |

## Optional fields

| Field | Type | Description |
|-------|------|-------------|
| `data_url` | string (URI) | Where the edition's machine-readable files can be obtained: a repository, a download page or a dataset record. Give it whenever TEI or other XML files are publicly available. Requires `data_format`. |
| `data_format` | string | Format of the files at `data_url`, with the same vocabulary as `encoding`. Requires `data_url`. |
| `data_formats` | array of strings | All available download formats, including the primary `data_format`. Requires `data_url` and `data_format`. |
| `api_url` | string (URI) | Official API documentation for access to the texts. |
| `author` | string | Author of the source document(s). |
| `date` | string | Date or period of the source document(s). |
| `institution` | string | Institution or team behind the edition. |
| `words` | integer | Resource size in words within 1450–1700, before content deduplication. Harvested counts may cover only part of a resource; omit unknown counts. |
| `texts` | integer | Resource text instances within the recorded scope; not a unique-work count. |
| `corpus_statistics` | object | Original Renascor Corpus contribution after its duplicate filter: `snapshot`, `words`, `texts`. |
| `resource_statistics` | object | Source audit `url`, retrieval `date` and methodological `note` for a separate resource census. Takes precedence over the corpus harvested subset. |
| `count_basis` | string | `rq-retained-rows` includes every retained in-core row; `rq-retained-rows-and-staging` also restores missing IDs from checksum-locked source staging. Unstaged exclusions remain unknown. `sefaria-source-versions` counts dated Hebrew source versions from Sefaria's official exports. |
| `license` | string | Licence of the edition text, preferably an SPDX identifier such as `CC-BY-SA-4.0` or `CC0-1.0`; otherwise `Copyright`, `Custom terms`, `Mixed`, `Public domain` or `Not stated`. Separate from the catalogue metadata licence. |
| `license_url` | string (URI) | Publisher terms, dataset record or licence file supporting the text licence. |
| `license_note` | string | Scope and exceptions, including different rights for texts, annotation and images. |
| `region` | string | Geographic area covered. |
| `period` | string | Period covered by the corpus, e.g. `1550-1620`. |
| `years_active` | object | `{"start": 2015, "end": 2020}` or `{"start": 2015, "end": "ongoing"}`. |
| `notes` | string | Additional information. |
| `last_modified` | string (date) | Last modification of the resource as reported by its host (GitHub push, Zenodo update). |

## Controlled vocabularies

- **encoding** (and **data_format**): the richest publicly available text format. When a project offers several, the precedence is `tei` > `xml` > `json` > `html` > `wikitext` > `plain-text` > `markdown`. Internal encoding alone does not establish that the resource is publicly available in that format.
  - `tei`: TEI XML (P5, or P4/SGML for older editions)
  - `xml`: other XML, not TEI
  - `json`: structured text data in JSON
  - `html`: HTML pages
  - `wikitext`: wiki markup (e.g. Wikisource)
  - `plain-text`: plain text
  - `markdown`: Markdown, including dialects such as OpenITI mARkdown
  - `other`: anything else (e.g. TSV or CoNLL-U)
- **status**: `active` (online and maintained), `archived` (still online but no longer maintained), `discontinued` (no longer online; the URL may point to an archived copy)
- **provenance**: `submitted`, `discovered`

The encoding describes what the edition publishes, not how the text happens to be displayed or how a third party harvested it. Check the project's download links, repository files or documentation before choosing.

## Validation

Validate an entry locally (add `--check-url` to check that `url` and `data_url` resolve):

```bash
python scripts/validate_entry.py data/entries/your-file.json
```

Or validate all entries:

```bash
python scripts/validate_all.py
```
