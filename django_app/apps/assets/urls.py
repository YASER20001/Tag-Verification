from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    PlantViewSet, DisciplineViewSet, TagClassViewSet, CriticalityLevelViewSet,
    TagViewSet, TagGroupViewSet, ChangeRequestViewSet, ImportBatchViewSet,
    DashboardStatsView,
)

router = DefaultRouter()
router.register("plants",            PlantViewSet,            basename="plant")
router.register("disciplines",       DisciplineViewSet,       basename="discipline")
router.register("tag-classes",       TagClassViewSet,         basename="tagclass")
router.register("criticality-levels",CriticalityLevelViewSet, basename="criticalitylevel")
router.register("tags",              TagViewSet,              basename="tag")
router.register("tag-groups",        TagGroupViewSet,         basename="taggroup")
router.register("change-requests",   ChangeRequestViewSet,    basename="changerequest")
router.register("import-batches",    ImportBatchViewSet,      basename="importbatch")

urlpatterns = router.urls + [
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
]
