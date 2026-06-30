-- Staging: faithful 1:1 with source. Rename + cast only. No joins, no aggregations. (view)
with
    source as (select * from {{ source('olist_landing', 'orders') }}),
    renamed as (
        select
            order_id,
            customer_id,
            order_status,
            {{ cast_timestamp('order_purchase_timestamp',      'order_purchase_ts') }},
            {{ cast_timestamp('order_approved_at',             'approved_at') }},
            {{ cast_timestamp('order_delivered_carrier_date',  'shipped_at') }},
            {{ cast_timestamp('order_delivered_customer_date', 'delivered_at') }},
            {{ cast_timestamp('order_estimated_delivery_date', 'estimated_delivery_at') }}
        from source
    )
select *
from renamed
