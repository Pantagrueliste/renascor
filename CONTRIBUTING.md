# Contributing to Renascor

Thank you for helping to build this catalogue. There are two ways to contribute, and neither requires technical expertise.

## Option 1: Open an issue (recommended for most people)

Use the [new entry form](https://github.com/Pantagrueliste/renascor/issues/new?template=new-entry.yml).

The form asks for the essential details about a digital edition project. Fill in what you know; leave blank what you do not. A maintainer will review your submission, format it as a catalogue entry, and add it to the dataset.

## Option 2: Edit files directly

If you are comfortable with Git and JSON, you can add an entry yourself.

### Steps

1. Fork the repository.
2. Create a new file in `data/entries/` named after the project, for example `data/entries/textgrid-repository.json`. Use lowercase letters, digits, and hyphens only.
3. Write the entry as JSON. The required fields are defined in [`schema/entry.schema.json`](schema/entry.schema.json) and explained in [`schema/README.md`](schema/README.md). You can copy an existing entry as a template. If the edition's TEI XML (or other machine-readable files) can be downloaded, give that address in `data_url` and the files' format in `data_format`.
4. Run the validation script locally:

   ```bash
   python scripts/validate_entry.py data/entries/your-file.json
   ```

5. Commit your change and open a pull request.

### What happens next

A GitHub Action automatically checks every pull request:

- validates the entry against the schema
- checks that the URLs resolve (the edition's `url` and, if given, its `data_url`)
- flags probable duplicates (same URL or very similar title)

A human maintainer then reviews the entry and merges it.

## What we accept

We catalogue projects that provide digital editions of Renaissance-era written documents (roughly 1450 to 1700):

- **Manuscript editions** (transcriptions, diplomatic editions)
- **Printed works** (editions of early printed books)
- **Correspondence** (letters, diplomatic documents, archives)

We record the project, not individual texts. A project may contain one text or thousands.

### The inclusion rule: new, countable text

A resource is added only if **both** conditions hold:

1. **The number of words it contributes can be counted exactly.** Its full texts must be obtainable (downloadable files, a repository, a dataset record) so that they can be counted. A figure quoted on a website is not enough.
2. **Its texts are verifiably not already in the catalogue.** It must not be a mirror, re-harvest, anthology or aggregation of projects that are already listed.

If either condition fails, the resource is not added, however useful it is. Rejected resources are listed in [`data/rejected.json`](data/rejected.json) with the reason.

## What we do not accept

- Page images or facsimiles only, with no text layer
- Raw, uncorrected OCR without editorial review
- Catalogues or bibliographies that contain no texts
- Portals, aggregators and federated search services that point to, or republish, other projects' texts
- Projects outside the 1450 to 1700 window, unless the majority of their material falls within it

If you are unsure whether a project qualifies, submit it anyway and say so. Misclassification is easy to fix.

## Corrections

If you find an error in an existing entry, [open an issue](https://github.com/Pantagrueliste/renascor/issues/new?template=correction.yml) or propose a fix via pull request.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful, be constructive, and assume good faith.
