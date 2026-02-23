"""HTML page views for Tag/CTDB pages."""
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count

from .models import Tag, Discipline, Plant, TagStatus


def dashboard(request):
    from apps.documents.models import DocumentRevision, TagDocumentLink
    tags_qs = Tag.objects.filter(is_deleted=False)
    total_tags   = tags_qs.count()
    active_tags  = tags_qs.filter(status="Active").count()
    void_tags    = tags_qs.filter(status="Void").count()
    safety_tags  = tags_qs.filter(is_safety_critical=True).count()

    revs_qs = DocumentRevision.objects.all()
    total_docs   = revs_qs.count()
    passed_docs  = revs_qs.filter(verification_status__in=["pass", "approved"]).count()
    issue_docs   = revs_qs.filter(verification_status="issues").count()
    pending_docs = revs_qs.filter(verification_status="pending").count()

    by_discipline = list(
        tags_qs.values("discipline__name", "discipline__colour")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    void_tag_ids = list(tags_qs.filter(status="Void").values_list("id", flat=True))
    void_alerts = (
        TagDocumentLink.objects
        .filter(tag_id__in=void_tag_ids)
        .values("tag__tag_number", "tag__tag_description")
        .annotate(doc_count=Count("document_revision", distinct=True))
        .order_by("-doc_count")[:10]
    )

    context = {
        "total_tags": total_tags,
        "active_tags": active_tags,
        "void_tags": void_tags,
        "safety_tags": safety_tags,
        "total_docs": total_docs,
        "passed_docs": passed_docs,
        "issue_docs": issue_docs,
        "pending_docs": pending_docs,
        "by_discipline": by_discipline,
        "void_alerts": void_alerts,
    }
    return render(request, "dashboard.html", context)


def tag_list(request):
    qs = Tag.objects.filter(is_deleted=False).select_related("discipline", "plant")
    search    = request.GET.get("q", "")
    discipline = request.GET.get("discipline", "")
    status_f  = request.GET.get("status", "")

    if search:
        qs = qs.filter(Q(tag_number__icontains=search) | Q(tag_description__icontains=search))
    if discipline:
        qs = qs.filter(discipline__name=discipline)
    if status_f:
        qs = qs.filter(status=status_f)

    qs = qs.order_by("tag_number")[:200]

    disciplines = Discipline.objects.filter(is_active=True).values_list("name", flat=True)
    context = {
        "tags": qs,
        "disciplines": disciplines,
        "search": search,
        "selected_discipline": discipline,
        "selected_status": status_f,
        "statuses": TagStatus.choices,
    }
    return render(request, "tags/list.html", context)


def tag_detail(request, pk):
    tag = get_object_or_404(Tag, pk=pk, is_deleted=False)
    history = tag.status_history.order_by("-changed_at")[:20]
    from apps.documents.models import TagDocumentLink
    links = TagDocumentLink.objects.filter(tag=tag).select_related(
        "document_revision__document"
    ).order_by("-created_at")[:50]
    context = {"tag": tag, "history": history, "links": links}
    return render(request, "tags/detail.html", context)
