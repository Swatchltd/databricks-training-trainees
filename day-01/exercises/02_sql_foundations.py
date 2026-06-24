# Databricks notebook source

# MAGIC %md
# MAGIC # Day 1 — Exercise 02: SQL Foundations
# MAGIC
# MAGIC In this notebook you will practise SQL on the Olist e-commerce dataset
# MAGIC stored in Databricks Unity Catalog.
# MAGIC
# MAGIC **Before you start:** replace every occurrence of `<name>` in the setup
# MAGIC cell below with your own first name (lowercase, no spaces).
# MAGIC Example: if your name is Anna, use `training_anna`.
# MAGIC
# MAGIC Work through **Parts A–F** in order. Each part has:
# MAGIC 1. A short explanation
# MAGIC 2. A worked example query you can run as-is
# MAGIC 3. A **TODO** query for you to write

# COMMAND ----------

# Reminder: replace <name> with your own name in the cell below before running it.
# Example: USE CATALOG `training_anna`;

# COMMAND ----------

# MAGIC %sql
# MAGIC USE CATALOG `training_<name>`;
# MAGIC USE SCHEMA landing;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part A — Basic SELECT, WHERE, ORDER BY
# MAGIC
# MAGIC Retrieve rows from a table, filter with `WHERE`, and sort with `ORDER BY`.
# MAGIC Use `LIMIT` to avoid scanning the full table during exploration.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example: most recent delivered orders
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
# MAGIC **TODO A:** Write a query that returns all **canceled** orders.
# MAGIC Show `order_id` and `order_purchase_timestamp`, ordered by most recent first.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO A: find all canceled orders, most recent first
# MAGIC -- YOUR QUERY HERE

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part B — Aggregations: COUNT, SUM, AVG, ROUND
# MAGIC
# MAGIC Aggregate functions collapse many rows into a single value.
# MAGIC `GROUP BY` splits rows into groups before aggregating.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example: count orders per status
# MAGIC SELECT
# MAGIC   order_status,
# MAGIC   COUNT(*) AS order_count
# MAGIC FROM orders
# MAGIC GROUP BY order_status
# MAGIC ORDER BY order_count DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC **TODO B:** Write a query that returns the **average payment value per payment type**
# MAGIC from the `order_payments` table.
# MAGIC Round the average to 2 decimal places and alias it `avg_payment_value`.
# MAGIC Order by `avg_payment_value` descending.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO B: average payment value per payment_type, rounded to 2 decimals
# MAGIC -- YOUR QUERY HERE

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part C — GROUP BY + HAVING
# MAGIC
# MAGIC `HAVING` filters *groups* after aggregation (like `WHERE` but for groups).
# MAGIC Always place `HAVING` after `GROUP BY` and before `ORDER BY`.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example: states with more than 500 customers
# MAGIC SELECT
# MAGIC   customer_state,
# MAGIC   COUNT(*) AS customer_count
# MAGIC FROM customers
# MAGIC GROUP BY customer_state
# MAGIC HAVING COUNT(*) > 500
# MAGIC ORDER BY customer_count DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC **TODO C:** Write a query that finds **product IDs with more than 100 order line items**.
# MAGIC Use the `order_items` table, group by `product_id`, and filter with `HAVING`.
# MAGIC Show `product_id` and the count aliased as `item_count`, ordered by `item_count` descending.
# MAGIC
# MAGIC *(We will join to the products table in Part D.)*

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO C: product_ids appearing in more than 100 order line items
# MAGIC -- YOUR QUERY HERE

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part D — JOINs
# MAGIC
# MAGIC `JOIN` combines rows from two or more tables on a matching key.
# MAGIC Use table aliases (e.g. `o` for `orders`) to keep queries readable.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example: join orders with customers to see city and state per order
# MAGIC SELECT
# MAGIC   o.order_id,
# MAGIC   o.order_status,
# MAGIC   c.customer_city,
# MAGIC   c.customer_state
# MAGIC FROM orders o
# MAGIC JOIN customers c
# MAGIC   ON o.customer_id = c.customer_id
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC **TODO D:** Write a query that joins `orders`, `order_items`, and `products`
# MAGIC to show the following columns for each order line:
# MAGIC   - `order_id`
# MAGIC   - `product_category_name`
# MAGIC   - `price`
# MAGIC
# MAGIC Limit the result to 20 rows.
# MAGIC
# MAGIC *Hint: join `orders` to `order_items` on `order_id`, then join `order_items`
# MAGIC to `products` on `product_id`.*

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO D: join orders + order_items + products
# MAGIC -- YOUR QUERY HERE

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part E — CTEs (WITH Clause)
# MAGIC
# MAGIC A **Common Table Expression (CTE)** names a subquery so you can reference
# MAGIC it like a table. This keeps complex queries readable and avoids repetition.
# MAGIC
# MAGIC ```sql
# MAGIC WITH cte_name AS (
# MAGIC   SELECT ...
# MAGIC )
# MAGIC SELECT * FROM cte_name;
# MAGIC ```

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example: orders per state using a CTE, top 10
# MAGIC WITH orders_per_state AS (
# MAGIC   SELECT
# MAGIC     c.customer_state,
# MAGIC     COUNT(DISTINCT o.order_id) AS order_count
# MAGIC   FROM orders o
# MAGIC   JOIN customers c
# MAGIC     ON o.customer_id = c.customer_id
# MAGIC   GROUP BY c.customer_state
# MAGIC )
# MAGIC SELECT *
# MAGIC FROM orders_per_state
# MAGIC ORDER BY order_count DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC **TODO E:** Write a CTE that:
# MAGIC 1. In the CTE body: computes the **average review score per product_id**
# MAGIC    by joining `order_reviews` with `order_items` on `order_id`.
# MAGIC    Call the CTE `avg_scores` and alias the average as `avg_score`.
# MAGIC 2. In the outer query: selects only products where `avg_score >= 4.0`.
# MAGIC    Show `product_id` and `avg_score`, ordered by `avg_score` descending.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO E: CTE for average review score per product, filter avg >= 4.0
# MAGIC -- YOUR QUERY HERE

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part F — Window Functions (Challenge)
# MAGIC
# MAGIC Window functions compute a value **across a set of rows** related to the
# MAGIC current row, without collapsing rows like `GROUP BY` does.
# MAGIC
# MAGIC Common window functions: `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`, `SUM()`, `AVG()`.
# MAGIC
# MAGIC Syntax:
# MAGIC ```sql
# MAGIC FUNCTION() OVER (
# MAGIC   PARTITION BY partition_column
# MAGIC   ORDER BY sort_column DESC
# MAGIC )
# MAGIC ```

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example: rank customers globally by their number of orders
# MAGIC SELECT
# MAGIC   customer_id,
# MAGIC   order_count,
# MAGIC   ROW_NUMBER() OVER (ORDER BY order_count DESC) AS global_rank
# MAGIC FROM (
# MAGIC   SELECT
# MAGIC     customer_id,
# MAGIC     COUNT(*) AS order_count
# MAGIC   FROM orders
# MAGIC   GROUP BY customer_id
# MAGIC ) t
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC **TODO F:** Write a query that ranks customers **within each state** by
# MAGIC their order count, and returns only the **top-ranked customer per state**.
# MAGIC
# MAGIC Steps:
# MAGIC 1. Use a CTE (or subquery) to compute `order_count` per **`customer_unique_id`**,
# MAGIC    joined with `customers` to get `customer_state`.
# MAGIC 2. Apply `RANK() OVER (PARTITION BY customer_state ORDER BY order_count DESC)`
# MAGIC    to assign a within-state rank.
# MAGIC 3. In the outer query, filter to `rank = 1`.
# MAGIC 4. Show `customer_state`, `customer_unique_id`, `order_count`, and `state_rank`.
# MAGIC
# MAGIC > **Olist gotcha (important):** group by **`customer_unique_id`**, NOT `customer_id`.
# MAGIC > In Olist, `customer_id` is generated **per order** (one row per order in `customers`),
# MAGIC > so counting orders by `customer_id` gives 1 for almost everyone. `customer_unique_id`
# MAGIC > is the persistent identity that lets you find true repeat customers (the busiest has 17 orders).
# MAGIC >
# MAGIC > *Note: `RANK()` assigns the same rank to ties, so a state may return several rows on a tie.*

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO F: top-ranked customer per state using RANK() OVER (PARTITION BY ...)
# MAGIC -- YOUR QUERY HERE

