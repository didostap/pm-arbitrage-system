# Story 10-9.3b: Backtest Depth Loading Memory Fix

Status: done

## Story

As an **operator**,
I want the backtest engine depth loading to operate within bounded memory,
so that production-scale backtests complete without V8 heap exhaustion.

## Problem Context

Story 10-9-3a introduced chunked pipeline loading (correct architectural approach), but `preloadDepthsForChunk` still loads ALL depth snapshots for ALL 5,640 contract IDs per 1-day chunk (~573K records). Each record is parsed into ~33 `decimal.js` `Decimal` objects (8 bid + 25 ask levels, 2 Decimals/level). Per-chunk memory:

```
573K records x ~33 levels x 2 Decimals x ~120 bytes/Decimal = ~5.7 GB
```

V8 old-space limit is ~4 GB. OOM occurs before simulation begins.

**Contributing factors:**
1. No contract filtering: `contractIds` derived from all 2,933 approved pairs regardless of chunk-active data
2. All 3 timeout checks in `backtest-engine.service.ts` are commented out (no circuit breaker)
3. `closedPositions` and `capitalSnapshots` grow unbounded across all chunks

**Evidence:** Fatal OOM stack trace `Builtins_GrowFastSmiOrObjectElements` during depth cache array growth. All recent backtest runs: FAILED or CONFIGURING.

## Acceptance Criteria

**Given** a backtest configuration with a date range spanning days to months of historical data
**When** the pipeline executes
**Then:**

1. Depth data is loaded only for contracts that have aligned price data in the current chunk (not all approved pairs)
2. Depth cache memory is bounded — peak depth cache size does not exceed configurable limit (default: 100K records per chunk)
3. If a chunk's depth data exceeds the bound, depths are loaded lazily per-contract via LRU cache (bounded size, e.g., 500 entries) instead of eager full pre-load
4. Depth level parsing uses native `number` for price/size instead of `decimal.js` `Decimal` (depth levels are used for VWAP fill estimation, not financial settlement)
5. Timeout checks are re-enabled at chunk boundaries and within the simulation loop
6. `closedPositions` array is bounded — positions are flushed to DB in batches at chunk boundaries to prevent unbounded growth
7. `capitalSnapshots` are downsampled to fixed intervals (e.g., 1 per hour) rather than 1 per open/close event
8. All existing backtest simulation tests continue to pass
9. A 7-day backtest with 2,933 approved pairs at 1-day chunk size completes without OOM (peak RSS < 1 GB)

## Implementation Priority Order

Start with highest-impact, lowest-risk changes. Contract filtering alone likely resolves OOM.

1. **Contract filtering (AC#1)** — highest impact, lowest risk
2. **Re-enable timeouts (AC#5)** — circuit breaker, trivial change
3. **Native numbers for depth (AC#4)** — 60% memory reduction per record
4. **Bounded depth cache with LRU fallback (AC#2-3)** — safety net
5. **closedPositions bounding (AC#6)** — secondary memory concern
6. **capitalSnapshots downsampling (AC#7)** — minor optimization

## Tasks / Subtasks

### [x] Task 1: Filter `contractIds` to chunk-active contracts (AC: #1)

**File:** `src/modules/backtesting/engine/backtest-engine.service.ts`

**Current code (lines 198-206):**
```typescript
const contractIds = [
  ...new Set([
    ...pairs.map((p) => p.kalshiContractId),
    ...pairs
      .filter((p) => p.polymarketClobTokenId)
      .map((p) => p.polymarketClobTokenId!),
  ]),
];
```

This derives IDs from ALL approved pairs before the chunk loop. Move contract ID extraction inside the chunk loop, after `loadAlignedPricesForChunk` returns `chunkTimeSteps`.

**Change:**
- Remove `contractIds` computation from lines 198-206
- Inside the chunk loop (after `chunkTimeSteps` is populated), extract distinct contract IDs from `chunkTimeSteps[].pairs[].kalshiContractId` and `polymarketContractId`
- Pass these filtered IDs to `preloadDepthsForChunk`
- Expected reduction: 5,640 -> <500 per chunk

### [x] Task 2: Add bounded depth cache with lazy LRU fallback (AC: #2, #3)

**File:** `src/modules/backtesting/engine/backtest-data-loader.service.ts`

**Current code:** `preloadDepthsForChunk` (lines 78-124) eagerly loads all depths for all passed contract IDs.

**Changes:**
- Add `MAX_DEPTH_RECORDS_PER_CHUNK` constant (default: 100,000)
- Before loading, run a lightweight `COUNT(*)` query with the same filters to check if the chunk exceeds the bound
- If count <= bound: proceed with current eager pre-load (no change)
- If count > bound: skip eager pre-load, return a lazy `DepthCache` wrapper backed by an LRU cache (bounded size, e.g., 500 entries)
- LRU cache: on miss, issue per-contract DB query (like `FillModelService.findNearestDepth` does today) and cache the result
- Export the LRU depth cache type so `findNearestDepthFromCache` can accept either eager or lazy cache
- Use `lru-cache` npm package (already in Node.js ecosystem) or implement a simple bounded Map with eviction

**Design choice — discriminated union approach (preferred over class polymorphism):**

Redefine the `DepthCache` type as a discriminated union. Keep `findNearestDepthFromCache` as a standalone pure function with a type guard:

```typescript
// Eager cache — current Map-based approach (for bounded chunks)
export interface EagerDepthCache {
  kind: 'eager';
  data: Map<string, NormalizedHistoricalDepth[]>;
}

// Lazy cache — LRU-backed, loads on demand (for large chunks)
export interface LazyDepthCache {
  kind: 'lazy';
  cache: LRUCache<string, NormalizedHistoricalDepth | null>;
  loader: (platform: string, contractId: string, timestamp: Date) => Promise<NormalizedHistoricalDepth | null>;
}

export type DepthCache = EagerDepthCache | LazyDepthCache;
```

Update `findNearestDepthFromCache` to dispatch on `depthCache.kind`:
- `'eager'` → existing binary search on `depthCache.data`
- `'lazy'` → call `depthCache.cache.get(key)`, on miss call `depthCache.loader(...)`, cache result

**Note:** Lazy path is async (DB call). `findNearestDepthFromCache` return type changes to `NormalizedHistoricalDepth | null | Promise<NormalizedHistoricalDepth | null>`. Alternatively, make the function always async. Callers (`FillModelService.modelFill`) already await — propagation is safe.

**LRU dependency:** Use `lru-cache` package. Check `pm-arbitrage-engine/package.json` — if not a direct dependency, run `pnpm add lru-cache`. Configure: `new LRUCache<string, NormalizedHistoricalDepth | null>({ max: 500 })`.

### [x] Task 3: Convert depth levels from `Decimal` to native `number` (AC: #4)

**Rationale:** Depth levels feed VWAP fill estimation, not financial settlement. `Decimal` precision is unnecessary. Each `Decimal` object is ~120 bytes vs 8 bytes for `number`.

**Files to modify:**

1. **`src/modules/backtesting/types/normalized-historical.types.ts` (lines 35-43):**
   - Change `bids: Array<{ price: Decimal; size: Decimal }>` to `bids: Array<{ price: number; size: number }>`
   - Same for `asks`

2. **`src/modules/backtesting/utils/depth-parsing.utils.ts` (lines 1-45):**
   - Rename `DepthLevel` interface: `price: number; size: number`
   - Change `parseJsonDepthLevels` to return `Array<{ price: number; size: number }>`
   - Replace `new Decimal(String(l.price))` with `Number(l.price)` (line 30)
   - Replace `new Decimal(String(l.size))` with `Number(l.size)` (line 31)
   - Update `isNumericValue` to use `Number()` + `Number.isFinite()` instead of Decimal construction

3. **`src/modules/backtesting/engine/fill-model.service.ts` (lines 21-40):**
   - `adaptDepthToOrderBook`: currently calls `l.price.toNumber()` / `l.size.toNumber()` — change to direct `l.price` / `l.size` (already numbers)
   - `findNearestDepth` (lines 42-77): the inline `parseLevel` function (line 63-66) still creates `Decimal` objects — change to `Number(String(l.price))` / `Number(String(l.size))`
   - Remove unused `Decimal` import if no longer needed

4. **`src/modules/backtesting/engine/backtest-data-loader.service.ts` (lines 164-172):**
   - `parseJsonDepthLevels` already handles the conversion — just verify the import and type propagation

### [x] Task 4: Re-enable timeout checks (AC: #5)

**File:** `src/modules/backtesting/engine/backtest-engine.service.ts`

Uncomment all 3 timeout blocks:

1. **Lines 307-318** — Empty chunk timeout (in chunk loop, after emitting chunk progress for empty chunks)
2. **Lines 418-426** — End-of-chunk timeout (cumulative check after simulation completes for a chunk)
3. **Lines 583-599** — Simulation loop timeout (per-step check inside `runSimulationLoop`, with headless throw vs main `failRun`)

All 3 blocks are functionally correct as-is. Just uncomment. They use `config.timeoutSeconds` from `IBacktestConfig`.

### [x] Task 5: Bound `closedPositions` — flush to DB at chunk boundaries (AC: #6)

**File:** `src/modules/backtesting/engine/backtest-portfolio.service.ts`

**Current behavior:** `closedPositions` array (line 75) grows monotonically — every closed position is pushed (line 171) and only cleared on `reset()` or `destroyRun()`. For long backtests with thousands of positions, this array grows unbounded.

**Changes:**
- Add a `flushClosedPositions(runId: string): SimulatedPosition[]` method that:
  1. Returns the current `closedPositions` array
  2. Resets it to `[]`
  3. Does NOT reset aggregate metrics (those stay)
- Call `flushClosedPositions` at the end of each chunk iteration in `backtest-engine.service.ts`
- Write flushed positions to `backtestPosition` table in batches (using `prisma.backtestPosition.createMany`)
- Update `persistResults` (line 829-876 in engine service) to NOT re-write positions that were already flushed — only write remaining unflushed positions
- Update `getAggregateMetrics` to compute from running accumulators instead of re-iterating `closedPositions` array (currently iterates full array at lines 239-258). Add running counters: `winCount`, `lossCount`, `grossWin`, `grossLoss`, `totalHoldingHours` updated in `closePosition()`.

**File:** `src/modules/backtesting/engine/backtest-engine.service.ts`
- After simulation loop per chunk, call `flushClosedPositions` and batch-write to DB

### [x] Task 6: Downsample `capitalSnapshots` to fixed intervals (AC: #7)

**File:** `src/modules/backtesting/engine/backtest-portfolio.service.ts`

**Current behavior:** A snapshot is pushed on every `openPosition` (line ~100-103) and every `closePosition` (line 173-176). High-frequency trading creates many snapshots.

**Changes:**
- Add `CAPITAL_SNAPSHOT_INTERVAL_MS = 3_600_000` (1 hour) constant
- In `openPosition` and `closePosition`, only push a new snapshot if:
  - `capitalSnapshots` is empty, OR
  - The time delta from the last snapshot exceeds `CAPITAL_SNAPSHOT_INTERVAL_MS`
- Always push a final snapshot at pipeline end (before `calculateCapitalUtilization` is called) with the current deployed capital and last known timestamp
- `calculateCapitalUtilization` (lines 358-381) works correctly with fewer snapshots since it's time-weighted

### [x] Task 7: Update existing depth-parsing tests for number type (AC: #4)

**File:** `src/modules/backtesting/utils/depth-parsing.utils.spec.ts`

Existing tests for `parseJsonDepthLevels` assert `Decimal` output types. Update all assertions to expect `number` values. Verify edge cases:
- Valid numeric strings: `"0.45"` -> `0.45`
- Already-numeric input: `0.45` -> `0.45`
- Invalid values (`"abc"`, `NaN`, empty string) -> filtered out
- Boundary values: `"0.00"`, `"1.00"`

Also update any tests in `fill-model.service.spec.ts` that construct `NormalizedHistoricalDepth` fixtures with `Decimal` bid/ask levels — change to plain `number`.

### [x] Task 8: Unit test — contract filtering (AC: #1)

Test that after `loadAlignedPricesForChunk`, only the contract IDs present in `chunkTimeSteps` are passed to `preloadDepthsForChunk`. Mock `loadAlignedPricesForChunk` to return steps with a small subset of contracts. Verify `preloadDepthsForChunk` receives only those IDs.

### [x] Task 9: Unit test — depth cache LRU fallback (AC: #2, #3)

Test that when the count query returns > `MAX_DEPTH_RECORDS_PER_CHUNK`:
- Eager pre-load is NOT called
- Lazy LRU cache is used instead
- LRU eviction works (insert more than capacity, verify oldest evicted)
- `findNearestDepthFromCache` works correctly with the lazy cache

### [x] Task 10: Integration test — 7-day backtest memory bounds (AC: #9)

Test with mocked Prisma returning realistic data volumes. Verify:
- Pipeline completes without OOM
- Peak RSS < 1 GB (use `process.memoryUsage().rss` snapshots)
- All chunk progress events emitted
- Timeout enforcement works

**Note:** This is a heavyweight test. Use realistic but synthetic data (e.g., 100 pairs, 7 chunks, ~1K depth records per chunk). The goal is proving the bounding mechanisms work, not replicating exact production volumes.

### [x] Task 11: Unit test — timeout halts pipeline (AC: #5)

Test each of the 3 timeout paths:
1. Empty chunk timeout — configure very short timeout, verify `failRun` called
2. End-of-chunk timeout — similar, verify `failRun` called after chunk completes
3. Simulation loop timeout — verify headless throws `SystemHealthError`, main calls `failRun`

## Dev Notes

### Files to Modify (all within `src/modules/backtesting/`)

| File | Changes |
|------|---------|
| `engine/backtest-engine.service.ts` | Contract filtering in chunk loop, uncomment 3 timeout blocks, chunk-boundary position flush |
| `engine/backtest-data-loader.service.ts` | Bounded depth cache, lazy LRU fallback, count-check before loading |
| `engine/backtest-portfolio.service.ts` | `flushClosedPositions()`, running aggregate accumulators, downsample `capitalSnapshots` |
| `engine/fill-model.service.ts` | Update `adaptDepthToOrderBook` for native number depth, update `findNearestDepth` parseLevel |
| `types/normalized-historical.types.ts` | `NormalizedHistoricalDepth` bid/ask: `Decimal` -> `number` |
| `utils/depth-parsing.utils.ts` | `DepthLevel` + `parseJsonDepthLevels`: `Decimal` -> `number` |

### No Cross-Module Changes

All changes are scoped to `modules/backtesting/`. No changes to:
- `common/` interfaces or types
- `connectors/`
- `persistence/`
- Other modules
- Prisma schema (no migrations)
- Dashboard (no frontend changes)

### Type Change Propagation (AC#4)

The `NormalizedHistoricalDepth` type change (`Decimal` -> `number` for bid/ask levels) propagates through:
1. `parseJsonDepthLevels` (produces the values)
2. `preloadDepthsForChunk` (stores in cache)
3. `findNearestDepthFromCache` (reads from cache — no change needed, just type propagation)
4. `findNearestDepth` in `FillModelService` (DB fallback — update inline parseLevel)
5. `adaptDepthToOrderBook` in `FillModelService` (consumes values — simplify `.toNumber()` calls)

The `NormalizedOrderBook` type in `common/types/` already uses `number` for price/quantity. No change needed there.

### Financial Math Safety

Depth levels (`price`/`size` in bid/ask arrays) are used exclusively for VWAP fill estimation in backtesting. They feed `calculateVwapWithFillInfo` which receives a `NormalizedOrderBook` already using `number`. The `Decimal` -> `number` conversion currently happens in `adaptDepthToOrderBook` via `.toNumber()`. This change simply moves that conversion earlier (at parse time), eliminating ~120 bytes/Decimal overhead.

**Not affected:** All other financial math (P&L, position sizing, edge calculation, fees) remains `decimal.js` `Decimal`.

### Previous Story (10-9-3a) Learnings

- `$queryRaw` with large `IN` arrays crashes the Prisma napi bridge — batching with `DEPTH_BATCH_SIZE = 500` is already in place (keep it)
- Walk-forward headless portfolios use `${runId}-wf-train` / `${runId}-wf-test` suffixes — the `flushClosedPositions` mechanism must handle these separately
- Chunk boundary deduplication (`lt` vs `lte`) was a previous bug — `endInclusive` flag already handles this correctly
- `EventEmitter2` dep was removed from `BacktestDataLoaderService` in the code review — keep it out
- `isHeadless` detection checks both `startsWith('headless-')` AND `endsWith('-wf-train')`/`-wf-test` — timeout handling differs for headless (throw) vs main (failRun)

### Existing Test Patterns

- Tests use Vitest with `vi.fn()` / `vi.spyOn()`
- Prisma is mocked via `{ provide: PrismaService, useValue: mockPrisma }` in test modules
- EventEmitter2 mocked with `vi.fn()` for `.emit()`
- `expect.objectContaining()` for event payload verification (CLAUDE.md requirement)
- Existing spec files: `backtest-engine.service.spec.ts`, `backtest-data-loader.service.spec.ts`, `backtest-portfolio.service.spec.ts`, `fill-model.service.spec.ts`

### Event Wiring

No new `@OnEvent` handlers introduced. No new events. Existing `backtest.pipeline.chunk.completed` event is unchanged.

### Collection Cleanup Strategy

| Collection | Current Cleanup | New Cleanup |
|------------|----------------|-------------|
| Depth cache (`Map`) | Goes out of scope per chunk → GC | Same (+ LRU eviction for lazy mode) |
| `closedPositions` (array) | `destroyRun()` / `reset()` | Flushed to DB at chunk boundaries |
| `capitalSnapshots` (array) | `destroyRun()` / `reset()` | Downsampled to 1/hour |
| `runs` (`Map`) | `.delete(runId)` on `destroyRun` | No change |

### Project Structure Notes

- All changes within `pm-arbitrage-engine/src/modules/backtesting/engine/` and sibling `types/` + `utils/`
- No new modules or providers required
- May add `lru-cache` as a dependency (check `package.json` first — if not present, `pnpm add lru-cache`)
- All tests co-located with source (same directory)

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-02-backtest-depth-oom.md] — Root cause analysis, memory calculations, implementation priority
- [Source: _bmad-output/implementation-artifacts/10-9-3a-backtest-pipeline-scalable-data-loading.md] — Previous story with pipeline flow, depth cache design, walk-forward integration
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 10.9] — Epic context, story definitions, scope boundaries
- [Source: CLAUDE.md] — Architecture constraints, testing standards, TDD workflow, financial math rules

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- Baseline: 3569 pass, 2 pre-existing e2e failures, 2 pre-existing timeout failures (commented-out blocks)
- Final: 3584 pass (+15 new tests), 2 pre-existing e2e failures only. All timeout tests now pass.

### Completion Notes List
- **Task 1 (AC#1):** Removed pre-loop `contractIds` computation. Added `chunkContractIds` extraction inside chunk loop from `chunkTimeSteps[].pairs[]`. Reduces depth queries from 5640 IDs to ~500 per chunk.
- **Task 2 (AC#2,3):** Refactored `DepthCache` from plain `Map` to discriminated union (`EagerDepthCache | LazyDepthCache`). Added COUNT(*) query before loading. If count > 100K (configurable), returns `LazyDepthCache` backed by `lru-cache` (500 entries). `findNearestDepthFromCache` now async, dispatches on `depthCache.kind`. Added `lru-cache@11.2.7` dependency.
- **Task 3 (AC#4):** Changed `NormalizedHistoricalDepth.bids/asks` from `Decimal` to `number`. Updated `depth-parsing.utils.ts` to use `Number()` instead of `new Decimal()`. Updated `fill-model.service.ts` `adaptDepthToOrderBook` (removed `.toNumber()`) and `findNearestDepth` (changed `parseLevel`). ~93% memory reduction per depth record (120 bytes/Decimal → 8 bytes/number).
- **Task 4 (AC#5):** Uncommented 3 timeout blocks (empty chunk, end-of-chunk, simulation loop). Fixed `_startTime` → `startTime` parameter name. Uncommented `SystemHealthError` import.
- **Task 5 (AC#6):** Added `flushClosedPositions(runId)` to portfolio service. Added `RunningAccumulators` (winCount, lossCount, grossWin, grossLoss, totalHoldingHours, dailyPnl) updated on every `closePosition()`, surviving flush. Refactored `getAggregateMetrics` to use accumulators instead of iterating closedPositions. Added `batchWritePositions` helper in engine service, called at chunk boundaries. Updated `persistResults` to only write remaining unflushed positions.
- **Task 6 (AC#7):** Added `CAPITAL_SNAPSHOT_INTERVAL_MS = 3_600_000` (1 hour). Added `maybeAddSnapshot` helper that skips if delta < 1 hour. Applied to both `openPosition` and `closePosition`.
- **Tasks 7-11:** All test tasks completed. 15 new tests covering contract filtering, LRU fallback, timeout paths, memory bounds, and capitalSnapshot downsampling.

### Change Log
- 2026-04-02: Implemented all 11 tasks for OOM fix. 3584 tests pass. Story ready for review.

### File List
- `src/modules/backtesting/engine/backtest-engine.service.ts` — contract filtering in chunk loop, uncommented 3 timeout blocks, chunk-boundary position flush, batchWritePositions helper
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts` — 5 new tests (AC#1 filtering, empty chunk timeout, 7-day memory bounds x2, contract ID reduction)
- `src/modules/backtesting/engine/backtest-data-loader.service.ts` — DepthCache discriminated union (eager/lazy), COUNT(*) check, LRU fallback, async findNearestDepthFromCache
- `src/modules/backtesting/engine/backtest-data-loader.service.spec.ts` — 4 new tests (eager/lazy selection, empty IDs), updated existing tests for new DepthCache/number types
- `src/modules/backtesting/engine/backtest-portfolio.service.ts` — RunningAccumulators, flushClosedPositions, maybeAddSnapshot downsampling, calculateSharpeRatioFromAccumulators
- `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` — 5 new tests (flush x3, downsampling x2)
- `src/modules/backtesting/engine/fill-model.service.ts` — adaptDepthToOrderBook simplified (direct number), findNearestDepth parseLevel uses Number(), await findNearestDepthFromCache
- `src/modules/backtesting/engine/fill-model.service.spec.ts` — Updated fixtures from Decimal to number for depth levels, EagerDepthCache wrapper
- `src/modules/backtesting/types/normalized-historical.types.ts` — NormalizedHistoricalDepth bids/asks: Decimal → number
- `src/modules/backtesting/utils/depth-parsing.utils.ts` — DepthLevel: Decimal → number, parseJsonDepthLevels uses Number(), isNumericValue uses Number.isFinite()
- `package.json` — Added lru-cache@11.2.7 dependency
