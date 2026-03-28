---
name: 'step-05-log-inspection'
description: 'Inspect server logs, browser console, and trade CSVs for errors and anomalies'
outputFile: '{test_artifacts}/qa-reports/qa-report-{date}.md'
nextStepFile: 'step-06-report.md'
---

# Step 5: Log Inspection

## STEP GOAL

Inspect all available log sources for errors, warnings, and anomalies. This step catches issues that may not be visible through API responses or UI behavior — silent failures, unhandled exceptions, performance warnings, and data pipeline issues.

---

## MANDATORY EXECUTION RULES

- Check ALL available log tiers — do not skip a tier just because another tier found no issues
- Search for ERROR and WARN level entries specifically — do not just read the last few lines
- When errors are found, trace the correlationId to understand the full request flow
- Summarize log findings — do not paste raw log dumps into the report

---

## MANDATORY SEQUENCE

### 1. Server Application Logs (Tier 2)

**If server log file exists (`{engine_dir}/{server_log}`):**

Search for errors:
```bash
grep -i "error\|ERR\|exception\|fatal" {engine_dir}/{server_log} | tail -20
```

Search for warnings:
```bash
grep -i "warn\|WARNING" {engine_dir}/{server_log} | tail -20
```

Check for recent activity (last 50 lines):
```bash
tail -50 {engine_dir}/{server_log}
```

**If correlationId found in errors:** Trace the full request:
```bash
grep "{correlationId}" {engine_dir}/{server_log}
```

**If server log file does not exist:**
Record: "Server log not available — server was not started with `tee` output capture."

**If running in Docker:**
```bash
docker logs pm-arbitrage-engine --tail 50 2>&1
```

### 2. Browser Console Logs (Tier 4)

Check the report frontmatter for `browser_open`:

**If `browser_open` is `true` (browser still open from Step 3):**
```
mcp__playwright-test__browser_console_messages()
```

After capturing console messages, close the browser:
```
mcp__playwright-test__browser_close()
```

**If `browser_open` is `false` (Step 3 was skipped or browser was closed):**
- If UI verification was in scope but browser was closed due to resume, open the dashboard briefly:
  ```
  mcp__playwright-test__browser_navigate(url: "{dashboard_url}")
  ```
  Capture console messages, then close.
- If UI verification was not in scope (stages did not include "ui"), skip this tier entirely and note: "Browser console not checked — UI verification was not in scope."

**Classify findings:**
- **Errors:** JS exceptions, failed resource loads, React error boundaries
- **Warnings:** Deprecation notices, missing props, performance warnings
- **Info:** Normal application logging (usually safe to ignore)

### 3. CSV Trade Logs (Tier 1)

Check if trade log files exist:

```bash
ls -la {engine_dir}/{trade_log_dir}/ 2>/dev/null
```

**If files exist:**

Read today's trade log:
```bash
cat {engine_dir}/{trade_log_dir}/trades-$(date +%Y-%m-%d).csv 2>/dev/null || echo "No trades today"
```

Check daily summaries:
```bash
tail -5 {engine_dir}/{trade_log_dir}/daily-summaries.csv 2>/dev/null || echo "No summaries"
```

**Verify:**
- CSV headers are present and correct
- No malformed rows
- Trade prices and sizes are reasonable (not zero, not negative)
- Timestamps are chronologically ordered

### 4. Database Audit Logs (Tier 3)

Query recent audit log entries:

```
mcp__postgres__execute_sql(sql: "
  SELECT event_type, module, severity, created_at,
         substring(details::text, 1, 100) as details_preview
  FROM audit_logs
  WHERE created_at > NOW() - INTERVAL '1 hour'
  ORDER BY created_at DESC
  LIMIT 20;
")
```

**Check for:**
- Any `severity` = 'critical' or 'error' entries
- Unusual event types or patterns
- Gaps in the audit chain (missing expected events)

### 5. Cross-Reference Issues

If errors were found in any tier, cross-reference:

- Server error with correlationId → trace through audit logs
- Browser console error → check if related API endpoint failed in network requests
- Trade CSV anomaly → check corresponding order in database

### 6. Record Findings

For each log tier, record in the QA report under `## Log Inspection`:

```markdown
### Server Logs

**Status:** PASS | FAIL | WARN
**Errors Found:** {count}
**Warnings Found:** {count}

{If errors:}
| Timestamp | Level | Module | Message |
|-----------|-------|--------|---------|
| ... | ERROR | ... | ... |

### Browser Console

**Status:** PASS | FAIL | WARN
**JS Errors:** {count}
**Warnings:** {count}

{If errors, list them}

### Trade CSV Logs

**Status:** PASS | FAIL | WARN | N/A
**Trades Today:** {count or "no trades"}
**Anomalies:** {none | list}

### Audit Log

**Status:** PASS | FAIL | WARN
**Critical Events:** {count}
**Error Events:** {count}
**Recent Activity:** {summary}
```

### 7. Update Report Frontmatter

```bash
python3 scripts/update-report-frontmatter.py {report_file_path} --step log-inspection --set browser_open=false
```

### 8. Present Summary

```
Log Inspection Complete
  Server log errors: {N}
  Browser console errors: {N}
  Trade CSV anomalies: {N}
  Audit log critical events: {N}
```

**Interactive mode:** "Ready to compile the final QA report?"
**Headless mode:** Proceed directly to next step.

---

## CONTEXT BOUNDARIES

**Available context:** All previous step results in the report, server log path, trade log dir
**Focus:** Error detection and anomaly identification across all log sources
**Limits:** Do NOT fix any issues found — only report them. Do NOT re-run API or UI tests
**Dependencies:** Steps 01-04 should be complete for full context

---

## SUCCESS METRICS

- All available log tiers inspected
- Errors and warnings identified and classified
- Cross-referencing performed for found issues
- Findings recorded with evidence in report
