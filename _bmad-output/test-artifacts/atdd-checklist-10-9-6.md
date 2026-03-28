---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-28'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-9-6-historical-data-freshness-incremental-updates.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-priorities-matrix.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
---

# ATDD Checklist — Story 10-9.6: Historical Data Freshness & Incremental Updates

**Date:** 2026-03-28
**Author:** Arbi
**Primary Test Level:** Unit (Vitest) + Integration (event wiring) + Component (React Testing Library)
**Repos:** `pm-arbitrage-engine/` (primary), `pm-arbitrage-dashboard/` (frontend)

---

## Story Summary

**As an** operator
**I want** the historical data to stay current with incremental updates
**So that** backtests always reflect the latest available market data

---

## Acceptance Criteria

1. Incremental fetch — only new data since last ingestion (configurable cron, default daily)
2. PMXT Archive — check for new hourly snapshots since last downloaded file
3. OddsPipe/Predexon — re-run match validation, detect new external-only pairs
4. Kalshi cutoff advancement — dual-partition routing handles transparently
5. Data quality re-checks — re-run on new data
6. Staleness detection — stale data warnings via EventEmitter2
7. Dashboard freshness indicators — REST endpoint, WS broadcast, frontend panel

---

## Test Strategy

| Level | Scope | Framework | Location |
|-------|-------|-----------|----------|
| Unit | Service logic, config, DTOs, event classes, concurrency guards | Vitest + vi.fn() mocks | `pm-arbitrage-engine/src/**/*.spec.ts` |
| Integration | Event wiring (@OnEvent → handler), module registration | Vitest + expectEventHandled() | `pm-arbitrage-engine/src/common/testing/event-wiring-audit.spec.ts` |
| Component | Frontend panel rendering, hook behavior | Vitest + @testing-library/react | `pm-arbitrage-dashboard/src/**/*.spec.tsx` |

**Priority rationale:**
- P0: Data integrity (incremental correctness, staleness detection, concurrency guards)
- P1: Operational visibility (dashboard freshness, event payloads, error isolation)
- P2: Edge cases (zero-new-data, single-provider degradation, OddsPipe 30-day cap)

---

## Failing Tests Created (RED Phase)

### Task 1: DataSourceFreshness Prisma Model + Migration (2 tests)

**File:** `pm-arbitrage-engine/prisma/schema.prisma` (MODIFIED) + migration (AUTO-GENERATED)

No dedicated spec file — model existence verified transitively. Schema-level checks:

- [ ] **Test:** [P0] `DataSourceFreshness` model exists in Prisma schema with all required fields (source, lastSuccessfulAt, lastAttemptAt, recordsFetched, contractsUpdated, status, errorMessage)
  - **Status:** RED — model does not exist in schema.prisma
  - **Verifies:** AC #1, #6, #7
  - **File:** inline in `incremental-ingestion.service.spec.ts` (Task 3) — first test verifies Prisma mock shape

- [ ] **Test:** [P0] `DataSourceFreshness` has unique constraint on `source` field
  - **Status:** RED — model does not exist
  - **Verifies:** AC #1 — one row per source, upsert semantics
  - **File:** verified by upsert test in Task 3

---

### Task 2: Config — Cron Expression + Staleness Thresholds (7 tests)

**File:** `pm-arbitrage-engine/src/common/config/env.schema.spec.ts` (MODIFIED, +4 tests)
**File:** `pm-arbitrage-engine/src/common/config/config-defaults.spec.ts` (MODIFIED, +3 tests)

**env.schema.ts — 4 tests:**

- [ ] **Test:** [P1] `INCREMENTAL_INGESTION_CRON_EXPRESSION` defaults to `'0 0 2 * * *'`
  - **Status:** RED — env var not defined in env.schema.ts
  - **Verifies:** AC #1 — configurable cron schedule, default daily 2 AM UTC

- [ ] **Test:** [P1] `INCREMENTAL_INGESTION_ENABLED` defaults to `true`
  - **Status:** RED — env var not defined
  - **Verifies:** AC #1 — enabled by default

- [ ] **Test:** [P1] `STALENESS_THRESHOLD_PLATFORM_MS` defaults to `129600000` (36 hours)
  - **Status:** RED — env var not defined
  - **Verifies:** AC #6 — staleness threshold for platform APIs

- [ ] **Test:** [P1] `STALENESS_THRESHOLD_PMXT_MS` defaults to `172800000` (48 hours), `STALENESS_THRESHOLD_ODDSPIPE_MS` defaults to `129600000`, `STALENESS_THRESHOLD_VALIDATION_MS` defaults to `259200000`
  - **Status:** RED — env vars not defined
  - **Verifies:** AC #6 — per-category staleness thresholds

**config-defaults.ts — 3 tests:**

- [ ] **Test:** [P1] config-defaults maps `incrementalIngestionCronExpression` to `INCREMENTAL_INGESTION_CRON_EXPRESSION`
  - **Status:** RED — config entry not defined
  - **Verifies:** AC #1

- [ ] **Test:** [P1] config-defaults maps `incrementalIngestionEnabled` to `INCREMENTAL_INGESTION_ENABLED`
  - **Status:** RED — config entry not defined
  - **Verifies:** AC #1

- [ ] **Test:** [P1] config-defaults maps staleness threshold keys to their env vars
  - **Status:** RED — config entries not defined
  - **Verifies:** AC #6

---

### Task 3: IncrementalIngestionService — Cron Scheduling + Coordination (12 tests)

**File:** `pm-arbitrage-engine/src/modules/backtesting/ingestion/incremental-ingestion.service.spec.ts` (NEW, ~300 lines)

**Cron + enabled flag — 3 tests:**

- [ ] **Test:** [P0] `handleCron()` should return immediately when `INCREMENTAL_INGESTION_ENABLED` is false
  - **Status:** RED — IncrementalIngestionService does not exist
  - **Verifies:** AC #1 — configurable enabled flag
  - **Assert:** `runIncrementalRefresh` NOT called, no events emitted

- [ ] **Test:** [P0] `handleCron()` should call `runIncrementalRefresh()` when enabled and no concurrency conflict
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — cron triggers incremental refresh

- [ ] **Test:** [P1] `handleCron()` should have `@Cron` decorator with expression from config and `{ timeZone: 'UTC' }`
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — cron scheduling pattern matches daily-summary.service.ts

**Concurrency guard — 3 tests:**

- [ ] **Test:** [P0] `handleCron()` should skip when own `_isRunning` flag is true
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — no concurrent incremental runs
  - **Assert:** `runIncrementalRefresh` NOT called, debug-level log emitted

- [ ] **Test:** [P0] `handleCron()` should skip when `IngestionOrchestratorService.isRunning` is true
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — no conflict with full ingestion
  - **Assert:** `runIncrementalRefresh` NOT called

- [ ] **Test:** [P1] `_isRunning` flag should be reset to false after `runIncrementalRefresh()` completes (even on error)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — flag cleanup prevents permanent lockout
  - **Assert:** after error thrown by IncrementalFetchService, flag is false

**DataSourceFreshness upsert — 3 tests:**

- [ ] **Test:** [P0] `runIncrementalRefresh()` should upsert DataSourceFreshness row per source with status, recordsFetched, contractsUpdated, lastAttemptAt
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1, #7 — freshness tracking
  - **Assert:** `prisma.dataSourceFreshness.upsert` called with `expect.objectContaining({ where: { source }, update: { status: 'success', recordsFetched, contractsUpdated, lastSuccessfulAt, lastAttemptAt } })`

- [ ] **Test:** [P0] `runIncrementalRefresh()` should update `lastSuccessfulAt` to `now()` even when 0 new records fetched
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — source was reachable, important for staleness accuracy
  - **Assert:** `lastSuccessfulAt` is set when `recordsFetched === 0`

- [ ] **Test:** [P1] `runIncrementalRefresh()` should upsert DataSourceFreshness with `status: 'failed'` and `errorMessage` when source fetch fails
  - **Status:** RED — service does not exist
  - **Verifies:** AC #6 — failed source tracking
  - **Assert:** upsert called with `{ status: 'failed', errorMessage: expect.any(String) }`

**Staleness check — 3 tests:**

- [ ] **Test:** [P0] `runIncrementalRefresh()` should emit `INCREMENTAL_DATA_STALE` event for sources exceeding staleness threshold
  - **Status:** RED — service does not exist
  - **Verifies:** AC #6 — stale data warning
  - **Assert:** `emitter.emit` called with `EVENT_NAMES.INCREMENTAL_DATA_STALE` and payload containing `expect.objectContaining({ source, lastSuccessfulAt, thresholdMs, ageMs })`

- [ ] **Test:** [P1] `runIncrementalRefresh()` should NOT emit `INCREMENTAL_DATA_STALE` for sources within staleness threshold
  - **Status:** RED — service does not exist
  - **Verifies:** AC #6 — no false alarms
  - **Assert:** `INCREMENTAL_DATA_STALE` NOT emitted when `ageMs < thresholdMs`

- [ ] **Test:** [P0] `runIncrementalRefresh()` should emit `INCREMENTAL_DATA_FRESHNESS_UPDATED` after every run with per-source summary
  - **Status:** RED — service does not exist
  - **Verifies:** AC #6, #7 — freshness event for dashboard
  - **Assert:** `emitter.emit` called with `EVENT_NAMES.INCREMENTAL_DATA_FRESHNESS_UPDATED` and payload containing `expect.objectContaining({ sources: expect.arrayContaining([expect.objectContaining({ source, recordsFetched, status })]) })`

---

### Task 4: IncrementalFetchService — Per-Source Data Fetching (14 tests)

**File:** `pm-arbitrage-engine/src/modules/backtesting/ingestion/incremental-fetch.service.spec.ts` (NEW, ~400 lines)

**Incremental start computation — 3 tests:**

- [ ] **Test:** [P0] `getIncrementalStart()` should return MAX(timestamp) from HistoricalPrice for given source+contractId
  - **Status:** RED — IncrementalFetchService does not exist
  - **Verifies:** AC #1 — incremental, not full re-download
  - **Assert:** `prisma.historicalPrice.aggregate` called with `{ where: { source, contractId }, _max: { timestamp: true } }`, returns max timestamp

- [ ] **Test:** [P0] `getIncrementalStart()` should fall back to dateRange.start when no existing data (null MAX)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — first-time ingestion falls back to full range

- [ ] **Test:** [P2] `getIncrementalStart()` for OddsPipe should cap start to `max(maxTimestamp, now - 30 days)` for free tier window
  - **Status:** RED — service does not exist
  - **Verifies:** AC #3 — OddsPipe 30-day rolling window limit
  - **Assert:** when maxTimestamp is older than 30 days, start is capped to now - 30 days

**Platform data fetching — 3 tests:**

- [ ] **Test:** [P0] `fetchPlatformData()` should call KalshiHistoricalService.ingestPrices() and ingestTrades() with incremental start per contract
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1, #4 — delegates to existing service with narrowed date range
  - **Assert:** `kalshiHistorical.ingestPrices` called with `expect.objectContaining({ start: incrementalStart, end: expect.any(Date) })`

- [ ] **Test:** [P0] `fetchPlatformData()` should call PolymarketHistoricalService.ingestPrices() with incremental start
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — Polymarket incremental fetch

- [ ] **Test:** [P1] `fetchPlatformData()` should return `Map<HistoricalDataSource, { recordCount, contractCount, error? }>` per source
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — result aggregation for freshness tracking

**Third-party data fetching — 2 tests:**

- [ ] **Test:** [P1] `fetchThirdPartyData()` should call PmxtArchiveService.discoverFiles() and ingestDepth() for new/failed files
  - **Status:** RED — service does not exist
  - **Verifies:** AC #2 — PMXT new file detection via DataCatalog

- [ ] **Test:** [P1] `fetchThirdPartyData()` should call OddsPipeService.ingestPrices() with incremental start for OHLCV refresh
  - **Status:** RED — service does not exist
  - **Verifies:** AC #3 — OddsPipe incremental OHLCV

**Error isolation — 3 tests:**

- [ ] **Test:** [P0] per-source error isolation: if Kalshi fetch fails after retries, continue with remaining sources
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — fault isolation
  - **Assert:** Polymarket/PMXT/OddsPipe still called after Kalshi throws; result map includes error for Kalshi, success for others

- [ ] **Test:** [P1] per-source retry: 3 attempts with exponential backoff (1s, 2s, 4s) via withRetry() before marking failed
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — transient failure resilience
  - **Assert:** source service called 3 times before error recorded

- [ ] **Test:** [P1] all fetch failures wrapped in SystemHealthError(4210) before recording
  - **Status:** RED — service does not exist
  - **Verifies:** Architecture — SystemError compliance
  - **Assert:** error in result map is instance of SystemHealthError with code 4210

**Quality re-check — 1 test:**

- [ ] **Test:** [P0] after each contract fetch, calls `qualityAssessor.runQualityAssessment()` with narrowed date range
  - **Status:** RED — service does not exist
  - **Verifies:** AC #5 — data quality re-checks on new data
  - **Assert:** `qualityAssessor.runQualityAssessment` called with `expect.objectContaining({ start: incrementalStart })` per contract

**Zero-new-data scenario — 2 tests:**

- [ ] **Test:** [P2] when all sources return 0 new records, result map has recordCount: 0 for each source (no errors)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #1 — graceful handling when data is already current

- [ ] **Test:** [P2] when Kalshi returns data from cutoff advancement zone (previously live-only, now historical), existing dual-partition routing handles transparently
  - **Status:** RED — service does not exist
  - **Verifies:** AC #4 — cutoff advancement is a black box
  - **Assert:** no special cutoff handling code; just passes `{ start: maxTimestamp, end: now }`

---

### Task 5: Match Validation Pair Refresh (4 tests)

**File:** `pm-arbitrage-engine/src/modules/backtesting/ingestion/incremental-fetch.service.spec.ts` (appended to Task 4 file)

- [ ] **Test:** [P1] `fetchThirdPartyData()` calls `MatchValidationService.runValidation()` and compares `externalOnlyCount` with previous report
  - **Status:** RED — service does not exist
  - **Verifies:** AC #3 — detect new external-only pairs
  - **Assert:** `matchValidation.runValidation()` called; when new report has higher `externalOnlyCount`, delta logged

- [ ] **Test:** [P2] single-provider degradation: if OddsPipe unreachable, Predexon validation still runs (and vice versa)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #3 — graceful degradation mirrors MatchValidationService pattern
  - **Assert:** one provider fails, other still validated, no run failure

- [ ] **Test:** [P1] DataSourceFreshness rows updated separately for ODDSPIPE and PREDEXON validation
  - **Status:** RED — service does not exist
  - **Verifies:** AC #3 — per-source freshness tracking
  - **Assert:** upsert called twice — once for ODDSPIPE, once for PREDEXON

- [ ] **Test:** [P2] when previous validation report does not exist (first run), no comparison error — just log baseline
  - **Status:** RED — service does not exist
  - **Verifies:** AC #3 — first-run edge case

---

### Task 6: Staleness Detection + Warning Events (5 tests)

**File:** `pm-arbitrage-engine/src/common/events/backtesting.events.spec.ts` (MODIFIED, +3 tests)
**File:** `pm-arbitrage-engine/src/common/events/event-catalog.ts` (verified via existing spec pattern)

**Event catalog — 2 tests:**

- [ ] **Test:** [P0] `EVENT_NAMES.INCREMENTAL_DATA_STALE` should equal `'backtesting.incremental.stale'`
  - **Status:** RED — event name not defined in event-catalog.ts
  - **Verifies:** AC #6 — event naming follows dot-notation convention

- [ ] **Test:** [P0] `EVENT_NAMES.INCREMENTAL_DATA_FRESHNESS_UPDATED` should equal `'backtesting.incremental.freshness-updated'`
  - **Status:** RED — event name not defined
  - **Verifies:** AC #6, #7 — freshness event for dashboard broadcast

**Event classes — 3 tests:**

- [ ] **Test:** [P0] `IncrementalDataStaleEvent` should carry `source`, `lastSuccessfulAt`, `thresholdMs`, `ageMs`, `severity`
  - **Status:** RED — event class does not exist in backtesting.events.ts
  - **Verifies:** AC #6 — staleness event payload for Telegram/monitoring
  - **Assert:** `new IncrementalDataStaleEvent(payload)` has all fields with correct types

- [ ] **Test:** [P0] `IncrementalDataFreshnessUpdatedEvent` should carry `sources` array with per-source `{ source, recordsFetched, contractsUpdated, status, lastSuccessfulAt }`
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #6, #7 — freshness summary event
  - **Assert:** payload `sources` array contains `expect.objectContaining(...)` for each source

- [ ] **Test:** [P1] Both event classes should extend `BaseEvent` with correct `eventName` property
  - **Status:** RED — event classes do not exist
  - **Verifies:** Architecture — event class pattern compliance

---

### Task 7: Dashboard Freshness REST Endpoint + WebSocket (8 tests)

**File:** `pm-arbitrage-engine/src/modules/backtesting/controllers/historical-data.controller.spec.ts` (MODIFIED, +4 tests)
**File:** `pm-arbitrage-engine/src/dashboard/dashboard.gateway.spec.ts` (MODIFIED, +2 tests)
**File:** `pm-arbitrage-engine/src/modules/backtesting/dto/data-source-freshness.dto.spec.ts` (NEW, +2 tests)

**REST endpoint — 4 tests:**

- [ ] **Test:** [P0] `GET /api/backtesting/freshness` should return all DataSourceFreshness rows with server-computed `freshStatus`
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #7 — freshness data visible on dashboard
  - **Assert:** response matches `{ data: { sources: [...], overallFresh, staleSources, nextScheduledRun }, timestamp }`

- [ ] **Test:** [P1] `freshStatus` computation: 'fresh' when ageMs < 50% threshold, 'warning' when 50-100%, 'stale' when >100%, 'never' when lastSuccessfulAt is null
  - **Status:** RED — endpoint/DTO does not exist
  - **Verifies:** AC #7 — server-computed status avoids frontend logic duplication
  - **Assert:** each freshStatus value tested with appropriate ageMs/threshold ratios

- [ ] **Test:** [P1] response includes `latestDataTimestamp` derived from MAX(timestamp) per source from data tables
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #7 — actual data timestamp separate from fetch timestamp

- [ ] **Test:** [P2] response includes `nextScheduledRun` derived from cron expression
  - **Status:** RED — endpoint does not exist
  - **Verifies:** AC #7 — operator knows when next refresh runs

**DTO — 2 tests:**

- [ ] **Test:** [P1] `DataSourceFreshnessDto` should include all fields: source, lastSuccessfulAt, lastAttemptAt, recordsFetched, contractsUpdated, status, errorMessage, freshStatus, stalenessThresholdMs, timeSinceLastSuccessMs, latestDataTimestamp
  - **Status:** RED — DTO does not exist
  - **Verifies:** AC #7 — DTO completeness

- [ ] **Test:** [P1] `DataSourceFreshnessDto.freshStatus` is constrained to `'fresh' | 'warning' | 'stale' | 'never'`
  - **Status:** RED — DTO does not exist
  - **Verifies:** AC #7 — type safety

**WebSocket gateway — 2 tests:**

- [ ] **Test:** [P0] DashboardGateway should have `@OnEvent` handler for `INCREMENTAL_DATA_FRESHNESS_UPDATED` that broadcasts to WS clients
  - **Status:** RED — handler does not exist in dashboard.gateway.ts
  - **Verifies:** AC #7 — real-time freshness updates to dashboard
  - **Assert:** when event emitted, all connected WS clients receive message with `type: 'backtesting.incremental.freshness-updated'`

- [ ] **Test:** [P1] DashboardGateway should have `@OnEvent` handler for `INCREMENTAL_DATA_STALE` that broadcasts staleness warning to WS clients
  - **Status:** RED — handler does not exist
  - **Verifies:** AC #6, #7 — staleness warning on dashboard
  - **Assert:** WS message includes `type: 'backtesting.incremental.stale'` and source details

---

### Task 7 (Event Wiring): Integration Tests (2 tests)

**File:** `pm-arbitrage-engine/src/common/testing/event-wiring-audit.spec.ts` (MODIFIED, +2 tests)

- [ ] **Test:** [P0] `expectEventHandled()` verifies `INCREMENTAL_DATA_FRESHNESS_UPDATED` event wiring from emitter to DashboardGateway handler
  - **Status:** RED — @OnEvent handler does not exist
  - **Verifies:** AC #7 — event actually reaches gateway via real EventEmitter2
  - **Assert:** `expectEventHandled({ module, eventName: EVENT_NAMES.INCREMENTAL_DATA_FRESHNESS_UPDATED, payload, handlerClass: DashboardGateway, handlerMethod: 'broadcastFreshnessUpdate' })`

- [ ] **Test:** [P1] `expectEventHandled()` verifies `INCREMENTAL_DATA_STALE` event wiring from emitter to DashboardGateway handler
  - **Status:** RED — handler does not exist
  - **Verifies:** AC #6 — staleness warning wiring
  - **Assert:** `expectEventHandled({ module, eventName: EVENT_NAMES.INCREMENTAL_DATA_STALE, payload, handlerClass: DashboardGateway, handlerMethod: 'broadcastStalenessWarning' })`

---

### Task 8: Frontend Freshness Indicators (8 tests)

**File:** `pm-arbitrage-dashboard/src/hooks/useDataFreshness.spec.ts` (NEW, ~80 lines)
**File:** `pm-arbitrage-dashboard/src/components/backtest/DataFreshnessPanel.spec.tsx` (NEW, ~200 lines)

**Hook — 3 tests:**

- [ ] **Test:** [P1] `useDataFreshness` should fetch from `GET /api/backtesting/freshness` with query key `['backtesting', 'freshness']`
  - **Status:** RED — hook does not exist
  - **Verifies:** AC #7 — data fetching convention
  - **Assert:** TanStack Query config uses correct key and endpoint

- [ ] **Test:** [P1] `useDataFreshness` should invalidate cache when WS event `backtesting.incremental.freshness-updated` received
  - **Status:** RED — hook does not exist
  - **Verifies:** AC #7 — real-time WS cache invalidation
  - **Assert:** `queryClient.invalidateQueries({ queryKey: ['backtesting', 'freshness'] })` called on WS message

- [ ] **Test:** [P2] `useDataFreshness` should return `isLoading`, `data`, `error` states
  - **Status:** RED — hook does not exist
  - **Verifies:** AC #7 — standard hook interface

**Component — 5 tests:**

- [ ] **Test:** [P1] `DataFreshnessPanel` renders per-source cards with name, last successful timestamp, records fetched, status badge
  - **Status:** RED — component does not exist
  - **Verifies:** AC #7 — freshness visibility per source
  - **Assert:** renders 6 source cards (KALSHI_API, POLYMARKET_API, GOLDSKY, PMXT_ARCHIVE, ODDSPIPE, PREDEXON)

- [ ] **Test:** [P1] status badge uses server `freshStatus` field: green (fresh), yellow (warning), red (stale), gray (never)
  - **Status:** RED — component does not exist
  - **Verifies:** AC #7 — color coding matches server-computed status
  - **Assert:** badge element has correct CSS class/color per freshStatus value; does NOT recompute staleness

- [ ] **Test:** [P1] timestamps displayed as relative ("2 hours ago") via `formatDistanceToNow()`
  - **Status:** RED — component does not exist
  - **Verifies:** AC #7 — human-readable timestamps

- [ ] **Test:** [P2] panel shows loading skeleton while data fetching
  - **Status:** RED — component does not exist
  - **Verifies:** AC #7 — loading state UX

- [ ] **Test:** [P2] panel shows error state with retry button when fetch fails
  - **Status:** RED — component does not exist
  - **Verifies:** AC #7 — error handling UX

---

## Module Registration (1 test)

**File:** `pm-arbitrage-engine/src/modules/backtesting/ingestion/ingestion.module.ts` — verified transitively

- [ ] **Test:** [P1] IncrementalIngestionService and IncrementalFetchService should be registered in ingestion.module.ts providers
  - **Status:** RED — services not registered
  - **Verifies:** AC #1 — NestJS DI wiring
  - **Assert:** verified transitively — if services instantiate via DI in integration tests, registration is correct

---

## Collection Lifecycle (1 test)

- [ ] **Test:** [P1] IncrementalIngestionService._isRunning flag cleanup: flag resets to false in finally block after runIncrementalRefresh()
  - **Status:** RED — service does not exist
  - **Verifies:** Architecture — collection/flag lifecycle requirement
  - **Assert:** covered by Task 3 concurrency guard tests (flag reset after error)

---

## Summary

| Category | Test Count | P0 | P1 | P2 |
|----------|-----------|----|----|-----|
| Task 1: Prisma Model | 2 | 2 | 0 | 0 |
| Task 2: Config | 7 | 0 | 7 | 0 |
| Task 3: IncrementalIngestionService | 12 | 7 | 5 | 0 |
| Task 4: IncrementalFetchService | 14 | 5 | 5 | 4 |
| Task 5: Match Validation Refresh | 4 | 0 | 2 | 2 |
| Task 6: Events | 5 | 4 | 1 | 0 |
| Task 7: Dashboard Backend | 10 | 3 | 5 | 2 |
| Task 8: Frontend | 8 | 0 | 5 | 3 |
| Module Registration | 1 | 0 | 1 | 0 |
| Collection Lifecycle | 1 | 0 | 1 | 0 |
| **Total** | **64** | **21** | **32** | **11** |

---

## Anti-Pattern Guards

- **DO NOT** duplicate ingestion logic — always delegate to existing services with narrowed date ranges
- **DO NOT** create separate rate limiter — existing services manage their own
- **DO NOT** track per-contract freshness in DataSourceFreshness — it's per-source only (6 rows)
- **DO NOT** use `setInterval` — use NestJS `@Cron` decorator
- **DO NOT** recompute staleness on frontend — trust server `freshStatus` field
- **DO NOT** test dual-partition routing in incremental tests — that's covered by Story 10-9-1a-fix tests
- **DO NOT** use bare `toHaveBeenCalled()` — always verify payloads with `expect.objectContaining()`
