"""
Tag-to-Document relationship routes.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import Tag, TagDocumentRelationship, Document

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


class CreateRelationshipsBody(BaseModel):
    document_id: int


@router.post("/create")
async def create_relationships(body: CreateRelationshipsBody, db: AsyncSession = Depends(get_db)):
    """
    Write tag-document relationships for a verified document.
    Replaces any previous relationships for the same document_number.
    """
    from routes.documents import _verification_cache

    doc_result = await db.execute(select(Document).where(Document.id == body.document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    cached = _verification_cache.get(body.document_id)
    if not cached:
        raise HTTPException(status_code=400, detail="No verification data found; please re-upload")

    # Delete previous relationships for this document number
    await db.execute(
        delete(TagDocumentRelationship).where(
            TagDocumentRelationship.document_number == doc.document_number
        )
    )

    now = datetime.utcnow()
    created_count = 0
    for t in cached.get("tags", []):
        rel = TagDocumentRelationship(
            tag_number=t["tag_number"],
            document_number=doc.document_number,
            document_title=doc.document_title,
            document_revision=doc.document_revision,
            found_at=now,
            verification_status=t.get("verification_status", "not_found"),
        )
        db.add(rel)
        created_count += 1

    await db.commit()
    return {"created": created_count, "document_number": doc.document_number}


@router.get("/impact/{tag_number}")
async def impact_analysis(tag_number: str, db: AsyncSession = Depends(get_db)):
    """
    Given a tag number, return all documents that reference it plus tag CTDB details.
    """
    tn = tag_number.upper()

    tag_result = await db.execute(select(Tag).where(Tag.tag_number == tn))
    tag = tag_result.scalar_one_or_none()

    rel_result = await db.execute(
        select(TagDocumentRelationship).where(TagDocumentRelationship.tag_number == tn)
    )
    rels = rel_result.scalars().all()

    return {
        "tag": {
            "tag_number": tag.tag_number,
            "tag_description": tag.tag_description,
            "discipline": tag.discipline,
            "status": tag.status,
            "voided_at": tag.voided_at.isoformat() if tag and tag.voided_at else None,
        } if tag else None,
        "documents": [
            {
                "id": r.id,
                "document_number": r.document_number,
                "document_title": r.document_title,
                "document_revision": r.document_revision,
                "found_at": r.found_at.isoformat() if r.found_at else None,
                "verification_status": r.verification_status,
            }
            for r in rels
        ],
        "affected_count": len(rels),
    }
