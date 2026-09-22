-- Ecommerce Sales & Returns Dataset starter queries
-- Checked against the v1.0.0 SQLite release.
-- Question: What was monthly net sales after successful payments and refunds?
WITH paid AS (
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
ORDER BY order_month;

-- Basic exploration:
SELECT COUNT(*) AS row_count
FROM customers;

SELECT *
FROM customers
LIMIT 20;
