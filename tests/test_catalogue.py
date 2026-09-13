"""Catalogue product listing: pagination, namespace and active-state filtering."""
import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from catalogue.models import Product

pytestmark = pytest.mark.django_db

HISTORICAL_NAMESPACE = "synthetic/revision-a/historical/v1"


def make_product(external_id, namespace=None, active=True):
    return Product.objects.create(
        namespace=namespace or settings.DEMO_NAMESPACE,
        external_id=external_id,
        name=f"Product {external_id}",
        category="Sample",
        price="10.00",
        cost="5.00",
        stock=10,
        lead_time_days=5,
        active=active,
    )


def test_product_list_is_public():
    make_product("p1")

    response = Client().get(reverse("catalogue:product_list"))

    assert response.status_code == 200
    assert response.templates[0].name == "catalogue/product_list.html"


def test_product_list_excludes_inactive_products():
    make_product("active", active=True)
    make_product("inactive", active=False)

    response = Client().get(reverse("catalogue:product_list"))

    external_ids = [p.external_id for p in response.context["products"]]
    assert external_ids == ["active"]


def test_product_list_excludes_other_namespaces():
    make_product("demo-item", namespace=settings.DEMO_NAMESPACE)
    make_product("historical-item", namespace=HISTORICAL_NAMESPACE)

    response = Client().get(reverse("catalogue:product_list"))

    external_ids = [p.external_id for p in response.context["products"]]
    assert external_ids == ["demo-item"]


def test_product_list_paginates_at_twelve_per_page():
    for i in range(13):
        make_product(f"p{i:02d}")

    first_page = Client().get(reverse("catalogue:product_list"))
    second_page = Client().get(reverse("catalogue:product_list"), {"page": 2})

    assert len(first_page.context["products"]) == 12
    assert len(second_page.context["products"]) == 1


def test_product_list_rejects_invalid_page():
    make_product("p1")
    client = Client()

    assert client.get(reverse("catalogue:product_list"), {"page": 999}).status_code == 404
    assert client.get(reverse("catalogue:product_list"), {"page": "not-a-number"}).status_code == 404


def test_product_list_labels_stock_as_indicative():
    make_product("p1")

    response = Client().get(reverse("catalogue:product_list"))

    assert "indicative" in response.content.decode()
