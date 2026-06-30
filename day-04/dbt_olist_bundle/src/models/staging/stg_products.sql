-- Staging: products. Category stays Portuguese here (translation happens in dim_products). (view)
with
    source as (select * from {{ source('olist_landing', 'products') }}),
    renamed as (
        select
            product_id,
            product_category_name,
            cast(product_weight_g as int) as product_weight_g,
            cast(product_length_cm as int) as product_length_cm,
            cast(product_height_cm as int) as product_height_cm,
            cast(product_width_cm as int) as product_width_cm
        from source
    )
select *
from renamed
