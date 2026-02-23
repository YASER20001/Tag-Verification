from django.urls import path
from . import page_views

urlpatterns = [
    path("verify/",     page_views.verify_document, name="verify-document"),
    path("documents/",  page_views.document_list,   name="document-list"),
    path("impact/",     page_views.impact_analysis, name="impact-analysis"),
]
