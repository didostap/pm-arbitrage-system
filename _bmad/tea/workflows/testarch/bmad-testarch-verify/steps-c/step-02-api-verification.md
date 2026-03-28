---
name: 'step-02-api-verification'
description: 'Test REST API endpoints, verify response formats and status codes'
outputFile: '{test_artifacts}/qa-reports/qa-report-{date}.md'
nextStepFile: 'step-03-ui-verification.md'
---

# Step 2: API Verification

## STEP GOAL

Systematically test REST API endpoints relevant to the verification scope. Verify response status codes, JSON format compliance, error handling, and data correctness. Record all findings with evidence in the QA report.

---

## MANDATORY EXECUTION RULES

- Test BOTH happy path and at least one error case per endpoint
- Record the exact request and response for every test
- Use `curl` for transparent, reproducible API calls
- If `{auth_token}` is set, include `-H "Authorization: Bearer {auth_token}"` in all curl calls
- If `{auth_token}` is empty, test only public/unprotected endpoints — note in report which endpoints were skipped due to auth
- Verify response format matches project standard: `{ data: T, timestamp: string }` for success, `{ error: { code, message, severity }, timestamp: string }` for errors
- Do NOT modify any data through API calls unless explicitly part of a test scenario (use GET requests primarily)

---

## MANDATORY SEQUENCE

### 1. Identify Target Endpoints

**Story mode:**
- Read the story ACs and identify which REST endpoints they reference
- Check the source code for relevant controller files to discover endpoint paths
- Search for route decorators: `@Get`, `@Post`, `@Put`, `@Delete`, `@Patch`

**Exploratory mode:**
- Discover available endpoints by reading controller files in the scope area
- List all routes found

Present the endpoint list to the user (interactive mode) or proceed (headless mode).

### 2. Test Each Endpoint

For each identified endpoint, execute the following test sequence:

#### A. Happy Path Test

**If `{auth_token}` is set:**
```bash
curl -s -w "\n%{http_code}" -H "Authorization: Bearer {auth_token}" {api_url}/{endpoint}
```

**If `{auth_token}` is empty (public endpoints only):**
```bash
curl -s -w "\n%{http_code}" {api_url}/{endpoint}
```

**Verify:**
- Status code is 200 (or 201 for creation)
- Response body is valid JSON
- Response has `data` field and `timestamp` field
- `timestamp` is a valid ISO 8601 string
- Data content is reasonable (not empty when data should exist)

#### B. Error Case Test (at minimum one per endpoint)

Test with invalid input, missing parameters, or non-existent resource IDs:

```bash
curl -s -w "\n%{http_code}" {api_url}/{endpoint}/nonexistent-id
```

**Verify:**
- Status code is appropriate (400, 404, 422)
- Response has `error` field with `code`, `message`, `severity`
- Error message is descriptive (not generic "Internal Server Error")

#### C. POST/PUT Endpoints (if applicable and safe to test)

For write endpoints relevant to the ACs:

```bash
curl -s -X POST -H "Content-Type: application/json" -d '{"test": "data"}' {api_url}/{endpoint}
```

**Verify:**
- Validation works (rejects invalid payloads)
- Required fields are enforced
- Response includes created/updated resource

### 3. Record Findings

For each endpoint tested, record in the QA report under `## API Verification`:

```markdown
### {METHOD} {endpoint}

**Status:** PASS | FAIL | WARN

**Happy Path:**
- Request: `{method} {url}`
- Response Status: {code}
- Response Body: (key fields, not full dump)
- Verdict: {PASS/FAIL with reason}

**Error Case:**
- Request: `{method} {url}`
- Response Status: {code}
- Response Body: (key fields)
- Verdict: {PASS/FAIL with reason}
```

### 4. Update Report Frontmatter

```bash
python3 scripts/update-report-frontmatter.py {report_file_path} --step api-verification
```

### 5. Present Summary

```
API Verification Complete
  Endpoints tested: {N}
  Passed: {N}
  Failed: {N}
  Warnings: {N}
```

**Interactive mode:** "Ready to proceed with UI verification?"
**Headless mode:** Proceed directly to next step.

---

## CONTEXT BOUNDARIES

**Available context:** Story ACs (from step-01), app URL, API URL
**Focus:** REST endpoint behavior and response compliance
**Limits:** Do NOT test UI or database directly — those are separate steps
**Dependencies:** Step 01 (preflight) must be complete — app must be running

---

## SUCCESS METRICS

- All identified endpoints tested
- Each endpoint has happy path + error case results
- Response format compliance verified
- Findings recorded in report with evidence
