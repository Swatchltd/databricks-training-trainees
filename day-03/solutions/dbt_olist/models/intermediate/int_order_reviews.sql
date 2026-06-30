-- Intermediate: collapse reviews to one row per order (an order can have >1 review row). view.
with reviews as (select * from {{ ref('stg_order_reviews') }})
select order_id, round(avg(review_score), 2) as avg_review_score, count(*) as n_reviews
from reviews
group by order_id
