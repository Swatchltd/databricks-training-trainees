-- Staging: reviews. review_id is NOT unique in Olist (a review can span orders) -> never test it
-- unique.
with
    source as (select * from {{ source('olist_landing', 'order_reviews') }}),

    -- Olist review_comment_message holds multi-line free text; rows that split during CSV ingestion
    -- become "continuation" rows with shifted columns (review_score ends up a timestamp/garbage).
    -- Keep only genuine reviews (score 1–5) BEFORE casting, so no row ever hits an invalid cast.
    real_reviews as (
        select * from source where review_score rlike '^[1-5]$'
    ),

    renamed as (
        select
            review_id,
            order_id,
            cast(review_score as int) as review_score,           -- safe now: filtered to 1–5
            {{ cast_timestamp('review_creation_date',    'review_created_at') }},
            {{ cast_timestamp('review_answer_timestamp', 'review_answered_at') }}
        from real_reviews
    )

select * from renamed