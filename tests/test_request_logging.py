"""Request logging: IDs, durations, sanitised errors, nothing sensitive (review finding SEC-001)."""
import io
import json
import logging
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.db.backends.postgresql.base import DatabaseWrapper
from django.test import Client
from django.urls import reverse

from config.jsonlog import JsonFormatter

pytestmark = pytest.mark.django_db
LOGGERS = ("northstar", "django.request", "django.security")


class Captured:
    def __init__(self, stream):
        self.stream = stream

    @property
    def raw(self):
        return self.stream.getvalue()

    def records(self, logger=None):
        found = [json.loads(line) for line in self.raw.splitlines() if line.strip()]
        return [record for record in found if logger is None or record["logger"] == logger]

    def request_lines(self):
        return self.records("northstar.request")


@pytest.fixture
def logs():
    """The JSON lines our loggers emit, formatted by the real formatter."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    loggers = [logging.getLogger(name) for name in LOGGERS]
    for logger in loggers:
        logger.addHandler(handler)
    yield Captured(stream)
    for logger in loggers:
        logger.removeHandler(handler)


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="shopper", password="Sup3rSecret!pass")


def test_a_request_produces_exactly_one_line_with_the_documented_fields(logs):
    response = Client().get(reverse("catalogue:product_list"))

    (line,) = logs.request_lines()
    assert set(line) == {"ts", "level", "logger", "message", "request_id", "method", "path", "status",
                         "duration_ms", "user_id"}
    assert (line["method"], line["path"], line["status"], line["level"]) == ("GET", "/products/", 200, "INFO")
    assert isinstance(line["duration_ms"], float) and line["duration_ms"] >= 0
    assert line["user_id"] is None
    assert len(line["request_id"]) == 32 and response["X-Request-ID"] == line["request_id"]


def test_the_numeric_user_id_is_logged_when_the_view_loaded_the_user(logs, user):
    client = Client()
    client.force_login(user)

    client.get(reverse("cart:detail"))

    assert logs.request_lines()[-1]["user_id"] == user.pk
    assert "shopper" not in logs.raw                       # the username is never logged


def test_logging_never_queries_the_database(logs, django_assert_num_queries):
    with django_assert_num_queries(0):
        Client().get("/health/")


def test_health_probes_are_not_logged_at_info(logs):
    Client().get("/health/")

    assert logs.request_lines() == []


@pytest.mark.parametrize("incoming", ["short", "has spaces in it", "x" * 65, 'abcdefgh\n{"forged":true}', "id/with/slashes"])
def test_an_unsafe_incoming_request_id_is_replaced(logs, incoming):
    response = Client().get(reverse("catalogue:product_list"), HTTP_X_REQUEST_ID=incoming)

    (line,) = logs.request_lines()
    assert line["request_id"] != incoming and response["X-Request-ID"] == line["request_id"]
    assert "forged" not in logs.raw


def test_a_safe_incoming_request_id_is_kept_so_a_proxy_can_correlate(logs):
    response = Client().get(reverse("catalogue:product_list"), HTTP_X_REQUEST_ID="proxy-1234.abcd")

    assert logs.request_lines()[0]["request_id"] == "proxy-1234.abcd" == response["X-Request-ID"]


def test_query_strings_are_not_logged(logs):
    Client().get("/products/?token=SECRET123&page=1")

    assert logs.request_lines()[0]["path"] == "/products/"
    assert "SECRET123" not in logs.raw and "token" not in logs.raw


def test_a_login_post_logs_neither_the_password_nor_the_cookie(logs, user):
    client = Client()
    client.cookies["sessionid"] = "COOKIEVALUE123"
    client.cookies["csrftoken"] = "c" * 32

    client.post(reverse("accounts:login"), {"username": "shopper", "password": "Sup3rSecret!pass"},
                HTTP_AUTHORIZATION="Bearer BEARERTOKEN999")
    client.post(reverse("accounts:login"), {"username": "shopper", "password": "wrong-Passw0rd"})

    assert len(logs.request_lines()) == 2
    for secret in ("Sup3rSecret", "wrong-Passw0rd", "COOKIEVALUE123", "BEARERTOKEN999", "csrftoken", "password"):
        assert secret not in logs.raw


def test_a_controlled_failure_can_be_correlated_without_leaking_its_message(logs, user):
    client = Client(raise_request_exception=False)
    client.force_login(user)

    with mock.patch("cart.services.get_cart", side_effect=ValueError("secret-detail password=hunter2")):
        response = client.get(reverse("cart:detail"))

    assert response.status_code == 500
    request_id = response["X-Request-ID"]
    (line,) = logs.request_lines()
    assert (line["status"], line["level"], line["exception"], line["request_id"]) == (500, "ERROR", "ValueError", request_id)
    (error,) = logs.records("django.request")
    assert error["exception"] == "ValueError" and error["request_id"] == request_id
    assert error["frames"] and all(":" in frame for frame in error["frames"])
    assert any("cart/views.py" in frame for frame in error["frames"])         # the frame that called the failing code
    for secret in ("secret-detail", "hunter2"):
        assert secret not in logs.raw


def test_a_database_outage_is_logged_with_its_class_and_request_id_and_without_a_lookup(logs, user):
    client = Client()
    client.force_login(user)

    with mock.patch.object(DatabaseWrapper, "create_cursor", side_effect=OperationalError("db-secret-host refused")):
        response = client.get(reverse("cart:detail"))

    assert response.status_code == 503
    (line,) = logs.request_lines()
    assert (line["status"], line["level"], line["exception"], line["user_id"]) == (503, "ERROR", "OperationalError", None)
    (warning,) = logs.records("northstar.errors")
    assert warning["request_id"] == line["request_id"] == response["X-Request-ID"]
    assert "OperationalError" in warning["message"] and "db-secret-host" not in logs.raw


def test_client_errors_are_logged_at_info_with_their_status(logs):
    Client().get("/no/such/page/")

    (line,) = logs.request_lines()
    assert (line["status"], line["level"]) == (404, "INFO")


# --- formatter and configuration -----------------------------------------------------------------

def test_the_formatter_emits_one_line_and_reduces_exceptions_to_class_and_frames():
    try:
        raise KeyError("secret\nmultiline value")
    except KeyError:
        import sys
        record = logging.LogRecord("x", logging.ERROR, __file__, 1, "multi\nline message", (), sys.exc_info())

    output = JsonFormatter().format(record)

    assert "\n" not in output
    payload = json.loads(output)
    assert payload["exception"] == "KeyError" and payload["frames"]
    assert "secret" not in output and "multiline value" not in output
    assert payload["message"] == "multi\nline message"


def test_the_formatter_tolerates_values_that_are_not_json_serialisable():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "m", (), None)
    record.fields = {"when": object()}

    assert json.loads(JsonFormatter().format(record))["when"].startswith("<object object")


def test_logging_is_configured_for_json_on_standard_output():
    handlers = logging.getLogger("northstar").handlers
    assert handlers and isinstance(handlers[0].formatter, JsonFormatter)
    assert logging.getLogger("northstar.request").getEffectiveLevel() == logging.INFO
    assert settings.LOGGING["loggers"]["django.request"]["propagate"] is False
