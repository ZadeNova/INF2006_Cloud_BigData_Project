from django.conf import settings
from django.db import models
from django.db.models import Q

MAX_QUANTITY = 999

class Cart(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalogue.Product", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    @property
    def line_total(self):
        return self.quantity * self.product.price

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="cart_product_unique"),
            models.CheckConstraint(
                condition=Q(quantity__gte=1) & Q(quantity__lte=MAX_QUANTITY), name="cart_quantity_bounds"
            ),
        ]
