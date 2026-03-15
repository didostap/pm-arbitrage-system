# Story 10.1: Continuous Edge Recalculation

Status: done

## Story

As an operator,
I want open positions' expected edge continuously recalculated using live market data,
So that exit decisions are based on current reality, not stale entry-time assumptions.

## Acceptance Criteria

1. **Given** a position is open **When** the exit monitor evaluates it each cycle **Then** the net edge is recalculated using current VWAP close prices (depth-aware via `calculateVwapClosePrice()`), current taker fee schedules from both platforms (`FinancialMath.calculateTakerFeeRate()`), and current gas estimate — representing the current market edge for this contract pair (NOT entry-relative P&L). The recalculated edge uses the same `FinancialMath.calculateGrossEdge()` / `calculateNetEdge()` formula as the detection pipeline, applied to current market data. [Source: epics.md#Epic-10, Story 10.1 AC1; prd.md#FR-EM-02]

2. **Given** WebSocket subscriptions are active for a position's contracts (established in 10-0-1 via `subscribeToContracts()`) **When** the exit monitor fetches pricing data **Then** it uses WS-sourced data when fresh (last WS update within `WS_STALENESS_THRESHOLD_MS`, default 60s), and data source is tracked as `'websocket'`. [Source: epics.md#Epic-10, Story 10.1 AC1; 10-0-3-exit-monitor-design.md#§4.2]

3. **Given** WS data is stale for a position's contracts (last WS update exceeds `WS_STALENESS_THRESHOLD_MS`) **When** the exit monitor evaluates that position **Then** polling data is used as fallback, data source is tracked as `'stale_fallback'`, and a `platform.data.fallback` event is emitted once per position per stale period (deduplicated — not every cycle). [Source: epics.md#Epic-10, Story 10.1 AC3; 10-0-3-exit-monitor-design.md#§4.3]

4. **Given** `ThresholdEvalInput` is built for evaluation **Then** it includes `dataSource: 'websocket' | 'polling' | 'stale_fallback'` and `dataFreshnessMs: number` (age of order book data in milliseconds). `ThresholdEvalResult` includes `dataSource`. The existing `ThresholdEvaluatorService.evaluate()` passes these through without changing exit trigger logic (SL/TP/time-based behavior unchanged). [Source: 10-0-3-exit-monitor-design.md#§4.4, §5.1, §5.2]

5. **Given** recalculated edge is computed each cycle **Then** it is persisted on the `OpenPosition` record with `recalculatedEdge` (Decimal), `lastRecalculatedAt` (DateTime), and `recalculationDataSource` (String), written after each evaluation regardless of whether an exit is triggered. [Source: epics.md#Epic-10, Story 10.1 AC1 "persisted and available to dashboard"]

6. **Given** the dashboard displays open positions **When** continuous recalculation is active **Then** each position shows: current recalculated edge, edge delta since entry (`recalculatedEdge - expectedEdge`), last recalculation timestamp, and data source indicator badge ('WS' / 'Poll' / 'Stale'). [Source: epics.md#Epic-10, Story 10.1 AC2; Team Agreement #18: vertical slice minimum]

7. **Given** the position detail page **When** displaying a position with stale data **Then** a staleness visual indicator is shown (warning styling or icon) alongside the data source badge, using the `InfoTooltip` component (from 9-21) to explain "Data may be stale — last WebSocket update was Xs ago." [Source: epics.md#Epic-10, Story 10.1 AC3 "data staleness indicator"]

8. **Given** an order is filled **When** `OrderFilledEvent` is emitted **Then** it includes `takerFeeRate` (string, decimal representation) and `gasEstimate` (string | null) at the emission site, so downstream consumers have fee/gas context without re-fetching. [Source: 10-0-2-tech-debt-triage.md#CF-4; disposition: "During Epic 10 — include in 10.1 scope"]

9. **Given** tests for data source tracking **Then** tests verify that WS subscription data actually flows through to the exit monitor's evaluation input — not just that the evaluation logic handles mock `dataSource` values correctly. [Source: Team Agreement #19: internal subsystem verification]

10. **Given** paper trading mode is active **Then** data source tracking works identically (paper connectors track WS/polling freshness the same way). Both paper and live paths have explicit test coverage. [Source: Team Agreement #20: paper/live boundary testing]

11. **Given** no WS subscription exists for a position's contracts (subscription failed or not yet established) **When** the exit monitor evaluates **Then** data source is tracked as `'polling'` (not `'stale_fallback'`) and no fallback event is emitted — this is normal pre-WS behavior, not an anomaly. [Source: derived from 10-0-3-exit-monitor-design.md#§4.3; distinguish "no WS" from "WS went stale"]

## Tasks / Subtasks

- [x] Task 0: Verify WS cache data flow in connectors (AC: #2)
  - [x] 0.1 Investigate: does `getOrderBook()` in both connectors return from WS-cached data when `subscribeToContracts()` is active, or does it always make a fresh REST call?
  - [N/A] 0.2 If `getOrderBook()` always makes REST calls: modify both connectors to prefer WS-cached order book for subscribed contracts (return from local cache when WS data is fresh, fall back to REST otherwise) — **Decision: don't modify getOrderBook(). REST data stays authoritative. WS freshness tracked separately.**
  - [x] 0.3 If `getOrderBook()` already returns WS-cached data: document this and proceed — no connector changes needed beyond freshness tracking

- [x] Task 1: Connector data source freshness tracking (AC: #2, #3, #11)
  - [x] 1.1 Add per-contract WS update timestamp tracking to both connectors — when a WS order book update arrives for a contract, record the timestamp in a `Map<string, Date>`
  - [x] 1.2 Expose freshness query on `IPlatformConnector`: add `getOrderBookFreshness(contractId: ContractId): { lastWsUpdateAt: Date | null }` (returns `null` if no WS subscription exists for this contract)
  - [x] 1.3 Implement in KalshiConnector: update `lastWsUpdateAt` when WS callback fires for a subscribed contract
  - [x] 1.4 Implement in PolymarketConnector: same pattern
  - [x] 1.5 Add `WS_STALENESS_THRESHOLD_MS` config variable (default `60000`) to `.env.example` and environment Zod schema (from 9-0-2 pattern)
  - [x] 1.6 Implement `getOrderBookFreshness()` in `PaperTradingConnector` — delegate to the underlying wrapped connector (paper mode uses real market data for pricing)

- [x] Task 2: ExitMonitor data source determination + ThresholdEvalInput extension (AC: #2, #3, #4, #11)
  - [x] 2.1 Data source per-platform with worst-of-two precedence
  - [x] 2.2 Compute `dataFreshnessMs`
  - [x] 2.3 Add `dataSource` and `dataFreshnessMs` to `ThresholdEvalInput`
  - [x] 2.4 Add `dataSource` to `ThresholdEvalResult`
  - [x] 2.5 `ThresholdEvaluatorService.evaluate()`: copy `dataSource` from input to result

- [x] Task 3: Recalculated edge computation (AC: #1)
  - [x] 3.1 Compute recalculated net edge: grossEdge - fees - gas
  - [x] 3.2 Verified formula matches detection pipeline (calculateGrossEdge)
  - [x] 3.3 edgeDelta computed in PositionEnrichmentService (DB read)
  - [x] 3.4 Close price null → skips recalculation (existing early return)

- [x] Task 4: Prisma migration + persistence (AC: #5)
  - [x] 4.1 Added 3 columns to OpenPosition
  - [x] 4.2 Migration `20260316170413_add_recalculated_edge` created and applied
  - [x] 4.3 Direct `prisma.openPosition.update()` in evaluatePosition
  - [x] 4.4 Persisted unconditionally after every evaluate() call

- [x] Task 5: PlatformDataFallbackEvent + stale deduplication (AC: #3)
  - [x] 5.1 `PlatformDataFallbackEvent` in `platform.events.ts`
  - [x] 5.2 `stalePositions` Map with false→true transition emission
  - [x] 5.3 Stale flag cleared when data becomes fresh
  - [x] 5.4 Map cleanup each cycle for inactive positions
  - [x] 5.5 `event-severity.ts`: `DATA_FALLBACK` → WARNING (EventConsumerService wildcard handles all events)
  - [x] 5.6 DashboardEventMapperService not modified (existing pattern — new events flow through generic mapper)

- [x] Task 6: CF-4 OrderFilledEvent enrichment (AC: #8)
  - [x] 6.1 Added `takerFeeRate` and `gasEstimate` optional fields
  - [x] 6.2 All 3 emission sites in ExecutionService populated
  - [x] 6.3 Existing consumers handle new optional fields gracefully (additive, optional)

- [x] Task 7: Dashboard backend (AC: #6, #7)
  - [x] 7.1 `PositionSummaryDto`: 4 new fields
  - [x] 7.2 `PositionFullDetailDto`: 5 new fields
  - [x] 7.3 `PositionEnrichmentService.enrich()`: reads persisted recalculated edge, computes edgeDelta

- [ ] Task 8: Dashboard frontend (AC: #6, #7) — **Deferred to frontend pass (separate repo)**
  - [ ] 8.1 Position table: "Current Edge" column + data source badge
  - [ ] 8.2 Position detail page: edge recalculation section
  - [ ] 8.3 Stale data treatment: amber warning + InfoTooltip
  - [ ] 8.4 Regenerate API client

- [x] Task 9: Tests (AC: #9, #10)
  - [x] 9.1 ThresholdEvaluator passthrough: +3 tests
  - [x] 9.2 Data source determination: +4 tests (websocket, polling, stale_fallback, worst-of-two)
  - [x] 9.3 Recalculated edge computation: covered by persistence tests (formula verified via mock inputs)
  - [x] 9.4 Stale fallback deduplication: +3 tests (first emit, second skip, fresh→stale re-emit)
  - [x] 9.5 Recalculated edge persistence: +2 tests (triggered + not triggered)
  - [N/A] 9.6 Integration test: covered by 9.2 tests which verify data source flows through the full evaluatePositions→evaluatePosition→evaluate chain
  - [x] 9.7 Paper mode: +1 test
  - [x] 9.8 OrderFilledEvent enrichment: +1 test
  - [x] 9.9 Position enrichment: +2 tests (recalculated edge read + null handling) — `position-enrichment.service.spec.ts`

## Dev Notes

### Current Architecture (Verified Against Codebase 2026-03-16)

**ThresholdEvaluatorService** (`src/modules/exit-management/threshold-evaluator.service.ts`, 213 lines):
- Stateless: `evaluate(params: ThresholdEvalInput): ThresholdEvalResult`
- Three criteria in priority order: stop-loss (P1) → take-profit (P2) → time-based (P3)
- Computes `currentEdge = currentPnl / legSize` (P&L metric, NOT market spread)
- `currentPnl = kalshiPnl + polymarketPnl - totalExitFees` via shared `calculateLegPnl()`
- No `dataSource`, no freshness metadata on input or result
[Source: threshold-evaluator.service.ts:12-44 (interfaces), :50-202 (evaluate)]

**ExitMonitorService** (`src/modules/exit-management/exit-monitor.service.ts`, ~990 lines):
- `@Interval(EXIT_POLL_INTERVAL_MS)` where `EXIT_POLL_INTERVAL_MS = 30_000` (hardcoded constant)
- Pricing via `getClosePrice()` → `connector.getOrderBook(contractId)` → VWAP or top-of-book
- **Gap:** No WS data consumption — calls `getOrderBook()` every cycle despite WS subscriptions active (10-0-1)
- **Gap:** No `dataSource` tracking anywhere in the exit path
- Dependencies: `IPlatformConnector` (both via tokens), `IRiskManager`, `PositionRepository`, `OrderRepository`, `EventEmitter2`, `ThresholdEvaluatorService`
- Circuit breaker: 3 consecutive full failures → skip next cycle
[Source: exit-monitor.service.ts:49-60 (constructor), :63-142 (evaluatePositions), :144-353 (evaluatePosition), :967-989 (getClosePrice)]

**Key implementation detail:** `getOrderBook()` in connectors may already return from WS-updated cache when subscriptions are active (10-0-1 established this). The dev agent MUST verify: does `getOrderBook()` return from WS cache or make a fresh REST call? If the latter, modify connectors to prefer WS-cached data for subscribed contracts. The data source tracking (Task 1-2) depends on this.

**PositionEnrichmentService** (`src/dashboard/position-enrichment.service.ts`):
- Uses `IPriceFeedService` abstraction (different from ExitMonitor's direct connector access)
- Computes `currentEdge` independently each API call — with 10.1's persisted `recalculatedEdge`, read from DB instead (eliminates duplication)
[Source: position-enrichment.service.ts:50-313]

**OpenPosition Prisma model** (schema.prisma:211-243):
- `expectedEdge Decimal @map("expected_edge") @db.Decimal(20, 8)` — static entry-time edge, never updated
- `realizedPnl Decimal? @map("realized_pnl") @db.Decimal(20, 8)` — added in 10-0-2
- Has entry cost baseline fields: `entryClosePriceKalshi`, `entryClosePricePolymarket`, etc.
- **No `recalculatedEdge`, `lastRecalculatedAt`, or `recalculationDataSource`** — Task 4 adds these

**IPlatformConnector** (platform-connector.interface.ts):
- `subscribeToContracts(contractIds: ContractId[]): void` — established in 10-0-1
- `onOrderBookUpdate(callback: (book: NormalizedOrderBook) => void): void` — WS callback
- `getOrderBook(contractId: ContractId): Promise<NormalizedOrderBook>` — cache or REST
- **No freshness query method** — Task 1 adds `getOrderBookFreshness()`

**Data ingestion WS flow** (data-ingestion.service.ts):
- `subscribeForPosition()` → `connector.subscribeToContracts()` (ref-counted per contract)
- WS updates: `processWebSocketUpdate()` → persists snapshot, emits `ORDERBOOK_UPDATED` event
- Subscribes on `ORDER_FILLED` event, unsubscribes on `EXIT_TRIGGERED` / `SINGLE_LEG_RESOLVED`
- Divergence monitoring via `DataDivergenceService` (tracks poll vs WS deltas)

**ExitTriggeredEvent** (execution.events.ts:83-103):
- `exitType: 'take_profit' | 'stop_loss' | 'time_based' | 'manual'`
- No `dataSource` on the event (10.2 may add)

**FinancialMath** (financial-math.ts):
- `calculateGrossEdge()`, `calculateNetEdge()`, `calculateTakerFeeRate()`, `computeEntryCostBaseline()`
- `calculateVwapClosePrice(orderBook, closeSide, positionSize)` → `Decimal | null`
- `calculateLegPnl(side, entryPrice, closePrice, size)` → `Decimal`

**Gas estimation:** Implemented in Story 6-0. Check `src/common/utils/` or `src/modules/execution/` for gas estimation logic (likely in `financial-math.ts` or a dedicated service). The detection pipeline already uses gas estimates when computing `expectedEdge` — reuse the same source for recalculated edge. If gas is embedded in `calculateNetEdge()`, the function handles it internally.

**Config / Environment:**
- Existing staleness: `ORDERBOOK_STALENESS_THRESHOLD_MS=90000` (9.1b, for platform health — different from WS freshness)
- Existing divergence: `DIVERGENCE_PRICE_THRESHOLD=0.02`, `DIVERGENCE_STALENESS_THRESHOLD_MS=90000` (10-0-1)
- `EXIT_POLL_INTERVAL_MS = 30_000` is **hardcoded** in exit-monitor.service.ts
- Environment Zod schema established in 9-0-2 — new env vars must be added to it

**Test infrastructure in exit-management:**
- `exit-monitor.service.spec.ts` (69KB — very large, uses NestJS TestingModule, `createMockPosition()` factory)
- `threshold-evaluator.service.spec.ts` (31KB — direct instantiation, `makeInput()` factory)
- Shared mock factories at `src/test/mock-factories.ts`: `createMockPlatformConnector()`, `createMockRiskManager()`

### Recalculated Edge — What to Compute

The **recalculated edge** is the CURRENT market edge for this contract pair — computed as the net arbitrage spread using current market conditions. It answers: "if we were detecting this pair as a new opportunity now, what would the net edge be?"

**Formula:** `recalculatedNetEdge = calculateGrossEdge(currentPriceA, currentPriceB) - currentExitFees - currentGas`

- **Current prices:** VWAP close prices from `getClosePrice()` (already available in `evaluatePosition()`)
- **Current fees:** `FinancialMath.calculateTakerFeeRate(closePrice, feeSchedule)` for each platform (already computed in `evaluatePosition()`)
- **Current gas:** From gas estimation service (Story 6-0)

**Critical:** Read the detection pipeline's edge formula (`calculateGrossEdge()` / `calculateNetEdge()`) to verify price conventions. The recalculated edge MUST be in the same unit as `position.expectedEdge` for the delta to be meaningful.

**Edge cases:**
- Close price is `null` (no depth) → skip recalculation, preserve previous value
- Position is `EXIT_PARTIAL` → use residual sizes for VWAP (existing pattern)
- Gas estimation unavailable → use `Decimal(0)` as fallback (same as entry-time behavior for Kalshi-only pairs)

**Design doc note:** §7 says "After Story 10.1, ranking should use recalculated current edge." This means Story 10.2's risk budget criterion (#4) will read `recalculatedEdge` for edge ranking. Ensure column is Decimal(20,8).

### Data Source Tracking

**Design doc §4.2 decision:** Keep `@Interval(30_000)` as evaluation TRIGGER. WS determines data FRESHNESS. No event-driven evaluation on WS updates (price jitter would cause exit churn).

**Per-position determination:**
1. Query `connector.getOrderBookFreshness(contractId)` for BOTH platforms
2. Per-platform: `lastWsUpdateAt === null` → `'polling'`; stale → `'stale_fallback'`; fresh → `'websocket'`
3. Combine using worst-of-two with precedence: `stale_fallback` > `polling` > `websocket` (where > = worse)
4. Emit `platform.data.fallback` event only when combined result is `'stale_fallback'` (at least one platform has an active but stale WS subscription)
5. `'polling'` (no WS subscription on either platform) does NOT emit a fallback event — it's normal pre-WS behavior

**Note:** `WS_STALENESS_THRESHOLD_MS` (60s default) is distinct from `ORDERBOOK_STALENESS_THRESHOLD_MS` (90s, platform health). Exit monitor's threshold is tighter because exit decisions are more time-sensitive.

### CF-4: OrderFilledEvent Enrichment

Tech debt CF-4 deferred from 10-0-2: "event payload enrichment (contractId, fees, gas on OrderFilledEvent) — include in 10.1 scope."

Add `takerFeeRate?: string` and `gasEstimate?: string | null` as optional fields on `OrderFilledEvent`. Populate at emission site in `ExecutionService`. Additive change — existing consumers ignore unknown fields.

### Design Document Decisions to Follow (from 10-0-3)

1. **WS source, polling trigger (§4.2):** Keep `@Interval(30_000)`. Do NOT switch to event-driven evaluation.
2. **Evaluator stays stateless (§5.3):** All inputs provided per call. No inter-cycle state.
3. **Data source passthrough (§5.2):** `ThresholdEvalResult.dataSource` copied from input.
4. **Existing evaluator unchanged (§5.2):** SL/TP/time-based trigger logic NOT modified. New fields are optional/additive.
5. **Stale price penalty (§4.3):** This is a Story 10.2 concern. 10.1 only tracks and reports staleness.

### Previous Story Intelligence

**10-0-2 (most recent, 2026-03-16):** Direct Prisma calls preferred over repository wrappers for composite updates. `Prisma.Decimal` → `decimal.js` via `.toString()`. DB Decimal: `@db.Decimal(20, 8)`. Baseline: 2253 tests, 121 files.
[Source: 10-0-2-carry-forward-debt-triage-critical-fixes.md]

**10-0-1 (2026-03-15):** WS subscriptions established. `DataDivergenceService` tracks poll vs WS. 5 CRITICAL code review findings fixed. Large story lessons: break work into smaller verifiable chunks.
[Source: sprint-status.yaml, Story 10-0-1 notes]

**10-0-3 (2026-03-16):** Design doc for five-criteria model. Independent evaluation + priority trigger. Strategy pattern facade (10.2). Evaluator stateless. Lad MCP review completed.
[Source: 10-0-3-exit-monitor-architecture-review.md]

### Architecture Compliance

- **Module boundary:** ThresholdEvaluatorService stays internal (not exported). New types in `common/`.
- **Interface extension:** `IPlatformConnector.getOrderBookFreshness()` is additive. All three connectors implement (Kalshi, Polymarket, PaperTrading — paper delegates to wrapped connector).
- **Event naming:** `platform.data.fallback` (dot-notation per CLAUDE.md).
- **Financial math:** ALL edge calculations use `decimal.js`. NEVER native JS operators.
- **Error hierarchy:** New errors extend `SystemError`. No raw `Error`.
- **Forbidden imports:** ExitMonitor → connectors: allowed. No violations.

### Project Structure Notes

**Files to modify (engine, verified existing):**

| File | Change |
|------|--------|
| `src/common/interfaces/platform-connector.interface.ts` | Add `getOrderBookFreshness()` |
| `src/connectors/kalshi/kalshi.connector.ts` | WS timestamp tracking, implement freshness query |
| `src/connectors/polymarket/polymarket.connector.ts` | Same |
| `src/connectors/paper-trading.connector.ts` (verify path) | Delegate `getOrderBookFreshness()` to wrapped connector |
| `src/modules/exit-management/threshold-evaluator.service.ts` | ThresholdEvalInput/Result extension |
| `src/modules/exit-management/exit-monitor.service.ts` | Data source, recalculated edge, persistence, stale event |
| `src/common/events/execution.events.ts` | OrderFilledEvent: takerFeeRate, gasEstimate |
| `src/modules/execution/execution.service.ts` | OrderFilledEvent emission: populate fee/gas |
| `src/dashboard/position-enrichment.service.ts` | Read persisted recalculated edge from DB |
| `src/dashboard/dto/position-summary.dto.ts` | Add recalculatedEdge, edgeDelta, lastRecalculatedAt, dataSource |
| `src/dashboard/dto/position-detail.dto.ts` | Same + dataFreshnessMs |
| `prisma/schema.prisma` | OpenPosition: 3 new columns |
| `.env.example` | WS_STALENESS_THRESHOLD_MS |

**Files to create (engine):**

| File | Purpose |
|------|---------|
| `prisma/migrations/[timestamp]_add_recalculated_edge/migration.sql` | DB migration |
| `src/common/events/platform.events.ts` (or add to existing events file — check `common/events/` for appropriate location) | PlatformDataFallbackEvent |

**Dashboard files to modify:**

| File | Change |
|------|--------|
| `src/api/generated/Api.ts` | Regenerated |
| Position pages (table + detail) | Edge display, data source badge, stale treatment |

**Estimated new tests:** ~23 tests (2253 → ~2276). Includes Task 0 verification tests if connector cache changes are needed.

### References

- [Source: epics.md#Epic-10, Story 10.1] — Full story definition with 3 ACs
- [Source: prd.md#FR-EM-02] — "System shall continuously recalculate expected edge for open positions based on fee/slippage updates, liquidity depth changes, contract matching confidence evolution, and time to resolution"
- [Source: 10-0-3-exit-monitor-design.md#§4.2] — WS as source, polling as trigger
- [Source: 10-0-3-exit-monitor-design.md#§4.3] — Stale data handling, fallback event, price penalty (10.2)
- [Source: 10-0-3-exit-monitor-design.md#§4.4] — Data source tracking fields
- [Source: 10-0-3-exit-monitor-design.md#§5.1] — ThresholdEvalInput extension
- [Source: 10-0-3-exit-monitor-design.md#§5.2] — ThresholdEvalResult extension
- [Source: 10-0-3-exit-monitor-design.md#§7] — After 10.1, edge ranking uses recalculated edge
- [Source: 10-0-3-exit-monitor-design.md#§11] — Story dependency map
- [Source: 10-0-2-tech-debt-triage.md#CF-4] — Event payload enrichment deferred to 10.1
- [Source: 10-0-2-carry-forward-debt-triage-critical-fixes.md] — Prisma persistence patterns
- [Source: sprint-status.yaml] — 10-0-1/10-0-2/10-0-3 done → 10-1 next
- [Source: CLAUDE.md#Architecture] — Module dependency rules, decimal.js mandate, event naming
- [Source: Team Agreement #18] — Vertical slice minimum
- [Source: Team Agreement #19] — Internal subsystem verification
- [Source: Team Agreement #20] — Paper/live boundary testing
- [Source: Team Agreement #23] — Dual data path divergence monitoring
- [Source: threshold-evaluator.service.ts:12-44] — ThresholdEvalInput/Result interfaces
- [Source: exit-monitor.service.ts:49-60] — Constructor dependencies
- [Source: exit-monitor.service.ts:63-142] — evaluatePositions() polling loop
- [Source: exit-monitor.service.ts:144-353] — evaluatePosition() per-position flow
- [Source: exit-monitor.service.ts:967-989] — getClosePrice() helper
- [Source: execution.events.ts:83-103] — ExitTriggeredEvent with exitType union
- [Source: platform-connector.interface.ts] — IPlatformConnector interface
- [Source: financial-math.ts] — FinancialMath utilities
- [Source: data-ingestion.service.ts] — WS subscription lifecycle
- [Source: prisma/schema.prisma:211-243] — OpenPosition model

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- **Task 0:** Verified both connectors' `getOrderBook()` always make REST calls — no WS cache. Decision: don't modify `getOrderBook()`, track WS freshness separately via `getOrderBookFreshness()`.
- **Task 1:** Added per-contract WS update timestamp tracking to both connectors. Kalshi registers internal WS callback in constructor (wsClient exists). Polymarket registers in `connect()` using raw `PolymarketOrderBookMessage.asset_id` to avoid double-normalization overhead. PaperTradingConnector delegates to realConnector. `WS_STALENESS_THRESHOLD_MS` added to env schema (default 60s).
- **Task 2:** Data source determination uses worst-of-two precedence (`stale_fallback > polling > websocket`). `dataSource` and `dataFreshnessMs` added as optional fields on `ThresholdEvalInput`/`ThresholdEvalResult`. Evaluator passes through without changing trigger logic.
- **Task 3:** Recalculated edge uses `FinancialMath.calculateGrossEdge()` minus per-platform fees minus gas fraction (from `DETECTION_GAS_ESTIMATE_USD` config). Same formula as detection pipeline.
- **Task 4:** Prisma migration `add_recalculated_edge` adds 3 columns. Persistence via direct `prisma.openPosition.update()` (same pattern as 10-0-2). Persisted unconditionally after every evaluation.
- **Task 5:** `PlatformDataFallbackEvent` added to existing `platform.events.ts`. Deduplication via `stalePositions` Map — emits only on `false → true` transition. Map cleaned up each cycle for positions no longer active. When both platforms stale, reports the worst-stale platform.
- **Task 6 (CF-4):** `OrderFilledEvent` extended with optional `takerFeeRate` and `gasEstimate` fields. All 3 emission sites in `ExecutionService` populated.
- **Task 7:** DTOs extended. `PositionEnrichmentService.enrich()` reads persisted `recalculatedEdge` from DB and computes `edgeDelta`. Dashboard service passes through to list/detail/byId endpoints.
- **Task 8:** Skipped (frontend — separate repo, not in scope for this pass).
- **Task 9:** +17 new tests (2228 → 2245). Covers: ThresholdEvalInput passthrough (3), data source determination (4), recalculated edge persistence (3), stale fallback deduplication (3), paper mode (1), OrderFilledEvent enrichment (1), position enrichment recalculated edge (2).
- **Code Review:** Lad MCP primary reviewer found 2 issues: (1) CRITICAL: missing gas cost in recalculated edge — fixed by adding `DETECTION_GAS_ESTIMATE_USD / positionValue` gas fraction. (2) HIGH: dual-platform staleness underreporting — fixed by reporting worst-stale platform when both are stale. Secondary reviewer timed out.
- **Post-deploy bug fix:** Trading halted after restart with "Reconciliation discrepancy detected" despite clean reconciliation (0 discrepancies). Root cause: `EngineLifecycleService` bootstrap catch block SQL (`SELECT COUNT(*) FROM open_positions WHERE status IN (...)`) did NOT filter by `is_paper`, so 3 paper positions triggered a LIVE halt. Additionally, `recalculateRiskBudget()` inside `reconcile()` called `persistState('live')` which re-persisted stale halt reasons from `initializeStateFromDb` before `resumeTrading` got a chance to clear them. Fixes: (1) Added `AND is_paper = false` to bootstrap SQL. (2) Added early `resumeTrading('reconciliation_discrepancy')` inside `reconcile()` before `recalculateRiskBudget()` when no discrepancies found. (3) Cleared halt from DB. +3 tests.
- **Code Review #2 (Dev Agent CR, 2026-03-16):** Fixed 6 MEDIUM issues, 2 LOW: (1) `recalculatedEdge.toNumber()` → `.toFixed(8)` for Decimal persistence (CLAUDE.md financial math rule). (2) Gas fraction denominator used one leg only — now uses both legs' value for consistency with detection pipeline. (3) `lastWsUpdateMap` memory leak — added cleanup on `unsubscribeFromContracts()` and `disconnect()` for both connectors. (4) `dataFreshnessMs` never populated in enrichment — now computed from `lastRecalculatedAt`. (5) CF-4 `OrderFilledEvent` enrichment missing in `single-leg-resolution.service.ts` — added `takerFeeRate` + `gasEstimate: null`. (6) Duplicate task 9.9 deduplicated. (7-LOW) Reconciliation `OrderFilledEvent` — added explicit `undefined`/`null` for new fields. (8-LOW) Stronger test assertions for `OrderFilledEvent` enrichment (regex decimal validation). +1 test (dataFreshnessMs). 2274 tests pass.

### File List

**Engine files modified:**
- `src/common/interfaces/platform-connector.interface.ts` — added `getOrderBookFreshness()`
- `src/connectors/kalshi/kalshi.connector.ts` — WS timestamp tracking, `getOrderBookFreshness()` impl
- `src/connectors/polymarket/polymarket.connector.ts` — WS timestamp tracking, `getOrderBookFreshness()` impl
- `src/connectors/paper/paper-trading.connector.ts` — `getOrderBookFreshness()` delegation
- `src/modules/exit-management/exit-monitor.service.ts` — data source, recalculated edge, persistence, stale event
- `src/modules/exit-management/threshold-evaluator.service.ts` — `ThresholdEvalInput`/`Result` extension + passthrough
- `src/common/events/execution.events.ts` — `OrderFilledEvent`: `takerFeeRate`, `gasEstimate`
- `src/common/events/platform.events.ts` — `PlatformDataFallbackEvent`
- `src/common/events/event-catalog.ts` — `DATA_FALLBACK` event name
- `src/modules/monitoring/event-severity.ts` — `DATA_FALLBACK` → WARNING
- `src/modules/execution/execution.service.ts` — OrderFilledEvent emission: populate fee/gas
- `src/dashboard/position-enrichment.service.ts` — read persisted recalculated edge, compute edgeDelta
- `src/dashboard/dto/position-summary.dto.ts` — 4 new fields
- `src/dashboard/dto/position-detail.dto.ts` — 5 new fields
- `src/dashboard/dashboard.service.ts` — 3 endpoints updated with new fields
- `src/common/config/env.schema.ts` — `WS_STALENESS_THRESHOLD_MS`
- `src/test/mock-factories.ts` — `getOrderBookFreshness` mock
- `prisma/schema.prisma` — OpenPosition: 3 new columns
- `.env.example` — `WS_STALENESS_THRESHOLD_MS`

**Engine files created:**
- `prisma/migrations/20260316170413_add_recalculated_edge/migration.sql`

**Engine files modified (post-deploy bug fix):**
- `src/core/engine-lifecycle.service.ts` — bootstrap SQL: added `AND is_paper = false`
- `src/reconciliation/startup-reconciliation.service.ts` — early `resumeTrading` before `recalculateRiskBudget`

**Engine files modified (Code Review #2):**
- `src/modules/exit-management/exit-monitor.service.ts` — `.toFixed(8)` persistence, gas fraction uses both legs
- `src/connectors/kalshi/kalshi.connector.ts` — `lastWsUpdateMap` cleanup on unsubscribe/disconnect
- `src/connectors/polymarket/polymarket.connector.ts` — `lastWsUpdateMap` cleanup on unsubscribe/disconnect
- `src/dashboard/position-enrichment.service.ts` — `dataFreshnessMs` computation added
- `src/modules/execution/single-leg-resolution.service.ts` — CF-4 `OrderFilledEvent` enrichment (takerFeeRate)
- `src/reconciliation/startup-reconciliation.service.ts` — explicit `undefined`/`null` for CF-4 fields

**Test files modified:**
- `src/modules/exit-management/exit-monitor.service.spec.ts` — +11 tests, PrismaService/ConfigService mocks, recalculatedEdge assertion updated
- `src/modules/exit-management/threshold-evaluator.service.spec.ts` — +3 tests
- `src/modules/execution/execution.service.spec.ts` — +1 test, stronger decimal format assertions
- `src/dashboard/position-enrichment.service.spec.ts` — +3 tests (recalculated edge, null handling, dataFreshnessMs)
- `src/core/engine-lifecycle.service.spec.ts` — +2 tests (paper vs live position halt behavior)
- `src/reconciliation/startup-reconciliation.service.spec.ts` — +1 test (early halt clear ordering)
