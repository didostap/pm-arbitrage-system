<!-- Powered by BMAD-CORE -->

# QA Verification

**Workflow ID**: `{project-root}/_bmad/tea/testarch/bmad-testarch-verify`
**Version**: 1.0 (Step-File Architecture)

---

## Overview

Performs post-implementation QA verification against a running application. Unlike test generation workflows (ATDD, Automate), this workflow interacts with the live application — navigating the UI via Playwright MCP, hitting REST endpoints, querying the database, and inspecting logs — to verify that acceptance criteria are met.

Two verification modes:

- **Story Mode**: Loads a story file, extracts acceptance criteria, and systematically verifies each AC
- **Exploratory Mode**: User describes an area to test; agent discovers and exercises functionality

---

## TOOL INTEGRATION

This workflow uses multiple MCP tools and system capabilities:

### Playwright MCP (Browser Automation)

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Navigate to app pages |
| `browser_snapshot` | Capture accessibility tree for element interaction |
| `browser_click` / `browser_type` / `browser_fill_form` | Interact with UI elements |
| `browser_take_screenshot` | Capture visual evidence (use `filename` parameter for file output) |
| `browser_verify_text_visible` / `browser_verify_element_visible` | Assert UI state |
| `browser_console_messages` | Check for JS errors and warnings |
| `browser_network_requests` | Monitor API calls made by the UI |
| `browser_evaluate` | Execute JS (e.g., `fetch()` for API calls) |
| `browser_run_code` | Run full Playwright scripts (e.g., `page.request.get()` for REST testing) |

### Postgres MCP (Database Verification)

| Tool | Purpose |
|------|---------|
| `execute_sql` | Query database state to verify data integrity |
| `explain_query` | Analyze query performance if relevant |

### System Tools (Logs & API)

| Tool | Purpose |
|------|---------|
| Bash `curl` | Direct REST endpoint testing |
| Read / Grep | Inspect server log file, trade CSVs, source code |
| Bash `docker logs` | Container log inspection (if Docker) |

---

## LOG ACCESS TIERS

The workflow accesses server information through three tiers:

1. **CSV Trade Logs** — `{engine_dir}/data/trade-logs/trades-YYYY-MM-DD.csv` — persistent trade execution data
2. **Application Stdout** — `{engine_dir}/server.log` (requires starting server with `pnpm start:dev 2>&1 | tee server.log`) — HTTP logs, errors, correlationIds
3. **Database Audit Logs** — PostgreSQL `audit_log` table — full event history with cryptographic chain
4. **Browser Console** — Playwright `browser_console_messages` — frontend JS errors and warnings

---

## SCREENSHOT HANDLING

Screenshots are saved as real PNG files using `browser_take_screenshot` with the `filename` parameter:

```
browser_take_screenshot(
  type: "png",
  filename: "{report_dir}/screenshot-{NN}-{description}.png"
)
```

Naming convention: `screenshot-{sequential-number}-{kebab-case-description}.png`

The QA report references screenshots with relative paths: `![Description](screenshot-01-dashboard-overview.png)`

**Important:** Create the report directory before taking screenshots — Playwright MCP does not auto-create directories.

---

## WORKFLOW ARCHITECTURE

This workflow uses **step-file architecture** for disciplined execution:

- **Micro-file Design**: Each step is self-contained
- **JIT Loading**: Only the current step file is in memory
- **Sequential Enforcement**: Execute steps in order without skipping

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

From `workflow.yaml`, resolve all variables.

### 2. First Step

Load, read completely, and execute:
`steps-c/step-01-preflight.md`

### 3. Resume Support

If the user selects **Resume** mode, load, read completely, and execute:
`steps-c/step-01b-resume.md`

This checks the output document for progress tracking frontmatter and routes to the next incomplete step.
