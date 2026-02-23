from django.urls import path
from . import page_views

urlpatterns = [
    path("dashboard/",    page_views.dashboard,    name="dashboard"),
    path("tags/",         page_views.tag_list,     name="tag-list"),
    path("tags/<int:pk>/",page_views.tag_detail,   name="tag-detail"),
]
