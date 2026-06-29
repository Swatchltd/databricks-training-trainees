# Developing dbt on Databricks in VS Code — see query results without leaving the editor

The goal of this guide: write a model, hit a key, and see the **result rows inside VS Code** —
no jumping to the Databricks SQL editor, no `dbt run` + go-look-at-the-table loop.

**Recommended extension for this training: [dbt Power User](https://marketplace.visualstudio.com/items?itemName=innoverio.vscode-dbt-power-user) (by Altimate).**
The rest of this doc explains why, then walks through setup and daily use.

---

## 1. Why Power User and not the "official" dbt extension

dbt Labs ships an official VS Code extension, and it's good — but it has one hard requirement
that rules it out for us right now:

> **The official dbt extension only works with the dbt Fusion engine. It does *not* work with
> dbt Core.**

Our training stack is **dbt Core + dbt-databricks, managed with uv** (a plain `.venv`, the CLI,
`profiles.yml`). That's deliberate — it's the simplest, fully open-source setup. The official
extension would force us to migrate the projects onto Fusion *and* register a dbt platform
account (free for ≤15 users, but mandatory within 14 days). Fusion's Databricks adapter is
supported but the engine as a whole was still on its path-to-GA through 2026 — not what you want
under a room full of trainees.

Power User, by contrast, talks to **whatever dbt you already have** (Core, Cloud, or Fusion) by
using the Python interpreter you point it at. It runs against our uv `.venv` with zero changes to
the projects, and it gives us exactly the feature we're after: inline query-result previews.

| | **dbt Power User** (Altimate) | **Official dbt extension** (dbt Labs) |
|---|---|---|
| Works with **dbt Core** (our stack) | ✅ Yes | ❌ **No — Fusion engine only** |
| Works with our **uv `.venv` + dbt-databricks** | ✅ Yes, via interpreter selection | ❌ Requires migrating to Fusion |
| Inline **query-results preview** | ✅ `Cmd/Ctrl+Enter`, full model or selection | ✅ `Cmd/Ctrl+Enter` (Fusion only) |
| **Compiled SQL** side-by-side, live | ✅ | ✅ |
| **Column-level lineage** | ✅ | ✅ |
| Account / login required | No (core features); free Altimate login only for AI extras | Free dbt platform account, register within 14 days |
| Future-proof toward Fusion | ✅ Also supports Fusion when we adopt it | ✅ (it *is* the Fusion extension) |

**Bottom line:** Power User now, because it fits the dbt Core + uv stack we teach. When/if we move
the projects to the Fusion engine, revisit the official extension — Power User will keep working
either way, so there's no lock-in.

---

## 2. One-time setup (≈5 minutes)

Do this once per machine. The single most common failure — `ModuleNotFoundError: No module named
'dbt'` — is just step 4 not done: the extension is pointed at a Python that doesn't have dbt.

**1. Install the extensions.** In VS Code Extensions (`Cmd/Ctrl+Shift+X`):

- **Power User for dbt** (publisher: Altimate / innoverio)
- **Python** (publisher: Microsoft) — Power User uses it to find your dbt. Install if not already.

**2. Make sure the dbt env is built.** In a terminal, inside the dbt project
(`day-03/examples/dbt_olist`):

```bash
uv sync          # creates .venv with dbt-core + dbt-databricks
uv run dbt deps  # vendors dbt_utils / dbt_expectations (needed so Jinja compiles)
```

**3. Open the dbt project as your workspace folder.** Open `day-03/examples/dbt_olist` (the folder
that contains `dbt_project.yml`) — **not** the repo root (see §4 for why).

**4. Point Power User at the uv `.venv` — this is the key step.**
`Cmd/Ctrl+Shift+P` → **Python: Select Interpreter** → **Enter interpreter path…** → choose:

```
<your dbt project>/.venv/bin/python      # macOS / Linux
<your dbt project>\.venv\Scripts\python.exe   # Windows
```

> uv-created `.venv`s often don't appear in the auto-detected list, so use **"Enter interpreter
> path"** and browse to it manually.

**5. Reload.** `Cmd/Ctrl+Shift+P` → **Developer: Reload Window**. The Power User status bar (bottom)
should now show your dbt project name with no "dbt not found" error.

**6. Make your Databricks creds available to the extension.** Previews run dbt, and our
`profiles.yml` reads every value via `env_var()` (`DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH`,
`DATABRICKS_TOKEN`, `DBT_USER`). **Power User does not read your terminal** — running
`source .env` in the integrated terminal does nothing for it. Instead, Power User loads the file
pointed to by the Python extension's `python.envFile` setting, whose default is
**`${workspaceFolder}/.env`**. So two rules:

- **Put `.env` at the dbt project root** (next to `dbt_project.yml`) — copy it from `.env.example`.
- **Open that dbt project as your workspace folder** (see §4), so `${workspaceFolder}` *is* the
  project and the default `${workspaceFolder}/.env` resolves to it. If you instead open the
  repo root, Power User looks for `.env` at the repo root and you get
  `Env var required but not provided: 'DATABRICKS_HOST'`.

> **Format matters.** One `KEY=value` per line, **no inline `#` comments** — put any comment on its
> own line. The Python extension's `.env` parser keeps everything after `=`, so
> `DATABRICKS_HOST=adb-... # note` would store the comment as part of the host and the connection
> fails. (Bash `source` tolerates inline comments; this parser doesn't.)

After editing `.env`, **reload the window** (`Developer: Reload Window`). Verify it worked with
`Cmd/Ctrl+Shift+P` → **dbt Power User: Print environment variable** — you should see your
`DATABRICKS_*` values and where they came from.

**Prefer to keep the repo root open?** Point the setting at the project's `.env` explicitly in
`.vscode/settings.json`:

```json
{ "python.envFile": "${workspaceFolder}/day-03/examples/dbt_olist/.env" }
```

**Terminal / CLI path (`dbt show`, not the extension).** For command-line work, export `.env` into
the shell first:

```bash
# macOS / Linux
set -a; source .env; set +a
uv run dbt show --select my_model --limit 20
```

```powershell
# Windows PowerShell — equivalent of `set -a; source .env; set +a`
Get-Content .env | Where-Object { $_ -and $_ -notmatch '^\s*#' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
}
uv run dbt show --select my_model --limit 20
```

(This shell-export path *also* feeds the extension, but only if you fully **quit** VS Code and
relaunch it with `code .` from that same shell — shell vars take precedence over `.env`. The
`.env`-at-project-root method above is simpler and survives restarts.)

---

## 3. Daily workflow — see results inside VS Code

### Build the upstreams once
Previews run the model's **compiled SQL**, which reads from your already-built upstream tables.
So when you start on a model, build it and everything it depends on once:

```bash
uv run dbt build -s +my_model
```

Then iterate on `my_model` with instant previews — no full rebuilds needed.

### Preview the result rows
- Open the model `.sql` file → press **`Cmd+Enter`** (Mac) / **`Ctrl+Enter`** (Windows/Linux).
  Results open in a **Query Results** panel at the bottom.
- Or click the **▶ play** ("Execute dbt SQL") button in the top-right editor toolbar.
- **Preview just a piece:** select any SQL fragment first, then `Cmd/Ctrl+Enter` — it runs only
  the selection. Great for checking a single CTE or a join.

### Inspect, sort, export
In the Query Results panel you can:

- **SQL tab** — see and copy the exact SQL that was executed (Jinja already compiled).
- **Sort / scroll** the grid; click **configure** for display, zoom (fit more columns), read-only.
- **Export** to CSV, or **Copy** as CSV/JSON.
- **Compare results:** open results in a tab, change the query, re-run — Power User shows old vs new.
- Default preview limit is **500 rows** (adjustable in settings / the "Help" tab of the panel).

### Compiled SQL, live
Open the **compiled-code preview** to see the rendered SQL next to your Jinja-SQL; it updates as
you type, so you can confirm `ref()`/`source()`/macros resolve the way you expect.

### Other things you'll use
- **Preview CTEs** — a codelens to run an individual CTE's output.
- **Column-level lineage** — trace a column upstream/downstream without leaving the file.
- **Run ad-hoc SQL** — the Query Results tab has a "new query" box for scratch queries against the
  warehouse.

### Terminal fallback (always works, no extension)
If the panel ever misbehaves, the CLI gives you the same thing:

```bash
uv run dbt show --select my_model --limit 20
uv run dbt show --inline "select * from {{ ref('stg_orders') }} limit 20"
```

---

## 4. Open the dbt project, not the repo root

The dbt project lives in a subfolder (`day-03/examples/dbt_olist`), and its `.venv` and `.env` sit
**inside that folder**. Power User resolves both relative to the **workspace folder**: it picks up
the interpreter and reads `${workspaceFolder}/.env`.

So open **`day-03/examples/dbt_olist`** itself as the workspace folder (File → Open Folder), not the
repo root. If you open the repo root instead, `${workspaceFolder}/.env` points at the repo root
(where there's no `.env`) and previews fail with `Env var required but not provided`. If you really
want the repo root open, set `python.envFile` explicitly (see §2 step 6).

---

## 5. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'dbt'` | Extension pointed at a Python without dbt | §2 step 4 — select the project's `.venv/bin/python`, reload window |
| `Env var required but not provided: 'DATABRICKS_HOST'` | Repo root open as workspace folder, so `python.envFile` (`${workspaceFolder}/.env`) misses the project's `.env` | §2 step 6 — open `day-03/examples/dbt_olist` as the workspace folder (or set `python.envFile` to the project's `.env`); reload; verify with **dbt Power User: Print environment variable** |
| Connection works but host/auth looks wrong | Inline `#` comment in `.env` swallowed into the value | §2 step 6 — one `KEY=value` per line, comments on their own line |
| Jinja / `dbt_utils.*` won't compile | dbt packages not installed | `uv run dbt deps` in the project |
| Preview returns no rows / "relation not found" | Upstream models not built yet | `uv run dbt build -s +my_model` once, then preview |
| Wrong project / "dbt not found" in status bar | Repo root open / wrong interpreter | §4 — open `day-03/examples/dbt_olist`, reselect interpreter |
| Preview is slow | Cold / oversized SQL warehouse | Point the `local` target at a **small serverless** warehouse (auto-stop) |

---

## 6. When to revisit the official extension

Reconsider switching to the **official dbt (Fusion) extension** only if/when we deliberately
migrate these projects to the **dbt Fusion engine** and confirm the **Databricks adapter on Fusion
is GA** for our use. At that point the official extension's deep Fusion integration (catalog tab,
native LSP) becomes attractive. Until then, dbt Core + uv + **Power User** is the right call, and
Power User will continue to work even after a Fusion migration — so adopting it now costs us nothing.

---

### Sources
- Official dbt extension — Fusion-only, features, account requirement:
  [About the dbt VS Code extension](https://docs.getdbt.com/docs/about-dbt-extension) ·
  [dbt extension features](https://docs.getdbt.com/docs/dbt-extension-features) ·
  [Install & configure](https://docs.getdbt.com/docs/install-dbt-extension)
- Power User — query results, dbt Core support, setup:
  [Preview query results](https://help.altimate.ai/dbt-power-user/test/) ·
  [dbt Core required config](https://help.altimate.ai/setup/reqdConfig/) ·
  [Marketplace listing](https://marketplace.visualstudio.com/items?itemName=innoverio.vscode-dbt-power-user)
- Fusion / Databricks adapter status:
  [About Fusion](https://docs.getdbt.com/docs/fusion/about-fusion) ·
  [Path to GA](https://docs.getdbt.com/blog/dbt-fusion-engine-path-to-ga)
