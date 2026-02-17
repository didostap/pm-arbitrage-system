# Story 3.2: Cross-Platform Arbitrage Detection

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the system to automatically identify price dislocations across my curated contract pairs,
so that I can see which opportunities exist in real-time.

**FRs covered:** FR-AD-01 (Identify cross-platform arbitrage opportunities, full detection cycle within 1 second)

## Acceptance Criteria

### AC1: Detection Cycle Evaluates All Configured Pairs

**Given** normalized order books from both platforms are available (Epic 2)
**When** the detection service runs a cycle via `DetectionService.detectDislocations()`
**Then** all active contract pairs from `ContractPairLoaderService.getActivePairs()` are evaluated for price dislocations
**And** the full detection cycle completes within 1 second (FR-AD-01)
**And** raw dislocations are returned as `RawDislocation[]` for downstream edge calculation (Story 3.3)
**And** NO public event is emitted — the public `OpportunityIdentifiedEvent` is emitted by Story 3.3 after enrichment

### AC2: Skip Degraded/Offline Platforms

**Given** either platform's health is "degraded" or "offline" (via `DegradationProtocolService.isDegraded()`)
**When** the detection cycle runs
**Then** pairs involving that platform are skipped entirely
**And** skipped pairs are logged at debug level with: pair event description, platform ID, skip reason
**And** the detection result includes a count of skipped pairs

### AC3: Order Book Fetching Per Pair

**Given** an active contract pair with `polymarketContractId` and `kalshiContractId`
**When** the detection service evaluates it
**Then** it fetches the latest order book for each platform via `IPlatformConnector.getOrderBook(contractId)`
**And** if either order book fetch fails, that pair is skipped (not the whole cycle) with an error-level log
**And** if either order book has empty bids OR empty asks, that pair is skipped with a debug-level log ("no market depth")

### AC4: Raw Dislocation Identification

**Given** valid order books exist for both platforms in a pair
**When** the detection service compares prices
**Then** it identifies dislocations by comparing complementary prices:
- **Scenario A (Buy Polymarket, Sell Kalshi):** `polymarketBestAsk` vs `(1 - kalshiBestAsk)` — if Polymarket's ask is lower than the implied Kalshi price, there's a potential arbitrage
- **Scenario B (Buy Kalshi, Sell Polymarket):** `kalshiBestAsk` vs `(1 - polymarketBestAsk)` — the reverse direction

**And** a `RawDislocation` is produced for each direction where `grossEdge > 0` (using `FinancialMath.calculateGrossEdge()` from Sprint 0)
**And** each `RawDislocation` includes: contract pair config, buy platform ID, sell platform ID, buy price, sell price, gross edge, buy order book, sell order book, detection timestamp

### AC5: Detection Result Summary

**Given** a detection cycle completes
**When** results are produced
**Then** the return type `DetectionCycleResult` includes: raw dislocations array, pairs evaluated count, pairs skipped count, cycle duration in ms
**And** a summary log is emitted: `"Detection cycle complete"` with total pairs, evaluated, skipped, dislocations found, and duration

### AC6: ArbitrageDetectionModule Registration

**Given** the `ArbitrageDetectionModule` is created
**When** the engine starts
**Then** it is registered in `app.module.ts`
**And** it imports `ContractMatchingModule` (for `ContractPairLoaderService`) and `DataIngestionModule` (for `PlatformHealthService` / `DegradationProtocolService`)
**And** it imports `ConnectorModule` (for platform connectors to fetch order books)
**And** the module does NOT import from other `modules/` directories beyond the allowed dependencies

### AC7: Integration with TradingEngineService

**Given** the detection service is ready
**When** `TradingEngineService.executeCycle()` runs
**Then** Step 2 calls the detection service (currently commented out placeholder)
**And** results are logged for now — risk validation (Epic 4) and execution (Epic 5) will consume them later
**And** detection is skipped if trading is halted (`isHalted` flag)

### AC8: Existing Test Suite Regression

**Given** all Story 3.2 changes are complete
**When** `pnpm test` runs
**Then** all 330 existing tests continue to pass
**And** new tests for `DetectionService` add 15+ test cases
**And** `pnpm lint` passes with no errors

## Tasks / Subtasks

- [x] Task 1: Create ArbitrageDetectionModule (AC: #6)
  - [x] 1.1 Create `src/modules/arbitrage-detection/arbitrage-detection.module.ts`
  - [x] 1.2 Import `ContractMatchingModule`, `DataIngestionModule`, `ConnectorModule`
  - [x] 1.3 Register module in `src/app.module.ts`
  - [x] 1.4 Declare and export `DetectionService`

- [x] Task 2: Create RawDislocation and DetectionCycleResult Types (AC: #4, #5)
  - [x] 2.1 Create `src/modules/arbitrage-detection/types/raw-dislocation.type.ts`
  - [x] 2.2 Create `src/modules/arbitrage-detection/types/detection-cycle-result.type.ts`
  - [x] 2.3 Create `src/modules/arbitrage-detection/types/index.ts` barrel export

- [x] Task 3: Create DetectionService (AC: #1, #2, #3, #4, #5)
  - [x] 3.1 Create `src/modules/arbitrage-detection/detection.service.ts`
  - [x] 3.2 Inject: `ContractPairLoaderService`, `DegradationProtocolService`, `KalshiConnector`, `PolymarketConnector`
  - [x] 3.3 Implement `detectDislocations(): Promise<DetectionCycleResult>`
  - [x] 3.4 Iterate over `getActivePairs()`, skip pairs where either platform is degraded
  - [x] 3.5 Fetch order books via connectors' `getOrderBook()` — catch per-pair, skip on failure
  - [x] 3.6 Skip pairs with empty bids/asks (no market depth)
  - [x] 3.7 Calculate gross edge for both directions using `FinancialMath.calculateGrossEdge()`
  - [x] 3.8 Produce `RawDislocation` for each direction where `grossEdge > 0`
  - [x] 3.9 Track timing and return `DetectionCycleResult`
  - [x] 3.10 Log detection summary at `log` level

- [x] Task 4: Wire into TradingEngineService (AC: #7)
  - [x] 4.1 Add `DetectionService` injection to `TradingEngineService` constructor
  - [x] 4.2 Uncomment/implement Step 2 in `executeCycle()` — call `detectDislocations()`
  - [x] 4.3 Log detection results; do NOT emit events or call risk/execution (future epics)
  - [x] 4.4 Update `CoreModule` to import `ArbitrageDetectionModule`

- [x] Task 5: Write Tests (AC: #8)
  - [x] 5.1 Create `src/modules/arbitrage-detection/detection.service.spec.ts`
  - [x] 5.2 Test: evaluates all active pairs and returns results
  - [x] 5.3 Test: completes within 1 second with 30 pairs (performance gate)
  - [x] 5.4 Test: skips pairs when Kalshi is degraded
  - [x] 5.5 Test: skips pairs when Polymarket is degraded
  - [x] 5.6 Test: skips pair (not entire cycle) when order book fetch fails
  - [x] 5.7 Test: skips pair when bids or asks are empty
  - [x] 5.8 Test: identifies dislocation in Scenario A (buy Polymarket, sell Kalshi)
  - [x] 5.9 Test: identifies dislocation in Scenario B (buy Kalshi, sell Polymarket)
  - [x] 5.10 Test: produces dislocation for both directions when both have positive gross edge
  - [x] 5.11 Test: no dislocation when prices are identical (gross edge = 0)
  - [x] 5.12 Test: no dislocation when fees would clearly eliminate edge (negative gross edge)
  - [x] 5.13 Test: detection result includes correct counts (evaluated, skipped, dislocations)
  - [x] 5.14 Test: returns empty dislocations when no active pairs exist
  - [x] 5.15 Test: correctly uses FinancialMath.calculateGrossEdge for price comparison
  - [x] 5.16 Run full regression: `pnpm test` — all 330+ tests pass

- [x] Task 6: Lint & Final Check (AC: #8)
  - [x] 6.1 Run `pnpm lint` and fix any issues
  - [x] 6.2 Verify no import boundary violations

## Dev Notes

### Architecture Constraints

- `DetectionService` lives in `src/modules/arbitrage-detection/` — domain logic for opportunity identification
- Allowed imports per CLAUDE.md dependency rules:
  - `modules/arbitrage-detection/ → modules/contract-matching/` (for `ContractPairLoaderService`)
  - `modules/arbitrage-detection/` → `common/` (types, utils, events, errors)
  - `core/ → modules/*` (TradingEngine orchestrates detection via DI)
- The module needs `ConnectorModule` for `KalshiConnector` and `PolymarketConnector` to call `getOrderBook()`
- The module needs `DataIngestionModule` for `DegradationProtocolService` to check platform health

### Connector Access Pattern — CRITICAL

The `DataIngestionService` currently uses platform connectors directly (imports `KalshiConnector`, `PolymarketConnector`). The detection service should follow the **same pattern** — inject the concrete connector classes directly, not through `IPlatformConnector` interface.

**Why not the interface?** NestJS DI resolves by token. The connectors are registered as their concrete classes (`KalshiConnector`, `PolymarketConnector`) in `ConnectorModule`, not as `IPlatformConnector`. To inject via interface, you'd need a custom provider token pattern — that's a future refactor (Epic 11, plugin architecture). For now, inject the concrete classes.

```typescript
constructor(
  private readonly contractPairLoader: ContractPairLoaderService,
  private readonly degradationService: DegradationProtocolService,
  private readonly kalshiConnector: KalshiConnector,
  private readonly polymarketConnector: PolymarketConnector,
) {}
```

To get the right connector for a platform ID:
```typescript
private getConnector(platformId: PlatformId): KalshiConnector | PolymarketConnector {
  return platformId === PlatformId.KALSHI
    ? this.kalshiConnector
    : this.polymarketConnector;
}
```

### Order Book Fetching — Use Connectors, Not DataIngestionService

The detection service fetches order books **directly from connectors** via `getOrderBook(contractId)`, NOT from `DataIngestionService`. The DataIngestionService handles persistence and health tracking — detection only needs the live order book data.

### Price Comparison Logic — CRITICAL CORRECTNESS

**Prediction market arbitrage operates on complementary pricing:**
- Kalshi uses YES/NO with `YES_price + NO_price ≈ 1.00`
- Polymarket uses YES/NO tokens with the same property

**The gross edge formula from Sprint 0:** `|buyPrice - (1 - sellPrice)|`

This means:
- **Scenario A:** Buy YES on Polymarket (at ask), Sell YES on Kalshi (at ask of NO side) → `buyPrice = polymarketBestAsk`, `sellPrice = kalshiBestAsk`
- **Scenario B:** Buy YES on Kalshi (at ask), Sell YES on Polymarket (at ask of NO side) → `buyPrice = kalshiBestAsk`, `sellPrice = polymarketBestAsk`

**IMPORTANT:** `bestAsk` means `asks[0].price` — the lowest ask (best price to buy at). `bestBid` means `bids[0].price` — the highest bid. For detecting dislocations, we use **asks** (the price you'd actually pay to enter).

**Use `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` which computes `|buyPrice - (1 - sellPrice)|`.** Convert the `number` prices from order books to `Decimal` before calling FinancialMath.

### RawDislocation Type Definition

```typescript
import Decimal from 'decimal.js';
import { ContractPairConfig } from '../../modules/contract-matching/types';
import { NormalizedOrderBook } from '../../common/types';
import { PlatformId } from '../../common/types';

export interface RawDislocation {
  pairConfig: ContractPairConfig;
  buyPlatformId: PlatformId;
  sellPlatformId: PlatformId;
  buyPrice: Decimal;      // Best ask on buy platform
  sellPrice: Decimal;      // Best ask on sell platform (used in complementary calc)
  grossEdge: Decimal;      // From FinancialMath.calculateGrossEdge()
  buyOrderBook: NormalizedOrderBook;
  sellOrderBook: NormalizedOrderBook;
  detectedAt: Date;
}
```

### DetectionCycleResult Type Definition

```typescript
import { RawDislocation } from './raw-dislocation.type';

export interface DetectionCycleResult {
  dislocations: RawDislocation[];
  pairsEvaluated: number;
  pairsSkipped: number;
  cycleDurationMs: number;
}
```

### FinancialMath Import

`FinancialMath` is exported from `src/common/utils/index.ts`. It also exports `FinancialDecimal` (a cloned Decimal class with precision=20). Use `FinancialDecimal` for creating Decimal instances from order book prices:

```typescript
import { FinancialMath, FinancialDecimal } from '../../common/utils';

const buyPrice = new FinancialDecimal(buyOrderBook.asks[0].price);
const sellPrice = new FinancialDecimal(sellOrderBook.asks[0].price);
const grossEdge = FinancialMath.calculateGrossEdge(buyPrice, sellPrice);
```

### What NOT to Do (Scope Guard)

- Do NOT calculate net edge — that's Story 3.3 (`EdgeCalculatorService`)
- Do NOT emit `OpportunityIdentifiedEvent` or `OpportunityFilteredEvent` — that's Story 3.3
- Do NOT implement opportunity filtering by threshold — that's Story 3.3
- Do NOT create the `contract_matches` Prisma migration — that's Story 3.4
- Do NOT add fee schedule fetching — that's Story 3.3
- Do NOT modify `DataIngestionService` (it still uses placeholder tickers for its own polling; detection uses contract pair config separately)
- Do NOT create REST API endpoints for detection results (future story)

### Existing Codebase Patterns to Follow

- **File naming:** kebab-case (`detection.service.ts`, `raw-dislocation.type.ts`)
- **Module registration:** See `data-ingestion.module.ts` for pattern — imports, providers, exports
- **Module registration in app.module.ts:** See how `ContractMatchingModule` was added (Story 3.1)
- **Logging:** Use NestJS `Logger` — `private readonly logger = new Logger(DetectionService.name)`
- **Structured logs:** Include `message`, `module: 'arbitrage-detection'`, `correlationId`, `timestamp`
- **Correlation ID:** Import `getCorrelationId` from `../../common/services/correlation-context`
- **Error handling:** Per-pair try/catch (see how `DataIngestionService.ingestCurrentOrderBooks()` handles per-ticker failures)

### TradingEngineService Integration

The `TradingEngineService.executeCycle()` currently has this commented placeholder at line 72:
```typescript
// STEP 2: Arbitrage Detection (Epic 3)
// await this.detectionService.detectOpportunities();
```

Replace with:
```typescript
// STEP 2: Arbitrage Detection (Epic 3)
const detectionResult = await this.detectionService.detectDislocations();
this.logger.log({
  message: `Detection: ${detectionResult.dislocations.length} dislocations found`,
  correlationId: getCorrelationId(),
  data: {
    dislocations: detectionResult.dislocations.length,
    evaluated: detectionResult.pairsEvaluated,
    skipped: detectionResult.pairsSkipped,
    durationMs: detectionResult.cycleDurationMs,
  },
});
```

**Also update `CoreModule`** to import `ArbitrageDetectionModule` so `DetectionService` is available for injection.

### Testing Strategy

- Mock `ContractPairLoaderService.getActivePairs()` to return test pairs
- Mock `DegradationProtocolService.isDegraded()` to control skip behavior
- Mock `KalshiConnector.getOrderBook()` and `PolymarketConnector.getOrderBook()` to return test order books
- Use `Test.createTestingModule()` from `@nestjs/testing`
- For price comparison tests, use realistic prices (e.g., Polymarket YES at 0.55, Kalshi NO at 0.42 → Kalshi implied YES = 0.58, gross edge = |0.55 - (1-0.42)| = |0.55 - 0.58| = 0.03)
- Performance test: create 30 mock pairs, verify cycle completes under 1000ms
- DO NOT mock `FinancialMath` — let it run for real to verify integration

### Dependencies — All Already Installed

| Package | Purpose | Installed In |
|---------|---------|-------------|
| `decimal.js` | Financial precision via FinancialDecimal | Sprint 0 |
| `@nestjs/event-emitter` | EventEmitter2 (not used in this story, but module may import it) | Epic 1 |

No new dependencies needed.

### Project Structure Notes

New files to create:
```
src/modules/arbitrage-detection/arbitrage-detection.module.ts
src/modules/arbitrage-detection/detection.service.ts
src/modules/arbitrage-detection/detection.service.spec.ts
src/modules/arbitrage-detection/types/raw-dislocation.type.ts
src/modules/arbitrage-detection/types/detection-cycle-result.type.ts
src/modules/arbitrage-detection/types/index.ts
```

Modified files:
```
src/app.module.ts                    (add ArbitrageDetectionModule import)
src/core/core.module.ts              (import ArbitrageDetectionModule for DetectionService injection)
src/core/trading-engine.service.ts   (add DetectionService injection, implement Step 2)
```

Files to delete:
```
src/modules/arbitrage-detection/.gitkeep   (no longer needed — module has real files)
```

### Previous Story Intelligence (3.1 + Sprint 0)

- **330 tests passing** — regression gate baseline
- **ContractPairLoaderService** returns `ContractPairConfig[]` via `getActivePairs()` — each has `polymarketContractId`, `kalshiContractId`, `primaryLeg`
- **FinancialMath** uses `FinancialDecimal` (cloned Decimal with precision=20) — NOT global `Decimal`
- **`FinancialMath.calculateGrossEdge(buyPrice, sellPrice)`** returns `Decimal`, formula: `|buyPrice - (1 - sellPrice)|`
- **DegradationProtocolService** has `isDegraded(platformId)` and `getEdgeThresholdMultiplier(platformId)` (multiplier is for Story 3.3's filtering, not this story)
- **NormalizedOrderBook** has `bids: PriceLevel[]` and `asks: PriceLevel[]` where `PriceLevel = { price: number, quantity: number }`
- **Connector pattern:** Concrete class injection (`KalshiConnector`, `PolymarketConnector`), not via interface token
- **`ConnectorModule`** must be imported to get access to connector instances (see `DataIngestionModule` pattern)

### Git Intelligence

Recent engine commits follow pattern: `feat: <description>`. Story 3.2 should use:
- `feat: add cross-platform arbitrage detection service`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2 — acceptance criteria]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3 — downstream consumer context (what NOT to build)]
- [Source: _bmad-output/implementation-artifacts/epic-3-sprint-0.md#AC2 — FinancialMath utility and formulas]
- [Source: _bmad-output/implementation-artifacts/3-1-manual-contract-pair-configuration.md — ContractPairLoaderService API]
- [Source: _bmad-output/planning-artifacts/architecture.md#Module Organization — arbitrage-detection placement]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries — allowed imports]
- [Source: CLAUDE.md#Module Dependency Rules — detection module constraints]
- [Source: CLAUDE.md#Domain Rules — price normalization, edge calculation]
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts — FinancialMath, FinancialDecimal]
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.ts — isDegraded(), getEdgeThresholdMultiplier()]
- [Source: pm-arbitrage-engine/src/core/trading-engine.service.ts:72 — Step 2 placeholder]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None required.

### Completion Notes List

- Created `ArbitrageDetectionModule` with imports for `ContractMatchingModule`, `DataIngestionModule`, `ConnectorModule`
- Implemented `DetectionService.detectDislocations()` with full detection cycle: pair iteration, degradation checks, order book fetching, bidirectional gross edge calculation using `FinancialMath.calculateGrossEdge()`
- Direction validation: only produces `RawDislocation` when `buyPrice < impliedSellPrice` (true arbitrage)
- Wired into `TradingEngineService.executeCycle()` Step 2 with structured logging
- Updated `CoreModule` to import `ArbitrageDetectionModule`
- Updated existing `trading-engine.service.spec.ts` with `DetectionService` mock
- 16 new test cases covering all ACs (15 detection tests + 1 extra edge case)
- All 349 tests pass (330 existing + 15 new + 4 review fixes), `pnpm lint` clean
- No import boundary violations; follows existing connector injection pattern (concrete classes)

**Code Review Fixes Applied:**
- M1: Added clarifying JSDoc comment on `RawDislocation` re: `Decimal` vs `FinancialDecimal` type usage
- M2: Added test verifying `detectedAt` timestamp is a valid Date within cycle bounds
- M3: Added test verifying connectors are called with correct per-pair contract IDs
- L1: Added 2 tests for empty-asks and Polymarket-no-depth scenarios
- L2: Removed redundant undefined check after length guard (dead logic)

### File List

New files:
- `src/modules/arbitrage-detection/arbitrage-detection.module.ts`
- `src/modules/arbitrage-detection/detection.service.ts`
- `src/modules/arbitrage-detection/detection.service.spec.ts`
- `src/modules/arbitrage-detection/types/raw-dislocation.type.ts`
- `src/modules/arbitrage-detection/types/detection-cycle-result.type.ts`
- `src/modules/arbitrage-detection/types/index.ts`

Modified files:
- `src/app.module.ts` (added ArbitrageDetectionModule import)
- `src/core/core.module.ts` (added ArbitrageDetectionModule import)
- `src/core/trading-engine.service.ts` (added DetectionService injection, implemented Step 2)
- `src/core/trading-engine.service.spec.ts` (added DetectionService mock)

Deleted files:
- `src/modules/arbitrage-detection/.gitkeep`
