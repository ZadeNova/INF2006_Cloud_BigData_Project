from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import View

from accounts.mixins import HtmxLoginRequiredMixin
from catalogue.models import Product

from . import services
from .forms import AddToCartForm, UpdateCartItemForm
from .models import CartItem
from .services import CartValidationError


class CartDetailView(HtmxLoginRequiredMixin, View):
    def get(self, request):
        cart = services.get_cart(request.user)
        items = cart.items.select_related("product").order_by("product__name", "product__size", "pk")
        context = {"cart": cart, "items": items, "subtotal": services.cart_subtotal(items), "error": None}
        return render(request, "cart/detail.html", context)


class CartMutationView(HtmxLoginRequiredMixin, View):
    def _respond(self, request, error=None):
        cart = services.get_cart(request.user)
        items = cart.items.select_related("product").order_by("product__name", "product__size", "pk")
        context = {"cart": cart, "items": items, "subtotal": services.cart_subtotal(items), "error": error}
        if request.headers.get("HX-Request") == "true":
            return render(request, "cart/_content.html", context, status=200)
        if error:
            messages.error(request, error)
        return redirect("cart:detail")


def _shop_return_path(request):
    """The catalogue page the customer added from, so they can keep shopping; None if unsafe."""
    target = request.POST.get("next", "")
    shop = reverse("catalogue:product_list")
    if (target.startswith(shop) and not target.startswith(reverse("catalogue:manage_list"))
            and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()})):
        return target
    return None


class CartAddView(CartMutationView):
    def _respond(self, request, error=None, product=None):
        back = _shop_return_path(request)
        if back is None or request.headers.get("HX-Request") == "true":
            return super()._respond(request, error=error)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, f"{product.display_name} added to your cart.", extra_tags="cart-added")
        return redirect(back)

    def post(self, request):
        form = AddToCartForm(request.POST)
        if not form.is_valid():
            return self._respond(request, error="Invalid product or quantity.")

        product = get_object_or_404(
            Product,
            pk=form.cleaned_data["product_id"],
            namespace=settings.DEMO_NAMESPACE,
            active=True,
        )
        cart = services.get_cart(request.user)
        try:
            services.add_item(cart, product, form.cleaned_data["quantity"])
        except CartValidationError as exc:
            return self._respond(request, error=exc.message)
        return self._respond(request, product=product)


class CartUpdateView(CartMutationView):
    def post(self, request, pk):
        cart = services.get_cart(request.user)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        form = UpdateCartItemForm(request.POST)
        if not form.is_valid():
            return self._respond(request, error="Invalid quantity.")

        try:
            services.set_item_quantity(cart, item, form.cleaned_data["quantity"])
        except services.CartItemNotFound:
            raise Http404 from None
        except CartValidationError as exc:
            return self._respond(request, error=exc.message)
        return self._respond(request)


class CartDeleteView(CartMutationView):
    def post(self, request, pk):
        cart = services.get_cart(request.user)
        services.remove_item(cart, pk)
        return self._respond(request)
