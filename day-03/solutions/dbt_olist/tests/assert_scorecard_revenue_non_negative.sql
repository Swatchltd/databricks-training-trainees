-- Singular test: a seller's total revenue can never be negative. Must return 0 rows.
select seller_id, revenue from {{ ref('gld_seller_scorecard') }}
where revenue < 0
