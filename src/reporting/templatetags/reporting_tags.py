from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def money(value):
    if value is None:
        return "—"
    return f"{Decimal(value):,.2f}"


@register.filter
def units(value):
    if value is None:
        return "—"
    return f"{int(value):,}"


@register.filter
def rate(value):
    if value is None:
        return "—"
    return f"{Decimal(value):,.2f}"


@register.filter
def signed_money(value):
    if value is None:
        return "—"
    amount = Decimal(value)
    return f"{amount:+,.2f}"


@register.filter
def signed_units(value):
    if value is None:
        return "—"
    return f"{int(value):+,}"


@register.filter
def signed_percent(value):
    if value is None:
        return "—"
    return f"{Decimal(value):+.1f}%"
