---
name: 'step-01-reassess'
description: 'Re-run specific verification stages and update an existing QA report'
---

# Edit Mode: Reassess & Update

## STEP GOAL

Re-run specific verification stages against the running application and update an existing QA report with fresh findings. Used when issues have been fixed and need re-verification, or when a stage was skipped.

---

## MANDATORY SEQUENCE

### 1. Load Existing Report

Ask the user for the report path, or find the most recent:

```bash
ls -t {report_dir}/qa-report-*.md | head -5
```

Read the selected report file. Parse the YAML frontmatter for context.

### 2. Identify Re-verification Scope

Ask the user which stages to re-run:

```
Which stages would you like to re-run?
  [2] API Verification
  [3] UI Verification
  [4] Data Verification
  [5] Log Inspection
  [A] All stages
  [F] Only failed ACs
```

**"Only failed ACs" option:** Parse the report for FAIL verdicts and re-test only those specific areas.

### 3. Verify Application Is Running

Run health check (same as step-01-preflight):

```bash
curl -s -o /dev/null -w "%{http_code}" {app_url}{health_endpoint}
```

### 4. Execute Selected Stages

For each selected stage, load and execute the corresponding step file:
- Stage 2 → `steps-c/step-02-api-verification.md`
- Stage 3 → `steps-c/step-03-ui-verification.md`
- Stage 4 → `steps-c/step-04-data-verification.md`
- Stage 5 → `steps-c/step-05-log-inspection.md`

**Important:** When re-running a stage, replace the corresponding section in the report rather than appending. Mark updated sections with `(Re-verified: {timestamp})`.

### 5. Update Verdicts

After re-running stages, re-evaluate AC verdicts:
- If a previously FAIL AC now passes → update to PASS with note: "Fixed — re-verified {timestamp}"
- If a previously PASS AC now fails → update to FAIL (regression detected)

### 6. Update Report

- Recalculate summary statistics
- Update overall verdict
- Update frontmatter `lastSaved` timestamp
- Add a `re-verification` section in frontmatter tracking what was re-run and when

### 7. Present Results

```
Re-verification Complete
  Stages re-run: {list}
  Previously Failed → Now Passing: {N}
  New Failures: {N}
  Updated Verdict: {PASS | FAIL | PASS WITH WARNINGS}
```
