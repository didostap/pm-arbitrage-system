# Story 3.3: Edge Calculation & Opportunity Filtering

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want each opportunity's net edge calculated accounting for all real costs, and sub-threshold opportunities filtered out,
so that only genuinely profitable opportunities are surfaced.

**FRs covered:** FR-AD-02 (Calculate expected edge accounting for fees, gas, liquidity depth), FR-AD-03 (Filter opportunities below minimum edge threshold)

## Acceptance Criteria

### AC1: Net Edge Calculation from Raw Dislocations

**Given** a raw price dislocation is passed from the detection service (Story 3.2) as `RawDislocation`
**When** the `EdgeCalculatorService.calculateEdge()` processes it
**Then** net edge is calculated using `FinancialMath.calculateNetEdge()` with:
- `grossEdge` from the `RawDislocation`
- `buyPrice` and `sellPrice` from the `RawDislocation`
- `buyFeeSchedule` from the buy platform connector's `getFeeSchedule()`
- `sellFeeSchedule` from the sell platform connector's `getFeeSchedule()`
- `gasEstimateUsd` from config (`DETECTION_GAS_ESTIMATE_USD`, default `0.30`)
- `positionSizeUsd` from config (`DETECTION_POSITION_SIZE_USD`, default `300`) — this is a **reference position size** for edge percentage calculation, NOT the actual trade size (actual sizing is Epic 4). Default $300 approximates MVP typical trade size ($10K bankroll × 3% per pair = $300). This matters because gas is converted to a percentage via `gasUsd / positionSizeUsd` — too low a reference overstates gas impact and filters too aggressively.
**And** fees are sourced dynamically from each platform connector's `getFeeSchedule()` (FR-AD-02)

### AC2: Opportunity Filtering Below Threshold

**Given** the edge calculator produces a net edge result
**When** net edge is below the minimum threshold (config `DETECTION_MIN_EDGE_THRESHOLD`, default `0.008` = 0.8%)
**Then** the opportunity is filtered out (FR-AD-03)
**And** filtered opportunities are logged at `debug` level with: pair event description, net edge value, threshold, filter reason
**And** an `OpportunityFilteredEvent` is emitted via EventEmitter2 with full context

### AC3: Threshold Multiplier for Degraded Platforms

**Given** a platform is degraded and `DegradationProtocolService.getEdgeThresholdMultiplier()` returns 1.5
**When** the edge calculator applies the threshold
**Then** the effective threshold is `baseThreshold * multiplier` (e.g., 0.008 * 1.5 = 0.012)
**And** only opportunities with net edge >= 0.012 pass during degradation (NFR-R2)

### AC4: Enriched Opportunity Output

**Given** the edge calculator produces a result
**When** net edge meets or exceeds the effective threshold
**Then** an `EnrichedOpportunity` is produced with: `RawDislocation` data, net edge (Decimal), gross edge (Decimal), fee breakdown (buy fee cost, sell fee cost, gas fraction), liquidity depth (best bid/ask sizes from both order books), and `recommendedPositionSize: null` (placeholder for Epic 4)
**And** an `OpportunityIdentifiedEvent` is emitted via EventEmitter2 with full enriched context
**And** this is the **single public event** that downstream modules (execution, monitoring) subscribe to

### AC5: Detection Cycle Summary Logging

**Given** a detection cycle completes (all dislocations processed through edge calculator)
**When** results are summarized
**Then** a log entry is emitted with: total raw dislocations input, total filtered (with breakdown: below threshold, other reasons), total actionable opportunities, cycle duration
**And** this is logged at `log` level with correlationId

### AC6: Edge Calculator Wired into Detection Pipeline

**Given** the `EdgeCalculatorService` is created in the `arbitrage-detection` module
**When** `TradingEngineService.executeCycle()` runs Step 2
**Then** after `DetectionService.detectDislocations()`, each `RawDislocation` is passed to `EdgeCalculatorService.processDislocations(dislocations)`
**And** the method returns `EdgeCalculationResult` with: `opportunities` (enriched), `filtered` (with reasons), `summary` counts

### AC7: Event Classes Created

**Given** this story creates domain event classes
**When** `OpportunityIdentifiedEvent` and `OpportunityFilteredEvent` are implemented
**Then** they extend `BaseEvent` from `common/events/base.event.ts`
**And** they are placed in `common/events/detection.events.ts`
**And** they use event names from `EVENT_NAMES.OPPORTUNITY_IDENTIFIED` and `EVENT_NAMES.OPPORTUNITY_FILTERED` in the catalog

### AC8: Configuration via Environment Variables

**Given** edge calculation config values are needed
**When** the engine starts
**Then** the following env vars are loaded via `ConfigService`:
- `DETECTION_MIN_EDGE_THRESHOLD` (default: `0.008`) — decimal, e.g., 0.008 = 0.8%
- `DETECTION_GAS_ESTIMATE_USD` (default: `0.30`) — static conservative gas estimate in USD
- `DETECTION_POSITION_SIZE_USD` (default: `300`) — reference position size for edge % calculation (approximates $10K bankroll × 3%)
**And** invalid values (negative, NaN) are rejected at startup with clear error

### AC9: Existing Test Suite Regression

**Given** all Story 3.3 changes are complete
**When** `pnpm test` runs
**Then** all 349 existing tests continue to pass
**And** new tests for `EdgeCalculatorService` add 15+ test cases
**And** `pnpm lint` passes with no errors

## Tasks / Subtasks

- [x] Task 1: Create Detection Event Classes (AC: #7)
  - [x]1.1 Create `src/common/events/detection.events.ts` with `OpportunityIdentifiedEvent` and `OpportunityFilteredEvent` extending `BaseEvent`
  - [x]1.2 Export from `src/common/events/index.ts`

- [x]Task 2: Create EnrichedOpportunity and EdgeCalculationResult Types (AC: #4, #6)
  - [x]2.1 Create `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts`
  - [x]2.2 Create `src/modules/arbitrage-detection/types/edge-calculation-result.type.ts`
  - [x]2.3 Export from `src/modules/arbitrage-detection/types/index.ts`

- [x]Task 3: Create EdgeCalculatorService (AC: #1, #2, #3, #4, #5)
  - [x]3.1 Create `src/modules/arbitrage-detection/edge-calculator.service.ts`
  - [x]3.2 Inject: `ConfigService`, `DegradationProtocolService`, `KalshiConnector`, `PolymarketConnector`, `EventEmitter2`
  - [x]3.3 Implement `processDislocations(dislocations: RawDislocation[]): EdgeCalculationResult`
  - [x]3.4 For each dislocation: get fee schedules, calculate net edge via `FinancialMath.calculateNetEdge()`
  - [x]3.5 Apply threshold multiplier from `DegradationProtocolService.getEdgeThresholdMultiplier()`
  - [x]3.6 Filter using `FinancialMath.isAboveThreshold(netEdge, effectiveThreshold)`
  - [x]3.7 Emit `OpportunityFilteredEvent` for filtered dislocations
  - [x]3.8 Build `EnrichedOpportunity` for passing dislocations
  - [x]3.9 Emit `OpportunityIdentifiedEvent` for enriched opportunities
  - [x]3.10 Return `EdgeCalculationResult` with summary counts
  - [x]3.11 Log cycle summary at `log` level

- [x]Task 4: Add EdgeCalculatorService to ArbitrageDetectionModule (AC: #6)
  - [x]4.1 Register `EdgeCalculatorService` as provider in `arbitrage-detection.module.ts`
  - [x]4.2 Export `EdgeCalculatorService`

- [x]Task 5: Wire into TradingEngineService (AC: #6)
  - [x]5.1 Add `EdgeCalculatorService` injection to `TradingEngineService` constructor
  - [x]5.2 After detection step, call `edgeCalculator.processDislocations(detectionResult.dislocations)`
  - [x]5.3 Log edge calculation results; opportunities are surfaced via events (no direct execution call yet — Epic 4/5)

- [x]Task 6: Add Configuration (AC: #8)
  - [x]6.1 Add `DETECTION_MIN_EDGE_THRESHOLD`, `DETECTION_GAS_ESTIMATE_USD`, `DETECTION_POSITION_SIZE_USD` to `.env.development` and `.env.example`
  - [x]6.2 Load via `ConfigService.get()` with defaults in `EdgeCalculatorService`
  - [x]6.3 Validate at startup (no negative values, no NaN)

- [x]Task 7: Write Tests (AC: #9)
  - [x]7.1 Create `src/modules/arbitrage-detection/edge-calculator.service.spec.ts`
  - [x]7.2 Test: calculates net edge correctly using FinancialMath (use CSV scenarios from Sprint 0)
  - [x]7.3 Test: filters opportunity below threshold (default 0.8%)
  - [x]7.4 Test: passes opportunity at exact threshold boundary (0.8%)
  - [x]7.5 Test: passes opportunity above threshold
  - [x]7.6 Test: applies 1.5x threshold multiplier when platform is degraded
  - [x]7.7 Test: emits `OpportunityFilteredEvent` for filtered dislocations
  - [x]7.8 Test: emits `OpportunityIdentifiedEvent` for passing dislocations
  - [x]7.9 Test: enriched opportunity includes fee breakdown and liquidity depth
  - [x]7.10 Test: processes multiple dislocations and returns correct summary counts
  - [x]7.11 Test: handles empty dislocations array gracefully
  - [x]7.12 Test: fetches fee schedules from correct connector per platform
  - [x]7.13 Test: uses configurable threshold from ConfigService
  - [x]7.14 Test: uses configurable gas estimate from ConfigService
  - [x]7.15 Test: uses configurable position size from ConfigService
  - [x]7.16 Test: negative net edge is filtered
  - [x]7.17 Test: threshold multiplier 1.0 when no platforms degraded (threshold unchanged)
  - [x]7.18 Test: skips dislocation gracefully when getFeeSchedule() throws, logs error, continues batch
  - [x]7.19 Run full regression: `pnpm test` — all 349+ tests pass

- [x]Task 8: Lint & Final Check (AC: #9)
  - [x]8.1 Run `pnpm lint` and fix any issues
  - [x]8.2 Verify no import boundary violations

## Dev Notes

### Architecture Constraints

- `EdgeCalculatorService` lives in `src/modules/arbitrage-detection/` — same module as `DetectionService`
- Allowed imports per CLAUDE.md dependency rules:
  - `modules/arbitrage-detection/` → `common/` (types, utils, events, errors)
  - `modules/arbitrage-detection/` → `modules/contract-matching/` (if needed, but not for this story)
  - `core/ → modules/*` (TradingEngine orchestrates via DI)
- The module already imports `ConnectorModule` and `DataIngestionModule` from Story 3.2

### Connector Access Pattern — Same as Story 3.2

Inject concrete connector classes directly (`KalshiConnector`, `PolymarketConnector`), not via `IPlatformConnector` interface. Use the same `getConnector(platformId)` pattern from `DetectionService`:

```typescript
private getConnector(platformId: PlatformId): KalshiConnector | PolymarketConnector {
  return platformId === PlatformId.KALSHI
    ? this.kalshiConnector
    : this.polymarketConnector;
}
```

Call `getConnector(buyPlatformId).getFeeSchedule()` and `getConnector(sellPlatformId).getFeeSchedule()` to get fee schedules dynamically.

### FinancialMath — All Methods Already Exist

All three methods needed are already implemented and tested from Sprint 0:

```typescript
import { FinancialMath, FinancialDecimal } from '../../common/utils';

// Already exists:
FinancialMath.calculateNetEdge(grossEdge, buyPrice, sellPrice, buyFeeSchedule, sellFeeSchedule, gasEstimateUsd, positionSizeUsd)
FinancialMath.isAboveThreshold(netEdge, threshold)
```

`calculateNetEdge` expects:
- `grossEdge`, `buyPrice`, `sellPrice`, `gasEstimateUsd`, `positionSizeUsd` as `Decimal` (use `FinancialDecimal`)
- `buyFeeSchedule`, `sellFeeSchedule` as `FeeSchedule` with `takerFeePercent` on 0-100 scale (e.g., 2.0 = 2%)

Formula: `netEdge = grossEdge - (buyPrice * buyFee/100) - (sellPrice * sellFee/100) - (gasUsd / positionSizeUsd)`

### FeeSchedule Interface

```typescript
interface FeeSchedule {
  platformId: PlatformId;
  makerFeePercent: number; // 0-100 scale
  takerFeePercent: number; // 0-100 scale
  description: string;
}
```

### Event Classes — MUST Avoid common/ → modules/ Import

Event classes do NOT exist yet. Create `src/common/events/detection.events.ts`.

**CRITICAL ARCHITECTURAL CONSTRAINT:** `common/` NEVER imports from `modules/`. The event classes must NOT import `EnrichedOpportunity` or `RawDislocation` from `modules/arbitrage-detection/types`.

**Solution: Use generic payload typing.** The event class accepts a plain `Record<string, unknown>` or a minimal interface defined in `common/types/`. The module-level code that *emits* the event passes the enriched opportunity, and consumers cast it to the module type. This keeps event classes in `common/events/` without violating the boundary.

```typescript
import { BaseEvent } from './base.event';
import Decimal from 'decimal.js';

/**
 * Emitted when an arbitrage opportunity meets minimum edge threshold.
 * Payload is an EnrichedOpportunity (defined in modules/arbitrage-detection/types),
 * typed as Record<string, unknown> here to avoid common/ → modules/ import.
 */
export class OpportunityIdentifiedEvent extends BaseEvent {
  constructor(
    public readonly opportunity: Record<string, unknown>,
    correlationId?: string,
  ) {
    super(correlationId);
  }
}

export class OpportunityFilteredEvent extends BaseEvent {
  constructor(
    public readonly pairEventDescription: string,
    public readonly netEdge: Decimal,
    public readonly threshold: Decimal,
    public readonly reason: string,
    correlationId?: string,
  ) {
    super(correlationId);
  }
}
```

**Future refinement (Epic 5+):** If multiple consumers emerge, consider defining a minimal `OpportunityPayload` interface in `common/types/` with just the fields consumers need (`netEdge`, `platformIds`, `contractIds`, `grossEdge`). This restores compile-time safety without the boundary violation. Not worth it now with zero consumers — revisit when execution or monitoring subscribes to this event.

When emitting from `EdgeCalculatorService` (which IS in `modules/`), pass the typed `EnrichedOpportunity` — TypeScript will accept it since it satisfies `Record<string, unknown>`. Downstream consumers in other modules cast the payload back:
```typescript
// In edge-calculator.service.ts (modules/ — can import EnrichedOpportunity):
this.eventEmitter.emit(EVENT_NAMES.OPPORTUNITY_IDENTIFIED, new OpportunityIdentifiedEvent(enrichedOpportunity));

// In a future consumer (e.g., monitoring, execution):
const opportunity = event.opportunity as EnrichedOpportunity;
```

### EnrichedOpportunity Type Definition

```typescript
import Decimal from 'decimal.js';
import { RawDislocation } from './raw-dislocation.type';
import { FeeSchedule } from '../../../common/types';

export interface FeeBreakdown {
  buyFeeCost: Decimal;     // buyPrice * (buyFee / 100)
  sellFeeCost: Decimal;    // sellPrice * (sellFee / 100)
  gasFraction: Decimal;    // gasEstimateUsd / positionSizeUsd
  totalCosts: Decimal;     // sum of above
  buyFeeSchedule: FeeSchedule;
  sellFeeSchedule: FeeSchedule;
}

export interface LiquidityDepth {
  buyBestAskSize: number;   // quantity at best ask on buy platform
  sellBestAskSize: number;  // quantity at best ask on sell platform
  buyBestBidSize: number;   // quantity at best bid on buy platform
  sellBestBidSize: number;  // quantity at best bid on sell platform
}

export interface EnrichedOpportunity {
  dislocation: RawDislocation;
  netEdge: Decimal;
  grossEdge: Decimal;
  feeBreakdown: FeeBreakdown;
  liquidityDepth: LiquidityDepth;
  recommendedPositionSize: null; // Placeholder for Epic 4
  enrichedAt: Date;
}
```

### EdgeCalculationResult Type Definition

```typescript
import { EnrichedOpportunity } from './enriched-opportunity.type';

export interface FilteredDislocation {
  pairEventDescription: string;
  netEdge: string;         // Decimal.toString() for logging
  threshold: string;       // Decimal.toString()
  reason: string;          // e.g., "below_threshold", "negative_edge"
}

export interface EdgeCalculationResult {
  opportunities: EnrichedOpportunity[];
  filtered: FilteredDislocation[];
  summary: {
    totalInput: number;
    totalFiltered: number;
    totalActionable: number;
    processingDurationMs: number;
  };
}
```

### DegradationProtocolService Threshold Multiplier — Precise Semantics

The `getEdgeThresholdMultiplier(platformId)` method logic (from actual code):
- If the **given platformId IS degraded** → returns `1.0` (not widened — this platform is the problem)
- If the given platformId is **NOT degraded** but **some other platform IS degraded** → returns `1.5` (widen threshold on healthy platforms per NFR-R2)
- If **no platforms are degraded** → returns `1.0` (normal threshold)

**Why "use either platform" is safe in this context:** Story 3.2's `DetectionService` already skips pairs where either platform is degraded. Therefore, by the time a `RawDislocation` reaches the edge calculator, **both platforms in the pair are guaranteed healthy**. If any other platform is in the degraded set, calling `getEdgeThresholdMultiplier()` for either platform in the pair returns the same `1.5`. If no platforms are degraded, both return `1.0`.

**Recommended call pattern:** Call for the buy platform — it's arbitrary but consistent:
```typescript
const multiplier = this.degradationService.getEdgeThresholdMultiplier(dislocation.buyPlatformId);
const effectiveThreshold = this.minEdgeThreshold.mul(multiplier);
```

### Configuration Pattern

Use `ConfigService.get<type>(key, defaultValue)` pattern (same as `ContractPairLoaderService`):

```typescript
constructor(
  private readonly configService: ConfigService,
  // ... other deps
) {}

private get minEdgeThreshold(): Decimal {
  return new FinancialDecimal(
    this.configService.get<number>('DETECTION_MIN_EDGE_THRESHOLD', 0.008),
  );
}

private get gasEstimateUsd(): Decimal {
  return new FinancialDecimal(
    this.configService.get<number>('DETECTION_GAS_ESTIMATE_USD', 0.30),
  );
}

private get positionSizeUsd(): Decimal {
  return new FinancialDecimal(
    this.configService.get<number>('DETECTION_POSITION_SIZE_USD', 300),
  );
}
```

### TradingEngineService Integration

After the existing detection step in `executeCycle()`, add:

```typescript
// STEP 2b: Edge Calculation & Opportunity Filtering (Story 3.3)
const edgeResult = await this.edgeCalculator.processDislocations(
  detectionResult.dislocations,
);
this.logger.log({
  message: `Edge calculation: ${edgeResult.summary.totalActionable} actionable opportunities`,
  correlationId: getCorrelationId(),
  data: {
    totalInput: edgeResult.summary.totalInput,
    filtered: edgeResult.summary.totalFiltered,
    actionable: edgeResult.summary.totalActionable,
    durationMs: edgeResult.summary.processingDurationMs,
  },
});
```

### What NOT to Do (Scope Guard)

- Do NOT implement actual position sizing — that's Epic 4 (`recommendedPositionSize: null`)
- Do NOT create REST API endpoints for opportunities (future story)
- Do NOT implement risk validation or execution — those are Epic 4/5
- Do NOT modify `DetectionService` — it returns `RawDislocation[]` as-is
- Do NOT create Prisma migrations — no new tables needed
- Do NOT implement dynamic gas estimation via viem — use static config (Epic 5)
- Do NOT create the `contract_matches` table — that's Story 3.4

### Existing Codebase Patterns to Follow

- **File naming:** kebab-case (`edge-calculator.service.ts`, `enriched-opportunity.type.ts`)
- **Event pattern:** See `platform.events.ts` for BaseEvent extension pattern
- **Event emission:** `this.eventEmitter.emit(EVENT_NAMES.OPPORTUNITY_IDENTIFIED, event)`
- **Module registration:** See `arbitrage-detection.module.ts` — add EdgeCalculatorService as provider + export
- **Logging:** Use NestJS `Logger` — `private readonly logger = new Logger(EdgeCalculatorService.name)`
- **Correlation ID:** `import { getCorrelationId } from '../../common/services/correlation-context'`
- **Error handling:** Per-dislocation try/catch (don't let one failed calculation kill the whole batch). If `getFeeSchedule()` throws or returns invalid data, skip that dislocation, log at `error` level with platform ID and pair description, and increment a `skippedErrors` counter in the result summary. Same treatment for any `FinancialMath` validation error (e.g., NaN inputs).

### Testing Strategy

- Mock `KalshiConnector.getFeeSchedule()` and `PolymarketConnector.getFeeSchedule()` to return test fee schedules
- Mock `DegradationProtocolService.getEdgeThresholdMultiplier()` to control threshold multiplier
- Mock `ConfigService.get()` for configurable thresholds
- Mock `EventEmitter2.emit()` to verify event emission
- Use `Test.createTestingModule()` from `@nestjs/testing`
- DO NOT mock `FinancialMath` — let it run for real to verify integration with actual formulas
- Reference Sprint 0's `edge-calculation-scenarios.csv` for realistic test data
- Use `FinancialDecimal` for all test price/edge values

### Dependencies — All Already Installed

| Package | Purpose | Installed In |
|---------|---------|-------------|
| `decimal.js` | Financial precision via FinancialDecimal | Sprint 0 |
| `@nestjs/event-emitter` | EventEmitter2 for event emission | Epic 1 |
| `@nestjs/config` | ConfigService for env vars | Epic 1 |

No new dependencies needed.

### Previous Story Intelligence (3.2 + Sprint 0)

- **349 tests passing** — regression gate baseline
- **DetectionService** returns `DetectionCycleResult` with `dislocations: RawDislocation[]`
- **RawDislocation** has: `pairConfig`, `buyPlatformId`, `sellPlatformId`, `buyPrice`, `sellPrice`, `grossEdge`, `buyOrderBook`, `sellOrderBook`, `detectedAt`
- **FinancialMath** uses `FinancialDecimal` (cloned Decimal with precision=20) — NOT global `Decimal`
- **Connector pattern:** Concrete class injection (`KalshiConnector`, `PolymarketConnector`)
- **getFeeSchedule()** returns `FeeSchedule` with `takerFeePercent` on 0-100 scale
- **DegradationProtocolService.getEdgeThresholdMultiplier()** returns 1.0 or 1.5
- **BaseEvent** constructor takes optional `correlationId`, falls back to async context
- **EVENT_NAMES** catalog already has `OPPORTUNITY_IDENTIFIED` and `OPPORTUNITY_FILTERED` string constants
- **Sprint 0 CSV** at `src/modules/arbitrage-detection/__tests__/edge-calculation-scenarios.csv` has 15+ hand-verified scenarios

### Git Intelligence

Recent engine commits follow pattern: `feat: <description>`. Story 3.3 should use:
- `feat: add edge calculator service with opportunity filtering and event emission`

### Project Structure Notes

New files to create:
```
src/common/events/detection.events.ts
src/modules/arbitrage-detection/edge-calculator.service.ts
src/modules/arbitrage-detection/edge-calculator.service.spec.ts
src/modules/arbitrage-detection/types/enriched-opportunity.type.ts
src/modules/arbitrage-detection/types/edge-calculation-result.type.ts
```

Modified files:
```
src/common/events/index.ts                       (export detection events)
src/modules/arbitrage-detection/types/index.ts   (export new types)
src/modules/arbitrage-detection/arbitrage-detection.module.ts (add EdgeCalculatorService)
src/core/trading-engine.service.ts               (add EdgeCalculatorService injection, Step 2b)
src/core/trading-engine.service.spec.ts          (add EdgeCalculatorService mock)
.env.development                                 (add DETECTION_* config vars)
.env.example                                     (add DETECTION_* config vars)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3 — acceptance criteria]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4 — downstream scope (what NOT to build)]
- [Source: _bmad-output/implementation-artifacts/epic-3-sprint-0.md#AC2 — FinancialMath utility and formulas]
- [Source: _bmad-output/implementation-artifacts/3-2-cross-platform-arbitrage-detection.md — DetectionService API, RawDislocation type]
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts — calculateNetEdge, isAboveThreshold]
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts — FeeSchedule interface]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts — OPPORTUNITY_IDENTIFIED, OPPORTUNITY_FILTERED]
- [Source: pm-arbitrage-engine/src/common/events/base.event.ts — BaseEvent pattern]
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.ts — getEdgeThresholdMultiplier()]
- [Source: pm-arbitrage-engine/src/core/trading-engine.service.ts — executeCycle Step 2]
- [Source: CLAUDE.md#Module Dependency Rules — detection module constraints]
- [Source: CLAUDE.md#Domain Rules — price normalization, edge calculation, 0.8% threshold]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None.

### Completion Notes List

- Created `OpportunityIdentifiedEvent` and `OpportunityFilteredEvent` in `common/events/detection.events.ts` using generic `Record<string, unknown>` payload to avoid `common/` → `modules/` import violation.
- Created `EnrichedOpportunity`, `FeeBreakdown`, `LiquidityDepth` types and `EdgeCalculationResult`, `FilteredDislocation` types.
- Implemented `EdgeCalculatorService` with per-dislocation try/catch for graceful error handling. Uses `FinancialMath.calculateNetEdge()` and `isAboveThreshold()` directly (no mocking in tests).
- Wired into `TradingEngineService.executeCycle()` as Step 2b after detection.
- `processDislocations()` is synchronous (no async needed) — all operations are in-memory.
- 17 new test cases covering: CSV scenarios (exact boundary, just below, just above), threshold multiplier, event emission, fee breakdown, liquidity depth, multiple dislocations, empty array, connector selection, configurable threshold/gas/position size, negative edge, error recovery.
- All 366 tests pass (349 existing + 17 new). Lint clean.

### Code Review Fixes (Claude Opus 4.6)

- **H1 Fixed:** `trading-engine.service.spec.ts` — Changed `mockResolvedValue` to `mockReturnValue` for synchronous `processDislocations()` mock. Previously caused silent error during test execution.
- **H2 Fixed:** `edge-calculator.service.ts` — Added `OnModuleInit` with `validateConfig()` to reject negative/NaN config values at startup per AC8.
- **M1 Fixed:** Added `skippedErrors` counter to `EdgeCalculationResult.summary` and `processDislocations()`. Summary now correctly accounts for `totalInput = totalFiltered + totalActionable + skippedErrors`.
- **M2 Fixed:** Removed `await` from all 17 test calls to synchronous `processDislocations()`, removed `async` from test callbacks, removed `eslint-disable @typescript-eslint/await-thenable`.
- Added 1 new test: validates negative config values rejected at startup.
- All 367 tests pass (349 existing + 18 new). Lint clean.

### File List

New files:
- `src/common/events/detection.events.ts`
- `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts`
- `src/modules/arbitrage-detection/types/edge-calculation-result.type.ts`
- `src/modules/arbitrage-detection/edge-calculator.service.ts`
- `src/modules/arbitrage-detection/edge-calculator.service.spec.ts`

Modified files:
- `src/common/events/index.ts` (added detection.events export)
- `src/modules/arbitrage-detection/types/index.ts` (added new type exports)
- `src/modules/arbitrage-detection/arbitrage-detection.module.ts` (added EdgeCalculatorService provider/export)
- `src/core/trading-engine.service.ts` (added EdgeCalculatorService injection + Step 2b call)
- `src/core/trading-engine.service.spec.ts` (added EdgeCalculatorService mock)
- `.env.development` (added DETECTION_* config vars)
- `.env.example` (added DETECTION_* config vars)
