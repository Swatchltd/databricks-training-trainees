# Activity: Incremental Parquet → Medallion Pipeline with Auto Loader & Auto CDC

## Context

The Data team of an e-commerce marketplace asks you to build an ingestion pipeline for
customer orders. The data is available as **date-partitioned Parquet files**
(folder structure: `year=YYYY/month=M/day=D/`), dropped into a Databricks Volume over time.

The operational context is as follows:

- The **2016 and 2017** historical data is available upfront in the Volume
- A new year of data (**2018**) will be dropped into the Volume at a later stage,
  with **no changes to the pipeline code**
- The pipeline will be **re-run regularly** (daily trigger or manual) — this must never
  produce duplicate rows in the target tables

Your mission is to design and deploy this pipeline in SQL Lakeflow, following the
Bronze → Silver Medallion architecture.

---

## Data

### Retrieving data from the demo environment

The Parquet files are available in the Databricks demo environment at:

```
/Volumes/<catalog>/<schema>/sources/orders_parquet/
```

Schema of each file:

| Column                          | Type      | Description                        |
|---------------------------------|-----------|------------------------------------|
| `order_id`                      | STRING    | Unique order identifier            |
| `customer_id`                   | STRING    | Customer identifier                |
| `order_status`                  | STRING    | Status (`delivered`, `shipped`, …) |
| `order_purchase_timestamp`      | TIMESTAMP | Purchase date and time             |
| `order_approved_at`             | TIMESTAMP | Approval date                      |
| `order_delivered_carrier_date`  | TIMESTAMP | Handoff to carrier                 |
| `order_delivered_customer_date` | TIMESTAMP | Actual delivery to customer        |
| `order_estimated_delivery_date` | TIMESTAMP | Estimated delivery date            |

The partition columns `year`, `month`, `day` are automatically inferred from the folder
structure at ingestion time — no extra configuration needed.


> The 2018 data will be added in a second phase — see Step 4.

---

## Instructions

### Step 1 — Bronze layer: incremental ingestion with Auto Loader

Create a **Streaming Table** `brz_orders_parquet` that reads Parquet files from the
Volume using Auto Loader (`read_files`).

Requirements:
- Format: `parquet`
- Schema evolution enabled (`schemaEvolutionMode = addNewColumns`)
- Column `_source_file` tracked from `_metadata.file_path`
- Column `_ingestion_timestamp` capturing the ingestion moment
- Column `_rescued_data` for rows that do not conform to the inferred schema
- **Do not** pass `schemaLocation` or `checkpointLocation` manually

> **Reminder:** in a Lakeflow pipeline, the Auto Loader checkpoint is fully managed by
> the runtime. It is tied to the `pipeline_id` and stored in the pipeline's internal
> storage — no path configuration required.

---

### Step 2 — Silver layer: deduplication with Auto CDC

Create a **Streaming Table** `slv_orders_parquet` populated via an **Auto CDC** flow
(SCD Type 1).

Requirements:
- Key: `order_id`
- Sequence column: `order_purchase_timestamp`
- Explicit TIMESTAMP casts on all date columns
- Derived column `delivery_days`: actual delivery duration in calendar days
- Derived column `is_on_time`: boolean indicating whether delivery met the estimate
- Expectations:
  - `order_id IS NOT NULL` → `FAIL UPDATE`
  - `customer_id IS NOT NULL` → `DROP ROW`
  - `order_status` belongs to known values → warn only

> **Required architecture:** the Auto CDC engine cannot transform data — it can only
> select or exclude columns. Use an intermediate **Temporary View** to apply casts and
> derived columns before wiring up the CDC flow.

---

### Step 3 — First run: 2016 + 2017

Deploy and run the pipeline for the first time.

Verify:
- The row count in `brz_orders_parquet`
- That every `order_id` in `slv_orders_parquet` appears exactly once
- That `delivery_days` and `is_on_time` columns are present and correctly populated

**Re-run the pipeline a second time** without touching the Volume.
Verify that the row counts in both tables are unchanged.

---

### Step 4 — Add 2018 data and re-run

Drop the new year's files into the Volume.
Re-run the pipeline **without modifying any SQL file**:

Verify:
- Only the new 2018 rows were appended to `brz_orders_parquet`
- The 2016/2017 rows in `slv_orders_parquet` are unchanged
- The new 2018 `order_id` values have been correctly inserted into Silver

---

## Definition of Done

### Auto Loader (Bronze)

- [ ] The `brz_orders_parquet` table is a Streaming Table fed by `read_files`
      with `format => "parquet"`
- [ ] No `schemaLocation` or `checkpointLocation` is passed manually —
      the checkpoint is entirely managed by the Lakeflow runtime
- [ ] **After re-running on the same files**, the Bronze row count is identical to the
      first run — Auto Loader detected that the 2016/2017 files were already recorded
      in its checkpoint and skipped them
- [ ] **After dropping the 2018 files**, only the new rows appear in Bronze —
      proving the checkpoint tracks only previously unseen files
- [ ] The partition columns `year`, `month`, `day` are present in the table
      with no extra configuration (automatic Hive-style partition discovery)

### Auto CDC (Silver)

- [ ] The `slv_orders_parquet` table contains exactly **one row per `order_id`**
      regardless of how many times the pipeline has been run — uniqueness is enforced
      by the CDC key, not by manual deduplication downstream
- [ ] **After a replay on the same files**, no duplicate rows appear in Silver —
      Auto CDC resolved the conflict via `SEQUENCE BY` and wrote nothing new
- [ ] **After dropping the 2018 data**, only the new `order_id` values are inserted
      into Silver — the existing 2016/2017 rows are untouched
- [ ] The derived columns `delivery_days` and `is_on_time` are correctly computed
      (transformations applied in the Temporary View before the CDC flow)
- [ ] Expectations are visible in the **Data quality** tab of the pipeline UI

### Overall architecture

- [ ] The pipeline SQL code was **not modified** between the first run, the replay,
      and the run with 2018 data — the pipeline is generic by design, not by
      configuration
- [ ] There is no `WHERE year IN (2016, 2017)` or any hardcoded time filter
      in the SQL files

---
