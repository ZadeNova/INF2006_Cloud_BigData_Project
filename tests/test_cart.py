"""Persistent cart: add/update/remove, ownership isolation, HTMX contract."""
import threading
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.test import Client
from django.urls import reverse

from cart import services, views as cart_views
from cart.models import Cart, CartItem
from catalogue.models import Product
from db_helpers import wait_until_blocked

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


# --- update ---


def test_update_replaces_quantity_within_bounds():
    product = make_product("p1")
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})
    item = CartItem.objects.get(product=product)

    client.post(reverse("cart:update", args=[item.pk]), {"quantity": 7})

    item.refresh_from_db()
    assert item.quantity == 7


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


def test_update_returns_404_if_the_item_disappears_after_the_view_looked_it_up(monkeypatch):
    # CART-001: another tab removes the item between the view's lookup and the service's locked lookup
    product = make_product("p1")
    client = logged_in_client()
    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})
    item = CartItem.objects.get(product=product)
    real_lookup = cart_views.get_object_or_404

    def look_up_then_remove(*args, **kwargs):
        found = real_lookup(*args, **kwargs)
        CartItem.objects.filter(pk=found.pk).delete()
        return found

    monkeypatch.setattr(cart_views, "get_object_or_404", look_up_then_remove)

    response = client.post(reverse("cart:update", args=[item.pk]), {"quantity": 3})

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


def test_add_from_the_shop_returns_to_that_page_with_a_message():
    product = make_product("p1")
    client = logged_in_client()
    back = reverse("catalogue:product_list") + "?page=2"

    response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1, "next": back})

    assert response.status_code == 302
    assert response.url == back
    page = client.get(back, follow=True).content.decode()
    assert f"{product.display_name} added to your cart." in page
    assert 'href="{}">View cart</a>'.format(reverse("cart:detail")) in page
    assert CartItem.objects.filter(product=product, quantity=1).exists()


def test_add_error_from_the_shop_returns_to_that_page_with_the_error():
    product = make_product("p1", stock=1)
    client = logged_in_client()
    back = reverse("catalogue:product_list")

    response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 5, "next": back})

    assert response.url == back
    page = client.get(back).content.decode()
    assert "message--error" in page
    assert "added to your cart" not in page
    assert not CartItem.objects.filter(product=product).exists()


@pytest.mark.parametrize("target", ["https://evil.example/products/", "//evil.example/products/",
                                    "/products/manage/", "/orders/"])
def test_add_ignores_a_next_outside_the_shop(target):
    product = make_product("p1")
    client = logged_in_client()

    response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1, "next": target})

    assert response.url == reverse("cart:detail")


def test_non_htmx_success_redirects_to_cart_detail():
    product = make_product("p1")
    client = logged_in_client()

    response = client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": 1})

    assert response.status_code == 302
    assert response.url == reverse("cart:detail")


def test_subtotal_sums_line_totals_exactly_and_skips_unavailable_items():
    user = make_user()
    cart = services.get_cart(user)
    services.add_item(cart, make_product("p1", price="19.99"), 3)      # 59.97
    services.add_item(cart, make_product("p2", price="5.05"), 2)       # 10.10
    withdrawn = make_product("p3", price="100.00")
    services.add_item(cart, withdrawn, 1)

    items = cart.items.select_related("product")
    assert services.cart_subtotal(items) == Decimal("170.07")

    Product.objects.filter(pk=withdrawn.pk).update(active=False)       # withdrawn while in the cart

    assert services.cart_subtotal(cart.items.select_related("product")) == Decimal("70.07")


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


# --- concurrency (real PostgreSQL connections; deterministic: a second connection holds a lock, the request
# under test starts and is seen blocked, then the lock is released) ---


def run_blocked_request(action):
    """Run `action` in a thread; returns (thread, outcome dict). The thread closes its own connection."""
    outcome = {}

    def target():
        try:
            outcome["result"] = action()
        except Exception as exc:  # noqa: BLE001 - asserted on by the tests
            outcome["error"] = exc
        finally:
            connection.close()

    return threading.Thread(target=target), outcome


@pytest.mark.django_db(transaction=True)
def test_add_waits_for_a_concurrent_update_and_increments_on_top_of_it():
    """Without the row lock the request reads 1, writes 2 and overwrites the concurrent change (CART-002)."""
    user = make_user()
    product = make_product("p1", stock=50)
    item = services.add_item(services.get_cart(user), product, 1)
    thread, outcome = run_blocked_request(lambda: services.add_item(services.get_cart(user), product, 1))

    with transaction.atomic():
        CartItem.objects.select_for_update().get(pk=item.pk)      # another request holds the row
        thread.start()
        wait_until_blocked()
        CartItem.objects.filter(pk=item.pk).update(quantity=5)    # its change, committed on leaving the block
    thread.join(10)

    assert "error" not in outcome, outcome
    assert CartItem.objects.get(pk=item.pk).quantity == 6         # 5 + 1, not 1 + 1


@pytest.mark.django_db(transaction=True)
def test_a_first_add_racing_a_concurrent_insert_becomes_an_increment():
    """The unique constraint makes the loser fail; add_item must retry it as an increment (CART-002)."""
    user = make_user()
    product = make_product("p1", stock=50)
    cart = services.get_cart(user)
    thread, outcome = run_blocked_request(lambda: services.add_item(services.get_cart(user), product, 2))

    with transaction.atomic():
        CartItem.objects.create(cart=cart, product=product, quantity=3)   # another request's uncommitted insert
        thread.start()
        wait_until_blocked()                                              # our insert waits on the unique index
    thread.join(10)

    assert "error" not in outcome, outcome
    rows = CartItem.objects.filter(cart=cart, product=product)
    assert rows.count() == 1 and rows.get().quantity == 5


@pytest.mark.django_db(transaction=True)
def test_update_waits_for_a_concurrent_removal_and_then_reports_the_item_gone():
    """The real interleaving behind CART-001: without the lock the update fails with a database error."""
    user = make_user()
    product = make_product("p1", stock=50)
    cart = services.get_cart(user)
    item = services.add_item(cart, product, 1)
    thread, outcome = run_blocked_request(lambda: services.set_item_quantity(cart, item, 3))

    with transaction.atomic():
        CartItem.objects.select_for_update().get(pk=item.pk)
        thread.start()
        wait_until_blocked()
        CartItem.objects.filter(pk=item.pk).delete()
    thread.join(10)

    assert isinstance(outcome.get("error"), services.CartItemNotFound), outcome
    assert not CartItem.objects.filter(pk=item.pk).exists()
