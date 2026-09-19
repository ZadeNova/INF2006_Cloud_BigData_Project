"""Explicit checkout business functions, callable from views or management commands.

See docs/plans/batch-04-checkout.md for the full design rationale — in particular
why the idempotency-order lookup happens before any empty-cart check, why the
locked cart-item query drops select_related, and why Order creation's
IntegrityError handling must re-raise when no winning order is found.
"""
import hashlib
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
        super().__init__("Your cart changed since you started checkout. Please review it again.")


class InactiveProductError(CheckoutError):
    pass


class InvalidProductError(CheckoutError):
    pass


class InsufficientStockError(CheckoutError):
    pass


class CheckoutConflictError(CheckoutError):
    def __init__(self):
        super().__init__("This checkout no longer matches your cart. Please review and try again.")


def compute_fingerprint(namespace, pairs):
    """pairs: iterable of (product.external_id, quantity)."""
    canonical = namespace + "|" + "|".join(f"{eid}:{qty}" for eid, qty in sorted(pairs))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _fingerprint_for(lines):
    return compute_fingerprint(settings.DEMO_NAMESPACE, [(product.external_id, item.quantity) for item, product in lines])


def checkout(user, idempotency_key, item_ids):
    """Turn the pinned cart items into a completed Order.

    item_ids is the session-pinned set of CartItem PKs the review page showed;
    every step is scoped to exactly this set, never the whole cart.
    """
    cart = get_cart(user)

    # Step 1: resolve the pinned items (unlocked read) — used only for the
    # dedupe/replay fingerprint below, never to build the order itself.
    pinned_items = list(cart.items.filter(pk__in=item_ids).select_related("product"))

    # Step 2: look up the existing order before raising anything about cart
    # state, so a duplicate POST after a successful checkout replays cleanly
    # instead of bouncing the user to an empty cart.
    existing = Order.objects.filter(owner=user, idempotency_key=idempotency_key).first()
    if existing is not None:
        if not pinned_items:
            return existing
        fingerprint = compute_fingerprint(
            settings.DEMO_NAMESPACE, [(item.product.external_id, item.quantity) for item in pinned_items]
        )
        if fingerprint == existing.request_fingerprint:
            return existing
        raise CheckoutConflictError()

    # Step 3: no order found, and nothing pinned survived — distinguish a
    # genuinely empty cart from a stale pin against a non-empty cart.
    if not pinned_items:
        if not cart.items.exists():
            raise EmptyCartError()
        raise CartChangedError()

    with transaction.atomic():
        # Step 4: re-fetch and lock only the pinned cart items. No
        # select_related here — item.product_id is a local column, and a
        # joined product would be a pre-lock copy of the row we're about to
        # lock separately below.
        locked_items = list(
            cart.items.filter(pk__in=item_ids).select_for_update(of=("self",)).order_by("pk")
        )
        if len(locked_items) != len(item_ids):
            winner = Order.objects.filter(owner=user, idempotency_key=idempotency_key).first()
            if winner is not None:
                return winner
            raise CartChangedError()

        product_ids = {item.product_id for item in locked_items}
        locked_products = {
            product.pk: product
            for product in Product.objects.filter(pk__in=product_ids).select_for_update().order_by("pk")
        }

        lines = []
        for item in locked_items:
            product = locked_products[item.product_id]
            if not product.active:
                raise InactiveProductError(
                    f'"{product.name}" is no longer available; remove it from your cart instead.'
                )
            if product.namespace != settings.DEMO_NAMESPACE:
                raise InvalidProductError(f'"{product.name}" is not available for checkout.')
            if item.quantity > product.stock:
                raise InsufficientStockError(f'Only {product.stock} of "{product.name}" left in stock.')
            lines.append((item, product))

        total = sum((product.price * item.quantity for item, product in lines), Decimal("0.00"))
        fingerprint = _fingerprint_for(lines)

        # Step 5: create the Order, guarding against the concurrent-same-key race.
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
            winner = Order.objects.filter(owner=user, idempotency_key=idempotency_key).first()
            if winner is None:
                raise
            return winner

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
