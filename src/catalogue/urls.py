from django.urls import path

from .views import ProductListView

app_name = "catalogue"

urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
]
