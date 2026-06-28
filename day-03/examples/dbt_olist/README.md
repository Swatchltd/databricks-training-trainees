# dbt_olist — example dbt project

A complete, runnable dbt project on Databricks (Unity Catalog + SQL Warehouse).

```folder
models/
  staging/        stg_orders, stg_order_items, stg_order_payments, stg_customers, stg_products   (views)
  intermediate/   int_order_payments (view, rolls payments to order grain), int_orders_enriched (table)
  marts/          fct_orders (incremental merge), dim_customers, dim_products,
                  gld_revenue_by_category, gld_delivery_performance          (tables)
macros/           cast_timestamp, generate_category_label, generate_schema_name
seeds/            br_state_regions.csv
tests/            assert_no_future_orders (singular)
  generic/        not_in_future (custom generic test, reused in marts)
snapshots/        orders_snapshot (SCD2 on order_status)
```

Layout in every environment: `<catalog>.{staging,intermediate,marts,seeds,snapshots}.*`,
sources from `<catalog>.landing.*`. Only the **catalog** changes per environment (see §3).

> dbt merges all YAML under `models/`, so with multiple source systems you'd split sources
> one-file-per-source — `_<source>__sources.yml` (+ `_<source>__models.yml`, `stg_<source>__<entity>.sql`);
> our single `olist_landing` source uses one `_sources.yml`.

---

## 1. Environment (uv)

A dbt project is **not** a Python package, so the uv project is package-less: `pyproject.toml`
sets `[tool.uv] package = false` so `uv add`/`uv sync` never tries to build a wheel. (Seeing
*"Unable to determine which files to ship inside the wheel"*? That flag is missing.)

```bash
uv sync                  # install dbt-core + dbt-databricks from uv.lock
uv run dbt deps          # install packages.yml deps (dbt_utils, dbt_expectations)
```

From scratch: `uv init dbt_olist --python 3.12` (do **not** pass `--build-backend hatch`), then
`uv add dbt-core dbt-databricks`.

---

## 2. Credentials (.env)

`profiles.yml` holds **no secrets** — every value is an `env_var(...)` reference (including
`host`), so it's safe to commit. Real values live in a **gitignored** `.env`:

```bash
cp .env.example .env     # fill in your workspace + token
```

```bash
# .env.example — local block (the only one trainees fill)
DATABRICKS_HOST=adb-1234567890.11.azuredatabricks.net   # bare hostname, no https://
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/abc123         # SQL Warehouse > Connection details
DATABRICKS_TOKEN=dapiXXXXXXXX                            # PAT (local target only)
DBT_USER=han                                            # informational; catalog = training_<name>
```

The `dev`/`prod` service-principal vars stay commented in `.env.example` and live in the CI
secret store, never on a laptop.

**Loading it** — `env_var()` reads the OS environment, not `.env`, so load it first. Simplest is
to let uv do it per command; or export once into the shell:

```bash
uv run --env-file .env dbt build         # cross-platform, no sourcing
```

```bash
# macOS / Linux — export into the shell, then run dbt normally
set -a; source .env; set +a              # -a auto-exports everything it reads
```

```powershell
# Windows PowerShell — same idea
Get-Content .env | Where-Object { $_ -and $_ -notmatch '^\s*#' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
}
```

> Never commit `.env`. `.gitignore` already excludes `.env`/`.envrc` — add the token *after*.

---

## 3. profiles.yml — isolation by catalog (local / dev / prod)

Three targets, isolated by **catalog**; **schema names are identical everywhere**:

```yaml
target: local                # default — safe for training
local:  # PAT,   catalog = training_<name>   (your personal catalog)
dev:    # OAuth, catalog = dev_olist          (shared dev workspace)
prod:   # OAuth, catalog = prod_olist         (production)
```

The same model lands at `<catalog>.staging.*` / `.intermediate.*` / `.marts.*` — only the catalog
differs. Two pieces make that work:

1. `dbt_project.yml` does **not** hardcode a catalog — it inherits the active target's `catalog:`.
2. Sources use `catalog: "{{ target.catalog }}"`, so `landing` is read from that same catalog.
3. `macros/generate_schema_name.sql` keeps the per-folder `+schema` names clean (next section).

(`host`, `http_path`, credentials are all env vars, so one committed file serves everyone + CI.
`host` is the bare hostname — no `https://`, no path; `http_path` is separate.)

### How `generate_schema_name.sql` works

dbt calls `generate_schema_name(custom_schema_name, node)` **once per model** to decide the
schema it builds into. `custom_schema_name` is whatever the model's `+schema` config resolves to
(here: `staging`/`intermediate`/`marts`/`seeds`/`snapshots`), or `none` if a model sets nothing.

dbt's **default** macro *prefixes* that onto the target schema:

```
default:  custom is none  ->  target.schema                    # e.g. staging
          custom set      ->  target.schema _ custom           # e.g. staging_marts   <-- ugly
```

Our override returns the custom name **as-is**, so the prefix never happens:

```jinja
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}              {# models with no +schema -> the target's default #}
    {%- else -%}
        {{ custom_schema_name | trim }}  {# +schema used verbatim: staging / marts / ... #}
    {%- endif -%}
{%- endmacro %}
```

Worked example, model in `models/marts/` with `+schema: marts`, target `prod` (`schema: staging`):

| | `custom_schema_name` | default macro | our override |
|---|---|---|---|
| marts model | `marts` | `staging_marts` | **`marts`** |
| untagged model | `none` | `staging` | `staging` |

So the per-folder `+schema` *is* the final schema, identical across local/dev/prod; isolation
comes purely from the catalog. (This is why the profile's `schema: staging` is just a fallback for
any model that doesn't tag a layer.)

---

## 4. Run it — covering every feature

First time through, run these in order; each step exercises one part of the project:

```bash
uv run dbt deps                  # install packages.yml (dbt_utils, dbt_expectations)
uv run dbt debug                 # verify the warehouse connection
uv run dbt source freshness      # check landing freshness (loaded_at_field vs thresholds)
uv run dbt seed                  # load seeds/br_state_regions.csv  -> <catalog>.seeds.*
uv run dbt run                   # build models: staging views, intermediate, marts (incl. incremental)
uv run dbt snapshot              # SCD2 history -> <catalog>.snapshots.orders_snapshot
uv run dbt test                  # generic + singular + dbt_expectations tests
uv run dbt docs generate         # docs + lineage; exposures appear in the DAG
uv run dbt docs serve            # browse docs locally (http://localhost:8080)
```

Order matters: `deps` first (models/macros use the packages); `seed` before `run`
(`gld_delivery_performance` joins the seed); `run`/`snapshot` before `test`.

### The one-shot: `dbt build`

`dbt build` does **seed → run → snapshot → test** in a single dependency-ordered pass — it
builds each model then immediately tests it, and skips downstream models if an upstream test
fails. It's what CI and the Day 4 Job use. The only things it does **not** cover are
`source freshness` and `docs generate`:

```bash
uv run dbt deps
uv run dbt source freshness
uv run dbt build                 # seed + run + snapshot + test, dependency-ordered
uv run dbt docs generate
```

### Incremental & snapshots

- `fct_orders` builds a full table on the **first** run; run it again to exercise the incremental `merge` path.
- `dbt build --full-refresh` rebuilds tables from scratch — but **never** `--full-refresh` the snapshot (it wipes accumulated history).

### Exposures

Exposures aren't "run" — they're metadata. They surface in `dbt docs` (the
`olist_executive_dashboard` shows as a downstream node) and can be used as a selector to build
everything that feeds them:

```bash
uv run dbt build -s +exposure:olist_executive_dashboard
```

### Selective runs (handy for the demo)

```bash
uv run dbt run   -s stg_orders                            # one model
uv run dbt run   -s +fct_orders                           # a model and all its upstreams
uv run dbt build -s staging                               # everything in the staging folder
uv run dbt test  -s source:olist_landing                  # just source tests
uv run dbt build -s state:modified+ --defer --state ./prod  # Slim CI (Day 4)
```

---

## 5. Prod profile in CI/CD

Two patterns (full story on Day 4):

- **dbt runs on the CI runner** (e.g. Slim CI) — manage `profiles.yml` with `env_var()`, inject
  values from **GitHub Environment secrets**, authenticate with a **service principal (OAuth)**,
  never a personal PAT. Don't use a `.env` file in CI.
- **dbt runs as a Databricks Job (Asset Bundle)** — no `profiles.yml`; Databricks builds the
  connection from the job's `catalog`/`schema`/`warehouse_id` and runs as the bundle's `run_as`
  service principal. CI just runs `databricks bundle deploy/run`.

---

## Concepts demonstrated

sources + freshness · staging / intermediate / marts layers · `ref()` / `source()` ·
view vs table vs incremental (merge on Delta) · surrogate keys · seeds · generic + custom-generic + singular tests
+ `dbt_expectations` · macros (incl. `generate_schema_name`) · snapshots (SCD2) · exposures · docs.

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
