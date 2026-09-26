from django.urls import path

from .views import ProductDetailView, ProductListView, ProductManageListView, ProductToggleActiveView

app_name = "catalogue"

urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
    path("<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("manage/", ProductManageListView.as_view(), name="manage_list"),
    path("manage/<int:pk>/toggle-active/", ProductToggleActiveView.as_view(), name="product_toggle_active"),

]
