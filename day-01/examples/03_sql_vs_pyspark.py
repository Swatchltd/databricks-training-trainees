# Databricks notebook source

# MAGIC %md
# MAGIC # Day 1 · Demo 03 — SQL vs PySpark, Side by Side.
# MAGIC
# MAGIC In Databricks you can express the same transformation in **SQL** or **PySpark** — both run on
# MAGIC the same engine and produce the same result. This demo runs each operation **both ways** so the
# MAGIC class can see the one-to-one mapping. Every cell is fully worked.
# MAGIC
# MAGIC **Catalog/schema:** tables live in `training_<name>.landing`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup — load the tables as DataFrames
# MAGIC
# MAGIC `spark.table()` reads from the catalog lazily — no data is copied until an action runs.

# COMMAND ----------

from pyspark.sql import functions as F

orders = spark.table("training_<name>.landing.orders")
order_items = spark.table("training_<name>.landing.order_items")
customers = spark.table("training_<name>.landing.customers")
products = spark.table("training_<name>.landing.products")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part A — Filter + select
# MAGIC
# MAGIC SQL uses `WHERE`; PySpark uses `.filter()` and `.select()`. First the SQL version.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT order_id, order_purchase_timestamp
# MAGIC FROM training_<name>.landing.orders
# MAGIC WHERE order_status = 'shipped'
# MAGIC LIMIT 10;

# COMMAND ----------

# Part A — PySpark equivalent
# F.col() is preferred over plain strings: IDE autocomplete + typos caught early
(
    orders.filter(F.col("order_status") == "shipped")
    .select("order_id", "order_purchase_timestamp")
    .limit(10)
    .display()
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part B — GROUP BY + count per state
# MAGIC
# MAGIC Count distinct orders per customer state. SQL `GROUP BY` maps to PySpark `.groupBy().agg()`.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   c.customer_state,
# MAGIC   COUNT(DISTINCT o.order_id) AS order_count
# MAGIC FROM training_<name>.landing.orders o
# MAGIC JOIN training_<name>.landing.customers c ON o.customer_id = c.customer_id
# MAGIC GROUP BY c.customer_state
# MAGIC ORDER BY order_count DESC;

# COMMAND ----------

# Part B — PySpark equivalent
# countDistinct because one customer_id can appear on multiple orders
(
    orders.join(customers, on="customer_id", how="inner")
    .groupBy("customer_state")
    .agg(F.countDistinct("order_id").alias("order_count"))
    .orderBy(F.desc("order_count"))
    .display()
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part C — Join order_items with products
# MAGIC
# MAGIC A `LEFT JOIN` keeps every line item even when product metadata is missing.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   oi.order_id,
# MAGIC   p.product_category_name,
# MAGIC   oi.price
# MAGIC FROM training_<name>.landing.order_items oi
# MAGIC LEFT JOIN training_<name>.landing.products p ON oi.product_id = p.product_id
# MAGIC LIMIT 20;

# COMMAND ----------

# Part C — PySpark equivalent
# how="left" matches the SQL LEFT JOIN — keeps all order_items rows
(
    order_items.join(products, on="product_id", how="left")
    .select("order_id", "product_category_name", "price")
    .limit(20)
    .display()
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part D — Top products by revenue
# MAGIC
# MAGIC `ROUND(SUM(price), 2)` in SQL is `F.round(F.sum("price"), 2)` in PySpark — same structure, same result.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   oi.product_id,
# MAGIC   p.product_category_name,
# MAGIC   ROUND(SUM(oi.price), 2) AS total_revenue
# MAGIC FROM training_<name>.landing.order_items oi
# MAGIC LEFT JOIN training_<name>.landing.products p ON oi.product_id = p.product_id
# MAGIC GROUP BY oi.product_id, p.product_category_name
# MAGIC ORDER BY total_revenue DESC
# MAGIC LIMIT 5;

# COMMAND ----------

# Part D — PySpark equivalent
# The chain .join().groupBy().agg().orderBy().limit() mirrors the SQL clause order
(
    order_items.join(products, on="product_id", how="left")
    .groupBy("product_id", "product_category_name")
    .agg(F.round(F.sum("price"), 2).alias("total_revenue"))
    .orderBy(F.desc("total_revenue"))
    .limit(5)
    .display()
)
# Always validate that both approaches agree — they should return identical rows.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recap
# MAGIC
# MAGIC | Operation | SQL | PySpark |
# MAGIC |-----------|-----|---------|
# MAGIC | Filter | `WHERE col = 'x'` | `.filter(F.col("col") == "x")` |
# MAGIC | Group + count | `GROUP BY` + `COUNT(DISTINCT ...)` | `.groupBy().agg(F.countDistinct(...))` |
# MAGIC | Join | `LEFT JOIN ... ON` | `.join(df, on=key, how="left")` |
# MAGIC | Aggregate revenue | `ROUND(SUM(price), 2)` | `F.round(F.sum("price"), 2)` |
# MAGIC | Sort + limit | `ORDER BY ... DESC LIMIT n` | `.orderBy(F.desc(...)).limit(n)` |
# MAGIC
# MAGIC Same engine, same results — pick the style that fits the task and the team.
