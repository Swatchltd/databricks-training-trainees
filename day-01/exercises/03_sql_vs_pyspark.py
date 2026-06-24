# Databricks notebook source

# MAGIC %md
# MAGIC # Exercise 03: SQL vs PySpark — Side by Side
# MAGIC
# MAGIC In Databricks, you can query data using either **SQL** or **PySpark**. Both are valid — the choice depends on your background, the complexity of the transformation, and team conventions.
# MAGIC
# MAGIC This notebook shows the same operations written in both styles so you can compare them directly.
# MAGIC
# MAGIC **Catalog:** `training_<name>` | **Schema:** `landing`

# COMMAND ----------

from pyspark.sql import functions as F

# Read tables into DataFrames
orders = spark.table("training_<name>.landing.orders")
order_items = spark.table("training_<name>.landing.order_items")
customers = spark.table("training_<name>.landing.customers")
products = spark.table("training_<name>.landing.products")
order_payments = spark.table("training_<name>.landing.order_payments")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part A: SELECT + Filter
# MAGIC
# MAGIC Both SQL and PySpark let you filter rows and select specific columns. Here's how they compare.
# MAGIC
# MAGIC - **SQL**: uses `WHERE` clause
# MAGIC - **PySpark**: uses `.filter()` (or `.where()`) and `.select()`

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT order_id, order_status, order_purchase_timestamp
# MAGIC FROM training_<name>.landing.orders
# MAGIC WHERE order_status = 'delivered'
# MAGIC LIMIT 10

# COMMAND ----------

# PySpark equivalent of the SQL cell above
orders.filter(F.col("order_status") == "delivered") \
      .select("order_id", "order_status", "order_purchase_timestamp") \
      .limit(10) \
      .display()

# COMMAND ----------

# TODO: Using PySpark, filter orders to only 'shipped' status and show order_id and order_purchase_timestamp
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part B: GROUP BY Aggregation
# MAGIC
# MAGIC Aggregations summarise data across groups of rows.
# MAGIC
# MAGIC - **SQL**: `GROUP BY` + aggregate functions like `COUNT(*)`, `SUM()`, `AVG()`
# MAGIC - **PySpark**: `.groupBy()` + `.agg()` with `F.count()`, `F.sum()`, etc.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT order_status, COUNT(*) AS order_count
# MAGIC FROM training_<name>.landing.orders
# MAGIC GROUP BY order_status
# MAGIC ORDER BY order_count DESC

# COMMAND ----------

# PySpark equivalent of the SQL cell above
orders.groupBy("order_status") \
      .agg(F.count("*").alias("order_count")) \
      .orderBy(F.desc("order_count")) \
      .display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Part B)
# MAGIC Count the number of orders per **customer state** by joining `orders` and `customers`.
# MAGIC Write both a SQL version and a PySpark version.
# MAGIC
# MAGIC Relevant tables: `orders` (customer_id), `customers` (customer_id, customer_state)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO: Count orders per customer_state (SQL version)
# MAGIC -- Hint: join orders and customers on customer_id, then group by customer_state

# COMMAND ----------

# TODO: Count orders per customer_state (PySpark version)
# Hint: join orders and customers DataFrames, then groupBy customer_state
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part C: JOIN
# MAGIC
# MAGIC Joins combine rows from two tables based on a matching key column.
# MAGIC
# MAGIC - **SQL**: `JOIN ... ON ...`
# MAGIC - **PySpark**: `.join(other_df, on="key_column", how="inner")`

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT o.order_id, o.order_status, c.customer_city, c.customer_state
# MAGIC FROM training_<name>.landing.orders o
# MAGIC JOIN training_<name>.landing.customers c
# MAGIC   ON o.customer_id = c.customer_id
# MAGIC LIMIT 20

# COMMAND ----------

# PySpark equivalent of the SQL cell above
orders.join(customers, on="customer_id", how="inner") \
      .select("order_id", "order_status", "customer_city", "customer_state") \
      .limit(20) \
      .display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Part C)
# MAGIC Join `order_items` with `products` to show `order_id`, `product_category_name`, and `price`.
# MAGIC Write both a SQL version and a PySpark version.
# MAGIC
# MAGIC Relevant columns: `order_items.product_id`, `products.product_id`, `products.product_category_name`, `order_items.price`

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO: Join order_items with products (SQL version)
# MAGIC -- Show: order_id, product_category_name, price

# COMMAND ----------

# TODO: Join order_items with products (PySpark version)
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part D: ORDER BY / Sort
# MAGIC
# MAGIC Sorting results helps you find top or bottom values quickly.
# MAGIC
# MAGIC - **SQL**: `ORDER BY column DESC`
# MAGIC - **PySpark**: `.orderBy(F.desc("column"))`

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT order_id, payment_value
# MAGIC FROM training_<name>.landing.order_payments
# MAGIC ORDER BY payment_value DESC
# MAGIC LIMIT 10

# COMMAND ----------

# PySpark equivalent of the SQL cell above
order_payments.orderBy(F.desc("payment_value")) \
              .select("order_id", "payment_value") \
              .limit(10) \
              .display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Part D)
# MAGIC Show the **top 5 products by total revenue** (sum of `price` in `order_items`).
# MAGIC Write both a SQL version and a PySpark version.
# MAGIC
# MAGIC Hint: Group by `product_id`, compute `SUM(price)`, sort descending, limit to 5.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO: Top 5 products by total revenue (SQL version)

# COMMAND ----------

# TODO: Top 5 products by total revenue (PySpark version)
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part E: Student Challenge
# MAGIC
# MAGIC **Business question:** What is the total revenue per seller state? Show the top 10 states by revenue.
# MAGIC
# MAGIC **Tables to use:**
# MAGIC - `order_items` — contains `seller_id`, `price`
# MAGIC - `sellers` — contains `seller_id`, `seller_state`
# MAGIC
# MAGIC **Revenue** = SUM(price)
# MAGIC
# MAGIC Write **both** a SQL version and a PySpark version.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO: Total revenue per seller state, top 10 (SQL version)

# COMMAND ----------

sellers = spark.table("training_<name>.landing.sellers")

# TODO: Total revenue per seller state, top 10 (PySpark version)
# your code here
