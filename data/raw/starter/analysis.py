"""Starter profile for Ecommerce Sales & Returns Dataset."""
import sqlite3
from pathlib import Path

database = next(Path(".").glob("*.sqlite"))
with sqlite3.connect(database) as connection:
    query = """WITH paid AS (
  SELECT order_id, SUM(amount) AS paid_amount
  FROM payments
  WHERE payment_status = 'succeeded'
  GROUP BY order_id
),
refunded AS (
  SELECT order_id, SUM(amount) AS refunded_amount
  FROM refunds
  GROUP BY order_id
)
SELECT substr(o.ordered_at, 1, 7) AS order_month,
       ROUND(SUM(COALESCE(p.paid_amount, 0) - COALESCE(r.refunded_amount, 0)), 2) AS net_sales
FROM orders o
LEFT JOIN paid p USING (order_id)
LEFT JOIN refunded r USING (order_id)
GROUP BY order_month
ORDER BY order_month;"""
    rows = connection.execute(query).fetchall()
    for row in rows:
        print(row)
