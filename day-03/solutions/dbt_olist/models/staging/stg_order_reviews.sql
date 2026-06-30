-- Staging: reviews. review_id is NOT unique in Olist (a review can span orders) -> never test it
-- unique.
with
    source as (select * from {{ source('olist_landing', 'order_reviews') }}),
    renamed as (
        select
            review_id,
            order_id,
            cast(review_score as int) as review_score,
            {{ cast_timestamp('review_creation_date',    'review_created_at') }},
            {{ cast_timestamp('review_answer_timestamp', 'review_answered_at') }}
        from source
    )
select *
from renamed
