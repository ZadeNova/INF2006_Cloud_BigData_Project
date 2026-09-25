"""Deterministic demo shoe catalogue (every model in every size) and store_operator role; create-only apart
from deactivating retired demo products, safe to re-run."""
import os
import random
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from catalogue.models import Product, ShoeModel
from catalogue.shoes import SHOES, SIZES, sku

# Earlier demo rows used these prefixes: general goods ("demo-") and one size-less row per sneaker
# ("sneaker-"). They are deactivated, not deleted, because carts, orders and reporting rows may still
# reference them.
RETIRED_EXTERNAL_ID_PREFIXES = ("demo-", "sneaker-")


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Create deterministic demo catalogue products in settings.DEMO_NAMESPACE. Create-only: safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--no-products", action="store_true", help="Create the operator without demo products")

    def handle(self, *args, **options):
        operator_password = os.environ.get("DEMO_OPERATOR_PASSWORD")
        if not operator_password and not settings.LOCAL:
            raise CommandError(
                "DEMO_OPERATOR_PASSWORD must be set outside local environments; refusing to seed."
            )

        rng = random.Random(options["seed"])
        created = 0
        shoes = [] if options["no_products"] else SHOES
        for shoe_id, name, category, price, cost, _, _ in shoes:
            model, _ = ShoeModel.objects.get_or_create(
                namespace=settings.DEMO_NAMESPACE, external_id=shoe_id,
                defaults={"name": name, "category": category})
            for size in SIZES:
                _, was_created = Product.objects.get_or_create(
                    namespace=settings.DEMO_NAMESPACE,
                    external_id=sku(shoe_id, size),
                    defaults={
                        "name": name,
                        "category": category,
                        "price": money(price),
                        "cost": money(cost),
                        "stock": rng.randint(0, 40),
                        "lead_time_days": rng.randint(3, 14),
                        "shoe_model": model,
                        "size": size,
                    },
                )
                created += was_created
        total = len(shoes) * len(SIZES)
        self.stdout.write(f"Created {created} demo product(s); {total - created} already existed.")
        retired = 0
        for prefix in RETIRED_EXTERNAL_ID_PREFIXES:
            retired += Product.objects.filter(
                namespace=settings.DEMO_NAMESPACE,
                external_id__startswith=prefix,
                active=True,
            ).update(active=False)
        if retired:
            self.stdout.write(f"Deactivated {retired} retired demo product(s).")

        group, _ = Group.objects.get_or_create(name="store_operator")
        for app_label, codename in [("catalogue", "toggle_product_active"), ("reporting", "view_analytics")]:
            try:
                permission = Permission.objects.get(codename=codename, content_type__app_label=app_label)
            except Permission.DoesNotExist:
                raise CommandError(
                    f"{app_label}.{codename} permission not found — run 'manage.py migrate' before seed_demo."
                ) from None
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
