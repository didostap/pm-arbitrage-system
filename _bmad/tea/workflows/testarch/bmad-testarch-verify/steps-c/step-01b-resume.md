---
name: 'step-01b-resume'
description: 'Resume an interrupted QA verification session'
outputFile: '{test_artifacts}/qa-reports/qa-report-{date}.md'
---

# Step 1b: Resume

## STEP GOAL

Resume an interrupted QA verification session by reading the existing report document and routing to the next incomplete step.

---

## MANDATORY SEQUENCE

### 1. Load Output Document

Ask the user for the path to the existing QA report, or search for the most recent report:

```bash
ls -t {report_dir}/qa-report-*.md | head -5
```

Present the list and let the user choose, or accept a direct path.

### 2. Parse Progress

Read the selected report file. Parse YAML frontmatter for:
- `status` — current status
- `stepsCompleted` — array of completed step names
- `lastStep` — last completed step
- `lastSaved` — timestamp of last update
- `inputs` — input files to reload for context

### 3. Reload Context

Re-read all files from the `inputs` array to restore context (e.g., story file).

### 4. Display Progress Dashboard

```
Resume QA Verification
  Report: {report_path}
  Last Step: {lastStep}
  Completed: {stepsCompleted as comma-separated list}
  Last Saved: {lastSaved}
```

### 5. Route to Next Step

Based on `lastStep`, route to the next step in sequence:

| Last Completed Step | Next Step File |
|---------------------|---------------|
| `preflight` | `step-02-api-verification.md` |
| `api-verification` | `step-03-ui-verification.md` |
| `ui-verification` | `step-04-data-verification.md` |
| `data-verification` | `step-05-log-inspection.md` |
| `log-inspection` | `step-06-report.md` |
| `report` | Already complete — offer to re-run specific stages |

Load and execute the identified next step file.
