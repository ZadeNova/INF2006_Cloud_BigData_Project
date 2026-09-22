from django.db import migrations

# One row per completed order line. This view is the only place that holds the "completed only"
# rule and the Singapore business-date conversion (docs/ANALYTICS.md, "Aggregation is SQL").
# placed_at is exposed so a reader can bound the scan with an indexable range on the raw column
# (order_reporting_window); business_date is computed and cannot use that index by itself.
CREATE_VIEW = """
CREATE VIEW reporting_completed_sale_lines AS
SELECT o.namespace AS namespace,
       o.id AS order_id,
       o.placed_at AS placed_at,
       i.product_id AS product_id,
       i.quantity AS quantity,
       i.unit_price AS unit_price,
       i.quantity * i.unit_price AS line_total,
       (o.placed_at AT TIME ZONE 'Asia/Singapore')::date AS business_date
FROM orders_order o
JOIN orders_orderitem i ON i.order_id = o.id
WHERE o.status = 'completed';
"""


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0001_initial"),
        ("reporting", "0002_inventory_guards"),
    ]

    operations = [
        migrations.RunSQL(CREATE_VIEW, reverse_sql="DROP VIEW reporting_completed_sale_lines;"),
    ]
