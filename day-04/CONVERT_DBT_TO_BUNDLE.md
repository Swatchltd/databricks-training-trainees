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
  databricks.yml                     # bundle: name, targets (local/dev/prod), presets/tags — §5a
  resources/
    dbt_olist_bundle.job.yml         # the Job: one dbt task on a job cluster (dbt build) — §5b
  dbt_project.yml                    # Day-3 content; name/profile=dbt_olist_bundle; paths → src/
  profiles.yml                       # SINGLE file: local/dev/prod all read injected/bundle env vars — §4
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
    staging: 
      +materialized: view
      +schema: staging
    intermediate:
      +materialized: view
      +schema: intermediate
    marts:
      +materialized: table
      +file_format: delta
      +schema: marts

seeds:
  dbt_olist_bundle:               # was 'dbt_olist'  ← rename this key
    +schema: seeds

vars:
  start_date: '2016-01-01'
```

---

## 4. Keep ONE `profiles.yml` at the project root (local + job)

This is the key consequence of the "single root profiles.yml" decision. dbt Core looks for
`profiles.yml` in this order: `--profiles-dir` → **the project root** → `~/.dbt/`, so a file at the
project root is picked up automatically.

The same file serves **both** local dev and the deployed job, because **all three targets
authenticate the same way** — so they share one YAML anchor. What differs per target (catalog,
warehouse, workspace) is supplied by the bundle (§5), not hardcoded here:

```yaml
dbt_olist_bundle:                 # must match dbt_project.yml `profile:`
  target: local
  outputs:
    # All three targets authenticate identically, so they share one YAML anchor.
    local: &databricks
      type: databricks
      method: http
      host:      "{{ env_var('DBT_HOST') }}"          # injected in-job; on laptop, set in .env
      token:     "{{ env_var('DBT_ACCESS_TOKEN') }}"  # injected in-job; on laptop, a PAT in .env
      http_path: "{{ env_var('DBT_HTTP_PATH') }}"     # supplied by the bundle (spark_env_vars, §5b)
      catalog:   "{{ env_var('DBT_CATALOG') }}"       # supplied by the bundle (spark_env_vars, §5b)
      schema:    staging                              # fallback; +schema sets the rest
      threads:   8
    dev:  *databricks
    prod: *databricks
```

Where the four env vars come from:

- **`DBT_HOST` + `DBT_ACCESS_TOKEN` — injected by Databricks**, with *exactly* those names, whenever
  dbt runs as a **job task** (`DBT_ACCESS_TOKEN` = the run‑as identity's OAuth token). You can't
  rename them — it's a Databricks convention (the `databricks bundle init dbt-sql` template's
  `dbt_profiles/profiles.yml` uses the same two).
- **`DBT_HTTP_PATH` + `DBT_CATALOG` — supplied by the bundle**, not injected. The job cluster's
  `spark_env_vars` export them per target (§5a sets the values, §5b wires them in). These two names
  are **arbitrary** — they only have to match between the job and this profile.
- **Laptop runs:** export all four in `.env` (`DBT_ACCESS_TOKEN` = a PAT), then
  `uv run dbt --target local` uses the identical profile. (See `.env.example`.)
- **`schema`** is only the fallback; your `generate_schema_name` macro + per‑layer `+schema` place
  models in `staging`/`intermediate`/`marts`. Keep `src/macros/generate_schema_name.sql`.

> Because we keep a single root file, **delete the init bundle's `dbt_profiles/` folder** — we won't
> use it (we repoint the job at the root file in §5).

---

## 5. Author the bundle files — best practices

`databricks bundle init dbt-sql` gives a *minimal* `databricks.yml` + a single‑task job. Don't ship
that as‑is — author the two files to the best‑practice shape below (the configuration we built and
validated in the Day‑4 example bundle). Shown **adapted to our choices**: `src/` layout + a single
root `profiles.yml`, so the dbt task uses `project_directory: ".."` and `profiles_directory: .`. The
init bundle's files are a fine *starting skeleton* to edit into this.

### 5a. `databricks.yml`

```yaml
bundle:
  name: dbt_olist_bundle

# include ONLY the active job. Two resources with the same job key collide, so keep any
# illustrative/alternative resource OUT of the glob (or give it a different key).
include:
  - resources/dbt_olist_bundle.job.yml

# catalog + http_path are exported to the dbt task as DBT_CATALOG / DBT_HTTP_PATH
# via the job cluster's spark_env_vars (§5b). They vary per target below.
variables:
  catalog:
    description: "Unity Catalog catalog dbt writes to"
    default: "training_${workspace.current_user.short_name}"
  http_path:
    description: "SQL warehouse HTTP path dbt connects to"
    default: /sql/1.0/warehouses/<dev-warehouse-id>

targets:
  local:                                   # developer deploys FROM laptop; tests ON Databricks
    mode: development                      # "[dev <you>]" prefix, schedule paused, runs as YOU
    default: true
    workspace:
      host: https://adb-<dev>.azuredatabricks.net
    variables:
      catalog: "training_${workspace.current_user.short_name}"   # YOUR personal catalog → isolated data
      http_path: /sql/1.0/warehouses/<dev-warehouse-id>
    presets:
      name_prefix: "${workspace.current_user.short_name}_"
      tags:
        environment: "${bundle.target}"
        managed_by: dabs
  dev:                                     # shared dev (no prefix), CI via OIDC
    mode: production                       # runs as the DEPLOYING principal (the OIDC SP in CI)
    workspace:
      host: https://adb-<dev>.azuredatabricks.net
    variables:
      catalog: "${bundle.target}_olist"    # → dev_olist
      http_path: /sql/1.0/warehouses/<dev-warehouse-id>
    presets:
      tags:
        environment: "${bundle.target}"
        managed_by: dabs
  prod:
    mode: production
    workspace:
      host: https://adb-<prod>.azuredatabricks.net   # prod workspace (different from dev)
    variables:
      catalog: "${bundle.target}_olist"    # → prod_olist
      http_path: /sql/1.0/warehouses/<prod-warehouse-id>
    presets:
      tags:
        environment: "${bundle.target}"
        managed_by: dabs
```

Why these are the best‑practice choices:
- **`include` only the active job.** Globbing in a second resource that reuses the job key collides — keep illustrations out, or give them a unique key.
- **`mode: development` (local) vs `mode: production` (dev/prod).** Development prefixes resources (`[dev <you>]`) and pauses schedules so personal deploys are safe; production deploys clean with active schedules. This is the "**with / without the username prefix**" knob.
- **`run_as` not set.** `mode: production` runs as the **deploying principal** — in CI that's the **OIDC service principal**; `mode: development` runs as you. Add an explicit `run_as` only to pin a different identity.
- **`presets.name_prefix` on local** = your short name, so two people deploying `local` never clobber each other; **`presets.tags`** merge with resource‑level tags.
- **`variables` (`catalog`, `http_path`) per target** are the single source for "where dbt writes" and "which warehouse." The job exports them to the dbt task as `DBT_CATALOG` / `DBT_HTTP_PATH` (§5b), and the profile just reads those — so `local` lands in your personal `training_<you>` catalog, `dev`/`prod` in `dev_olist`/`prod_olist`.

### 5b. `resources/dbt_olist_bundle.job.yml`

A single **dbt task** running on a classic **job cluster** — dbt‑only (no Python/wheel tasks, no
serverless environment).

```yaml
resources:
  jobs:
    dbt_olist_bundle_job:
      name: dbt_olist_bundle_job
      tags:
        managed_by: dabs
        data_source: olist                       # merges with target presets.tags
      schedule:
        quartz_cron_expression: "0 30 6 * * ?"    # 06:30 — paused for local, active for dev/prod (trigger_pause_status)
        timezone_id: Europe/Zurich

      tasks:
        - task_key: dbt_build
          job_cluster_key: olist_job_cluster        # <-- attaches the classic cluster
          libraries:                                # <-- dbt installed HERE, on the task
            - pypi:
                package: dbt-databricks             # pulls a compatible dbt-core automatically
          dbt_task:
            project_directory: ".."                 # up from resources/ to the BUNDLE ROOT (dbt_project.yml lives there)
            profiles_directory: "."                 # relative to project_directory → bundle root = our profiles.yml
            commands:
              - "dbt debug --target ${bundle.target}"   # use the deploy target, NOT the default 'local'
              - "dbt deps"                              # reads packages.yml; ignores --target
              - "dbt build --target ${bundle.target}"

      job_clusters:
        - job_cluster_key: olist_job_cluster
          new_cluster:
            spark_version: 15.4.x-scala2.12       # current LTS
            node_type_id: Standard_F4s            # 4 cores, 8 GB
            num_workers: 0                        # single node
            spark_conf:
              spark.databricks.cluster.profile: singleNode
              spark.master: "local[*]"
            spark_env_vars:                       # bundle vars → cluster env → dbt profile env_var()
              DBT_CATALOG:   "${var.catalog}"     # which UC catalog dbt writes to (per target)
              DBT_HTTP_PATH: "${var.http_path}"   # which SQL warehouse runs the model SQL
            custom_tags:
              ResourceClass: SingleNode

      email_notifications:
        on_failure: ["data-team@swatchgroup.example"]
```

Why:
- **`project_directory: ".."`** — paths in a resource file are relative to **that file** (`resources/`), so `..` climbs to the bundle root where `dbt_project.yml` lives. `""` would point at `resources/` and dbt would report *profiles.yml / dbt_project.yml not found*.
- **Two computes, on purpose** (good slide): the **dbt CLI** runs on the **job cluster**; the **model SQL** it generates runs on the **SQL warehouse** from the profile's `http_path` (*not* a `warehouse_id` on the task).
- **dbt installed on the task** via `libraries: pypi: dbt-databricks` (pulls a compatible `dbt-core`) — the **classic job‑cluster** pattern, no serverless `environments:` block. dbt **packages** (`dbt_utils`/`dbt_expectations`) still install at runtime via `dbt deps` (`packages.yml`).
- **`spark_env_vars` wire the bundle's per‑target values into dbt:** `DBT_CATALOG` / `DBT_HTTP_PATH` come from `${var.catalog}` / `${var.http_path}` (§5a) and are read by the profile's `env_var()` (§4). (`DBT_HOST`/`DBT_ACCESS_TOKEN` are injected by Databricks — don't set them here.)
- **`schedule`** = quartz cron + timezone; the target `mode` pauses it for `local` (development) and activates it for `dev`/`prod` (production).
- **Commands**: `dbt debug --target ${bundle.target}` (connect as the deploy target, not the default `local`) → `dbt deps` (reads `packages.yml`; ignores `--target`) → `dbt build --target ${bundle.target}` — `build` already runs seed + run + snapshot + test, so **no separate `dbt seed`**.

### 5c. Further reading (not used here)

We keep this bundle **dbt‑only** — no Python/wheel tasks and no Git‑sourced tasks. If you ever need
them, the docs cover it:

- **Pin a release for prod** — instead of deploying the working tree, point a job's tasks at a Git
  ref and pin a `git_tag` (e.g. `v0.1.0`) for prod while `dev` tracks a branch:
  [Run a job from Git / bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/) ·
  [dbt task for jobs](https://learn.microsoft.com/en-us/azure/databricks/jobs/dbt).
- **Python wheel tasks** — build & ship a wheel for non‑dbt steps via `artifacts` + `python_wheel_task`:
  [Python wheel in bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/python-wheel).

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
- **Job‑runtime dbt**: the deployed job installs `dbt-databricks` via the task's `libraries: pypi`
  (§5b) — not from your local uv env — and pulls dbt **packages** via `dbt deps` (`packages.yml`).

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
set -a; source .env; set +a          # load DBT_HOST / DBT_ACCESS_TOKEN / DBT_HTTP_PATH / DBT_CATALOG
uv sync
uv run sqlfmt .
uv run sqlfluff lint src/models src/tests src/snapshots
uv run sqlfluff fix src/models src/tests src/snapshots
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
uv run sqlfmt .
uv run sqlfluff lint src/models src/tests src/snapshots
uv run sqlfluff fix src/models src/tests src/snapshots
uv run dbt deps
uv run dbt build
```

If this passes, the `src/` move + path repointing is correct.

**B. The bundle deploys and runs.** These `databricks` commands are **identical on macOS, Linux, and
PowerShell**:

```bash
databricks bundle validate            # catches path / naming / schema errors
databricks bundle deploy -t local       # deploys the job to your workspace (uses your CLI auth)
databricks bundle run dbt_olist_bundle_job -t local
```

`validate` is the cheap gate — run it after every edit in §3–§8. `run` executes the deployed dbt
task, where Databricks injects `DBT_HOST`/`DBT_ACCESS_TOKEN`, the cluster's `spark_env_vars` supply
`DBT_HTTP_PATH`/`DBT_CATALOG`, and the matching profile target (here `local`) takes over.

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

## 11. CI/CD — deploy dev & prod via GitHub OIDC

Once the bundle deploys/runs by hand, automate it. The workflows live in
[`day-04/.github/workflows/`](.github/workflows) and the full setup is in
[`CICD_SETUP.md`](CICD_SETUP.md):

- **`pr_validation.yml`** — on a PR to `main`: `databricks bundle validate -t dev` + SQLFluff lint + sqlfmt check.
- **`deploy.yml`** — on push to `main`: deploy + run on **dev**, then **prod** gated by the `prod` GitHub Environment (required reviewers). No git tags / releases.

Two auth boundaries, kept separate (this is the part people conflate):

- **CI → workspace (deploy):** **GitHub OIDC**, secret‑free. The workflow sets
  `DATABRICKS_AUTH_TYPE: github-oidc` + `DATABRICKS_HOST` + `DATABRICKS_CLIENT_ID` (client id only)
  and `permissions: id-token: write`; the CLI exchanges the OIDC token. Configured **in the
  workflow, not `profiles.yml`**.
- **dbt → warehouse (runtime):** the injected `DBT_HOST`/`DBT_ACCESS_TOKEN` (§4) — the run‑as
  principal is the OIDC SP in `production` mode.

dbt‑only by design: **no Python checks, no Lakeflow, no release/versioning** workflow.

---

### What we deliberately did NOT do
- We did **not** rebuild the project inside the init skeleton (we'd have lost tests/snapshots/docs).
- We did **not** keep the template's split `dbt_profiles/` (single root file by choice).
- We did **not** change any SQL — only locations (`→ src/`) and config names.
- We kept it **dbt‑only** — no Python/wheel tasks, no serverless environment, no Git‑sourced tasks (see §5c for pointers).

### Sources
- [dbt task for jobs — Databricks](https://learn.microsoft.com/en-us/azure/databricks/jobs/dbt) (DBT_HOST / DBT_ACCESS_TOKEN injection)
- [Bundle project templates (dbt-sql)](https://docs.databricks.com/aws/en/dev-tools/bundles/templates) · [dbt integration in bundles](https://deepwiki.com/databricks/bundle-examples/5.3-dbt-integration)
- [About profiles.yml — lookup order](https://docs.getdbt.com/docs/local/profiles.yml)
- [Declarative Automation Bundles (renamed from Asset Bundles, Mar 2026)](https://docs.databricks.com/aws/en/dev-tools/bundles/)
