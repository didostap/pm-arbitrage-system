---
name: 'step-04-data-verification'
description: 'Query database state to verify data integrity and expected state'
outputFile: '{test_artifacts}/qa-reports/qa-report-{date}.md'
nextStepFile: 'step-05-log-inspection.md'
---

# Step 4: Data Verification

## STEP GOAL

Query the PostgreSQL database via Postgres MCP to verify that data state matches expected outcomes. Check data integrity, mode isolation (paper vs live), and verify that operations performed through the API/UI produced correct database records.

---

## MANDATORY EXECUTION RULES

- Use READ-ONLY queries — SELECT only, no INSERT/UPDATE/DELETE
- Always filter by `is_paper` when querying mode-sensitive tables (`open_positions`, `orders`, `risk_states`)
- Do NOT expose sensitive data in the report (redact API keys, credentials if encountered)
- Query results should be summarized, not dumped verbatim (include row counts and key field values)

---

## MANDATORY SEQUENCE

### 1. Verify Database Connectivity

```
mcp__postgres__list_schemas()
```

**If connection fails:** Record the failure in the report and skip to Step 5. Database verification is valuable but not blocking.

### 2. Identify Verification Queries

**Story mode:** Based on ACs, determine what database state should be verified:
- Did a contract match get created? → Query `contract_matches`
- Did an order execute? → Query `orders`
- Is position tracking correct? → Query `open_positions`
- Was a risk state updated? → Query `risk_states`

**Exploratory mode:** Run general health queries:
- Table row counts for key tables
- Recent records in `audit_log`
- Any orphaned records (e.g., orders without positions)

### 3. Execute Verification Queries

For each query, use the Postgres MCP:

```
mcp__postgres__execute_sql(sql: "SELECT ...")
```

**Common verification queries:**

#### Table Health Overview
```sql
SELECT 'contract_matches' as table_name, count(*) as row_count FROM contract_matches
UNION ALL
SELECT 'orders', count(*) FROM orders
UNION ALL
SELECT 'open_positions', count(*) FROM open_positions
UNION ALL
SELECT 'risk_states', count(*) FROM risk_states
UNION ALL
SELECT 'audit_logs', count(*) FROM audit_logs;
```

#### Mode Isolation Check
```sql
-- Verify paper and live data are properly separated
SELECT is_paper, count(*) as count
FROM open_positions
GROUP BY is_paper;
```

#### Recent Activity
```sql
SELECT id, event_type, module, created_at
FROM audit_logs
ORDER BY created_at DESC
LIMIT 10;
```

#### Data Integrity Spot Checks
```sql
-- Orders with missing position references
SELECT id, status, position_id
FROM orders
WHERE position_id IS NOT NULL
AND position_id NOT IN (SELECT id FROM open_positions);
```

### 4. Verify AC-Specific State (Story Mode)

For each AC that has a data component, construct and run a specific verification query:

```
AC: "Contract match is persisted with confidence score"
→ SELECT id, confidence_score, created_at FROM contract_matches ORDER BY created_at DESC LIMIT 5;
→ Verify: rows exist, confidence_score is between 0 and 1, timestamps are recent
```

### 5. Record Findings

For each query, record in the QA report under `## Data Verification`:

```markdown
### {Verification Area}

**Status:** PASS | FAIL | WARN

**Query:** `{SQL query}`
**Result:** {summary of results — row count, key values}
**Expected:** {what was expected}
**Verdict:** {PASS/FAIL with reason}
```

### 6. Update Report Frontmatter

Update the report file:
- Add `"data-verification"` to `stepsCompleted` array
- Update `lastStep` to `"data-verification"`
- Update `lastSaved` timestamp

### 7. Present Summary

```
Data Verification Complete
  Queries executed: {N}
  Passed: {N}
  Failed: {N}
  Warnings: {N}
  Mode isolation: {verified | issues found}
```

**Interactive mode:** "Ready to proceed with log inspection?"
**Headless mode:** Proceed directly to next step.

---

## CONTEXT BOUNDARIES

**Available context:** Story ACs, API verification results (from step-02)
**Focus:** Database state correctness and data integrity
**Limits:** READ-ONLY queries only. Do NOT modify data. Do NOT verify API behavior — that was Step 2
**Dependencies:** Step 01 (preflight) — database must be accessible

---

## SUCCESS METRICS

- Database connectivity confirmed
- Key tables queried for expected state
- Mode isolation verified
- Data integrity spot checks passed
- Findings recorded with query evidence
