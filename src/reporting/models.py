import uuid
from django.conf import settings
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
        permissions = [("view_analytics", "Can view sales and inventory analytics")]
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


class CustomerSegment(models.Model):
    run = models.ForeignKey(AnalyticsRun, on_delete=models.CASCADE, related_name="customer_segments")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    model_version = models.CharField(max_length=100)
    cluster_id = models.PositiveSmallIntegerField()
    segment_label = models.CharField(max_length=40)
    recency_days = models.PositiveIntegerField()
    frequency_orders = models.PositiveIntegerField()
    monetary_total = models.DecimalField(max_digits=18, decimal_places=2)
    k_clusters = models.PositiveSmallIntegerField()
    silhouette_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "customer", "model_version"], name="segment_run_customer_version_unique"),
            models.CheckConstraint(condition=~Q(model_version=""), name="segment_model_version_nonempty"),
            models.CheckConstraint(condition=~Q(segment_label=""), name="segment_label_nonempty"),
            models.CheckConstraint(condition=Q(cluster_id__gte=0), name="segment_cluster_id_nonnegative"),
            models.CheckConstraint(condition=Q(k_clusters__gte=2), name="segment_k_clusters_min"),
            models.CheckConstraint(condition=Q(monetary_total__gte=0) & Q(monetary_total__lte="9999999999999999.99"),
                                   name="segment_monetary_nonnegative"),
            models.CheckConstraint(
                condition=Q(
                    Q(silhouette_score__isnull=True),
                    Q(("silhouette_score__gte", -1), ("silhouette_score__lte", 1), _connector="AND"),
                    _connector="OR",
                ),
                name="segment_silhouette_range"),
        ]
        indexes = [
            models.Index(fields=["run", "model_version"], name="segment_run_model_idx"),
            models.Index(fields=["run", "segment_label"], name="segment_run_label_idx"),
        ]
