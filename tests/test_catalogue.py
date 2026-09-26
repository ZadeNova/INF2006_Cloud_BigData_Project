"""Catalogue product listing and operator product management."""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings
from django.urls import reverse

from catalogue.models import Product, ShoeModel
from catalogue.shoes import SHOES, SIZES

pytestmark = pytest.mark.django_db

HISTORICAL_NAMESPACE = "synthetic/revision-a/historical/v1"


def make_product(external_id, namespace=None, active=True, shoe_model=None, size=None, stock=10):
    return Product.objects.create(
        namespace=namespace or settings.DEMO_NAMESPACE,
        external_id=external_id,
        name=shoe_model.name if shoe_model else f"Product {external_id}",
        category="Sample",
        price="10.00",
        cost="5.00",
        stock=stock,
        lead_time_days=5,
        active=active,
        shoe_model=shoe_model,
        size=size,
    )


def make_shoe(external_id, sizes=("9",), namespace=None, active=True, stock=10):
    """A shoe model and one SKU per size, as the importer and seed_demo create them."""
    namespace = namespace or settings.DEMO_NAMESPACE
    model = ShoeModel.objects.create(namespace=namespace, external_id=external_id, name=f"Shoe {external_id}",
                                     category="Sample")
    for size in sizes:
        make_product(f"{external_id}-{size}", namespace=namespace, active=active, shoe_model=model, size=size,
                     stock=stock)
    return model


def listed(response):
    return [shoe.external_id for shoe in response.context["shoes"]]


def make_operator():
    user = get_user_model().objects.create_user(username="operator")
    permission = Permission.objects.get(codename="toggle_product_active", content_type__app_label="catalogue")
    user.user_permissions.add(permission)
    return user


def test_product_list_is_public():
    make_shoe("s1")

    response = Client().get(reverse("catalogue:product_list"))

    assert response.status_code == 200
    assert response.templates[0].name == "catalogue/product_list.html"


def test_product_card_links_to_product_detail_page():
    shoe = make_shoe("s1")

    response = Client().get(reverse("catalogue:product_list"))

    assert reverse("catalogue:product_detail", args=[shoe.pk]) in response.content.decode()


def test_product_detail_shows_size_dropdown_and_add_to_cart():
    shoe = make_shoe("s1", sizes=("8", "9"))
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="customer-detail"))

    response = client.get(reverse("catalogue:product_detail", args=[shoe.pk]))

    body = response.content.decode()
    assert response.status_code == 200
    assert '<select class="size-select" id="size-{}'.format(shoe.pk) in body
    assert "Add to cart" in body


def test_product_detail_404_when_shoe_has_no_active_size():
    shoe = make_shoe("s1", sizes=("9",), active=False)

    response = Client().get(reverse("catalogue:product_detail", args=[shoe.pk]))

    assert response.status_code == 404


def test_product_list_shows_one_card_per_shoe_with_its_active_sizes():
    shoe = make_shoe("s1", sizes=("9.5", "8", "10"))
    Product.objects.filter(external_id="s1-10").update(active=False)
    make_shoe("retired", active=False)
    make_product("size-less")
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="customer"))

    response = client.get(reverse("catalogue:product_list"))

    assert listed(response) == ["s1"]
    assert [sku.size_label for sku in response.context["shoes"][0].sizes] == ["US 8", "US 9.5"]
    assert f'<select class="size-select" id="size-{shoe.pk}" name="product_id" required>' in response.content.decode()


def test_product_list_disables_sold_out_sizes():
    make_shoe("s1", sizes=("9",), stock=0)
    make_shoe("s2", sizes=("8", "9"))
    Product.objects.filter(external_id="s2-8").update(stock=0)
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="customer"))

    response = client.get(reverse("catalogue:product_list"))

    body = response.content.decode()
    sold_out = Product.objects.get(external_id="s2-8")
    assert f'<option value="{sold_out.pk}" disabled>US 8 · sold out</option>' in body
    assert "1 of 2 sizes in stock" in body
    assert [s.stock_status for s in response.context["shoes"]] == ["out-of-stock", "low-stock"]


def test_chosen_size_is_added_to_the_cart():
    make_shoe("s1", sizes=("8", "9"))
    chosen = Product.objects.get(external_id="s1-9")
    client = Client()
    user = get_user_model().objects.create_user(username="customer")
    client.force_login(user)

    client.post(reverse("cart:add"), {"product_id": chosen.pk, "quantity": 1})

    assert list(user.cart.items.values_list("product__external_id", flat=True)) == ["s1-9"]


def test_product_list_excludes_other_namespaces():
    make_shoe("demo-item", namespace=settings.DEMO_NAMESPACE)
    make_shoe("historical-item", namespace=HISTORICAL_NAMESPACE)

    response = Client().get(reverse("catalogue:product_list"))

    assert listed(response) == ["demo-item"]


def test_product_list_paginates_at_twelve_per_page():
    for i in range(13):
        make_shoe(f"s{i:02d}")

    first_page = Client().get(reverse("catalogue:product_list"))
    second_page = Client().get(reverse("catalogue:product_list"), {"page": 2})

    assert len(first_page.context["shoes"]) == 12
    assert len(second_page.context["shoes"]) == 1


def test_product_list_rejects_invalid_page():
    make_shoe("s1")
    client = Client()

    assert client.get(reverse("catalogue:product_list"), {"page": 999}).status_code == 404
    assert client.get(reverse("catalogue:product_list"), {"page": "not-a-number"}).status_code == 404


def test_product_list_labels_stock_as_indicative():
    make_shoe("s1")

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


def test_manage_list_filters_products_by_status_and_category_and_query():
    nike_active = make_product("nike-active", active=True)
    nike_active.name = "Nike Runner"
    nike_active.category = "Running"
    nike_active.save(update_fields=["name", "category"])

    nike_inactive = make_product("nike-inactive", active=False)
    nike_inactive.name = "Nike Street"
    nike_inactive.category = "Running"
    nike_inactive.save(update_fields=["name", "category"])

    adidas = make_product("adidas-active", active=True)
    adidas.name = "Adidas Court"
    adidas.category = "Lifestyle"
    adidas.save(update_fields=["name", "category"])

    client = Client()
    client.force_login(make_operator())

    response = client.get(reverse("catalogue:manage_list"), {
        "status": "inactive",
        "category": "Running",
        "q": "Nike",
    })

    external_ids = {p.external_id for p in response.context["products"]}
    assert external_ids == {"nike-inactive"}


def make_filter_products():
    for index in range(14):
        make_product(f"run-{index:02d}", active=index % 2 == 0)
    Product.objects.filter(external_id__startswith="run-").update(category="Running")
    court = make_product("court-1")
    Product.objects.filter(pk=court.pk).update(name="Court Classic", category="Lifestyle")


def test_manage_list_chips_and_pager_keep_the_other_filters():
    make_filter_products()
    client = Client()
    client.force_login(make_operator())

    response = client.get(reverse("catalogue:manage_list"), {"q": "Product", "category": "Running"})
    body = response.content.decode()

    chips = {chip["label"]: chip for chip in response.context["status_chips"]}
    assert chips["Inactive"]["query"] == "q=Product&category=Running&status=inactive"
    assert chips["All"]["selected"] is True
    assert response.context["paginator"].count == 14
    assert 'href="?q=Product&amp;category=Running&amp;page=2"' in body
    assert "14 products match" in body


def test_manage_list_unknown_filter_values_fall_back_to_all():
    make_filter_products()
    client = Client()
    client.force_login(make_operator())

    response = client.get(reverse("catalogue:manage_list"), {"status": "deleted", "category": "Nope"})

    assert response.context["filters"] == {"q": "", "category": "all", "status": "all"}
    assert response.context["paginator"].count == 15


def test_manage_list_shows_empty_state_when_nothing_matches():
    make_filter_products()
    client = Client()
    client.force_login(make_operator())

    response = client.get(reverse("catalogue:manage_list"), {"q": "no such shoe"})

    assert "No products match these filters." in response.content.decode()


def test_manage_list_clamps_a_page_beyond_the_filtered_result():
    make_filter_products()
    client = Client()
    client.force_login(make_operator())

    response = client.get(reverse("catalogue:manage_list"), {"status": "inactive", "page": "9"})

    assert response.status_code == 200
    assert response.context["page_obj"].number == 1


def test_toggle_returns_to_the_filtered_manage_page():
    product = make_product("p1")
    client = Client()
    client.force_login(make_operator())
    back = reverse("catalogue:manage_list") + "?status=active&page=2"

    response = client.post(reverse("catalogue:product_toggle_active", args=[product.pk]),
                           {"active": "false", "next": back})

    assert response.status_code == 302
    assert response["Location"] == back


@pytest.mark.parametrize("target", ["https://evil.example/products/manage/", "//evil.example/", "/cart/"])
def test_toggle_ignores_a_next_outside_the_manage_list(target):
    product = make_product("p1")
    client = Client()
    client.force_login(make_operator())

    response = client.post(reverse("catalogue:product_toggle_active", args=[product.pk]),
                           {"active": "false", "next": target})

    assert response["Location"] == reverse("catalogue:manage_list")


def test_product_detail_for_anonymous_user_offers_login_back_to_the_page():
    shoe = make_shoe("s1")

    response = Client().get(reverse("catalogue:product_detail", args=[shoe.pk]))

    body = response.content.decode()
    detail = reverse("catalogue:product_detail", args=[shoe.pk])
    assert reverse("accounts:login") + "?next=" + detail in body
    assert "Add to cart" not in body


def test_toggle_requires_post():
    product = make_product("p1")
    client = Client()
    client.force_login(make_operator())

    response = client.get(reverse("catalogue:product_toggle_active", args=[product.pk]))

    assert response.status_code == 405


def test_operator_can_deactivate_and_reactivate_a_product():
    make_shoe("s1")
    product = Product.objects.get(external_id="s1-9")
    client = Client()
    client.force_login(make_operator())
    url = reverse("catalogue:product_toggle_active", args=[product.pk])
    public_url = reverse("catalogue:product_list")

    client.post(url, {"active": "false"})
    product.refresh_from_db()
    assert product.active is False
    assert listed(Client().get(public_url)) == []

    client.post(url, {"active": "true"})
    product.refresh_from_db()
    assert product.active is True
    assert listed(Client().get(public_url)) == ["s1"]


def test_toggle_rejects_invalid_active_value():
    product = make_product("p1", active=True)
    client = Client()
    client.force_login(make_operator())
    url = reverse("catalogue:product_toggle_active", args=[product.pk])

    response = client.post(url, {"active": "maybe"})

    assert response.status_code == 400
    product.refresh_from_db()
    assert product.active is True


@pytest.mark.parametrize("start_active, target", [(True, "false"), (False, "true")], ids=["deactivate", "activate"])
def test_toggle_is_idempotent_under_double_submit(start_active, target):
    product = make_product("p1", active=start_active)
    client = Client()
    client.force_login(make_operator())
    url = reverse("catalogue:product_toggle_active", args=[product.pk])

    client.post(url, {"active": target})
    client.post(url, {"active": target})

    product.refresh_from_db()
    assert product.active is (target == "true")


def test_seed_demo_refuses_to_promote_an_existing_customer(monkeypatch):
    monkeypatch.setenv("DEMO_OPERATOR_PASSWORD", "irrelevant-for-existing-user")
    customer = get_user_model().objects.create_user(username="demo-operator", password="customer-pass")

    with pytest.raises(CommandError):
        call_command("seed_demo")

    customer.refresh_from_db()
    assert customer.groups.count() == 0
    assert customer.check_password("customer-pass")


def test_seed_demo_requires_password_outside_local(monkeypatch):
    monkeypatch.delenv("DEMO_OPERATOR_PASSWORD", raising=False)

    with override_settings(LOCAL=False), pytest.raises(CommandError):
        call_command("seed_demo")

    assert Product.objects.count() == 0
    assert not get_user_model().objects.filter(username="demo-operator").exists()


def test_seed_demo_allows_fallback_password_in_local(monkeypatch):
    monkeypatch.delenv("DEMO_OPERATOR_PASSWORD", raising=False)

    with override_settings(LOCAL=True):
        call_command("seed_demo")

    operator = get_user_model().objects.get(username="demo-operator")
    assert operator.check_password("Str0ngDemoOperator!2026")


def test_seed_demo_creates_every_shoe_in_every_size_and_deactivates_retired_demo_products(monkeypatch):
    monkeypatch.delenv("DEMO_OPERATOR_PASSWORD", raising=False)
    retired = make_product("demo-001")
    old_sneaker = make_product("sneaker-001")
    other_namespace = make_product("demo-001", namespace=HISTORICAL_NAMESPACE)

    with override_settings(LOCAL=True):
        call_command("seed_demo")
        call_command("seed_demo")

    for product in (retired, old_sneaker, other_namespace):
        product.refresh_from_db()
    assert ShoeModel.objects.filter(namespace=settings.DEMO_NAMESPACE).count() == len(SHOES) == 20
    skus = Product.objects.filter(namespace=settings.DEMO_NAMESPACE, shoe_model__isnull=False)
    assert skus.count() == len(SHOES) * len(SIZES) == 200
    assert all(sku.active and sku.name == sku.shoe_model.name for sku in skus.select_related("shoe_model"))
    assert retired.active is False and old_sneaker.active is False
    assert other_namespace.active is True
