# Story 10.4: Adaptive Leg Sequencing & Matched-Count Execution

Status: done

## Story

As an operator,
I want the system to dynamically choose which platform's leg to execute first based on real-time latency and to execute matched contract counts on both legs,
so that leg risk is minimized and positions are truly hedged (equal contract counts on both sides of the arbitrage).

## Acceptance Criteria

1. **Given** both platforms have P95 latency data available (via `PlatformHealthService.calculateP95Latency()`), **when** the latency difference exceeds 200ms (`ADAPTIVE_SEQUENCING_LATENCY_THRESHOLD_MS`), **then** the lower-latency platform's leg is executed first, overriding the static `primaryLeg` config. **And** the sequencing decision is logged with both latency measurements and the override reason. [Source: epics.md#Story-10.4-AC1, FR-EX-08]

2. **Given** P95 latency profiles are stable (difference ≤ 200ms) or one/both platforms report null latency, **when** sequencing is determined, **then** the static `primaryLeg` config is used (preserving current behavior). [Source: epics.md#Story-10.4-AC2]

3. **Given** an arbitrage opportunity is ready for execution, **when** position sizing is calculated, **then** the system uses the unified collateral-aware formula: `idealCount = floor(reservedCapitalUsd / (primaryDivisor + secondaryDivisor))` where `primaryDivisor = price` for buy and `(1 - price)` for sell. **And** this single `idealCount` replaces the two independent per-leg ideal sizes. **And** each leg is depth-capped independently: `cappedCount = min(idealCount, availableDepth)`. **And** `matchedCount = min(primaryCapped, secondaryCapped)` is used for BOTH legs. **And** edge re-validation (FR-EX-03a) runs with `matchedCount` before any order is submitted. [Source: epics.md#Story-10.4-AC3, architecture.md#Execution-Position-Sizing-Model]

4. **Given** pre-flight depth check rejects one or both legs, **when** neither order has been submitted yet, **then** the full reservation is released cleanly (no single-leg exposure possible). (Already implemented by Story 6.5.5h — this AC validates continued correctness after the sizing formula change.) [Source: epics.md#Story-10.4-AC4]

5. **Given** adaptive sequencing makes a decision, **when** the dashboard displays recent executions or position details, **then** each execution shows: which platform went first, latency measurements for both platforms, sequencing reason (latency override / static config), matched contract count vs ideal count, and data source per leg (websocket/polling/stale_fallback). [Source: epics.md#Story-10.4-AC5, Team Agreement #18]

6. **Given** both poll and WebSocket data paths may be active for a contract, **when** execution uses depth data for pre-flight verification, **then** depth data source is classified per leg (websocket/polling/stale_fallback) using `getOrderBookFreshness()`. **And** the data source classification is persisted with the execution metadata. **And** if `DataDivergenceService.getDivergenceStatus()` reports divergence for a contract, a warning is logged and the `platform.data.divergence` event is checked (no additional REST fetch — the REST-based `getOrderBook()` is already the authoritative conservative source). [Source: epics.md#Story-10.4-AC6, Team Agreement #23]

7. **Given** tests validate execution flow, **when** depth verification and order submission are tested, **then** tests verify orders actually reach the connector (not just that sizing logic produces correct values). [Source: epics.md#Story-10.4-AC7, Team Agreement #19]

## Tasks / Subtasks

### Task 0: Configuration & Environment Setup (AC: #1, #2)

- [x] Add config keys to `common/config/env.schema.ts`:
  - `ADAPTIVE_SEQUENCING_ENABLED` (`z.boolean().default(true)`) — enabled by default (safe: falls back to static if latency unavailable)
  - `ADAPTIVE_SEQUENCING_LATENCY_THRESHOLD_MS` (`z.number().int().min(0).default(200)`) — minimum latency difference to trigger override
  - `POLYMARKET_ORDER_POLL_TIMEOUT_MS` (`z.number().int().min(1000).max(30000).default(5000)`) — configurable order fill poll timeout
  - `POLYMARKET_ORDER_POLL_INTERVAL_MS` (`z.number().int().min(100).max(5000).default(500)`) — configurable poll interval
- [x] Add all keys to `.env.example` and `.env.development` with descriptive comments
- [x] Verify: when `ADAPTIVE_SEQUENCING_ENABLED=false`, sequencing logic is identical to pre-story behavior

### Task 1: Unified Sizing Formula (AC: #3, #4)

- [x] **Keep the existing `primaryDivisor` and `secondaryDivisor` computations** — they are already collateral-aware (buy → `price`, sell → `new Decimal(1).minus(price)`). These DO NOT change. Only what happens AFTER them changes.
- [x] Replace the two independent ideal-size computations with the unified collateral-aware formula:

  ```typescript
  // BEFORE (current — over-deploys capital):
  // const idealSize = new Decimal(reservation.reservedCapitalUsd).div(primaryDivisor).floor().toNumber();
  // const secondaryIdealSize = new Decimal(reservation.reservedCapitalUsd).div(secondaryDivisor).floor().toNumber();

  // AFTER (unified — guarantees both legs fit within budget):
  const combinedDivisor = primaryDivisor.plus(secondaryDivisor);
  const idealCount = new Decimal(reservation.reservedCapitalUsd).div(combinedDivisor).floor().toNumber();
  ```

- [x] Use `idealCount` for BOTH legs' depth capping: `primaryCapped = min(idealCount, primaryAvailableDepth)`, `secondaryCapped = min(idealCount, secondaryAvailableDepth)`
- [x] Keep the existing `equalizedSize = min(primaryCapped, secondaryCapped)` and edge re-validation logic — they now operate on properly-sized counts
- [x] Remove the separate `secondaryIdealSize` variable and its guard (the combined divisor guard replaces both individual guards)
- [x] Add guard for `combinedDivisor.lte(0)` — return `ExecutionError(EXECUTION_ERROR_CODES.GENERIC_EXECUTION_FAILURE, 'Non-positive combined collateral divisor', 'warning')` and emit `ExecutionFailedEvent`. Release reservation via normal error return path (caller handles).
- [x] Update the `sizeWasReduced` check: compare `equalizedSize < idealCount` (single ideal, not two)
- [x] In edge re-validation: `conservativePositionSizeUsd = new Decimal(equalizedSize).mul(combinedDivisor)` — simpler than before
- [x] Preserve the runtime invariant check (`targetSize !== secondarySize`) — still correct
- [x] Log both `idealCount` and `equalizedSize` for observability

### Task 2: Adaptive Leg Sequencing (AC: #1, #2)

- [x] Add `DataIngestionModule` to `ExecutionModule.imports` to access `PlatformHealthService`
- [x] Inject `PlatformHealthService` into `ExecutionService`
- [x] Create private method `determineSequencing(staticPrimaryLeg: string): SequencingDecision`:
  ```typescript
  interface SequencingDecision {
    primaryLeg: string; // 'kalshi' | 'polymarket'
    reason: 'static_config' | 'latency_override';
    kalshiLatencyMs: number | null;
    polymarketLatencyMs: number | null;
  }
  ```

  - If `ADAPTIVE_SEQUENCING_ENABLED=false`, return `{ primaryLeg: staticPrimaryLeg, reason: 'static_config', kalshiLatencyMs: null, polymarketLatencyMs: null }`
  - Get P95 latency for both platforms via `healthService.getPlatformHealth(platform).latencyMs`
  - If either latency is null (no samples yet — startup, post-outage), fall back to static config (AC#2)
  - If `|kalshiLatency - polymarketLatency| > threshold`, use the platform with LOWER latency as primary
  - **Note:** `calculateP95Latency()` returns null when zero samples exist and is based on a rolling 100-sample window. With few samples (e.g., 5), the P95 is noisy but still a valid signal. The null check handles the truly-unknown case; the threshold handles the noise case (small differences are ignored).
  - Otherwise, use static config
  - Log the decision with both latency values
- [x] Call `determineSequencing()` at the top of `execute()`, use its `primaryLeg` instead of `dislocation.pairConfig.primaryLeg ?? 'kalshi'`
- [x] Carry `SequencingDecision` through execution for persistence and event emission

### Task 3: Data Source Classification in Execution (AC: #6)

- [x] Add `DataIngestionModule` import already handled in Task 2 — also need `DataDivergenceService` (already exported)
- [x] Inject `DataDivergenceService` into `ExecutionService`
- [x] After each `getAvailableDepth()` call, classify the data source per leg:
  - Call `connector.getOrderBookFreshness(contractId)` for each platform
  - Classify using the same logic as exit-monitor: null → 'polling', fresh WS → 'websocket', stale WS → 'stale_fallback'
  - Use `WS_STALENESS_THRESHOLD_MS` from ConfigService (already defined in env.schema.ts, default 60000ms) as the staleness boundary
  - Define `classifyDataSource()` as a private helper (or extract from exit-monitor into a shared utility in `common/utils/`)
  - Store per-leg classification using **platform-specific** names: `kalshiDataSource`, `polymarketDataSource` (NOT primary/secondary — avoids ambiguity when adaptive sequencing swaps leg order)
- [x] Check `DataDivergenceService.getDivergenceStatus(contractId)` per leg — if divergent, log warning with contract ID
- [x] Combine data sources using worst-of-two precedence (reuse pattern from exit-monitor)

### Task 4: Execution Metadata Persistence (AC: #5, #6)

- [x] Create Prisma migration adding to `OpenPosition`:
  ```prisma
  executionMetadata  Json?  @map("execution_metadata")
  ```
  JSON structure (uses platform-specific names, NOT primary/secondary — avoids ambiguity with adaptive sequencing):
  ```typescript
  {
    primaryLeg: string; // 'kalshi' | 'polymarket' — which went first
    sequencingReason: string; // 'static_config' | 'latency_override'
    kalshiLatencyMs: number | null;
    polymarketLatencyMs: number | null;
    idealCount: number;
    matchedCount: number;
    kalshiDataSource: string; // 'websocket' | 'polling' | 'stale_fallback'
    polymarketDataSource: string;
    divergenceDetected: boolean;
  }
  ```
- [x] Populate `executionMetadata` JSON in the `positionRepository.create()` call within `execute()`
- [x] No breaking schema changes — single nullable JSON column, backward-compatible

### Task 5: Polymarket Order Poll Configurability & Jitter (AC: tech debt Finding #7)

- [x] In `polymarket.connector.ts`, replace hardcoded constants with config values:

  ```typescript
  // BEFORE:
  // const ORDER_POLL_TIMEOUT_MS = 5000;
  // const ORDER_POLL_INTERVAL_MS = 500;

  // AFTER:
  const timeoutMs = this.configService.get<number>('POLYMARKET_ORDER_POLL_TIMEOUT_MS', 5000);
  const baseIntervalMs = this.configService.get<number>('POLYMARKET_ORDER_POLL_INTERVAL_MS', 500);
  ```

- [x] Add jitter to poll interval: `const interval = baseIntervalMs + Math.floor(Math.random() * (baseIntervalMs * 0.2))` — 0-20% random jitter
- [x] Inject `ConfigService` into `PolymarketConnector` constructor (check if already injected — it may be via `ConnectorModule`)

### Task 6: Dashboard Backend — Execution Metadata (AC: #5)

- [x] Extend `PositionFullDetailDto` with optional execution metadata fields (platform-specific names):
  - `executionPrimaryLeg?: string` — which platform went first
  - `executionSequencingReason?: string` — 'static_config' | 'latency_override'
  - `executionKalshiLatencyMs?: number | null`
  - `executionPolymarketLatencyMs?: number | null`
  - `executionIdealCount?: number`
  - `executionMatchedCount?: number`
  - `executionKalshiDataSource?: string` — 'websocket' | 'polling' | 'stale_fallback'
  - `executionPolymarketDataSource?: string`
  - `executionDivergenceDetected?: boolean`
- [x] In `DashboardService`, map `executionMetadata` JSON to flat DTO fields when building position detail
- [x] Extend `WsExecutionCompletePayload` with optional `sequencingReason?: string` and `primaryLeg?: string`
- [x] In `DashboardEventMapperService.mapOrderFilled()`, populate new fields from enriched `OrderFilledEvent`
- [x] Extend `OrderFilledEvent` with optional `sequencingDecision?: SequencingDecision` field (only populated for the first leg's event)

### Task 7: Dashboard Frontend — Execution Detail (AC: #5)

- [x] In `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx`:
  - Add "Execution Info" section for positions with `executionMetadata`:
    - Primary leg platform with badge
    - Sequencing reason badge (green for static, amber for latency override)
    - Latency measurements for both platforms (show "N/A" if null)
    - Ideal count vs matched count (show difference if depth-capped)
    - Data source per leg with badge (green=websocket, gray=polling, red=stale_fallback)
    - Divergence warning if detected
  - Use existing `StatusBadge` and `MetricDisplay` component patterns
- [x] Regenerate API client: `cd pm-arbitrage-dashboard && pnpm generate-api`

### Task 8: Tests (AC: #1-#7)

- [x] **Unified sizing formula tests** (~10 tests in `execution.service.spec.ts`):
  - Verify `idealCount = floor(reservedCapital / (primaryDivisor + secondaryDivisor))` produces correct counts
  - Verify total capital used ≤ `reservedCapitalUsd` (the bug this formula fixes)
  - Verify depth capping uses single `idealCount` for both legs
  - Verify edge re-validation uses `equalizedSize * combinedDivisor` as position size
  - Verify `combinedDivisor ≤ 0` returns `GENERIC_EXECUTION_FAILURE` error and emits `ExecutionFailedEvent`
  - Verify existing min-fill-ratio logic still works with single `idealCount`
  - Verify clean reservation release on depth check failure with unified sizing (AC#4 regression)
  - Regression: verify equalization still produces equal leg sizes

- [x] **Adaptive sequencing tests** (~8 tests in `execution.service.spec.ts`):
  - Kalshi latency 100ms, Polymarket 400ms, threshold 200ms → Kalshi goes first (latency override)
  - Kalshi latency 300ms, Polymarket 100ms, threshold 200ms → Polymarket goes first (latency override)
  - Kalshi latency 200ms, Polymarket 300ms, threshold 200ms → static config (difference = 100ms < 200ms)
  - Kalshi latency null, Polymarket 100ms → static config (null fallback)
  - Both latencies null → static config
  - `ADAPTIVE_SEQUENCING_ENABLED=false` → always static config
  - Override logged with both latency values

- [x] **Data source classification tests** (~5 tests in `execution.service.spec.ts`):
  - WS fresh → classifies as 'websocket'
  - WS null → classifies as 'polling'
  - WS stale → classifies as 'stale_fallback'
  - Divergence detected → warning logged, execution proceeds
  - Combined data source uses worst-of-two precedence

- [x] **Execution metadata persistence tests** (~3 tests):
  - Verify `executionMetadata` JSON persisted on position create
  - Verify all fields populated (primaryLeg, reason, latencies, counts, kalshiDataSource, polymarketDataSource)
  - Verify null latencies stored correctly

- [x] **Polymarket poll configurability tests** (~4 tests in `polymarket.connector.spec.ts`):
  - Custom timeout via config → poll loop respects it
  - Custom interval via config → poll loop uses it
  - Jitter applied (interval varies between base and base × 1.2)
  - Default values used when config not set

- [x] **Internal subsystem verification** (Team Agreement #19, ~3 tests):
  - Verify orders actually reach connector mocks (not just sizing logic)
  - Verify `getOrderBookFreshness()` actually called per leg
  - Verify `getDivergenceStatus()` actually called for each contract

- [x] **Paper/live boundary tests** (Team Agreement #20, ~3 tests):
  - Paper mode: adaptive sequencing still works (uses paper connector health → latency from PlatformHealthService)
  - Live mode: real latency data drives sequencing
  - Both modes: unified sizing formula identical

- [x] **Dashboard backend tests** (~3 tests):
  - Position detail DTO includes execution metadata fields
  - WS execution complete event includes sequencing info
  - Null execution metadata handled gracefully (pre-10.4 positions)

## Dev Notes

### Design Decisions

**Unified Sizing Formula — Capital Conservation Fix:**
The current code computes `idealSize = reservedCapitalUsd / primaryDivisor` and `secondaryIdealSize = reservedCapitalUsd / secondaryDivisor` independently, treating the entire reserved capital as available for each leg. This double-counts the budget. Example:

- Budget: $100, Buy @ 0.17 (divisor 0.17), Sell @ 0.21 (divisor 0.79)
- Current: primaryIdeal = 588, secondaryIdeal = 126, equalized = 126. Actual capital: 126 × 0.17 + 126 × 0.79 = **$120.96** (20.96% over-budget)
- Unified: idealCount = floor(100 / 0.96) = 104. Actual capital: 104 × 0.17 + 104 × 0.79 = **$99.84** (within budget)

The unified formula `floor(reservedCapitalUsd / (primaryDivisor + secondaryDivisor))` guarantees total capital ≤ reservation. The `combinedDivisor` = `primaryDivisor + secondaryDivisor` represents the true per-contract cost of the hedged pair.

[Source: architecture.md#Execution-Position-Sizing-Model — "True matched-count execution... using a unified sizing formula"]
[Source: epics.md#Story-6.5.5b — "MVP model computes leg sizes independently... producing mismatched contract counts"]
[Verified: execution.service.ts lines 228-230, 322-325 — current independent sizing confirmed]

**Latency Source — PlatformHealthService P95:**
Connectors' `getHealth()` returns `latencyMs: null` on both platforms [Verified: kalshi.connector.ts:567, polymarket.connector.ts:491]. The only latency data comes from `PlatformHealthService.calculateP95Latency()`, computed from order book fetch timing (rolling 100-sample window) [Verified: platform-health.service.ts:466-472]. This is a platform-responsiveness proxy, not execution latency, but it's the available signal and correlates with platform health.

`PlatformHealthService` IS exported from `DataIngestionModule` [Verified: data-ingestion.module.ts exports array]. The execution module needs to add `DataIngestionModule` to its imports.

[Source: prd.md#FR-EX-08 — "adapt leg sequencing based on venue-specific latency profiles"]

**Data Source Tracking — REST Is Already Conservative:**
`getOrderBook()` ALWAYS makes a fresh REST call — it does NOT return cached WS data [Verified: kalshi.connector.ts:294-334, polymarket.connector.ts submitOrder]. WS data is tracked separately via `getOrderBookFreshness()` for freshness classification only. Since the execution path already uses REST (the authoritative source), AC#6's "use the more conservative depth" is inherently satisfied. The story adds:

1. Data source classification per leg (informational — what WAS available)
2. Divergence status check via `DataDivergenceService` (warn if prices diverge)
3. Persistence of classification in execution metadata

[Source: exit-monitor.service.ts:1358-1375 — classifyDataSource() pattern]
[Verified: DataDivergenceService exported from DataIngestionModule]

**Sequencing Decision as First-Class Object:**
The `SequencingDecision` interface captures the full context: which platform goes first, why, and the latency measurements. This flows through execution → position metadata → dashboard, creating a complete audit trail.

**Execution Metadata as JSON Column:**
Rather than adding multiple nullable columns to `OpenPosition`, a single `executionMetadata Json?` column stores the sequencing context. This is forward-compatible (future execution context can be added without migrations), matches the existing pattern used for `reconciliationContext Json?` and `entryPrices Json`, and avoids schema bloat.

### Position Sizing — Before vs After

```
BEFORE (current — independent per-leg):
  primaryIdeal   = floor(reservedCapital / primaryDivisor)
  secondaryIdeal = floor(reservedCapital / secondaryDivisor)
  primaryCapped  = min(primaryIdeal, primaryDepth)
  secondaryCapped = min(secondaryIdeal, secondaryDepth)
  equalized = min(primaryCapped, secondaryCapped)
  → Can over-deploy capital (both legs "claim" full budget)

AFTER (unified):
  idealCount     = floor(reservedCapital / (primaryDivisor + secondaryDivisor))
  primaryCapped  = min(idealCount, primaryDepth)
  secondaryCapped = min(idealCount, secondaryDepth)
  matchedCount   = min(primaryCapped, secondaryCapped)
  → Total capital ≤ reservation guaranteed
```

### Sequencing Decision Flow

```
execute(opportunity, reservation)
  │
  ├─ [1] Get static primaryLeg from pairConfig (default 'kalshi')
  ├─ [2] determineSequencing(staticPrimaryLeg)
  │     ├─ ADAPTIVE_SEQUENCING_ENABLED=false → static
  │     ├─ Get P95 latency for both platforms
  │     ├─ Either null → static (AC#2)
  │     ├─ |delta| ≤ threshold → static (AC#2)
  │     └─ |delta| > threshold → lower-latency platform first (AC#1)
  │
  ├─ [3] resolveConnectors(decision.primaryLeg) — existing method, unchanged
  ├─ [4] Unified sizing → depth check → equalization → edge re-validation
  ├─ [5] Classify data source per leg (getOrderBookFreshness)
  ├─ [6] Check divergence status per leg (DataDivergenceService)
  ├─ [7] Submit primary → submit secondary (existing flow)
  └─ [8] Persist position with executionMetadata JSON
```

### Module Dependency Change

```
// BEFORE:
ExecutionModule.imports = [RiskManagementModule, ConnectorModule]

// AFTER:
ExecutionModule.imports = [RiskManagementModule, ConnectorModule, DataIngestionModule]
```

This is allowed per CLAUDE.md module dependency rules: `modules/execution/` → `connectors/` + `modules/risk-management/` are listed. Adding `modules/data-ingestion/` for health/divergence data is architecturally sound — execution already depends on platform data (via connectors). The dependency is read-only: execution queries health/divergence status, does not write.

[Source: CLAUDE.md#Module-Dependency-Rules — allowed imports list]

### Polymarket Order Poll Jitter (Tech Debt Finding #7)

**Current** (polymarket.connector.ts:574-575):

```typescript
const ORDER_POLL_TIMEOUT_MS = 5000; // hardcoded
const ORDER_POLL_INTERVAL_MS = 500; // hardcoded, no jitter
```

**After:**

```typescript
const timeoutMs = this.configService.get<number>('POLYMARKET_ORDER_POLL_TIMEOUT_MS', 5000);
const baseIntervalMs = this.configService.get<number>('POLYMARKET_ORDER_POLL_INTERVAL_MS', 500);
// 0-20% random jitter prevents thundering herd if multiple orders poll simultaneously
const interval = baseIntervalMs + Math.floor(Math.random() * (baseIntervalMs * 0.2));
```

Kalshi does NOT need this — it returns order status immediately in the REST response [Verified: kalshi.connector.ts:347-426, no polling loop].

[Source: 6-5-0-code-review-findings.md#Finding-7 — "make timeouts configurable via @nestjs/config and add jitter"]
[Source: epics.md#Story-10.4-Tech-Debt-Notes — "When implementing Story 10.4, make these timeouts configurable"]

### Data Source Classification Helper

Extract the classification logic from exit-monitor into a shared utility or inline as a private method. Pattern from exit-monitor.service.ts:1358-1364:

```typescript
classifyDataSource(lastWsUpdateAt: Date | null, now: Date, stalenessThresholdMs: number): DataSource {
  if (lastWsUpdateAt === null) return 'polling';
  const age = now.getTime() - lastWsUpdateAt.getTime();
  return age >= stalenessThresholdMs ? 'stale_fallback' : 'websocket';
}
```

Decision: Inline as private method in `ExecutionService` (same as exit-monitor pattern). If a third consumer needs it later, extract to `common/utils/`. Avoid premature abstraction.

[Verified: exit-monitor.service.ts:1358-1364 — existing pattern]
[Verified: WS_STALENESS_THRESHOLD_MS config key exists in env.schema.ts]

### Files to Modify

| File                                                      | Changes                                                                                                                            |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `src/common/config/env.schema.ts`                         | +4 config keys (ADAPTIVE_SEQUENCING_ENABLED, \_LATENCY_THRESHOLD_MS, POLYMARKET_ORDER_POLL_TIMEOUT_MS, \_INTERVAL_MS)              |
| `src/modules/execution/execution.service.ts`              | Unified sizing formula, adaptive sequencing via `determineSequencing()`, data source classification, execution metadata population |
| `src/modules/execution/execution.module.ts`               | +DataIngestionModule import                                                                                                        |
| `src/connectors/polymarket/polymarket.connector.ts`       | Replace hardcoded ORDER*POLL*\* with ConfigService + jitter                                                                        |
| `src/dashboard/dto/position-detail.dto.ts`                | +execution metadata fields on PositionFullDetailDto                                                                                |
| `src/dashboard/dto/ws-events.dto.ts`                      | +sequencingReason, primaryLeg on WsExecutionCompletePayload                                                                        |
| `src/dashboard/dashboard.service.ts`                      | Map executionMetadata JSON → DTO fields in position detail                                                                         |
| `src/dashboard/dashboard-event-mapper.service.ts`         | Map OrderFilledEvent sequencing fields to WS payload                                                                               |
| `src/common/events/execution.events.ts`                   | +sequencingDecision field on OrderFilledEvent                                                                                      |
| `prisma/schema.prisma`                                    | +executionMetadata Json? on OpenPosition                                                                                           |
| `.env.example`                                            | +4 config keys with comments                                                                                                       |
| `.env.development`                                        | +4 config keys                                                                                                                     |
| `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx` | +Execution Info section                                                                                                            |
| `pm-arbitrage-dashboard/src/api/generated/Api.ts`         | Regenerate after DTO changes                                                                                                       |

### Files NOT Modified (Verified Unchanged)

| File                                    | Reason                                                                |
| --------------------------------------- | --------------------------------------------------------------------- |
| `execution-queue.service.ts`            | Calls `execute()` — no change needed, receives same `ExecutionResult` |
| `risk-manager.service.ts`               | `reserveBudget()` unchanged — capital semantics preserved             |
| `single-leg-resolution.service.ts`      | Post-execution resolution unchanged                                   |
| `auto-unwind.service.ts`                | Event-driven, no sizing dependency                                    |
| `exit-monitor.service.ts`               | Independent data source classification, no coupling                   |
| `connectors/kalshi/kalshi.connector.ts` | No polling loop, instant REST response                                |

### Existing Code to Reuse (DO NOT REINVENT)

- **`resolveConnectors(primaryLeg)`** — Returns primary/secondary connectors and platforms. Unchanged — called with `SequencingDecision.primaryLeg` instead of static config.
- **`getAvailableDepth()`** — Unchanged depth query method. Still returns depth from REST order book.
- **Edge re-validation block** — Existing gas fraction recalculation. Minor adjustment: uses `combinedDivisor` instead of `primaryDivisor.plus(secondaryDivisor)` (same value, already computed).
- **`handleSingleLeg()`** — Unchanged. Receives same `SingleLegContext` regardless of sequencing.
- **`PlatformHealthService.getPlatformHealth(platform).latencyMs`** — Existing P95 latency query.
- **`DataDivergenceService.getDivergenceStatus(contractId)`** — Existing divergence check.
- **`getOrderBookFreshness(contractId)`** — Existing WS freshness query on both connectors.
- **`StatusBadge`, `MetricDisplay`** components in dashboard — Reuse for execution info display.

### Anti-Patterns to Avoid

- **DO NOT** add execution latency tracking to connectors — use PlatformHealthService P95 (order book fetch latency as proxy)
- **DO NOT** add `getWsOrderBook()` to IPlatformConnector — REST `getOrderBook()` is already the authoritative conservative source
- **DO NOT** duplicate data source classification into a shared utility prematurely — inline in ExecutionService, extract if a third consumer appears
- **DO NOT** modify `resolveConnectors()` — it already accepts a `primaryLeg` string, just pass the adaptive decision
- **DO NOT** add multiple nullable columns to OpenPosition — use a single `executionMetadata Json?` column (matches `reconciliationContext` pattern)
- **DO NOT** use native JS operators for financial math — `decimal.js` only for `combinedDivisor`, `idealCount` computation
- **DO NOT** throw raw `Error` — use `ExecutionError` from `common/errors/`
- **DO NOT** block on `DataDivergenceService` results — divergence check is informational, not a gate
- **DO NOT** import `PlatformHealthService` or `DataDivergenceService` directly — import `DataIngestionModule` which exports both
- **DO NOT** use `reservedCapitalUsd / buyPrice` or `reservedCapitalUsd / sellPrice` — use collateral-aware divisors (buy → price, sell → 1-price)

### Testing Conventions (from Epic 9 Retro)

- **Internal subsystem verification (Team Agreement #19):** Tests must verify orders actually reach connector mocks. Don't just test that the unified formula computes correct counts — verify `submitOrder()` was called with those counts.
- **Paper/live boundary (Team Agreement #20):** Adaptive sequencing should work identically in paper mode. PlatformHealthService tracks latency from real data feeds even when execution is simulated.
- **Vertical slice minimum (Team Agreement #18):** Dashboard shows execution metadata for every position. Pre-10.4 positions show "N/A" gracefully.

### Concurrency & Edge Cases

1. **Latency data unavailable at startup:** Before any order book updates, `calculateP95Latency()` returns null. Sequencing falls back to static config (AC#2). No special handling needed.
2. **Both platforms have identical latency:** Difference = 0 ≤ threshold → static config used. No tie-breaking needed.
3. **One platform degraded:** `PlatformHealthService` still reports latency for degraded platforms (from recent samples). Sequencing proceeds normally. If truly disconnected (no samples), latency = null → static fallback.
4. **Config hot-reload:** `ConfigService.get()` reads current config on each call. `ADAPTIVE_SEQUENCING_ENABLED` change takes effect on next execution cycle.
5. **Existing positions:** Pre-10.4 positions have `executionMetadata: null`. Dashboard handles gracefully with "N/A" display.

### Key Implementation Details

**DataIngestionModule Import:**

```typescript
@Module({
  imports: [RiskManagementModule, ConnectorModule, DataIngestionModule],
  // ...
})
export class ExecutionModule {}
```

**SequencingDecision Type:** Define in `execution.service.ts` (private to execution module, not a shared type). If needed externally later, move to `common/types/`.

**Polymarket ConfigService Access:** The Polymarket connector already receives `ConfigService` via constructor injection [Verified: polymarket.connector.ts constructor]. No additional wiring needed.

**WS Staleness Threshold:** Reuse `WS_STALENESS_THRESHOLD_MS` from env.schema.ts (already defined, default 60000ms). No new threshold constant needed for data source classification.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-10.4] — Acceptance criteria, dependencies, vertical slice
- [Source: _bmad-output/planning-artifacts/prd.md#FR-EX-08] — Adaptive leg sequencing requirement
- [Source: _bmad-output/planning-artifacts/prd.md#FR-EX-03a] — Edge re-validation with execution-time contract counts
- [Source: _bmad-output/planning-artifacts/architecture.md#Execution-Position-Sizing-Model] — Unified sizing formula specification
- [Source: _bmad-output/implementation-artifacts/6-5-0-code-review-findings.md#Finding-7] — Polymarket hardcoded timeouts tech debt
- [Source: _bmad-output/implementation-artifacts/6-5-5h-execution-equal-leg-sizing.md] — Collateral-aware sizing, cross-leg equalization
- [Source: Team Agreement #18] — Vertical slice minimum (dashboard observability)
- [Source: Team Agreement #19] — Internal subsystem verification (connector mock verification)
- [Source: Team Agreement #20] — Paper/live boundary testing
- [Source: Team Agreement #23] — Two-data-path divergence monitoring
- [Verified: execution.service.ts:228-362] — Current independent sizing + equalization code
- [Verified: platform-health.service.ts:466-472] — P95 latency calculation
- [Verified: kalshi.connector.ts:567, polymarket.connector.ts:491] — getHealth() returns latencyMs: null
- [Verified: data-ingestion.module.ts exports] — PlatformHealthService, DataDivergenceService exported
- [Verified: polymarket.connector.ts:574-575] — Hardcoded ORDER_POLL_TIMEOUT_MS/INTERVAL_MS
- [Verified: kalshi.connector.ts:347-426] — No polling loop (instant REST response)
- [Verified: exit-monitor.service.ts:1358-1364] — Data source classification pattern
- [Verified: prisma/schema.prisma:226] — reconciliationContext Json? column pattern

### Previous Story Intelligence (from 10-3)

- AutoUnwindService added as event-driven handler for single-leg exposure — orthogonal to this story
- Test count at story start: 2369 tests (2321 → 2369 via 10-3 + code reviews)
- `@OnEvent` wiring pattern established: subscribe in service, emit result event
- Dashboard DTOs extended additively (optional fields, no breaking changes)
- Code review found `.abs()` masking profitable closes, null guards, config boolean defense — test edge cases thoroughly
- Config keys follow UPPER_SNAKE_CASE convention with descriptive prefixes

### Git Intelligence

Recent commits follow `feat:` prefix convention. Key patterns:

- Services registered in module providers, NOT exports (unless other modules inject them)
- Config keys added to both `.env.example` and `.env.development` simultaneously
- Dashboard DTOs extended additively (new optional fields)
- Tests co-located: `*.spec.ts` next to source file
- Prisma migrations via `pnpm prisma migrate dev --name <name>`

---

## Dev Agent Record

### Implementation Summary (2026-03-21)

**Test count:** 2369 → 2409 (+40 unit tests) + 5 E2E tests (all passing)
**Lint:** 0 errors, 4 pre-existing warnings
**Build:** Clean (both engine and dashboard)

### Files Created

- `prisma/migrations/20260321204003_add_execution_metadata/migration.sql` — adds `execution_metadata` nullable JSON column to `open_positions`

### Files Modified

| File                                                      | Changes                                                                                                                                                                                                                                                        |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/common/config/env.schema.ts`                         | +4 config keys (ADAPTIVE_SEQUENCING_ENABLED, \_LATENCY_THRESHOLD_MS, POLYMARKET_ORDER_POLL_TIMEOUT_MS, \_INTERVAL_MS)                                                                                                                                          |
| `src/modules/execution/execution.service.ts`              | Unified sizing formula (combinedDivisor), `determineSequencing()` + `classifyDataSource()` private methods, `PlatformHealthService` + `DataDivergenceService` injection, `executionMetadata` JSON population, `sequencingDecision` on primary OrderFilledEvent |
| `src/modules/execution/execution.module.ts`               | +DataIngestionModule import                                                                                                                                                                                                                                    |
| `src/modules/execution/execution.service.spec.ts`         | Fixed 14 existing tests for unified formula (222→111, 126→104, actualCapitalUsed recalc), added PlatformHealthService/DataDivergenceService mocks, unskipped+fixed 31 ATDD tests                                                                               |
| `src/common/events/execution.events.ts`                   | +optional `sequencingDecision` field on OrderFilledEvent                                                                                                                                                                                                       |
| `src/connectors/polymarket/polymarket.connector.ts`       | Replaced hardcoded ORDER*POLL*\* with configService.get + 0-20% jitter                                                                                                                                                                                         |
| `src/connectors/polymarket/polymarket.connector.spec.ts`  | Unskipped+fixed 4 ATDD tests (configService spy pattern)                                                                                                                                                                                                       |
| `src/dashboard/dto/position-detail.dto.ts`                | +9 execution metadata fields on PositionFullDetailDto                                                                                                                                                                                                          |
| `src/dashboard/dto/ws-events.dto.ts`                      | +sequencingReason, primaryLeg on WsExecutionCompletePayload                                                                                                                                                                                                    |
| `src/dashboard/dashboard.service.ts`                      | +mapExecutionMetadata() helper, spread into getPositionDetails return                                                                                                                                                                                          |
| `src/dashboard/dashboard.service.spec.ts`                 | Unskipped+fixed 3 ATDD tests (corrected field names, mock data)                                                                                                                                                                                                |
| `src/dashboard/dashboard-event-mapper.service.ts`         | Spread sequencingDecision into WS execution complete payload                                                                                                                                                                                                   |
| `src/dashboard/dashboard-event-mapper.service.spec.ts`    | Unskipped+fixed 2 ATDD tests (sequencingDecision on event)                                                                                                                                                                                                     |
| `prisma/schema.prisma`                                    | +executionMetadata Json? on OpenPosition                                                                                                                                                                                                                       |
| `.env.example`                                            | +4 config keys with descriptions                                                                                                                                                                                                                               |
| `.env.development`                                        | +4 config keys                                                                                                                                                                                                                                                 |
| `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx` | +ExecutionInfoSection component (primary leg, sequencing, latencies, counts, data sources, divergence warning)                                                                                                                                                 |
| `pm-arbitrage-dashboard/src/api/generated/Api.ts`         | Regenerated from swagger                                                                                                                                                                                                                                       |
| `e2e/tests/ui/execution-metadata-display.spec.ts`         | Unskipped 5 E2E tests, fixed data-variant expectations + data-testid placement                                                                                                                                                                                 |

### Key Design Decisions

1. **ADAPTIVE_SEQUENCING_ENABLED uses string→boolean defense** — ConfigService may return raw string in test environments despite Zod transform. Implementation checks both `true` and `'true'`.
2. **executionMetadata persisted via JSON.parse(JSON.stringify())** — Prisma's `InputJsonValue` type doesn't accept plain objects directly; round-trip serialization produces a clean JSON-compatible value.
3. **Data source classification inlined** — Private `classifyDataSource()` on ExecutionService (not shared utility), matching exit-monitor pattern. Extract if third consumer appears.
4. **ATDD tests required significant fixes** — 40 tests were generated pre-implementation with incorrect mock targets (connector.getHealth vs platformHealthService.getPlatformHealth), wrong field names (sequencingDecision vs sequencingReason), and result.executionMetadata (doesn't exist on ExecutionResult). All fixed to match actual implementation.
