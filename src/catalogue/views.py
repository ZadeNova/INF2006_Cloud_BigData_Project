from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.http import HttpResponseBadRequest, QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, ListView, View

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


class ProductDetailView(DetailView):
    model = ShoeModel
    template_name = "catalogue/product_detail.html"
    context_object_name = "shoe"

    def get_queryset(self):
        active = Product.objects.filter(namespace=settings.DEMO_NAMESPACE, active=True)
        return (ShoeModel.objects
                .filter(namespace=settings.DEMO_NAMESPACE)
                .filter(Exists(active.filter(shoe_model=OuterRef("pk"))))
                .prefetch_related(Prefetch("skus", queryset=active.order_by("size", "pk"), to_attr="sizes")))


STATUS_CHOICES = (("all", "All"), ("active", "Active"), ("inactive", "Inactive"))


class ProductManageListView(OperatorPermissionRequiredMixin, ListView):
    model = Product
    template_name = "catalogue/manage_list.html"
    context_object_name = "products"
    paginate_by = 12

    def _base_queryset(self):
        return Product.objects.filter(namespace=settings.DEMO_NAMESPACE)

    def _categories(self):
        return list(self._base_queryset().order_by("category").values_list("category", flat=True).distinct())

    def _filters(self):
        """Cleaned filters; unknown status or category values fall back to "all"."""
        if not hasattr(self, "_cleaned_filters"):
            status = self.request.GET.get("status", "all")
            category = self.request.GET.get("category", "all")
            self._cleaned_filters = {
                "q": self.request.GET.get("q", "").strip(),
                "category": category if category in self._categories() else "all",
                "status": status if status in dict(STATUS_CHOICES) else "all",
            }
        return self._cleaned_filters

    def _query(self, **changes):
        """Query string for the current filters with some replaced; defaults are left out."""
        values = {**self._filters(), **changes}
        query = QueryDict(mutable=True)
        for key in ("q", "category", "status"):
            if values[key] not in ("", "all"):
                query[key] = values[key]
        return query.urlencode()

    def paginate_queryset(self, queryset, page_size):
        # Clamp to the last page: toggling can shrink a filtered list under the page being viewed.
        paginator = self.get_paginator(queryset, page_size)
        page = paginator.get_page(self.request.GET.get("page"))
        return paginator, page, page.object_list, page.has_other_pages()

    def get_queryset(self):
        filters = self._filters()
        queryset = self._base_queryset()
        if filters["status"] != "all":
            queryset = queryset.filter(active=filters["status"] == "active")
        if filters["category"] != "all":
            queryset = queryset.filter(category=filters["category"])
        if filters["q"]:
            queryset = queryset.filter(name__icontains=filters["q"])
        return queryset.order_by("name", "size", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = self._filters()
        context["filters"] = filters
        context["filter_query"] = self._query()
        context["status_chips"] = [
            {"label": label, "query": self._query(status=value), "selected": filters["status"] == value}
            for value, label in STATUS_CHOICES]
        context["category_chips"] = [
            {"label": label, "query": self._query(category=value), "selected": filters["category"] == value}
            for value, label in [("all", "All"), *[(name, name) for name in self._categories()]]]
        context["filtered"] = any(filters[key] not in ("", "all") for key in filters)
        return context


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

        # Return to the operator's filtered page, but only ever within the manage list.
        target = request.POST.get("next", "")
        if (target.startswith(reverse("catalogue:manage_list"))
                and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()})):
            return redirect(target)
        return redirect("catalogue:manage_list")
