"""Language labels used by the catalogue, independently of source classifications."""

REMOVED_LABELS = {"multilingual", "romance", "romance (other)"}
GREEK_LABELS = {"ancient greek", "modern greek"}
# Historical stages and varieties are counted under the modern language.
STAGE_LABELS = {
    "middle english": "English",
    "early modern english": "English",
    "old french": "French",
    "middle french": "French",
    "middle high german": "German",
    "early new high german": "German",
    "low german": "German",
    "middle low german": "German",
    "middle dutch": "Dutch",
    "old spanish": "Spanish",
}


def catalogue_languages(values):
    """Merge Greek varieties and historical stages, drop non-language labels and retain input order."""
    result = []
    for value in values:
        label = value.strip()
        key = label.casefold()
        if not label or key in REMOVED_LABELS:
            continue
        if key in GREEK_LABELS:
            label = "Greek"
        label = STAGE_LABELS.get(key, label)
        if label not in result:
            result.append(label)
    return result
