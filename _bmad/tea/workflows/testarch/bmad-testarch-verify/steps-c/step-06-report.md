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

```bash
python3 scripts/update-report-frontmatter.py {report_file_path} \
  --step report \
  --set status=complete \
  --set "verdict={overall_verdict}"
```

### 8. Write Failed ACs to Story File (Story Mode Only)

**Skip this step if:** verify_mode is "exploratory" OR overall verdict is PASS.

When ACs fail in story mode, write findings back into the story file so the dev agent can pick them up automatically. This mirrors the `[AI-Review]` pattern used by the code review workflow.

#### 8a. Write "QA Verification (AI)" Section

Append to the story file (after any existing "Senior Developer Review (AI)" section, or at the end before Dev Agent Record if no review section exists):

```markdown
## QA Verification (AI)

**QA Outcome:** {FAIL | PASS WITH WARNINGS}
**Verification Date:** {date}
**Report:** {report_file_path}

### Failed ACs

{For each FAIL verdict:}
- [ ] [SEVERITY: {High|Medium|Low}] AC {N}: {AC description}
  - **Expected:** {expected behavior}
  - **Actual:** {actual behavior}
  - **Evidence:** {screenshot reference or API response}
  - **Reproduction:** {steps to reproduce}

**Summary:** {high_count} High, {med_count} Medium, {low_count} Low
```

**Severity assignment:**
- **High** — Core AC functionality broken, feature doesn't work
- **Medium** — AC partially met, edge case failure, data inconsistency
- **Low** — Minor UI issue, non-critical log warning, cosmetic problem

#### 8b. Write "QA Follow-ups (AI)" Task Section

Find the `## Tasks / Subtasks` section in the story file. Append a new subsection:

```markdown
### QA Follow-ups (AI)

{For each FAIL verdict:}
- [ ] [AI-QA] Fix: {AC description} — {one-line summary of what's wrong}
```

#### 8c. Update Story Status

If the story status is currently `review` or `done`, set it back to `in-progress` in `sprint-status.yaml` so the dev agent picks it up:

```
Story status: review → in-progress (QA findings require fixes)
```

#### 8d. Present Feedback Summary

```
QA Findings Written to Story
  Story: {story_file_path}
  Failed ACs: {N}
  [AI-QA] tasks created: {N}
  Story status: → in-progress

  The dev agent will prioritize [AI-QA] tasks on next run.
```

### 9. Final Report Validation

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
