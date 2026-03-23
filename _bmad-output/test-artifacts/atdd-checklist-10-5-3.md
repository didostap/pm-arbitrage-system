---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-22'
status: complete
storyId: '10-5-3'
storyName: 'Dashboard Settings Page UI'
detectedStack: fullstack
generationMode: ai-generation
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-5-3-dashboard-settings-page-ui.md'
  - 'e2e/playwright.config.ts'
  - 'e2e/support/fixtures/index.ts'
  - 'e2e/support/helpers/api-client.ts'
  - 'e2e/support/helpers/websocket.ts'
  - 'e2e/support/helpers/auth.ts'
  - 'e2e/support/page-objects/dashboard.page.ts'
  - 'e2e/support/factories/index.ts'
  - 'e2e/tests/ui/exit-criteria-display.spec.ts'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/selector-resilience.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
---

# ATDD Checklist — Story 10-5-3: Dashboard Settings Page UI

## Step 1: Preflight & Context

### Stack Detection
- **Detected stack:** fullstack
- Frontend: React 19 + Vite (pm-arbitrage-dashboard/)
- Backend: NestJS 11 + Prisma (pm-arbitrage-engine/)
- E2E: Playwright (e2e/ — independent repo)

### Prerequisites — All Passed
- Story approved with 13 acceptance criteria
- Playwright configured at e2e/playwright.config.ts
- Dev environment available (webServer for engine + dashboard)

### TEA Config
- tea_use_playwright_utils: true
- tea_browser_automation: auto
- tea_use_pactjs_utils: true
- tea_pact_mcp: mcp
- test_stack_type: fullstack

### Existing Patterns
- Fixtures: apiTest, authedTest (merged via mergeTests)
- Helpers: ApiClient, websocket (waitForWebSocket, collectWebSocketFrames), auth
- Page Objects: DashboardPage
- Factories: faker-based (contract match, order, position)
- Test style: route mocking via page.route(), data-testid selectors, [P1]/[P2] tags

## Step 2: Generation Mode

**Mode:** AI Generation

**Rationale:** Clear ACs, standard CRUD/nav/form/WS scenarios, exact API contracts provided, existing test patterns available.

## Step 3: Test Strategy

### AC → Test Scenario Matrix (29 tests)

| # | AC | Scenario | Level | Priority | Red Phase |
|---|-----|----------|-------|----------|-----------|
| 1 | AC1 | Navigate to /settings via sidebar — page loads | E2E-UI | P0 | FAIL |
| 2 | AC1 | Settings nav item after Stress Test with gear icon | E2E-UI | P2 | FAIL |
| 3 | AC2 | All 15 sections rendered in correct order | E2E-UI | P1 | FAIL |
| 4 | AC2 | Section header click toggles content visibility | E2E-UI | P2 | FAIL |
| 5 | AC3 | Boolean → Switch toggle | E2E-UI | P1 | FAIL |
| 6 | AC3 | Enum → Select dropdown with options | E2E-UI | P1 | FAIL |
| 7 | AC3 | Integer → number input with min/max | E2E-UI | P1 | FAIL |
| 8 | AC3 | Decimal → text input | E2E-UI | P2 | FAIL |
| 9 | AC3 | Unit label suffix shown | E2E-UI | P2 | FAIL |
| 10 | AC3 | Invalid value → inline error, no PATCH | E2E-UI | P1 | FAIL |
| 11 | AC4 | Tooltip shows description, unit, range, env var | E2E-UI | P2 | FAIL |
| 12 | AC5 | Debounced PATCH fires ~300ms after change | E2E-UI | P0 | FAIL |
| 13 | AC5 | Success → green flash highlight | E2E-UI | P2 | FAIL |
| 14 | AC5 | Failure → red flash + toast error | E2E-UI | P1 | FAIL |
| 15 | AC5 | Blur with pending change triggers immediate save | E2E-UI | P1 | FAIL |
| 16 | AC6 | Per-field reset: confirmation → POST → value reverts | E2E-UI | P1 | FAIL |
| 17 | AC6 | Per-section reset: confirmation → resets all keys | E2E-UI | P1 | FAIL |
| 18 | AC6 | Reset button disabled when at default | E2E-UI | P2 | FAIL |
| 19 | AC7 | "(default)" label when currentValue === envDefault | E2E-UI | P2 | FAIL |
| 20 | AC7 | Override indicator when value differs | E2E-UI | P2 | FAIL |
| 21 | AC8 | WS config.settings.updated updates value in real-time | E2E-UI | P1 | FAIL |
| 22 | AC8 | WS update cancels pending debounce, accepts server value | E2E-UI | P1 | FAIL |
| 23 | AC9 | Collapse state persists across reload (localStorage) | E2E-UI | P2 | FAIL |
| 24 | AC9 | All sections expanded on first visit | E2E-UI | P2 | FAIL |
| 25 | AC10 | GET /settings returns grouped settings | E2E-API | P1 | PASS |
| 26 | AC10 | PATCH /settings updates and returns state | E2E-API | P1 | PASS |
| 27 | AC10 | POST /settings/reset resets and returns state | E2E-API | P1 | PASS |
| 28 | AC11 | Desktop: two-column grid layout | E2E-UI | P2 | FAIL |
| 29 | AC11 | Mobile: single-column stack | E2E-UI | P3 | FAIL |

### Priority Distribution
- P0: 2 (navigation + debounced save)
- P1: 14 (input types, validation, reset, WS sync, API contracts)
- P2: 11 (visual indicators, tooltips, collapse, responsive desktop)
- P3: 1 (mobile responsive)

### Red Phase Confirmation
- 26 E2E-UI tests → FAIL (no /settings route, page, or components exist)
- 3 E2E-API tests → PASS (backend from story 10-5-2)
- API tests included for regression, not red-phase

### Test File Structure
```
e2e/tests/
├── api/settings-api.spec.ts       # 3 API tests
└── ui/settings-page.spec.ts       # 26 UI tests
```

## Step 4: Test Generation (TDD Red Phase)

### Execution
- **Mode:** subagent (parallel)
- **Subagent A (API):** 3 tests generated — 272 lines
- **Subagent B (E2E):** 26 tests generated — 1003 lines

### TDD Red Phase Validation: PASS
- All 29 tests use `test.skip()` — confirmed
- Zero placeholder assertions — confirmed
- All tests assert expected behavior — confirmed

### Generated Files
| File | Lines | Tests | Priority |
|------|-------|-------|----------|
| `e2e/tests/api/settings-api.spec.ts` | 272 | 3 | P1: 3 |
| `e2e/tests/ui/settings-page.spec.ts` | 1003 | 26 | P0: 2, P1: 12, P2: 11, P3: 1 |

### Fixture Infrastructure
No new fixtures needed — both files use existing `@fixtures` (`apiContext`, `authedPage`). E2E tests use inline `MOCK_SETTINGS_RESPONSE` with `page.route()` mocking.

### Acceptance Criteria Coverage
| AC | Description | Tests | Status |
|----|-------------|-------|--------|
| AC1 | Settings Route & Navigation | #1, #2 | Covered |
| AC2 | Collapsible Grouped Sections | #3, #4 | Covered |
| AC3 | Type-Appropriate Input Controls | #5-#10 | Covered |
| AC4 | InfoTooltip Per Setting | #11 | Covered |
| AC5 | Debounced Inline Save | #12-#15 | Covered |
| AC6 | Reset to Default | #16-#18 | Covered |
| AC7 | Default vs Override Indicator | #19-#20 | Covered |
| AC8 | Real-Time WebSocket Sync | #21-#22 | Covered |
| AC9 | Persistent Section Collapse State | #23-#24 | Covered |
| AC10 | TanStack Query Integration | API #25-#27 | Covered |
| AC11 | Responsive Layout | #25-#26 (UI) | Covered |
| AC12 | API Client Regeneration | N/A (build task) | N/A |
| AC13 | Component Tests | N/A (Vitest, not E2E) | N/A |

### Next Steps (TDD Green Phase)
1. Implement the Settings page (Story 10-5-3 tasks)
2. Remove `test.skip()` from all 29 tests
3. Run `pnpm exec playwright test` → verify PASS
4. Fix any failing tests (implementation or test bugs)
5. Commit passing tests

## Step 5: Validation & Completion

### Final Validation
| Check | Status |
|-------|--------|
| Prerequisites satisfied | PASS |
| Test files created correctly (2 files, 1275 lines) | PASS |
| TypeScript compilation (tsc --noEmit) | PASS |
| All 29 tests use test.skip() | PASS |
| Zero placeholder assertions | PASS |
| Checklist covers 11/13 ACs (2 N/A) | PASS |
| No orphaned CLI/browser sessions | PASS |
| Artifacts in test_artifacts/ | PASS |

### Key Assumptions & Risks
1. **Mock data vs real API shapes**: E2E UI tests use mock data matching the story's API contract spec. During green phase, mock data may need adjustment if backend group names or field keys differ slightly from mock values.
2. **WebSocket simulation**: Tests #21-#22 use `CustomEvent` dispatch to simulate WS events. The actual dashboard may use Socket.IO or native WS — the WS simulation approach may need adaptation during green phase.
3. **data-testid selectors**: Tests assume specific `data-testid` patterns (e.g., `settings-section-exit-strategy`, `setting-field-exitMode`). Implementation must add matching test IDs.
4. **Settings group names**: The API test uses `EXPECTED_GROUPS` matching the `SettingsGroup` enum. E2E test uses the display names from the story spec. If backend uses different display names, tests need updating.

### Recommended Next Workflow
- **Implementation**: `bmad-dev-story` with story file `10-5-3-dashboard-settings-page-ui.md`
- During implementation, progressively remove `test.skip()` and verify green phase
- After all tests pass, run `bmad-testarch-test-review` for quality validation
