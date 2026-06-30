-- Case 3: review sentiment per English category. table.
-- Caveat: a review is per ORDER; an order can span multiple categories, so a review is counted
-- ONCE per category of its order (multi-category orders ~0.8%). Documented, accepted here.
{{ config(materialized='table') }}
with
    reviews as (select order_id, review_score from {{ ref('stg_order_reviews') }}),
    order_category as (
        -- one row per (order, category): dedup at CATEGORY level so a review is counted once per
        -- category, not once per product (an order can have several products in the same category).
        select distinct oi.order_id, p.category
        from {{ ref('stg_order_items') }} oi
        left join {{ ref('dim_products') }} p on oi.product_id = p.product_id
    )
select
    oc.category,
    count(r.review_score) as n_reviews,
    round(avg(r.review_score), 2) as avg_review_score,
    round(
        100.0 * sum(case when r.review_score = 1 then 1 else 0 end) / count(r.review_score), 1
    ) as pct_1_star,
    round(
        100.0 * sum(case when r.review_score = 5 then 1 else 0 end) / count(r.review_score), 1
    ) as pct_5_star
from reviews r
join order_category oc on r.order_id = oc.order_id
group by oc.category
