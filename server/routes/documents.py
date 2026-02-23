"""
Document upload and verification routes.
"""
import os
import json
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import Document, TagDocumentRelationship
from services.pdf_extractor import extract_text_from_file
from services.tag_detector import extract_tags_from_text, flatten_detected_tags
from services.verifier import verify_tags, summarise_results

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Cache for verification results (in memory for prototype — keyed by document id)
_verification_cache: dict[int, dict] = {}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def doc_to_dict(d: Document) -> dict:
    return {
        "id": d.id,
        "document_number": d.document_number,
        "document_title": d.document_title,
        "document_revision": d.document_revision,
        "filename": d.filename,
        "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        "verification_status": d.verification_status,
        "approved_at": d.approved_at.isoformat() if d.approved_at else None,
        "approved_by": d.approved_by,
        "override_justification": d.override_justification,
        "tags_found": d.tags_found,
        "tags_valid": d.tags_valid,
        "tags_void": d.tags_void,
        "tags_not_found": d.tags_not_found,
        "tags_shorthand": d.tags_shorthand,
    }


@router.post("/upload")
async def upload_document(
    document_number: str = Form(...),
    document_title: str = Form(""),
    document_revision: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    # Save file
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Extract text
    extraction = extract_text_from_file(file_bytes, file.filename)
    full_text = extraction["full_text"]

    # Detect tags
    detected = extract_tags_from_text(full_text)
    flat_tags = flatten_detected_tags(detected)

    # Attach page numbers from per-page extraction
    page_tag_map: dict[str, int] = {}
    for page_info in extraction.get("pages", []):
        page_num = page_info["page"]
        page_tags = flatten_detected_tags(extract_tags_from_text(page_info["text"]))
        for t in page_tags:
            if t["tag_number"] not in page_tag_map:
                page_tag_map[t["tag_number"]] = page_num
    for t in flat_tags:
        t["page_number"] = page_tag_map.get(t["tag_number"])

    # Verify against CTDB
    verified = await verify_tags(flat_tags, db)
    summary = summarise_results(verified)

    # Persist document record
    doc = Document(
        document_number=document_number.strip(),
        document_title=document_title.strip(),
        document_revision=document_revision.strip(),
        filename=file.filename,
        file_path=file_path,
        verification_status=summary["overall_status"],
        tags_found=summary["total"],
        tags_valid=summary["valid_active"],
        tags_void=summary["valid_void"],
        tags_not_found=summary["not_found"],
        tags_shorthand=summary["shorthand_detected"],
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Cache full results
    _verification_cache[doc.id] = {
        "summary": summary,
        "tags": verified,
        "extraction_method": extraction["method"],
        "page_count": extraction["page_count"],
    }

    return {
        "document": doc_to_dict(doc),
        "summary": summary,
        "extraction_method": extraction["method"],
    }


@router.get("/{doc_id}/report")
async def get_report(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    cached = _verification_cache.get(doc_id, {})
    return {
        "document": doc_to_dict(doc),
        "summary": cached.get("summary", {}),
        "tags": cached.get("tags", []),
        "extraction_method": cached.get("extraction_method", "unknown"),
        "page_count": cached.get("page_count", 0),
    }


@router.post("/{doc_id}/approve")
async def approve_document(
    doc_id: int,
    approved_by: str = Form("engineer"),
    override_justification: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.verification_status = "approved"
    doc.approved_at = datetime.utcnow()
    doc.approved_by = approved_by
    doc.override_justification = override_justification
    await db.commit()
    await db.refresh(doc)
    return doc_to_dict(doc)


@router.get("/{doc_number}/tags")
async def get_document_tags(doc_number: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TagDocumentRelationship).where(
        TagDocumentRelationship.document_number == doc_number
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "tag_number": r.tag_number,
            "document_number": r.document_number,
            "document_title": r.document_title,
            "document_revision": r.document_revision,
            "found_at": r.found_at.isoformat() if r.found_at else None,
            "verification_status": r.verification_status,
        }
        for r in rows
    ]
