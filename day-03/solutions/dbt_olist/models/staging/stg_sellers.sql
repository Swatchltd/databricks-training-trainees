-- Staging: sellers (rename only). view.
with
    source as (select * from {{ source('olist_landing', 'sellers') }}),
    renamed as (
        select seller_id, seller_zip_code_prefix as zip_code, seller_city, seller_state from source
    )
select *
from renamed
