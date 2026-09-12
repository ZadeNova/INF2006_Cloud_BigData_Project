from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe


@require_safe
def home(request):
    """Presentation-only frontend foundation preview until business routes land."""
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
def health(request):
    """Process liveness, deliberately independent of shared database availability."""
    request.get_host()  # Apply the explicit host policy even for this minimal response.
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store"
    return response
