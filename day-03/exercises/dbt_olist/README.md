# dbt_olist — Day 3 Exercise (your starting point)

This **is** the `dbt_olist` project — an exact copy of the example backbone (staging → intermediate →
marts, with `fct_orders`, `dim_customers`, `dim_products`, snapshot, seed, tests). It builds green
as-is. **Your job:** add three new business-case models on top of it.

## 1. Get the backbone running

```bash
uv sync                              # dbt-core + dbt-databricks
uv run dbt deps                      # dbt_utils, dbt_expectations
cp .env.example .env                 # set DATABRICKS_HOST / HTTP_PATH / TOKEN
uv run --env-file .env dbt build     # the 11 backbone models + snapshot + seed + tests should pass
```

(Connection details, the medallion layering, `generate_schema_name`, and all concepts are documented
in the example project's README and the Day 3 slides.)

## 2. Your task — three business cases

Build each case as **new models inside this project**: add the staging you need to
`models/staging/`, an intermediate to `models/intermediate/` if it helps, and the gold mart to
`models/marts/`. Then test and document it.

Starter **stubs** and the full brief are in **`business_cases/`** (these sit outside `models/`, so
they don't affect the backbone build — copy/rename them into `models/…` as you implement):

| # | Case | Output (grain) |
|---|------|----------------|
| 1 | **Seller performance scorecard** | 1 row per seller: orders, revenue, avg delivery days, on-time %, avg review score |
| 2 | **Customer retention / cohorts** | 1 row per first-order month: customers, repeat rate, avg lifetime value (build on `dim_customers`) |
| 3 | **Review sentiment by category** | 1 row per English category: n_reviews, avg score, % 1-star, % 5-star (reuse `dim_products`) |

The `sellers` and `order_reviews` sources are already declared in `models/staging/_sources.yml`.

**"What good looks like":** rename/cast-only staging (views); a sensible materialization you can
justify; tests (not_null/unique keys, `accepted_values`, a `dbt_expectations` range, a singular
test); and descriptions. Full checklist in `business_cases/EXERCISE.md`.

## 3. Useful commands

```bash
uv run --env-file .env dbt build -s +gld_seller_scorecard   # build a model and its upstreams
uv run --env-file .env dbt test  -s gld_customer_cohorts
uv run --env-file .env dbt ls    -s +gld_seller_scorecard   # inspect lineage
uv run --env-file .env dbt docs generate && uv run --env-file .env dbt docs serve
```

The correct, best-practice implementation is in `../../solutions/dbt_olist/` (models integrated under
`models/`). Try it yourself first.

## Code quality

All tooling config lives in `pyproject.toml` (single source of truth); CI runs the same
checks on every PR.

**SQL** — [SQLFluff](https://sqlfluff.com) lints/gates and [sqlfmt](https://sqlfmt.com) formats:

```bash
uv sync                       # installs the dev tools from pyproject
uv run sqlfluff lint models   # lint (gate)
uv run sqlfluff fix models    # auto-fix lint violations
uv run sqlfmt .               # format SQL in place
```

SQLFluff uses the **dbt templater** so `dbt_utils.*`, `dbt_expectations.*` and the
custom macros resolve. Run `uv run dbt deps` once to vendor the dbt packages.

Config: `[tool.sqlfluff.*]` / `[tool.sqlfmt]` in `pyproject.toml`; ignore paths in
`.sqlfluffignore`.
