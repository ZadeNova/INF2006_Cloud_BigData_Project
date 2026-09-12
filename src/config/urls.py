from django.urls import path
from .views import design_notes, health, home

urlpatterns = [
    path("", home, name="home"),
    path("foundation/design-notes/", design_notes, name="design-notes"),
    path("health/", health, name="health"),
]
