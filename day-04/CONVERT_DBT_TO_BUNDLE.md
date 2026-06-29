# Converting the Day‑3 dbt project into a Declarative Automation Bundle (DAB)

**Goal:** take the working Day‑3 dbt project (`dbt_olist`) and turn it into a Databricks bundle
that is structurally identical to what `databricks bundle init dbt-sql` generates
(`dbt_olist_bundle`) — `src/` layout, a `databricks.yml`, and a dbt Job in `resources/` — while
keeping **one** `profiles.yml` at the project root for both local development and the deployed job.

> **Why adapt instead of copy?** A bundle is just a **thin wrapper around an existing dbt project**.
> The init template's `src/` is an empty skeleton (`models/example` only); all the real value —
> staging/intermediate/marts, snapshots, generic tests, `persist_docs`, the `generate_schema_name`
> macro, `packages.yml`, sqlfluff config — already lives in Day‑3. So we start from the working
> project and bolt the bundle layer on, rather than rebuilding the project inside the skeleton.

**Naming decision:** everything will be called **`dbt_olist_bundle`** (project, profile, bundle,
job, folder). **Naming reconciliation is the #1 thing that breaks bundles** — see the checklist in
§8 and keep these in sync as you go.

---

## 0. Starting point

Two folders sit side by side in `day-04/`:

```
day-04/
  dbt_olist          <- copy of the Day-3 project (the thing we convert)  ← we edit THIS
  dbt_olist_bundle   <- output of `databricks bundle init dbt-sql`        ← reference only
```

We will transform `dbt_olist` into a bundle. The init `dbt_olist_bundle` is a **starting skeleton**
for the bundle files — but we don't ship its thin defaults; we **author `databricks.yml` and the job
resource to the best‑practice shape in §5**, and otherwise leave the dbt code untouched, just
relocated under `src/`.

At the end, rename the converted `dbt_olist` folder to `dbt_olist_bundle` (and delete/keep the
reference init folder as you like).

---

## 1. Target end‑state (what we're building toward)

```
dbt_olist_bundle/
  databricks.yml                     # bundle: name, targets (local/dev/prod), variables, artifacts — §5a
  resources/
    dbt_olist_bundle.job.yml         # the Job: best-practice DAG (dbt build → quality → export) — §5b
  dbt_project.yml                    # Day-3 content; name/profile=dbt_olist_bundle; paths → src/
  profiles.yml                       # SINGLE file: local (PAT) + dev/prod (job) targets
  packages.yml                       # Day-3 (dbt_utils, dbt_expectations)
  package-lock.yml                   # Day-3 (pinned package versions)
  pyproject.toml  uv.lock  .python-version   # Day-3 local dev via uv (+ sqlfluff/sqlfmt config)
  .sqlfluffignore                    # Day-3 (repath to src/)
  .env  .env.example                 # Day-3 local creds (gitignored)
  .gitignore
  src/
    models/  staging/ intermediate/ marts/    # moved from Day-3 models/
    macros/  cast_timestamp.sql generate_category_label.sql generate_schema_name.sql
    seeds/   br_state_regions.csv
    snapshots/ orders_snapshot.sql
    tests/   assert_no_future_orders.sql  generic/not_in_future.sql
    analyses/                                # (optional, empty)
  tasks/                             # (optional) uv package for the wheel DAG — §5b. Skip for a dbt-only job.
    pyproject.toml                   #   [project.scripts]: quality-check, export-report
    src/olist_tasks/…                #   the Python modules the wheel tasks call
  README.md  DATA_MODELLING.md  VSCODE_DBT_SETUP.md
```

---

## 2. Move the dbt files under `src/`

From inside `day-04/dbt_olist`, create `src/` and move the six dbt source folders into it. The dbt
**project root stays where it is** (`dbt_project.yml`, `profiles.yml`, `packages.yml` remain at the
top) — only the *source* directories move.

**macOS / Linux (bash/zsh):**

```bash
cd day-04/dbt_olist
mkdir -p src
mv models src/models
mv macros src/macros
mv seeds src/seeds
mv snapshots src/snapshots
mv tests src/tests
mkdir -p src/analyses              # optional; init creates it
```

**Windows (PowerShell):**

```powershell
cd day-04/dbt_olist
# 'src' already exists from earlier — skip 'mkdir src' if so
mv models src/models
mv macros src/macros
mv seeds src/seeds
mv snapshots src/snapshots
mv tests src/tests
mkdir src/analyses                 # no '-p' in PowerShell; parents are auto-created
```

> **Use plain `mv`, not `git mv`.** This copied project isn't tracked in git yet, so `git mv` fails
> with *"source directory is empty"* (it only moves files already in the git index). Plain `mv`
> works on both shells (in PowerShell `mv` is an alias for `Move-Item`, and `/` paths are fine);
> git records the moves when you later `git add` the converted bundle.

Nothing inside the SQL changes — `ref()`/`source()`/macros all resolve by name, not by path.

---

## 3. Repoint `dbt_project.yml` to `src/` and rename the project

Edit `dbt_project.yml`. Two kinds of change: (a) the **name/profile** → `dbt_olist_bundle`, and
(b) the **`*-paths`** → `src/…`. **Keep all your Day‑3 model config** (persist_docs, per‑layer
materializations + schemas, seeds, vars) — just note the `models:`/`seeds:` keys must use the new
project name.

```yaml
name: 'dbt_olist_bundle'          # was 'dbt_olist'
version: '1.0.0'
config-version: 2
profile: 'dbt_olist_bundle'       # was 'dbt_olist'  (must match the profiles.yml key in §4)

# point every path at src/ (this is the only reason the src/ layout "works")
model-paths:    ["src/models"]
macro-paths:    ["src/macros"]
test-paths:     ["src/tests"]
seed-paths:     ["src/seeds"]
snapshot-paths: ["src/snapshots"]
analysis-paths: ["src/analyses"]
target-path: "target"
clean-targets: ["target", "dbt_packages"]

models:
  dbt_olist_bundle:               # was 'dbt_olist'  ← rename this key
    +persist_docs:
      relation: true
      columns: true
    staging:      {+materialized: view,  +schema: staging}
    intermediate: {+materialized: view,  +schema: intermediate}
    marts:        {+materialized: table, +file_format: delta, +schema: marts}

seeds:
  dbt_olist_bundle:               # was 'dbt_olist'  ← rename this key
    +schema: seeds

vars:
  start_date: '2016-01-01'
```

---

## 4. Keep ONE `profiles.yml` at the project root (local + job)

This is the key consequence of the "single root profiles.yml" decision. dbt Core looks for
`profiles.yml` in this order: `--profiles-dir` → **the project root** → `~/.dbt/`. So a file at the
project root is picked up automatically for **local** dev. We'll make the **same file** serve the
**deployed job** by giving it `dev`/`prod` targets that use the credentials Databricks injects.

Rename the profile key to `dbt_olist_bundle` and split targets by purpose:

```yaml
dbt_olist_bundle:                 # was 'dbt_olist'  (must match dbt_project.yml `profile:`)
  target: local                   # default = safe local target

  outputs:
    # ---- LOCAL dev: personal PAT, runs from your laptop ----
    local:
      type: databricks
      host:      "{{ env_var('DATABRICKS_HOST') }}"        # bare hostname
      http_path: "{{ env_var('DATABRICKS_HTTP_PATH') }}"
      token:     "{{ env_var('DATABRICKS_TOKEN') }}"       # PAT (local only)
      catalog:   "training_{{ env_var('DBT_USER') }}"
      schema:    staging                                   # fallback; +schema sets the rest
      threads:   4

    # ---- DEPLOYED JOB (dev): Databricks injects DBT_HOST + DBT_ACCESS_TOKEN ----
    dev:
      type: databricks
      host:      "{{ env_var('DBT_HOST') }}"               # injected by the dbt task at runtime
      token:     "{{ env_var('DBT_ACCESS_TOKEN') }}"       # injected (Run-As principal's OAuth token)
      http_path: /sql/1.0/warehouses/xxxxxxxxxxxxxxxx      # YOUR SQL warehouse — set explicitly (see note); not a secret
      catalog:   dev_olist
      schema:    staging
      threads:   8

    # ---- DEPLOYED JOB (prod): same injection, prod catalog ----
    prod:
      type: databricks
      host:      "{{ env_var('DBT_HOST') }}"
      token:     "{{ env_var('DBT_ACCESS_TOKEN') }}"
      http_path: /sql/1.0/warehouses/xxxxxxxxxxxxxxxx      # YOUR SQL warehouse (can be a different one than dev)
      catalog:   prod_olist
      schema:    staging
      threads:   8
```

Two things to understand here — they map directly onto the **two CI/CD patterns** in your Day‑3
README §5:

- **Local** uses a **personal PAT** from `.env` (the "dbt from your laptop" pattern).
- **dev/prod** are the **"dbt as a Databricks Job"** pattern: you do *not* put any secret in the
  file. When the dbt task runs, Databricks injects **only** `DBT_HOST` and `DBT_ACCESS_TOKEN` for
  the job's **Run‑As** principal. (This replaces the Day‑3 service‑principal OAuth block, which was
  for the *other* pattern — dbt running on a CI runner.)
- ⚠️ **`http_path` is NOT injected** — only host + token are. So the warehouse path must be set
  explicitly (it's not a secret). Hardcode it in each target as shown — which is exactly what the
  init template does — or, to avoid hardcoding, define a bundle variable and pass it to the task as
  an environment variable. Grab the path from **SQL Warehouses → your warehouse → Connection
  details** (e.g. `/sql/1.0/warehouses/9fca341663cb3b8b`, the one the init bundle used).
- `catalog`/`schema`: the `schema:` here is only the fallback. Your `generate_schema_name` macro +
  per‑layer `+schema` still place models in `staging`/`intermediate`/`marts`; only the **catalog**
  differs per target. Keep `macros/generate_schema_name.sql` (now in `src/macros/`).

> Because we keep a single root file, **delete the init bundle's `dbt_profiles/` folder** — we won't
> use it (we repoint the job at the root file in §5).

---

## 5. Author the bundle files — best practices

`databricks bundle init dbt-sql` gives a *minimal* `databricks.yml` + a single‑task job. Don't ship
that as‑is — author the two files to the best‑practice shape below (the configuration we built and
validated in the Day‑4 example bundle). Shown **adapted to our choices**: `src/` layout + a single
root `profiles.yml`, so the dbt task uses `project_directory: ""` and `profiles_directory: .` (the
example itself uses split `dbt_profiles/`). The init bundle's files are a fine *starting skeleton* to
edit into this.

### 5a. `databricks.yml`

```yaml
bundle:
  name: dbt_olist_bundle

# include ONLY the active job. Two resources with the same job key collide, so keep any
# illustrative/alternative resource OUT of the glob (or give it a different key).
include:
  - resources/dbt_olist_bundle.job.yml

# Build downstream task code into a VERSIONED WHEEL from ./tasks. The dbt project stays
# package-less; only the Python tasks become a wheel. (Omit this block for a dbt-only job.)
artifacts:
  olist_tasks:
    type: whl
    build: uv build --wheel
    path: ./tasks

variables:
  catalog:
    description: "Unity Catalog catalog the gold tables live in"
    default: "training_${workspace.current_user.short_name}"

targets:
  local:                                   # deploy from YOUR laptop; the job runs as YOU
    mode: development                      # schedule paused; resources prefixed
    default: true
    workspace:
      host: https://adb-dev.azuredatabricks.net
    variables:
      catalog: "training_${workspace.current_user.short_name}"
    presets:
      name_prefix: "${workspace.current_user.short_name}_"   # personal deploys never collide
      trigger_pause_status: PAUSED
      tags:
        environment: "${bundle.target}"
        managed_by: dabs
    run_as: "${workspace.current_user.userName}"  # run as YOU, not the CI OIDC service principal
  dev:                                     # prod-like TEST env, deployed by CI (OIDC)
    mode: production                       # runs as the DEPLOYING principal; schedule active; no prefix
    workspace:
      host: https://adb-dev.azuredatabricks.net
    variables:
      catalog: "${bundle.target}_olist"
    presets:
      trigger_pause_status: UNPAUSED
      tags:
        environment: "${bundle.target}"
        managed_by: dabs
    # run_as: "${bundle.service_principal}"  # run as the CI OIDC service principal
  prod:
    mode: production
    workspace:
      host: https://adb-dev.azuredatabricks.net
    variables:
      catalog: "${bundle.target}_olist"
    presets:
      trigger_pause_status: UNPAUSED
      tags:
        environment: "${bundle.target}"
        managed_by: dabs
    # run_as: "${bundle.service_principal}"  # run as the CI OIDC service principal
```

Why these are the best‑practice choices:
- **`include` only the active job.** Globbing in a second resource that reuses the job key collides — keep illustrations out, or give them a unique key.
- **`mode: development` (local) vs `mode: production` (dev/prod).** Development prefixes resources (`[dev you]`) and pauses schedules so personal deploys are safe; production deploys clean with active schedules.
- **`run_as` is usually unnecessary.** With `mode: production` the job runs as the **deploying principal** — in CI that's your **OIDC service principal** (`DATABRICKS_CLIENT_ID`), whose token Databricks injects as `DBT_ACCESS_TOKEN`. Add an explicit `run_as` only to force a different identity.
- **`presets.name_prefix` on local** = your short name, so two people deploying `local` never clobber each other; **`presets.tags`** merge with resource‑level tags (cost/ownership attribution).
- **`variables.catalog` per target.** ⚠️ The catalog is *also* set in the **dbt profile** (where dbt writes). **Keep the two equal per target — especially `local`** — or the downstream wheel tasks read `${var.catalog}` while dbt wrote to a different catalog.

### 5b. `resources/dbt_olist_bundle.job.yml`

Best practice is a small **DAG** that exercises the three compute types. The two wheel tasks are
optional — see the minimal (dbt‑only) variant below.

```yaml
resources:
  jobs:
    dbt_olist_bundle_job:
      name: dbt_olist_bundle_job
      tags:
        managed_by: dabs
        data_source: olist                       # merges with target presets.tags
      schedule:
        quartz_cron_expression: "0 30 6 * * ?"    # 06:30 — paused in dev (mode preset), active in prod
        timezone_id: Europe/Zurich

      tasks:
        - task_key: dbt_build
          job_cluster_key: olist_job_cluster        # <-- attaches the classic cluster
          libraries:                                # <-- dbt installed HERE, on the task
            - pypi:
                package: dbt-databricks             # pulls a compatible dbt-core automatically
          dbt_task:
            project_directory: ""                   # bundle root (dbt_project.yml here)
            profiles_directory: .                   # single root profiles.yml
            commands:
              - "dbt debug"
              - "dbt deps"                          # deps ignores --target; it just reads packages.yml
              - "dbt build --target ${bundle.target}"

      job_clusters:
        - job_cluster_key: olist_job_cluster
          new_cluster:
            spark_version: 15.4.x-scala2.12       # current LTS
            node_type_id: Standard_F4s            # 4 cores, 8 GB
            num_workers: 0                        # 0 workers = single node
            # autoscale:                          # if there is a need for autoscale
            #   min_workers: 1
            #   max_workers: 2
            spark_conf:
              spark.databricks.cluster.profile: singleNode
              spark.master: "local[*]"
            custom_tags:
              ResourceClass: SingleNode

      email_notifications:
        on_failure: ["data-team@swatchgroup.example"]
```

Why:
- **Two computes, on purpose** (good slide): dbt CLI = **Job Compute**; model SQL = **SQL warehouse** (the profile's `http_path`, *not* a `warehouse_id` on the task)
- **`depends_on` builds the DAG** — the quality gate runs after `dbt_build` and fails the run before `export_report`.
- **`python_wheel_task`**: `entry_point` must match a `[project.scripts]` name in `tasks/pyproject.toml`; `package_name` = the wheel's `name`; `libraries: whl` = the `artifacts` output (`./tasks/dist/*.whl`).
- **`schedule`** = quartz cron + timezone; the target `mode` preset pauses it in dev, activates in prod.
- **No separate `dbt seed`** — `dbt build` already seeds (then runs, snapshots, tests). `source freshness`/`docs generate` aren't part of `build`; add them as extra commands if you want them in the job.

**Minimal variant (dbt‑only job):** if you're not adding the `tasks/` package, drop tasks 2 & 3, the
`job_clusters:` block, and the `artifacts:` block in `databricks.yml`. You're left with just
`dbt_build` + `environments` — a complete, working bundle.

### 5c. Git‑source instead of a wheel (alternative)

Rather than building/shipping a wheel, you can point tasks at code fetched from Git at run time
(`git_source:` on the job + `source: GIT` on the task; pin a `git_tag` for prod). It's an
**either/or** with the wheel — don't wire both into one job, and don't `include` two resources that
reuse the same job key. Databricks now recommends **workspace source** (the deployed bundle files)
over `git_source` for bundles, so prefer the wheel unless you specifically want the
monorepo/release‑branch flow.

---

## 6. Dependencies & tooling paths

- **Local dev = uv.** Keep `pyproject.toml` + `uv.lock` + `.python-version` as the source of truth
  for your laptop (`uv sync`, `uv run dbt …`). The init template's `requirements-dev.txt` is a
  *second* dependency source — **delete it** to avoid drift (or, if you want to keep it for non‑uv
  users, regenerate it from uv and keep it minimal).
- **sqlfluff / sqlfmt paths moved.** Update anything that referenced `models`/`tests`:
  - `.sqlfluffignore`: `tests/generic/` → `src/tests/generic/`
  - `pyproject.toml` `[tool.sqlfmt] exclude`: `tests/generic/**/*.sql` → `src/tests/generic/**/*.sql`
  - lint/format commands in docs: `sqlfluff lint models` → `sqlfluff lint src/models`
- **packages.yml / package-lock.yml**: keep both at the root, unchanged.
- **Wheel tasks (only if you use the DAG):** the `tasks/` package is its **own** uv project (own
  `pyproject.toml`); the bundle's `artifacts:` builds it on deploy (§5b). The dbt project itself
  stays package‑less.

---

## 7. `.gitignore` and cleanup

Make sure the bundle ignores generated state. Add (if missing) at the project root `.gitignore`:

```gitignore
target/
dbt_packages/
logs/
.venv/
.env
.user.yml
.databricks/          # bundle deploy state (created by the Databricks CLI)
```

Delete leftover build artifacts before validating:

```bash
# macOS / Linux
rm -rf target dbt_packages logs .databricks
```

```powershell
# Windows PowerShell (comma-separated paths; -rf is not valid here)
Remove-Item -Recurse -Force target, dbt_packages, logs, .databricks -ErrorAction SilentlyContinue
```

---

## 8. Naming reconciliation checklist (do this before validating)

All of these must read **`dbt_olist_bundle`** (the job/resource keys are cosmetic but keep them
consistent):

- [ ] `dbt_project.yml` → `name:` **and** `profile:`
- [ ] `profiles.yml` → top‑level profile key
- [ ] `dbt_project.yml` → `models:` key and `seeds:` key
- [ ] `databricks.yml` → `bundle.name`
- [ ] `resources/dbt_olist_bundle.job.yml` → filename, the job resource key, and `name:`
- [ ] the folder itself (rename `dbt_olist` → `dbt_olist_bundle` as the last step)

A mismatch here is the classic *"Could not find profile named 'dbt_olist_bundle'"* error.

---

## 9. Validate — local first, then the bundle

**A. Local dbt still works (run from the project root).** Only the `.env` loading differs by shell;
the `uv …` lines are identical.

```bash
# macOS / Linux
set -a; source .env; set +a          # load DATABRICKS_HOST / HTTP_PATH / TOKEN / DBT_USER
uv sync
uv run dbt deps
uv run dbt build                      # target=local by default; builds from src/ now
```

```powershell
# Windows PowerShell — load .env into the session, then the same uv commands
Get-Content .env | Where-Object { $_ -and $_ -notmatch '^\s*#' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
}
uv sync
uv run dbt deps
uv run dbt build
```

If this passes, the `src/` move + path repointing is correct.

**B. The bundle deploys and runs.** These `databricks` commands are **identical on macOS, Linux, and
PowerShell**:

```bash
databricks bundle validate            # catches path / naming / schema errors
databricks bundle deploy -t dev       # deploys the job to your workspace (uses your CLI auth)
databricks bundle run dbt_olist_bundle_job -t dev
```

`validate` is the cheap gate — run it after every edit in §3–§8. `run` executes the deployed dbt
task, where Databricks injects `DBT_HOST`/`DBT_ACCESS_TOKEN` and the `dev` target in `profiles.yml`
takes over.

> ⚠️ **`validate` does not read `profiles.yml` contents.** A placeholder warehouse `http_path`
> (e.g. `/sql/1.0/warehouses/<dev-warehouse-id>`) passes `validate` but the **`run` fails**. Put a
> real SQL‑warehouse id in the dev/prod targets first (§4).

---

## 10. Finish

```bash
# macOS / Linux / PowerShell — `mv` renames the folder on all three
cd day-04
mv dbt_olist dbt_olist_bundle_FINAL    # or overwrite the reference init folder, your call
```

Keep the original init `dbt_olist_bundle` around only if you want to diff against it; the converted
project is now the real bundle.

---

### What we deliberately did NOT do
- We did **not** rebuild the project inside the init skeleton (we'd have lost tests/snapshots/docs).
- We did **not** keep the template's split `dbt_profiles/` (single root file by choice).
- We did **not** change any SQL — only locations (`→ src/`) and config names.

### Sources
- [dbt task for jobs — Databricks](https://learn.microsoft.com/en-us/azure/databricks/jobs/dbt) (DBT_HOST / DBT_ACCESS_TOKEN injection)
- [Bundle project templates (dbt-sql)](https://docs.databricks.com/aws/en/dev-tools/bundles/templates) · [dbt integration in bundles](https://deepwiki.com/databricks/bundle-examples/5.3-dbt-integration)
- [About profiles.yml — lookup order](https://docs.getdbt.com/docs/local/profiles.yml)
- [Declarative Automation Bundles (renamed from Asset Bundles, Mar 2026)](https://docs.databricks.com/aws/en/dev-tools/bundles/)
