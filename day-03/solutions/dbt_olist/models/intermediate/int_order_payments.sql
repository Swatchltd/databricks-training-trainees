-- Intermediate: roll payments up to one row per order.
-- Materialized as a VIEW (the intermediate folder default) so it can be queried and tested.
-- Reads the typed stg_order_payments (rename/cast live THERE); this model owns ONLY the rollup.
-- (ephemeral would inline it as a CTE but you couldn't query/test it - see the materializations
-- slide.)
with payments as (select * from {{ ref('stg_order_payments') }})
select
    order_id,
    round(sum(payment_value), 2) as total_paid,
    count(*) as n_payment_rows,
    max(payment_installments) as max_installments
from payments
group by order_id
