"""Checkout: idempotency, pin-scoping, locking. See docs/plans/batch-04-checkout.md."""
import threading
import uuid
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.urls import reverse

from cart.models import CartItem
from cart.services import add_item, get_cart, remove_item
from catalogue.models import Product
from orders import services
from orders.models import Order, OrderItem
from orders.views import SESSION_ITEM_IDS, SESSION_KEY

pytestmark = pytest.mark.django_db


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


def logged_in_client(user):
    client = Client()
    client.force_login(user)
    return client


# --- successful checkout ---


def test_successful_checkout_creates_order_decrements_stock_clears_cart():
    user = make_user()
    product = make_product("p1", price="10.00", stock=5)
    add_item(get_cart(user), product, 2)
    client = logged_in_client(user)
    client.get(reverse("orders:checkout"))

    response = client.post(reverse("orders:checkout"))

    order = Order.objects.get(owner=user)
    assert response.status_code == 302
    assert response.url == reverse("orders:detail", args=[order.pk])
    assert order.status == Order.Status.COMPLETED
    assert order.external_id is None
    assert order.namespace == settings.DEMO_NAMESPACE
    assert order.total == Decimal("20.00")
    item = OrderItem.objects.get(order=order)
    assert item.quantity == 2
    assert item.unit_price == Decimal("10.00")
    product.refresh_from_db()
    assert product.stock == 3
    assert not CartItem.objects.filter(cart__owner=user).exists()


def test_unit_price_captured_is_live_price_not_cart_time_price():
    user = make_user()
    product = make_product("p1", price="10.00", stock=5)
    add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    client.get(reverse("orders:checkout"))
    product.price = "15.00"
    product.save(update_fields=["price"])

    client.post(reverse("orders:checkout"))

    item = OrderItem.objects.get(order__owner=user)
    assert item.unit_price == Decimal("15.00")


def test_get_checkout_with_empty_cart_redirects_to_cart():
    client = logged_in_client(make_user())

    response = client.get(reverse("orders:checkout"))

    assert response.status_code == 302
    assert response.url == reverse("cart:detail")


# --- all-or-nothing blocking ---


def test_inactive_product_blocks_whole_order_no_mutation():
    user = make_user()
    product_ok = make_product("p1", stock=5)
    product_bad = make_product("p2", active=False, stock=5)
    add_item(get_cart(user), product_ok, 1)
    add_item(get_cart(user), product_bad, 1)
    client = logged_in_client(user)
    client.get(reverse("orders:checkout"))

    response = client.post(reverse("orders:checkout"))

    assert response.status_code == 200
    assert "no longer available" in response.content.decode()
    assert not Order.objects.filter(owner=user).exists()
    assert CartItem.objects.filter(cart__owner=user).count() == 2
    product_ok.refresh_from_db()
    assert product_ok.stock == 5


def test_insufficient_stock_blocks_order_with_409_no_mutation():
    user = make_user()
    product = make_product("p1", stock=2)
    add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    client.get(reverse("orders:checkout"))
    product.stock = 0
    product.save(update_fields=["stock"])

    response = client.post(reverse("orders:checkout"))

    assert response.status_code == 409
    assert not Order.objects.filter(owner=user).exists()
    assert CartItem.objects.filter(cart__owner=user).exists()


# --- replay / idempotency (service-level, per docs/plans/batch-04-checkout.md) ---


def test_replay_after_cart_already_cleared_returns_original_order():
    user = make_user()
    product = make_product("p1", stock=5)
    item = add_item(get_cart(user), product, 1)
    key = str(uuid.uuid4())

    first = services.checkout(user, key, [item.pk])
    second = services.checkout(user, key, [item.pk])

    assert second.pk == first.pk
    assert Order.objects.filter(owner=user).count() == 1


def test_replay_with_fingerprint_still_matching_returns_original_order():
    user = make_user()
    product = make_product("p1", stock=5)
    item = add_item(get_cart(user), product, 2)
    key = str(uuid.uuid4())
    first = services.checkout(user, key, [item.pk])

    # A resurrected stale key (known accepted edge case) plus an identical
    # re-add: new CartItem rows the original pin never referenced, but whose
    # content still fingerprints identically to the original order.
    new_item = add_item(get_cart(user), product, 2)

    second = services.checkout(user, key, [item.pk, new_item.pk])

    assert second.pk == first.pk
    assert Order.objects.filter(owner=user).count() == 1
    assert CartItem.objects.filter(pk=new_item.pk).exists()


def test_replay_with_different_fingerprint_raises_conflict_no_new_order():
    user = make_user()
    product = make_product("p1", stock=5)
    item = add_item(get_cart(user), product, 1)
    key = str(uuid.uuid4())
    services.checkout(user, key, [item.pk])

    other_product = make_product("p2", stock=5)
    new_item = add_item(get_cart(user), other_product, 1)

    with pytest.raises(services.CheckoutConflictError):
        services.checkout(user, key, [new_item.pk])

    assert Order.objects.filter(owner=user).count() == 1


def test_post_with_fingerprint_mismatch_rerenders_at_409():
    user = make_user()
    product = make_product("p1", stock=5)
    item = add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    client.get(reverse("orders:checkout"))
    client.post(reverse("orders:checkout"))
    order = Order.objects.get(owner=user)

    other_product = make_product("p2", stock=5)
    new_item = add_item(get_cart(user), other_product, 1)
    session = client.session
    session[SESSION_KEY] = str(order.idempotency_key)
    session[SESSION_ITEM_IDS] = [new_item.pk]
    session.save()

    response = client.post(reverse("orders:checkout"))

    assert response.status_code == 409
    assert Order.objects.filter(owner=user).count() == 1


# --- pin-scoping / ecommerce parity ---


def test_item_added_after_review_page_excluded_from_order_and_stays_in_cart():
    user = make_user()
    product = make_product("p1", stock=5)
    add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    client.get(reverse("orders:checkout"))

    other_product = make_product("p2", stock=5)
    new_item = add_item(get_cart(user), other_product, 1)

    client.post(reverse("orders:checkout"))

    order = Order.objects.get(owner=user)
    assert OrderItem.objects.filter(order=order).count() == 1
    assert OrderItem.objects.get(order=order).product == product
    assert CartItem.objects.filter(pk=new_item.pk).exists()


def test_removing_pinned_item_blocks_order_and_retry_after_rerender_succeeds():
    user = make_user()
    product_a = make_product("p1", stock=5)
    product_b = make_product("p2", stock=5)
    item_a = add_item(get_cart(user), product_a, 1)
    item_b = add_item(get_cart(user), product_b, 1)
    client = logged_in_client(user)
    client.get(reverse("orders:checkout"))
    remove_item(get_cart(user), item_b.pk)

    blocked = client.post(reverse("orders:checkout"))

    assert blocked.status_code == 200
    assert "changed" in blocked.content.decode().lower()
    assert not Order.objects.filter(owner=user).exists()
    assert CartItem.objects.filter(pk=item_a.pk).exists()

    retried = client.post(reverse("orders:checkout"))

    assert retried.status_code == 302
    order = Order.objects.get(owner=user)
    assert OrderItem.objects.filter(order=order).count() == 1


def test_stale_pin_against_nonempty_cart_reports_changed_not_empty():
    user = make_user()
    product = make_product("p1", stock=5)
    item = add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    client.get(reverse("orders:checkout"))
    remove_item(get_cart(user), item.pk)
    other_product = make_product("p2", stock=5)
    add_item(get_cart(user), other_product, 1)

    response = client.post(reverse("orders:checkout"))

    assert response.status_code == 200
    content = response.content.decode().lower()
    assert "changed" in content
    assert "empty" not in content


# --- auth / ownership / CSRF ---


def test_checkout_requires_login():
    response = Client().get(reverse("orders:checkout"))

    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)


def test_order_detail_returns_404_for_foreign_order_200_for_owner():
    owner = make_user("owner")
    other = make_user("other")
    product = make_product("p1", stock=5)
    item = add_item(get_cart(owner), product, 1)
    order = services.checkout(owner, str(uuid.uuid4()), [item.pk])

    assert logged_in_client(owner).get(reverse("orders:detail", args=[order.pk])).status_code == 200
    assert logged_in_client(other).get(reverse("orders:detail", args=[order.pk])).status_code == 404


def test_post_without_csrf_token_is_rejected():
    user = make_user()
    product = make_product("p1", stock=5)
    add_item(get_cart(user), product, 1)
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    client.get(reverse("orders:checkout"))

    response = client.post(reverse("orders:checkout"))

    assert response.status_code == 403


# --- NULL external_id uniqueness (order_source_unique tolerates only NULLs) ---


def test_two_sequential_checkouts_both_succeed():
    user = make_user()
    product = make_product("p1", stock=10)
    item1 = add_item(get_cart(user), product, 1)
    order1 = services.checkout(user, str(uuid.uuid4()), [item1.pk])

    item2 = add_item(get_cart(user), product, 1)
    order2 = services.checkout(user, str(uuid.uuid4()), [item2.pk])

    assert order1.pk != order2.pk
    assert Order.objects.filter(owner=user).count() == 2


# --- concurrent (real PostgreSQL transactions/connections, per docs/TESTING.md) ---


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkouts_same_idempotency_key_create_exactly_one_order():
    user = make_user()
    product = make_product("p1", stock=10)
    item = add_item(get_cart(user), product, 2)
    key = str(uuid.uuid4())
    item_ids = [item.pk]

    results = []
    errors = []
    barrier = threading.Barrier(2)

    def attempt():
        barrier.wait()
        try:
            results.append(services.checkout(user, key, item_ids))
        except Exception as exc:  # noqa: BLE001 - surfaced via assertion below
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, errors
    assert Order.objects.filter(owner=user).count() == 1
    assert len({order.pk for order in results}) == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkouts_different_users_racing_last_unit_of_stock():
    product = make_product("p1", stock=1)
    user_a = make_user("racer-a")
    user_b = make_user("racer-b")
    item_a = add_item(get_cart(user_a), product, 1)
    item_b = add_item(get_cart(user_b), product, 1)

    outcomes = {}
    barrier = threading.Barrier(2)

    def attempt(label, user, item_id):
        barrier.wait()
        try:
            order = services.checkout(user, str(uuid.uuid4()), [item_id])
            outcomes[label] = ("ok", order)
        except services.InsufficientStockError as exc:
            outcomes[label] = ("conflict", exc)
        finally:
            connection.close()

    threads = [
        threading.Thread(target=attempt, args=("a", user_a, item_a.pk)),
        threading.Thread(target=attempt, args=("b", user_b, item_b.pk)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcome[0] for outcome in outcomes.values()) == ["conflict", "ok"]
    product.refresh_from_db()
    assert product.stock == 0
