from django.conf import settings
from django.db import models
from django.db.models import Q

class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    namespace = models.CharField(max_length=160)
    external_id = models.CharField(max_length=100)
    source_signup_at = models.DateTimeField()
    channel = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "external_id"], name="customer_source_unique"),
            models.CheckConstraint(condition=~Q(namespace="") & ~Q(external_id=""), name="customer_identity_nonempty"),
        ]
