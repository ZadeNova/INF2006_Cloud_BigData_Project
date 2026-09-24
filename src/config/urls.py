from django.urls import include, path
from .views import design_notes, design_notes_unavailable, health, home, statistics_preview

urlpatterns = [
    path("", home, name="home"),
    path("", include("accounts.urls")),
    path("", include("orders.urls")),
    path("products/", include("catalogue.urls")),
    path("cart/", include("cart.urls")),
    path("analytics/", include("reporting.urls")),
    path("foundation/design-notes/", design_notes, name="design-notes"),
    path("foundation/design-notes-unavailable/", design_notes_unavailable, name="design-notes-unavailable"),
    path("foundation/statistics/", statistics_preview, name="statistics-preview"),
    path("health/", health, name="health"),
]
