"""HTML page views for Document / Verification pages."""
from django.shortcuts import render
from django.db.models import Q

from .models import Document, DocumentRevision


def verify_document(request):
    return render(request, "documents/verify.html", {})


def document_list(request):
    qs = Document.objects.filter(is_active=True).select_related(
        "document_type", "current_revision"
    ).order_by("-created_at")
    search = request.GET.get("q", "")
    if search:
        qs = qs.filter(
            Q(document_number__icontains=search) | Q(title__icontains=search)
        )
    context = {"documents": qs[:100], "search": search}
    return render(request, "documents/list.html", context)


def impact_analysis(request):
    from apps.assets.models import Tag
    from .models import TagDocumentLink

    tag_number = request.GET.get("tag", "").strip().upper()
    tag_obj = None
    links = []
    if tag_number:
        tag_obj = Tag.objects.filter(tag_number=tag_number, is_deleted=False).first()
        if tag_obj:
            links = TagDocumentLink.objects.filter(tag=tag_obj).select_related(
                "document_revision__document"
            ).order_by("-created_at")

    context = {
        "tag_number": tag_number,
        "tag": tag_obj,
        "links": links,
    }
    return render(request, "documents/impact.html", context)
