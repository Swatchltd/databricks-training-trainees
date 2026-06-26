# Databricks notebook source
# MAGIC %md
# MAGIC # Exercise 04: Dataset Exploration
# MAGIC
# MAGIC In this exercise you will explore the **Olist e-commerce dataset** to answer real business questions.
# MAGIC
# MAGIC You are free to use **SQL** (`%sql` cells) or **PySpark** — or both. There is no single correct approach.
# MAGIC
# MAGIC **Catalog:** `training_<name>` | **Schema:** `landing`
# MAGIC
# MAGIC **Available tables:**
# MAGIC - `orders` — order lifecycle and timestamps
# MAGIC - `order_items` — products and prices per order
# MAGIC - `customers` — customer location data
# MAGIC - `products` — product metadata and category
# MAGIC - `sellers` — seller location data
# MAGIC - `order_reviews` — customer review scores and comments
# MAGIC - `order_payments` — payment type and value
# MAGIC - `geolocation` — zip code to lat/lng mapping
# MAGIC - `product_category_name_translation` — Portuguese to English category names
# MAGIC
# MAGIC Work through each question below. Try to interpret the results — what do they tell you about the business?

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ## Question 1: Order Status Distribution
# MAGIC
# MAGIC **How many orders are in each status?** (delivered, shipped, canceled, etc.)
# MAGIC
# MAGIC **Hints:**
# MAGIC - Table: `orders`
# MAGIC - Relevant column: `order_status`
# MAGIC - Use `COUNT(*)` grouped by `order_status`

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TODO: Count orders per status and display the results
# MAGIC -- your code here
# MAGIC select order_status, count(*) as count from training_andrea_licastro.bronze.orders group by order_status order by count desc

# COMMAND ----------

orders = spark.table("training_andrea_licastro.bronze.orders")
grouped_orders = orders.groupBy("order_status").count().orderBy("count", ascending=False)
display(grouped_orders)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Question 2: Average Delivery Time
# MAGIC
# MAGIC **What is the average delivery time in days** — from `order_purchase_timestamp` to `order_delivered_customer_date`?
# MAGIC
# MAGIC **Hints:**
# MAGIC - Table: `orders`
# MAGIC - Filter out rows where `order_delivered_customer_date` is NULL (undelivered orders)
# MAGIC - SQL: `DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)`
# MAGIC - PySpark: `F.datediff(F.col("order_delivered_customer_date"), F.col("order_purchase_timestamp"))`
# MAGIC - Take the `AVG()` of that difference

# COMMAND ----------

# TODO: Calculate the average delivery time in days across all delivered orders
# your code here
orders.agg(F.avg(F.datediff('order_delivered_customer_date', 'order_purchase_timestamp')).alias('avg')).show()

# COMMAND ----------

# MAGIC %sql
# MAGIC select AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)) as avg
# MAGIC from training_andrea_licastro.bronze.orders
# MAGIC where order_delivered_customer_date is not null

# COMMAND ----------

# MAGIC %md
# MAGIC ## Question 3: Revenue by Product Category
# MAGIC
# MAGIC **Which product categories generate the most total revenue? Show the top 10.**
# MAGIC
# MAGIC **Hints:**
# MAGIC - Join `order_items` with `products` on `product_id`
# MAGIC - Revenue = `SUM(price)`
# MAGIC - Group by `product_category_name`
# MAGIC - Sort descending, limit to 10
# MAGIC - Note: some category names may be NULL — you can include or exclude them

# COMMAND ----------

# TODO: Top 10 product categories by total revenue
# your code here
order_items = spark.table("training_andrea_licastro.bronze.order_items")
products = spark.table("training_andrea_licastro.bronze.products")
product_order_items = products.join(order_items, on='product_id')
display(product_order_items.groupBy('product_category_name').agg(F.round(F.sum(order_items.price), 2).alias('sum_price')).orderBy(F.desc('sum_price')).limit(10))

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT product_category_name, round(sum(price),2)
# MAGIC from training_andrea_licastro.bronze.order_items as I
# MAGIC inner JOIN training_andrea_licastro.bronze.products as P
# MAGIC on I.product_id = P.product_id
# MAGIC group by product_category_name
# MAGIC order by sum(price) desc
# MAGIC LIMIT 10

# COMMAND ----------

# MAGIC %md
# MAGIC ## Question 4: Review Score Distribution
# MAGIC
# MAGIC **What is the distribution of review scores (1–5)?** How many orders received each score?
# MAGIC
# MAGIC **Hints:**
# MAGIC - Table: `order_reviews`
# MAGIC - Relevant column: `review_score`
# MAGIC - Group by `review_score`, count rows, sort by score ascending

# COMMAND ----------

# TODO: Distribution of review scores — count per score value
# your code here
order_reviews = spark.table("training_andrea_licastro.bronze.order_reviews")
display(order_reviews.groupBy('review_score').count().orderBy('review_score'))

# COMMAND ----------

# MAGIC %sql
# MAGIC Select review_score, count(*) as count  from training_andrea_licastro.bronze.order_reviews
# MAGIC group by review_score
# MAGIC order by review_score

# COMMAND ----------

# MAGIC %md
# MAGIC ## Question 5: Late Delivery Rate by State
# MAGIC
# MAGIC **Which customer states have the highest late delivery rate?**
# MAGIC
# MAGIC A delivery is **late** when `order_delivered_customer_date > order_estimated_delivery_date`.
# MAGIC
# MAGIC **Hints:**
# MAGIC - Join `orders` with `customers` on `customer_id`
# MAGIC - Filter to orders with `order_status = 'delivered'` and non-NULL delivered/estimated dates
# MAGIC - Create an `is_late` flag: 1 if late, 0 otherwise
# MAGIC   - SQL: `CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END`
# MAGIC   - PySpark: `F.when(F.col(...) > F.col(...), 1).otherwise(0)`
# MAGIC - Aggregate by `customer_state`:
# MAGIC   - `late_rate = SUM(is_late) / COUNT(*) * 100`
# MAGIC - Sort descending by late_rate

# COMMAND ----------

# TODO: Late delivery rate per customer state, sorted by highest rate first
# your code here
customers = spark.read.table("training_andrea_licastro.bronze.customers")
orders = spark.table("training_andrea_licastro.bronze.orders")
customers_delivered_late_orders = customers.join(orders, on='customer_id').filter(orders.order_status == 'delivered').filter(~(orders.order_delivered_customer_date.isNull())).filter(~(orders.order_estimated_delivery_date.isNull())).select('customers.customer_state', F.when(F.col('order_delivered_customer_date') > F.col('order_estimated_delivery_date'), 1).otherwise(0).alias('late_delivery_flag'))


display(customers_delivered_late_orders.groupby('customer_state').agg((F.round(F.sum('late_delivery_flag')/F.count('late_delivery_flag')*100,2)).alias('late_rate')).orderBy(F.desc('late_rate')))


# COMMAND ----------

# MAGIC %sql
# MAGIC with late_orders as (
# MAGIC Select customer_state,
# MAGIC CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END as is_late
# MAGIC from training_andrea_licastro.bronze.orders as O 
# MAGIC inner join training_andrea_licastro.bronze.customers  C on C.customer_id = O.customer_id
# MAGIC
# MAGIC
# MAGIC  where order_status = 'delivered'
# MAGIC and order_estimated_delivery_date is not null
# MAGIC and order_estimated_delivery_date is not null
# MAGIC )
# MAGIC select customer_state, round((sum(is_late)/count(*)) * 100,2)  as late_Rate from late_orders
# MAGIC group by customer_state
# MAGIC order by late_Rate desc

# COMMAND ----------

# MAGIC %md
# MAGIC ## Question 6 (Bonus): Most Popular Payment Type by State
# MAGIC
# MAGIC **What is the most popular payment type in each customer state?**
# MAGIC
# MAGIC **Hints:**
# MAGIC - Join `orders`, `customers`, and `order_payments` (join key: `order_id` for payments, `customer_id` for customers)
# MAGIC - Count occurrences of each `payment_type` per `customer_state`
# MAGIC - Keep only the payment type with the **highest count** per state
# MAGIC - SQL approach: use a subquery or CTE to rank payment types per state, then filter to rank = 1
# MAGIC - PySpark approach: use a Window function with `F.rank()` or `F.row_number()` partitioned by `customer_state`, ordered by count descending

# COMMAND ----------

from pyspark.sql.window import Window

joined = orders.join(customers, on="customer_id").join(order_payments, on="order_id")
payment_counts = joined.groupBy("customer_state", "payment_type").count()

window_spec = Window.partitionBy("customer_state").orderBy(F.desc("count"))
ranked = payment_counts.withColumn("rn", F.row_number().over(window_spec))
most_popular = ranked.filter(F.col("rn") == 1).select("customer_state", "payment_type", "count")

display(most_popular.orderBy("customer_state"))

# COMMAND ----------

orders_payment = spark.table("training_andrea_licastro.bronze.order_payments")


# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC WITH payment_counts AS (
# MAGIC   SELECT
# MAGIC     c.customer_state,
# MAGIC     p.payment_type,
# MAGIC     COUNT(*) AS payment_count
# MAGIC   FROM training_andrea_licastro.bronze.orders o
# MAGIC   INNER JOIN training_andrea_licastro.bronze.customers c ON o.customer_id = c.customer_id
# MAGIC   INNER JOIN training_andrea_licastro.bronze.order_payments p ON o.order_id = p.order_id
# MAGIC   GROUP BY c.customer_state, p.payment_type
# MAGIC ),
# MAGIC ranked_payments AS (
# MAGIC   SELECT
# MAGIC     customer_state,
# MAGIC     payment_type,
# MAGIC     payment_count,
# MAGIC     ROW_NUMBER() OVER (PARTITION BY customer_state ORDER BY payment_count DESC) AS rn
# MAGIC   FROM payment_counts
# MAGIC )
# MAGIC SELECT
# MAGIC   customer_state,
# MAGIC   payment_type,
# MAGIC   payment_count
# MAGIC FROM ranked_payments
# MAGIC WHERE rn = 1
# MAGIC ORDER BY customer_state

# COMMAND ----------

# MAGIC %sql
# MAGIC with counts as (
# MAGIC     select C.customer_state, P.payment_type , count(*) as counted from
# MAGIC     training_andrea_licastro.bronze.orders as O 
# MAGIC     inner join training_andrea_licastro.bronze.customers  C on C.customer_id = O.customer_id
# MAGIC     inner join training_andrea_licastro.bronze.order_payments P on p.order_id = O.order_id
# MAGIC     GROUP BY C.customer_state, P.payment_type
# MAGIC )
# MAGIC select customer_state, row_number() over (partition by customer_state,payment_type order by counted desc) as rank, payment_type, counted from counts
# MAGIC
# MAGIC
