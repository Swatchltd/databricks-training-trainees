-- Gold: monthly revenue by English product category (delivered orders only).
-- Full table rebuild: a monthly rollup re-aggregates history (don't make it incremental).
with
    order_items as (select * from {{ ref('stg_order_items') }}),
    orders as (
        select order_id, order_purchase_ts
        from {{ ref('fct_orders') }}
        where order_status = 'delivered'
    ),
    products as (select product_id, category from {{ ref('dim_products') }})
select
    p.category,
    date_trunc('month', o.order_purchase_ts) as order_month,
    count(distinct o.order_id) as order_count,
    round(sum(oi.price), 2) as revenue
from order_items oi
join orders o on oi.order_id = o.order_id
left join products p on oi.product_id = p.product_id
group by p.category, date_trunc('month', o.order_purchase_ts)
