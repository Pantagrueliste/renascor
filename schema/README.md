# Entry schema

`entry.schema.json` defines the format for every catalogue entry in `data/entries/`.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Name of the edition project or collection. |
| `url` | string (URI) | URL where the edition can be found. Must resolve. |
| `languages` | array of strings | Languages of the texts, as human-readable names. At least one. |
| `encoding` | string | One of: `tei`, `html`, `markdown`, `other`. |
| `status` | string | One of: `active`, `archived`. |
| `provenance` | string | One of: `submitted` (human contributor), `discovered` (automated search). |
| `date_added` | string (date) | Date the entry was added, in `YYYY-MM-DD` format. |

## Optional fields

| Field | Type | Description |
|-------|------|-------------|
| `author` | string | Author of the source document(s). |
| `date` | string | Date or period of the source document(s). |
| `institution` | string | Institution or team behind the edition. |
| `words` | integer | Approximate corpus size in words. |
| `region` | string | Geographic area covered. |
| `period` | string | Period covered by the corpus. |
| `years_active` | object | `{"start": 2015, "end": 2020}` or `{"start": 2015, "end": "ongoing"}`. |
| `notes` | string | Additional information. |

## Controlled vocabularies

- **encoding**: `tei`, `html`, `markdown`, `other`
- **status**: `active`, `archived`
- **provenance**: `submitted`, `discovered`

## Validation

Validate an entry locally:

```bash
python scripts/validate_entry.py data/entries/your-file.json
```

Or validate all entries:

```bash
python scripts/validate_all.py
```
