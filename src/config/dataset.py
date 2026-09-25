"""CSV acceptance and deterministic mappings, independent of Django/database state."""
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import random
from zoneinfo import ZoneInfo

SGT = ZoneInfo("Asia/Singapore")
CENT = Decimal("0.01")
TABLES = {"customers": "customer_id", "products": "product_id",
          "orders": "order_id", "order_items": "order_item_id"}
STATUS = {"completed": "completed", "cancelled": "cancelled",
          "refunded": "refunded", "partially_refunded": "refunded"}
FIELDS = {
    "customers": "customer_id created_at country_code acquisition_channel customer_segment",
    "products": "product_id sku product_name category list_price",
    "orders": "order_id customer_id ordered_at order_status currency subtotal tax_amount shipping_amount order_total",
    "order_items": "order_item_id order_id product_id quantity unit_price discount_amount line_total",
}


def load_source(path):
    source = {}
    for table in TABLES:
        with (Path(path) / f"{table}.csv").open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames and len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError(f"{table}: duplicate CSV columns")
            if not set(FIELDS[table].split()).issubset(reader.fieldnames or []):
                raise ValueError(f"{table}: missing required columns")
            source[table] = list(reader)
    return source


def decimal(value, maximum="999999999999.99"):
    try:
        number = Decimal(value)
        if not number.is_finite() or number < 0 or number > Decimal(maximum):
            raise ValueError("money must be finite, nonnegative and within precision")
        return number
    except (InvalidOperation, TypeError):
        raise ValueError("invalid money") from None


def unit_money(value):
    return decimal(value, "9999999999.99").quantize(CENT, rounding=ROUND_HALF_UP)


def timestamp(value):
    result = datetime.fromisoformat(value)
    return result.replace(tzinfo=SGT) if result.tzinfo is None else result.astimezone(SGT)


def text(value, length):
    if not isinstance(value, str) or not value.strip() or len(value) > length:
        raise ValueError(f"required text must have 1..{length} characters")
    return value


def shoe_size(row):
    """Optional shoe columns: both empty/absent (a size-less product) or a shoe ID with a half size."""
    shoe_id, size = row.get("shoe_id", ""), row.get("size", "")
    if not shoe_id and not size:
        return {"shoe_id": None, "size": None}
    try:
        number = Decimal(size)
    except InvalidOperation:
        raise ValueError("invalid shoe size") from None
    if not number.is_finite() or not Decimal(1) <= number <= Decimal(20) or number * 2 % 1:
        raise ValueError("shoe size must be a half size from 1 to 20")
    return {"shoe_id": text(shoe_id, 100), "size": number.quantize(Decimal("0.1"))}


def validate(source):
    """Return typed valid rows and auditable rejects; an incomplete order is rejected whole."""
    parsed = {table: {} for table in TABLES}
    rejects = {}

    def reject(table, index, reason):
        entry = rejects.setdefault((table, index), {
            "table": table, "row": index + 2,
            "external_id": source[table][index].get(TABLES[table], ""), "reasons": []})
        if reason not in entry["reasons"]:
            entry["reasons"].append(reason)

    for table, key in TABLES.items():
        counts = Counter(row.get(key) for row in source[table])
        for index, row in enumerate(source[table]):
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("malformed CSV row")
                external_id = text(row[key], 100)
                if counts[external_id] != 1:
                    raise ValueError("duplicate primary ID")
                typed = {"external_id": external_id, "_row": index}
                if table == "customers":
                    typed.update(source_signup_at=timestamp(row["created_at"]),
                                 channel=text(row["acquisition_channel"], 100), country=text(row["country_code"], 100))
                elif table == "products":
                    typed.update(name=text(row["product_name"], 200), category=text(row["category"], 100),
                                 price=unit_money(row["list_price"]),
                                 cost=unit_money(row["unit_cost"]) if row.get("unit_cost", "") else None)
                    typed.update(shoe_size(row))
                elif table == "orders":
                    if row["order_status"] not in STATUS:
                        raise ValueError("unknown order status")
                    typed.update(customer_id=text(row["customer_id"], 100), placed_at=timestamp(row["ordered_at"]),
                                 status=STATUS[row["order_status"]])
                    for field in ("subtotal", "tax_amount", "shipping_amount", "order_total"):
                        typed[field] = decimal(row[field])
                    if typed["subtotal"] + typed["tax_amount"] + typed["shipping_amount"] != typed["order_total"]:
                        raise ValueError("subtotal + tax + shipping != order_total")
                else:
                    quantity = int(row["quantity"])
                    if not 1 <= quantity <= 2147483647:
                        raise ValueError("quantity must be a positive PostgreSQL integer")
                    typed.update(order_id=text(row["order_id"], 100), product_id=text(row["product_id"], 100),
                                 quantity=quantity, unit_price=unit_money(row["unit_price"]),
                                 line_total=decimal(row["line_total"]), discount_amount=decimal(row["discount_amount"]))
                    if typed["unit_price"] * quantity - typed["discount_amount"] != typed["line_total"]:
                        raise ValueError("line total != rounded unit price * quantity - discount")
                parsed[table][external_id] = typed
            except (ValueError, InvalidOperation, OverflowError) as exc:
                reject(table, index, str(exc))

    # Every size of one shoe must agree on name and category, and each size appears once per shoe.
    shoes, sizes = {}, Counter()
    for row in parsed["products"].values():
        if row["shoe_id"] is not None:
            shoes.setdefault(row["shoe_id"], (row["name"], row["category"]))
            sizes[row["shoe_id"], row["size"]] += 1
    for row in parsed["products"].values():
        if row["shoe_id"] is None:
            continue
        if shoes[row["shoe_id"]] != (row["name"], row["category"]):
            reject("products", row["_row"], "shoe name/category differs between sizes")
        if sizes[row["shoe_id"], row["size"]] != 1:
            reject("products", row["_row"], "duplicate shoe size")
    for row in parsed["orders"].values():
        customer = parsed["customers"].get(row["customer_id"])
        if customer is None:
            reject("orders", row["_row"], "missing/rejected customer")
        elif row["placed_at"] < customer["source_signup_at"]:
            reject("orders", row["_row"], "order before customer signup")
    for row in parsed["order_items"].values():
        if row["product_id"] not in parsed["products"]:
            reject("order_items", row["_row"], "missing/rejected product")
        if row["order_id"] not in parsed["orders"]:
            reject("order_items", row["_row"], "missing/rejected order")
    # Every source line participates: invalid or duplicate lines invalidate their parent,
    # preventing allow-rejects from importing a silently truncated order.
    source_lines = defaultdict(list)
    for index, row in enumerate(source["order_items"]):
        source_lines[row.get("order_id")].append(index)
    lines_by_order = defaultdict(list)
    for row in parsed["order_items"].values():
        lines_by_order[row["order_id"]].append(row)
    for external_id, order in parsed["orders"].items():
        indices = source_lines[external_id]
        lines = lines_by_order[external_id]
        if not indices or any(("order_items", i) in rejects for i in indices):
            reject("orders", order["_row"], "missing/rejected order items")
        elif sum((line["line_total"] for line in lines), Decimal(0)) != order["subtotal"]:
            reject("orders", order["_row"], "line net sum != subtotal")
        order["total"] = sum((line["unit_price"] * line["quantity"] for line in lines), Decimal(0))
        if order["total"] > Decimal("999999999999.99"):
            reject("orders", order["_row"], "application total exceeds precision")
    for row in parsed["order_items"].values():
        parent = parsed["orders"].get(row["order_id"])
        if parent is None or ("orders", parent["_row"]) in rejects:
            reject("order_items", row["_row"], "missing/rejected order")
    valid = {table: {key: row for key, row in rows.items() if (table, row["_row"]) not in rejects}
             for table, rows in parsed.items()}
    return valid, [rejects[key] for key in sorted(rejects)]


def prepare(source, valid, seed, anchor=None):
    if not valid["products"] or not valid["orders"]:
        raise ValueError("at least one valid product and order is required")
    latest = max(row["placed_at"] for row in valid["orders"].values())
    source_cutoff = datetime.combine(latest.date() + timedelta(days=1), time.min, SGT)
    cutoff = datetime.combine(date.fromisoformat(anchor), time.min, SGT) if anchor else source_cutoff
    offset = cutoff - source_cutoff
    for table, field in (("customers", "source_signup_at"), ("orders", "placed_at")):
        for row in valid[table].values():
            row[field] += offset
            if row[field] >= cutoff:
                raise ValueError(f"{table} {row['external_id']}: event at/after cutoff")
    recent = Counter()
    for line in valid["order_items"].values():
        order = valid["orders"][line["order_id"]]
        if order["status"] == "completed" and cutoff - timedelta(days=7) <= order["placed_at"] < cutoff:
            recent[line["product_id"]] += line["quantity"]
    for key, row in valid["products"].items():
        rng = random.Random(f"{seed}:{key}")
        row["lead_time_days"] = rng.randint(3, 14)
        factor = rng.randint(2, 20)
        row["stock"] = int((Decimal(recent[key]) * factor / 7).quantize(Decimal(1), rounding=ROUND_HALF_UP)) if recent[key] else rng.randint(20, 200)
        if row["stock"] > 2147483647:
            raise ValueError(f"product {key}: generated stock exceeds PostgreSQL integer")
        if row["cost"] is None:
            row["cost"] = (row["price"] * Decimal("0.60")).quantize(CENT, rounding=ROUND_HALF_UP)
    # Persist the accepted input manifest as a fingerprint in the immutable inventory
    # version identity. This guards original product inputs without comparing live fields.
    accepted = {table: sorted((source[table][r["_row"]] for r in rows.values()), key=lambda r: r[TABLES[table]])
                for table, rows in valid.items()}
    manifest = {"source": accepted, "seed": seed, "offset_days": offset.days, "cutoff": cutoff.isoformat()}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return cutoff, offset.days, "import-v1-" + digest


def username(namespace, external_id):
    identity = json.dumps([namespace, external_id], separators=(",", ":"))
    return "import-" + hashlib.sha256(identity.encode()).hexdigest()
