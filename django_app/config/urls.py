"""
Tag Verification System — Root URL configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # DRF browsable API login
    path("api-auth/", include("rest_framework.urls")),

    # REST API (v1)
    path("api/v1/", include("apps.assets.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.verification.urls")),
    path("api/v1/", include("apps.audit.urls")),

    # HTML pages
    path("", include("apps.assets.page_urls")),
    path("", include("apps.documents.page_urls")),
    path("", include("apps.verification.page_urls")),

    # Root redirect → dashboard
    path("", RedirectView.as_view(url="/dashboard/", permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customise admin site
admin.site.site_header = "Tag Verification — Admin"
admin.site.site_title = "Tag Verification"
admin.site.index_title = "Tag Verification System Administration"
