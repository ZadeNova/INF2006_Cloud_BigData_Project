"""Catalogue product listing and operator product management."""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
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


def make_operator():
    user = get_user_model().objects.create_user(username="operator")
    permission = Permission.objects.get(codename="toggle_product_active", content_type__app_label="catalogue")
    user.user_permissions.add(permission)
    return user


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


def test_manage_list_forbidden_for_non_operators():
    make_product("p1")
    anonymous = Client()
    customer = Client()
    customer.force_login(get_user_model().objects.create_user(username="customer"))

    assert anonymous.get(reverse("catalogue:manage_list")).status_code == 403
    assert customer.get(reverse("catalogue:manage_list")).status_code == 403


def test_toggle_forbidden_for_non_operators():
    product = make_product("p1")
    anonymous = Client()
    customer = Client()
    customer.force_login(get_user_model().objects.create_user(username="customer"))
    url = reverse("catalogue:product_toggle_active", args=[product.pk])

    assert anonymous.post(url).status_code == 403
    assert customer.post(url).status_code == 403
    product.refresh_from_db()
    assert product.active is True


def test_manage_list_shows_all_products_including_inactive():
    make_product("active", active=True)
    make_product("inactive", active=False)
    client = Client()
    client.force_login(make_operator())

    response = client.get(reverse("catalogue:manage_list"))

    external_ids = {p.external_id for p in response.context["products"]}
    assert external_ids == {"active", "inactive"}


def test_toggle_requires_post():
    product = make_product("p1")
    client = Client()
    client.force_login(make_operator())

    response = client.get(reverse("catalogue:product_toggle_active", args=[product.pk]))

    assert response.status_code == 405


def test_operator_can_deactivate_and_reactivate_a_product():
    product = make_product("p1", active=True)
    client = Client()
    client.force_login(make_operator())
    url = reverse("catalogue:product_toggle_active", args=[product.pk])
    public_url = reverse("catalogue:product_list")

    client.post(url)
    product.refresh_from_db()
    assert product.active is False
    assert product.external_id not in [p.external_id for p in Client().get(public_url).context["products"]]

    client.post(url)
    product.refresh_from_db()
    assert product.active is True
    assert product.external_id in [p.external_id for p in Client().get(public_url).context["products"]]
