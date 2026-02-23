"""
Assets API views — Tag CTDB, plants, disciplines, change requests, imports.
"""
import csv
import io
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from .models import (
    Plant, Area, Unit, Discipline, TagClass, CriticalityLevel,
    Tag, TagStatusHistory, TagAttribute, TagGroup,
    ChangeRequest, ImportBatch, ImportBatchItem, TagStatus,
)
from .serializers import (
    PlantSerializer, AreaSerializer, UnitSerializer,
    DisciplineSerializer, TagClassSerializer, CriticalityLevelSerializer,
    TagListSerializer, TagDetailSerializer, TagGroupSerializer,
    TagStatusHistorySerializer, TagAttributeSerializer,
    ChangeRequestSerializer, ImportBatchSerializer,
)


# ---------------------------------------------------------------------------
# Filter classes
# ---------------------------------------------------------------------------

class TagFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=TagStatus.choices)
    discipline = django_filters.ModelChoiceFilter(queryset=Discipline.objects.all())
    plant = django_filters.ModelChoiceFilter(queryset=Plant.objects.all())
    is_safety_critical = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(tag_number__icontains=value) | Q(tag_description__icontains=value)
        )

    class Meta:
        model = Tag
        fields = ["status", "discipline", "plant", "is_safety_critical"]


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class PlantViewSet(viewsets.ModelViewSet):
    queryset = Plant.objects.filter(is_deleted=False).order_by("code")
    serializer_class = PlantSerializer
    search_fields = ["code", "name", "location"]


class DisciplineViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Discipline.objects.filter(is_active=True).order_by("name")
    serializer_class = DisciplineSerializer


class TagClassViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TagClass.objects.filter(is_active=True).select_related("discipline")
    serializer_class = TagClassSerializer


class CriticalityLevelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CriticalityLevel.objects.all()
    serializer_class = CriticalityLevelSerializer


class TagViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Tags (the CTDB).

    Extra actions:
      POST  /tags/{id}/toggle-status/   — Toggle Active ↔ Void
      GET   /tags/{id}/history/         — Status change history
      GET   /tags/{id}/impact/          — Documents referencing this tag
      GET   /tags/stats/                — Aggregate counts
      POST  /tags/import-csv/           — Bulk import from CSV
      GET   /tags/export-csv/           — Export all tags as CSV
    """
    queryset = Tag.objects.filter(is_deleted=False).select_related(
        "discipline", "plant", "unit", "tag_class", "criticality_level", "created_by"
    ).order_by("tag_number")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TagFilter
    search_fields = ["tag_number", "tag_description", "serial_number", "manufacturer"]
    ordering_fields = ["tag_number", "status", "created_at", "updated_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return TagListSerializer
        return TagDetailSerializer

    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        tag = self.get_object()
        reason = request.data.get("reason", "")
        new_status = tag.toggle_status(user=request.user if request.user.is_authenticated else None,
                                       reason=reason)
        return Response({"tag_number": tag.tag_number, "new_status": new_status})

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        tag = self.get_object()
        qs = tag.status_history.all()
        serializer = TagStatusHistorySerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="impact")
    def impact(self, request, pk=None):
        tag = self.get_object()
        from apps.documents.models import TagDocumentLink
        links = TagDocumentLink.objects.filter(tag=tag).select_related(
            "document_revision__document"
        ).order_by("-created_at")
        data = [
            {
                "document_number": lnk.document_revision.document.document_number,
                "document_title": lnk.document_revision.document.title,
                "revision_number": lnk.document_revision.revision_number,
                "verification_status": lnk.verification_status,
                "page_number": lnk.page_number,
                "linked_at": lnk.created_at,
            }
            for lnk in links
        ]
        return Response({
            "tag_number": tag.tag_number,
            "tag_description": tag.tag_description,
            "status": tag.status,
            "affected_document_count": len(data),
            "documents": data,
        })

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        qs = Tag.objects.filter(is_deleted=False)
        total = qs.count()
        by_status = dict(
            qs.values_list("status").annotate(c=Count("id")).values_list("status", "c")
        )
        by_discipline = list(
            qs.values("discipline__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        safety_critical = qs.filter(is_safety_critical=True).count()
        return Response({
            "total_tags": total,
            "active": by_status.get("Active", 0),
            "void": by_status.get("Void", 0),
            "provisional": by_status.get("Provisional", 0),
            "obsolete": by_status.get("Obsolete", 0),
            "safety_critical": safety_critical,
            "by_discipline": by_discipline,
        })

    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        batch = ImportBatch.objects.create(
            batch_type="csv",
            filename=file_obj.name,
            status="processing",
            started_at=timezone.now(),
            initiated_by=request.user if request.user.is_authenticated else None,
        )

        content = file_obj.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        batch.total_rows = len(rows)

        created, updated, skipped, failed = 0, 0, 0, 0
        items = []

        for i, row in enumerate(rows, start=1):
            tn = (row.get("tag_number") or "").strip().upper()
            if not tn:
                failed += 1
                items.append(ImportBatchItem(
                    batch=batch, row_number=i, tag_number=tn,
                    action="skip", status="failed", error_message="Missing tag_number",
                    raw_data=row,
                ))
                continue

            existing = Tag.objects.filter(tag_number=tn, is_deleted=False).first()
            if existing:
                skipped += 1
                items.append(ImportBatchItem(
                    batch=batch, row_number=i, tag_number=tn, tag=existing,
                    action="skip", status="skipped", raw_data=row,
                ))
                continue

            try:
                discipline = None
                if row.get("discipline"):
                    discipline, _ = Discipline.objects.get_or_create(
                        name=row["discipline"], defaults={"code": row["discipline"][:10]}
                    )
                tag = Tag.objects.create(
                    tag_number=tn,
                    tag_description=row.get("tag_description", ""),
                    discipline=discipline,
                    status=row.get("status", "Active"),
                    created_by=request.user if request.user.is_authenticated else None,
                )
                created += 1
                items.append(ImportBatchItem(
                    batch=batch, row_number=i, tag_number=tn, tag=tag,
                    action="create", status="created", raw_data=row,
                ))
            except Exception as exc:
                failed += 1
                items.append(ImportBatchItem(
                    batch=batch, row_number=i, tag_number=tn,
                    action="create", status="failed", error_message=str(exc), raw_data=row,
                ))

        ImportBatchItem.objects.bulk_create(items)
        batch.created_count = created
        batch.updated_count = updated
        batch.skipped_count = skipped
        batch.failed_count = failed
        batch.status = "completed" if failed == 0 else "partial"
        batch.completed_at = timezone.now()
        batch.save()

        return Response({
            "batch_id": batch.id,
            "created": created,
            "skipped": skipped,
            "failed": failed,
            "total": len(rows),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tags_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "tag_number", "tag_description", "discipline", "status",
            "plant", "manufacturer", "serial_number",
            "is_safety_critical", "created_at", "updated_at",
        ])
        for tag in qs:
            writer.writerow([
                tag.tag_number, tag.tag_description,
                tag.discipline.name if tag.discipline else "",
                tag.status,
                tag.plant.code if tag.plant else "",
                tag.manufacturer, tag.serial_number,
                tag.is_safety_critical,
                tag.created_at.strftime("%Y-%m-%d"),
                tag.updated_at.strftime("%Y-%m-%d"),
            ])
        return response


class TagGroupViewSet(viewsets.ModelViewSet):
    queryset = TagGroup.objects.filter(is_active=True).order_by("group_type", "name")
    serializer_class = TagGroupSerializer


class ChangeRequestViewSet(viewsets.ModelViewSet):
    queryset = ChangeRequest.objects.select_related("tag", "created_by").order_by("-created_at")
    serializer_class = ChangeRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["status", "request_type", "priority"]
    search_fields = ["reference_number", "title", "tag__tag_number"]


class ImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImportBatch.objects.order_by("-created_at")
    serializer_class = ImportBatchSerializer


# ---------------------------------------------------------------------------
# Dashboard stats view
# ---------------------------------------------------------------------------

class DashboardStatsView(APIView):
    def get(self, request):
        from apps.documents.models import DocumentRevision
        from apps.verification.models import VerificationSession

        tags_qs = Tag.objects.filter(is_deleted=False)
        total_tags  = tags_qs.count()
        active_tags = tags_qs.filter(status="Active").count()
        void_tags   = tags_qs.filter(status="Void").count()
        safety_critical = tags_qs.filter(is_safety_critical=True).count()

        revs_qs    = DocumentRevision.objects.all()
        total_docs  = revs_qs.count()
        passed_docs = revs_qs.filter(verification_status__in=["pass", "approved"]).count()
        issue_docs  = revs_qs.filter(verification_status="issues").count()
        pending_docs= revs_qs.filter(verification_status="pending").count()

        # Void tag impact alerts
        void_tag_ids = list(tags_qs.filter(status="Void").values_list("id", flat=True))
        from apps.documents.models import TagDocumentLink
        affected_docs = (
            TagDocumentLink.objects
            .filter(tag_id__in=void_tag_ids)
            .values("tag__tag_number", "tag__tag_description")
            .annotate(doc_count=Count("document_revision", distinct=True))
            .order_by("-doc_count")[:10]
        )
        void_alerts = [
            {
                "tag_number": a["tag__tag_number"],
                "tag_description": a["tag__tag_description"],
                "affected_document_count": a["doc_count"],
            }
            for a in affected_docs
        ]

        # Recent sessions
        recent_sessions = VerificationSession.objects.select_related(
            "document_revision__document"
        ).order_by("-started_at")[:5]
        recent = [
            {
                "id": s.id,
                "document_number": s.document_revision.document.document_number,
                "revision": s.document_revision.revision_number,
                "overall_result": s.overall_result,
                "total_tags": s.total_tags_found,
                "started_at": s.started_at,
            }
            for s in recent_sessions
        ]

        return Response({
            "tags": {
                "total": total_tags,
                "active": active_tags,
                "void": void_tags,
                "safety_critical": safety_critical,
            },
            "documents": {
                "total": total_docs,
                "passed": passed_docs,
                "issues": issue_docs,
                "pending": pending_docs,
            },
            "void_tag_alerts": void_alerts,
            "recent_verification_sessions": recent,
        })
