# QA Verification Checklist

## Step 1: Preflight

- [ ] Verification mode determined (story or exploratory)
- [ ] Story ACs extracted and listed (story mode) OR scope defined (exploratory mode)
- [ ] Application health check passed (HTTP 200 from health endpoint)
- [ ] Report directory created
- [ ] Report skeleton initialized with YAML frontmatter
- [ ] Server log accessibility confirmed (file exists or fallback noted)

## Step 2: API Verification

- [ ] All relevant REST endpoints identified
- [ ] Each endpoint tested with at least one request
- [ ] Response status codes verified (200, 201, 400, 404 as appropriate)
- [ ] Response format validated (camelCase JSON, timestamp present)
- [ ] Error responses tested for at least one endpoint
- [ ] API findings recorded in report with evidence (request/response pairs)

## Step 3: UI Verification

- [ ] Dashboard loads successfully (no blank screens)
- [ ] Key navigation flows tested (page transitions work)
- [ ] Data displays correctly (tables populated, values reasonable)
- [ ] Interactive elements respond (buttons, forms, filters)
- [ ] No console errors during navigation
- [ ] Screenshots captured for each verified area
- [ ] UI findings recorded in report with screenshot references

## Step 4: Data Verification

- [ ] Database accessible via Postgres MCP
- [ ] Key tables queried for expected state
- [ ] Data integrity checks performed (foreign keys, required fields)
- [ ] Mode isolation verified (paper vs live data separation)
- [ ] Data findings recorded in report with query results

## Step 5: Log Inspection

- [ ] Server log checked for errors/warnings since session start
- [ ] Browser console checked for JS errors
- [ ] Trade CSV logs checked if applicable
- [ ] Correlation IDs traced for key operations
- [ ] Log findings recorded in report

## Step 6: Report

- [ ] All stages compiled into final report
- [ ] Each AC has pass/fail status with evidence (story mode)
- [ ] Summary section with overall verdict
- [ ] Issues section with severity classification
- [ ] Screenshots embedded with relative paths
- [ ] Report YAML frontmatter updated to status "complete"

---

## Quality Checks

- [ ] Every PASS verdict has supporting evidence
- [ ] Every FAIL verdict has reproduction steps
- [ ] Screenshots are named descriptively
- [ ] No placeholder text remains in report
- [ ] Report is self-contained (readable without running the workflow)

## Completion Criteria

- [ ] All requested stages executed
- [ ] QA report written to `{report_dir}`
- [ ] All screenshots saved alongside report
- [ ] User notified of results with report path
