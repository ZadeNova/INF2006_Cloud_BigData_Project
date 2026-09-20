"""Negative security tests from docs/SECURITY.md (review finding SEC-003).

Each test asserts both the rejection and that business state is unchanged, so a status code alone can never
pass. Covered here: unauthenticated mutations, forged price/owner/total fields, quantity manipulation and CSRF on
every browser mutation (normal and HTMX). Foreign cart/order access and duplicate checkout are covered in
test_cart.py and test_orders.py; non-operator analytics and anonymous S3 access wait for the dashboard and the
cloud deployment.
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from cart.models import CartItem
from cart.services import add_item, get_cart
from catalogue.models import Product
from orders import services
from orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db
COOKIE = "c" * 32          # a well-formed CSRF secret


def make_product(external_id="p1", price="10.00", stock=10):
    return Product.objects.create(namespace=settings.DEMO_NAMESPACE, external_id=external_id,
                                  name=f"Product {external_id}", category="Sample", price=price, cost="5.00",
                                  stock=stock, lead_time_days=5, active=True)


def make_user(username="shopper", operator=False):
    user = get_user_model().objects.create_user(username=username)
    if operator:
        user.user_permissions.add(Permission.objects.get(codename="toggle_product_active"))
    return user


def review_for(user):
    items = get_cart(user).items.select_related("product")
    return services.fingerprint_for([(item.product, item.quantity) for item in items])


# --- scenarios: (url, data, check that nothing changed) ------------------------------------------

def cart_add(user):
    product = make_product()
    return reverse("cart:add"), {"product_id": product.pk, "quantity": 1}, \
        lambda: not CartItem.objects.filter(cart__owner=user).exists()


def cart_update(user):
    item = add_item(get_cart(user), make_product(), 1)
    return reverse("cart:update", args=[item.pk]), {"quantity": 5}, \
        lambda: CartItem.objects.get(pk=item.pk).quantity == 1


def cart_delete(user):
    item = add_item(get_cart(user), make_product(), 1)
    return reverse("cart:delete", args=[item.pk]), {}, lambda: CartItem.objects.filter(pk=item.pk).exists()


def toggle_active(user):
    product = make_product()
    return reverse("catalogue:product_toggle_active", args=[product.pk]), {"active": "false"}, \
        lambda: Product.objects.get(pk=product.pk).active is True


def checkout(user):
    product = make_product(stock=5)
    add_item(get_cart(user), product, 1)
    return reverse("orders:checkout"), {"review": review_for(user)}, \
        lambda: not Order.objects.filter(owner=user).exists() and Product.objects.get(pk=product.pk).stock == 5


SCENARIOS = [cart_add, cart_update, cart_delete, toggle_active, checkout]
IDS = [scenario.__name__ for scenario in SCENARIOS]


# --- CSRF on every browser mutation, normal and HTMX ---------------------------------------------

def csrf_client(user, cookie=True):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    if cookie:
        client.cookies["csrftoken"] = COOKIE
    return client


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
@pytest.mark.parametrize("htmx", [False, True], ids=["normal", "htmx"])
@pytest.mark.parametrize("mode", ["no_token", "wrong_header", "wrong_form_field"])
def test_a_mutation_without_a_valid_csrf_token_is_rejected_and_changes_nothing(scenario, htmx, mode):
    user = make_user(operator=True)
    url, data, unchanged = scenario(user)
    client = csrf_client(user, cookie=mode != "no_token")
    extra = {"HTTP_HX_REQUEST": "true"} if htmx else {}
    if mode == "wrong_header":
        extra["HTTP_X_CSRFTOKEN"] = "a" * 32
    if mode == "wrong_form_field":
        data = {**data, "csrfmiddlewaretoken": "b" * 64}

    response = client.post(url, data, **extra)

    assert response.status_code == 403
    assert unchanged()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
@pytest.mark.parametrize("htmx", [False, True], ids=["normal", "htmx"])
def test_the_same_mutation_with_a_valid_csrf_token_is_accepted(scenario, htmx):
    """Control: the 403s above are caused by the token, not by some other refusal."""
    user = make_user(operator=True)
    url, data, unchanged = scenario(user)
    client = csrf_client(user)
    if scenario is checkout:
        client.get(url)                     # checkout needs its review page opened first (session key)
    extra = {"HTTP_X_CSRFTOKEN": COOKIE}
    if htmx:
        extra["HTTP_HX_REQUEST"] = "true"

    response = client.post(url, data, **extra)

    assert response.status_code in (200, 302)
    assert not unchanged()


# --- unauthenticated mutations -------------------------------------------------------------------

def test_anonymous_checkout_post_is_redirected_to_login_and_creates_nothing():
    owner = make_user("owner")
    product = make_product(stock=5)
    add_item(get_cart(owner), product, 1)

    response = Client().post(reverse("orders:checkout"), {"review": review_for(owner)})

    assert response.status_code == 302 and response.url.startswith(settings.LOGIN_URL)
    assert not Order.objects.exists()
    product.refresh_from_db()
    assert product.stock == 5


@pytest.mark.parametrize("scenario", [cart_add, cart_update, cart_delete], ids=["add", "update", "delete"])
def test_anonymous_cart_mutations_are_redirected_to_login_and_change_nothing(scenario):
    owner = make_user("owner")
    url, data, unchanged = scenario(owner)

    response = Client().post(url, data)

    assert response.status_code == 302 and response.url.startswith(settings.LOGIN_URL)
    assert unchanged()


@pytest.mark.parametrize("scenario", [cart_add, cart_update, cart_delete], ids=["add", "update", "delete"])
def test_anonymous_htmx_cart_mutations_get_an_hx_redirect_and_change_nothing(scenario):
    owner = make_user("owner")
    url, data, unchanged = scenario(owner)

    response = Client().post(url, data, HTTP_HX_REQUEST="true")

    assert response.status_code == 200 and response["HX-Redirect"].startswith(settings.LOGIN_URL)
    assert unchanged()


def test_a_customer_cannot_use_the_operator_toggle():
    customer = make_user("customer")
    url, data, unchanged = toggle_active(customer)
    client = Client()
    client.force_login(customer)

    assert client.post(url, data).status_code == 403
    assert Client().post(url, data).status_code == 403
    assert unchanged()


# --- forged price, owner and total fields --------------------------------------------------------

def test_checkout_ignores_forged_price_owner_total_and_status_fields():
    user = make_user()
    victim = make_user("victim")
    product = make_product(price="10.00", stock=5)
    add_item(get_cart(user), product, 2)
    client = Client()
    client.force_login(user)
    review = client.get(reverse("orders:checkout")).context["review"]

    client.post(reverse("orders:checkout"), {
        "review": review, "price": "0.01", "unit_price": "0.01", "total": "0.01", "subtotal": "0.01",
        "owner": victim.pk, "owner_id": victim.pk, "user": victim.pk, "user_id": victim.pk,
        "status": "refunded", "namespace": "attacker/namespace", "quantity": 999,
        "idempotency_key": "11111111-1111-1111-1111-111111111111", "request_fingerprint": "f" * 64,
        "product": product.pk, "stock": 999,
    })

    order = Order.objects.get()
    assert order.owner == user and not Order.objects.filter(owner=victim).exists()
    assert order.status == Order.Status.COMPLETED
    assert order.namespace == settings.DEMO_NAMESPACE
    assert str(order.idempotency_key) != "11111111-1111-1111-1111-111111111111"
    assert order.request_fingerprint == review
    assert str(order.total) == "20.00"
    line = OrderItem.objects.get(order=order)
    assert (line.quantity, str(line.unit_price)) == (2, "10.00")
    product.refresh_from_db()
    assert product.stock == 3


def test_cart_add_ignores_forged_owner_cart_and_price_fields():
    user = make_user()
    victim = make_user("victim")
    victim_cart = get_cart(victim)
    product = make_product()
    client = Client()
    client.force_login(user)

    client.post(reverse("cart:add"), {
        "product_id": product.pk, "quantity": 2, "owner": victim.pk, "user": victim.pk, "cart": victim_cart.pk,
        "cart_id": victim_cart.pk, "price": "0.01", "unit_price": "0.01"})

    item = CartItem.objects.get()
    assert item.cart.owner == user and item.quantity == 2
    assert not victim_cart.items.exists()


# --- quantity manipulation -----------------------------------------------------------------------

BAD_QUANTITIES = ["-1", "0", "abc", "", " ", "1.5", "1e3", "1000", "99999999999999999999", "0x10", "١٢"]


@pytest.mark.parametrize("quantity", BAD_QUANTITIES)
def test_cart_add_rejects_bad_quantities_without_creating_anything(quantity):
    user = make_user()
    product = make_product()
    client = Client()
    client.force_login(user)

    client.post(reverse("cart:add"), {"product_id": product.pk, "quantity": quantity})

    assert not CartItem.objects.filter(cart__owner=user).exists()


@pytest.mark.parametrize("quantity", BAD_QUANTITIES)
def test_cart_update_rejects_bad_quantities_without_changing_the_item(quantity):
    user = make_user()
    item = add_item(get_cart(user), make_product(), 3)
    client = Client()
    client.force_login(user)

    client.post(reverse("cart:update", args=[item.pk]), {"quantity": quantity})

    assert CartItem.objects.get(pk=item.pk).quantity == 3
