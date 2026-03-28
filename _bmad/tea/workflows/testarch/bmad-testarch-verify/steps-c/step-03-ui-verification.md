---
name: 'step-03-ui-verification'
description: 'Navigate dashboard UI, verify visual state, test interactions, capture screenshots'
outputFile: '{test_artifacts}/qa-reports/qa-report-{date}.md'
nextStepFile: 'step-04-data-verification.md'
---

# Step 3: UI Verification

## STEP GOAL

Navigate the application's dashboard UI via Playwright MCP, verify that pages render correctly, data displays as expected, interactive elements function, and no browser errors occur. Capture screenshot evidence for every verified area.

---

## MANDATORY EXECUTION RULES

- Use `browser_snapshot` (accessibility tree) as the primary inspection method — it is faster and more reliable than screenshots for understanding page structure
- Use `browser_take_screenshot` with the `filename` parameter to save evidence as real PNG files
- Check `browser_console_messages` after each page navigation for JS errors
- Check `browser_network_requests` to verify API calls succeed (no 4xx/5xx responses)
- Do NOT use coordinate-based clicking unless accessibility tree elements are insufficient
- Number screenshots sequentially: `screenshot-{NN}-{description}.png`

---

## MANDATORY SEQUENCE

### 1. Open Browser and Navigate to App

```
mcp__playwright-test__browser_navigate(url: "{dashboard_url}")
```

Take an initial accessibility snapshot to understand the page structure:

```
mcp__playwright-test__browser_snapshot()
```

Capture the initial screenshot:

```
mcp__playwright-test__browser_take_screenshot(
  type: "png",
  filename: "{screenshot_dir}/screenshot-01-initial-load.png"
)
```

**Verify:**
- Page loads without errors
- Main layout elements are present (navigation, content area)
- No "Error" or "Loading..." stuck states

### 2. Check Browser Console

```
mcp__playwright-test__browser_console_messages()
```

**Record:** Any errors or warnings. JS errors at this stage indicate fundamental issues.

### 3. Verify Page Content

**Story mode — for each UI-related AC:**

Navigate to the relevant page/section:
```
mcp__playwright-test__browser_click(element: "{nav element ref}", ref: "{ref}")
```

Take a snapshot to inspect content:
```
mcp__playwright-test__browser_snapshot()
```

Use assertion tools to verify expected content:
```
mcp__playwright-test__browser_verify_text_visible(text: "{expected text}")
mcp__playwright-test__browser_verify_element_visible(role: "{role}", name: "{name}")
```

Capture screenshot evidence:
```
mcp__playwright-test__browser_take_screenshot(
  type: "png",
  filename: "{screenshot_dir}/screenshot-{NN}-{ac-description}.png"
)
```

**Exploratory mode:**

Systematically navigate through the application:
1. Identify all navigation elements from the snapshot
2. Visit each page/section
3. For each page:
   - Take a snapshot to understand content structure
   - Verify data tables have rows (not empty)
   - Verify charts/panels render (elements present in accessibility tree)
   - Check for error states or broken layouts
   - Capture a screenshot

### 4. Test Interactive Elements

For forms, buttons, filters, and other interactive elements relevant to the scope:

**Form testing:**
```
mcp__playwright-test__browser_fill_form(values: [
  { ref: "{field-ref}", value: "{test value}" }
])
```

**Button clicks:**
```
mcp__playwright-test__browser_click(element: "{button text}", ref: "{ref}")
```

**After each interaction:**
- Take a snapshot to verify the result
- Check console for errors
- Check network requests for failed API calls
- Capture screenshot if the interaction produces a visible state change

### 5. Verify Network Requests

```
mcp__playwright-test__browser_network_requests()
```

**Verify:**
- API calls return 200/201 status codes
- No 4xx or 5xx errors in the network log
- Expected API endpoints were called (data is fetched, not hardcoded)

### 6. Record Findings

For each verified area, record in the QA report under `## UI Verification`:

```markdown
### {Page/Feature Name}

**Status:** PASS | FAIL | WARN

**Observations:**
- {what was tested}
- {what was observed}

**Evidence:**
![{Description}](screenshot-{NN}-{description}.png)

**Console Errors:** {none | list of errors}
**Network Issues:** {none | list of failed requests}
```

### 7. Keep Browser Open

**Do NOT close the browser.** Step 5 (Log Inspection) needs `browser_console_messages` to retrieve frontend console output from this session. The browser will be closed in Step 5 after console messages are captured.

### 8. Update Report Frontmatter

```bash
python3 scripts/update-report-frontmatter.py {report_file_path} --step ui-verification --set browser_open=true
```

### 9. Present Summary

```
UI Verification Complete
  Pages tested: {N}
  Interactions tested: {N}
  Screenshots captured: {N}
  Console errors: {N}
  Network failures: {N}
  Passed: {N}
  Failed: {N}
```

**Interactive mode:** "Ready to proceed with data verification?"
**Headless mode:** Proceed directly to next step.

---

## CONTEXT BOUNDARIES

**Available context:** Story ACs, app URL, report from previous steps
**Focus:** Visual correctness, interaction behavior, frontend error detection
**Limits:** Do NOT verify database state — that is Step 4. Do NOT test API responses directly — that was Step 2
**Dependencies:** Step 01 (preflight) — app must be running

---

## SUCCESS METRICS

- All UI-relevant ACs verified (story mode) or all accessible pages explored (exploratory mode)
- Screenshots captured for every verified area
- Browser console checked for errors after each navigation
- Network requests verified for failures
- Findings recorded with evidence in report
