# Databricks notebook source

# MAGIC %md
# MAGIC # Day 1 — Exercise 01: Python Basics
# MAGIC
# MAGIC In this notebook you will practise core Python concepts using the Olist e-commerce dataset as context.
# MAGIC
# MAGIC Work through **Parts A–E** in order. Each part has:
# MAGIC 1. A short explanation
# MAGIC 2. A worked example you can run as-is
# MAGIC 3. A **TODO** exercise for you to complete
# MAGIC
# MAGIC > **Tip:** Run each cell with `Shift + Enter` before moving to the next one.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part A — Data Types
# MAGIC
# MAGIC Python's built-in types: `int`, `float`, `str`, `bool`, `list`, `dict`.
# MAGIC
# MAGIC We will use Olist order data as our running example.

# COMMAND ----------

# --- Example: common data types in the Olist context ---

# Integer: number of orders in a batch
order_count = 1500

# Float: average order value in BRL
avg_order_value = 154.73

# String: a single order status
current_status = "delivered"

# Boolean: whether free shipping applies
is_free_shipping = True

# List: all possible order statuses in the dataset
order_statuses = ["delivered", "shipped", "canceled", "processing", "unavailable", "approved", "invoiced", "created"]

# Dict: mapping a status to a human-readable description
status_descriptions = {
    "delivered": "Order successfully delivered to the customer",
    "shipped": "Order dispatched, in transit",
    "canceled": "Order was canceled before delivery",
    "processing": "Payment confirmed, preparing for shipment",
}

print("Order count:", order_count)
print("Average value:", avg_order_value)
print("Status list:", order_statuses)
print("Description for 'shipped':", status_descriptions["shipped"])

# COMMAND ----------

# TODO: Create a dict called `orders_by_state` that maps Brazilian state
#       abbreviations to a plausible number of orders (integers you invent).
#       Include at least five states: e.g. "SP", "RJ", "MG", "BA", "RS".
#
#       Then:
#         1. Print the full dict.
#         2. Print the number of states using len().

# YOUR CODE HERE


# COMMAND ----------

# MAGIC %md
# MAGIC ## Part B — Variables and Functions
# MAGIC
# MAGIC Key concepts: `def`, `return`, default argument values, calling functions.

# COMMAND ----------

# --- Example: compute delivery time in days ---

from datetime import datetime

def compute_delivery_days(order_purchase: str, order_delivered: str, date_fmt: str = "%Y-%m-%d %H:%M:%S") -> int:
    """
    Return the number of days between purchase and delivery.

    Parameters
    ----------
    order_purchase : str
        Timestamp string of when the order was placed.
    order_delivered : str
        Timestamp string of when the order was delivered.
    date_fmt : str
        Format used to parse both timestamps (default: '%Y-%m-%d %H:%M:%S').

    Returns
    -------
    int
        Delivery duration in whole days.
    """
    purchased = datetime.strptime(order_purchase, date_fmt)
    delivered = datetime.strptime(order_delivered, date_fmt)
    delta = delivered - purchased
    return delta.days

# Call the function
days = compute_delivery_days("2017-10-02 10:56:33", "2017-10-12 18:30:00")
print(f"Delivery took {days} days")

# COMMAND ----------

# TODO: Write a function called `categorize_review_score(score)` that accepts
#       an integer score (1–5) and returns a string category:
#         - score 1 or 2  -> "negative"
#         - score 3       -> "neutral"
#         - score 4 or 5  -> "positive"
#
#       After defining the function, test it by calling it with scores
#       1, 3, and 5, printing each result in the format:
#           "Score 1 -> negative"

# YOUR CODE HERE


# COMMAND ----------

# MAGIC %md
# MAGIC ## Part C — Loops and Conditionals
# MAGIC
# MAGIC Key concepts: `for` loops, `while` loops, `if / elif / else`.

# COMMAND ----------

# --- Example: iterate over order statuses and print a message ---

order_statuses = ["delivered", "shipped", "canceled", "processing", "unavailable"]

for status in order_statuses:
    if status == "delivered":
        print(f"[OK]      Order status '{status}' — no action needed.")
    elif status == "canceled":
        print(f"[ALERT]   Order status '{status}' — trigger refund workflow.")
    elif status in ("shipped", "processing"):
        print(f"[INFO]    Order status '{status}' — monitor for delays.")
    else:
        print(f"[UNKNOWN] Order status '{status}' — investigate.")

# COMMAND ----------

# --- Example: while loop — retry logic ---

attempts = 0
max_attempts = 3

while attempts < max_attempts:
    print(f"Attempt {attempts + 1}: connecting to data source...")
    attempts += 1

print("Done.")

# COMMAND ----------

# TODO: The dict `state_order_counts` below maps state abbreviations to
#       order counts.
#
#       Write a for loop that:
#         - Iterates over the dict using .items()
#         - Prints ONLY states with MORE than 1000 orders
#         - Output format: "SP: 45000 orders"

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
    "PE": 1600,
    "CE": 1200,
    "MT": 800,
    "DF": 950,
    "MS": 600,
    "AM": 350,
}

# YOUR CODE HERE


# COMMAND ----------

# MAGIC %md
# MAGIC ## Part D — List Comprehensions and Built-ins
# MAGIC
# MAGIC Key built-in functions: `sum()`, `max()`, `min()`, `len()`, `sorted()`.
# MAGIC List comprehensions offer a concise way to filter or transform lists.

# COMMAND ----------

# --- Example: filter order values above 100 BRL using a list comprehension ---

order_values = [23.50, 154.00, 89.99, 210.75, 45.00, 320.10, 67.30, 105.00, 9.99, 175.50]

high_value_orders = [v for v in order_values if v > 100]

print("All order values:   ", order_values)
print("High-value (>100):  ", high_value_orders)
print("Total high-value BRL:", sum(high_value_orders))
print("Largest single order:", max(order_values))
print("Smallest single order:", min(order_values))
print("Sorted descending:  ", sorted(order_values, reverse=True))

# COMMAND ----------

# TODO: Given the list of review scores below:
#   1. Compute the average score using sum() and len() — store it in `avg_score`
#   2. Find the maximum score — store it in `max_score`
#   3. Find the minimum score — store it in `min_score`
#   4. Create `sorted_scores`: the scores sorted in descending order
#   5. Print all four results with descriptive labels, e.g.:
#          "Average: 3.25"

review_scores = [4, 2, 5, 1, 3, 5, 4, 2]

# YOUR CODE HERE


# COMMAND ----------

# MAGIC %md
# MAGIC ## Part E — Dictionaries
# MAGIC
# MAGIC Key operations: create, read with `.get()`, iterate with `.items()`,
# MAGIC sort with `sorted()` and a `key=` function.

# COMMAND ----------

# --- Example: product category counts ---

category_counts = {
    "bed_bath_table": 11115,
    "health_beauty": 9672,
    "sports_leisure": 8641,
    "furniture_decor": 8334,
    "computers_accessories": 7827,
    "housewares": 6964,
    "watches_gifts": 5991,
    "telephony": 4545,
    "garden_tools": 4347,
    "toys": 4117,
}

# Safe access with .get() — returns None (or a default) if the key is missing
count = category_counts.get("toys")
missing = category_counts.get("automotive", 0)  # default 0

print(f"Toys count: {count}")
print(f"Automotive count (default): {missing}")

# Iterate and print all categories
print("\nAll categories:")
for category, cnt in category_counts.items():
    print(f"  {category}: {cnt}")

# Sort by count descending and take top 3
top3 = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
print("\nTop 3 categories:", top3)

# COMMAND ----------

# TODO: Write a function called `top_states_by_revenue(state_revenue_dict, n=3)`
#       that accepts:
#         - `state_revenue_dict`: a dict mapping state abbreviation (str) to
#           total revenue in BRL (float)
#         - `n`: how many top states to return (default 3)
#
#       The function should return a list of (state, revenue) tuples,
#       sorted by revenue descending, containing only the top `n` entries.
#
#       After defining the function, call it with the `state_revenue` dict
#       below (using the default n=3) and print the returned list.

state_revenue = {
    "SP": 5_432_100.50,
    "RJ": 1_987_430.20,
    "MG": 1_654_320.75,
    "RS": 892_100.00,
    "PR": 834_560.30,
    "SC": 567_890.10,
    "BA": 498_320.00,
    "GO": 345_670.80,
}

# YOUR CODE HERE

