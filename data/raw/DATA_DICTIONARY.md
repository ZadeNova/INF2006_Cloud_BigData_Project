# Ecommerce Sales & Returns Dataset data dictionary

Version: 1.0.0  
Coverage: 2023-01-01 through 2025-12-31  
Source type: synthetic

## `customers`

Grain: One row per customer.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `customer_id` | text | no | Stable customer key. |
| `created_at` | date | no | Customer registration date. |
| `country_code` | text | no | ISO-like market code. |
| `acquisition_channel` | text | no | First-touch acquisition channel. |
| `customer_segment` | text | no | Consumer, small_business, or enterprise. |

## `products`

Grain: One row per product.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `product_id` | text | no | Stable product key. |
| `sku` | text | no | Unique stock keeping unit. |
| `product_name` | text | no | Display name. |
| `category` | text | no | Merchandising category. |
| `unit_cost` | decimal | no | Standard cost in USD. |
| `list_price` | decimal | no | List price in USD. |

## `orders`

Grain: One row per placed order.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `order_id` | text | no | Stable order key. |
| `customer_id` | text | no | Ordering customer. |
| `ordered_at` | datetime | no | UTC order timestamp. |
| `order_status` | text | no | completed, partially_refunded, refunded, or cancelled. |
| `currency` | text | no | Transaction currency; USD in v1. |
| `subtotal` | decimal | no | Sum of line net amounts. |
| `tax_amount` | decimal | no | Calculated sales tax. |
| `shipping_amount` | decimal | no | Shipping charge. |
| `order_total` | decimal | no | Subtotal plus tax and shipping. |

## `order_items`

Grain: One row per order line.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `order_item_id` | text | no | Stable line key. |
| `order_id` | text | no | Parent order. |
| `product_id` | text | no | Purchased product. |
| `quantity` | integer | no | Units purchased. |
| `unit_price` | decimal | no | Price per unit at purchase. |
| `discount_amount` | decimal | no | Line discount in USD. |
| `line_total` | decimal | no | Quantity times unit price less discount. |

## `payments`

Grain: One row per payment attempt.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `payment_id` | text | no | Stable payment key. |
| `order_id` | text | no | Order being paid. |
| `paid_at` | datetime | no | UTC payment attempt timestamp. |
| `payment_method` | text | no | card, paypal, or bank_transfer. |
| `payment_status` | text | no | succeeded or failed. |
| `amount` | decimal | no | Attempted amount in USD. |

## `refunds`

Grain: One row per refund event.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `refund_id` | text | no | Stable refund key. |
| `payment_id` | text | no | Refunded successful payment. |
| `order_id` | text | no | Refunded order. |
| `refunded_at` | datetime | no | UTC refund timestamp. |
| `refund_reason` | text | no | Customer-facing reason category. |
| `amount` | decimal | no | Refunded amount in USD. |

## Relationships

- `orders.customer_id` → `customers.customer_id` (many-to-one)
- `order_items.order_id` → `orders.order_id` (many-to-one)
- `order_items.product_id` → `products.product_id` (many-to-one)
- `payments.order_id` → `orders.order_id` (many-to-one)
- `refunds.payment_id` → `payments.payment_id` (many-to-one)
- `refunds.order_id` → `orders.order_id` (many-to-one)
