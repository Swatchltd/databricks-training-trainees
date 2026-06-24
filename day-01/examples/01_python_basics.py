# Databricks notebook source

# MAGIC %md
# MAGIC # Day 1 · Demo 01 — Python Basics
# MAGIC
# MAGIC A complete, runnable walk-through of core Python concepts.
# MAGIC Every cell is fully worked — there are no TODOs. We use the **Olist** e-commerce dataset
# MAGIC (order statuses, review scores, state counts) for our example values, but this notebook
# MAGIC is **pure Python** — no Spark tables yet.
# MAGIC
# MAGIC > **Flow:** run each cell with `Shift + Enter` and talk through the printed output.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part A — Data Types
# MAGIC
# MAGIC Python's built-in types: `int`, `float`, `str`, `bool`, `list`, `dict`. `type()` inspects any value.

# COMMAND ----------

# Each Olist concept maps naturally to a Python type
order_count = 1500  # int   — number of orders in a batch
avg_order_value = 154.73  # float — average order value in BRL
current_status = "delivered"  # str   — a single order status
is_free_shipping = True  # bool  — whether free shipping applies

# list — every possible order status in the dataset (ordered, mutable)
order_statuses = ["delivered", "shipped", "canceled", "processing", "unavailable"]

# dict — map a status code to a human-readable description (key → value lookups)
status_descriptions = {
    "delivered": "Order successfully delivered to the customer",
    "shipped": "Order dispatched, in transit",
    "canceled": "Order was canceled before delivery",
}

print(f"order_count       {order_count!r:<12} -> {type(order_count).__name__}")
print(f"avg_order_value   {avg_order_value!r:<12} -> {type(avg_order_value).__name__}")
print(f"current_status    {current_status!r:<12} -> {type(current_status).__name__}")
print(f"is_free_shipping  {is_free_shipping!r:<12} -> {type(is_free_shipping).__name__}")
print(f"order_statuses    -> {type(order_statuses).__name__} with {len(order_statuses)} items")
print(f"status for 'shipped': {status_descriptions['shipped']}")

# COMMAND ----------

# MAGIC %md
# MAGIC We can also build a `state → order count` dict and inspect it with `len()` and `sum()`.

# COMMAND ----------

orders_by_state = {
    "SP": 41746,
    "RJ": 12852,
    "MG": 11635,
    "RS": 5466,
    "BA": 3380,
}

print(f"States tracked: {len(orders_by_state)}")
print(f"Total orders across these states: {sum(orders_by_state.values()):,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part B — Variables and Functions
# MAGIC
# MAGIC Functions use `def`, `return`, type hints, and a docstring. Default argument values make them flexible.

# COMMAND ----------

from datetime import datetime


def compute_delivery_days(
    order_purchase: str, order_delivered: str, date_fmt: str = "%Y-%m-%d %H:%M:%S"
) -> int:
    """Return the number of whole days between purchase and delivery.

    Args:
        order_purchase: Timestamp string of when the order was placed.
        order_delivered: Timestamp string of when the order was delivered.
        date_fmt: Format used to parse both timestamps.
    Returns:
        Delivery duration in whole days.
    """
    purchased = datetime.strptime(order_purchase, date_fmt)
    delivered = datetime.strptime(order_delivered, date_fmt)
    return (delivered - purchased).days


days = compute_delivery_days("2017-10-02 10:56:33", "2017-10-12 18:30:00")
print(f"Delivery took {days} days")

# COMMAND ----------

# MAGIC %md
# MAGIC A second function maps a review score (1–5) to a sentiment label using `if / elif / else`.

# COMMAND ----------


def categorize_review_score(score: int) -> str:
    """Bucket a review score (1-5) into 'negative', 'neutral', or 'positive'."""
    if score <= 2:
        return "negative"
    elif score == 3:
        return "neutral"
    else:  # 4 or 5
        return "positive"


for s in [1, 3, 5]:
    print(f"Score {s} -> {categorize_review_score(s)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part C — Loops and Conditionals
# MAGIC
# MAGIC A `for` loop iterates over a sequence; `if / elif / else` branches on each item.

# COMMAND ----------

for status in order_statuses:
    if status == "delivered":
        print(f"[OK]      '{status}' — no action needed.")
    elif status == "canceled":
        print(f"[ALERT]   '{status}' — trigger refund workflow.")
    elif status in ("shipped", "processing"):
        print(f"[INFO]    '{status}' — monitor for delays.")
    else:
        print(f"[UNKNOWN] '{status}' — investigate.")

# COMMAND ----------

# MAGIC %md
# MAGIC A `while` loop repeats until its condition becomes false — here, a simple retry counter.

# COMMAND ----------

attempts = 0
max_attempts = 3
while attempts < max_attempts:
    print(f"Attempt {attempts + 1}: connecting to data source...")
    attempts += 1
print("Done.")

# COMMAND ----------

# MAGIC %md
# MAGIC Looping over a dict with `.items()` plus a condition: print only states with more than 1,000 orders.

# COMMAND ----------

state_order_counts = {
    "SP": 45000,
    "RJ": 13000,
    "MG": 12000,
    "RS": 6500,
    "PR": 5800,
    "SC": 3200,
    "BA": 3100,
    "GO": 2100,
    "ES": 1800,
    "AM": 350,
}

print("States with more than 1000 orders:")
for state, count in state_order_counts.items():
    if count > 1000:
        print(f"  {state}: {count:,} orders")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part D — List Comprehensions and Built-ins
# MAGIC
# MAGIC List comprehensions filter/transform in one line; `sum/max/min/len/sorted` cover most numeric needs.

# COMMAND ----------

order_values = [23.50, 154.00, 89.99, 210.75, 45.00, 320.10, 67.30, 105.00, 9.99, 175.50]

high_value_orders = [v for v in order_values if v > 100]  # filter with a comprehension

print("High-value orders (>100):", high_value_orders)
print(f"Total high-value BRL:     {sum(high_value_orders):.2f}")
print(f"Largest single order:     {max(order_values)}")
print(f"Smallest single order:    {min(order_values)}")
print(f"Count of orders:          {len(order_values)}")
print("Sorted descending:        ", sorted(order_values, reverse=True))

# COMMAND ----------

# MAGIC %md
# MAGIC The same built-ins applied to review scores: average, max, min, and a descending-sorted copy.

# COMMAND ----------

review_scores = [4, 2, 5, 1, 3, 5, 4, 2]

avg_score = sum(review_scores) / len(review_scores)
max_score = max(review_scores)
min_score = min(review_scores)
sorted_scores = sorted(review_scores, reverse=True)

print(f"Average: {avg_score:.2f}")
print(f"Max:     {max_score}")
print(f"Min:     {min_score}")
print(f"Sorted:  {sorted_scores}")
print(f"5-star reviews: {len([s for s in review_scores if s == 5])}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part E — Dictionaries
# MAGIC
# MAGIC Safe reads with `.get()`, iteration with `.items()`, and sorting with `sorted(..., key=...)`.

# COMMAND ----------

category_counts = {
    "bed_bath_table": 11115,
    "health_beauty": 9672,
    "sports_leisure": 8641,
    "furniture_decor": 8334,
    "computers_accessories": 7827,
}

# .get() returns a default instead of raising KeyError on a missing key
print(f"sports_leisure count: {category_counts.get('sports_leisure')}")
print(f"automotive count (default 0): {category_counts.get('automotive', 0)}")

# Iterate over key/value pairs
print("\nAll categories:")
for category, cnt in category_counts.items():
    print(f"  {category}: {cnt:,}")

# Sort items by value (index 1) descending, take the top 3
top3 = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
print("\nTop 3 categories:", top3)

# COMMAND ----------

# MAGIC %md
# MAGIC A reusable function that sorts a `state → revenue` dict and returns the top-N as `(state, revenue)` tuples.

# COMMAND ----------


def top_states_by_revenue(state_revenue: dict, n: int = 3) -> list:
    """Return the top-n states by revenue, sorted descending, as (state, revenue) tuples."""
    return sorted(state_revenue.items(), key=lambda x: x[1], reverse=True)[:n]


state_revenue = {
    "SP": 5_432_100.50,
    "RJ": 1_987_430.20,
    "MG": 1_654_320.75,
    "RS": 892_100.00,
    "PR": 834_560.30,
}

print("Top 3 states by revenue:")
for rank, (state, revenue) in enumerate(top_states_by_revenue(state_revenue), start=1):
    print(f"  #{rank} {state}: R$ {revenue:,.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recap
# MAGIC
# MAGIC | Part | Topic | Key takeaway |
# MAGIC |------|-------|--------------|
# MAGIC | A | Data types | `dict` for lookups, `list` for ordered sequences; `type()` inspects |
# MAGIC | B | Functions | Type hints + docstrings make code self-documenting |
# MAGIC | C | Loops | `.items()` unpacks dicts; `{:,}` formats numbers with commas |
# MAGIC | D | Built-ins | `sum/max/min/len/sorted` cover most numeric work without imports |
# MAGIC | E | Dicts + sorting | `sorted(d.items(), key=lambda x: x[1])` is the idiomatic value-sort |
