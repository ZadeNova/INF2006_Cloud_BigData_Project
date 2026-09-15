"""Persistent cart: add/update/remove, ownership isolation, HTMX contract."""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from cart.models import Cart, CartItem
from catalogue.models import Product

pytestmark = pytest.mark.django_db

HISTORICAL_NAMESPACE = "synthetic/revision-a/historical/v1"


def make_product(external_id, namespace=None, active=True, price="10.00", stock=10):
    return Product.objects.create(
        namespace=namespace or settings.DEMO_NAMESPACE,
        external_id=external_id,
        name=f"Product {external_id}",
        category="Sample",
        price=price,
        cost="5.00",
        stock=stock,
        lead_time_days=5,
        active=active,
    )


def make_user(username="shopper"):
    return get_user_model().objects.create_user(username=username)


def logged_in_client(username="shopper"):
    client = Client()
    client.force_login(make_user(username))
    return client


def csrf_token_from(response):
    return response.context["csrf_token"]


# --- add ---


def test_add_creates_a_new_cart_item():
    product = make_product("p1")
    client = logged_in_client()

    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 2})

    item = CartItem.objects.get(cart__owner__username="shopper", product=product)
    assert item.quantity == 2


def test_add_increments_an_existing_cart_item():
    product = make_product("p1")
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 2})

    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 3})

    item = CartItem.objects.get(product=product)
    assert item.quantity == 5


def test_add_rejects_when_exceeding_999_without_mutation():
    product = make_product("p1", stock=2000)
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 998})

    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 5})

    item = CartItem.objects.get(product=product)
    assert item.quantity == 998


def test_add_rejects_when_exceeding_current_stock_without_mutation():
    product = make_product("p1", stock=3)
    client = logged_in_client()

    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 4})

    assert not CartItem.objects.filter(product=product).exists()


def test_add_rejects_inactive_product():
    product = make_product("p1", active=False)
    client = logged_in_client()

    response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})

    assert response.status_code == 404
    assert not CartItem.objects.filter(product=product).exists()


def test_add_rejects_product_outside_demo_namespace():
    product = make_product("p1", namespace=HISTORICAL_NAMESPACE)
    client = logged_in_client()

    response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})

    assert response.status_code == 404
    assert not CartItem.objects.filter(product=product).exists()


def test_add_requires_login_normal_request_redirects():
    product = make_product("p1")

    response = Client().post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})

    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)


def test_add_requires_login_htmx_request_gets_hx_redirect():
    product = make_product("p1")

    response = Client().post(
        reverse("cart:add"), {"product_id": product.pk, "quantity": 1}, HTTP_HX_REQUEST="true"
    )

    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == settings.LOGIN_URL


# --- update ---


def test_update_replaces_quantity_within_bounds():
    product = make_product("p1")
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})
    item = CartItem.objects.get(product=product)

    client.post(reverse("cart:update", args=[item.pk]), {"quantity": 7})

    item.refresh_from_db()
    assert item.quantity == 7


@pytest.mark.parametrize("bad_quantity", [0, 1000])
def test_update_rejects_out_of_bounds_quantity_without_mutation(bad_quantity):
    product = make_product("p1", stock=2000)
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 5})
    item = CartItem.objects.get(product=product)

    client.post(reverse("cart:update", args=[item.pk]), {"quantity": bad_quantity})

    item.refresh_from_db()
    assert item.quantity == 5


def test_update_rejects_when_exceeding_current_stock():
    product = make_product("p1", stock=3)
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 2})
    item = CartItem.objects.get(product=product)

    client.post(reverse("cart:update", args=[item.pk]), {"quantity": 4})

    item.refresh_from_db()
    assert item.quantity == 2


def test_update_rejects_quantity_change_on_an_inactive_product():
    product = make_product("p1")
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})
    item = CartItem.objects.get(product=product)
    product.active = False
    product.save(update_fields=["active"])

    client.post(reverse("cart:update", args=[item.pk]), {"quantity": 5})

    item.refresh_from_db()
    assert item.quantity == 1


def test_update_on_foreign_item_returns_404_and_does_not_mutate():
    product = make_product("p1")
    owner_client = logged_in_client("owner")
    owner_client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})
    item = CartItem.objects.get(product=product)
    other_client = logged_in_client("other")

    response = other_client.post(reverse("cart:update", args=[item.pk]), {"quantity": 9})

    assert response.status_code == 404
    item.refresh_from_db()
    assert item.quantity == 1


def test_update_on_missing_item_returns_404():
    client = logged_in_client()

    response = client.post(reverse("cart:update", args=[999999]), {"quantity": 1})

    assert response.status_code == 404


# --- delete ---


def test_delete_removes_an_item():
    product = make_product("p1")
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})
    item = CartItem.objects.get(product=product)

    client.post(reverse("cart:delete", args=[item.pk]))

    assert not CartItem.objects.filter(pk=item.pk).exists()


def test_delete_does_not_touch_a_foreign_cart_item():
    product = make_product("p1")
    owner_client = logged_in_client("owner")
    owner_client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})
    item = CartItem.objects.get(product=product)
    other_client = logged_in_client("other")

    other_client.post(reverse("cart:delete", args=[item.pk]))

    assert CartItem.objects.filter(pk=item.pk).exists()


def test_delete_on_already_gone_item_is_idempotent_success():
    client = logged_in_client()

    response = client.post(reverse("cart:delete", args=[999999]))

    assert response.status_code == 302


# --- HTMX contract and cross-cutting ---


def test_htmx_mutation_response_renders_cart_content_fragment():
    product = make_product("p1")
    client = logged_in_client()

    response = client.post(
        reverse("cart:add"), {"product_id": product.pk, "quantity": 1}, HTTP_HX_REQUEST="true"
    )

    assert response.status_code == 200
    assert response.templates[0].name == "cart/_content.html"
    assert 'id="cart-content"' in response.content.decode()


def test_non_htmx_success_redirects_to_cart_detail():
    product = make_product("p1")
    client = logged_in_client()

    response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})

    assert response.status_code == 302
    assert response.url == reverse("cart:detail")


def test_add_without_csrf_token_is_rejected():
    product = make_product("p1")
    client = Client(enforce_csrf_checks=True)
    client.force_login(make_user())

    response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})

    assert response.status_code == 403


def test_add_with_csrf_token_succeeds():
    product = make_product("p1")
    client = Client(enforce_csrf_checks=True)
    client.force_login(make_user())
    token = csrf_token_from(client.get(reverse("cart:detail")))

    response = client.post(
        reverse("cart:add"),
        {"product_id": product.pk, "quantity": 1, "csrfmiddlewaretoken": token},
    )

    assert response.status_code == 302


@pytest.mark.parametrize(
    "url_name,args",
    [("cart:add", []), ("cart:update", [1]), ("cart:delete", [1])],
)
def test_get_on_post_only_routes_returns_405(url_name, args):
    client = logged_in_client()

    response = client.get(reverse(url_name, args=args))

    assert response.status_code == 405


def test_users_only_see_their_own_cart():
    shared_product = make_product("p1")
    owner_client = logged_in_client("owner")
    owner_client.post(reverse("cart:add"), {"product_id": shared_product.pk, "quantity": 3})
    other_client = logged_in_client("other")

    response = other_client.get(reverse("cart:detail"))

    assert list(response.context["items"]) == []
    assert Cart.objects.get(owner__username="owner").items.count() == 1
