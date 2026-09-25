"""Derived shoe dataset: mapping coverage, exact money identities, importer acceptance and determinism."""
import csv
import importlib.util
from pathlib import Path

import pytest

from catalogue.shoes import CATEGORY_MAP, SHOES, SIZES
from config.dataset import load_source, validate

spec = importlib.util.spec_from_file_location("build_shoe_dataset", Path(__file__).resolve().parents[1] / "build_shoe_dataset.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def raw(tmp_path):
    """Enough source products per category (60) that every shoe receives at least one."""
    source = tmp_path / "raw"
    source.mkdir()
    products = [dict(product_id=f"P{c}{i:02d}", sku=f"SKU{c}{i}", product_name=f"{category} {i}", category=category,
                     unit_cost="4.00", list_price="10.00")
                for c, category in enumerate(CATEGORY_MAP) for i in range(60)]
    items, orders = [], []
    for n, product in enumerate(products):
        order_id = f"O{n:04d}"
        # Source price drifts 3% under list; the discount is 10% of the gross; tax is 8% of the subtotal.
        items.append(dict(order_item_id=f"L{n:04d}a", order_id=order_id, product_id=product["product_id"],
                          quantity="3", unit_price="9.70", discount_amount="2.91", line_total="26.19"))
        items.append(dict(order_item_id=f"L{n:04d}b", order_id=order_id, product_id=products[n - 1]["product_id"],
                          quantity="1", unit_price="10.00", discount_amount="0.00", line_total="10.00"))
        orders.append(dict(order_id=order_id, customer_id="C1", ordered_at="2025-01-02T10:00:00Z", order_status="completed",
                           currency="USD", subtotal="36.19", tax_amount="2.90", shipping_amount="4.99", order_total="44.08"))
    write(source / "customers.csv", [dict(customer_id="C1", created_at="2024-01-01", country_code="SG",
                                          acquisition_channel="organic", customer_segment="consumer")])
    write(source / "products.csv", products)
    write(source / "orders.csv", orders)
    write(source / "order_items.csv", items)
    return source


def test_every_source_product_maps_to_one_shoe_and_the_importer_accepts_the_output(raw, tmp_path):
    output = tmp_path / "shoes"
    build.build(raw, output, 42)

    valid, rejects = validate(load_source(output))
    assert rejects == []
    assert len(valid["products"]) == len(SHOES) * len(SIZES) == 200
    assert (len(valid["orders"]), len(valid["order_items"])) == (360, 720)
    with (output / "product_map.csv").open(encoding="utf-8") as stream:
        mapping = list(csv.DictReader(stream))
    assert len(mapping) == 360 and {row["shoe_id"] for row in mapping} == {shoe[0] for shoe in SHOES}
    shoes = {shoe[0]: shoe for shoe in SHOES}
    assert all(CATEGORY_MAP[row["source_category"]] == shoes[row["shoe_id"]][2] for row in mapping)
    # Money follows the shoe: list price x the source's 0.97 drift, the source discount rate kept.
    first = valid["order_items"]["L0000a"]
    shoe_price = valid["products"][first["product_id"]]["price"]
    assert first["unit_price"] == (shoe_price * build.Decimal("0.97")).quantize(build.CENT, rounding=build.ROUND_HALF_UP)
    assert first["discount_amount"] == (first["unit_price"] * 3 * build.Decimal("0.1")).quantize(build.CENT, rounding=build.ROUND_HALF_UP)


def test_regeneration_is_byte_identical_and_raw_is_unchanged(raw, tmp_path):
    before = {path.name: path.read_bytes() for path in raw.iterdir()}
    first = build.build(raw, tmp_path / "a", 42)
    second = build.build(raw, tmp_path / "b", 42)
    assert first == second
    assert {path.name: path.read_bytes() for path in raw.iterdir()} == before
    assert b"\r\n" not in (tmp_path / "a" / "order_items.csv").read_bytes()
