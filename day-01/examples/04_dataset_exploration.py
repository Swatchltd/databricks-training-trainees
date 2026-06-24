# Databricks notebook source

# MAGIC %md
# MAGIC # Day 1 · Demo 04 — Dataset Exploration (Trainer "I do")
# MAGIC
# MAGIC We now answer real **business questions** about the Olist dataset, showing the PySpark
# MAGIC solution and the equivalent SQL for each. Every cell is fully worked — no TODOs.
# MAGIC
# MAGIC **Catalog/schema:** tables live in `training_<name>.landing`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup
# MAGIC
# MAGIC Import the functions/window helpers we'll reuse across the questions.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# COMMAND ----------

# MAGIC %md
# MAGIC ## Q1 — Order status distribution
# MAGIC
# MAGIC How many orders sit in each status? A simple `groupBy` + count answers it.

# COMMAND ----------

# Q1 — PySpark
orders = spark.table("training_<name>.landing.orders")
(
    orders
    .groupBy("order_status")
    .agg(F.count("*").alias("order_count"))
    .orderBy(F.desc("order_count"))
    .display()
)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Q1 — SQL
# MAGIC SELECT order_status, COUNT(*) AS order_count
# MAGIC FROM training_<name>.landing.orders
# MAGIC GROUP BY order_status
# MAGIC ORDER BY order_count DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Q2 — Average delivery time
# MAGIC
# MAGIC `datediff` on (delivered − purchased) gives days. We filter out NULLs — undelivered orders
# MAGIC have no delivery date and would otherwise skew the average.

# COMMAND ----------

# Q2 — PySpark
orders = spark.table("training_<name>.landing.orders")
(
    orders
    .filter(F.col("order_delivered_customer_date").isNotNull())
    .withColumn(
        "delivery_days",
        F.datediff(F.col("order_delivered_customer_date"), F.col("order_purchase_timestamp"))
    )
    .agg(
        F.round(F.avg("delivery_days"), 1).alias("avg_delivery_days"),
        F.min("delivery_days").alias("min_delivery_days"),
        F.max("delivery_days").alias("max_delivery_days"),
    )
    .display()
)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Q2 — SQL
# MAGIC SELECT
# MAGIC   ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)), 1) AS avg_delivery_days,
# MAGIC   MIN(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)) AS min_days,
# MAGIC   MAX(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)) AS max_days
# MAGIC FROM training_<name>.landing.orders
# MAGIC WHERE order_delivered_customer_date IS NOT NULL;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Q3 — Revenue by product category (top 10)
# MAGIC
# MAGIC `LEFT JOIN` to products keeps every line item; we coalesce a missing category to `'unknown'`
# MAGIC so those rows are counted rather than dropped.

# COMMAND ----------

# Q3 — PySpark
order_items = spark.table("training_<name>.landing.order_items")
products = spark.table("training_<name>.landing.products")
(
    order_items
    .join(products, on="product_id", how="left")
    .fillna({"product_category_name": "unknown"})
    .groupBy("product_category_name")
    .agg(F.round(F.sum("price"), 2).alias("total_revenue"))
    .orderBy(F.desc("total_revenue"))
    .limit(10)
    .display()
)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Q3 — SQL
# MAGIC SELECT
# MAGIC   COALESCE(p.product_category_name, 'unknown') AS product_category_name,
# MAGIC   ROUND(SUM(oi.price), 2) AS total_revenue,
# MAGIC   COUNT(DISTINCT oi.order_id) AS order_count
# MAGIC FROM training_<name>.landing.order_items oi
# MAGIC LEFT JOIN training_<name>.landing.products p ON oi.product_id = p.product_id
# MAGIC GROUP BY COALESCE(p.product_category_name, 'unknown')
# MAGIC ORDER BY total_revenue DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Q4 — Review score distribution
# MAGIC
# MAGIC Count reviews per score and add the percentage share. In SQL, `SUM(COUNT(*)) OVER ()`
# MAGIC gives the grand total in a single pass.

# COMMAND ----------

# Q4 — PySpark
order_reviews = spark.table("training_<name>.landing.order_reviews")
total_reviews = order_reviews.count()
(
    order_reviews
    .groupBy("review_score")
    .agg(F.count("*").alias("review_count"))
    .withColumn("pct", F.round(F.col("review_count") / F.lit(total_reviews) * 100, 1))
    .orderBy("review_score")
    .display()
)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Q4 — SQL
# MAGIC SELECT
# MAGIC   review_score,
# MAGIC   COUNT(*) AS review_count,
# MAGIC   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
# MAGIC FROM training_<name>.landing.order_reviews
# MAGIC GROUP BY review_score
# MAGIC ORDER BY review_score;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Q5 — Late-delivery rate by state
# MAGIC
# MAGIC Among delivered orders, flag those delivered after the estimate, then aggregate per state.
# MAGIC Casting the boolean to `int` (0/1) lets us `sum` it to count late orders.

# COMMAND ----------

# Q5 — PySpark
orders = spark.table("training_<name>.landing.orders")
customers = spark.table("training_<name>.landing.customers")
(
    orders
    .filter(F.col("order_delivered_customer_date").isNotNull())
    .withColumn(
        "is_late",
        (F.col("order_delivered_customer_date") > F.col("order_estimated_delivery_date")).cast("int")
    )
    .join(customers, on="customer_id", how="left")
    .groupBy("customer_state")
    .agg(
        F.count("*").alias("delivered_orders"),
        F.sum("is_late").alias("late_orders"),
        F.round(F.sum("is_late") / F.count("*") * 100, 1).alias("late_rate_pct"),
    )
    .orderBy(F.desc("late_rate_pct"))
    .display()
)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Q5 — SQL
# MAGIC SELECT
# MAGIC   c.customer_state,
# MAGIC   COUNT(*) AS delivered_orders,
# MAGIC   SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) AS late_orders,
# MAGIC   ROUND(
# MAGIC     SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END)
# MAGIC     * 100.0 / COUNT(*),
# MAGIC     1
# MAGIC   ) AS late_rate_pct
# MAGIC FROM training_<name>.landing.orders o
# MAGIC JOIN training_<name>.landing.customers c ON o.customer_id = c.customer_id
# MAGIC WHERE o.order_delivered_customer_date IS NOT NULL
# MAGIC GROUP BY c.customer_state
# MAGIC ORDER BY late_rate_pct DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recap
# MAGIC
# MAGIC | Question | Key technique |
# MAGIC |----------|---------------|
# MAGIC | Q1 status distribution | `groupBy` + count |
# MAGIC | Q2 avg delivery time | `datediff` + NULL filter on delivery date |
# MAGIC | Q3 revenue by category | `LEFT JOIN` + `COALESCE`/`fillna` to 'unknown' |
# MAGIC | Q4 review distribution | count + share via `SUM(COUNT(*)) OVER ()` |
# MAGIC | Q5 late-delivery rate | boolean→int flag, sum / count per state |
