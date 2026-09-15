"""Explicit cart business functions, callable from views or management commands."""
from decimal import Decimal

from django.db import IntegrityError, transaction

from .models import MAX_QUANTITY, Cart, CartItem


class CartValidationError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(owner=user)
    return cart


def _check_stock(product, quantity):
    if quantity > product.stock:
        raise CartValidationError(f'Only {product.stock} of "{product.name}" in stock (indicative).')


def add_item(cart, product, quantity):
    """Increment quantity for (cart, product), creating the row if needed.

    Handles two distinct races: concurrent increments of an existing row
    (locked via select_for_update) and concurrent first-time inserts of the
    same (cart, product) pair (caught via IntegrityError on the unique
    constraint, then retried as an increment).
    """
    with transaction.atomic():
        try:
            item = CartItem.objects.select_for_update().get(cart=cart, product=product)
        except CartItem.DoesNotExist:
            _check_stock(product, quantity)
            try:
                with transaction.atomic():
                    return CartItem.objects.create(cart=cart, product=product, quantity=quantity)
            except IntegrityError:
                item = CartItem.objects.select_for_update().get(cart=cart, product=product)

        new_quantity = item.quantity + quantity
        if new_quantity > MAX_QUANTITY:
            raise CartValidationError(
                f'Cannot add {quantity} more of "{product.name}": cart is limited to {MAX_QUANTITY}.'
            )
        _check_stock(product, new_quantity)
        item.quantity = new_quantity
        item.save(update_fields=["quantity"])
        return item


def set_item_quantity(cart, item, quantity):
    with transaction.atomic():
        item = CartItem.objects.select_for_update().get(pk=item.pk, cart=cart)
        if not item.product.active:
            raise CartValidationError(
                f'"{item.product.name}" is no longer available; remove it from your cart instead.'
            )
        _check_stock(item.product, quantity)
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        return item


def remove_item(cart, item_id):
    CartItem.objects.filter(pk=item_id, cart=cart).delete()


def cart_subtotal(items):
    """Sum line totals for currently-active items in an already-fetched iterable.

    Takes the view's already select_related-fetched `items` rather than
    re-querying cart.items, to avoid a duplicate query plus one extra
    product lookup per item.
    """
    return sum((item.line_total for item in items if item.product.active), Decimal("0.00"))
