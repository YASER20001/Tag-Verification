"""
Tests for services/pdf_extractor.py

Covers:
  - Digital PDF extraction (PyMuPDF)
  - OCR flag path (image file)
  - Unsupported file type graceful return
  - Page count and structure of return value
  - Integration with the three sample PDFs
"""
import io
import os
import pytest

from services.pdf_extractor import extract_text_from_file
from tests.conftest import read_sample_pdf


# ===========================================================================
# Return-value contract
# ===========================================================================

class TestReturnStructure:
    """Every call must return a dict with the same four keys."""

    def _assert_structure(self, result: dict):
        assert isinstance(result, dict)
        assert "pages" in result
        assert "full_text" in result
        assert "method" in result
        assert "page_count" in result
        assert isinstance(result["pages"], list)
        assert isinstance(result["full_text"], str)
        assert isinstance(result["page_count"], int)

    def test_structure_pdf(self):
        data = read_sample_pdf("test_doc_1_should_pass.pdf")
        self._assert_structure(extract_text_from_file(data, "test_doc_1_should_pass.pdf"))

    def test_structure_unsupported(self):
        self._assert_structure(extract_text_from_file(b"whatever", "report.docx"))

    def test_structure_empty_bytes(self):
        # Should not raise; returns a dict with method "failed" when no content
        result = extract_text_from_file(b"", "empty.pdf")
        self._assert_structure(result)
        assert result["method"] in ("failed", "pymupdf")


# ===========================================================================
# Unsupported format
# ===========================================================================

class TestUnsupportedFormat:
    def test_docx_returns_unsupported(self):
        result = extract_text_from_file(b"fake content", "doc.docx")
        assert result["method"] == "unsupported"
        assert result["full_text"] == ""
        assert result["page_count"] == 0

    def test_txt_returns_unsupported(self):
        result = extract_text_from_file(b"plain text", "notes.txt")
        assert result["method"] == "unsupported"


# ===========================================================================
# Sample PDF 1 — should PASS (only active tags, no issues)
# ===========================================================================

class TestSampleDoc1Pass:
    @pytest.fixture(autouse=True)
    def load(self):
        self.data = read_sample_pdf("test_doc_1_should_pass.pdf")
        self.result = extract_text_from_file(self.data, "test_doc_1_should_pass.pdf")

    def test_method_is_pymupdf_or_pdfplumber(self):
        assert self.result["method"] in ("pymupdf", "pdfplumber", "pypdf", "ocr")

    def test_has_pages(self):
        assert self.result["page_count"] >= 1
        assert len(self.result["pages"]) == self.result["page_count"]

    def test_full_text_not_empty(self):
        assert len(self.result["full_text"].strip()) > 20

    def test_pages_have_page_and_text_keys(self):
        for p in self.result["pages"]:
            assert "page" in p
            assert "text" in p

    def test_pages_are_numbered_from_1(self):
        assert self.result["pages"][0]["page"] == 1

    def test_full_text_contains_tag_numbers(self):
        text = self.result["full_text"].upper()
        # At least one standard tag pattern should appear
        import re
        found = re.findall(r'\d{1,3}-[A-Z]{1,5}-\d{1,5}[A-Z]?', text)
        assert len(found) >= 1, "Expected at least one tag number in pass-doc text"


# ===========================================================================
# Sample PDF 2 — has issues (tag not in CTDB)
# ===========================================================================

class TestSampleDoc2Issues:
    @pytest.fixture(autouse=True)
    def load(self):
        self.data = read_sample_pdf("test_doc_2_has_issues.pdf")
        self.result = extract_text_from_file(self.data, "test_doc_2_has_issues.pdf")

    def test_extraction_succeeds(self):
        assert self.result["method"] != "failed"

    def test_has_content(self):
        assert self.result["full_text"].strip()

    def test_contains_unknown_tag(self):
        # Doc 2 includes 10-PSV-9999 which is NOT in the CTDB
        assert "10-PSV-9999" in self.result["full_text"].upper()


# ===========================================================================
# Sample PDF 3 — shorthand notation
# ===========================================================================

class TestSampleDoc3Shorthand:
    @pytest.fixture(autouse=True)
    def load(self):
        self.data = read_sample_pdf("test_doc_3_shorthand.pdf")
        self.result = extract_text_from_file(self.data, "test_doc_3_shorthand.pdf")

    def test_extraction_succeeds(self):
        assert self.result["method"] != "failed"

    def test_has_content(self):
        assert self.result["full_text"].strip()


# ===========================================================================
# File-type routing — image vs pdf
# ===========================================================================

class TestFileTypeRouting:
    def test_png_extension_routed_to_image_path(self):
        # Fake PNG bytes — OCR will fail gracefully but method is image_ocr or ocr_unavailable
        result = extract_text_from_file(b"NOT A REAL PNG", "schematic.png")
        assert result["method"] in ("image_ocr", "ocr_unavailable", "failed")

    def test_jpg_extension_routed(self):
        result = extract_text_from_file(b"FAKE", "drawing.jpg")
        assert result["method"] in ("image_ocr", "ocr_unavailable", "failed")

    def test_tiff_extension_routed(self):
        result = extract_text_from_file(b"FAKE", "scan.tiff")
        assert result["method"] in ("image_ocr", "ocr_unavailable", "failed")

    def test_pdf_extension_routed_to_pdf_path(self):
        # Corrupt bytes won't parse but the method returned must not be "unsupported".
        # PyMuPDF will fail gracefully; pdfplumber/pypdf are silently skipped if
        # their dependencies are broken in this environment.
        result = extract_text_from_file(b"NOT A PDF", "doc.pdf")
        assert result["method"] != "unsupported", (
            "A .pdf file should be routed to the PDF extraction path, not rejected as unsupported"
        )
