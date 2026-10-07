# Contributing to Renascore

Thank you for helping to build this catalogue. There are two ways to contribute, and neither requires technical expertise.

## Option 1: Open an issue (recommended for most people)

Use the [new entry form](https://github.com/Pantagrueliste/renascore/issues/new?template=new-entry.yml).

The form asks for the essential details about a digital edition project. Fill in what you know; leave blank what you do not. A maintainer will review your submission, format it as a catalogue entry, and add it to the dataset.

## Option 2: Edit files directly

If you are comfortable with Git and JSON, you can add an entry yourself.

### Steps

1. Fork the repository.
2. Create a new file in `data/entries/` named after the project, for example `data/entries/textgrid-repository.json`. Use lowercase letters, digits, and hyphens only.
3. Write the entry as JSON. The required fields are defined in [`schema/entry.schema.json`](schema/entry.schema.json). You can copy an existing entry as a template.
4. Run the validation script locally:

   ```bash
   python scripts/validate_entry.py data/entries/your-file.json
   ```

5. Commit your change and open a pull request.

### What happens next

A GitHub Action automatically checks every pull request:

- validates the entry against the schema
- checks that the URL resolves
- flags probable duplicates (same URL or very similar title)

A human maintainer then reviews the entry and merges it.

## What we accept

We catalogue projects that provide digital editions of Renaissance-era written documents (roughly 1450 to 1700):

- **Manuscript editions** (transcriptions, diplomatic editions)
- **Printed works** (editions of early printed books)
- **Correspondence** (letters, diplomatic documents, archives)

We record the project, not individual texts. A project may contain one text or thousands.

## What we do not accept

- Page images or facsimiles only, with no text layer
- Raw, uncorrected OCR without editorial review
- Catalogues or bibliographies that contain no texts
- Projects outside the 1450 to 1700 window, unless the majority of their material falls within it

If you are unsure whether a project qualifies, submit it anyway and say so. Misclassification is easy to fix.

## Corrections

If you find an error in an existing entry, [open an issue](https://github.com/Pantagrueliste/renascore/issues/new?template=correction.yml) or propose a fix via pull request.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful, be constructive, and assume good faith.
