-- Case 1: seller scorecard. table (re-aggregated rollup; one row per seller).
{{ config(materialized='table') }}
with
    items as (select * from {{ ref('stg_order_items') }}),
    delivered as (
        select order_id, days_to_deliver, is_late
        from {{ ref('fct_orders') }}
        where order_status = 'delivered'
    ),
    sellers as (select * from {{ ref('stg_sellers') }}),
    order_reviews as (select * from {{ ref('int_order_reviews') }})
select
    s.seller_id,
    s.seller_state,
    count(distinct i.order_id) as n_orders,
    round(sum(i.price), 2) as revenue,
    round(avg(d.days_to_deliver), 1) as avg_delivery_days,
    round(100.0 * avg(d.is_late), 1) as late_pct,
    round(avg(r.avg_review_score), 2) as avg_review_score
from items i
join delivered d on i.order_id = d.order_id  -- delivered orders only
join sellers s on i.seller_id = s.seller_id
left join order_reviews r on i.order_id = r.order_id
group by s.seller_id, s.seller_state
