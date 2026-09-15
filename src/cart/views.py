from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.views.generic import View

from catalogue.models import Product

from . import services
from .forms import AddToCartForm, UpdateCartItemForm
from .models import CartItem
from .services import CartValidationError


class HtmxLoginRequiredMixin(LoginRequiredMixin):
    def handle_no_permission(self):
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=200, headers={"HX-Redirect": resolve_url(self.get_login_url())})
        return super().handle_no_permission()


class CartDetailView(HtmxLoginRequiredMixin, View):
    def get(self, request):
        cart = services.get_cart(request.user)
        items = cart.items.select_related("product").order_by("product__name", "pk")
        context = {"cart": cart, "items": items, "subtotal": services.cart_subtotal(items), "error": None}
        return render(request, "cart/detail.html", context)


class CartMutationView(HtmxLoginRequiredMixin, View):
    def _respond(self, request, error=None):
        cart = services.get_cart(request.user)
        items = cart.items.select_related("product").order_by("product__name", "pk")
        context = {"cart": cart, "items": items, "subtotal": services.cart_subtotal(items), "error": error}
        if request.headers.get("HX-Request") == "true":
            return render(request, "cart/_content.html", context, status=200)
        if error:
            messages.error(request, error)
        return redirect("cart:detail")


class CartAddView(CartMutationView):
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
        return self._respond(request)


class CartUpdateView(CartMutationView):
    def post(self, request, pk):
        cart = services.get_cart(request.user)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        form = UpdateCartItemForm(request.POST)
        if not form.is_valid():
            return self._respond(request, error="Invalid quantity.")

        try:
            services.set_item_quantity(cart, item, form.cleaned_data["quantity"])
        except CartValidationError as exc:
            return self._respond(request, error=exc.message)
        return self._respond(request)


class CartDeleteView(CartMutationView):
    def post(self, request, pk):
        cart = services.get_cart(request.user)
        services.remove_item(cart, pk)
        return self._respond(request)
