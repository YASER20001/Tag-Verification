"""HTML page views for Verification session pages."""
from django.shortcuts import render
from .models import VerificationSession


def session_list(request):
    sessions = VerificationSession.objects.select_related(
        "document_revision__document"
    ).order_by("-started_at")[:50]
    context = {"sessions": sessions}
    return render(request, "verification/sessions.html", context)
