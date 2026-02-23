from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import VerificationSession, VerificationResult
from .serializers import VerificationSessionSerializer, VerificationResultSerializer


class VerificationSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VerificationSession.objects.select_related(
        "document_revision__document", "initiated_by"
    ).order_by("-started_at")
    serializer_class = VerificationSessionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["overall_result", "status", "document_revision__document"]
    ordering_fields = ["started_at", "total_tags_found"]

    @action(detail=True, methods=["get"], url_path="results")
    def results(self, request, pk=None):
        session = self.get_object()
        qs = session.results.all().order_by("tag_number")
        serializer = VerificationResultSerializer(qs, many=True)
        return Response(serializer.data)
