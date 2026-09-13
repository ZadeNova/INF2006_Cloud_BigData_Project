from django.conf import settings
from django.views.generic import ListView

from .models import Product


class ProductListView(ListView):
    model = Product
    template_name = "catalogue/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(
            namespace=settings.DEMO_NAMESPACE, active=True
        ).order_by("name", "pk")
