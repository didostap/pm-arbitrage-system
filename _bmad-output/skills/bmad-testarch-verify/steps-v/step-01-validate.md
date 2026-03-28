---
name: 'step-01-validate'
description: 'Validate completeness and quality of an existing QA verification report'
---

# Validate Mode: Report Quality Check

## STEP GOAL

Validate an existing QA verification report against the checklist to ensure completeness, evidence quality, and verdict accuracy.

---

## MANDATORY SEQUENCE

### 1. Load Report

Ask the user for the report path, or find the most recent:

```bash
ls -t {report_dir}/qa-report-*.md | head -5
```

Read the selected report file completely.

### 2. Check Structure

Verify the report contains all required sections:
- [ ] YAML frontmatter with `status`, `mode`, `verdict`
- [ ] Summary section with overall verdict and statistics
- [ ] API Verification section with endpoint results
- [ ] UI Verification section with screenshots
- [ ] Data Verification section with query results
- [ ] Log Inspection section with log analysis
- [ ] Verdict per AC (story mode) or per area (exploratory mode)
- [ ] Issues section (even if "no issues found")

### 3. Validate Evidence

For each verdict in the report:
- PASS verdicts: verify supporting evidence is cited
- FAIL verdicts: verify reproduction steps are included
- Check that all referenced screenshots exist as files

```bash
# Extract screenshot references and verify files exist
grep -o 'screenshot-[^)]*\.png' {report_path} | while read f; do
  test -f "{report_dir}/$f" && echo "OK: $f" || echo "MISSING: $f"
done
```

### 4. Validate Frontmatter

- `status` should be "complete"
- `stepsCompleted` should contain all stages
- `verdict` should match the summary section

### 5. Present Validation Results

```
Report Validation
  Structure: {complete | missing sections: ...}
  Evidence: {all cited | missing: ...}
  Screenshots: {all exist | missing: ...}
  Frontmatter: {valid | issues: ...}
  Overall: VALID | NEEDS ATTENTION
```

If issues found, ask if the user wants to switch to Edit mode to fix them.
