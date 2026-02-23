"""
End-to-end integration tests for the full pipeline:
  extract_text_from_file → extract_tags_from_text → flatten_detected_tags
  → verify_tags_sync → summarise → save_document → create_relationships

Uses the real sample PDFs from sample_docs/.
"""
import pytest
from tests.conftest import read_sample_pdf
from services.pdf_extractor import extract_text_from_file
from services.tag_detector import extract_tags_from_text, flatten_detected_tags


# ===========================================================================
# Helpers
# ===========================================================================

def run_pipeline(filename: str, doc_number: str, seeded_db):
    """Extract, detect, flatten, verify, summarise — return (verified, summary)."""
    from db.db_sync import verify_tags_sync, summarise
    raw = read_sample_pdf(filename)
    extraction = extract_text_from_file(raw, filename)
    detected  = extract_tags_from_text(extraction["full_text"])
    flat      = flatten_detected_tags(detected)
    verified  = verify_tags_sync(flat)
    summary   = summarise(verified)
    return verified, summary


# ===========================================================================
# Doc 1 — mostly active tags; one tag (20-FT-2001) is not in the seeded CTDB
# ===========================================================================

class TestDoc1ShouldPass:
    @pytest.fixture(autouse=True)
    def run(self, seeded_db):
        self.verified, self.summary = run_pipeline(
            "test_doc_1_should_pass.pdf", "P&ID-10-001", seeded_db
        )

    def test_at_least_one_tag_found(self):
        assert self.summary["total"] >= 1

    def test_majority_of_tags_are_valid_active(self):
        # Most tags in doc1 should resolve as valid_active against the seeded CTDB
        assert self.summary["valid_active"] >= 10

    def test_no_void_tags(self):
        # Doc 1 should not reference any void equipment
        assert self.summary["valid_void"] == 0

    def test_no_shorthand_detected(self):
        # Doc 1 uses full tag notation throughout
        assert self.summary["shorthand_detected"] == 0

    def test_known_active_tag_is_valid(self):
        statuses = {t["tag_number"]: t["verification_status"] for t in self.verified}
        # 10-P-101A is in the CTDB as Active — must be valid_active
        assert statuses.get("10-P-101A") == "valid_active"

    def test_valid_active_tags_have_ctdb_description(self):
        for t in self.verified:
            if t["verification_status"] == "valid_active":
                assert t["ctdb_description"] != "", (
                    f"Active tag {t['tag_number']} missing CTDB description"
                )

    def test_save_document_status_reflects_summary(self, seeded_db):
        from db.db_sync import save_document, get_recent_documents
        doc_id = save_document("P&ID-10-001", "Feed Water System", "A",
                               "test_doc_1_should_pass.pdf", self.summary)
        docs = get_recent_documents()
        doc = next(d for d in docs if d["id"] == doc_id)
        assert doc["verification_status"] == self.summary["overall_status"]


# ===========================================================================
# Doc 2 — has issues (contains unknown tag 10-PSV-9999)
# ===========================================================================

class TestDoc2HasIssues:
    @pytest.fixture(autouse=True)
    def run(self, seeded_db):
        self.verified, self.summary = run_pipeline(
            "test_doc_2_has_issues.pdf", "P&ID-10-002", seeded_db
        )

    def test_overall_status_is_issues(self):
        assert self.summary["overall_status"] == "issues"

    def test_not_found_count_at_least_one(self):
        assert self.summary["not_found"] >= 1

    def test_unknown_tag_9999_is_not_found(self):
        nf = [t["tag_number"] for t in self.verified if t["verification_status"] == "not_found"]
        assert "10-PSV-9999" in nf

    def test_known_tags_are_valid_active(self):
        valid = [t for t in self.verified if t["verification_status"] == "valid_active"]
        assert len(valid) >= 1

    def test_approve_with_justification_works(self, seeded_db):
        from db.db_sync import save_document, approve_document, get_recent_documents
        doc_id = save_document("P&ID-10-002", "Cooling System", "B",
                               "test_doc_2_has_issues.pdf", self.summary)
        approve_document(doc_id, "lead_engineer", "10-PSV-9999 is a new tag; CTDB update pending.")
        docs = get_recent_documents()
        doc = next(d for d in docs if d["id"] == doc_id)
        assert doc["verification_status"] == "approved"
        assert "new tag" in doc["override_justification"]


# ===========================================================================
# Doc 3 — shorthand notation (A/B or ranges)
# ===========================================================================

class TestDoc3Shorthand:
    @pytest.fixture(autouse=True)
    def run(self, seeded_db):
        self.verified, self.summary = run_pipeline(
            "test_doc_3_shorthand.pdf", "P&ID-10-003", seeded_db
        )

    def test_overall_status_is_issues(self):
        # Shorthand notation counts as issues
        assert self.summary["overall_status"] == "issues"

    def test_shorthand_detected_count_nonzero(self):
        assert self.summary["shorthand_detected"] >= 1

    def test_shorthand_items_have_original_shorthand(self):
        shorthand_items = [t for t in self.verified if t.get("is_shorthand")]
        assert len(shorthand_items) >= 1
        for item in shorthand_items:
            assert item.get("original_shorthand") is not None


# ===========================================================================
# Relationship traceability — full pipeline including DB persistence
# ===========================================================================

class TestRelationshipPipeline:
    def test_full_trace_doc1_to_impact(self, seeded_db):
        """
        Verify doc1 → save → create_relationships → get_impact
        correctly links tags to the document.
        """
        from db.db_sync import verify_tags_sync, summarise, save_document, create_relationships, get_impact

        raw = read_sample_pdf("test_doc_1_should_pass.pdf")
        extraction = extract_text_from_file(raw, "test_doc_1_should_pass.pdf")
        flat     = flatten_detected_tags(extract_tags_from_text(extraction["full_text"]))
        verified = verify_tags_sync(flat)
        summary  = summarise(verified)
        doc_id   = save_document("TRACE-001", "Full Trace", "A",
                                 "test_doc_1_should_pass.pdf", summary)
        create_relationships(doc_id, verified)

        # Pick any valid_active tag and confirm it traces back to this doc
        active = [t for t in verified if t["verification_status"] == "valid_active"]
        assert active, "Expected at least one valid_active tag for traceability"
        tag_num = active[0]["tag_number"]

        impact = get_impact(tag_num)
        assert impact["affected_count"] >= 1
        assert any(d["document_number"] == "TRACE-001" for d in impact["documents"])

    def test_void_tag_appears_in_void_alerts(self, seeded_db):
        """
        After saving a doc that references a void tag, that tag must
        appear in get_void_alerts().
        """
        from db.db_sync import save_document, create_relationships, get_void_alerts

        void_tag = "10-P-102B"   # seeded as Void
        s = {"valid_active": 0, "valid_void": 1, "not_found": 0,
             "shorthand_detected": 0, "total": 1, "overall_status": "issues"}
        doc_id = save_document("ALERT-TEST", "Alert Doc", "A", "a.pdf", s)
        create_relationships(doc_id, [{
            "tag_number": void_tag,
            "verification_status": "valid_void",
            "raw_text": void_tag,
            "is_shorthand": False,
            "original_shorthand": None,
            "page_number": 1,
        }])
        alerts = get_void_alerts()
        assert any(a["tag_number"] == void_tag for a in alerts)
        alert = next(a for a in alerts if a["tag_number"] == void_tag)
        assert "ALERT-TEST" in alert["documents"]

    def test_stats_reflect_saved_documents(self, seeded_db):
        from db.db_sync import verify_tags_sync, summarise, save_document, get_stats

        raw = read_sample_pdf("test_doc_1_should_pass.pdf")
        ext = extract_text_from_file(raw, "test_doc_1_should_pass.pdf")
        flat = flatten_detected_tags(extract_tags_from_text(ext["full_text"]))
        v    = verify_tags_sync(flat)
        s    = summarise(v)
        save_document("STATS-001", "S", "A", "s.pdf", s)

        raw2 = read_sample_pdf("test_doc_2_has_issues.pdf")
        ext2 = extract_text_from_file(raw2, "test_doc_2_has_issues.pdf")
        flat2 = flatten_detected_tags(extract_tags_from_text(ext2["full_text"]))
        v2    = verify_tags_sync(flat2)
        s2    = summarise(v2)
        save_document("STATS-002", "S2", "B", "s2.pdf", s2)

        stats = get_stats()
        assert stats["total_documents"] == 2
        # At least one document has issues
        assert stats["issue_documents"] >= 1
