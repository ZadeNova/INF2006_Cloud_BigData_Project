from django.conf import settings
from django.db import models
from django.db.models import Q

class Order(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed"
        CANCELLED = "cancelled"
        REFUNDED = "refunded"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    namespace = models.CharField(max_length=160)
    external_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    placed_at = models.DateTimeField()
    idempotency_key = models.UUIDField(null=True, blank=True)
    request_fingerprint = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["owner", "-placed_at"], name="order_owner_date"),
                   models.Index(fields=["namespace", "status", "placed_at"], name="order_reporting_window")]
        constraints = [
            models.UniqueConstraint(fields=["namespace", "external_id"], name="order_source_unique"),
            models.UniqueConstraint(fields=["owner", "idempotency_key"], name="order_owner_key_unique"),
            models.CheckConstraint(condition=Q(total__gte=0) & Q(total__lte="999999999999.99"), name="order_total_nonnegative"),
            models.CheckConstraint(condition=Q(status__in=["completed", "cancelled", "refunded"]), name="order_status_valid"),
            models.CheckConstraint(condition=~Q(namespace=""), name="order_namespace_nonempty"),
            models.CheckConstraint(condition=(Q(external_id__isnull=False) & ~Q(external_id="") & Q(idempotency_key__isnull=True) & Q(request_fingerprint="")) | (Q(external_id__isnull=True) & Q(idempotency_key__isnull=False) & Q(request_fingerprint__regex=r"^[0-9a-f]{64}$") & Q(status="completed")), name="order_origin_valid"),
        ]

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey("catalogue.Product", on_delete=models.PROTECT)
    external_id = models.CharField(max_length=100, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="order_item_quantity_positive"),
            models.CheckConstraint(condition=Q(external_id__isnull=True) | ~Q(external_id=""), name="order_item_source_nonempty"),
            models.CheckConstraint(condition=Q(unit_price__gte=0) & Q(unit_price__lte="9999999999.99"), name="order_item_price_nonnegative"),
            models.UniqueConstraint(fields=["order", "external_id"], name="order_item_source_unique"),
        ]
