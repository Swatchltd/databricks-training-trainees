# CI/CD for the dbt bundle — setup

Two GitHub Actions workflows, **dbt‑only**, authenticating with **OAuth M2M** — a service‑principal
**client id + client secret**. No Python checks, no Lakeflow, no release/versioning.

> **Where the workflows live (important):** GitHub only runs workflows from `.github/workflows/` at
> the **repo root**. The runnable ones are `.github/workflows/day04-deploy.yml` and
> `day04-pr-validation.yml` (with `working-directory: day-04/dbt_olist_bundle`, triggers scoped to
> `day-04/dbt_olist_bundle/**`). The copies under `day-04/.github/workflows/` are **illustrative
> only** — GitHub does **not** run a nested `.github/`.

| Workflow (repo root) | Trigger | What it does |
|---|---|---|
| `day04-pr-validation.yml` | PR to `main` touching `day-04/dbt_olist_bundle/**` | `databricks bundle validate -t dev` + SQLFluff lint + sqlfmt format check |
| `day04-deploy.yml` | push to `main` touching that path (and manual) | deploy + run on **dev**, then **prod** gated by the `prod` environment |

Promotion dev → prod is gated by **GitHub Environment approval** — not git tags or releases.

> **Why even the lint job needs dev access:** SQLFluff uses the **dbt templater**, which *compiles*
> models — and the incremental `fct_orders` checks whether its table exists, so it opens a real
> warehouse connection. The `sql-lint` job therefore also runs in the `dev` environment, **mints a
> token from the SP's client credentials** (`client_credentials` grant → `DBT_ACCESS_TOKEN`), and
> points dbt at the dev warehouse (read‑only metadata; the tables need not exist). So the dev SP's
> warehouse + `dev_olist` access from §1 is required for PR checks too, not just deploys.

---

## 1. Databricks side (per environment: dev, prod)

1. Create a **service principal** (one for dev, one for prod) at the **account** level.
2. **Generate an OAuth secret** for each SP: SP → **Credentials & secrets → OAuth secrets →
   Generate secret**. Copy the **client id** (the SP's application id) and the **secret** — both go
   into GitHub (§2). *(M2M uses a stored client secret; this replaces the earlier OIDC /
   workload‑identity‑federation policy, so there's no federation policy to configure.)*
3. **Add the SP to the workspace** it deploys to (the one in `databricks.yml`'s `host`, e.g.
   `7405611603719107` for dev): Account console → **Workspaces → \<workspace\> → Permissions → Add**.
   *(This is the membership the CLI checks — an account‑level SP can't touch a workspace it isn't a
   member of. This was the #1 gotcha during setup.)*
4. Grant each SP what the jobs need: **CAN USE** on the SQL warehouse, and **Unity Catalog** rights
   on its catalog (`dev_olist` / `prod_olist`) — read is enough for the lint job's relation check,
   create/write for the deploy job's `dbt build`.

## 2. GitHub side

**Create two environments** — Settings → **Environments** → `dev` and `prod`. On **`prod`** you
**must add "Required reviewers"** — this is the **manual review before prod**: the `deploy-prod` job
pauses with a *"Review deployments"* prompt and won't run until a reviewer approves (or rejects it).
⚠️ If you skip this, prod deploys automatically right after dev, with **no** review.

**Add environment‑scoped secrets** — in each environment (Settings → Environments → `<env>` →
**Environment secrets**). Same names in both environments, different values; the job's `environment:`
selects which set. **No `_DEV`/`_PROD` suffix** — the environment does the scoping:

| Environment | Secret | Value |
|---|---|---|
| `dev`  | `DATABRICKS_HOST`          | `https://adb-7405611603719107.7.azuredatabricks.net` |
| `dev`  | `DATABRICKS_CLIENT_ID`     | dev SP application id |
| `dev`  | `DATABRICKS_CLIENT_SECRET` | dev SP OAuth secret |
| `prod` | `DATABRICKS_HOST`          | `https://adb-prod.azuredatabricks.net` |
| `prod` | `DATABRICKS_CLIENT_ID`     | prod SP application id |
| `prod` | `DATABRICKS_CLIENT_SECRET` | prod SP OAuth secret |

> **Secret vs variable:** `DATABRICKS_CLIENT_SECRET` **is** sensitive — keep it a **secret**.
> `DATABRICKS_HOST` and `DATABRICKS_CLIENT_ID` aren't sensitive (a URL and an app id), so they could
> be **variables** (`vars.*`, which stay unmasked in logs); we keep all three as environment
> **secrets** for simplicity and consistent per‑environment scoping.

## 3. How auth flows

- **Deploy auth (CI → workspace):** **OAuth M2M.** The workflow sets `DATABRICKS_AUTH_TYPE: oauth-m2m`
  + `DATABRICKS_HOST` + `DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET`, and the Databricks CLI
  exchanges the client credentials for a short‑lived OAuth token. (No `id-token: write` permission —
  that was the OIDC approach.)
- **dbt in the deployed job (job → warehouse):** the dbt task runs as a Databricks **job**, so
  Databricks injects `DBT_HOST` + `DBT_ACCESS_TOKEN` for the run‑as principal (the SP, in
  `mode: production`). Not configured in `profiles.yml` beyond reading those vars.
- **dbt in the `sql-lint` job (runner → warehouse):** dbt runs *on the GitHub runner*, not as a job,
  so there's no injected token — the workflow mints one from the SP's client credentials
  (`curl … grant_type=client_credentials … /oidc/v1/token`) and exports it as `DBT_ACCESS_TOKEN`.

## 4. Paths / assumptions

- The runnable workflows (`day04-*.yml`) sit at the **repo root** `.github/workflows/` with
  `working-directory: day-04/dbt_olist_bundle`. The copies under `day-04/.github/workflows/` are
  illustrative and don't run.
- The `sql-lint` job hardcodes the dev warehouse path (`/sql/1.0/warehouses/3e5b6674e311a1ff`) and
  `dev_olist` — adjust if yours differ.

## 5. Local equivalents (for trying the steps by hand)

```bash
databricks bundle validate -t dev
databricks bundle deploy   -t dev
databricks bundle run dbt_olist_bundle_job -t dev
```

SQL quality (same as the `sql-lint` job):

```bash
uv sync && uv run dbt deps
uv run sqlfluff lint src/models src/tests src/snapshots
uv run sqlfmt --check .
```

Sources: [Authenticate with OAuth M2M (service principal)](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m) ·
[GitHub Actions CI/CD for Databricks](https://docs.databricks.com/aws/en/dev-tools/ci-cd/github).

Please follow this readme.md to learn CI/CD.