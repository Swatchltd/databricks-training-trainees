-- Fact: one row per order. Incremental MERGE on Delta with a surrogate key.
{{ config(
    materialized         = 'incremental',
    unique_key           = 'order_id',
    incremental_strategy = 'merge',
    file_format          = 'delta'
) }}

with base as (
    select * from {{ ref('int_orders_enriched') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['order_id']) }} as order_sk,
    *
from base
{% if is_incremental() %}
  -- only process orders newer than the latest already loaded
  where order_purchase_ts > (select max(order_purchase_ts) from {{ this }})
{% endif %}
