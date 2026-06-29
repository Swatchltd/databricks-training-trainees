-- Staging: payments, one row per (order_id, payment_sequential).
-- Rename + cast ONLY (a view) - the source has multiple payment lines per order
-- (e.g. part voucher + part card). The roll-up to ONE row per order happens in
-- int_order_payments; payment-grain consumers (e.g. a payment-behaviour mart) build on THIS.
with
    source as (select * from {{ source('olist_landing', 'order_payments') }}),
    renamed as (
        select
            order_id,
            cast(payment_sequential as int) as payment_sequential,
            payment_type,
            cast(payment_installments as int) as payment_installments,
            cast(payment_value as double) as payment_value
        from source
    )
select *
from renamed
