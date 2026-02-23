"""
Synchronous DB operations for use in Streamlit pages.
Uses the same SQLite file as the async FastAPI layer.
"""
import csv
import io
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, or_, func, delete
from sqlalchemy.orm import sessionmaker

from .models import Base, Tag, Document, TagDocumentRelationship

DB_PATH = os.path.join(os.path.dirname(__file__), "tag_verify.db")
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

SAMPLE_TAGS = [
    # Unit 10 — Mechanical Pumps
    ("10-P-101A", "Centrifugal Pump - Feed Water A", "Mechanical", "Active"),
    ("10-P-101B", "Centrifugal Pump - Feed Water B", "Mechanical", "Active"),
    ("10-P-102A", "Booster Pump - Cooling Water A", "Mechanical", "Active"),
    ("10-P-102B", "Booster Pump - Cooling Water B", "Mechanical", "Void"),
    ("10-P-103",  "Chemical Dosing Pump", "Mechanical", "Active"),
    # Vessels
    ("10-V-201",  "Feed Water Storage Vessel", "Mechanical", "Active"),
    ("10-V-202",  "Chemical Injection Pot", "Mechanical", "Active"),
    ("10-V-203",  "Condensate Collection Vessel", "Mechanical", "Void"),
    ("10-TK-101", "Fuel Oil Day Tank", "Mechanical", "Active"),
    ("10-TK-102", "Lube Oil Storage Tank", "Mechanical", "Active"),
    # Unit 20 — Heat Transfer
    ("20-E-301",  "Feed Water Preheater", "Mechanical", "Active"),
    ("20-E-302",  "Cooling Water Heat Exchanger", "Mechanical", "Active"),
    ("20-E-303",  "Lube Oil Cooler", "Mechanical", "Active"),
    ("20-HX-301", "Shell & Tube Heat Exchanger - Process Fluid", "Mechanical", "Active"),
    ("20-HX-302", "Plate Heat Exchanger - Cooling Water", "Mechanical", "Void"),
    # Instrumentation — Flow
    ("10-FT-1001", "Flow Transmitter - Feed Water Discharge", "Instrumentation", "Active"),
    ("10-FT-1002", "Flow Transmitter - Cooling Water Supply", "Instrumentation", "Active"),
    ("10-FT-1003", "Flow Transmitter - Fuel Gas Header", "Instrumentation", "Active"),
    ("10-FT-1004", "Flow Transmitter - Chemical Injection", "Instrumentation", "Active"),
    ("10-FT-1005", "Flow Transmitter - Condensate Return", "Instrumentation", "Active"),
    # Instrumentation — Temperature
    ("10-TT-1001", "Temperature Transmitter - Feed Water Inlet", "Instrumentation", "Active"),
    ("10-TT-1002", "Temperature Transmitter - Feed Water Outlet", "Instrumentation", "Active"),
    ("10-TT-1003", "Temperature Transmitter - Cooling Water", "Instrumentation", "Active"),
    ("10-TT-1004", "Temperature Transmitter - Lube Oil", "Instrumentation", "Void"),
    # Instrumentation — Pressure
    ("10-PT-1001", "Pressure Transmitter - Pump Discharge", "Instrumentation", "Active"),
    ("10-PT-1002", "Pressure Transmitter - Feed Header", "Instrumentation", "Active"),
    ("10-PT-1003", "Pressure Transmitter - Fuel Gas", "Instrumentation", "Active"),
    # Level
    ("10-LT-1001", "Level Transmitter - Feed Water Vessel", "Instrumentation", "Active"),
    ("10-LT-1002", "Level Transmitter - Condensate Vessel", "Instrumentation", "Active"),
    ("10-LT-1003", "Level Transmitter - Chemical Tank", "Instrumentation", "Active"),
    # Safety
    ("10-PSV-1001",  "Pressure Safety Valve - Pump Discharge", "Mechanical", "Active"),
    ("10-PSV-1002",  "Pressure Safety Valve - Feed Vessel", "Mechanical", "Active"),
    ("10-PSV-1003",  "Pressure Safety Valve - Fuel Gas", "Mechanical", "Active"),
    ("10-PSV-1004",  "Pressure Safety Valve - Chemical Pot", "Mechanical", "Active"),
    ("10-PSV-1004A", "Pressure Safety Valve - Chemical Pot A", "Mechanical", "Active"),
    ("10-PSV-1004B", "Pressure Safety Valve - Chemical Pot B", "Mechanical", "Void"),
    # Valves
    ("20-XV-2001",  "Shutdown Valve - Feed Water Inlet", "Instrumentation", "Active"),
    ("20-XV-2002",  "Shutdown Valve - Cooling Water", "Instrumentation", "Active"),
    ("20-XV-2003",  "Shutdown Valve - Fuel Gas Supply", "Instrumentation", "Active"),
    ("20-XV-2004",  "Shutdown Valve - Condensate Outlet", "Instrumentation", "Void"),
    ("20-FCV-2001", "Flow Control Valve - Feed Water", "Instrumentation", "Active"),
    ("20-FCV-2002", "Flow Control Valve - Cooling Water Return", "Instrumentation", "Active"),
    ("20-PCV-2001", "Pressure Control Valve - Gas Header", "Instrumentation", "Active"),
    ("20-LCV-2001", "Level Control Valve - Vessel Outlet", "Instrumentation", "Active"),
    # Electrical
    ("10-MCC-101",  "Motor Control Centre - Unit 10 Main", "Electrical", "Active"),
    ("10-MTR-101A", "Electric Motor - Feed Pump A", "Electrical", "Active"),
    ("10-MTR-101B", "Electric Motor - Feed Pump B", "Electrical", "Active"),
    ("20-MTR-201",  "Electric Motor - Cooling Fan", "Electrical", "Active"),
    # Piping
    ("10-STR-101",  "Y-Strainer - Pump Suction", "Piping", "Active"),
    ("10-STR-102",  "Duplex Strainer - Fuel Oil", "Piping", "Active"),
]


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Init & seed
# ---------------------------------------------------------------------------

def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_if_empty()


def _seed_if_empty():
    with db_session() as s:
        if s.query(Tag).count() > 0:
            return
        now = datetime.utcnow()
        for tag_number, desc, discipline, status in SAMPLE_TAGS:
            s.add(Tag(
                tag_number=tag_number,
                tag_description=desc,
                discipline=discipline,
                status=status,
                created_at=now,
                updated_at=now,
                voided_at=now if status == "Void" else None,
                created_by="system",
            ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tag_dict(t: Tag) -> dict:
    return {
        "id": t.id,
        "tag_number": t.tag_number,
        "tag_description": t.tag_description or "",
        "discipline": t.discipline or "",
        "status": t.status,
        "created_at": t.created_at.strftime("%Y-%m-%d") if t.created_at else "",
        "updated_at": t.updated_at.strftime("%Y-%m-%d") if t.updated_at else "",
        "voided_at": t.voided_at.strftime("%Y-%m-%d") if t.voided_at else "",
        "created_by": t.created_by or "",
    }


def _doc_dict(d: Document) -> dict:
    return {
        "id": d.id,
        "document_number": d.document_number,
        "document_title": d.document_title or "",
        "document_revision": d.document_revision or "",
        "filename": d.filename or "",
        "uploaded_at": d.uploaded_at.strftime("%Y-%m-%d %H:%M") if d.uploaded_at else "",
        "verification_status": d.verification_status or "pending",
        "tags_found": d.tags_found or 0,
        "tags_valid": d.tags_valid or 0,
        "tags_void": d.tags_void or 0,
        "tags_not_found": d.tags_not_found or 0,
        "tags_shorthand": d.tags_shorthand or 0,
        "approved_by": d.approved_by or "",
        "override_justification": d.override_justification or "",
    }


# ---------------------------------------------------------------------------
# Tags (CTDB)
# ---------------------------------------------------------------------------

def get_tags(search: str = "", discipline: str = "", status: str = "", limit: int = 200):
    with db_session() as s:
        q = s.query(Tag)
        if search:
            p = f"%{search.upper()}%"
            q = q.filter(or_(Tag.tag_number.ilike(p), Tag.tag_description.ilike(p)))
        if discipline:
            q = q.filter(Tag.discipline == discipline)
        if status:
            q = q.filter(Tag.status == status)
        total = q.count()
        tags = q.order_by(Tag.tag_number).limit(limit).all()
        return [_tag_dict(t) for t in tags], total


def create_tag(tag_number: str, description: str, discipline: str,
               status: str, created_by: str) -> dict:
    with db_session() as s:
        existing = s.query(Tag).filter(Tag.tag_number == tag_number.upper()).first()
        if existing:
            raise ValueError(f"Tag {tag_number.upper()} already exists")
        tag = Tag(
            tag_number=tag_number.upper(),
            tag_description=description,
            discipline=discipline,
            status=status,
            created_by=created_by,
        )
        s.add(tag)
        s.flush()
        return _tag_dict(tag)


def toggle_tag_status(tag_id: int) -> str:
    """Toggle Active ↔ Void. Returns new status."""
    with db_session() as s:
        tag = s.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise ValueError("Tag not found")
        tag.status = "Void" if tag.status == "Active" else "Active"
        tag.voided_at = datetime.utcnow() if tag.status == "Void" else None
        tag.updated_at = datetime.utcnow()
        return tag.status


def import_tags_csv(content: bytes) -> dict:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    created, skipped = 0, 0
    with db_session() as s:
        for row in reader:
            tn = (row.get("tag_number") or "").strip().upper()
            if not tn:
                skipped += 1
                continue
            if s.query(Tag).filter(Tag.tag_number == tn).first():
                skipped += 1
                continue
            s.add(Tag(
                tag_number=tn,
                tag_description=row.get("tag_description", ""),
                discipline=row.get("discipline", ""),
                status=row.get("status", "Active"),
                created_by=row.get("created_by", "import"),
            ))
            created += 1
    return {"created": created, "skipped": skipped}


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_tags_sync(flat_tags: list[dict]) -> list[dict]:
    """Verify a list of flat tags against the CTDB. Returns list with status fields."""
    if not flat_tags:
        return []
    tag_numbers = [t["tag_number"] for t in flat_tags]
    # Convert to plain dicts INSIDE the session so attributes are read before expiry
    with db_session() as s:
        db_tags: dict[str, dict] = {}
        for row in s.query(Tag).filter(Tag.tag_number.in_(tag_numbers)).all():
            db_tags[row.tag_number] = {
                "status": row.status,
                "tag_description": row.tag_description or "",
                "discipline": row.discipline or "",
            }
    verified = []
    for t in flat_tags:
        num = t["tag_number"]
        db_tag = db_tags.get(num)
        if db_tag is None:
            status = "shorthand_detected" if t.get("is_shorthand") else "not_found"
            description, discipline = "", ""
        elif db_tag["status"] == "Active":
            status = "valid_active"
            description, discipline = db_tag["tag_description"], db_tag["discipline"]
        else:
            status = "valid_void"
            description, discipline = db_tag["tag_description"], db_tag["discipline"]
        verified.append({
            **t,
            "verification_status": status,
            "ctdb_description": description,
            "ctdb_discipline": discipline,
        })
    return verified


def summarise(verified: list[dict]) -> dict:
    counts = {"valid_active": 0, "valid_void": 0, "not_found": 0, "shorthand_detected": 0}
    for t in verified:
        k = t.get("verification_status", "not_found")
        if k in counts:
            counts[k] += 1
    has_issues = counts["valid_void"] > 0 or counts["not_found"] > 0 or counts["shorthand_detected"] > 0
    return {**counts, "total": len(verified), "overall_status": "issues" if has_issues else "pass"}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def save_document(doc_number: str, title: str, revision: str,
                  filename: str, summary: dict) -> int:
    with db_session() as s:
        doc = Document(
            document_number=doc_number.strip(),
            document_title=title.strip(),
            document_revision=revision.strip(),
            filename=filename,
            file_path="",
            verification_status=summary["overall_status"],
            tags_found=summary["total"],
            tags_valid=summary["valid_active"],
            tags_void=summary["valid_void"],
            tags_not_found=summary["not_found"],
            tags_shorthand=summary["shorthand_detected"],
        )
        s.add(doc)
        s.flush()
        return doc.id


def approve_document(doc_id: int, approved_by: str = "engineer",
                     override_justification: str = "") -> None:
    with db_session() as s:
        doc = s.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise ValueError("Document not found")
        doc.verification_status = "approved"
        doc.approved_at = datetime.utcnow()
        doc.approved_by = approved_by
        doc.override_justification = override_justification or None


def create_relationships(doc_id: int, verified_tags: list[dict]) -> int:
    with db_session() as s:
        doc = s.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise ValueError("Document not found")
        s.execute(
            delete(TagDocumentRelationship).where(
                TagDocumentRelationship.document_number == doc.document_number
            )
        )
        now = datetime.utcnow()
        for t in verified_tags:
            s.add(TagDocumentRelationship(
                tag_number=t["tag_number"],
                document_number=doc.document_number,
                document_title=doc.document_title,
                document_revision=doc.document_revision,
                found_at=now,
                verification_status=t.get("verification_status", "not_found"),
            ))
        return len(verified_tags)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    with db_session() as s:
        total_tags    = s.query(func.count(Tag.id)).scalar()
        active_tags   = s.query(func.count(Tag.id)).filter(Tag.status == "Active").scalar()
        void_tags     = s.query(func.count(Tag.id)).filter(Tag.status == "Void").scalar()
        total_docs    = s.query(func.count(Document.id)).scalar()
        passed_docs   = s.query(func.count(Document.id)).filter(
            Document.verification_status.in_(["pass", "approved"])).scalar()
        issue_docs    = s.query(func.count(Document.id)).filter(
            Document.verification_status == "issues").scalar()
        return {
            "total_tags": total_tags,
            "active_tags": active_tags,
            "void_tags": void_tags,
            "total_documents": total_docs,
            "passed_documents": passed_docs,
            "issue_documents": issue_docs,
        }


def get_recent_documents(limit: int = 10) -> list[dict]:
    with db_session() as s:
        docs = s.query(Document).order_by(Document.uploaded_at.desc()).limit(limit).all()
        return [_doc_dict(d) for d in docs]


def get_void_alerts() -> list[dict]:
    with db_session() as s:
        void_tags = {t.tag_number: t for t in s.query(Tag).filter(Tag.status == "Void").all()}
        if not void_tags:
            return []
        rels = s.query(TagDocumentRelationship).filter(
            TagDocumentRelationship.tag_number.in_(list(void_tags.keys()))
        ).all()
        alerts: dict[str, dict] = {}
        for r in rels:
            tn = r.tag_number
            if tn not in alerts:
                tag = void_tags[tn]
                alerts[tn] = {
                    "tag_number": tn,
                    "tag_description": tag.tag_description or "",
                    "voided_at": tag.voided_at.strftime("%Y-%m-%d") if tag.voided_at else "",
                    "affected_count": 0,
                    "documents": [],
                }
            alerts[tn]["affected_count"] += 1
            alerts[tn]["documents"].append(r.document_number)
        result = list(alerts.values())
        result.sort(key=lambda x: x["affected_count"], reverse=True)
        return result


# ---------------------------------------------------------------------------
# Impact Analysis
# ---------------------------------------------------------------------------

def get_impact(tag_number: str) -> dict:
    tn = tag_number.strip().upper()
    with db_session() as s:
        tag = s.query(Tag).filter(Tag.tag_number == tn).first()
        rels = s.query(TagDocumentRelationship).filter(
            TagDocumentRelationship.tag_number == tn
        ).all()
        return {
            "tag": _tag_dict(tag) if tag else None,
            "documents": [
                {
                    "document_number": r.document_number,
                    "document_title": r.document_title or "",
                    "document_revision": r.document_revision or "",
                    "found_at": r.found_at.strftime("%Y-%m-%d") if r.found_at else "",
                    "verification_status": r.verification_status or "",
                }
                for r in rels
            ],
            "affected_count": len(rels),
        }
