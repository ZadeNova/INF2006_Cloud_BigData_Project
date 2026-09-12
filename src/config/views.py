from django.http import JsonResponse
from django.views.decorators.http import require_safe

@require_safe
def health(request):
    """Process liveness, deliberately independent of shared database availability."""
    request.get_host()  # Apply the explicit host policy even for this minimal response.
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store"
    return response
