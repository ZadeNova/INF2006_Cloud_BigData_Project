"""Transient database failures answer 503; bugs stay 500 (review finding SEC-002)."""
import uuid
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, InterfaceError, OperationalError, ProgrammingError
from django.db.backends.postgresql.base import DatabaseWrapper
from django.test import Client
from django.urls import reverse

from cart.services import add_item, get_cart
from catalogue.models import Product
from orders import services as order_services
from orders.models import Order
from orders.views import SESSION_KEY

pytestmark = pytest.mark.django_db
SECRET = "connection to server at db-secret-host failed"


def database_down(error):
    """Every new database cursor fails, as when the server is unreachable."""
    return mock.patch.object(DatabaseWrapper, "create_cursor", side_effect=error)


@pytest.fixture
def shopper():
    """A logged-in user with one item in the cart, established while the database is still up."""
    user = get_user_model().objects.create_user(username="shopper")
    product = Product.objects.create(namespace=settings.DEMO_NAMESPACE, external_id="p1", name="Product p1",
                                     category="Sample", price="10.00", cost="5.00", stock=5, lead_time_days=5)
    add_item(get_cart(user), product, 1)
    client = Client()
    client.force_login(user)
    return user, product, client


@pytest.mark.parametrize("method, route", [
    ("get", "cart:detail"), ("post", "cart:add"), ("get", "orders:checkout"), ("post", "orders:checkout"),
    ("get", "orders:list"), ("get", "catalogue:product_list"),
])
def test_a_database_outage_answers_503_with_retry_after_and_no_details(shopper, method, route):
    _, _, client = shopper
    with database_down(OperationalError(SECRET)):
        response = getattr(client, method)(reverse(route))

    assert response.status_code == 503
    assert response["Retry-After"] == "5"
    assert "no-store" in response["Cache-Control"]
    body = response.content.decode()
    assert "temporarily unavailable" in body
    assert SECRET not in body and "OperationalError" not in body


def test_an_htmx_mutation_gets_the_same_503(shopper):
    _, product, client = shopper
    with database_down(OperationalError(SECRET)):
        response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1}, HTTP_HX_REQUEST="true")

    assert response.status_code == 503 and response["Retry-After"] == "5"


def test_a_closed_connection_is_also_treated_as_unavailable(shopper):
    _, _, client = shopper
    with database_down(InterfaceError("connection already closed")):
        assert client.get(reverse("cart:detail")).status_code == 503


@pytest.mark.parametrize("error", [IntegrityError(SECRET), ProgrammingError(SECRET)])
def test_bugs_are_not_turned_into_retryable_503s(shopper, error):
    user, _, _ = shopper
    client = Client(raise_request_exception=False)
    client.force_login(user)
    with database_down(error):
        response = client.get(reverse("cart:detail"))

    assert response.status_code == 500
    assert SECRET not in response.content.decode()


def test_the_health_endpoint_does_not_depend_on_the_database(shopper):
    _, _, client = shopper
    with database_down(OperationalError(SECRET)):
        response = client.get("/health/")

    assert response.status_code == 200


def test_checkout_retry_after_an_uncertain_outcome_resolves_the_committed_order(shopper, monkeypatch):
    user, product, client = shopper
    review = client.get(reverse("orders:checkout")).context["review"]
    key = client.session[SESSION_KEY]
    real_checkout = order_services.checkout

    def commit_then_lose_the_connection(*args, **kwargs):
        real_checkout(*args, **kwargs)
        raise OperationalError("connection lost after the commit")

    monkeypatch.setattr(order_services, "checkout", commit_then_lose_the_connection)
    first = client.post(reverse("orders:checkout"), {"review": review})

    assert first.status_code == 503
    assert Order.objects.filter(owner=user).count() == 1          # the order really was committed
    assert client.session[SESSION_KEY] == key                     # and the key was kept for the retry

    monkeypatch.setattr(order_services, "checkout", real_checkout)
    retry = client.post(reverse("orders:checkout"), {"review": review})

    order = Order.objects.get(owner=user)
    assert retry.status_code == 302 and retry.url == reverse("orders:detail", args=[order.pk])
    product.refresh_from_db()
    assert product.stock == 4                                      # ordered once, not twice
