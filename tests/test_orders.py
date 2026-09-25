"""Checkout: idempotency, review fingerprint, locking.

See docs/plans/batch-04-checkout.md and docs/plans/checkout-review-fixes.md (review findings CHK-001, CHK-002).
"""
import threading
import uuid
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from cart.models import CartItem
from cart.services import add_item, cart_subtotal, get_cart, remove_item, set_item_quantity
from catalogue.models import Product
from orders import services
from orders.models import Order, OrderItem
from db_helpers import wait_until_blocked
from orders.views import SESSION_KEY

pytestmark = pytest.mark.django_db
NO_MATCH = "0" * 64      # well-formed, but the fingerprint of no cart


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


def review_for(user):
    """The fingerprint a review page would render for the user's current cart."""
    items = get_cart(user).items.select_related("product")
    return services.fingerprint_for([(item.product, item.quantity) for item in items])


def open_checkout(client):
    """GET the review page and return the fingerprint it rendered."""
    return client.get(reverse("orders:checkout")).context["review"]


def place(client, review):
    return client.post(reverse("orders:checkout"), {"review": review})


# --- successful checkout ---


def test_successful_checkout_creates_order_decrements_stock_clears_cart():
    user = make_user()
    product = make_product("p1", price="10.00", stock=5)
    add_item(get_cart(user), product, 2)
    client = logged_in_client(user)
    review = open_checkout(client)

    response = place(client, review)

    order = Order.objects.get(owner=user)
    assert response.status_code == 302
    assert response.url == reverse("orders:detail", args=[order.pk])
    assert order.status == Order.Status.COMPLETED
    assert order.external_id is None
    assert order.namespace == settings.DEMO_NAMESPACE
    assert order.total == Decimal("20.00")
    assert order.request_fingerprint == review
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
    review = open_checkout(client)
    product.price = "15.00"
    product.save(update_fields=["price"])

    place(client, review)     # price is not part of the review fingerprint

    item = OrderItem.objects.get(order__owner=user)
    assert item.unit_price == Decimal("15.00")


def test_order_total_sums_several_lines_exactly_without_rounding_drift():
    user = make_user()
    cheap = make_product("p1", price="19.99", stock=10)
    cheaper = make_product("p2", price="5.05", stock=10)
    add_item(get_cart(user), cheap, 3)          # 59.97
    add_item(get_cart(user), cheaper, 2)        # 10.10
    client = logged_in_client(user)

    place(client, open_checkout(client))

    order = Order.objects.get(owner=user)
    lines = OrderItem.objects.filter(order=order)
    assert order.total == Decimal("70.07")
    assert order.total == sum(line.line_total for line in lines)
    assert sorted(line.unit_price for line in lines) == [Decimal("5.05"), Decimal("19.99")]


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
    review = open_checkout(client)

    response = place(client, review)

    assert response.status_code == 200
    assert "no longer available" in response.content.decode()
    assert not Order.objects.filter(owner=user).exists()
    assert CartItem.objects.filter(cart__owner=user).count() == 2
    product_ok.refresh_from_db()
    assert product_ok.stock == 5


def test_review_page_total_leaves_out_a_deactivated_product_like_the_cart_does():
    user = make_user()
    add_item(get_cart(user), make_product("p1", price="10.00"), 2)
    add_item(get_cart(user), make_product("p2", price="7.50", active=False), 1)
    client = logged_in_client(user)

    response = client.get(reverse("orders:checkout"))

    assert response.status_code == 200
    assert "No longer available" in response.content.decode()      # the line is still shown, with its warning
    assert len(response.context["lines"]) == 2
    assert response.context["available_count"] == 1
    assert "<dt>1 available product</dt>" in response.content.decode()     # the row agrees with the total beside it
    assert response.context["subtotal"] == Decimal("20.00")
    assert response.context["subtotal"] == cart_subtotal(get_cart(user).items.select_related("product"))


def test_insufficient_stock_blocks_order_with_409_no_mutation():
    user = make_user()
    product = make_product("p1", stock=2)
    add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    review = open_checkout(client)
    product.stock = 0
    product.save(update_fields=["stock"])

    response = place(client, review)

    assert response.status_code == 409
    assert not Order.objects.filter(owner=user).exists()
    assert CartItem.objects.filter(cart__owner=user).exists()


# --- replay / idempotency (service level) ---


def test_replay_after_cart_already_cleared_returns_original_order():
    user = make_user()
    product = make_product("p1", stock=5)
    add_item(get_cart(user), product, 1)
    review = review_for(user)
    key = str(uuid.uuid4())

    first = services.checkout(user, key, review)
    second = services.checkout(user, key, review)     # the cart is empty now

    assert second.pk == first.pk
    assert Order.objects.filter(owner=user).count() == 1


def test_replay_with_an_identical_readded_cart_returns_original_order_and_leaves_the_cart_alone():
    user = make_user()
    product = make_product("p1", stock=5)
    add_item(get_cart(user), product, 2)
    review = review_for(user)
    key = str(uuid.uuid4())
    first = services.checkout(user, key, review)

    # A resurrected stale key (known accepted edge case) plus an identical re-add.
    new_item = add_item(get_cart(user), product, 2)
    second = services.checkout(user, key, review)

    assert second.pk == first.pk
    assert Order.objects.filter(owner=user).count() == 1
    assert CartItem.objects.filter(pk=new_item.pk).exists()


def test_same_key_with_a_different_review_conflicts_even_when_the_cart_is_empty():
    # CHK-002: a cleared cart must not let a request with different contents collect the existing order.
    user = make_user()
    product = make_product("p1", stock=5)
    add_item(get_cart(user), product, 1)
    key = str(uuid.uuid4())
    services.checkout(user, key, review_for(user))

    with pytest.raises(services.CheckoutConflictError):
        services.checkout(user, key, NO_MATCH)          # empty cart, different review

    add_item(get_cart(user), make_product("p2", stock=5), 1)
    with pytest.raises(services.CheckoutConflictError):
        services.checkout(user, key, review_for(user))  # non-empty cart, different contents

    assert Order.objects.filter(owner=user).count() == 1
    assert CartItem.objects.filter(cart__owner=user).count() == 1


def test_post_with_a_different_review_and_an_existing_key_rerenders_at_409():
    user = make_user()
    product = make_product("p1", stock=5)
    add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    place(client, open_checkout(client))
    order = Order.objects.get(owner=user)

    add_item(get_cart(user), make_product("p2", stock=5), 1)
    session = client.session
    session[SESSION_KEY] = str(order.idempotency_key)      # a resurrected key
    session.save()

    response = place(client, review_for(user))

    assert response.status_code == 409
    assert Order.objects.filter(owner=user).count() == 1


@pytest.mark.parametrize("winner_review, replays", [("same", True), ("different", False)])
def test_integrity_error_safety_net_compares_the_winners_fingerprint(monkeypatch, winner_review, replays):
    user = make_user()
    product = make_product("p1", stock=5)
    add_item(get_cart(user), product, 1)
    review = review_for(user)
    key = uuid.uuid4()
    winner = Order.objects.create(
        owner=user, namespace=settings.DEMO_NAMESPACE, external_id=None, status=Order.Status.COMPLETED,
        total="10.00", placed_at=timezone.now(), idempotency_key=key,
        request_fingerprint=review if winner_review == "same" else "b" * 64)

    # Force both pre-checks to miss the existing order so the unique constraint fires at insert time.
    real, calls = services._find_order, {"n": 0}

    def find(owner, idempotency_key):
        calls["n"] += 1
        return None if calls["n"] <= 2 else real(owner, idempotency_key)

    monkeypatch.setattr(services, "_find_order", find)

    if replays:
        assert services.checkout(user, key, review).pk == winner.pk
    else:
        with pytest.raises(services.CheckoutConflictError):
            services.checkout(user, key, review)
    assert Order.objects.filter(owner=user).count() == 1
    assert CartItem.objects.filter(cart__owner=user).exists()
    product.refresh_from_db()
    assert product.stock == 5


# --- review binding (CHK-001) ---


def test_item_added_after_review_blocks_the_order_until_it_is_reviewed_again():
    user = make_user()
    add_item(get_cart(user), make_product("p1", stock=5), 1)
    client = logged_in_client(user)
    review = open_checkout(client)
    add_item(get_cart(user), make_product("p2", stock=5), 1)

    blocked = place(client, review)

    assert blocked.status_code == 200
    assert "changed" in blocked.content.decode().lower()
    assert not Order.objects.filter(owner=user).exists()
    assert CartItem.objects.filter(cart__owner=user).count() == 2
    fresh = blocked.context["review"]
    assert fresh != review

    done = place(client, fresh)

    assert done.status_code == 302
    assert OrderItem.objects.filter(order__owner=user).count() == 2


def test_a_second_tab_does_not_change_what_the_first_tab_buys():
    user = make_user()
    add_item(get_cart(user), make_product("p1", stock=5), 1)
    browser = logged_in_client(user)            # both tabs share one session
    review_tab_1 = open_checkout(browser)
    add_item(get_cart(user), make_product("p2", stock=5), 1)
    review_tab_2 = open_checkout(browser)
    assert review_tab_1 != review_tab_2

    first = place(browser, review_tab_1)

    assert first.status_code == 200 and not Order.objects.filter(owner=user).exists()

    second = place(browser, review_tab_2)

    assert second.status_code == 302
    assert OrderItem.objects.filter(order__owner=user).count() == 2


def test_quantity_changed_after_review_blocks_the_order():
    user = make_user()
    product = make_product("p1", stock=20)
    item = add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    review = open_checkout(client)
    set_item_quantity(get_cart(user), item, 9)

    blocked = place(client, review)

    assert blocked.status_code == 200 and "changed" in blocked.content.decode().lower()
    assert not Order.objects.filter(owner=user).exists()
    product.refresh_from_db()
    assert product.stock == 20

    place(client, blocked.context["review"])

    assert OrderItem.objects.get(order__owner=user).quantity == 9
    product.refresh_from_db()
    assert product.stock == 11


def test_removing_an_item_after_review_blocks_the_order_and_a_rereview_succeeds():
    user = make_user()
    item_a = add_item(get_cart(user), make_product("p1", stock=5), 1)
    item_b = add_item(get_cart(user), make_product("p2", stock=5), 1)
    client = logged_in_client(user)
    review = open_checkout(client)
    remove_item(get_cart(user), item_b.pk)

    blocked = place(client, review)

    assert blocked.status_code == 200
    assert "changed" in blocked.content.decode().lower()
    assert not Order.objects.filter(owner=user).exists()
    assert CartItem.objects.filter(pk=item_a.pk).exists()

    retried = place(client, blocked.context["review"])

    assert retried.status_code == 302
    assert OrderItem.objects.filter(order__owner=user).count() == 1


def test_a_replaced_cart_reports_changed_not_empty():
    user = make_user()
    item = add_item(get_cart(user), make_product("p1", stock=5), 1)
    client = logged_in_client(user)
    review = open_checkout(client)
    remove_item(get_cart(user), item.pk)
    add_item(get_cart(user), make_product("p2", stock=5), 1)

    response = place(client, review)

    assert response.status_code == 200
    content = response.content.decode().lower()
    assert "changed" in content
    assert "empty" not in content


def test_an_emptied_cart_after_review_is_reported_as_empty():
    user = make_user()
    item = add_item(get_cart(user), make_product("p1", stock=5), 1)
    client = logged_in_client(user)
    review = open_checkout(client)
    remove_item(get_cart(user), item.pk)

    response = place(client, review)

    assert response.status_code == 302 and response.url == reverse("cart:detail")
    assert not Order.objects.filter(owner=user).exists()


def test_a_forged_but_well_formed_review_is_rejected_as_changed():
    user = make_user()
    product = make_product("p1", stock=5)
    add_item(get_cart(user), product, 1)
    client = logged_in_client(user)
    open_checkout(client)

    response = place(client, NO_MATCH)

    assert response.status_code == 200 and "changed" in response.content.decode().lower()
    assert not Order.objects.filter(owner=user).exists()
    product.refresh_from_db()
    assert product.stock == 5


@pytest.mark.parametrize("value", ["", "not-hex"])        # missing (an absent field reads as ""), malformed
def test_a_missing_or_malformed_review_redirects_without_ordering(value):
    user = make_user()
    add_item(get_cart(user), make_product("p1", stock=5), 1)
    client = logged_in_client(user)
    open_checkout(client)

    response = client.post(reverse("orders:checkout"), {"review": value})

    assert response.status_code == 302 and response.url == reverse("orders:checkout")
    assert not Order.objects.filter(owner=user).exists()


# --- auth / ownership / CSRF ---


def test_order_detail_returns_404_for_foreign_order_200_for_owner():
    owner = make_user("owner")
    other = make_user("other")
    product = make_product("p1", stock=5)
    add_item(get_cart(owner), product, 1)
    order = services.checkout(owner, str(uuid.uuid4()), review_for(owner))

    assert logged_in_client(owner).get(reverse("orders:detail", args=[order.pk])).status_code == 200
    assert logged_in_client(other).get(reverse("orders:detail", args=[order.pk])).status_code == 404


# --- NULL external_id uniqueness (order_source_unique tolerates only NULLs) ---


def test_two_sequential_checkouts_both_succeed():
    user = make_user()
    product = make_product("p1", stock=10)
    add_item(get_cart(user), product, 1)
    order1 = services.checkout(user, str(uuid.uuid4()), review_for(user))

    add_item(get_cart(user), product, 1)
    order2 = services.checkout(user, str(uuid.uuid4()), review_for(user))

    assert order1.pk != order2.pk
    assert Order.objects.filter(owner=user).count() == 2


# --- concurrent (real PostgreSQL transactions/connections, per docs/TESTING.md) ---


def run_in_threads(target, argument_sets):
    """Start one thread per argument set behind a barrier; each closes its own connection."""
    barrier = threading.Barrier(len(argument_sets))

    def wrapped(*args):
        barrier.wait()
        try:
            target(*args)
        finally:
            connection.close()

    threads = [threading.Thread(target=wrapped, args=args) for args in argument_sets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkouts_same_idempotency_key_create_exactly_one_order():
    user = make_user()
    product = make_product("p1", stock=10)
    add_item(get_cart(user), product, 2)
    key = str(uuid.uuid4())
    review = review_for(user)
    results, errors = [], []

    def attempt():
        try:
            results.append(services.checkout(user, key, review))
        except Exception as exc:  # noqa: BLE001 - surfaced via assertion below
            errors.append(exc)

    run_in_threads(attempt, [(), ()])

    assert not errors, errors
    assert Order.objects.filter(owner=user).count() == 1
    assert len({order.pk for order in results}) == 1
    product.refresh_from_db()
    assert product.stock == 8


@pytest.mark.django_db(transaction=True)
def test_checkout_waits_for_a_concurrent_cart_change_and_then_rejects_the_stale_review():
    """Checkout locks the cart rows: a change committing mid-checkout must be seen, not overwritten."""
    user = make_user()
    product = make_product("p1", stock=10)
    item = add_item(get_cart(user), product, 1)
    review = review_for(user)
    outcome = {}

    def attempt():
        try:
            outcome["result"] = services.checkout(user, str(uuid.uuid4()), review)
        except Exception as exc:  # noqa: BLE001 - asserted on below, and shown if the test fails early
            outcome["result"] = exc
        finally:
            connection.close()

    thread = threading.Thread(target=attempt)
    with transaction.atomic():
        CartItem.objects.select_for_update().get(pk=item.pk)      # another tab is in the middle of an update
        thread.start()
        wait_until_blocked()                                       # checkout is now waiting on the row lock
        CartItem.objects.filter(pk=item.pk).update(quantity=5)
    thread.join(10)

    assert isinstance(outcome["result"], services.CartChangedError)
    assert not Order.objects.filter(owner=user).exists()
    product.refresh_from_db()
    assert product.stock == 10
    assert CartItem.objects.get(pk=item.pk).quantity == 5


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_key_with_a_valid_and_an_invalid_review_never_orders_for_the_invalid_one():
    user = make_user()
    product = make_product("p1", stock=10)
    add_item(get_cart(user), product, 2)
    key = str(uuid.uuid4())
    valid = review_for(user)
    outcomes = {}

    def attempt(label, review):
        try:
            outcomes[label] = ("ok", services.checkout(user, key, review))
        except (services.CartChangedError, services.CheckoutConflictError) as exc:
            outcomes[label] = ("rejected", exc)

    run_in_threads(attempt, [("valid", valid), ("invalid", NO_MATCH)])

    assert outcomes["valid"][0] == "ok"
    assert outcomes["invalid"][0] == "rejected"
    assert Order.objects.filter(owner=user).count() == 1
    product.refresh_from_db()
    assert product.stock == 8


# --- order history (Batch 5) ---


def test_order_list_requires_login():
    response = Client().get(reverse("orders:list"))

    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)


def test_order_list_shows_only_the_owners_orders_most_recent_first():
    owner = make_user("owner")
    other = make_user("other")
    product = make_product("p1", stock=10)

    add_item(get_cart(owner), product, 1)
    older = services.checkout(owner, str(uuid.uuid4()), review_for(owner))
    add_item(get_cart(owner), product, 1)
    newer = services.checkout(owner, str(uuid.uuid4()), review_for(owner))

    add_item(get_cart(other), product, 1)
    services.checkout(other, str(uuid.uuid4()), review_for(other))

    response = logged_in_client(owner).get(reverse("orders:list"))

    assert response.status_code == 200
    order_pks = [order.pk for order in response.context["orders"]]
    assert order_pks == [newer.pk, older.pk]


def test_order_list_item_count_is_distinct_line_items_not_total_quantity():
    user = make_user()
    product_a = make_product("p1", stock=10)
    product_b = make_product("p2", stock=10)
    add_item(get_cart(user), product_a, 5)
    add_item(get_cart(user), product_b, 3)
    order = services.checkout(user, str(uuid.uuid4()), review_for(user))

    response = logged_in_client(user).get(reverse("orders:list"))

    listed = next(o for o in response.context["orders"] if o.pk == order.pk)
    assert listed.item_count == 2


def test_order_list_pagination_boundary():
    user = make_user()
    product = make_product("p1", stock=20)
    for _ in range(11):
        add_item(get_cart(user), product, 1)
        services.checkout(user, str(uuid.uuid4()), review_for(user))

    client = logged_in_client(user)
    page1 = client.get(reverse("orders:list"))
    page2 = client.get(reverse("orders:list"), {"page": 2})

    assert len(page1.context["orders"]) == 10
    assert len(page2.context["orders"]) == 1


def test_order_list_empty_state():
    client = logged_in_client(make_user())

    response = client.get(reverse("orders:list"))

    assert response.status_code == 200
    assert "haven't placed any orders" in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkouts_different_users_racing_last_unit_of_stock():
    product = make_product("p1", stock=1)
    user_a = make_user("racer-a")
    user_b = make_user("racer-b")
    add_item(get_cart(user_a), product, 1)
    add_item(get_cart(user_b), product, 1)
    review_a, review_b = review_for(user_a), review_for(user_b)

    outcomes = {}
    barrier = threading.Barrier(2)

    def attempt(label, user, review):
        barrier.wait()
        try:
            order = services.checkout(user, str(uuid.uuid4()), review)
            outcomes[label] = ("ok", order)
        except services.InsufficientStockError as exc:
            outcomes[label] = ("conflict", exc)
        finally:
            connection.close()

    threads = [
        threading.Thread(target=attempt, args=("a", user_a, review_a)),
        threading.Thread(target=attempt, args=("b", user_b, review_b)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcome[0] for outcome in outcomes.values()) == ["conflict", "ok"]
    product.refresh_from_db()
    assert product.stock == 0
