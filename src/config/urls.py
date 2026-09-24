from django.urls import include, path
from django.views.generic import RedirectView

from .views import design_notes, design_notes_unavailable, foundation_preview, health, statistics_preview

urlpatterns = [
    # The storefront is the landing page; one canonical catalogue URL, so this redirects rather than re-serving it.
    path("", RedirectView.as_view(pattern_name="catalogue:product_list"), name="home"),
    path("foundation/", foundation_preview, name="foundation-preview"),
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
