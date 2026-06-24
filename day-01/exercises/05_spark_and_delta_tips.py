# Databricks notebook source

# MAGIC %md
# MAGIC # Exercise 05: Spark and Delta Lake Tips
# MAGIC
# MAGIC This notebook walks through practical patterns you will use when building production-grade pipelines in Databricks:
# MAGIC
# MAGIC - **Part A**: Explicit schema vs schema inference
# MAGIC - **Part B**: Caching and unpersisting DataFrames
# MAGIC - **Part C**: Broadcast joins for small tables
# MAGIC - **Part D**: MERGE INTO (upsert) with Delta Lake
# MAGIC - **Part E**: Time travel — querying previous versions of a Delta table
# MAGIC - **Bonus**: `repartition` vs `coalesce`
# MAGIC
# MAGIC **Catalog:** `training_<name>` | **Schema:** `landing`

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part A: Explicit Schema vs Schema Inference
# MAGIC
# MAGIC When you read a Delta table without specifying a schema, Spark **infers** it by scanning the data and reading metadata. This works fine interactively, but in production:
# MAGIC
# MAGIC - Schema inference can be slow on large datasets
# MAGIC - Inferred types may surprise you (e.g., a column you expect as `Integer` gets inferred as `Long`)
# MAGIC - Explicit schemas make your code self-documenting and fail fast on unexpected input
# MAGIC
# MAGIC **Rule of thumb:** use inference for exploration, use explicit schemas in production jobs.

# COMMAND ----------

# Schema inference — works, but Spark reads metadata and may scan data to determine types
orders_inferred = spark.table("training_<name>.landing.orders")
orders_inferred.printSchema()

# COMMAND ----------

# Explicit schema — define exactly what you expect
orders_schema = StructType([
    StructField("order_id", StringType(), nullable=False),
    StructField("customer_id", StringType(), nullable=True),
    StructField("order_status", StringType(), nullable=True),
    StructField("order_purchase_timestamp", TimestampType(), nullable=True),
])

# When reading from Delta, the schema is enforced by the table definition.
# For CSV/JSON sources you would pass the schema directly:
#   spark.read.schema(orders_schema).csv("path/to/file")
#
# For Delta tables, you can validate by casting or selecting with the expected types:
orders_explicit = spark.table("training_<name>.landing.orders").select(
    F.col("order_id").cast(StringType()),
    F.col("customer_id").cast(StringType()),
    F.col("order_status").cast(StringType()),
    F.col("order_purchase_timestamp").cast(TimestampType()),
)
orders_explicit.printSchema()

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Part A)
# MAGIC Write a `StructType` schema for the `order_items` table covering these columns:
# MAGIC - `order_id` — String
# MAGIC - `order_item_id` — Integer
# MAGIC - `product_id` — String
# MAGIC - `price` — Double
# MAGIC - `freight_value` — Double

# COMMAND ----------

# TODO: Define a StructType schema for order_items
order_items_schema = StructType([
    # your StructField definitions here
])

print(order_items_schema)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part B: Cache and Unpersist
# MAGIC
# MAGIC By default, Spark recomputes a DataFrame from scratch every time you call an action (`.count()`, `.display()`, `.write`, etc.). If you use the same DataFrame multiple times, this wastes time.
# MAGIC
# MAGIC **Caching** stores the computed result in memory (or memory + disk) after the first action, so subsequent actions reuse it.
# MAGIC
# MAGIC **When to cache:**
# MAGIC - You reference the same DataFrame 2+ times in the same notebook
# MAGIC - The DataFrame is expensive to compute (large joins, aggregations)
# MAGIC
# MAGIC **When NOT to cache:**
# MAGIC - You only use the DataFrame once
# MAGIC - The DataFrame is very large and would evict other data from memory
# MAGIC - Always call `.unpersist()` when you are done to free memory

# COMMAND ----------

orders_df = spark.table("training_<name>.landing.orders")

# Cache the DataFrame — nothing is stored yet, caching is lazy
orders_df.cache()

# First action triggers the cache — data is read and stored in memory
print("Total orders:", orders_df.count())

# Second action uses the cached data — much faster
delivered_count = orders_df.filter(F.col("order_status") == "delivered").count()
print("Delivered orders:", delivered_count)

# Always unpersist when done to free up cluster memory
orders_df.unpersist()
print("Cache cleared.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Part B)
# MAGIC Cache the `order_items` table, run two different aggregations, then unpersist.
# MAGIC
# MAGIC Suggested aggregations:
# MAGIC 1. Total number of order items (`.count()`)
# MAGIC 2. Total sum of the `price` column

# COMMAND ----------

# TODO: Cache order_items, run two aggregations, then unpersist
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part C: Broadcast Join
# MAGIC
# MAGIC In a standard join, Spark shuffles both DataFrames across the network so matching keys end up on the same executor. This is expensive.
# MAGIC
# MAGIC A **broadcast join** avoids the shuffle by sending a copy of the *small* table to every executor. The large table is never moved.
# MAGIC
# MAGIC **Use broadcast joins when:**
# MAGIC - One table is small (typically < 200 MB, configurable via `spark.sql.autoBroadcastJoinThreshold`)
# MAGIC - You are joining a large fact table with a small dimension/lookup table
# MAGIC
# MAGIC Spark can auto-broadcast small tables, but you can force it with `broadcast()`.

# COMMAND ----------

from pyspark.sql.functions import broadcast

products_df = spark.table("training_<name>.landing.products")       # small dimension table
order_items_df = spark.table("training_<name>.landing.order_items")  # large fact table

# Broadcast the small products table to every executor
result = order_items_df.join(broadcast(products_df), on="product_id", how="left")
result.limit(10).display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Part C)
# MAGIC Perform a broadcast join between `order_items` and `product_category_name_translation`.
# MAGIC `product_category_name_translation` is a small lookup table that maps Portuguese category names to English ones.
# MAGIC
# MAGIC Join key: `product_category_name` (present in both `products` and the translation table)
# MAGIC
# MAGIC Steps:
# MAGIC 1. Load `order_items`, `products`, and `product_category_name_translation`
# MAGIC 2. Join `order_items` with `products` to get the Portuguese category name
# MAGIC 3. Broadcast join with `product_category_name_translation` to get the English name
# MAGIC 4. Display `order_id` and the English category name

# COMMAND ----------

translation_df = spark.table("training_<name>.landing.product_category_name_translation")

# TODO: Broadcast join order_items -> products -> translation table
# Show: order_id, English category name
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part D: MERGE INTO (Upsert)
# MAGIC
# MAGIC Delta Lake supports `MERGE INTO` — a single statement that handles both **updates** to existing rows and **inserts** of new rows. This is the standard pattern for incremental data loads.
# MAGIC
# MAGIC ```
# MAGIC MERGE INTO target_table AS t
# MAGIC USING source_table AS s
# MAGIC ON t.key = s.key
# MAGIC WHEN MATCHED THEN UPDATE SET ...
# MAGIC WHEN NOT MATCHED THEN INSERT ...
# MAGIC ```
# MAGIC
# MAGIC Use cases: slowly changing dimensions, deduplication, CDC (change data capture).

# COMMAND ----------

# Setup: create a small target table from the first 100 orders
spark.sql("""
    CREATE OR REPLACE TABLE `training_<name>`.landing.orders_sample
    AS SELECT * FROM `training_<name>`.landing.orders LIMIT 100
""")

print("orders_sample created with", spark.table("training_<name>.landing.orders_sample").count(), "rows")

# COMMAND ----------

# Create a small DataFrame simulating "new incoming data"
# This contains:
#   - some rows that already exist in orders_sample (matched -> update)
#   - one completely new row (not matched -> insert)

from pyspark.sql import Row

existing_order = spark.table("training_<name>.landing.orders_sample").first()

new_data = spark.createDataFrame([
    # Update: same order_id but status changed to 'canceled'
    Row(
        order_id=existing_order["order_id"],
        customer_id=existing_order["customer_id"],
        order_status="canceled",
        order_purchase_timestamp=existing_order["order_purchase_timestamp"],
        order_approved_at=existing_order["order_approved_at"],
        order_delivered_carrier_date=existing_order["order_delivered_carrier_date"],
        order_delivered_customer_date=existing_order["order_delivered_customer_date"],
        order_estimated_delivery_date=existing_order["order_estimated_delivery_date"],
    ),
    # Insert: brand new order not in the target table
    Row(
        order_id="new-order-00001",
        customer_id="new-customer-00001",
        order_status="processing",
        order_purchase_timestamp=None,
        order_approved_at=None,
        order_delivered_carrier_date=None,
        order_delivered_customer_date=None,
        order_estimated_delivery_date=None,
    ),
])

new_data.createOrReplaceTempView("orders_updates")
print("Source (new_data) row count:", new_data.count())

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Part D)
# MAGIC Write a `MERGE INTO` statement that:
# MAGIC - **WHEN MATCHED**: updates the `order_status` column
# MAGIC - **WHEN NOT MATCHED**: inserts all columns from the source
# MAGIC
# MAGIC Fill in the `ON` condition and the action clauses where indicated.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO: Complete the MERGE statement below
# MAGIC
# MAGIC MERGE INTO `training_<name>`.landing.orders_sample AS target
# MAGIC USING orders_updates AS source
# MAGIC ON /* TODO: match on the primary key column */
# MAGIC
# MAGIC WHEN MATCHED THEN
# MAGIC   UPDATE SET /* TODO: set order_status = source.order_status */
# MAGIC
# MAGIC WHEN NOT MATCHED THEN
# MAGIC   INSERT * /* inserts all columns from source — works when schemas match */

# COMMAND ----------

# Verify the result
spark.table("training_<name>.landing.orders_sample") \
     .filter(F.col("order_id").isin(["new-order-00001", existing_order["order_id"]])) \
     .display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part E: Time Travel
# MAGIC
# MAGIC Every write to a Delta table (INSERT, UPDATE, DELETE, MERGE) creates a new **version**. Delta Lake keeps the full history, so you can:
# MAGIC
# MAGIC - **Query** any previous version using `VERSION AS OF` or `TIMESTAMP AS OF`
# MAGIC - **Restore** the table to a previous version with `RESTORE TABLE`
# MAGIC - **Audit** what changed and when with `DESCRIBE HISTORY`
# MAGIC
# MAGIC This is invaluable for debugging, recovering from bad writes, and regulatory compliance.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- View the full history of orders_sample (each MERGE, CREATE, etc. creates a version)
# MAGIC DESCRIBE HISTORY `training_<name>`.landing.orders_sample

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Query version 0 — the table as it was immediately after creation (before the MERGE)
# MAGIC SELECT * FROM `training_<name>`.landing.orders_sample VERSION AS OF 0
# MAGIC LIMIT 5

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Restore to version 0 (commented out — uncomment to run)
# MAGIC -- RESTORE TABLE `training_<name>`.landing.orders_sample TO VERSION AS OF 0

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Part E)
# MAGIC 1. Query `orders_sample` at `VERSION AS OF 0` and count the rows
# MAGIC 2. Count the rows in the **current** version of `orders_sample`
# MAGIC 3. Are the counts different? Why?

# COMMAND ----------

# TODO: Count rows in VERSION AS OF 0
# Hint: spark.read.format("delta").option("versionAsOf", 0).table("training_<name>.landing.orders_sample")
version_0_count = None  # replace with your code
print("Version 0 count:", version_0_count)

# TODO: Count rows in the current version
current_count = None  # replace with your code
print("Current count:", current_count)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bonus: repartition vs coalesce
# MAGIC
# MAGIC Spark splits data into **partitions** that are processed in parallel across executors. The number of partitions affects performance:
# MAGIC
# MAGIC - **Too few partitions** → executors are underutilised, jobs run slowly
# MAGIC - **Too many partitions** → task scheduling overhead, many small files written to storage
# MAGIC
# MAGIC | Method | Behaviour | Use case |
# MAGIC |--------|-----------|----------|
# MAGIC | `repartition(n)` | Full shuffle — redistributes data evenly | Increase partition count, or partition by a specific column |
# MAGIC | `repartition(n, col)` | Shuffle by column value | Ensure all rows with the same key land on the same partition |
# MAGIC | `coalesce(n)` | No shuffle — merges existing partitions | Reduce partition count before writing (avoids many tiny files) |
# MAGIC
# MAGIC **Rule of thumb:** aim for partition sizes of 100–200 MB. Use `coalesce` before writing to storage.

# COMMAND ----------

orders_df = spark.table("training_<name>.landing.orders")

print("Default partitions:", orders_df.rdd.getNumPartitions())

# repartition — triggers a full shuffle, data is redistributed evenly
orders_repartitioned = orders_df.repartition(8)
print("After repartition(8):", orders_repartitioned.rdd.getNumPartitions())

# coalesce — no full shuffle, merges partitions on the same executor
orders_coalesced = orders_df.coalesce(2)
print("After coalesce(2):", orders_coalesced.rdd.getNumPartitions())

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (Bonus)
# MAGIC Repartition the `order_items` table into **4 partitions** keyed by `seller_id`, then verify the partition count.
# MAGIC
# MAGIC Why might partitioning by `seller_id` be useful if you often aggregate or filter by seller?

# COMMAND ----------

order_items_df = spark.table("training_<name>.landing.order_items")

# TODO: Repartition order_items into 4 partitions by seller_id
# your code here

# TODO: Print the number of partitions to verify
# Hint: .rdd.getNumPartitions()
