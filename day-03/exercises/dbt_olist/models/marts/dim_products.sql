-- Dimension: products with an English category label (translation joined here, not in staging).
with
    products as (select * from {{ ref('stg_products') }}),
    translation as (
        select * from {{ source('olist_landing', 'product_category_name_translation') }}
    )
select
    {{ dbt_utils.generate_surrogate_key(['p.product_id']) }} as product_sk,
    p.product_id,
    {{ generate_category_label('t.product_category_name_english', 'p.product_category_name') }}
    as category,
    p.product_category_name as category_pt,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm
from products p
left join translation t on p.product_category_name = t.product_category_name
