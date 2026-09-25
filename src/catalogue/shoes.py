"""The shoe catalogue: the single definition of every shoe model and size.

Standard library only, so analytics/build_shoe_dataset.py (host Python) and seed_demo (Django) read the
same list. See docs/plans/shoe-sizes-catalogue.md.
"""
from decimal import Decimal

# US men's sizes. SIZE_WEIGHTS is the seeded share of order lines per size (mid sizes sell most).
SIZES = tuple(Decimal(value) for value in ("7", "7.5", "8", "8.5", "9", "9.5", "10", "10.5", "11", "11.5"))
SIZE_WEIGHTS = (3, 6, 10, 13, 15, 15, 13, 11, 8, 6)

# Source dataset category -> shoe category, one to one, so category totals keep their shape.
CATEGORY_MAP = {
    "apparel": "Lifestyle",
    "beauty": "Luxury",
    "electronics": "Running",
    "home": "Classics",
    "office": "Basketball",
    "outdoors": "Trail",
}

# (shoe_id, name, category, list_price, unit_cost, 3D model asset, weight within its category)
SHOES = (
    ("S01", "Air Jordan 1 High", "Basketball", "249.00", "142.00", "models/air-jordan-1-high.glb", 40),
    ("S02", "Air Jordan 1 Classic", "Basketball", "229.00", "131.00", "models/air-jordan-1-classic.glb", 30),
    ("S03", 'Air Jordan 1 High "Bred"', "Basketball", "259.00", "148.00", "models/air-jordan-1-high.glb", 20),
    ("S04", 'Air Jordan 1 Classic "Royal"', "Basketball", "235.00", "134.00", "models/air-jordan-1-classic.glb", 10),
    ("S05", "Nike Air Max 90", "Running", "199.00", "112.00", "models/nike-air-max-90.glb", 40),
    ("S06", "Adidas Yellow & Black Runner", "Running", "169.00", "95.00", "models/adidas-yellow-black.glb", 30),
    ("S07", 'Nike Air Max 90 "Infrared"', "Running", "209.00", "118.00", "models/nike-air-max-90.glb", 20),
    ("S08", 'Adidas Runner "Core Black"', "Running", "175.00", "98.00", "models/adidas-yellow-black.glb", 10),
    ("S09", "New Balance 574 Classic", "Lifestyle", "139.00", "78.00", "models/new-balance-574.glb", 50),
    ("S10", "New Balance 997", "Lifestyle", "219.00", "124.00", "models/new-balance-997.glb", 30),
    ("S11", 'New Balance 574 "Navy"', "Lifestyle", "145.00", "81.00", "models/new-balance-574.glb", 20),
    ("S12", "Converse Chuck High", "Classics", "95.00", "52.00", "models/converse-high.glb", 50),
    ("S13", "Classic Brown Sneaker", "Classics", "119.00", "66.00", "models/brown-sneaker.glb", 30),
    ("S14", "FILA Chunky Sneaker", "Classics", "129.00", "72.00", "models/fila-sneaker.glb", 20),
    ("S15", "Salomon XT-6", "Trail", "265.00", "150.00", "models/salomon-xt6.glb", 50),
    ("S16", 'Salomon XT-6 "Black"', "Trail", "269.00", "152.00", "models/salomon-xt6.glb", 30),
    ("S17", 'Salomon XT-6 "Lunar Grey"', "Trail", "275.00", "156.00", "models/salomon-xt6.glb", 20),
    ("S18", "Air Jordan 1 Low Dior", "Luxury", "2990.00", "1700.00", "models/air-jordan-1-low-dior.glb", 50),
    ("S19", "RTFKT Creator One", "Luxury", "1450.00", "820.00", "models/rtfkt-creator-one.glb", 30),
    ("S20", 'RTFKT Creator One "Genesis"', "Luxury", "1590.00", "900.00", "models/rtfkt-creator-one.glb", 20),
)

MODEL_ASSETS = {name: asset for _, name, _, _, _, asset, _ in SHOES}


def sku(shoe_id, size):
    """SKU external ID: the shoe ID and the size in tenths, for example S05-095 for US 9.5."""
    return f"{shoe_id}-{int(size * 10):03d}"
