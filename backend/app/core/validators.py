"""Shared Pydantic field-normalization helpers used across schemas that accept
Gemini-generated numeric fields (which occasionally arrive currency-formatted,
e.g. "₹3,500" or "3500 INR" instead of a plain number)."""
import re

_CURRENCY_SYMBOLS = re.compile(r"[₹$€£]")
_CURRENCY_WORDS = re.compile(r"(?i)\b(INR|USD|EUR|GBP|RS\.?|RUPEES?|DOLLARS?)\b")
_NUMERIC_PATTERN = re.compile(r"-?\d+(\.\d+)?")


def coerce_numeric_cost(value: object) -> object:
    """Normalize occasionally currency-formatted numbers (e.g. "₹3,500",
    "3500 INR") into plain floats, without accepting non-numeric text such as
    "around 3500 rupees" or "three thousand". Only str/int/float pass through;
    anything else, or text that still contains non-numeric content after
    stripping known currency symbols/words/commas, is rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{value!r} is not a valid numeric cost")
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = _CURRENCY_SYMBOLS.sub("", value)
    cleaned = _CURRENCY_WORDS.sub("", cleaned)
    cleaned = cleaned.replace(",", "").strip()
    if not _NUMERIC_PATTERN.fullmatch(cleaned):
        raise ValueError(f"{value!r} is not a valid numeric cost")
    return float(cleaned)
