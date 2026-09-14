"""Deterministic demo catalogue products and store_operator role; create-only, safe to re-run."""
import os
import random
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from catalogue.models import Product

DEMO_PRODUCTS = [
    ("Trail Backpack 30L", "Outdoor"),
    ("Insulated Water Bottle", "Outdoor"),
    ("Camping Lantern", "Outdoor"),
    ("Ceramic Coffee Mug", "Kitchen"),
    ("Nonstick Frying Pan", "Kitchen"),
    ("Electric Kettle", "Kitchen"),
    ("Wireless Earbuds", "Electronics"),
    ("USB-C Charging Cable", "Electronics"),
    ("Portable Bluetooth Speaker", "Electronics"),
    ("Cotton Bath Towel Set", "Home"),
    ("Scented Candle Trio", "Home"),
    ("Throw Blanket", "Home"),
    ("Desk Organizer", "Home"),
    ("Reusable Grocery Bags", "Home"),
]


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Create deterministic demo catalogue products in settings.DEMO_NAMESPACE. Create-only: safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        created = 0
        for index, (name, category) in enumerate(DEMO_PRODUCTS, start=1):
            price = money(rng.uniform(5, 150))
            cost = money(price * Decimal(str(round(rng.uniform(0.4, 0.7), 2))))
            _, was_created = Product.objects.get_or_create(
                namespace=settings.DEMO_NAMESPACE,
                external_id=f"demo-{index:03d}",
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

        group, _ = Group.objects.get_or_create(name="store_operator")
        permission = Permission.objects.get(codename="toggle_product_active", content_type__app_label="catalogue")
        group.permissions.add(permission)

        User = get_user_model()
        operator, operator_created = User.objects.get_or_create(username="demo-operator")
        if operator_created:
            operator.set_password(os.environ.get("DEMO_OPERATOR_PASSWORD", "Str0ngDemoOperator!2026"))
            operator.save()
        operator.groups.add(group)
        self.stdout.write(
            "Created demo-operator account with a fresh password."
            if operator_created
            else "demo-operator already existed; password left unchanged."
        )
