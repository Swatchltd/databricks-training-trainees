# Day 3 — Exercise: build your own marts (3 business cases)

You have the `dbt_olist` example project (orders / order_items / customers / products already
staged, plus `fct_orders`, `dim_customers`, `dim_products`). Now **you** design the models for
three business questions. For each: add any **staging** you need, an **intermediate** model if it
helps, and a **mart** — then test and document it.

You are already inside the `dbt_olist` project (a copy of the example backbone). Add your new models
into `models/staging|intermediate|marts`. Stubs are in `business_cases/stubs/` to get you started;
rename/extend freely (move them into `models/…`).

## The three cases

1. **Seller performance scorecard** — one row per seller: seller_state, orders, revenue, avg delivery days,
   on-time %, avg review score. *(new staging: sellers, reviews)*
2. **Customer retention / cohorts** — group customers by their **first-order month** (cohort) and
   measure repeat rate and average lifetime value. *(use `customer_unique_id`, build on `dim_customers`)*
3. **Review sentiment by category** — per **English** product category: number of reviews, avg
   score, % 1-star, % 5-star. *(new staging: reviews; reuse `dim_products`)*
   *(grain trap: a review is per **order**, not per item/category — an order can span categories; decide
   how to attribute it and avoid double-counting a review within a single category.)*

## What "good" looks like

- Staging = rename/cast only (views). Business logic in intermediate/marts.
- Pick a sensible **materialization** (view vs table vs incremental) and justify it.
- Add **tests** (not_null/unique on keys, accepted_values, a `dbt_expectations` range, a singular test).
- Add **descriptions** (they become dbt docs).
- Use `customer_unique_id` (not `customer_id`) for case 2.

## dbt commands to practise

```bash
uv run dbt build -s +gld_seller_scorecard      # build a model and everything it needs
uv run dbt test  -s gld_seller_scorecard
uv run dbt ls -s tag:marts                      # list / select
uv run dbt compile -s gld_customer_cohorts      # inspect the compiled SQL
uv run dbt retry                                # rerun only what failed
uv run dbt docs generate && uv run dbt docs serve
```

> Be creative — if you see a better mart for this data, build that instead. We'll compare in the solutions.
