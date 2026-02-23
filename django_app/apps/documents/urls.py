from rest_framework.routers import DefaultRouter
from .views import (
    DocumentTypeViewSet, DocumentViewSet, DocumentRevisionViewSet,
    VerifyDocumentView, TagDocumentLinkViewSet,
)

router = DefaultRouter()
router.register("document-types",    DocumentTypeViewSet,    basename="documenttype")
router.register("documents",         DocumentViewSet,        basename="document")
router.register("document-revisions",DocumentRevisionViewSet,basename="documentrevision")
router.register("verify",            VerifyDocumentView,     basename="verify")
router.register("tag-document-links",TagDocumentLinkViewSet, basename="tagdocumentlink")

urlpatterns = router.urls
