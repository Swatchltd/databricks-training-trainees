# Databricks notebook source

# MAGIC %md
# MAGIC # Day 1 · Demo 02 — SQL Foundations
# MAGIC
# MAGIC A complete, runnable tour of Databricks SQL on the **Olist** dataset.
# MAGIC Every query is fully worked — no TODOs. We build up from `SELECT` to window functions.
# MAGIC
# MAGIC **Catalog/schema:** tables live in `training_<name>.landing`. We set the active
# MAGIC catalog and schema once so every query can use short table names.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup — active catalog and schema
# MAGIC
# MAGIC `USE CATALOG` / `USE SCHEMA` save us from repeating the full path in every query.

# COMMAND ----------

# MAGIC %sql
# MAGIC USE CATALOG `training_<name>`;
# MAGIC USE SCHEMA landing;
# MAGIC -- Replace <name> with your own name (e.g., training_jan).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part A — SELECT, WHERE, ORDER BY
# MAGIC
# MAGIC Pick columns, filter rows with `WHERE`, sort with `ORDER BY`, and cap output with `LIMIT`.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Most recent delivered orders
# MAGIC SELECT
# MAGIC   order_id,
# MAGIC   customer_id,
# MAGIC   order_status,
# MAGIC   order_purchase_timestamp
# MAGIC FROM orders
# MAGIC WHERE order_status = 'delivered'
# MAGIC ORDER BY order_purchase_timestamp DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC Swap the filter value to inspect canceled orders — same shape, different `WHERE`.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- All canceled orders, most recent first
# MAGIC SELECT
# MAGIC   order_id,
# MAGIC   order_purchase_timestamp
# MAGIC FROM orders
# MAGIC WHERE order_status = 'canceled'
# MAGIC ORDER BY order_purchase_timestamp DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part B — GROUP BY + Aggregates
# MAGIC
# MAGIC Aggregate functions (`COUNT`, `SUM`, `AVG`, `ROUND`) collapse rows; `GROUP BY` defines the buckets.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Count orders per status
# MAGIC SELECT
# MAGIC   order_status,
# MAGIC   COUNT(*) AS order_count
# MAGIC FROM orders
# MAGIC GROUP BY order_status
# MAGIC ORDER BY order_count DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC Average payment value per payment type — `ROUND(..., 2)` keeps money readable; show the count for context.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   payment_type,
# MAGIC   COUNT(*) AS payment_count,
# MAGIC   ROUND(AVG(payment_value), 2) AS avg_payment_value
# MAGIC FROM order_payments
# MAGIC GROUP BY payment_type
# MAGIC ORDER BY avg_payment_value DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part C — GROUP BY + HAVING
# MAGIC
# MAGIC `HAVING` filters *groups* after aggregation — `WHERE` can't reference aggregate functions.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Products appearing in more than 100 order line items
# MAGIC SELECT
# MAGIC   product_id,
# MAGIC   COUNT(*) AS item_count
# MAGIC FROM order_items
# MAGIC GROUP BY product_id
# MAGIC HAVING COUNT(*) > 100
# MAGIC ORDER BY item_count DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part D — JOINs
# MAGIC
# MAGIC `JOIN` combines tables on a key. Aliases (`o`, `oi`, `p`) keep multi-table queries readable.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Join orders -> order_items -> products to see category and price per line
# MAGIC SELECT
# MAGIC   o.order_id,
# MAGIC   p.product_category_name,
# MAGIC   oi.price
# MAGIC FROM orders o
# MAGIC JOIN order_items oi ON o.order_id = oi.order_id
# MAGIC JOIN products p ON oi.product_id = p.product_id
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part E — CTEs (WITH clause)
# MAGIC
# MAGIC A CTE names a sub-query so you can reference it like a table — great for readability.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Average review score per product (CTE), then keep only products averaging >= 4.0
# MAGIC WITH product_avg_reviews AS (
# MAGIC   SELECT
# MAGIC     oi.product_id,
# MAGIC     ROUND(AVG(r.review_score), 2) AS avg_score,
# MAGIC     COUNT(r.review_id) AS review_count
# MAGIC   FROM order_items oi
# MAGIC   JOIN order_reviews r ON oi.order_id = r.order_id
# MAGIC   GROUP BY oi.product_id
# MAGIC )
# MAGIC SELECT
# MAGIC   product_id,
# MAGIC   avg_score,
# MAGIC   review_count
# MAGIC FROM product_avg_reviews
# MAGIC WHERE avg_score >= 4.0
# MAGIC ORDER BY avg_score DESC, review_count DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part F — Window Functions
# MAGIC
# MAGIC `RANK() OVER (PARTITION BY ... ORDER BY ...)` ranks rows within groups *without* collapsing them.
# MAGIC You can't filter on a window result directly — wrap it in a CTE first, then filter the outer query.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Top-ranked customer (by order count) within each state
# MAGIC WITH customer_order_counts AS (
# MAGIC   SELECT
# MAGIC     c.customer_id,
# MAGIC     c.customer_state,
# MAGIC     COUNT(*) AS order_count
# MAGIC   FROM orders o
# MAGIC   JOIN customers c ON o.customer_id = c.customer_id
# MAGIC   GROUP BY c.customer_id, c.customer_state
# MAGIC ),
# MAGIC ranked AS (
# MAGIC   SELECT
# MAGIC     customer_id,
# MAGIC     customer_state,
# MAGIC     order_count,
# MAGIC     RANK() OVER (PARTITION BY customer_state ORDER BY order_count DESC) AS state_rank
# MAGIC   FROM customer_order_counts
# MAGIC )
# MAGIC SELECT customer_state, customer_id, order_count, state_rank
# MAGIC FROM ranked
# MAGIC WHERE state_rank = 1
# MAGIC ORDER BY customer_state;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recap
# MAGIC
# MAGIC | Part | Feature | Key rule |
# MAGIC |------|---------|----------|
# MAGIC | A | SELECT / WHERE / ORDER BY | `WHERE` filters rows; `ORDER BY` sorts results |
# MAGIC | B | GROUP BY / aggregates | Non-aggregate columns must appear in `GROUP BY` |
# MAGIC | C | HAVING | Use `HAVING` (not `WHERE`) to filter after aggregation |
# MAGIC | D | JOINs | `INNER JOIN` = intersection; aliases keep columns unambiguous |
# MAGIC | E | CTEs | Named sub-queries that improve readability and reuse |
# MAGIC | F | Window functions | `OVER (PARTITION BY ... ORDER BY ...)` ranks without collapsing rows |
