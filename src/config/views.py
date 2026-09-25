from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe


@require_safe
def foundation_preview(request):
    """Presentation-only frontend foundation preview, kept as reviewed design evidence; the shop is at /."""
    return render(request, "foundation/home.html")


@require_safe
def design_notes(request):
    """Return the small presentation fragment used to prove the HTMX wiring."""
    return render(request, "foundation/_design-notes.html")


@require_safe
def design_notes_unavailable(request):
    """Return a presentation-only 503 fragment for exercising HTMX failure UI."""
    return render(request, "foundation/_design-notes-unavailable.html", status=503)


@require_safe
def statistics_preview(request):
    """Presentation-only operator dashboard comp. Every figure is invented.

    The real dashboard is batch 06c and reads reporting.queries against a
    completed analytics run; it lives at its own protected route. This one is
    a design comp with hardcoded numbers, so it deliberately sits in the
    foundation preview namespace and has no permission check to imply.
    """
    return render(request, "foundation/statistics.html")


@require_safe
def health(request):
    """Process liveness, deliberately independent of shared database availability."""
    request.get_host()  # Apply the explicit host policy even for this minimal response.
    return health_response()


def health_response():
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store"
    return response
