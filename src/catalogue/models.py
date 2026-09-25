from decimal import Decimal

from django.db import models
from django.db.models import Q

from .shoes import MODEL_ASSETS

LOW_STOCK_THRESHOLD = 10

# Static 3D model per shoe name, from the shoe catalogue (colourways reuse their base model).
PRODUCT_MODELS = MODEL_ASSETS
# Database bounds for a size; the importer and seed_demo only use half sizes from shoes.SIZES.
SIZE_MIN, SIZE_MAX = Decimal("1.0"), Decimal("20.0")


class ShoeModel(models.Model):
    """One shoe style. Its sizes are Product rows (SKUs) that share its name and category."""
    namespace = models.CharField(max_length=160)
    external_id = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)

    @property
    def model_asset(self):
        return PRODUCT_MODELS.get(self.name)

    # The properties below read `sizes`, the active SKUs the catalogue view prefetches.
    @property
    def price(self):
        return self.sizes[0].price if self.sizes else None

    @property
    def display_price(self):
        return self.sizes[0].display_price if self.sizes else ""

    @property
    def sizes_in_stock(self):
        return sum(sku.stock > 0 for sku in self.sizes)

    @property
    def stock_status(self):
        """out-of-stock when no size has stock, low-stock when some sizes are out or low, else in-stock."""
        if not self.sizes_in_stock:
            return "out-of-stock"
        if any(sku.stock_status != "in-stock" for sku in self.sizes):
            return "low-stock"
        return "in-stock"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "external_id"], name="shoe_model_source_unique"),
            models.CheckConstraint(condition=~Q(namespace="") & ~Q(external_id=""), name="shoe_model_identity_nonempty"),
        ]


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
    # A product is one size of a shoe model (a SKU). Both are null only for legacy rows imported without sizes.
    shoe_model = models.ForeignKey(ShoeModel, on_delete=models.PROTECT, null=True, blank=True, related_name="skus")
    size = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

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
    def size_label(self):
        return f"US {self.size.normalize():f}" if self.size is not None else ""

    @property
    def display_name(self):
        return f"{self.name} · {self.size_label}" if self.size is not None else self.name

    @property
    def display_price(self):
        return f"S${self.price}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "external_id"], name="product_source_unique"),
            models.CheckConstraint(condition=Q(price__gte=0) & Q(price__lte="9999999999.99") & Q(cost__gte=0) & Q(cost__lte="9999999999.99"), name="product_money_nonnegative"),
            models.CheckConstraint(condition=~Q(namespace="") & ~Q(external_id=""), name="product_identity_nonempty"),
            models.CheckConstraint(condition=Q(shoe_model__isnull=True, size__isnull=True)
                                   | Q(shoe_model__isnull=False, size__isnull=False), name="product_size_pair"),
            models.CheckConstraint(condition=Q(size__isnull=True) | (Q(size__gte=SIZE_MIN) & Q(size__lte=SIZE_MAX)),
                                   name="product_size_range"),
            models.UniqueConstraint(fields=["shoe_model", "size"], name="product_model_size_unique"),
        ]
        permissions = [("toggle_product_active", "Can activate or deactivate catalogue products")]
