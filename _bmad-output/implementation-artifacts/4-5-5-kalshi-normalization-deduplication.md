# Story 4.5.5: Kalshi Order Book Normalization Deduplication

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the Kalshi cents-to-decimal and NO-to-YES inversion logic extracted to a single shared utility,
so that Epic 5 execution code builds on a single source of truth instead of 3 duplicated implementations.

## Acceptance Criteria

### AC1: Shared Utility Exists

**Given** Kalshi normalization logic is duplicated in `kalshi.connector.ts`, `kalshi-websocket.client.ts`, and `order-book-normalizer.service.ts`
**When** deduplication is complete
**Then** `normalizeKalshiLevels()` exists in `common/utils/kalshi-price.util.ts` containing the cents-to-decimal conversion and NO-to-YES price inversion
**And** the utility includes: YES bids mapping (`priceCents / 100`), NO-to-YES asks mapping (`1 - priceCents / 100`), and ascending ask sort

### AC2: All Three Consumers Refactored

**Given** the shared utility exists
**When** I inspect the three consumer files
**Then** all three import from the shared utility instead of implementing their own inline transformation
**And** `kalshi.connector.ts` `getOrderBook()` no longer contains inline cents-to-decimal math
**And** `kalshi-websocket.client.ts` `emitUpdate()` no longer contains inline cents-to-decimal math
**And** `order-book-normalizer.service.ts` `normalize()` no longer contains inline cents-to-decimal math

### AC3: All Tests Pass

**Given** the refactoring is complete
**When** `pnpm test` runs
**Then** all existing 498+ tests pass with zero failures
**And** `pnpm lint` reports zero errors

### AC4: New Unit Tests for Shared Utility

**Given** the shared utility is created
**When** unit tests are written
**Then** edge cases are covered: zero price (0 cents → 0.00), boundary values (0 cents → 0.00, 100 cents → 1.00), YES/NO sides, empty arrays, single-element arrays
**And** the tests verify the same output as the existing normalizer tests (consistency check)

## Tasks / Subtasks

- [x] Task 1: Create shared utility `common/utils/kalshi-price.util.ts` (AC: #1)
  - [x] 1.1 Create `normalizeKalshiLevels()` function accepting YES levels `[cents, qty][]` and NO levels `[cents, qty][]`, returning `{ bids: PriceLevel[], asks: PriceLevel[] }`
  - [x] 1.2 Include the three-step transformation: YES→bids (cents/100), NO→asks (1 - cents/100), sort asks ascending
  - [x] 1.3 Export `normalizeKalshiLevels` and `KalshiNormalizedLevels` from `common/utils/index.ts` barrel
- [x] Task 2: Write unit tests `common/utils/kalshi-price.util.spec.ts` (AC: #4)
  - [x] 2.1 Test zero price: `[0, 10]` → price 0.00
  - [x] 2.2 Test boundary 100 cents: `[100, 5]` → price 1.00
  - [x] 2.3 Test NO-to-YES inversion: NO `[35, 10]` → YES ask at 0.65
  - [x] 2.4 Test ask sorting: multiple NO levels produce ascending asks
  - [x] 2.5 Test empty arrays: `[], []` → `{ bids: [], asks: [] }`
  - [x] 2.6 Test single-element arrays
  - [x] 2.7 Test realistic spread: YES `[60, 100]` + NO `[35, 50]` → bid 0.60, ask 0.65
- [x] Task 3: Refactor `kalshi.connector.ts` `getOrderBook()` (AC: #2)
  - [x] 3.1 Replace inline transformation with `normalizeKalshiLevels()` call
  - [x] 3.2 Preserve the `?? 0` null guards — apply them before passing to the utility (the REST SDK response uses `true`/`false` keys and may have nullish elements)
  - [x] 3.3 Verify `kalshi.connector.spec.ts` tests still pass
- [x] Task 4: Refactor `kalshi-websocket.client.ts` `emitUpdate()` (AC: #2)
  - [x] 4.1 Replace inline transformation with `normalizeKalshiLevels()` call
  - [x] 4.2 Input is `state.yes` and `state.no` from `LocalOrderbookState` — both are `[number, number][]`
  - [x] 4.3 Verify `kalshi-websocket.client.spec.ts` tests still pass
- [x] Task 5: Refactor `order-book-normalizer.service.ts` `normalize()` (AC: #2)
  - [x] 5.1 Replace the transformation block (lines ~28-40) with `normalizeKalshiLevels()` call
  - [x] 5.2 KEEP the validation logic (price range check, crossed market warning) — those stay in the service, they are NOT part of the shared utility
  - [x] 5.3 KEEP the latency instrumentation — stays in the service
  - [x] 5.4 Verify `order-book-normalizer.service.spec.ts` tests still pass (28 tests)
- [x] Task 6: Final verification (AC: #3)
  - [x] 6.1 `pnpm test` — 506 tests pass (498 existing + 8 new)
  - [x] 6.2 `pnpm lint` — zero errors

## Dev Notes

### Architecture Decision: Utility Function, Not a Service

The shared utility is a **pure function** in `common/utils/`, not an injectable NestJS service. Rationale:
- The transformation is stateless arithmetic — no dependencies, no DI needed
- All three consumers operate in different module contexts (connectors, data-ingestion)
- A service would require cross-module DI wiring for no benefit
- Follows the existing pattern: `withRetry()`, `FinancialMath`, `syncAndMeasureDrift` are all pure utility functions

### What the Utility Does and Does NOT Do

**The utility ONLY does:**
1. Map YES levels: `[priceCents, qty][]` → `PriceLevel[]` where `price = priceCents / 100`
2. Map NO levels: `[priceCents, qty][]` → `PriceLevel[]` where `price = 1 - priceCents / 100`
3. Sort asks ascending by price

**The utility does NOT do:**
- Price range validation (0-1 check) — stays in `order-book-normalizer.service.ts`
- Crossed market detection — stays in `order-book-normalizer.service.ts`
- Latency instrumentation — stays in `order-book-normalizer.service.ts`
- Null guarding on input tuples — each consumer handles its own input quirks before calling
- Building the full `NormalizedOrderBook` object — each consumer sets `platformId`, `contractId`, `timestamp`, `sequenceNumber` themselves

### Input Format Differences Between Consumers

The three consumers receive raw data in slightly different shapes:

| Consumer | YES key | NO key | Null risk | Sequence |
|---|---|---|---|---|
| `kalshi.connector.ts` (REST) | `orderbook.true` | `orderbook.false` | Yes (SDK response) | None |
| `kalshi-websocket.client.ts` (WS) | `state.yes` | `state.no` | No (controlled internally) | `state.seq` |
| `order-book-normalizer.service.ts` | `kalshiBook.yes` | `kalshiBook.no` | No (typed input) | `kalshiBook.seq` |

The shared utility accepts `[number, number][]` for both YES and NO — each consumer maps its proprietary key names to these arrays before calling.

### Critical: Do NOT Move Validation Into the Utility

The `order-book-normalizer.service.ts` is the **only** path with price validation and crossed-market warnings. After this refactoring, validation responsibility stays exactly where it is. A follow-up concern (not this story): the REST connector path (`kalshi.connector.ts` `getOrderBook()`) and WS path (`kalshi-websocket.client.ts` `emitUpdate()`) both lack validation. If validation is needed on those paths, it should be added in a future story — not by bloating the shared utility.

### File Naming Convention

Following existing patterns in `common/utils/`:
- `with-retry.ts` — retry utility
- `rate-limiter.ts` — rate limiter
- `ntp-sync.util.ts` — NTP sync
- `financial-math.ts` — financial calculations
- `platform.ts` — platform enum mapper

New file: **`kalshi-price.util.ts`** — Kalshi price normalization (the `.util.ts` suffix follows the `ntp-sync.util.ts` pattern for stateless utility functions)

### Function Signature

```typescript
// common/utils/kalshi-price.util.ts
import { PriceLevel } from '../types/normalized-order-book.type.js';

export interface KalshiNormalizedLevels {
  bids: PriceLevel[];
  asks: PriceLevel[];
}

export function normalizeKalshiLevels(
  yesLevels: [number, number][],
  noLevels: [number, number][],
): KalshiNormalizedLevels {
  const bids: PriceLevel[] = yesLevels.map(([priceCents, qty]) => ({
    price: priceCents / 100,
    quantity: qty,
  }));

  const asks: PriceLevel[] = noLevels.map(([priceCents, qty]) => ({
    price: 1 - priceCents / 100,
    quantity: qty,
  }));

  asks.sort((a, b) => a.price - b.price);

  return { bids, asks };
}
```

### Refactoring Pattern for Each Consumer

**`kalshi.connector.ts` (before):**
```typescript
const yesBids = orderbook?.true ?? [];
const noBids = orderbook?.false ?? [];
const bids = yesBids.map(([priceCents, quantity]: number[]) => ({
  price: (priceCents ?? 0) / 100,
  quantity: quantity ?? 0,
}));
const asks = noBids.map(([priceCents, quantity]: number[]) => ({
  price: 1 - (priceCents ?? 0) / 100,
  quantity: quantity ?? 0,
}));
asks.sort((a, b) => a.price - b.price);
```

**`kalshi.connector.ts` (after):**
```typescript
import { normalizeKalshiLevels } from '../../common/utils/kalshi-price.util.js';

const yesBids: [number, number][] = (orderbook?.true ?? []).map(
  ([p, q]: number[]) => [p ?? 0, q ?? 0],
);
const noBids: [number, number][] = (orderbook?.false ?? []).map(
  ([p, q]: number[]) => [p ?? 0, q ?? 0],
);
const { bids, asks } = normalizeKalshiLevels(yesBids, noBids);
```

Note: null guards stay in the connector because the REST SDK response may contain nullish values — the utility assumes clean `[number, number][]` input.

**`kalshi-websocket.client.ts` (after):**
```typescript
import { normalizeKalshiLevels } from '../../common/utils/kalshi-price.util.js';

const { bids, asks } = normalizeKalshiLevels(state.yes, state.no);
```

**`order-book-normalizer.service.ts` (after):**
```typescript
import { normalizeKalshiLevels } from '../../common/utils/kalshi-price.util.js';

const { bids, asks } = normalizeKalshiLevels(kalshiBook.yes, kalshiBook.no);
// Validation and latency tracking continue below using bids/asks...
```

### Test Baseline

- Previous story (4.5.4) confirmed **498 tests passing**
- This story must end with 498+ tests (existing) + new utility tests
- Key test files to re-verify after refactoring:
  - `kalshi.connector.spec.ts` (8 tests)
  - `kalshi-websocket.client.spec.ts` (9 tests)
  - `order-book-normalizer.service.spec.ts` (28 tests)

### Project Structure Notes

- New file `src/common/utils/kalshi-price.util.ts` — aligns with `common/utils/` convention
- New file `src/common/utils/kalshi-price.util.spec.ts` — co-located test per project convention
- Export added to `src/common/utils/index.ts` — barrel file pattern
- No new modules, no new NestJS providers, no Prisma changes
- Import path uses `.js` extension per project's ESM convention (e.g., `from '../../common/utils/kalshi-price.util.js'`)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5.5] — Original acceptance criteria
- [Source: pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts:122-172] — REST path duplication
- [Source: pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.ts:285-314] — WebSocket path duplication
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/order-book-normalizer.service.ts:23-99] — Service path (with validation)
- [Source: pm-arbitrage-engine/src/common/utils/index.ts] — Existing utility barrel exports
- [Source: pm-arbitrage-engine/src/common/types/normalized-order-book.type.ts] — PriceLevel type definition
- [Source: _bmad-output/implementation-artifacts/4-5-4-technical-debt-consolidation.md] — Debt item #1 identifies this duplication
- [Source: pm-arbitrage-engine/technical-debt.md] — Technical debt registry entry

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None required.

### Completion Notes List

- Created `normalizeKalshiLevels()` pure utility function in `common/utils/kalshi-price.util.ts`
- Exported `normalizeKalshiLevels` from barrel `common/utils/index.ts` (removed unused `KalshiNormalizedLevels` type export after code review)
- 10 unit tests covering: zero price, boundary 100 cents, NO-to-YES inversion, ask sorting, empty arrays, single-element arrays, realistic spread, bid ordering preservation, floating-point precision
- Refactored `kalshi.connector.ts` `getOrderBook()` — preserved `?? 0` null guards before calling shared utility
- Refactored `kalshi-websocket.client.ts` `emitUpdate()` — direct pass-through of `state.yes`/`state.no`
- Refactored `order-book-normalizer.service.ts` `normalize()` — kept validation, crossed market detection, and latency instrumentation in the service
- Removed unused `PriceLevel` import from `kalshi-websocket.client.ts`
- All 508 tests pass (498 existing + 10 new), lint clean

### Code Review Fixes Applied

- **M1**: `order-book-normalizer.service.ts` — changed import to use barrel (`common/utils/index.js`) instead of direct file path
- **M2**: `order-book-normalizer.service.ts` — removed stale step-numbering comments (4., 5.) left over from pre-extraction inline code
- **M3**: `common/utils/index.ts` — removed dead `KalshiNormalizedLevels` type export (no consumers)
- **L1**: `kalshi-price.util.spec.ts` — added floating-point precision test (33 cents)
- **L2**: `kalshi-price.util.spec.ts` — added multi-bid ordering preservation test
- **L3**: `kalshi-price.util.ts` — added JSDoc to `normalizeKalshiLevels()`
- **L4**: `order-book-normalizer.service.ts` — fixed pre-existing missing `.js` extensions on type imports

### File List

- `src/common/utils/kalshi-price.util.ts` (new) — shared Kalshi cents-to-decimal normalization utility
- `src/common/utils/kalshi-price.util.spec.ts` (new) — 10 unit tests for shared utility
- `src/common/utils/index.ts` (modified) — added barrel exports
- `src/connectors/kalshi/kalshi.connector.ts` (modified) — refactored `getOrderBook()` to use shared utility
- `src/connectors/kalshi/kalshi-websocket.client.ts` (modified) — refactored `emitUpdate()` to use shared utility
- `src/modules/data-ingestion/order-book-normalizer.service.ts` (modified) — refactored `normalize()` to use shared utility
