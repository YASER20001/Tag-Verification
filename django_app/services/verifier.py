"""
Verification engine — Django ORM version.
Compares detected tags against the CTDB and returns per-tag results.
"""
from apps.assets.models import Tag

VALID_ACTIVE = "valid_active"
VALID_VOID   = "valid_void"
NOT_FOUND    = "not_found"
SHORTHAND    = "shorthand_detected"


def verify_tags_sync(flat_tags: list[dict]) -> list[dict]:
    """
    Verify a flat list of tag dicts against the CTDB using Django ORM.

    flat_tags: output of services.tag_detector.flatten_detected_tags()
    Returns the same list with added keys:
        verification_status, ctdb_description, ctdb_discipline, tag_id
    """
    if not flat_tags:
        return []

    tag_numbers = [t["tag_number"] for t in flat_tags]

    # Bulk-fetch all relevant tags in one query
    db_tags: dict[str, Tag] = {
        t.tag_number: t
        for t in Tag.objects.filter(tag_number__in=tag_numbers, is_deleted=False)
    }

    verified = []
    for t in flat_tags:
        num = t["tag_number"]
        db_tag = db_tags.get(num)

        if db_tag is None:
            status = SHORTHAND if t.get("is_shorthand") else NOT_FOUND
            description = ""
            discipline = ""
            tag_id = None
        elif db_tag.status == "Active":
            status = VALID_ACTIVE
            description = db_tag.tag_description or ""
            discipline = db_tag.get_discipline_name()
            tag_id = db_tag.id
        else:
            status = VALID_VOID
            description = db_tag.tag_description or ""
            discipline = db_tag.get_discipline_name()
            tag_id = db_tag.id

        verified.append({
            **t,
            "verification_status": status,
            "ctdb_description": description,
            "ctdb_discipline": discipline,
            "tag_id": tag_id,
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
    return {
        "total": total,
        "valid_active": counts[VALID_ACTIVE],
        "valid_void": counts[VALID_VOID],
        "not_found": counts[NOT_FOUND],
        "shorthand_detected": counts[SHORTHAND],
        "overall_status": "issues" if has_issues else "pass",
    }
