"""Deterministic demo sneaker catalogue and store_operator role; create-only apart from
deactivating retired demo products, safe to re-run."""
import os
import random
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from catalogue.models import Product

DEMO_PRODUCTS = [
    ("Air Jordan 1 High", "Sneakers"),
    ("Air Jordan 1 Low Dior", "Sneakers"),
    ("Classic Brown Sneaker", "Sneakers"),
    ("Converse Chuck High", "Sneakers"),
    ("FILA Chunky Sneaker", "Sneakers"),
    ("New Balance 997", "Sneakers"),
    ("Air Jordan 1 Classic", "Sneakers"),
    ("Nike Air Max 90", "Sneakers"),
    ("RTFKT Creator One", "Sneakers"),
    ("Salomon XT-6", "Sneakers"),
    ("Adidas Yellow & Black Runner", "Sneakers"),
    ("New Balance 574 Classic", "Sneakers"),
]

# Earlier general-goods demo rows used this prefix. They are deactivated, not
# deleted, because carts, orders and reporting rows may still reference them.
RETIRED_EXTERNAL_ID_PREFIX = "demo-"


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Create deterministic demo catalogue products in settings.DEMO_NAMESPACE. Create-only: safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        operator_password = os.environ.get("DEMO_OPERATOR_PASSWORD")
        if not operator_password and not settings.LOCAL:
            raise CommandError(
                "DEMO_OPERATOR_PASSWORD must be set outside local environments; refusing to seed."
            )

        rng = random.Random(options["seed"])
        created = 0
        for index, (name, category) in enumerate(DEMO_PRODUCTS, start=1):
            price = money(rng.uniform(5, 150))
            cost = money(price * Decimal(str(round(rng.uniform(0.4, 0.7), 2))))
            _, was_created = Product.objects.get_or_create(
                namespace=settings.DEMO_NAMESPACE,
                external_id=f"sneaker-{index:03d}",
                defaults={
                    "name": name,
                    "category": category,
                    "price": price,
                    "cost": cost,
                    "stock": rng.randint(0, 200),
                    "lead_time_days": rng.randint(3, 14),
                },
            )
            created += was_created
        self.stdout.write(f"Created {created} demo product(s); {len(DEMO_PRODUCTS) - created} already existed.")
        retired = Product.objects.filter(
            namespace=settings.DEMO_NAMESPACE,
            external_id__startswith=RETIRED_EXTERNAL_ID_PREFIX,
            active=True,
        ).update(active=False)
        if retired:
            self.stdout.write(f"Deactivated {retired} retired demo product(s).")

        group, _ = Group.objects.get_or_create(name="store_operator")
        try:
            permission = Permission.objects.get(codename="toggle_product_active", content_type__app_label="catalogue")
        except Permission.DoesNotExist:
            raise CommandError(
                "catalogue.toggle_product_active permission not found — run 'manage.py migrate' before seed_demo."
            ) from None
        if not group.permissions.filter(pk=permission.pk).exists():
            group.permissions.add(permission)

        User = get_user_model()
        operator, operator_created = User.objects.get_or_create(username="demo-operator")
        if operator_created:
            operator.set_password(operator_password or "Str0ngDemoOperator!2026")
            operator.save()
            operator.groups.add(group)
        elif not operator.groups.filter(pk=group.pk).exists():
            raise CommandError(
                "'demo-operator' already exists and is not a seed-provisioned operator; "
                "refusing to grant privileges."
            )
        self.stdout.write(
            "Created demo-operator account with a fresh password."
            if operator_created
            else "demo-operator already existed; password left unchanged."
        )
