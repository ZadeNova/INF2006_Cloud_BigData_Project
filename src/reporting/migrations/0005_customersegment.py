import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0004_analyticsrun_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerSegment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_version", models.CharField(max_length=100)),
                ("cluster_id", models.PositiveSmallIntegerField()),
                ("segment_label", models.CharField(max_length=40)),
                ("recency_days", models.PositiveIntegerField()),
                ("frequency_orders", models.PositiveIntegerField()),
                ("monetary_total", models.DecimalField(decimal_places=2, max_digits=18)),
                ("k_clusters", models.PositiveSmallIntegerField()),
                ("silhouette_score", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_segments",
                                          to="reporting.analyticsrun")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["run", "model_version"], name="segment_run_model_idx"),
                    models.Index(fields=["run", "segment_label"], name="segment_run_label_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("run", "customer", "model_version"),
                                            name="segment_run_customer_version_unique"),
                    models.CheckConstraint(condition=models.Q(("model_version", ""), _negated=True),
                                           name="segment_model_version_nonempty"),
                    models.CheckConstraint(condition=models.Q(("segment_label", ""), _negated=True),
                                           name="segment_label_nonempty"),
                    models.CheckConstraint(condition=models.Q(("cluster_id__gte", 0)),
                                           name="segment_cluster_id_nonnegative"),
                    models.CheckConstraint(condition=models.Q(("k_clusters__gte", 2)),
                                           name="segment_k_clusters_min"),
                    models.CheckConstraint(
                        condition=models.Q(("monetary_total__gte", 0), ("monetary_total__lte", "9999999999999999.99")),
                        name="segment_monetary_nonnegative"),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("silhouette_score__isnull", True)),
                            models.Q(("silhouette_score__gte", -1), ("silhouette_score__lte", 1), _connector="AND"),
                            _connector="OR"),
                        name="segment_silhouette_range"),
                ],
            },
        ),
    ]
