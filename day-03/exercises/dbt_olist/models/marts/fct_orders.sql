-- Fact: one row per order. Incremental MERGE on Delta with a surrogate key.
{{ config(
    materialized         = 'incremental',
    unique_key           = 'order_id',
    incremental_strategy = 'merge',
    file_format          = 'delta'
) }}

with base as (select * from {{ ref('int_orders_enriched') }})
select
    {{ dbt_utils.generate_surrogate_key(['order_id']) }} as order_sk,
    order_id,
    customer_id,
    customer_unique_id,
    customer_state,
    customer_city,
    order_status,
    order_purchase_ts,
    delivered_at,
    estimated_delivery_at,
    item_count,
    items_total,
    freight_total,
    order_total,
    total_paid,
    max_installments,
    days_to_deliver,
    is_late
from base
{% if is_incremental() %}
    -- only process orders newer than the latest already loaded
    where order_purchase_ts > (select max(order_purchase_ts) from {{ this }})
{% endif %}
