from django.urls import path

from .views import CartAddView, CartDeleteView, CartDetailView, CartUpdateView

app_name = "cart"

urlpatterns = [
    path("", CartDetailView.as_view(), name="detail"),
    path("items/", CartAddView.as_view(), name="add"),
    path("items/<int:pk>/update/", CartUpdateView.as_view(), name="update"),
    path("items/<int:pk>/delete/", CartDeleteView.as_view(), name="delete"),
]
