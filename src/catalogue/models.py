from django.db import models
from django.db.models import Q

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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "external_id"], name="product_source_unique"),
            models.CheckConstraint(condition=Q(price__gte=0) & Q(price__lte="9999999999.99") & Q(cost__gte=0) & Q(cost__lte="9999999999.99"), name="product_money_nonnegative"),
            models.CheckConstraint(condition=~Q(namespace="") & ~Q(external_id=""), name="product_identity_nonempty"),
        ]
