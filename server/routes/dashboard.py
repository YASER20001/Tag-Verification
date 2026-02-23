"""
Dashboard statistics routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import Tag, Document, TagDocumentRelationship

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_tags = (await db.execute(select(func.count()).select_from(Tag))).scalar()
    active_tags = (
        await db.execute(select(func.count()).select_from(Tag).where(Tag.status == "Active"))
    ).scalar()
    void_tags = (
        await db.execute(select(func.count()).select_from(Tag).where(Tag.status == "Void"))
    ).scalar()
    total_docs = (await db.execute(select(func.count()).select_from(Document))).scalar()
    passed_docs = (
        await db.execute(
            select(func.count()).select_from(Document).where(
                Document.verification_status.in_(["pass", "approved"])
            )
        )
    ).scalar()
    issue_docs = (
        await db.execute(
            select(func.count()).select_from(Document).where(
                Document.verification_status == "issues"
            )
        )
    ).scalar()

    return {
        "total_tags": total_tags,
        "active_tags": active_tags,
        "void_tags": void_tags,
        "total_documents": total_docs,
        "passed_documents": passed_docs,
        "issue_documents": issue_docs,
    }


@router.get("/recent")
async def get_recent(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Document)
        .order_by(desc(Document.uploaded_at))
        .limit(10)
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "document_number": d.document_number,
            "document_title": d.document_title,
            "document_revision": d.document_revision,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            "verification_status": d.verification_status,
            "tags_found": d.tags_found,
            "tags_valid": d.tags_valid,
            "tags_void": d.tags_void,
            "tags_not_found": d.tags_not_found,
        }
        for d in docs
    ]


@router.get("/alerts")
async def get_alerts(db: AsyncSession = Depends(get_db)):
    """
    Return voided tags that are still referenced in documents via relationships.
    """
    # Tags that are Void
    void_tags_result = await db.execute(
        select(Tag).where(Tag.status == "Void")
    )
    void_tags = {t.tag_number: t for t in void_tags_result.scalars().all()}

    if not void_tags:
        return []

    # Relationships referencing those void tags
    rel_result = await db.execute(
        select(TagDocumentRelationship).where(
            TagDocumentRelationship.tag_number.in_(list(void_tags.keys()))
        )
    )
    rels = rel_result.scalars().all()

    # Group by tag
    alerts: dict[str, dict] = {}
    for r in rels:
        tn = r.tag_number
        if tn not in alerts:
            tag = void_tags[tn]
            alerts[tn] = {
                "tag_number": tn,
                "tag_description": tag.tag_description,
                "voided_at": tag.voided_at.isoformat() if tag.voided_at else None,
                "affected_documents": [],
            }
        alerts[tn]["affected_documents"].append(
            {
                "document_number": r.document_number,
                "document_title": r.document_title,
                "document_revision": r.document_revision,
            }
        )

    result_list = list(alerts.values())
    result_list.sort(key=lambda x: len(x["affected_documents"]), reverse=True)
    return result_list
