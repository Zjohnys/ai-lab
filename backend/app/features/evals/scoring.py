"""Turn a raw model answer into a label, and record how well it followed the format."""

import json
import re
import unicodedata

from pydantic import BaseModel

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)
_FIRST_OBJECT = re.compile(r"\{.*?\}", re.DOTALL)


class ParsedOutput(BaseModel):
    strict_json: bool
    """The whole answer is exactly one JSON object with a string "category"."""
    json_found: bool
    """A JSON object with a string "category" was found somewhere in the answer."""
    label: str | None
    """The normalized category, or None if no JSON was found."""
    label_valid: bool
    """The normalized category is one of the allowed labels."""


def normalize_label(text: str) -> str:
    """Lowercase, trim and drop accents: 'Segurança ' -> 'seguranca'.

    This is a scoring decision, and it is lenient on purpose: the metric is about
    picking the right category, not spelling it. strict_json measures the format.
    """
    decomposed = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _category_from(candidate: str) -> str | None:
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and isinstance(data.get("category"), str):
        return data["category"]
    return None


def parse_output(text: str, labels: list[str]) -> ParsedOutput:
    stripped = text.strip()
    category = _category_from(stripped)
    strict = category is not None

    if category is None:
        fenced = _FENCE.match(stripped)
        if fenced:
            category = _category_from(fenced.group(1))
    if category is None:
        for match in _FIRST_OBJECT.finditer(stripped):
            category = _category_from(match.group(0))
            if category is not None:
                break

    if category is None:
        return ParsedOutput(strict_json=False, json_found=False, label=None, label_valid=False)
    label = normalize_label(category)
    return ParsedOutput(
        strict_json=strict, json_found=True, label=label, label_valid=label in labels
    )
