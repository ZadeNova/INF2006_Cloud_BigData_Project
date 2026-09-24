import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, View

from cart.services import cart_subtotal

from . import services
from .models import Order

SESSION_KEY = "checkout_idempotency_key"


class CheckoutView(LoginRequiredMixin, View):
    """Read-only review page (GET) + place-order action (POST). No HTMX — page-to-page flow."""

    def _clear_session(self, request):
        request.session.pop(SESSION_KEY, None)

    def _prepare(self, request):
        """Shared render path: redirect if the cart is empty, else make sure a key exists.

        Returns an HttpResponse to return immediately, or a list of cart items.
        """
        cart = services.get_cart(request.user)
        items = list(cart.items.select_related("product").order_by("product__name", "pk"))
        if not items:
            self._clear_session(request)
            messages.info(request, "Your cart is empty.")
            return redirect("cart:detail")

        if not request.session.get(SESSION_KEY):
            request.session[SESSION_KEY] = str(uuid.uuid4())

        return items

    def _context(self, items, error=None):
        lines = []
        for item in items:
            product = item.product
            warning = None
            if not product.active:
                warning = "No longer available."
            elif item.quantity > product.stock:
                warning = f"Only {product.stock} left in stock."
            lines.append({"item": item, "product": product, "line_total": item.line_total, "warning": warning})
        review = services.fingerprint_for([(item.product, item.quantity) for item in items])
        # Same rule as the cart page: an unavailable line stays visible but is not added to the total.
        return {"lines": lines, "subtotal": cart_subtotal(items), "error": error, "review": review}

    def _render_error(self, request, message, status):
        result = self._prepare(request)
        if isinstance(result, HttpResponse):
            return result
        return render(request, "orders/checkout.html", self._context(result, error=message), status=status)

    def get(self, request):
        result = self._prepare(request)
        if isinstance(result, HttpResponse):
            return result
        return render(request, "orders/checkout.html", self._context(result))

    def post(self, request):
        key = request.session.get(SESSION_KEY)
        review = request.POST.get("review", "")
        if not key or not services.FINGERPRINT_RE.fullmatch(review):
            return redirect("orders:checkout")

        try:
            order = services.checkout(request.user, key, review)
        except services.EmptyCartError:
            self._clear_session(request)
            messages.info(request, "Your cart is empty.")
            return redirect("cart:detail")
        except services.CheckoutConflictError as exc:
            self._clear_session(request)
            return self._render_error(request, exc.message, status=409)
        except services.CartChangedError as exc:
            return self._render_error(request, exc.message, status=200)
        except (services.InactiveProductError, services.InvalidProductError) as exc:
            return self._render_error(request, exc.message, status=200)
        except services.InsufficientStockError as exc:
            return self._render_error(request, exc.message, status=409)

        self._clear_session(request)
        return redirect("orders:detail", pk=order.pk)


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "orders/list.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        return (
            Order.objects.filter(owner=self.request.user)
            .annotate(item_count=Count("items"))
            .order_by("-placed_at", "-pk")
        )


class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, owner=request.user)
        items = order.items.select_related("product").order_by("pk")
        return render(request, "orders/detail.html", {"order": order, "items": items})
