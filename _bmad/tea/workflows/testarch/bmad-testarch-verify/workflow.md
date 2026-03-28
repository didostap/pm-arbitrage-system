---
name: bmad-testarch-verify
description: Post-implementation QA verification against running app. Use when user says 'verify story', 'QA check', or 'test the running app'
---

# QA Verification

**Goal:** Perform post-implementation QA verification against a running application, producing an evidence-backed QA report with pass/fail per acceptance criterion.

**Role:** You are the Master Test Architect performing manual QA verification. Be methodical, evidence-driven, and thorough. Test happy paths and edge cases. Capture evidence for every finding.

---

## PIPELINE POSITION

This workflow runs **after code review** as the final acceptance gate before a story is considered done.

```
Dev Story → Code Review → Dev fixes review findings → VR (this workflow) → Dev fixes QA findings → Done
(implement)  (review code)  (patch findings)           (test running app)   ([AI-QA] tasks)
```

**When ACs fail:** VR writes `[AI-QA]` tasks into the story file (same pattern as `[AI-Review]` tasks from code review). The dev agent detects these on its next run and prioritizes fixing them.

**Feedback loop:**
1. VR runs → produces QA report with PASS/FAIL per AC
2. Failed ACs → written as `[AI-QA]` tasks in story file, story status → `in-progress`
3. Dev agent resumes → detects "QA Verification (AI)" section → prioritizes `[AI-QA]` tasks
4. Dev fixes → tests pass → story status → `review`
5. VR re-runs in Edit mode (only failed ACs) → all pass → done

---

## ACTIVATION MODE DETECTION

**Check activation context immediately:**

1. **Headless mode**: If the user passes `--headless` or `-H` flags, or if their intent clearly indicates non-interactive execution (e.g., "run full QA check on story X"):
   - Load story file, verify app is running, run all stages sequentially
   - Capture all evidence automatically (screenshots, API responses, DB queries)
   - Generate complete QA report without pausing
   - If `--headless:{stage}` → run only that specific stage (e.g., `--headless:api`)

2. **Interactive mode** (default): Proceed to `## On Activation` section below

---

## WORKFLOW ARCHITECTURE

This workflow uses **tri-modal step-file architecture**:

- **Create mode (steps-c/)**: Primary QA verification flow
- **Validate mode (steps-v/)**: Validate existing QA report completeness
- **Edit mode (steps-e/)**: Re-run specific verifications or update report

---

## ON ACTIVATION

### 1. Configuration Loading

From `workflow.yaml`, resolve:

- `config_source`, `test_artifacts`, `user_name`, `communication_language`, `date`
- `app_url`, `api_url`, `health_endpoint`, `engine_dir`
- `server_log`, `trade_log_dir`, `report_dir`, `screenshot_dir`
- `stages`, `verify_mode`

### 2. Mode Determination

"Welcome to QA Verification. What would you like to do?"

- **[C] Create** — Run a new QA verification session
- **[R] Resume** — Resume an interrupted verification
- **[V] Validate** — Check completeness of an existing QA report
- **[E] Edit** — Re-run specific verifications or update a report

### 3. Route to First Step

- **If C:** Load `steps-c/step-01-preflight.md`
- **If R:** Load `steps-c/step-01b-resume.md`
- **If V:** Load `steps-v/step-01-validate.md`
- **If E:** Load `steps-e/step-01-reassess.md`

---

## STAGE SKIP LOGIC

The `{stages}` variable controls which verification stages run. Check it before loading each step:

| stages value | Steps to run |
|-------------|-------------|
| `all` (default) | All steps: 01 → 02 → 03 → 04 → 05 → 06 |
| `api` | 01 → 02 → 06 |
| `ui` | 01 → 03 → 06 |
| `data` | 01 → 04 → 06 |
| `logs` | 01 → 05 → 06 |
| `api,ui` | 01 → 02 → 03 → 06 |
| (any comma-separated combination) | 01 → selected stages → 06 |

**Step 01 (preflight) and Step 06 (report) always run.** They are not skippable.

When a step is skipped, record in the report under that stage's section: "Stage skipped — not included in `stages` configuration."

**Implementation:** Each step file's `nextStepFile` defines the default chain. When skipping, the executing agent must check `{stages}` and jump to the next non-skipped step instead of following `nextStepFile`.

---

## HEADLESS MODE ROUTING

When running in headless mode:

1. Determine verification mode:
   - If story file path provided → story mode
   - If area/scope description provided → exploratory mode
   - If neither → prompt user (even in headless, this input is required)

2. Check `{stages}` variable and execute applicable stages sequentially:
   - Preflight (step-01) — always
   - API Verification (step-02) — if stages includes "api" or is "all"
   - UI Verification (step-03) — if stages includes "ui" or is "all"
   - Data Verification (step-04) — if stages includes "data" or is "all"
   - Log Inspection (step-05) — if stages includes "logs" or is "all"
   - Report Generation (step-06) — always

3. Output path to completed QA report
