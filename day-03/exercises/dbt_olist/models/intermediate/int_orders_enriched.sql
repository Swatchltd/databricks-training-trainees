-- Intermediate: order-grain enrichment. Joins staging + aggregates items + payments,
-- and derives delivery metrics. Business logic lives here, not yet a use-case product.
-- Materialized as a TABLE (overrides the folder 'view' default): it is reused by BOTH
-- fct_orders and dim_customers, so compute it once rather than recomputing per consumer.
{{ config(materialized='table') }}

with
    orders as (select * from {{ ref('stg_orders') }}),
    customers as (select * from {{ ref('stg_customers') }}),
    item_agg as (
        select
            order_id,
            count(*) as item_count,
            round(sum(price), 2) as items_total,
            round(sum(freight_value), 2) as freight_total
        from {{ ref('stg_order_items') }}
        group by order_id
    ),
    payments as (
        select * from {{ ref('int_order_payments') }}  -- a reused per-order rollup (view)
    ),
    final as (
        select
            o.order_id,
            o.customer_id,
            c.customer_unique_id,
            c.customer_state,
            c.customer_city,
            o.order_status,
            o.order_purchase_ts,
            o.delivered_at,
            o.estimated_delivery_at,
            -- 775 Olist orders (mostly canceled/unavailable) have no order_items rows,
            -- so the LEFT JOIN yields NULL. Treat "no items" as 0 so order_total is never
            -- NULL and gold revenue/delivery marts don't drop or null-propagate these orders.
            coalesce(i.item_count, 0) as item_count,
            coalesce(i.items_total, 0) as items_total,
            coalesce(i.freight_total, 0) as freight_total,
            round(coalesce(i.items_total, 0) + coalesce(i.freight_total, 0), 2) as order_total,
            p.total_paid,
            p.max_installments,
            datediff(o.delivered_at, o.order_purchase_ts) as days_to_deliver,
            case when o.delivered_at > o.estimated_delivery_at then 1 else 0 end as is_late
        from orders o
        left join customers c on o.customer_id = c.customer_id
        left join item_agg i on o.order_id = i.order_id
        left join payments p on o.order_id = p.order_id
    )
select *
from final
