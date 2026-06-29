-- Staging: customers. customer_id is per-order; customer_unique_id is the real customer. (view)
with
    source as (select * from {{ source('olist_landing', 'customers') }}),
    renamed as (
        select
            customer_id,
            customer_unique_id,
            customer_zip_code_prefix as zip_code,
            customer_city,
            customer_state
        from source
    )
select *
from renamed
