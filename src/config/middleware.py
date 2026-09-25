"""Turn transient database failures into a controlled 503 (docs/API.md; review finding SEC-002)."""
import logging
import re
import time
import uuid

from django.conf import settings
from django.db import InterfaceError, OperationalError
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.functional import empty

logger = logging.getLogger("northstar.errors")
request_logger = logging.getLogger("northstar.request")

RETRY_AFTER_SECONDS = "5"
# An incoming X-Request-ID is reused only if it is short and plain, so it cannot carry log-injection text.
SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")


class HealthProbeMiddleware:
    """Exact internal ALB probe exception; ordinary requests keep explicit Host validation."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (settings.HEALTH_PROBE_HOST and request.META.get("HTTP_HOST") == settings.HEALTH_PROBE_HOST
                and request.path_info == "/health/" and request.method in {"GET", "HEAD"}):
            from config.views import health_response
            return health_response()
        request.get_host()
        return self.get_response(request)


class RequestLoggingMiddleware:
    """Give every request an ID and log one JSON line with method, path, status, duration and user ID.

    Logged: request ID, method, path without the query string, status code, duration in milliseconds, the
    numeric user ID if the user was already resolved, and the exception class if the view raised. Never
    logged: query strings, cookies, headers, request bodies, usernames or exception messages. The user is not
    resolved here, so logging never queries the database (it must keep working during a database outage).
    Health probes and static files are logged at DEBUG unless they fail.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = self._request_id(request)
        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response["X-Request-ID"] = request.request_id

        if response.status_code >= 500:
            level = logging.ERROR
        elif request.path.startswith(("/health/", settings.STATIC_URL)):
            level = logging.DEBUG
        else:
            level = logging.INFO
        fields = {
            "request_id": request.request_id, "method": request.method, "path": request.path,
            "status": response.status_code, "duration_ms": duration_ms, "user_id": self._user_id(request),
        }
        exception = getattr(request, "_logged_exception", None)
        if exception:
            fields["exception"] = exception
        request_logger.log(level, "request", extra={"fields": fields})
        return response

    def process_exception(self, request, exception):
        request._logged_exception = type(exception).__name__      # class only; the message may hold user data
        return None

    @staticmethod
    def _request_id(request):
        incoming = request.headers.get("X-Request-ID", "")
        return incoming if SAFE_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex

    @staticmethod
    def _user_id(request):
        """The numeric user ID if the user object was already loaded; never triggers a lookup."""
        wrapped = getattr(getattr(request, "user", None), "_wrapped", empty)
        if wrapped is empty or not getattr(wrapped, "is_authenticated", False):
            return None
        return wrapped.pk


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
        logger.warning("database unavailable: %s (%s %s)", type(exception).__name__, request.method, request.path,
                       extra={"fields": {"request_id": getattr(request, "request_id", None)}})
        response = HttpResponse(render_to_string("503.html"), status=503)
        response["Retry-After"] = RETRY_AFTER_SECONDS
        response["Cache-Control"] = "no-store"
        return response
