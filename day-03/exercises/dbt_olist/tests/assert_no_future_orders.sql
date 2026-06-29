-- Singular test: must return 0 rows. No order can be purchased in the future.
select order_id, order_purchase_ts
from {{ ref('stg_orders') }}
where order_purchase_ts > current_timestamp()
