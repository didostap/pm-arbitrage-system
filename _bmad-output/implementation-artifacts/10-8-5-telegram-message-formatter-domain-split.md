# Story 10.8.5: Telegram Message Formatter Domain Split

Status: done

## Story

As a developer,
I want the `TelegramMessageFormatter` God File (797 lines, 26 exported formatters + 4 private helpers + constants) split into 7 domain-specific formatter files plus a shared utilities file,
so that each formatter file is focused, under 200 lines, and domain-discoverable.

## Acceptance Criteria

1. **Given** the existing `telegram-message.formatter.ts` (797 lines) in `src/modules/monitoring/formatters/`
   **When** the split is complete
   **Then** the original file is deleted and replaced by 10 new files in the same directory:
   | File | Contents | Est. Lines |
   |------|----------|-----------|
   | `formatter-utils.ts` | 7 shared utilities + constants | ~110 |
   | `detection-formatters.ts` | 1 formatter | ~30 |
   | `execution-formatters.ts` | 4 formatters | ~171 |
   | `exit-formatters.ts` | 1 formatter | ~45 |
   | `risk-formatters.ts` | 5 formatters | ~120 |
   | `platform-formatters.ts` | 5 formatters | ~114 |
   | `system-formatters.ts` | 5 formatters | ~105 |
   | `resolution-formatters.ts` | 4 formatters | ~140 |
   | `unwind-formatters.ts` | 1 formatter (`formatAutoUnwind`) | ~48 |
   | `index.ts` | Barrel re-exports | ~20 |

2. **Given** the 200-line-per-file target
   **When** each domain file is measured
   **Then** all domain files are under 200 lines and `formatter-utils.ts` is under 200 lines.

3. **Given** existing consumers (`telegram-alert.service.ts`, `daily-summary.service.ts`) import from `telegram-message.formatter`
   **When** the barrel `index.ts` re-exports all public functions
   **Then** consumers import from `./formatters/index` (or `./formatters`) with zero logic changes.

4. **Given** the existing test suite in `telegram-message.formatter.spec.ts` (609 lines, 50+ tests)
   **When** tests are split into domain-specific spec files matching the new source files
   **Then** all tests pass with zero behavioral changes, zero skipped tests, and equivalent coverage.

5. **Given** TypeScript strict mode is enabled
   **When** all new files compile
   **Then** zero compilation errors, zero unused imports, zero unused variables.

6. **Given** the `FORMATTER_REGISTRY` in `telegram-alert.service.ts` maps event names to formatter functions
   **When** imports are updated to use the barrel
   **Then** the registry logic and all 25 event-to-formatter mappings are unchanged.

7. **Given** the initial decomposition is a zero-functional-change refactor, with targeted post-CR improvements applied to 6 formatters
   **When** the full test suite runs
   **Then** the total test count is equal to or greater than the baseline (currently ~2934) with no regressions.

8. **Given** post-internal-review findings (F1-F8) identified escaping gaps, missing data rendering, and a truncation fragility
   **When** those fixes are applied during this story
   **Then** the following functional improvements are included beyond verbatim copy:
   - F1: `smartTruncate` TAG_CLOSE_RESERVE=50 prevents closing tags from being sliced off
   - F2: `escapeHtml()` on `formatClusterLimitBreached` triage values
   - F3: `escapeHtml()` on `formatLimitBreached` Decimal output (defense-in-depth)
   - F4: EXIT_LABELS map + raw-value fallback in `formatExitTriggered`
   - F5: Tests for 6 previously untested formatters
   - F6: `formatPlatformDegraded` renders metadata (JSON, 200-char truncated, escaped)
   - F7: `formatExecutionFailed` renders context entries (max 5, escaped)
   - F8: `formatSingleLegExposure` shows attemptedPrice/attemptedSize in Failed Leg section

## Tasks / Subtasks

- [x] Task 1: Establish baseline and create `formatter-utils.ts` (AC: 1, 2, 5)
  - [x] 1.1 Run `pnpm test` — record baseline test count
  - [x] 1.2 Create `src/modules/monitoring/formatters/formatter-utils.ts` with:
    - Constants: `SEVERITY_EMOJI`, `MAX_MESSAGE_LENGTH`, `HEADER_RESERVE`, `FOOTER_RESERVE`
    - Exported: `escapeHtml()`, `smartTruncate()`, `closeUnclosedTags()`, `formatTimestamp()`, `formatCorrelationFooter()`, `paperModeTag()`
    - **Note:** `closeUnclosedTags`, `formatTimestamp`, `formatCorrelationFooter`, `paperModeTag` are currently file-private — they must become exported so domain files can import them
  - [x] 1.3 Create `src/modules/monitoring/formatters/formatter-utils.spec.ts` — migrate `escapeHtml` (7 tests) and `smartTruncate` (3 tests) describe blocks from the original spec

- [x] Task 2: Create 7 domain formatter files (AC: 1, 2, 5)
  - [x] 2.1 `detection-formatters.ts` — `formatOpportunityIdentified`
  - [x] 2.2 `execution-formatters.ts` — `formatOrderFilled`, `formatExecutionFailed`, `formatSingleLegExposure`, `formatSingleLegResolved`, `formatAutoUnwind`
  - [x] 2.3 `exit-formatters.ts` — `formatExitTriggered`
  - [x] 2.4 `risk-formatters.ts` — `formatLimitApproached`, `formatLimitBreached`, `formatClusterLimitBreached`, `formatAggregateClusterLimitBreached`, `formatBankrollUpdated`
  - [x] 2.5 `platform-formatters.ts` — `formatPlatformDegraded`, `formatPlatformRecovered`, `formatOrderbookStale`, `formatOrderbookRecovered`, `formatDataDivergence`
  - [x] 2.6 `system-formatters.ts` — `formatTradingHalted`, `formatTradingResumed`, `formatReconciliationDiscrepancy`, `formatSystemHealthCritical`, `formatTestAlert`
  - [x] 2.7 `resolution-formatters.ts` — `formatResolutionDivergence`, `formatResolutionPollCompleted`, `formatCalibrationCompleted`, `formatShadowDailySummary`
  - [x] 2.8 Each file imports only needed utilities from `./formatter-utils` — copy function bodies verbatim, no logic changes

- [x] Task 3: Create barrel `index.ts` and update consumers (AC: 1, 3, 6)
  - [x] 3.1 Create `src/modules/monitoring/formatters/index.ts` with `export *` from all 8 source files
  - [x] 3.2 Update `telegram-alert.service.ts` imports: change from `./formatters/telegram-message.formatter` to `./formatters` (or `./formatters/index`)
  - [x] 3.3 Update `daily-summary.service.ts` import of `escapeHtml`: change to `./formatters`
  - [x] 3.4 Verify no other files import from `telegram-message.formatter` (grep check)

- [x] Task 4: Split test file into domain-specific specs (AC: 4, 5)
  - [x] 4.1 Create `detection-formatters.spec.ts` — migrate `formatOpportunityIdentified` tests
  - [x] 4.2 Create `execution-formatters.spec.ts` — migrate `formatOrderFilled`, `formatExecutionFailed`, `formatSingleLegExposure`, `formatSingleLegResolved` tests + `HTML escaping in formatters prevents injection`, `correlationId inclusion`, `timestamps in ISO format` cross-cutting tests
  - [x] 4.3 Create `exit-formatters.spec.ts` — migrate `formatExitTriggered` tests
  - [x] 4.4 Create `risk-formatters.spec.ts` — migrate `formatLimitApproached`, `formatLimitBreached` tests
  - [x] 4.5 Create `platform-formatters.spec.ts` — migrate `formatPlatformDegraded`, `formatPlatformRecovered`, `formatOrderbookStale`, `formatOrderbookRecovered` tests
  - [x] 4.6 Create `system-formatters.spec.ts` — migrate `formatTradingHalted`, `formatTradingResumed`, `formatReconciliationDiscrepancy`, `formatSystemHealthCritical`, `formatTestAlert` tests
  - [x] 4.7 Create `resolution-formatters.spec.ts` — migrate `formatResolutionDivergence`, `formatResolutionPollCompleted`, `formatCalibrationCompleted` tests + `classifyEventSeverity — Story 8.3 events` block
  - [x] 4.8 **Note:** `classifyEventSeverity` tests (4 base + 5 Story 8.3) test a function in `event-severity.ts`, NOT in the formatter. Check if `event-severity.spec.ts` already exists — if yes, move these tests there. If no, create `event-severity.spec.ts` and move them. Do NOT leave severity classification tests in a formatter spec file.

- [x] Task 5: Delete original file and final verification (AC: 4, 5, 7)
  - [x] 5.1 Delete `telegram-message.formatter.ts`
  - [x] 5.2 Delete `telegram-message.formatter.spec.ts`
  - [x] 5.3 `pnpm lint` — zero errors
  - [x] 5.4 `pnpm test` — all pass, count >= baseline
  - [x] 5.5 Verify zero behavioral changes (grep for any remaining references to deleted files)

## Dev Notes

### This is a God FILE decomposition, NOT a God Object decomposition

Unlike stories 10-8-1 through 10-8-4 which decomposed class-based services with DI, this story splits a file of standalone pure functions. Key differences:
- **No DI changes** — formatters are pure functions, not injectable services
- **No facade needed** — barrel `index.ts` provides backward-compatible re-exports
- **No constructor deps** — functions import only from `formatter-utils.ts` and `decimal.js`
- **No module registration** — `monitoring.module.ts` unchanged (formatters are not providers)
- **Simpler test migration** — tests move to domain specs with updated import paths only

### Design Spike Method-to-File Allocation (Authoritative Source)

Follow the allocation table from `10-8-0-god-object-decomposition-design-spike.md` Section 4.5 exactly. Key allocations that may seem non-obvious:
- `formatAutoUnwind` → `execution-formatters.ts` (not exit — it's execution result formatting)
- `formatShadowDailySummary` → `resolution-formatters.ts` (not system — shadow is resolution-adjacent)
- `formatOpportunityIdentified` → `detection-formatters.ts` (standalone, only 1 function — this is correct per domain boundaries)
- `formatBankrollUpdated` → `risk-formatters.ts` (not config — bankroll is a risk concern)
- `formatDataDivergence` → `platform-formatters.ts` (not detection — it's platform data quality)

### Private → Exported Visibility Change

Currently file-private helpers (`closeUnclosedTags`, `formatTimestamp`, `formatCorrelationFooter`, `paperModeTag`) must become exported from `formatter-utils.ts` so domain files can import them. This is the only "behavioral" change — previously unreachable functions become importable. No consumer outside `formatters/` should import these directly; the barrel can choose to re-export only the public API (`escapeHtml`, `smartTruncate`, plus all 26 domain formatters).

### Consumer Import Updates

Only 2 files import from the formatter:
1. **`telegram-alert.service.ts`** (line ~5-30) — imports 24 formatters + `escapeHtml` via named imports. Update to: `import { formatOrderFilled, ... } from './formatters';`
2. **`daily-summary.service.ts`** (line ~14) — imports only `escapeHtml`. Update to: `import { escapeHtml } from './formatters';`

### Test Coverage Gap (Pre-existing, addressed post-CR)

6 formatters lacked unit tests (added in recent stories without corresponding specs):
- `formatClusterLimitBreached`, `formatAggregateClusterLimitBreached`, `formatBankrollUpdated`
- `formatDataDivergence`, `formatShadowDailySummary`, `formatAutoUnwind`

Post-internal-review (F5) expanded scope to include tests for all 6 formatters. This was originally out of scope but approved as part of the AC8 functional improvements.

### Cross-Cutting Test Placement

The original spec has cross-cutting describe blocks that test formatter behavior generically:
- `HTML escaping in formatters prevents injection` — place in `execution-formatters.spec.ts` (uses `formatOrderFilled` as example)
- `correlationId inclusion` — place in `execution-formatters.spec.ts` (uses `formatOrderFilled` as example)
- `timestamps in ISO format` — place in `execution-formatters.spec.ts` (uses `formatOrderFilled` as example)
- `classifyEventSeverity` blocks — these test `event-severity.ts`, not the formatter. If no `event-severity.spec.ts` exists, place in `resolution-formatters.spec.ts` (Story 8.3 block is there).

### File Naming Convention

Design spike uses `{domain}-formatters.ts` (plural). Follow exactly:
- `detection-formatters.ts` (not `detection.formatter.ts`)
- `formatter-utils.ts` (not `formatter.utils.ts`)
- `index.ts` (barrel)

### Import Pattern for Domain Files

```typescript
// detection-formatters.ts
import Decimal from 'decimal.js';
import { BaseEvent } from '../../../common/events/base.event.js';
import {
  escapeHtml,
  smartTruncate,
  formatCorrelationFooter,
  SEVERITY_EMOJI,
} from './formatter-utils.js';
```

Each domain file imports only the utilities it actually uses.

### Barrel Re-export Pattern

```typescript
// index.ts
export { escapeHtml, smartTruncate } from './formatter-utils.js';
export * from './detection-formatters.js';
export * from './execution-formatters.js';
export * from './exit-formatters.js';
export * from './risk-formatters.js';
export * from './platform-formatters.js';
export * from './system-formatters.js';
export * from './resolution-formatters.js';
export * from './unwind-formatters.js';
```

Note: Only re-export `escapeHtml` and `smartTruncate` from utils (the public API). Do NOT re-export private helpers (`closeUnclosedTags`, `formatTimestamp`, `formatCorrelationFooter`, `paperModeTag`) — they are internal to the formatters directory.

### Project Structure Notes

All new files go in the existing `src/modules/monitoring/formatters/` directory. No new directories needed. The monitoring module registration (`monitoring.module.ts`) requires zero changes — formatters are standalone functions, not NestJS providers.

### References

- [Source: `_bmad-output/implementation-artifacts/10-8-0-design-doc.md` Section 4.5 — Method-to-File Allocation Table]
- [Source: `_bmad-output/implementation-artifacts/10-8-4-dashboard-service-decomposition.md` — Previous story decomposition patterns]
- [Source: `CLAUDE.md` — No God Objects or God Files section, 400-line file limit]
- [Source: `CLAUDE.md` — Testing section, assertion depth, co-located specs]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation with zero compilation errors, zero test failures.

### Completion Notes List

- Baseline: 2934 tests, 173 test files
- Split 797-line `telegram-message.formatter.ts` (26 exports + 4 private helpers + constants) into 8 focused source files + barrel
- All domain files under 200 lines (largest: `execution-formatters.ts` at 200 lines exactly)
- `formatter-utils.ts`: 107 lines — 4 constants + 6 exported functions (4 previously private)
- Barrel `index.ts`: re-exports only public API (`escapeHtml`, `smartTruncate`, + 26 domain formatters); internal helpers not re-exported
- Consumer imports updated: `telegram-alert.service.ts` and `daily-summary.service.ts` now import from `./formatters/index.js`
- Test split: 42 tests from original spec distributed across 8 new spec files (7 formatter + 1 event-severity)
- Created `event-severity.spec.ts` (did not exist) — moved 9 `classifyEventSeverity` tests out of formatter spec per Task 4.8
- Final: 2934 tests passing, 181 test files (+9 new, -1 deleted), zero regressions, zero remaining references to deleted files
- Zero functional changes — verbatim function body copies, import path updates only
- Post-decomposition code review fixes (Lad MCP, 8 findings):
  - F1: smartTruncate defensive TAG_CLOSE_RESERVE=50 prevents closing tags from being sliced off
  - F2: escapeHtml() on formatClusterLimitBreached triage values (expectedEdge, capitalDeployed)
  - F3: escapeHtml() on formatLimitBreached Decimal output (defense-in-depth)
  - F4: EXIT_LABELS map + raw-value fallback replaces hardcoded "Time-Based" default in formatExitTriggered
  - F5: Added tests for 6 untested formatters (formatAutoUnwind, formatShadowDailySummary, formatClusterLimitBreached, formatAggregateClusterLimitBreached, formatBankrollUpdated, formatDataDivergence)
  - F6: formatPlatformDegraded now renders metadata (JSON, 200-char truncated, escaped)
  - F7: formatExecutionFailed now renders context entries (max 5, escaped)
  - F8: formatSingleLegExposure now shows attemptedPrice/attemptedSize in Failed Leg section
  - Extracted formatAutoUnwind to unwind-formatters.ts (execution-formatters.ts was at 200 lines)
- Final: 2950 tests passing, 182 test files, zero regressions

### Change Log

- 2026-03-25: Story 10-8-5 implemented — God File decomposition of telegram-message.formatter.ts into 7 domain files + utils + barrel
- 2026-03-25: Post-CR fixes — 8 Lad MCP findings addressed: smartTruncate tag closure, escaping gaps, exit type fallback, context/metadata rendering, 6 formatter test coverage gaps, formatAutoUnwind extraction

### File List

**New files:**
- `src/modules/monitoring/formatters/formatter-utils.ts`
- `src/modules/monitoring/formatters/formatter-utils.spec.ts`
- `src/modules/monitoring/formatters/detection-formatters.ts`
- `src/modules/monitoring/formatters/detection-formatters.spec.ts`
- `src/modules/monitoring/formatters/execution-formatters.ts`
- `src/modules/monitoring/formatters/execution-formatters.spec.ts`
- `src/modules/monitoring/formatters/exit-formatters.ts`
- `src/modules/monitoring/formatters/exit-formatters.spec.ts`
- `src/modules/monitoring/formatters/risk-formatters.ts`
- `src/modules/monitoring/formatters/risk-formatters.spec.ts`
- `src/modules/monitoring/formatters/platform-formatters.ts`
- `src/modules/monitoring/formatters/platform-formatters.spec.ts`
- `src/modules/monitoring/formatters/system-formatters.ts`
- `src/modules/monitoring/formatters/system-formatters.spec.ts`
- `src/modules/monitoring/formatters/resolution-formatters.ts`
- `src/modules/monitoring/formatters/resolution-formatters.spec.ts`
- `src/modules/monitoring/formatters/unwind-formatters.ts`
- `src/modules/monitoring/formatters/unwind-formatters.spec.ts`
- `src/modules/monitoring/formatters/index.ts`
- `src/modules/monitoring/event-severity.spec.ts`

**Modified files:**
- `src/modules/monitoring/telegram-alert.service.ts` (import path)
- `src/modules/monitoring/daily-summary.service.ts` (import path)

**Deleted files:**
- `src/modules/monitoring/formatters/telegram-message.formatter.ts`
- `src/modules/monitoring/formatters/telegram-message.formatter.spec.ts`
