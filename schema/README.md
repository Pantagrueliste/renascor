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
| `author` | string | Author of the source document(s). |
| `date` | string | Date or period of the source document(s). |
| `institution` | string | Institution or team behind the edition. |
| `words` | integer | Approximate corpus size in words. |
| `texts` | integer | Approximate number of transcribed texts. |
| `region` | string | Geographic area covered. |
| `period` | string | Period covered by the corpus, e.g. `1550-1620`. |
| `years_active` | object | `{"start": 2015, "end": 2020}` or `{"start": 2015, "end": "ongoing"}`. |
| `notes` | string | Additional information. |
| `last_modified` | string (date) | Last modification of the resource as reported by its host (GitHub push, Zenodo update). |

## Controlled vocabularies

- **encoding** (and **data_format**): the richest format in which the project publishes or documents its text. When a project offers several, the precedence is `tei` > `xml` > `html` > `wikitext` > `plain-text` > `markdown`.
  - `tei`: TEI XML (P5, or P4/SGML for older editions)
  - `xml`: other XML, not TEI
  - `html`: HTML pages
  - `wikitext`: wiki markup (e.g. Wikisource)
  - `plain-text`: plain text
  - `markdown`: Markdown, including dialects such as OpenITI mARkdown
  - `other`: anything else (e.g. TSV, CoNLL-U, JSON)
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
