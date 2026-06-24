# Day 1 — Databricks & Python Foundations

All Day 1 code is delivered as **Databricks notebooks** (`.py` source format). Each topic
comes in three flavours:

- **`examples/`** — complete, runnable notebooks the **trainer demos** live ("I do").
- **`exercises/`** — the same concepts with `TODO`s for you to complete ("you do").
- **`solutions/`** — the worked answers ("we review").

## Prerequisites

- Access to the Databricks workspace (URL and login from the trainer).
- A compute cluster (or the shared training cluster) and a SQL warehouse.
- The Olist dataset ingested as managed Delta tables in **`training_<name>.landing`**, where
  `<name>` is your own name (e.g. `training_anna`). The trainer demos this ingestion via
  **Data Engineering → Add data / Ingestion** at the start of Chapter 3.

Set your catalog/schema once at the top of each notebook:

```python
spark.sql("USE CATALOG `training_<name>`")
spark.sql("USE SCHEMA landing")
```

## Notebooks

| # | Topic | Tool |
|---|-------|------|
| 01 | `01_python_basics` — types, variables, functions, loops, comprehensions, dicts | Notebook (pure Python) |
| 02 | `02_sql_foundations` — SELECT/WHERE, GROUP BY, HAVING, JOIN, CTEs, window functions | Notebook (`%sql`) |
| 03 | `03_sql_vs_pyspark` — every Spark SQL operation and its PySpark counterpart | Notebook |
| 04 | `04_dataset_exploration` — business questions on Olist (SQL + PySpark) | Notebook |

### Bonus / overflow material

| # | Topic |
|---|-------|
| 05 | `05_spark_and_delta_tips` — explicit schema, cache/unpersist, broadcast join, MERGE, time travel, repartition/coalesce |
| 06 | `06_performance_and_delta_optimization` — `.explain()` & narrow/wide, broadcasting the 71-row translation table, data skew & salting (`review_id`, SP-heavy state), partitioning by date, `OPTIMIZE`/`ZORDER`, liquid clustering, `VACUUM`, avoiding UDFs |

## How to open a notebook in Databricks

1. Sidebar → **Workspace**, navigate to your user folder (or a Git folder).
2. **Import** and upload the `.py` file, or drag it in.
3. Attach your cluster from the top-right dropdown.
4. Run cells with `Shift + Enter`.

## Olist tables (in `training_<name>.landing`)

`orders`, `order_items`, `order_payments`, `order_reviews`, `products`, `sellers`,
`customers`, `product_category_name_translation`, `geolocation`.

> **Two data gotchas used throughout the week:** `order_reviews.review_id` is **not unique**
> (~814 duplicate rows), and some `products.product_category_name` values have **no English
> translation** — `COALESCE` them to a fallback. For "top customer" analysis, group by
> **`customer_unique_id`**, not `customer_id` (the latter is generated per order).

## Solutions

Solutions are in `solutions/`. Try first — peek only if stuck.
