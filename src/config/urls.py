from django.urls import path
from .views import design_notes, design_notes_unavailable, health, home

urlpatterns = [
    path("", home, name="home"),
    path("foundation/design-notes/", design_notes, name="design-notes"),
    path("foundation/design-notes-unavailable/", design_notes_unavailable, name="design-notes-unavailable"),
    path("health/", health, name="health"),
]
