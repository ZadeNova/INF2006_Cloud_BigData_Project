from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_health_is_safe_and_has_no_database_queries(client, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = client.get(reverse("health"))
        head = client.head(reverse("health"))
    assert response.status_code == head.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response["Cache-Control"] == "no-store"
    assert response["Content-Type"] == "application/json"
    assert not head.content
    assert not response.cookies


def test_health_survives_database_failure(client):
    with patch("django.db.backends.postgresql.base.DatabaseWrapper.get_new_connection",
               side_effect=OperationalError("private connection details")):
        assert client.get("/health/").status_code == 200


def test_health_rejects_mutations(client):
    assert client.post("/health/").status_code == 405
    assert client.delete("/health/").status_code == 405


@override_settings(ALLOWED_HOSTS=["localhost"])
def test_health_validates_host(client):
    assert client.get("/health/", HTTP_HOST="unexpected.example").status_code == 400


@override_settings(SECURE_SSL_REDIRECT=True)
def test_health_exempt_from_redirect_for_internal_checks(client):
    assert client.get("/health/").status_code == 200


@pytest.mark.django_db
def test_database_readiness_command():
    output = StringIO()
    call_command("check_database", stdout=output)
    assert output.getvalue().strip() == '{"database": "ok", "migrations": "applied"}'


def test_database_failure_is_sanitized():
    with patch("config.management.commands.check_database.connection.cursor",
               side_effect=OperationalError("private connection details")):
        with pytest.raises(CommandError, match=r"^Database unavailable\.$"):
            call_command("check_database")


@pytest.mark.django_db
def test_pending_migrations_fail_readiness():
    with patch("config.management.commands.check_database.MigrationExecutor") as executor:
        executor.return_value.migration_plan.return_value = ["pending"]
        with pytest.raises(CommandError, match="migrations are pending"):
            call_command("check_database")
