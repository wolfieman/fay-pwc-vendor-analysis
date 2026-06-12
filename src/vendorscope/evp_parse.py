"""Pure parser: the eVP results page's embedded dataset to text records.

The results page renders the entire filtered dataset into an inline script
variable, ``var data = "[...]"``, HTML-entity-encoded. Extraction is a DOTALL
regex over that variable, then entity unescape, then JSON decode. A missing
variable means a template change and raises ``EmbeddedDataError`` (the raw bytes
are already frozen by the client, so the failure is forensically recoverable).

Every value is stringified on the way out so the rest of the pipeline runs in
text mode: the ten trade flags are JSON booleans and become ``'True'`` /
``'False'`` via ``str()`` (REQ-07); ``None`` becomes the empty string.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import html
import json
import re

DATA_RE = re.compile(r'var\s+data\s*=\s*"(\[.*?\])"\s*;?', re.S)


class EmbeddedDataError(ValueError):
    """The inline ``var data`` dataset variable was not found (template change)."""


def _stringify(value: object) -> str:
    if isinstance(value, bool):  # checked before str/int: bool is an int subclass
        return str(value)
    if value is None:
        return ""
    return str(value)


def parse_records(page: str) -> list[dict[str, str]]:
    """Decode the embedded dataset into a list of all-string records."""
    match = DATA_RE.search(page)
    if match is None:
        raise EmbeddedDataError("inline 'var data' dataset variable not found")
    decoded = json.loads(html.unescape(match.group(1)))
    return [
        {key: _stringify(value) for key, value in record.items()} for record in decoded
    ]
