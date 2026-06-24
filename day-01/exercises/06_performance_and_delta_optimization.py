# Databricks notebook source

# MAGIC %md
# MAGIC # Day 1 — Bonus 06: Spark Performance & Delta Optimization
# MAGIC
# MAGIC Extra / overflow material for when the room moves faster than planned. It goes one
# MAGIC level deeper than Exercise 05, using the **Olist** tables to show *why* a query is
# MAGIC slow and how to fix it.
# MAGIC
# MAGIC | Part | Topic |
# MAGIC |------|-------|
# MAGIC | A | Narrow vs wide transformations — reading `.explain()` |
# MAGIC | B | Broadcast join — the 71-row `product_category_name_translation` |
# MAGIC | C | Data skew & salting — the `review_id` duplicates and the SP-heavy state key |
# MAGIC | D | Partitioning by date (and why liquid clustering usually wins) |
# MAGIC | E | `OPTIMIZE` + `ZORDER` — the small-file problem |
# MAGIC | F | Liquid clustering — `CLUSTER BY` |
# MAGIC | G | `VACUUM` — reclaiming storage safely |
# MAGIC | H | Avoid Python UDFs — use built-ins |
# MAGIC
# MAGIC **Catalog:** `training_<name>` | **Schema:** `landing`
# MAGIC
# MAGIC > Each part has a worked example you can run, then a **TODO** for you. Solutions are in
# MAGIC > `solutions/06_performance_and_delta_optimization_solution.py`.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast

CATALOG = "training_<name>"   # <-- replace <name> with your own
SCHEMA  = "landing"
spark.sql(f"USE CATALOG `{CATALOG}`")
spark.sql(f"USE SCHEMA {SCHEMA}")

orders      = spark.table("orders")
order_items = spark.table("order_items")
products    = spark.table("products")
order_reviews = spark.table("order_reviews")
customers   = spark.table("customers")
translation = spark.table("product_category_name_translation")  # only 71 rows

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part A — Narrow vs wide transformations
# MAGIC
# MAGIC - **Narrow** (e.g. `filter`, `select`, `withColumn`): each output partition depends on a
# MAGIC   single input partition. No data moves between executors — cheap.
# MAGIC - **Wide** (e.g. `groupBy`, `join`, `distinct`): rows must be re-grouped across the cluster.
# MAGIC   This is a **shuffle** — the expensive boundary that creates a new *stage*.
# MAGIC
# MAGIC `.explain()` shows the physical plan. Look for **`Exchange`** — that is a shuffle.

# COMMAND ----------

# Narrow only — no Exchange in the plan
narrow = order_items.filter(F.col("price") > 100).select("order_id", "price")
narrow.explain()

# COMMAND ----------

# Wide — groupBy forces a shuffle; you'll see an "Exchange hashpartitioning(...)" node
wide = order_items.groupBy("seller_id").agg(F.sum("price").alias("rev"))
wide.explain()

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (A)
# MAGIC Build a DataFrame that joins `order_items` to `orders` on `order_id`, then call
# MAGIC `.explain()`. Find the `Exchange` node(s) in the plan — how many shuffles happen,
# MAGIC and which join strategy did Spark pick (`SortMergeJoin` or `BroadcastHashJoin`)?

# COMMAND ----------

# TODO (A): join order_items + orders on order_id, then .explain()
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part B — Broadcast join (the 71-row translation table)
# MAGIC
# MAGIC `product_category_name_translation` has only **71 rows**. Shuffling the large
# MAGIC `order_items`/`products` data to join it would be wasteful. A **broadcast join**
# MAGIC ships the tiny table to every executor instead — no shuffle of the big side.
# MAGIC
# MAGIC Spark auto-broadcasts tables under `spark.sql.autoBroadcastJoinThreshold` (10 MB by
# MAGIC default), but being explicit with `broadcast()` documents intent and is safe.

# COMMAND ----------

# Big side: order_items -> products (Portuguese category). Small side: translation (EN names).
items_with_cat = order_items.join(products, on="product_id", how="left")

bjoin = items_with_cat.join(broadcast(translation), on="product_category_name", how="left")
# Look for "BroadcastHashJoin" + "BroadcastExchange" on the small side
bjoin.select("order_id", "product_category_name_english", "price").explain()

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (B)
# MAGIC Run the same join **without** `broadcast()` and compare the plan. Which join strategy
# MAGIC does Spark choose now? (For a 71-row table it will usually still auto-broadcast — note
# MAGIC what you'd expect if the table were, say, 5 GB instead.)

# COMMAND ----------

# TODO (B): join items_with_cat to translation WITHOUT broadcast(), then .explain()
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part C — Data skew & salting
# MAGIC
# MAGIC A shuffle sends all rows with the same key to one partition. If one key is huge, one
# MAGIC task does most of the work while others idle — **data skew**. Two Olist examples:
# MAGIC
# MAGIC 1. **`review_id` is not unique** (~814 duplicate rows). Joining/grouping on it sends the
# MAGIC    repeated ids to the same partition.
# MAGIC 2. **`customer_state` is dominated by SP** (~42% of all orders). Any aggregation/join by
# MAGIC    state piles ~42% of the data onto one partition.
# MAGIC
# MAGIC **Fix: salting** — append a small random bucket to the key so a hot key spreads across
# MAGIC several partitions; aggregate in two passes.

# COMMAND ----------

# Surface the review_id duplication (the data-quality root of the skew)
dupes = (order_reviews.groupBy("review_id").count()
         .filter(F.col("count") > 1))
print("review_ids appearing more than once:", dupes.count())
dupes.orderBy(F.desc("count")).show(5, truncate=False)

# COMMAND ----------

# Show the state skew: SP dwarfs the rest
(orders.join(customers, on="customer_id")
       .groupBy("customer_state").count()
       .orderBy(F.desc("count"))
       .show(5))

# COMMAND ----------

# Salting pattern (generic): spread a hot key across N buckets before the wide op
N = 16
salted = (orders.join(customers, on="customer_id")
          .withColumn("salt", (F.rand() * N).cast("int")))

# Pass 1: aggregate by (state, salt) -> many small groups, evenly spread
pass1 = salted.groupBy("customer_state", "salt").agg(F.count("*").alias("c"))
# Pass 2: collapse the salt buckets -> final per-state count
final = pass1.groupBy("customer_state").agg(F.sum("c").alias("order_count"))
final.orderBy(F.desc("order_count")).show(5)

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (C)
# MAGIC The duplicate `review_id`s would break a downstream join that assumes one row per review.
# MAGIC Write a query that **deduplicates** `order_reviews` to one row per `review_id`
# MAGIC (keep the most recent `review_answer_timestamp`). Hint: `ROW_NUMBER() OVER (PARTITION BY
# MAGIC review_id ORDER BY review_answer_timestamp DESC)` then keep `rn = 1`.

# COMMAND ----------

# TODO (C): deduplicate order_reviews to one row per review_id
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part D — Partitioning by date
# MAGIC
# MAGIC Physical partitioning stores rows in separate folders per partition value, so queries
# MAGIC that filter on that column **skip** (prune) the rest.
# MAGIC
# MAGIC **Pitfalls:** partition only on a **low-cardinality** column (month/year, not `order_id`).
# MAGIC Too many small partitions = the small-file problem. For most tables Databricks now
# MAGIC recommends **liquid clustering** (Part F) instead of Hive-style partitioning.

# COMMAND ----------

# Build a partitioned copy keyed by purchase month (low cardinality ~25 values)
spark.sql("""
CREATE OR REPLACE TABLE orders_by_month
USING DELTA
PARTITIONED BY (purchase_month)
AS SELECT *, date_format(order_purchase_timestamp, 'yyyy-MM') AS purchase_month
FROM orders
""")

# A filter on the partition column prunes whole folders — check the scan in .explain()
spark.table("orders_by_month").filter(F.col("purchase_month") == "2018-01").explain()

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (D)
# MAGIC Count how many distinct `purchase_month` values exist. Would partitioning by
# MAGIC `order_purchase_timestamp` (full timestamp) instead of month be a good idea? Why not?

# COMMAND ----------

# TODO (D): count distinct purchase_month values
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part E — OPTIMIZE + ZORDER (the small-file problem)
# MAGIC
# MAGIC Streaming/incremental writes leave many small files; reading them is slow (lots of
# MAGIC metadata + I/O). `OPTIMIZE` compacts them into ~1 GB files. `ZORDER BY (col)` co-locates
# MAGIC rows with similar values so filters on that column read fewer files (data skipping).

# COMMAND ----------

# Make a working copy, then compact + Z-order on a common filter column
spark.sql("CREATE OR REPLACE TABLE order_items_opt AS SELECT * FROM order_items")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Compact small files and co-locate by the column you filter on most
# MAGIC OPTIMIZE order_items_opt ZORDER BY (product_id);
# MAGIC -- DESCRIBE HISTORY order_items_opt;   -- see the OPTIMIZE operation + metrics

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (E)
# MAGIC We most often filter `order_items` by `seller_id`. Run `OPTIMIZE ... ZORDER BY` on the
# MAGIC column that would speed those queries up, then run `DESCRIBE HISTORY` and read the
# MAGIC `operationMetrics` (how many files were removed vs added?).

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO (E): OPTIMIZE order_items_opt, Z-ordered by the right column
# MAGIC -- YOUR QUERY HERE

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part F — Liquid clustering (`CLUSTER BY`)
# MAGIC
# MAGIC Liquid clustering is the modern replacement for partitioning **and** ZORDER. You declare
# MAGIC clustering keys once; Databricks keeps data clustered incrementally as it's written —
# MAGIC no folder explosion, and you can change keys later. You **cannot** combine it with
# MAGIC `PARTITIONED BY` or `ZORDER`.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create a liquid-clustered table, then let OPTIMIZE cluster the data
# MAGIC CREATE OR REPLACE TABLE order_items_lc
# MAGIC CLUSTER BY (seller_id, product_id) AS
# MAGIC SELECT * FROM order_items;
# MAGIC
# MAGIC OPTIMIZE order_items_lc;   -- clusters the data by the declared keys

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (F)
# MAGIC Change the clustering keys of `order_items_lc` to cluster by `order_id` only, using
# MAGIC `ALTER TABLE ... CLUSTER BY (...)`, then `OPTIMIZE` again. (Changing keys is allowed —
# MAGIC that's the point of liquid clustering.)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO (F): ALTER the clustering keys, then OPTIMIZE
# MAGIC -- YOUR QUERY HERE

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part G — VACUUM (reclaim storage safely)
# MAGIC
# MAGIC `OPTIMIZE`, `UPDATE`, `MERGE` etc. leave old data files behind so time travel still
# MAGIC works. `VACUUM` deletes files older than the **retention period** (default **7 days**).
# MAGIC
# MAGIC > **Trade-off:** vacuuming below the retention window breaks time travel for those
# MAGIC > versions. Databricks blocks `RETAIN < 168 HOURS` unless you disable the safety check —
# MAGIC > never do that in production without understanding the consequence.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Preview what WOULD be deleted (no files removed in DRY RUN)
# MAGIC VACUUM order_items_opt RETAIN 168 HOURS DRY RUN;

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (G)
# MAGIC Run a real `VACUUM` on `order_items_opt` with the default 7-day retention (no `DRY RUN`).
# MAGIC Then explain in a comment: after this VACUUM, can you still `SELECT ... VERSION AS OF 0`?

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO (G): VACUUM order_items_opt with default retention
# MAGIC -- YOUR QUERY HERE

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part H — Avoid Python UDFs; prefer built-ins
# MAGIC
# MAGIC A Python UDF runs row-by-row in a separate Python process — Spark can't optimise it and
# MAGIC pays serialization cost. Built-in `pyspark.sql.functions` run in the JVM/Photon and are
# MAGIC optimised by Catalyst. Reach for a built-in (or `when/otherwise`) before a UDF.

# COMMAND ----------

# DON'T: a Python UDF for something built-ins already do
from pyspark.sql.types import StringType

@F.udf(returnType=StringType())
def bucket_udf(score):
    return "positive" if score >= 4 else ("neutral" if score == 3 else "negative")

slow = order_reviews.withColumn("sentiment", bucket_udf("review_score"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### TODO (H)
# MAGIC Rewrite the sentiment bucketing **without** a UDF, using `F.when(...).otherwise(...)`.
# MAGIC The result should match the UDF version.

# COMMAND ----------

# TODO (H): reproduce the sentiment column using F.when / .otherwise
# your code here

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bonus — Predictive Optimization
# MAGIC
# MAGIC Rather than scheduling `OPTIMIZE`/`VACUUM` yourself, Databricks runs them automatically
# MAGIC when it detects they'll help — **Predictive Optimization**, now **on by default** for
# MAGIC Unity Catalog managed tables (all accounts since May 2025). Combined with **Automatic
# MAGIC Liquid Clustering** (`CLUSTER BY AUTO`), the platform even **picks and maintains the
# MAGIC clustering keys** for you based on your query patterns — you just declare `CLUSTER BY AUTO`
# MAGIC and let it tune. In production this is usually the right default.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cleanup (optional)
# MAGIC Drop the scratch tables this notebook created.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- DROP TABLE IF EXISTS orders_by_month;
# MAGIC -- DROP TABLE IF EXISTS order_items_opt;
# MAGIC -- DROP TABLE IF EXISTS order_items_lc;
