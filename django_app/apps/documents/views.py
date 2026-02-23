"""
Documents API views — document CRUD, verification trigger, tag impact.
"""
import hashlib
import os
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend

from .models import DocumentType, Document, DocumentRevision, DocumentFile, TagDocumentLink
from .serializers import (
    DocumentTypeSerializer, DocumentListSerializer, DocumentDetailSerializer,
    DocumentRevisionSerializer, TagDocumentLinkSerializer,
)


class DocumentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DocumentType.objects.filter(is_active=True)
    serializer_class = DocumentTypeSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.filter(is_active=True).select_related(
        "document_type", "current_revision"
    ).order_by("-created_at")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["document_number", "title", "project_number"]
    ordering_fields = ["document_number", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        return DocumentDetailSerializer


class DocumentRevisionViewSet(viewsets.ModelViewSet):
    queryset = DocumentRevision.objects.select_related("document", "approved_by").order_by("-created_at")
    serializer_class = DocumentRevisionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["document", "verification_status", "status"]

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        revision = self.get_object()
        justification = request.data.get("justification", "")
        user = request.user if request.user.is_authenticated else None
        revision.approve(user=user, justification=justification)
        return Response({
            "status": "approved",
            "approved_by": user.username if user else "anonymous",
            "justification": justification,
        })


class VerifyDocumentView(viewsets.ViewSet):
    """
    POST /api/v1/verify/
    Accepts a multipart form with:
      - file: PDF / image file
      - document_number: str
      - document_title: str (optional)
      - revision_number: str (default "0")
    Returns full verification results and saves to DB.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request):
        import time
        from services.tag_detector import extract_tags_from_text, flatten_detected_tags
        from services.pdf_extractor import extract_text_from_file
        from services.verifier import verify_tags_sync, summarise_results
        from apps.assets.models import Tag
        from apps.verification.models import VerificationSession, VerificationResult

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        doc_number = (request.data.get("document_number") or "").strip()
        if not doc_number:
            return Response({"error": "document_number is required."}, status=status.HTTP_400_BAD_REQUEST)

        doc_title    = request.data.get("document_title", doc_number).strip()
        rev_number   = request.data.get("revision_number", "0").strip() or "0"
        user = request.user if request.user.is_authenticated else None

        # ---- Get or create Document + DocumentRevision ----
        document, _ = Document.objects.get_or_create(
            document_number=doc_number,
            defaults={"title": doc_title, "created_by": user},
        )
        revision, _ = DocumentRevision.objects.get_or_create(
            document=document,
            revision_number=rev_number,
            defaults={"title": doc_title, "created_by": user},
        )

        # ---- Read file ----
        file_bytes = file_obj.read()
        filename = file_obj.name
        file_size = len(file_bytes)
        checksum = hashlib.md5(file_bytes).hexdigest()

        # ---- Save physical file ----
        from django.conf import settings
        upload_dir = os.path.join(settings.MEDIA_ROOT, "documents")
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"{checksum}_{filename}"
        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, "wb") as fh:
            fh.write(file_bytes)

        DocumentFile.objects.update_or_create(
            revision=revision,
            defaults={
                "filename": filename,
                "file_path": file_path,
                "file_size": file_size,
                "checksum_md5": checksum,
                "mime_type": file_obj.content_type or "",
                "uploaded_by": user,
            },
        )

        # ---- Extract text ----
        t0 = time.time()
        extraction = extract_text_from_file(file_bytes, filename)
        full_text = extraction.get("full_text", "")
        extraction_method = extraction.get("method", "unknown")
        page_count = extraction.get("page_count", 0)

        # ---- Detect + verify tags ----
        detected = extract_tags_from_text(full_text)
        flat_tags = flatten_detected_tags(detected)
        verified = verify_tags_sync(flat_tags)
        summary = summarise_results(verified)
        duration = time.time() - t0

        # ---- Create VerificationSession ----
        session = VerificationSession.objects.create(
            document_revision=revision,
            status="completed",
            extraction_method=extraction_method,
            page_count=page_count,
            initiated_by=user,
            completed_at=timezone.now(),
            duration_seconds=round(duration, 2),
            total_tags_found=summary["total"],
            tags_valid_active=summary["valid_active"],
            tags_valid_void=summary["valid_void"],
            tags_not_found=summary["not_found"],
            tags_shorthand=summary["shorthand_detected"],
            overall_result=summary["overall_status"],
        )

        # ---- Save per-tag results ----
        result_objs = []
        for t in verified:
            tag_obj = None
            if t.get("tag_id"):
                try:
                    tag_obj = Tag.objects.get(id=t["tag_id"])
                except Tag.DoesNotExist:
                    pass
            result_objs.append(VerificationResult(
                session=session,
                tag_number=t["tag_number"],
                raw_text=t.get("raw_text", ""),
                is_shorthand=t.get("is_shorthand", False),
                original_shorthand=t.get("original_shorthand") or "",
                page_number=t.get("page_number"),
                verification_status=t["verification_status"],
                ctdb_description=t.get("ctdb_description", ""),
                ctdb_discipline=t.get("ctdb_discipline", ""),
                tag=tag_obj,
            ))
        VerificationResult.objects.bulk_create(result_objs)

        # ---- Update DocumentRevision summary ----
        revision.verification_status = summary["overall_status"]
        revision.tags_found = summary["total"]
        revision.tags_valid_active = summary["valid_active"]
        revision.tags_valid_void = summary["valid_void"]
        revision.tags_not_found = summary["not_found"]
        revision.tags_shorthand = summary["shorthand_detected"]
        revision.save()

        # ---- Update Document.current_revision ----
        document.current_revision = revision
        document.save(update_fields=["current_revision"])

        # ---- Save TagDocumentLinks ----
        link_objs = []
        for t in verified:
            tag_obj = None
            if t.get("tag_id"):
                try:
                    tag_obj = Tag.objects.get(id=t["tag_id"])
                except Tag.DoesNotExist:
                    pass
            if tag_obj:
                link_objs.append(TagDocumentLink(
                    tag=tag_obj,
                    document_revision=revision,
                    verification_status=t["verification_status"],
                    raw_text=t.get("raw_text", ""),
                    page_number=t.get("page_number"),
                    is_shorthand=t.get("is_shorthand", False),
                    original_shorthand=t.get("original_shorthand") or "",
                    linked_by=user,
                ))
        if link_objs:
            TagDocumentLink.objects.bulk_create(link_objs, ignore_conflicts=True)

        return Response({
            "session_id": session.id,
            "document_number": doc_number,
            "revision_number": rev_number,
            "extraction_method": extraction_method,
            "page_count": page_count,
            "duration_seconds": round(duration, 2),
            "summary": summary,
            "tags": verified,
        }, status=status.HTTP_201_CREATED)


class TagDocumentLinkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TagDocumentLink.objects.select_related(
        "tag", "document_revision__document"
    ).order_by("-created_at")
    serializer_class = TagDocumentLinkSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["tag", "document_revision", "verification_status"]
