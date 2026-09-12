import uuid
from django.db import models
from django.db.models import Q

class InventoryVersion(models.Model):
    namespace = models.CharField(max_length=160)
    version = models.CharField(max_length=100)
    sealed = models.BooleanField(default=False)
    cutoff = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "version"], name="inventory_version_unique"),
            models.CheckConstraint(condition=~Q(namespace="") & ~Q(version=""), name="inventory_identity_nonempty"),
        ]

class InventorySnapshot(models.Model):
    inventory = models.ForeignKey(InventoryVersion, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey("catalogue.Product", on_delete=models.PROTECT)
    stock = models.PositiveIntegerField()
    lead_time_days = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["inventory", "product"], name="snapshot_product_unique")]

class AnalyticsRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory = models.ForeignKey(InventoryVersion, on_delete=models.PROTECT)
    window_start = models.DateTimeField()
    cutoff = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    processed_count = models.PositiveIntegerField(default=0)
    summary_version = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(cutoff__gt=models.F("window_start")), name="analytics_window_valid"),
            models.CheckConstraint(condition=Q(status__in=["running", "completed", "failed"]), name="analytics_status_valid"),
            models.CheckConstraint(condition=(Q(status="running") & Q(finished_at__isnull=True)) | (Q(status__in=["completed", "failed"]) & Q(finished_at__isnull=False)), name="analytics_finish_valid"),
        ]

class DailyProductSales(models.Model):
    run = models.ForeignKey(AnalyticsRun, on_delete=models.CASCADE, related_name="daily_sales")
    business_date = models.DateField()
    product = models.ForeignKey("catalogue.Product", on_delete=models.PROTECT)
    units = models.PositiveBigIntegerField()
    sales_amount = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "business_date", "product"], name="daily_run_product_unique"),
            models.CheckConstraint(condition=Q(sales_amount__gte=0) & Q(sales_amount__lte="9999999999999999.99"), name="daily_sales_nonnegative"),
        ]
