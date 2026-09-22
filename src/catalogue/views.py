from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, View

from .models import Product


class OperatorPermissionRequiredMixin(PermissionRequiredMixin):
    permission_required = "catalogue.toggle_product_active"
    raise_exception = True


class ProductListView(ListView):
    model = Product
    template_name = "catalogue/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(
            namespace=settings.DEMO_NAMESPACE,
            active=True,
        ).order_by("name", "pk")


class ProductManageListView(OperatorPermissionRequiredMixin, ListView):
    model = Product
    template_name = "catalogue/manage_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(
            namespace=settings.DEMO_NAMESPACE,
        ).order_by("name", "pk")


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