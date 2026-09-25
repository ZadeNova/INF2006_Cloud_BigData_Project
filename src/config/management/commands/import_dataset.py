"""Create-only historical import, with a sealed input fingerprint and inventory."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction, IntegrityError

from accounts.models import CustomerProfile
from catalogue.models import Product, ShoeModel
from config import dataset
from orders.models import Order, OrderItem
from reporting.models import InventorySnapshot, InventoryVersion


def conflict(message):
    raise CommandError(f"Import conflict: {message}; no database changes committed.")


def verify(instance, values, label):
    for field, expected in values.items():
        if getattr(instance, field) != expected:
            conflict(f"{label}: {field} differs")


class Command(BaseCommand):
    help = "Import local CSV history atomically. One accepted input manifest per namespace; replay is create-only."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, type=Path)
        parser.add_argument("--namespace", required=True)
        parser.add_argument("--shift-anchor", help="Exclusive Singapore midnight cutoff YYYY-MM-DD")
        parser.add_argument("--allow-rejects", action="store_true")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--rejects-file", type=Path, help="Audit JSON destination (default: temporary directory, content-addressed)")

    def handle(self, *args, **options):
        namespace = options["namespace"]
        try:
            dataset.text(namespace, 160)
            source = dataset.load_source(options["source"])
            valid, rejects = dataset.validate(source)
            for table in dataset.TABLES:
                self.stdout.write(f"{table}: read={len(source[table])} valid={len(valid[table])} rejected={sum(r['table'] == table for r in rejects)}")
            if rejects:
                audit = json.dumps({"namespace": namespace, "rejects": rejects}, indent=2, sort_keys=True) + "\n"
                digest = hashlib.sha256(audit.encode()).hexdigest()
                path = options["rejects_file"] or Path(tempfile.gettempdir()) / f"import-rejects-{digest}.json"
                resolved = path.resolve()
                source_path = options["source"].resolve()
                if resolved == source_path or source_path in resolved.parents:
                    raise ValueError("rejects file must be outside the source directory")
                path.write_text(audit, encoding="utf-8")
                self.stdout.write(f"Reject audit: {path}; reasons: {dict(Counter(reason for row in rejects for reason in row['reasons']))}")
                for row in rejects:
                    self.stdout.write(json.dumps(row, sort_keys=True))
                if not options["allow_rejects"]:
                    raise CommandError("Rejected rows exist; no database writes. Inspect audit or explicitly use --allow-rejects.")
            cutoff, offset, version = dataset.prepare(source, valid, options["seed"], options["shift_anchor"])
            self.stdout.write(f"cutoff={cutoff.isoformat()} offset_days={offset} inventory={version}")
            result = self.persist(namespace, valid, cutoff, version)
        except (ValueError, OSError, OverflowError) as exc:
            raise CommandError(str(exc)) from exc
        except IntegrityError as exc:
            raise CommandError("Import database constraint conflict; transaction rolled back.") from exc
        for table, (created, unchanged) in result.items():
            self.stdout.write(f"{table}: created={created} unchanged={unchanged}")
        for status in sorted(set(dataset.STATUS.values())):
            rows = [r for r in valid["orders"].values() if r["status"] == status]
            self.stdout.write(f"{status}: orders={len(rows)} source_total={sum(r['order_total'] for r in rows):.2f} "
                              f"net_lines={sum(r['subtotal'] for r in rows):.2f} application_lines={sum(r['total'] for r in rows):.2f}")

    @transaction.atomic
    def persist(self, namespace, data, cutoff, version):
        # Serialize importers for one namespace. Checkout does not need this lock:
        # import only reads its historical records and never mutates live products.
        lock = int.from_bytes(hashlib.sha256(namespace.encode()).digest()[:8], "big", signed=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock])
        inventories = list(InventoryVersion.objects.filter(namespace=namespace, version__startswith="import-v1-"))
        replay = bool(inventories)
        if replay and (len(inventories) != 1 or inventories[0].version != version or not inventories[0].sealed):
            conflict("accepted source manifest, seed, dates or inventory seal differs; use a new namespace for revisions")
        products = {p.external_id: p for p in Product.objects.filter(namespace=namespace)}
        if products.keys() - data["products"].keys():
            conflict("namespace contains products outside the accepted source; use an empty product namespace and seed_demo --no-products")
        result = {}
        User = get_user_model()
        profiles = {r.external_id: r for r in CustomerProfile.objects.filter(namespace=namespace).select_related("user")}
        names = {key: dataset.username(namespace, key) for key in data["customers"]}
        users = {u.username: u for u in User.objects.filter(username__in=names.values())}
        new_users = []
        for key, row in data["customers"].items():
            if key in profiles:
                if not replay:
                    conflict(f"customer {key} exists without accepted manifest")
                verify(profiles[key].user, {"username": names[key]}, f"customer {key} identity")
                verify(profiles[key], {field: row[field] for field in ("source_signup_at", "channel", "country")}, f"customer {key}")
            else:
                if replay or names[key] in users:
                    conflict(f"customer {key}: missing profile or username already owned")
                user = User(username=names[key], date_joined=row["source_signup_at"])
                user.set_unusable_password()
                new_users.append(user)
        User.objects.bulk_create(new_users, batch_size=1000)
        users.update({u.username: u for u in new_users})
        new_profiles = [CustomerProfile(namespace=namespace, external_id=key, user=users[names[key]],
                                       **{f: row[f] for f in ("source_signup_at", "channel", "country")})
                        for key, row in data["customers"].items() if key not in profiles]
        CustomerProfile.objects.bulk_create(new_profiles, batch_size=1000)
        profiles.update({p.external_id: p for p in new_profiles})
        result["users"] = (len(new_users), len(names) - len(new_users))
        result["customer_profiles"] = (len(new_profiles), len(names) - len(new_profiles))

        # Shoe models come first: each is the distinct shoe_id of its sized product rows.
        models = {m.external_id: m for m in ShoeModel.objects.filter(namespace=namespace)}
        wanted = {row["shoe_id"]: (row["name"], row["category"]) for row in data["products"].values() if row["shoe_id"]}
        if models.keys() - wanted.keys():
            conflict("namespace contains shoe models outside the accepted source")
        new_models = []
        for key, (name, category) in wanted.items():
            if key in models:
                if not replay:
                    conflict(f"shoe model {key} exists without accepted manifest")
                verify(models[key], {"name": name, "category": category}, f"shoe model {key}")
            else:
                if replay:
                    conflict(f"shoe model {key} missing on replay")
                new_models.append(ShoeModel(namespace=namespace, external_id=key, name=name, category=category))
        ShoeModel.objects.bulk_create(new_models, batch_size=1000)
        models.update({m.external_id: m for m in new_models})
        result["shoe_models"] = (len(new_models), len(wanted) - len(new_models))

        new_products = []
        for key, row in data["products"].items():
            shoe = models[row["shoe_id"]] if row["shoe_id"] else None
            if key in products:
                if not replay:
                    conflict(f"product {key} exists without accepted manifest")
                verify(products[key], {"category": row["category"], "size": row["size"],
                                       "shoe_model_id": shoe.pk if shoe else None}, f"product {key}")
            else:
                if replay:
                    conflict(f"product {key} missing on replay")
                new_products.append(Product(namespace=namespace, external_id=key, shoe_model=shoe, size=row["size"],
                                            **{f: row[f] for f in ("name", "category", "price", "cost", "stock", "lead_time_days")}))
        Product.objects.bulk_create(new_products, batch_size=1000)
        products.update({p.external_id: p for p in new_products})
        result["products"] = (len(new_products), len(data["products"]) - len(new_products))
        orders = {o.external_id: o for o in Order.objects.filter(namespace=namespace, external_id__isnull=False)}
        new_orders = []
        for key, row in data["orders"].items():
            values = {f: row[f] for f in ("status", "total", "placed_at")}
            values.update(owner_id=profiles[row["customer_id"]].user_id, idempotency_key=None, request_fingerprint="")
            if key in orders:
                if not replay:
                    conflict(f"order {key} exists without accepted manifest")
                verify(orders[key], values, f"order {key}")
            else:
                if replay:
                    conflict(f"order {key} missing on replay")
                new_orders.append(Order(namespace=namespace, external_id=key, **values))
        Order.objects.bulk_create(new_orders, batch_size=1000)
        orders.update({o.external_id: o for o in new_orders})
        result["orders"] = (len(new_orders), len(data["orders"]) - len(new_orders))
        existing_items = {(r.order_id, r.external_id): r for r in OrderItem.objects.filter(order__namespace=namespace, order__external_id__isnull=False)}
        expected_keys = set()
        new_items = []
        for key, row in data["order_items"].items():
            pair = (orders[row["order_id"]].pk, key)
            expected_keys.add(pair)
            values = {"product_id": products[row["product_id"]].pk, "quantity": row["quantity"], "unit_price": row["unit_price"]}
            if pair in existing_items:
                verify(existing_items[pair], values, f"order item {key}")
            else:
                if replay:
                    conflict(f"order item {key} missing on replay")
                new_items.append(OrderItem(order_id=pair[0], external_id=key, **values))
        if set(existing_items) - expected_keys:
            conflict("unexpected historical order items")
        OrderItem.objects.bulk_create(new_items, batch_size=1000)
        result["order_items"] = (len(new_items), len(expected_keys) - len(new_items))
        expected = {products[key].pk: (r["stock"], r["lead_time_days"]) for key, r in data["products"].items()}
        if replay:
            inventory = inventories[0]
            verify(inventory, {"cutoff": cutoff}, "inventory")
            actual = {r.product_id: (r.stock, r.lead_time_days) for r in inventory.items.all()}
            if actual != expected:
                conflict("sealed inventory differs from expected generated values")
        else:
            inventory = InventoryVersion.objects.create(namespace=namespace, version=version, cutoff=cutoff)
            InventorySnapshot.objects.bulk_create([
                InventorySnapshot(inventory=inventory, product_id=key, stock=stock, lead_time_days=lead)
                for key, (stock, lead) in expected.items()], batch_size=1000)
            if inventory.items.count() != len(expected):
                conflict("incomplete inventory")
            inventory.sealed = True
            inventory.save(update_fields=["sealed"])
        result["inventory_versions"] = (0, 1) if replay else (1, 0)
        result["inventory_snapshots"] = (0, len(expected)) if replay else (len(expected), 0)
        return result
