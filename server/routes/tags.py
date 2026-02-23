"""
CTDB tag management routes.
"""
import csv
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import Tag, TagDocumentRelationship

router = APIRouter(prefix="/api/tags", tags=["tags"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TagCreate(BaseModel):
    tag_number: str
    tag_description: Optional[str] = None
    discipline: Optional[str] = None
    status: str = "Active"
    created_by: str = "admin"


class TagUpdate(BaseModel):
    tag_description: Optional[str] = None
    discipline: Optional[str] = None
    status: Optional[str] = None
    created_by: Optional[str] = None


def tag_to_dict(t: Tag) -> dict:
    return {
        "id": t.id,
        "tag_number": t.tag_number,
        "tag_description": t.tag_description,
        "discipline": t.discipline,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "voided_at": t.voided_at.isoformat() if t.voided_at else None,
        "created_by": t.created_by,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def list_tags(
    search: Optional[str] = Query(None),
    discipline: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tag)
    if search:
        pattern = f"%{search.upper()}%"
        stmt = stmt.where(
            or_(Tag.tag_number.ilike(pattern), Tag.tag_description.ilike(pattern))
        )
    if discipline:
        stmt = stmt.where(Tag.discipline == discipline)
    if status:
        stmt = stmt.where(Tag.status == status)
    stmt = stmt.order_by(Tag.tag_number).offset(offset).limit(limit)
    result = await db.execute(stmt)
    tags = result.scalars().all()

    # Total count (for pagination)
    count_stmt = select(func.count()).select_from(Tag)
    if search:
        pattern = f"%{search.upper()}%"
        count_stmt = count_stmt.where(
            or_(Tag.tag_number.ilike(pattern), Tag.tag_description.ilike(pattern))
        )
    if discipline:
        count_stmt = count_stmt.where(Tag.discipline == discipline)
    if status:
        count_stmt = count_stmt.where(Tag.status == status)
    total = (await db.execute(count_stmt)).scalar()

    return {"tags": [tag_to_dict(t) for t in tags], "total": total}


@router.post("")
async def create_tag(body: TagCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Tag).where(Tag.tag_number == body.tag_number.upper()))
    if existing.scalar():
        raise HTTPException(status_code=409, detail="Tag number already exists")
    tag = Tag(
        tag_number=body.tag_number.upper(),
        tag_description=body.tag_description,
        discipline=body.discipline,
        status=body.status,
        created_by=body.created_by,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag_to_dict(tag)


@router.put("/{tag_id}")
async def update_tag(tag_id: int, body: TagUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    if body.tag_description is not None:
        tag.tag_description = body.tag_description
    if body.discipline is not None:
        tag.discipline = body.discipline
    if body.status is not None and body.status != tag.status:
        tag.status = body.status
        if body.status == "Void":
            tag.voided_at = datetime.utcnow()
        else:
            tag.voided_at = None
    tag.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(tag)
    return tag_to_dict(tag)


@router.post("/import")
async def import_tags_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    created, skipped = 0, 0
    for row in reader:
        tn = (row.get("tag_number") or "").strip().upper()
        if not tn:
            skipped += 1
            continue
        existing = await db.execute(select(Tag).where(Tag.tag_number == tn))
        if existing.scalar():
            skipped += 1
            continue
        tag = Tag(
            tag_number=tn,
            tag_description=row.get("tag_description", ""),
            discipline=row.get("discipline", ""),
            status=row.get("status", "Active"),
            created_by=row.get("created_by", "import"),
        )
        db.add(tag)
        created += 1
    await db.commit()
    return {"created": created, "skipped": skipped}


@router.get("/{tag_number}/documents")
async def get_tag_documents(tag_number: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TagDocumentRelationship).where(
        TagDocumentRelationship.tag_number == tag_number.upper()
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
