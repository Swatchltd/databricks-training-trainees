-- TODO: staging for sellers. Rename/cast only, materialized as a view.
-- columns you'll want: seller_id, seller_state, seller_city
-- House style: two CTEs (source -> renamed), then `select * from renamed`.
with source ?? ?
