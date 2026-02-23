"""
Tests for db/db_sync.py — all DB operations run against an in-memory SQLite DB.

Fixtures (from conftest.py):
  patched_db  — empty DB, tables created, no data
  seeded_db   — empty DB seeded with 50 sample tags via init_db()
"""
import csv
import io
import pytest


# ===========================================================================
# init_db / seed
# ===========================================================================

class TestInitDb:
    def test_creates_tables_and_seeds_tags(self, patched_db):
        from db.db_sync import init_db
        init_db()
        from db.db_sync import get_stats
        stats = get_stats()
        assert stats["total_tags"] == 50

    def test_seed_counts_active_and_void(self, patched_db):
        from db.db_sync import init_db, get_stats
        init_db()
        s = get_stats()
        assert s["active_tags"] + s["void_tags"] == 50
        assert s["void_tags"] == 6   # exactly 6 void in SAMPLE_TAGS

    def test_seed_is_idempotent(self, patched_db):
        """Calling init_db twice must not duplicate tags."""
        from db.db_sync import init_db, get_stats
        init_db()
        init_db()
        assert get_stats()["total_tags"] == 50


# ===========================================================================
# get_tags — filtering
# ===========================================================================

class TestGetTags:
    def test_returns_all_tags_no_filter(self, seeded_db):
        from db.db_sync import get_tags
        tags, total = get_tags()
        assert total == 50
        assert len(tags) <= 200

    def test_search_by_tag_number(self, seeded_db):
        from db.db_sync import get_tags
        tags, total = get_tags(search="10-P-101")
        numbers = [t["tag_number"] for t in tags]
        assert "10-P-101A" in numbers
        assert "10-P-101B" in numbers

    def test_search_is_case_insensitive(self, seeded_db):
        from db.db_sync import get_tags
        tags, _ = get_tags(search="10-p-101")
        assert any(t["tag_number"].startswith("10-P-101") for t in tags)

    def test_search_by_description(self, seeded_db):
        from db.db_sync import get_tags
        tags, _ = get_tags(search="Lube Oil")
        assert len(tags) >= 1
        assert all("lube oil" in t["tag_description"].lower() for t in tags)

    def test_filter_discipline_instrumentation(self, seeded_db):
        from db.db_sync import get_tags
        tags, _ = get_tags(discipline="Instrumentation")
        assert all(t["discipline"] == "Instrumentation" for t in tags)
        assert len(tags) >= 10

    def test_filter_status_active(self, seeded_db):
        from db.db_sync import get_tags
        tags, total = get_tags(status="Active")
        assert total == 44
        assert all(t["status"] == "Active" for t in tags)

    def test_filter_status_void(self, seeded_db):
        from db.db_sync import get_tags
        tags, total = get_tags(status="Void")
        assert total == 6
        assert all(t["status"] == "Void" for t in tags)

    def test_combined_filter(self, seeded_db):
        from db.db_sync import get_tags
        tags, _ = get_tags(discipline="Mechanical", status="Active")
        assert all(t["discipline"] == "Mechanical" and t["status"] == "Active" for t in tags)

    def test_no_results_returns_empty_list(self, seeded_db):
        from db.db_sync import get_tags
        tags, total = get_tags(search="DOES_NOT_EXIST_XYZ")
        assert tags == []
        assert total == 0

    def test_limit_respected(self, seeded_db):
        from db.db_sync import get_tags
        tags, _ = get_tags(limit=5)
        assert len(tags) == 5

    def test_tag_dict_has_required_keys(self, seeded_db):
        from db.db_sync import get_tags
        tags, _ = get_tags(limit=1)
        required = {"id", "tag_number", "tag_description", "discipline", "status",
                    "created_at", "updated_at", "voided_at", "created_by"}
        assert required.issubset(tags[0].keys())


# ===========================================================================
# create_tag
# ===========================================================================

class TestCreateTag:
    def test_creates_tag_successfully(self, seeded_db):
        from db.db_sync import create_tag, get_tags
        create_tag("99-P-999", "Test pump", "Mechanical", "Active", "tester")
        tags, _ = get_tags(search="99-P-999")
        assert any(t["tag_number"] == "99-P-999" for t in tags)

    def test_returns_tag_dict(self, seeded_db):
        from db.db_sync import create_tag
        result = create_tag("99-P-998", "Test pump 2", "Piping", "Void", "admin")
        assert result["tag_number"] == "99-P-998"
        assert result["status"] == "Void"

    def test_tag_number_uppercased(self, seeded_db):
        from db.db_sync import create_tag
        result = create_tag("99-p-997", "Lower case input", "Mechanical", "Active", "admin")
        assert result["tag_number"] == "99-P-997"

    def test_duplicate_raises_value_error(self, seeded_db):
        from db.db_sync import create_tag
        with pytest.raises(ValueError, match="already exists"):
            create_tag("10-P-101A", "Duplicate", "Mechanical", "Active", "admin")

    def test_duplicate_check_is_case_insensitive(self, seeded_db):
        from db.db_sync import create_tag
        with pytest.raises(ValueError):
            create_tag("10-p-101a", "Lower case dup", "Mechanical", "Active", "admin")


# ===========================================================================
# toggle_tag_status
# ===========================================================================

class TestToggleTagStatus:
    def _get_id(self, tag_number):
        from db.db_sync import get_tags
        tags, _ = get_tags(search=tag_number)
        return next(t["id"] for t in tags if t["tag_number"] == tag_number)

    def test_active_to_void(self, seeded_db):
        from db.db_sync import toggle_tag_status, get_tags
        tag_id = self._get_id("10-P-101A")
        new_status = toggle_tag_status(tag_id)
        assert new_status == "Void"
        tags, _ = get_tags(search="10-P-101A")
        assert tags[0]["status"] == "Void"

    def test_void_to_active(self, seeded_db):
        from db.db_sync import toggle_tag_status, get_tags
        tag_id = self._get_id("10-P-102B")   # seeded as Void
        new_status = toggle_tag_status(tag_id)
        assert new_status == "Active"

    def test_toggle_twice_returns_to_original(self, seeded_db):
        from db.db_sync import toggle_tag_status
        tag_id = self._get_id("10-P-101A")
        toggle_tag_status(tag_id)
        status = toggle_tag_status(tag_id)
        assert status == "Active"

    def test_voiding_sets_voided_at(self, seeded_db):
        from db.db_sync import toggle_tag_status, get_tags
        tag_id = self._get_id("10-P-101A")
        toggle_tag_status(tag_id)
        tags, _ = get_tags(search="10-P-101A")
        assert tags[0]["voided_at"] != ""

    def test_unvoiding_clears_voided_at(self, seeded_db):
        from db.db_sync import toggle_tag_status, get_tags
        tag_id = self._get_id("10-P-102B")   # Void seed
        toggle_tag_status(tag_id)             # → Active
        tags, _ = get_tags(search="10-P-102B")
        assert tags[0]["voided_at"] == ""

    def test_missing_tag_raises_value_error(self, seeded_db):
        from db.db_sync import toggle_tag_status
        with pytest.raises(ValueError, match="not found"):
            toggle_tag_status(999999)


# ===========================================================================
# import_tags_csv
# ===========================================================================

class TestImportTagsCsv:
    def _make_csv(self, rows: list[dict]) -> bytes:
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["tag_number", "tag_description", "discipline", "status", "created_by"],
        )
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue().encode()

    def test_imports_new_tags(self, seeded_db):
        from db.db_sync import import_tags_csv, get_stats
        csv_data = self._make_csv([
            {"tag_number": "99-FT-9001", "tag_description": "Test FT",
             "discipline": "Instrumentation", "status": "Active", "created_by": "test"},
            {"tag_number": "99-FT-9002", "tag_description": "Test FT 2",
             "discipline": "Instrumentation", "status": "Active", "created_by": "test"},
        ])
        result = import_tags_csv(csv_data)
        assert result["created"] == 2
        assert result["skipped"] == 0
        assert get_stats()["total_tags"] == 52

    def test_skips_duplicate_tags(self, seeded_db):
        from db.db_sync import import_tags_csv
        csv_data = self._make_csv([
            {"tag_number": "10-P-101A", "tag_description": "Dup",
             "discipline": "Mechanical", "status": "Active", "created_by": "test"},
        ])
        result = import_tags_csv(csv_data)
        assert result["created"] == 0
        assert result["skipped"] == 1

    def test_skips_empty_tag_number_rows(self, seeded_db):
        from db.db_sync import import_tags_csv
        csv_data = self._make_csv([
            {"tag_number": "", "tag_description": "No tag",
             "discipline": "Mechanical", "status": "Active", "created_by": "test"},
        ])
        result = import_tags_csv(csv_data)
        assert result["skipped"] == 1
        assert result["created"] == 0

    def test_mixed_new_and_duplicate(self, seeded_db):
        from db.db_sync import import_tags_csv
        csv_data = self._make_csv([
            {"tag_number": "99-NEW-001", "tag_description": "New",
             "discipline": "Piping", "status": "Active", "created_by": "test"},
            {"tag_number": "10-P-101A",  "tag_description": "Dup",
             "discipline": "Mechanical", "status": "Active", "created_by": "test"},
        ])
        result = import_tags_csv(csv_data)
        assert result["created"] == 1
        assert result["skipped"] == 1

    def test_bom_utf8_encoded_csv(self, seeded_db):
        """CSV files exported from Excel often have a UTF-8 BOM."""
        from db.db_sync import import_tags_csv
        csv_str = "tag_number,tag_description,discipline,status,created_by\n99-BOM-001,BOM test,Piping,Active,test\n"
        bom_bytes = b'\xef\xbb\xbf' + csv_str.encode("utf-8")
        result = import_tags_csv(bom_bytes)
        assert result["created"] == 1


# ===========================================================================
# verify_tags_sync + summarise
# ===========================================================================

class TestVerifyTagsSync:
    def _tag(self, number, is_shorthand=False):
        return {
            "tag_number": number,
            "raw_text": number,
            "is_shorthand": is_shorthand,
            "original_shorthand": None,
            "page_number": 1,
        }

    def test_empty_list_returns_empty(self, seeded_db):
        from db.db_sync import verify_tags_sync
        assert verify_tags_sync([]) == []

    def test_active_tag_gets_valid_active(self, seeded_db):
        from db.db_sync import verify_tags_sync
        result = verify_tags_sync([self._tag("10-P-101A")])
        assert result[0]["verification_status"] == "valid_active"
        assert result[0]["ctdb_description"] != ""
        assert result[0]["ctdb_discipline"] == "Mechanical"

    def test_void_tag_gets_valid_void(self, seeded_db):
        from db.db_sync import verify_tags_sync
        result = verify_tags_sync([self._tag("10-P-102B")])  # seeded as Void
        assert result[0]["verification_status"] == "valid_void"

    def test_unknown_tag_gets_not_found(self, seeded_db):
        from db.db_sync import verify_tags_sync
        result = verify_tags_sync([self._tag("99-XX-9999")])
        assert result[0]["verification_status"] == "not_found"
        assert result[0]["ctdb_description"] == ""

    def test_shorthand_unknown_tag_gets_shorthand_detected(self, seeded_db):
        from db.db_sync import verify_tags_sync
        tag = self._tag("10-P-101C", is_shorthand=True)  # 101C not in CTDB
        result = verify_tags_sync([tag])
        assert result[0]["verification_status"] == "shorthand_detected"

    def test_shorthand_known_tag_gets_valid_active(self, seeded_db):
        """A shorthand-expanded tag that IS in CTDB resolves as valid_active, not shorthand."""
        from db.db_sync import verify_tags_sync
        tag = self._tag("10-P-101A", is_shorthand=True)  # is in CTDB
        result = verify_tags_sync([tag])
        assert result[0]["verification_status"] == "valid_active"

    def test_mixed_statuses(self, seeded_db):
        from db.db_sync import verify_tags_sync
        flat = [
            self._tag("10-P-101A"),   # active
            self._tag("10-P-102B"),   # void
            self._tag("99-XX-9999"),  # not found
        ]
        result = verify_tags_sync(flat)
        statuses = {r["tag_number"]: r["verification_status"] for r in result}
        assert statuses["10-P-101A"] == "valid_active"
        assert statuses["10-P-102B"] == "valid_void"
        assert statuses["99-XX-9999"] == "not_found"

    def test_original_tag_fields_preserved(self, seeded_db):
        """Input fields should be carried through unchanged."""
        from db.db_sync import verify_tags_sync
        tag = self._tag("10-P-101A")
        tag["page_number"] = 3
        result = verify_tags_sync([tag])
        assert result[0]["page_number"] == 3
        assert result[0]["tag_number"] == "10-P-101A"


class TestSummarise:
    def _v(self, status):
        return {"verification_status": status}

    def test_all_active_is_pass(self):
        from db.db_sync import summarise
        s = summarise([self._v("valid_active")] * 5)
        assert s["overall_status"] == "pass"
        assert s["valid_active"] == 5
        assert s["total"] == 5

    def test_any_void_is_issues(self):
        from db.db_sync import summarise
        s = summarise([self._v("valid_active"), self._v("valid_void")])
        assert s["overall_status"] == "issues"

    def test_any_not_found_is_issues(self):
        from db.db_sync import summarise
        s = summarise([self._v("valid_active"), self._v("not_found")])
        assert s["overall_status"] == "issues"

    def test_any_shorthand_is_issues(self):
        from db.db_sync import summarise
        s = summarise([self._v("valid_active"), self._v("shorthand_detected")])
        assert s["overall_status"] == "issues"

    def test_empty_list_is_pass(self):
        from db.db_sync import summarise
        s = summarise([])
        assert s["total"] == 0
        assert s["overall_status"] == "pass"

    def test_counts_are_correct(self):
        from db.db_sync import summarise
        items = (
            [self._v("valid_active")] * 3 +
            [self._v("valid_void")] * 2 +
            [self._v("not_found")] * 1 +
            [self._v("shorthand_detected")] * 1
        )
        s = summarise(items)
        assert s["valid_active"] == 3
        assert s["valid_void"] == 2
        assert s["not_found"] == 1
        assert s["shorthand_detected"] == 1
        assert s["total"] == 7


# ===========================================================================
# save_document / approve_document
# ===========================================================================

class TestSaveDocument:
    def _summary(self, **kwargs):
        base = {"valid_active": 5, "valid_void": 0, "not_found": 0,
                "shorthand_detected": 0, "total": 5, "overall_status": "pass"}
        base.update(kwargs)
        return base

    def test_returns_integer_id(self, seeded_db):
        from db.db_sync import save_document
        doc_id = save_document("P-001", "Test Doc", "A", "test.pdf", self._summary())
        assert isinstance(doc_id, int)
        assert doc_id > 0

    def test_doc_appears_in_recent(self, seeded_db):
        from db.db_sync import save_document, get_recent_documents
        save_document("P-001", "Test Doc", "A", "test.pdf", self._summary())
        recent = get_recent_documents()
        assert any(d["document_number"] == "P-001" for d in recent)

    def test_pass_status_stored(self, seeded_db):
        from db.db_sync import save_document, get_recent_documents
        save_document("P-PASS", "Pass Doc", "0", "p.pdf", self._summary(overall_status="pass"))
        recent = get_recent_documents()
        doc = next(d for d in recent if d["document_number"] == "P-PASS")
        assert doc["verification_status"] == "pass"

    def test_issues_status_stored(self, seeded_db):
        from db.db_sync import save_document, get_recent_documents
        save_document("P-FAIL", "Fail Doc", "0", "f.pdf",
                      self._summary(overall_status="issues", not_found=1, total=6))
        recent = get_recent_documents()
        doc = next(d for d in recent if d["document_number"] == "P-FAIL")
        assert doc["verification_status"] == "issues"

    def test_tag_counts_stored(self, seeded_db):
        from db.db_sync import save_document, get_recent_documents
        s = self._summary(valid_active=3, valid_void=1, not_found=1, total=5,
                          overall_status="issues")
        save_document("P-CTR", "Count Doc", "B", "c.pdf", s)
        doc = next(d for d in get_recent_documents() if d["document_number"] == "P-CTR")
        assert doc["tags_valid"] == 3
        assert doc["tags_void"] == 1
        assert doc["tags_not_found"] == 1
        assert doc["tags_found"] == 5


class TestApproveDocument:
    def _save(self, num="P-TEST"):
        from db.db_sync import save_document
        summary = {"valid_active": 2, "valid_void": 1, "not_found": 0,
                   "shorthand_detected": 0, "total": 3, "overall_status": "issues"}
        return save_document(num, "Doc", "A", "f.pdf", summary)

    def test_approve_changes_status(self, seeded_db):
        from db.db_sync import approve_document, get_recent_documents
        doc_id = self._save()
        approve_document(doc_id, "jsmith")
        docs = get_recent_documents()
        doc = next(d for d in docs if d["id"] == doc_id)
        assert doc["verification_status"] == "approved"
        assert doc["approved_by"] == "jsmith"

    def test_approve_with_justification(self, seeded_db):
        from db.db_sync import approve_document, get_recent_documents
        doc_id = self._save("P-OVER")
        approve_document(doc_id, "jsmith", "Tag 10-P-102B is being decommissioned.")
        docs = get_recent_documents()
        doc = next(d for d in docs if d["id"] == doc_id)
        assert "decommissioned" in doc["override_justification"]

    def test_approve_missing_document_raises(self, seeded_db):
        from db.db_sync import approve_document
        with pytest.raises(ValueError, match="not found"):
            approve_document(999999)


# ===========================================================================
# create_relationships
# ===========================================================================

class TestCreateRelationships:
    def _make_doc(self, num="REL-001"):
        from db.db_sync import save_document
        s = {"valid_active": 2, "valid_void": 0, "not_found": 0,
             "shorthand_detected": 0, "total": 2, "overall_status": "pass"}
        return save_document(num, "Rel Doc", "A", "r.pdf", s)

    def _tags(self):
        return [
            {"tag_number": "10-P-101A", "verification_status": "valid_active",
             "raw_text": "10-P-101A", "is_shorthand": False,
             "original_shorthand": None, "page_number": 1},
            {"tag_number": "10-V-201",  "verification_status": "valid_active",
             "raw_text": "10-V-201",  "is_shorthand": False,
             "original_shorthand": None, "page_number": 1},
        ]

    def test_returns_count_of_relationships(self, seeded_db):
        from db.db_sync import create_relationships
        doc_id = self._make_doc()
        n = create_relationships(doc_id, self._tags())
        assert n == 2

    def test_relationships_appear_in_impact(self, seeded_db):
        from db.db_sync import create_relationships, get_impact
        doc_id = self._make_doc("REL-002")
        create_relationships(doc_id, self._tags())
        impact = get_impact("10-P-101A")
        assert any(d["document_number"] == "REL-002" for d in impact["documents"])

    def test_relationships_replaced_on_second_call(self, seeded_db):
        """Calling create_relationships twice for the same doc replaces, not duplicates."""
        from db.db_sync import create_relationships, get_impact
        doc_id = self._make_doc("REL-003")
        create_relationships(doc_id, self._tags())
        create_relationships(doc_id, self._tags())  # second call
        impact = get_impact("10-P-101A")
        docs_for_rel003 = [d for d in impact["documents"] if d["document_number"] == "REL-003"]
        assert len(docs_for_rel003) == 1  # not 2

    def test_missing_doc_raises(self, seeded_db):
        from db.db_sync import create_relationships
        with pytest.raises(ValueError, match="not found"):
            create_relationships(999999, self._tags())


# ===========================================================================
# get_stats
# ===========================================================================

class TestGetStats:
    def test_stats_keys(self, seeded_db):
        from db.db_sync import get_stats
        s = get_stats()
        assert {"total_tags", "active_tags", "void_tags",
                "total_documents", "passed_documents", "issue_documents"}.issubset(s.keys())

    def test_initial_zero_documents(self, seeded_db):
        from db.db_sync import get_stats
        s = get_stats()
        assert s["total_documents"] == 0

    def test_documents_counted_after_save(self, seeded_db):
        from db.db_sync import save_document, get_stats
        summary = {"valid_active": 3, "valid_void": 0, "not_found": 0,
                   "shorthand_detected": 0, "total": 3, "overall_status": "pass"}
        save_document("STAT-001", "S", "A", "s.pdf", summary)
        assert get_stats()["total_documents"] == 1

    def test_passed_docs_counted(self, seeded_db):
        from db.db_sync import save_document, approve_document, get_stats
        s_pass = {"valid_active": 3, "valid_void": 0, "not_found": 0,
                  "shorthand_detected": 0, "total": 3, "overall_status": "pass"}
        doc_id = save_document("STAT-P", "Pass", "A", "p.pdf", s_pass)
        approve_document(doc_id, "eng")
        stats = get_stats()
        assert stats["passed_documents"] >= 1


# ===========================================================================
# get_recent_documents
# ===========================================================================

class TestGetRecentDocuments:
    def test_empty_when_no_documents(self, seeded_db):
        from db.db_sync import get_recent_documents
        assert get_recent_documents() == []

    def test_returns_up_to_limit(self, seeded_db):
        from db.db_sync import save_document, get_recent_documents
        s = {"valid_active": 1, "valid_void": 0, "not_found": 0,
             "shorthand_detected": 0, "total": 1, "overall_status": "pass"}
        for i in range(5):
            save_document(f"LIMIT-{i:03}", "L", "A", "l.pdf", s)
        recent = get_recent_documents(limit=3)
        assert len(recent) == 3

    def test_ordered_newest_first(self, seeded_db):
        import time
        from db.db_sync import save_document, get_recent_documents
        s = {"valid_active": 1, "valid_void": 0, "not_found": 0,
             "shorthand_detected": 0, "total": 1, "overall_status": "pass"}
        save_document("ORDER-A", "A", "0", "a.pdf", s)
        time.sleep(0.01)
        save_document("ORDER-B", "B", "0", "b.pdf", s)
        recent = get_recent_documents(limit=2)
        assert recent[0]["document_number"] == "ORDER-B"


# ===========================================================================
# get_void_alerts
# ===========================================================================

class TestGetVoidAlerts:
    def test_no_alerts_when_no_void_relationships(self, seeded_db):
        """Void tags exist but have no document relationships → no alerts."""
        from db.db_sync import get_void_alerts
        assert get_void_alerts() == []

    def test_alert_appears_after_relationship_created(self, seeded_db):
        from db.db_sync import save_document, create_relationships, get_void_alerts
        s = {"valid_active": 0, "valid_void": 1, "not_found": 0,
             "shorthand_detected": 0, "total": 1, "overall_status": "issues"}
        doc_id = save_document("VOID-DOC", "Void test", "A", "v.pdf", s)
        create_relationships(doc_id, [{
            "tag_number": "10-P-102B",   # seeded as Void
            "verification_status": "valid_void",
            "raw_text": "10-P-102B",
            "is_shorthand": False,
            "original_shorthand": None,
            "page_number": 1,
        }])
        alerts = get_void_alerts()
        assert any(a["tag_number"] == "10-P-102B" for a in alerts)

    def test_alert_affected_count(self, seeded_db):
        from db.db_sync import save_document, create_relationships, get_void_alerts
        s = {"valid_active": 0, "valid_void": 1, "not_found": 0,
             "shorthand_detected": 0, "total": 1, "overall_status": "issues"}
        void_tag = [{
            "tag_number": "10-P-102B",
            "verification_status": "valid_void",
            "raw_text": "10-P-102B",
            "is_shorthand": False,
            "original_shorthand": None,
            "page_number": 1,
        }]
        for i in range(3):
            doc_id = save_document(f"VA-{i}", "T", "A", "v.pdf", s)
            create_relationships(doc_id, void_tag)
        alerts = get_void_alerts()
        alert = next(a for a in alerts if a["tag_number"] == "10-P-102B")
        assert alert["affected_count"] == 3


# ===========================================================================
# get_impact
# ===========================================================================

class TestGetImpact:
    def test_unknown_tag_returns_none_tag(self, seeded_db):
        from db.db_sync import get_impact
        result = get_impact("99-XX-0000")
        assert result["tag"] is None
        assert result["affected_count"] == 0
        assert result["documents"] == []

    def test_known_tag_returns_tag_dict(self, seeded_db):
        from db.db_sync import get_impact
        result = get_impact("10-P-101A")
        assert result["tag"]["tag_number"] == "10-P-101A"
        assert result["tag"]["status"] == "Active"

    def test_lowercase_input_is_normalised(self, seeded_db):
        from db.db_sync import get_impact
        result = get_impact("10-p-101a")
        assert result["tag"] is not None
        assert result["tag"]["tag_number"] == "10-P-101A"

    def test_zero_documents_when_no_relationships(self, seeded_db):
        from db.db_sync import get_impact
        result = get_impact("10-P-101A")
        assert result["affected_count"] == 0

    def test_documents_after_relationship_created(self, seeded_db):
        from db.db_sync import save_document, create_relationships, get_impact
        s = {"valid_active": 1, "valid_void": 0, "not_found": 0,
             "shorthand_detected": 0, "total": 1, "overall_status": "pass"}
        doc_id = save_document("IMP-001", "Impact doc", "A", "i.pdf", s)
        create_relationships(doc_id, [{
            "tag_number": "10-P-101A",
            "verification_status": "valid_active",
            "raw_text": "10-P-101A",
            "is_shorthand": False,
            "original_shorthand": None,
            "page_number": 1,
        }])
        result = get_impact("10-P-101A")
        assert result["affected_count"] == 1
        assert result["documents"][0]["document_number"] == "IMP-001"

    def test_document_dict_has_required_keys(self, seeded_db):
        from db.db_sync import save_document, create_relationships, get_impact
        s = {"valid_active": 1, "valid_void": 0, "not_found": 0,
             "shorthand_detected": 0, "total": 1, "overall_status": "pass"}
        doc_id = save_document("IMP-002", "Doc", "A", "d.pdf", s)
        create_relationships(doc_id, [{
            "tag_number": "10-P-101A",
            "verification_status": "valid_active",
            "raw_text": "10-P-101A",
            "is_shorthand": False,
            "original_shorthand": None,
            "page_number": 1,
        }])
        result = get_impact("10-P-101A")
        required = {"document_number", "document_title", "document_revision",
                    "found_at", "verification_status"}
        assert required.issubset(result["documents"][0].keys())
