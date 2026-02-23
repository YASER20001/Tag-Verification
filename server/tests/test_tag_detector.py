"""
Tests for services/tag_detector.py

Covers:
  - Full tag extraction
  - Multi-suffix shorthand (A/B/C)
  - Range shorthand (1001 to 1005)
  - Implicit prefix resolution
  - De-duplication
  - flatten_detected_tags expansion
  - Edge cases (empty text, punctuation, boundaries)
"""
import pytest
from services.tag_detector import (
    extract_tags_from_text,
    flatten_detected_tags,
    _clean,
    _expand_multi_suffix,
    _expand_range,
)


# ===========================================================================
# _clean helper
# ===========================================================================

class TestClean:
    def test_strips_whitespace(self):
        assert _clean("  10-P-101A  ") == "10-P-101A"

    def test_uppercases(self):
        assert _clean("10-p-101a") == "10-P-101A"

    def test_strips_trailing_punctuation(self):
        assert _clean("10-P-101A.") == "10-P-101A"
        assert _clean("10-P-101A,") == "10-P-101A"
        assert _clean("(10-P-101A)") == "10-P-101A"

    def test_strips_semicolon(self):
        assert _clean("10-P-101A;") == "10-P-101A"


# ===========================================================================
# _expand_multi_suffix
# ===========================================================================

class TestExpandMultiSuffix:
    def test_two_suffixes(self):
        assert _expand_multi_suffix("10-P-101A/B") == ["10-P-101A", "10-P-101B"]

    def test_three_suffixes(self):
        assert _expand_multi_suffix("10-P-101A/B/C") == [
            "10-P-101A", "10-P-101B", "10-P-101C"
        ]

    def test_preserves_base(self):
        result = _expand_multi_suffix("20-FCV-2001A/B")
        assert result == ["20-FCV-2001A", "20-FCV-2001B"]

    def test_no_suffix_returns_original(self):
        # No trailing alpha — returns as-is
        result = _expand_multi_suffix("10-P-101")
        assert result == ["10-P-101"]


# ===========================================================================
# _expand_range
# ===========================================================================

class TestExpandRange:
    def test_simple_range(self):
        assert _expand_range("10-FT-", "1001", "1003") == [
            "10-FT-1001", "10-FT-1002", "10-FT-1003"
        ]

    def test_zero_padded(self):
        result = _expand_range("10-FT-", "001", "003")
        assert result == ["10-FT-001", "10-FT-002", "10-FT-003"]

    def test_single_value_when_start_equals_end(self):
        assert _expand_range("10-FT-", "1001", "1001") == ["10-FT-1001"]

    def test_reversed_range_returns_start_only(self):
        # start > end is clamped to just the start
        result = _expand_range("10-FT-", "1005", "1001")
        assert result == ["10-FT-1005"]

    def test_huge_range_returns_start_only(self):
        # ranges > 100 are rejected
        result = _expand_range("10-FT-", "1", "999")
        assert result == ["10-FT-1"]


# ===========================================================================
# Full tag extraction
# ===========================================================================

class TestFullTagExtraction:
    def test_single_tag(self):
        tags = extract_tags_from_text("Install pump 10-P-101A at location A.")
        assert len(tags) == 1
        assert tags[0].tag_number == "10-P-101A"
        assert tags[0].is_shorthand is False

    def test_multiple_different_tags(self):
        text = "Check 10-P-101A, 20-E-301 and 10-FT-1001."
        tags = extract_tags_from_text(text)
        numbers = [t.tag_number for t in tags]
        assert "10-P-101A" in numbers
        assert "20-E-301" in numbers
        assert "10-FT-1001" in numbers

    def test_no_duplicates_for_same_tag_repeated(self):
        text = "Tag 10-P-101A is adjacent to 10-P-101A."
        tags = extract_tags_from_text(text)
        numbers = [t.tag_number for t in tags if not t.is_shorthand]
        assert numbers.count("10-P-101A") == 1

    def test_empty_text_returns_empty(self):
        assert extract_tags_from_text("") == []

    def test_no_tags_in_text(self):
        assert extract_tags_from_text("This document has no equipment tags.") == []

    def test_tag_not_extracted_from_partial_word(self):
        # "P-101" inside a longer word should not match a false full tag
        tags = extract_tags_from_text("See section 10-P-101A for details.")
        numbers = [t.tag_number for t in tags]
        assert "10-P-101A" in numbers

    def test_tag_with_project_prefix(self):
        text = "Refer to ABC-10-P-101A for this equipment."
        tags = extract_tags_from_text(text)
        numbers = [t.tag_number for t in tags]
        assert any("10-P-101A" in n for n in numbers)

    def test_whitespace_around_tags(self):
        tags = extract_tags_from_text("   10-P-101A   ")
        assert len(tags) == 1

    def test_newline_separated_tags(self):
        text = "10-P-101A\n10-V-201\n10-FT-1001"
        tags = extract_tags_from_text(text)
        assert len(tags) == 3


# ===========================================================================
# Multi-suffix shorthand
# ===========================================================================

class TestMultiSuffixShorthand:
    def test_detected_as_shorthand(self):
        tags = extract_tags_from_text("Pumps 10-P-101A/B/C to be installed.")
        shorthand = [t for t in tags if t.is_shorthand]
        assert len(shorthand) == 1

    def test_expansion_is_correct(self):
        tags = extract_tags_from_text("10-P-101A/B/C")
        sh = next(t for t in tags if t.is_shorthand)
        assert sh.shorthand_expansion == ["10-P-101A", "10-P-101B", "10-P-101C"]

    def test_two_suffix_expansion(self):
        tags = extract_tags_from_text("Valves 20-XV-2001A/B")
        sh = next(t for t in tags if t.is_shorthand)
        assert sh.shorthand_expansion == ["20-XV-2001A", "20-XV-2001B"]

    def test_shorthand_not_duplicated_as_full_tags(self):
        # When shorthand is 10-P-101A/B, the individual 10-P-101A and
        # 10-P-101B should NOT also appear as separate full tags
        text = "10-P-101A/B connected to 10-V-201."
        tags = extract_tags_from_text(text)
        full_numbers = [t.tag_number for t in tags if not t.is_shorthand]
        assert "10-P-101A" not in full_numbers
        assert "10-P-101B" not in full_numbers
        assert "10-V-201" in full_numbers


# ===========================================================================
# Range shorthand
# ===========================================================================

class TestRangeShorthand:
    def test_range_with_to_keyword(self):
        tags = extract_tags_from_text("Transmitters 10-FT-1001 to 1003.")
        sh = [t for t in tags if t.is_shorthand]
        assert len(sh) == 1
        assert sh[0].shorthand_expansion == ["10-FT-1001", "10-FT-1002", "10-FT-1003"]

    def test_range_with_dash_separator(self):
        tags = extract_tags_from_text("Instruments 10-PT-1001-1002")
        sh = [t for t in tags if t.is_shorthand]
        assert len(sh) == 1
        assert "10-PT-1001" in sh[0].shorthand_expansion
        assert "10-PT-1002" in sh[0].shorthand_expansion

    def test_range_single_item(self):
        tags = extract_tags_from_text("Valves 10-FT-1001 to 1001.")
        sh = [t for t in tags if t.is_shorthand]
        assert len(sh[0].shorthand_expansion) == 1


# ===========================================================================
# Implicit prefix
# ===========================================================================

class TestImplicitPrefix:
    def test_prefix_context_expands_partial_tags(self):
        text = "All tags prefixed with 10-\nP-101A and FT-1001 are in unit 10."
        tags = extract_tags_from_text(text)
        full_numbers = [t.tag_number for t in tags]
        assert "10-P-101A" in full_numbers
        assert "10-FT-1001" in full_numbers

    def test_no_prefix_leaves_partial_as_is(self):
        # Without a prefix context line, partial tags should NOT resolve
        text = "Equipment P-101A and FT-1001."
        tags = extract_tags_from_text(text)
        full_numbers = [t.tag_number for t in tags]
        assert "10-P-101A" not in full_numbers
        assert "10-FT-1001" not in full_numbers


# ===========================================================================
# flatten_detected_tags
# ===========================================================================

class TestFlattenDetectedTags:
    def test_full_tags_pass_through(self):
        tags = extract_tags_from_text("10-P-101A and 10-V-201.")
        flat = flatten_detected_tags(tags)
        numbers = [f["tag_number"] for f in flat]
        assert "10-P-101A" in numbers
        assert "10-V-201" in numbers
        assert all(not f["is_shorthand"] for f in flat if f["tag_number"] in ("10-P-101A", "10-V-201"))

    def test_shorthand_expanded_in_flat(self):
        tags = extract_tags_from_text("10-P-101A/B/C")
        flat = flatten_detected_tags(tags)
        numbers = [f["tag_number"] for f in flat]
        assert "10-P-101A" in numbers
        assert "10-P-101B" in numbers
        assert "10-P-101C" in numbers

    def test_shorthand_items_marked_correctly(self):
        tags = extract_tags_from_text("10-P-101A/B")
        flat = flatten_detected_tags(tags)
        for item in flat:
            assert item["is_shorthand"] is True
            assert item["original_shorthand"] == "10-P-101A/B"

    def test_no_duplicates_in_flat(self):
        # 10-P-101A/B in text + standalone 10-P-101A should deduplicate
        text = "Pumps 10-P-101A/B and also 10-P-101A separately."
        tags = extract_tags_from_text(text)
        flat = flatten_detected_tags(tags)
        numbers = [f["tag_number"] for f in flat]
        assert numbers.count("10-P-101A") == 1

    def test_empty_detected_list(self):
        assert flatten_detected_tags([]) == []

    def test_range_shorthand_expanded_in_flat(self):
        tags = extract_tags_from_text("10-FT-1001 to 1003")
        flat = flatten_detected_tags(tags)
        numbers = [f["tag_number"] for f in flat]
        assert numbers == ["10-FT-1001", "10-FT-1002", "10-FT-1003"]

    def test_flat_dict_has_required_keys(self):
        tags = extract_tags_from_text("10-P-101A")
        flat = flatten_detected_tags(tags)
        required = {"tag_number", "raw_text", "is_shorthand", "original_shorthand", "page_number"}
        assert required.issubset(flat[0].keys())
