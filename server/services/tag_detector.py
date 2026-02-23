"""
Tag detection service.
Extracts, normalises, and expands tag numbers from raw document text.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DetectedTag:
    raw_text: str
    tag_number: str
    is_shorthand: bool = False
    shorthand_expansion: list[str] = field(default_factory=list)
    page_number: Optional[int] = None
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Full tag:  [opt project prefix]-[unit]-[type]-[seq][opt suffix]
#   e.g.  10-P-101A,  ABC-20-FT-1001,  20-XV-2001
FULL_TAG_RE = re.compile(
    r'\b(?:[A-Z]{1,6}-)?(\d{1,3}-[A-Z]{1,5}-\d{1,5}[A-Z]?)\b'
)

# Shorthand multi-suffix:  10-P-101A/B/C  or  P-101A/B
MULTI_SUFFIX_RE = re.compile(
    r'\b(\d{1,3}-[A-Z]{1,5}-\d{1,5})([A-Z])(?:/([A-Z]))+\b'
)

# Shorthand range:  P-101 to 105  |  10-FT-1001-1005  |  FT-1001 to 1005
RANGE_RE = re.compile(
    r'\b(\d{1,3}-[A-Z]{1,5}-)(\d{1,5})\s*(?:to|–|-)\s*(\d{1,5})\b',
    re.IGNORECASE,
)

# Detect prefix context lines like "All tags prefixed with 10-"
PREFIX_CONTEXT_RE = re.compile(
    r'(?:all\s+tags?\s+(?:are\s+)?prefixed?\s+with|prefix[:\s]+)\s*([A-Z0-9]{1,6}-)',
    re.IGNORECASE,
)

# Short partial tag (type + number only), used after a prefix context is found
PARTIAL_TAG_RE = re.compile(
    r'\b([A-Z]{1,5}-\d{1,5}[A-Z]?)\b'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(tag: str) -> str:
    """Normalise tag to uppercase and strip surrounding punctuation."""
    return tag.strip().upper().strip(".,;:()")


def _expand_multi_suffix(match_text: str) -> list[str]:
    """P-101A/B/C → [P-101A, P-101B, P-101C]."""
    parts = match_text.split('/')
    if not parts:
        return [match_text]
    # First part contains base + first suffix (e.g. 10-P-101A)
    base_with_first = parts[0]
    # Strip trailing letter to get base
    if base_with_first and base_with_first[-1].isalpha():
        base = base_with_first[:-1]
        suffixes = [base_with_first[-1]] + parts[1:]
    else:
        return [match_text]
    return [f"{base}{s.strip().upper()}" for s in suffixes]


def _expand_range(prefix: str, start: str, end: str) -> list[str]:
    """10-FT-1001 to 1005 → [10-FT-1001, …, 10-FT-1005]."""
    try:
        s, e = int(start), int(end)
        if s > e or (e - s) > 100:
            return [f"{prefix}{start}"]
        width = max(len(start), len(end))
        return [f"{prefix}{str(n).zfill(width)}" for n in range(s, e + 1)]
    except ValueError:
        return [f"{prefix}{start}"]


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extract_tags_from_text(text: str) -> list[DetectedTag]:
    """
    Extract all tag numbers (and shorthands) from raw text.
    Returns a list of DetectedTag objects — one per logical tag.
    """
    detected: list[DetectedTag] = []
    seen_tags: set[str] = set()

    # ---- 1. Detect any implicit prefix from context lines ----
    implicit_prefix: Optional[str] = None
    prefix_match = PREFIX_CONTEXT_RE.search(text)
    if prefix_match:
        implicit_prefix = prefix_match.group(1).upper()

    # ---- 2. Multi-suffix shorthand:  10-P-101A/B/C ----
    for m in re.finditer(
        r'\b(\d{1,3}-[A-Z]{1,5}-\d{1,5}[A-Z](?:/[A-Z])+)\b', text
    ):
        raw = m.group(0)
        expansions = _expand_multi_suffix(raw)
        dt = DetectedTag(
            raw_text=raw,
            tag_number=raw,
            is_shorthand=True,
            shorthand_expansion=[_clean(t) for t in expansions],
        )
        key = raw.upper()
        if key not in seen_tags:
            seen_tags.add(key)
            detected.append(dt)

    # ---- 3. Range shorthand:  10-FT-1001 to 1005 ----
    for m in RANGE_RE.finditer(text):
        prefix, start, end = m.group(1), m.group(2), m.group(3)
        raw = m.group(0)
        expansions = _expand_range(prefix, start, end)
        dt = DetectedTag(
            raw_text=raw,
            tag_number=raw,
            is_shorthand=True,
            shorthand_expansion=[_clean(t) for t in expansions],
        )
        key = raw.upper()
        if key not in seen_tags:
            seen_tags.add(key)
            detected.append(dt)

    # ---- 4. Full / normal tags ----
    for m in FULL_TAG_RE.finditer(text):
        tag = _clean(m.group(0))
        if tag not in seen_tags and not _is_covered_by_shorthand(tag, detected):
            seen_tags.add(tag)
            detected.append(DetectedTag(raw_text=m.group(0), tag_number=tag))

    # ---- 5. Partial tags resolved via implicit prefix ----
    if implicit_prefix:
        for m in PARTIAL_TAG_RE.finditer(text):
            partial = _clean(m.group(1))
            full_tag = f"{implicit_prefix}{partial}"
            if full_tag not in seen_tags:
                seen_tags.add(full_tag)
                detected.append(
                    DetectedTag(
                        raw_text=m.group(0),
                        tag_number=full_tag,
                        is_shorthand=True,
                        shorthand_expansion=[full_tag],
                        confidence=0.8,
                    )
                )

    return detected


def _is_covered_by_shorthand(tag: str, detected: list[DetectedTag]) -> bool:
    """Return True if this tag is already accounted for inside a shorthand expansion."""
    for dt in detected:
        if dt.is_shorthand and tag in dt.shorthand_expansion:
            return True
    return False


# ---------------------------------------------------------------------------
# Flatten for verification (expand shorthands into individual tags)
# ---------------------------------------------------------------------------

def flatten_detected_tags(detected: list[DetectedTag]) -> list[dict]:
    """
    Convert DetectedTag list into a flat list of dicts ready for verification.
    Each shorthand is expanded into its constituent tags.
    """
    flat: list[dict] = []
    seen: set[str] = set()
    for dt in detected:
        if dt.is_shorthand and dt.shorthand_expansion:
            for expanded in dt.shorthand_expansion:
                if expanded not in seen:
                    seen.add(expanded)
                    flat.append({
                        "tag_number": expanded,
                        "raw_text": dt.raw_text,
                        "is_shorthand": True,
                        "original_shorthand": dt.tag_number,
                        "page_number": dt.page_number,
                    })
        else:
            tag = dt.tag_number
            if tag not in seen:
                seen.add(tag)
                flat.append({
                    "tag_number": tag,
                    "raw_text": dt.raw_text,
                    "is_shorthand": False,
                    "original_shorthand": None,
                    "page_number": dt.page_number,
                })
    return flat
