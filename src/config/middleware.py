"""Turn transient database failures into a controlled 503 (docs/API.md; review finding SEC-002)."""
import logging

from django.db import InterfaceError, OperationalError
from django.template.loader import render_to_string
from django.http import HttpResponse

logger = logging.getLogger("northstar.errors")

RETRY_AFTER_SECONDS = "5"


class DatabaseUnavailableMiddleware:
    """Answer 503 with Retry-After when the database is temporarily unavailable.

    Only OperationalError and InterfaceError are treated as transient (connection failures, timeouts,
    deadlocks, a closed connection). Integrity, data and programming errors are bugs, not outages, and still
    surface as 500. The page is rendered without touching the database, and the exception text is never shown
    or logged, only its class. Checkout keeps its idempotency key across this response, so retrying after an
    uncertain outcome resolves the committed order instead of creating a second one.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, (OperationalError, InterfaceError)):
            return None
        logger.warning("database unavailable: %s (%s %s)", type(exception).__name__, request.method, request.path)
        response = HttpResponse(render_to_string("503.html"), status=503)
        response["Retry-After"] = RETRY_AFTER_SECONDS
        response["Cache-Control"] = "no-store"
        return response
