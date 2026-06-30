{% snapshot orders_snapshot %}
    {{ config(
    schema='snapshots',
    unique_key='order_id',
    strategy='check',
    check_cols=['order_status']
) }}
    -- SCD2: track how each order's status changes over time.
    select order_id, order_status, order_purchase_timestamp
    from {{ source('olist_landing', 'orders') }}
{% endsnapshot %}
