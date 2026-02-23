from django.urls import path
from . import page_views

urlpatterns = [
    path("sessions/", page_views.session_list, name="session-list"),
]
