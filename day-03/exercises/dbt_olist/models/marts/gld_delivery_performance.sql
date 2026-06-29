-- Gold: delivery KPIs by customer state + region (delivered orders only).
-- Demonstrates a SEED: br_state_regions (static lookup) joined via ref().
with
    o as (
        select *
        from {{ ref('fct_orders') }}
        where order_status = 'delivered' and delivered_at is not null
    ),
    regions as (
        select * from {{ ref('br_state_regions') }}  -- seeded CSV (state -> region)
    )
select
    o.customer_state,
    r.region,
    count(*) as delivered_orders,
    round(avg(o.days_to_deliver), 1) as avg_delivery_days,
    round(100.0 * sum(o.is_late) / count(*), 1) as late_pct,
    round(100.0 * sum(1 - o.is_late) / count(*), 1) as on_time_pct
from o
left join regions r on o.customer_state = r.state
group by o.customer_state, r.region
