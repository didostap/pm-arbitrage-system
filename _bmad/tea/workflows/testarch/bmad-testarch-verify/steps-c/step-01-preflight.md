---
name: 'step-01-preflight'
description: 'Determine verification mode, verify app is running, initialize QA report'
outputFile: '{test_artifacts}/qa-reports/qa-report-{date}.md'
nextStepFile: 'step-02-api-verification.md'
---

# Step 1: Preflight & Context

## STEP GOAL

Establish the verification scope, confirm the target application is running and accessible, and initialize the QA report document that will accumulate evidence through subsequent steps.

---

## MANDATORY EXECUTION RULES

- Do NOT skip health check — a failed health check means the app is not running
- Do NOT proceed to verification steps if the app is unreachable
- Do NOT assume verification mode — ask the user or infer from provided arguments

---

## MANDATORY SEQUENCE

### 1. Determine Verification Mode

**If story file path was provided or user specifies a story:**
- Set `verify_mode` = "story"
- Read the story file completely
- Extract all acceptance criteria (ACs) into a numbered list
- Extract the story ID for report naming

**If user describes an area/feature to test:**
- Set `verify_mode` = "exploratory"
- Record the scope description
- Identify relevant modules/endpoints from the description

**If neither:**
- Ask the user: "Would you like to verify a specific story (provide the story file path) or do exploratory testing (describe the area to test)?"
- **STOP and WAIT for user input**

### 2. Run Preflight Checks

Run the preflight script to check all prerequisites at once:

```bash
scripts/preflight-check.sh \
  --api-url {api_url} \
  --dashboard-url {dashboard_url} \
  --engine-dir {engine_dir} \
  --server-log {server_log} \
  --report-dir {report_dir} \
  --auth-token "{auth_token}"
```

The script outputs JSON. Parse the result and act on each check:

**`api_health.ok = false`:**
- Inform the user: "The API server at {api_url} is not responding. Please ensure the server is running."
- Suggest: "Start the server with log capture: `cd {engine_dir} && pnpm start:dev 2>&1 | tee server.log`"
- **STOP and WAIT** for user to start the app, then re-run the script

**`dashboard_health.ok = false`:**
- Warn user: "Dashboard at {dashboard_url} is not responding. UI verification will be skipped. Start the dashboard with: `cd pm-arbitrage-dashboard && pnpm dev`"

**`auth.token_provided = false`:**
- **Interactive mode:** "No auth token configured. Protected endpoints will be skipped. Provide a Bearer token? (or press Enter to continue without)"
- **Headless mode:** Continue without auth, note limitation in report

**`server_log.exists = false`:**
- Inform user: "Server log file not found. Log inspection will be limited to browser console and database audit logs. For full log access, restart the server with: `pnpm start:dev 2>&1 | tee server.log`"

**`overall = "ready"`:** Proceed to report initialization.
**`overall = "blocked"`:** API server must be running — do not proceed until resolved.

### 5. Initialize QA Report

Determine report filename:
- Story mode: `qa-report-{story-id}-{date}.md`
- Exploratory mode: `qa-report-exploratory-{date}.md`

Create the report file using the template from `templates/qa-report-template.md`. Fill in:

**YAML Frontmatter:**
```yaml
---
title: "QA Verification: {story-id or scope}"
status: "in-progress"
mode: "{verify_mode}"
stepsCompleted: ["preflight"]
lastStep: "step-01-preflight"
lastSaved: "{timestamp}"
api_url: "{api_url}"
dashboard_url: "{dashboard_url}"
authenticated: {true | false}
browser_open: false
story_file: "{story_file_path or n/a}"
inputs:
  - "{story_file_path}"
---
```

**Body sections to populate:**
- Summary (placeholder — filled in Step 6)
- Verification Scope (fill now with ACs list or exploratory scope)

### 6. Present Preflight Summary

Display to the user:

```
Preflight Complete
  Mode: {story | exploratory}
  Scope: {number of ACs | scope description}
  API: {api_url} — Running
  Dashboard: {dashboard_url} — {Running | Not available}
  Auth: {authenticated | public only}
  Logs: {available | limited}
  Report: {report_file_path}

Proceeding to API Verification...
```

**Interactive mode:** Ask "Ready to proceed with API verification, or would you like to adjust the scope?"

**Headless mode:** Proceed directly to next step.

---

## CONTEXT BOUNDARIES

**Available context:** Story file (if story mode), app URL, health check result
**Focus:** Establishing scope and confirming prerequisites
**Limits:** Do NOT start any verification activity in this step
**Dependencies:** None — this is the entry step

---

## SUCCESS METRICS

- Verification mode is set (story or exploratory)
- ACs are extracted and numbered (story mode)
- Health check passed
- Report file created with frontmatter
- User knows what will be tested
