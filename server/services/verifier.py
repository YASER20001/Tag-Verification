"""
Verification engine.
Compares detected tags against the CTDB and returns per-tag results.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Tag


VALID_ACTIVE = "valid_active"
VALID_VOID   = "valid_void"
NOT_FOUND    = "not_found"
SHORTHAND    = "shorthand_detected"


async def verify_tags(flat_tags: list[dict], db: AsyncSession) -> list[dict]:
    """
    flat_tags: output of flatten_detected_tags()
    Returns same list with added keys: verification_status, ctdb_description, ctdb_discipline
    """
    # Bulk-load all relevant tags from DB in one query
    tag_numbers = [t["tag_number"] for t in flat_tags]
    if not tag_numbers:
        return []

    stmt = select(Tag).where(Tag.tag_number.in_(tag_numbers))
    result = await db.execute(stmt)
    db_tags: dict[str, Tag] = {row.tag_number: row for row in result.scalars()}

    verified = []
    for t in flat_tags:
        num = t["tag_number"]
        db_tag = db_tags.get(num)

        if db_tag is None:
            status = NOT_FOUND
            description = None
            discipline = None
        elif db_tag.status == "Active":
            status = VALID_ACTIVE
            description = db_tag.tag_description
            discipline = db_tag.discipline
        else:
            status = VALID_VOID
            description = db_tag.tag_description
            discipline = db_tag.discipline

        # Override status for confirmed shorthands
        if t.get("is_shorthand") and status in (NOT_FOUND,):
            # Still flag as shorthand_detected even if not found,
            # so the user can confirm intent first.
            status = SHORTHAND

        verified.append({
            **t,
            "verification_status": status,
            "ctdb_description": description,
            "ctdb_discipline": discipline,
        })

    return verified


def summarise_results(verified: list[dict]) -> dict:
    total = len(verified)
    counts = {VALID_ACTIVE: 0, VALID_VOID: 0, NOT_FOUND: 0, SHORTHAND: 0}
    for t in verified:
        s = t.get("verification_status", NOT_FOUND)
        if s in counts:
            counts[s] += 1

    has_issues = counts[VALID_VOID] > 0 or counts[NOT_FOUND] > 0 or counts[SHORTHAND] > 0
    overall = "issues" if has_issues else "pass"

    return {
        "total": total,
        "valid_active": counts[VALID_ACTIVE],
        "valid_void": counts[VALID_VOID],
        "not_found": counts[NOT_FOUND],
        "shorthand_detected": counts[SHORTHAND],
        "overall_status": overall,
    }
