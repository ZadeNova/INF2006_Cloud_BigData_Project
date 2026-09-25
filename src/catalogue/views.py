from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, View

from .models import Product, ShoeModel


class OperatorPermissionRequiredMixin(PermissionRequiredMixin):
    permission_required = "catalogue.toggle_product_active"
    raise_exception = True


class ProductListView(ListView):
    """One card per shoe model that has an active size; each card lists its active sizes (SKUs)."""
    model = ShoeModel
    template_name = "catalogue/product_list.html"
    context_object_name = "shoes"
    paginate_by = 12

    def get_queryset(self):
        active = Product.objects.filter(namespace=settings.DEMO_NAMESPACE, active=True)
        return (ShoeModel.objects
                .filter(namespace=settings.DEMO_NAMESPACE)
                .filter(Exists(active.filter(shoe_model=OuterRef("pk"))))
                .prefetch_related(Prefetch("skus", queryset=active.order_by("size", "pk"), to_attr="sizes"))
                .order_by("name", "pk"))


class ProductManageListView(OperatorPermissionRequiredMixin, ListView):
    model = Product
    template_name = "catalogue/manage_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(
            namespace=settings.DEMO_NAMESPACE,
        ).order_by("name", "size", "pk")


class ProductToggleActiveView(OperatorPermissionRequiredMixin, View):
    def post(self, request, pk):
        desired = request.POST.get("active")
        if desired not in ("true", "false"):
            return HttpResponseBadRequest("active must be 'true' or 'false'")

        with transaction.atomic():
            product = get_object_or_404(
                Product.objects.select_for_update(),
                pk=pk,
                namespace=settings.DEMO_NAMESPACE,
            )
            product.active = desired == "true"
            product.save(update_fields=["active"])

        return redirect("catalogue:manage_list")