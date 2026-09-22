"""Explicit checkout business functions, callable from views or management commands.

See docs/plans/batch-04-checkout.md for the design rationale (why the idempotency lookup
precedes the empty-cart check, why the locked cart-item query drops select_related, and why
Order creation's IntegrityError handling re-raises when no winning order is found) and
docs/plans/checkout-review-fixes.md for the review-fingerprint design that replaced the
session-pinned item IDs (review findings CHK-001 and CHK-002).
"""
import hashlib
import re
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from cart.models import CartItem
from cart.services import get_cart
from catalogue.models import Product

from .models import Order, OrderItem


class CheckoutError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class EmptyCartError(CheckoutError):
    def __init__(self):
        super().__init__("Your cart is empty.")


class CartChangedError(CheckoutError):
    def __init__(self):
        super().__init__("Your cart changed since you reviewed it. Please review it again.")


class InactiveProductError(CheckoutError):
    pass


class InvalidProductError(CheckoutError):
    pass


class InsufficientStockError(CheckoutError):
    pass


class CheckoutConflictError(CheckoutError):
    def __init__(self):
        super().__init__("This checkout no longer matches your cart. Please review and try again.")


# A review value is the hex SHA-256 produced by fingerprint_for; anything else is rejected before checkout.
FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")


def compute_fingerprint(namespace, pairs):
    """pairs: iterable of (product.external_id, quantity). Price is deliberately excluded."""
    canonical = namespace + "|" + "|".join(f"{eid}:{qty}" for eid, qty in sorted(pairs))
    return hashlib.sha256(canonical.encode()).hexdigest()


def fingerprint_for(lines):
    """Fingerprint of cart lines. lines: iterable of (product, quantity).

    The review page renders this for the lines it shows; checkout recomputes it from the locked cart
    and requires the two to match, so a stale or forged value can only cause a rejection.
    """
    return compute_fingerprint(settings.DEMO_NAMESPACE, [(product.external_id, quantity) for product, quantity in lines])


def _find_order(user, idempotency_key):
    return Order.objects.filter(owner=user, idempotency_key=idempotency_key).first()


def _replay(order, review):
    """An existing order for this key answers the request only if it was for the same reviewed contents."""
    if order.request_fingerprint == review:
        return order
    raise CheckoutConflictError()


def checkout(user, idempotency_key, review):
    """Turn the user's cart into a completed Order, provided it still matches what the review page showed.

    `review` is the fingerprint of the lines the page displayed (fingerprint_for). Every path that would
    return an existing order for this key compares fingerprints first.
    """
    cart = get_cart(user)

    # Step 1: look up the existing order before raising anything about cart state, so a duplicate POST
    # after a successful checkout replays cleanly instead of bouncing the user to an empty cart.
    existing = _find_order(user, idempotency_key)
    if existing is not None:
        return _replay(existing, review)

    with transaction.atomic():
        # Step 2: lock every cart row of this user. No select_related — item.product_id is a local
        # column, and a joined product would be a pre-lock copy of the row we lock separately below.
        locked_items = list(cart.items.select_for_update(of=("self",)).order_by("pk"))

        # Step 3: another request with this key may have committed while we waited for the locks.
        existing = _find_order(user, idempotency_key)
        if existing is not None:
            return _replay(existing, review)
        if not locked_items:
            raise EmptyCartError()

        product_ids = {item.product_id for item in locked_items}
        locked_products = {
            product.pk: product
            for product in Product.objects.filter(pk__in=product_ids).select_for_update().order_by("pk")
        }
        lines = [(item, locked_products[item.product_id]) for item in locked_items]

        # Step 4: what we are about to buy must be exactly what the user reviewed.
        fingerprint = fingerprint_for([(product, item.quantity) for item, product in lines])
        if fingerprint != review:
            raise CartChangedError()

        for item, product in lines:
            if not product.active:
                raise InactiveProductError(
                    f'"{product.name}" is no longer available; remove it from your cart instead.'
                )
            if product.namespace != settings.DEMO_NAMESPACE:
                raise InvalidProductError(f'"{product.name}" is not available for checkout.')
            if item.quantity > product.stock:
                raise InsufficientStockError(f'Only {product.stock} of "{product.name}" left in stock.')

        total = sum((product.price * item.quantity for item, product in lines), Decimal("0.00"))

        # Step 5: create the Order, guarding against a concurrent same-key insert. With the cart rows
        # locked this is a safety net; it still compares fingerprints before returning the winner.
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    owner=user,
                    namespace=settings.DEMO_NAMESPACE,
                    external_id=None,
                    status=Order.Status.COMPLETED,
                    total=total,
                    placed_at=timezone.now(),
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                )
        except IntegrityError:
            winner = _find_order(user, idempotency_key)
            if winner is None:
                raise
            return _replay(winner, review)

        # Step 6: items, stock, cart — all still inside the outer atomic().
        OrderItem.objects.bulk_create(
            OrderItem(order=order, product=product, external_id=None, quantity=item.quantity, unit_price=product.price)
            for item, product in lines
        )

        for item, product in lines:
            product.stock -= item.quantity
        Product.objects.bulk_update([product for _, product in lines], ["stock"])

        CartItem.objects.filter(pk__in=[item.pk for item, _ in lines]).delete()

        return order
