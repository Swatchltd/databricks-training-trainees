# CI/CD for the dbt bundle — setup

Two GitHub Actions workflows under `.github/workflows/`, **dbt‑only** and **secret‑free** (GitHub
OIDC / workload‑identity federation). No Python checks, no Lakeflow, no release/versioning.

| Workflow | Trigger | What it does |
|---|---|---|
| `pr_validation.yml` | PR to `main` | `databricks bundle validate -t dev` + SQLFluff lint + sqlfmt format check |
| `deploy.yml` | push to `main` (and manual) | deploy + run on **dev**, then **prod** gated by the `prod` environment |

Promotion dev → prod is gated by **GitHub Environment approval** — not git tags or releases.

---

## 1. Databricks side (per environment: dev, prod)

1. Create a **service principal** (one for dev, one for prod).
2. Add a **workload‑identity federation policy** to each SP that trusts this GitHub repo and
   environment, e.g. subject `repo:<org>/<repo>:environment:dev` (and `:environment:prod`).
   → [Enable workload identity federation for GitHub Actions](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/provider-github)
3. Grant each SP what the job needs: workspace access, **Unity Catalog** rights on its catalog
   (`dev_olist` / `prod_olist`), and **CAN USE** on the SQL warehouse.
4. No client secret is created or stored — OIDC mints a short‑lived token at run time.

## 2. GitHub side

**Create two environments** — Settings → **Environments** → `dev` and `prod`. On **`prod`**, add
**required reviewers** so prod deploys wait for approval (this is the dev→prod gate).

**Add environment‑scoped secrets** — in each environment (Settings → Environments → `<env>` →
**Environment secrets**). Use the **same names** in both environments with **different values**; a
job that declares `environment: dev` sees the `dev` values, a job with `environment: prod` sees the
`prod` values. **No `_DEV`/`_PROD` suffix** — the environment does the scoping:

| Environment | Secret | Value |
|---|---|---|
| `dev`  | `DATABRICKS_HOST`      | `https://adb-7405611603719107.7.azuredatabricks.net` |
| `dev`  | `DATABRICKS_CLIENT_ID` | dev SP application id |
| `prod` | `DATABRICKS_HOST`      | `https://adb-prod.azuredatabricks.net` |
| `prod` | `DATABRICKS_CLIENT_ID` | prod SP application id |

Both `deploy.yml` and `pr_validation.yml` reference the **same** `${{ secrets.DATABRICKS_HOST }}` /
`${{ secrets.DATABRICKS_CLIENT_ID }}` — GitHub resolves each to the value from the job's environment.

> **Secret vs variable (a teaching point):** neither value is actually sensitive (a workspace URL and
> an app id), so they could just as well be **variables** (`vars.*`), which stay **unmasked in logs**
> and are easier to debug; secrets show as `***`. We use **environment secrets** here to demonstrate
> environment‑scoped secrets and the dev/prod environments.

## 3. How auth flows (important)

- **Deploy auth (CI → workspace):** GitHub OIDC. The workflow sets
  `DATABRICKS_AUTH_TYPE: github-oidc` + `DATABRICKS_HOST` + `DATABRICKS_CLIENT_ID`, and
  `permissions: id-token: write` lets the CLI exchange the OIDC token — **no credential secret**
  (no PAT, no `client_secret`). The host/client‑id we store as environment secrets in §2 are just
  config, not the auth token.
- **dbt runtime auth (job → warehouse):** the dbt task runs as a Databricks **job**, so Databricks
  injects `DBT_HOST` + `DBT_ACCESS_TOKEN` for the run‑as principal (the SP, in `mode: production`).
  This is **not** configured in CI or in `profiles.yml` beyond reading those injected vars.

## 4. Paths / assumptions

- The workflows use `working-directory: dbt_olist_bundle`, i.e. they assume the bundle sits at the
  **repo root**. If your real repo nests it (e.g. `day-04/dbt_olist_bundle`), update that path.
- GitHub only runs workflows from `.github/workflows/` at the **repo root**. These files live under
  `day-04/.github/workflows/` as the training artifact — move them to the repo root in a real repo.

## 5. Local equivalents (for trying the steps by hand)

```bash
databricks bundle validate -t dev
databricks bundle deploy   -t dev
databricks bundle run dbt_olist_bundle_job -t dev
```

SQL quality (same as the `sql-lint` job):

```bash
uv sync && uv run dbt deps
uv run sqlfluff lint src/models
uv run sqlfmt --check .
```

Sources: [Workload identity federation for GitHub Actions](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/provider-github) ·
[GitHub Actions CI/CD for Databricks](https://docs.databricks.com/aws/en/dev-tools/ci-cd/github).
