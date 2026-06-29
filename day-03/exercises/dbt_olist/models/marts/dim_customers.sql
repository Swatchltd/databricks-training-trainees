-- Dimension: one row per REAL customer (customer_unique_id), enriched with order history.
-- NOTE: a customer_unique_id can map to several customer_id rows with DIFFERENT city/state
-- (122 customers ordered from more than one location). A plain DISTINCT would therefore
-- produce multiple rows per customer. We collapse to ONE row using the location from the
-- customer's MOST RECENT order.
with
    orders as (select * from {{ ref('int_orders_enriched') }}),
    agg as (
        select
            customer_unique_id,
            count(*) as n_orders,
            round(sum(order_total), 2) as lifetime_value,
            min(order_purchase_ts) as first_order_ts,
            max(order_purchase_ts) as last_order_ts
        from orders
        group by customer_unique_id
    ),
    ranked_loc as (
        select
            customer_unique_id,
            customer_state,
            customer_city,
            row_number() over (
                partition by customer_unique_id
                order by order_purchase_ts desc, customer_state, customer_city
            ) as rn
        from orders
    ),
    loc as (
        select customer_unique_id, customer_state, customer_city from ranked_loc
where rn = 1  -- exactly one location per customer
    )
select
    {{ dbt_utils.generate_surrogate_key(['a.customer_unique_id']) }} as customer_sk,
    a.customer_unique_id,
    l.customer_state,
    l.customer_city,
    a.n_orders,
    a.lifetime_value,
    a.first_order_ts,
    a.last_order_ts,
    case when a.n_orders > 1 then true else false end as is_repeat_customer
from agg a
join loc l on a.customer_unique_id = l.customer_unique_id
