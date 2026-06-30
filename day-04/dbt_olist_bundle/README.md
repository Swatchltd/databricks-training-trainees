# dbt_olist_bundle — the Olist dbt project as a Databricks bundle

The Day‑3 Olist dbt project wrapped as a **Declarative Automation Bundle (DAB)** — dbt‑only (no
Python/wheel tasks). It runs locally with `uv run dbt` and deploys to Databricks as a scheduled
**Job** via `databricks bundle`.

- **How it was built:** [`../CONVERT_DBT_TO_BUNDLE.md`](../CONVERT_DBT_TO_BUNDLE.md)
- **CI/CD (OAuth M2M):** [`../CICD_SETUP.md`](../CICD_SETUP.md) + [`../.github/workflows/`](../.github/workflows)
- **Editor setup:** [`VSCODE_DBT_SETUP.md`](VSCODE_DBT_SETUP.md) · **Data modelling:** [`DATA_MODELLING.md`](DATA_MODELLING.md)

```folder
dbt_olist_bundle/
  databricks.yml                 # bundle: name + targets (local/dev/prod) + per-target catalog/http_path vars
  resources/
    dbt_olist_bundle.job.yml     # the Job: one dbt task on a job cluster (dbt deps + build)
  dbt_project.yml                # name/profile = dbt_olist_bundle; *-paths point at src/
  profiles.yml                   # ONE profile; all targets read DBT_* env vars (injected in-job / .env locally)
  packages.yml  package-lock.yml # dbt_utils, dbt_expectations
  pyproject.toml  uv.lock        # local dev env (uv) + sqlfluff/sqlfmt config
  .env  .env.example             # local creds (gitignored)
  src/
    models/ staging/ intermediate/ marts/
    macros/ seeds/ snapshots/ tests/ (+ tests/generic/) analyses/
```

---

## 1. Local development (uv)

```bash
uv sync                       # dbt-core + dbt-databricks + sqlfluff/sqlfmt from uv.lock
uv run dbt deps               # vendor packages.yml (dbt_utils, dbt_expectations)
```

Credentials for **local** runs live in a gitignored `.env` (copy from `.env.example`). The profile
reads four variables — for local runs you supply all four; **in the deployed job they come from
Databricks/the bundle** (see §2):

```bash
DBT_HOST=adb-….azuredatabricks.net       # workspace host (bare, no https://)
DBT_ACCESS_TOKEN=dapiXXXX                 # your PAT (local only)
DBT_HTTP_PATH=/sql/1.0/warehouses/xxxx    # SQL Warehouse > Connection details
DBT_CATALOG=training_<you>                # your personal catalog
```

Load it, then run (target `local` is the default):

```bash
# macOS / Linux
set -a; source .env; set +a
uv run dbt build                          # seed + run + snapshot + test, building from src/
```

```powershell
# Windows PowerShell
Get-Content .env | Where-Object { $_ -and $_ -notmatch '^\s*#' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
}
uv run dbt build
```

---

## 2. profiles.yml — one profile, env‑driven

All three targets (`local` / `dev` / `prod`) authenticate identically (one YAML anchor); only the
**values** differ, and they come from the environment:

- **`DBT_HOST` + `DBT_ACCESS_TOKEN`** — **injected by Databricks** when dbt runs as a job task
  (`DBT_ACCESS_TOKEN` = the run‑as identity's OAuth token). Fixed names — don't rename. On the
  laptop you set them in `.env`.
- **`DBT_HTTP_PATH` + `DBT_CATALOG`** — supplied **per target by the bundle** via the job cluster's
  `spark_env_vars` (`databricks.yml` sets `${var.http_path}` / `${var.catalog}`). On the laptop,
  from `.env`.

So isolation is **by catalog** (`training_<you>` / `dev_olist` / `prod_olist`); schema names are
identical everywhere (the `+schema` configs + `generate_schema_name` macro handle that — §3).

---

## 3. How `generate_schema_name.sql` works

dbt calls `generate_schema_name(custom_schema_name, node)` once per model. `custom_schema_name` is
the model's `+schema` (`staging`/`intermediate`/`marts`/`seeds`/`snapshots`), or `none`.

dbt's **default** macro *prefixes* it onto the target schema (`staging_marts` — ugly). Our override
returns the custom name **as‑is**:

```jinja
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

So the per‑folder `+schema` *is* the final schema, identical across targets; only the **catalog**
(from `DBT_CATALOG`) differs. Sources read `catalog: "{{ target.catalog }}"`, which resolves to that
same `DBT_CATALOG`. The profile's `schema: staging` is just the fallback for an untagged model.

---

## 4. Deploy & run as a bundle

```bash
databricks bundle validate -t local
databricks bundle deploy   -t local       # development mode → job "[dev <you>] dbt_olist_bundle_job", runs as YOU
databricks bundle run dbt_olist_bundle_job -t local
```

- **`local`** (`mode: development`) — personal: resources prefixed `[dev <you>]`, schedule paused,
  runs as you, writes to your `training_<you>` catalog. Deploy this from your laptop to test on Databricks.
- **`dev` / `prod`** (`mode: production`) — shared, no prefix, schedule active, run as the deploying
  principal (the **M2M service principal** in CI). Normally deployed by GitHub Actions — see
  [`../CICD_SETUP.md`](../CICD_SETUP.md).

**Cleanup:** `databricks bundle destroy -t local` removes your personal `[dev <you>]` job and
resources when you're done, so they don't pile up in the shared dev workspace.

---

## Concepts demonstrated

sources + freshness · staging / intermediate / marts · `ref()` / `source()` · view vs table vs
incremental (merge on Delta) · surrogate keys · seeds · generic + custom‑generic + singular tests +
`dbt_expectations` · macros (incl. `generate_schema_name`) · snapshots (SCD2) · exposures · docs ·
**packaged as a DAB job with dev/prod CI/CD**.

## Code quality

Config lives in `pyproject.toml`; CI runs the same checks (see `../.github/workflows/pr_validation.yml`):

```bash
uv run sqlfmt .                     # 1. format in place — sqlfmt owns layout
uv run sqlfluff fix  src/models     # 2. auto-fix any semantic findings
uv run sqlfluff lint src/models     # 3. gate (semantics only; layout rules excluded)
```

SQLFluff uses the **dbt templater**, so `dbt_utils.*` / `dbt_expectations.*` / custom macros resolve
(run `uv run dbt deps` once). Ignore paths in `.sqlfluffignore` (incl. `src/tests/generic/`).
