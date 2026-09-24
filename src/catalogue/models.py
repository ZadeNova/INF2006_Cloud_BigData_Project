from django.db import models
from django.db.models import Q

LOW_STOCK_THRESHOLD = 10

# Trial: static 3D models for selected products, keyed by product name.
PRODUCT_MODELS = {
    "Air Jordan 1 High": "models/air-jordan-1-high.glb",
    "Air Jordan 1 Low Dior": "models/air-jordan-1-low-dior.glb",
    "Classic Brown Sneaker": "models/brown-sneaker.glb",
    "Converse Chuck High": "models/converse-high.glb",
    "FILA Chunky Sneaker": "models/fila-sneaker.glb",
    "New Balance 997": "models/new-balance-997.glb",
    "Air Jordan 1 Classic": "models/air-jordan-1-classic.glb",
    "Nike Air Max 90": "models/nike-air-max-90.glb",
    "RTFKT Creator One": "models/rtfkt-creator-one.glb",
    "Salomon XT-6": "models/salomon-xt6.glb",
    "Adidas Yellow & Black Runner": "models/adidas-yellow-black.glb",
    "New Balance 574 Classic": "models/new-balance-574.glb",
}

class Product(models.Model):
    namespace = models.CharField(max_length=160)
    external_id = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField()
    lead_time_days = models.PositiveIntegerField()
    active = models.BooleanField(default=True)

    @property
    def stock_status(self):
        if self.stock == 0:
            return "out-of-stock"
        if self.stock <= LOW_STOCK_THRESHOLD:
            return "low-stock"
        return "in-stock"

    @property
    def model_asset(self):
        return PRODUCT_MODELS.get(self.name)

    @property
    def display_price(self):
        return f"S${self.price}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "external_id"], name="product_source_unique"),
            models.CheckConstraint(condition=Q(price__gte=0) & Q(price__lte="9999999999.99") & Q(cost__gte=0) & Q(cost__lte="9999999999.99"), name="product_money_nonnegative"),
            models.CheckConstraint(condition=~Q(namespace="") & ~Q(external_id=""), name="product_identity_nonempty"),
        ]
        permissions = [("toggle_product_active", "Can activate or deactivate catalogue products")]
