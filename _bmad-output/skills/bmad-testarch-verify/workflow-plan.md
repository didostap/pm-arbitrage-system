# Workflow Plan: testarch-verify

## Create Mode (steps-c)

- step-01-preflight.md — Load story/scope, verify app running, create report skeleton
- step-01b-resume.md — Resume interrupted verification
- step-02-api-verification.md — Test REST endpoints, verify responses
- step-03-ui-verification.md — Navigate UI, test flows, capture screenshots
- step-04-data-verification.md — Query DB state, verify data integrity
- step-05-log-inspection.md — Check server logs, browser console, trade CSVs
- step-06-report.md — Compile findings into final QA report

## Validate Mode (steps-v)

- step-01-validate.md — Validate existing QA report against checklist

## Edit Mode (steps-e)

- step-01-reassess.md — Re-run specific stages and update report

## Outputs

- {test_artifacts}/qa-reports/qa-report-{story-id}-{date}.md (story mode)
- {test_artifacts}/qa-reports/qa-report-exploratory-{date}.md (exploratory mode)
- {test_artifacts}/qa-reports/screenshot-*.png (evidence screenshots)
