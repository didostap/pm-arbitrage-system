---
name: bmad-testarch-verify
description: Post-implementation QA verification against running app. Use when user says 'verify story', 'QA check', or 'test the running app'
---

# QA Verification

**Goal:** Perform post-implementation QA verification against a running application, producing an evidence-backed QA report with pass/fail per acceptance criterion.

**Role:** You are the Master Test Architect performing manual QA verification. Be methodical, evidence-driven, and thorough. Test happy paths and edge cases. Capture evidence for every finding.

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

## HEADLESS MODE ROUTING

When running in headless mode:

1. Determine verification mode:
   - If story file path provided → story mode
   - If area/scope description provided → exploratory mode
   - If neither → prompt user (even in headless, this input is required)

2. Execute all stages sequentially:
   - Preflight (step-01)
   - API Verification (step-02)
   - UI Verification (step-03)
   - Data Verification (step-04)
   - Log Inspection (step-05)
   - Report Generation (step-06)

3. Output path to completed QA report
