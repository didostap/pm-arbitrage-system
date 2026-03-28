---
name: 'step-06-report'
description: 'Compile all findings into final QA verification report'
outputFile: '{test_artifacts}/qa-reports/qa-report-{date}.md'
nextStepFile: false
---

# Step 6: Report Compilation

## STEP GOAL

Compile all findings from Steps 2-5 into a polished, self-contained QA verification report. Assign pass/fail verdicts to each acceptance criterion (story mode) or each tested area (exploratory mode). Generate the summary section with an overall verdict.

---

## MANDATORY EXECUTION RULES

- Every AC must have a final verdict: PASS, FAIL, or BLOCKED
- Every verdict must cite specific evidence (screenshot reference, API response, DB query result)
- The report must be self-contained — readable without re-running the workflow
- Do NOT add optimistic language to failed items — state the failure clearly
- Include reproduction steps for every FAIL verdict

---

## MANDATORY SEQUENCE

### 1. Read Current Report

Read the report file to get all accumulated findings from previous steps.

### 2. Generate AC Verdicts (Story Mode)

For each acceptance criterion, synthesize evidence from all verification steps:

```markdown
### AC {N}: {AC description}

**Verdict: PASS | FAIL | BLOCKED**

**Evidence:**
- API: {endpoint test result — reference step 2 finding}
- UI: {visual verification — reference screenshot}
- Data: {DB state — reference step 4 query}
- Logs: {any relevant log findings}

{If FAIL:}
**Reproduction Steps:**
1. {step to reproduce}
2. {step to reproduce}
**Expected:** {what should happen}
**Actual:** {what actually happens}
```

### 3. Generate Area Verdicts (Exploratory Mode)

For each tested area, synthesize a verdict:

```markdown
### {Area Name}

**Verdict: PASS | FAIL | WARN**

**What was tested:**
- {list of tests performed}

**Findings:**
- {key observations}

**Evidence:**
- {references to screenshots, API responses, etc.}
```

### 4. Write Summary Section

Calculate overall statistics and write the summary at the top of the report:

```markdown
## Summary

| Metric | Value |
|--------|-------|
| **Overall Verdict** | PASS / FAIL / PASS WITH WARNINGS |
| **ACs Passed** | {N}/{total} |
| **ACs Failed** | {N}/{total} |
| **Issues Found** | {N} (Critical: {N}, Warning: {N}) |
| **Screenshots** | {N} captured |
| **Date** | {date} |
| **Duration** | {approximate} |
```

**Overall Verdict Rules:**
- **PASS** — All ACs pass, no errors in logs, no console errors
- **PASS WITH WARNINGS** — All ACs pass, but warnings found (non-critical log entries, minor console warnings)
- **FAIL** — Any AC fails, or critical errors found in logs

### 5. Write Issues Section

If any issues were found across all steps:

```markdown
## Issues Found

### Issue {N}: {Short title}

**Severity:** Critical | High | Medium | Low
**Found In:** {Step where discovered}
**Description:** {Clear description}
**Evidence:** {Reference to specific finding}
**Recommendation:** {Suggested fix or investigation}
```

### 6. Write Recommendations Section

```markdown
## Recommendations

{Based on all findings, provide actionable recommendations:}
- {Fix for any failed ACs}
- {Investigation needed for warnings}
- {Improvements noticed during testing}
```

### 7. Update Report Frontmatter

Update the report YAML frontmatter:
- Set `status` to `"complete"`
- Add `"report"` to `stepsCompleted` array
- Update `lastStep` to `"report"`
- Update `lastSaved` timestamp
- Add `verdict` field with overall verdict

### 8. Final Report Validation

Verify the report is complete:
- [ ] Summary section has overall verdict
- [ ] Every AC has a verdict with evidence
- [ ] All screenshots referenced actually exist as files
- [ ] No placeholder text remains
- [ ] Issues section is populated (or explicitly says "No issues found")
- [ ] Frontmatter status is "complete"

### 9. Present Final Result

```
QA Verification Complete

  Report: {report_file_path}
  Overall Verdict: {PASS | FAIL | PASS WITH WARNINGS}

  ACs Passed: {N}/{total}
  ACs Failed: {N}/{total}
  Issues Found: {N}
  Screenshots: {N}
```

If any ACs failed, highlight them specifically.

---

## CONTEXT BOUNDARIES

**Available context:** Complete report with all step findings
**Focus:** Synthesis, verdict assignment, and report polish
**Limits:** Do NOT re-run any verification — work only from collected evidence
**Dependencies:** All previous steps (02-05) should be complete

---

## SUCCESS METRICS

- Every AC/area has a verdict
- Summary section is accurate and complete
- Issues are classified by severity
- Report is self-contained and readable
- Frontmatter indicates completion
