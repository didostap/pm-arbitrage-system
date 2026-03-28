# Sprint Change Proposal: Backtest Depth Loading Memory Fix

**Date:** 2026-04-02
**Triggered by:** Post-implementation OOM in Story 10-9-3a (Backtest Pipeline Scalable Data Loading)
**Scope classification:** Minor — Direct implementation by dev team
**Status:** Approved

---

## 1. Issue Summary

Story 10-9-3a (completed 2026-04-01) introduced chunked pipeline loading — the correct architectural approach. However, the depth pre-loading step (`preloadDepthsForChunk`) still causes V8 heap exhaustion on production-scale data. All recent backtest runs fail with `FATAL ERROR: Ineffective mark-compacts near heap limit`.

**Root cause:** A single 1-day chunk loads ~573K depth snapshot records for all 5,640 contract IDs (all approved pairs). Each record is parsed into ~33 `decimal.js` `Decimal` objects (8 bid levels + 25 ask levels, 2 Decimals per level). Total per chunk:

```
573K records x ~33 levels x 2 Decimals x ~120 bytes/Decimal = ~5.7 GB
```

Node.js V8 default old-space limit is ~4 GB. The depth cache exceeds the heap limit before simulation begins.

**Contributing factors:**
1. **No contract filtering:** `contractIds` derived from all 2,933 approved pairs regardless of chunk-active data. Most contracts have no aligned prices in any given chunk.
2. **Timeout disabled:** All 3 timeout checks in `backtest-engine.service.ts` are commented out — no circuit breaker for runaway memory consumption.
3. **Unbounded collections:** `closedPositions` and `capitalSnapshots` arrays grow monotonically across all chunks with no cap or flush.

**Evidence:**
- Fatal OOM stack trace: `Builtins_GrowFastSmiOrObjectElements` during depth cache array growth
- Database queries: 573K depth snapshots/day, 5,640 unique contract IDs, avg 8 bid + 25 ask levels per record
- All recent backtest runs: FAILED or CONFIGURING (never reaches SIMULATING)

---

## 2. Impact Analysis

### Epic Impact

- **Epic 10.9** (Backtesting & System Calibration): Remains in-progress. Story 10-9-3a is functionally broken at production scale. New Story **10-9-3b** added as P0 hotfix. Epic cannot close until 10-9-3b is done.

### Story Impact

- **10-9-3a** (done): Scope boundary note added — chunked architecture is correct; depth loading density was underestimated. Fix deferred to 10-9-3b.
- **10-9-3b** (new, backlog): Backtest Depth Loading Memory Fix. 10 tasks, P0 priority. Addresses all 4 root causes.
- **10-9-4** (done): Calibration reports depend on successful backtest runs. Blocked at production scale until 10-9-3b ships.

### Artifact Conflicts

- **PRD:** No conflict. MVP unaffected.
- **Architecture:** No changes needed. All changes within `modules/backtesting/engine/`. Module boundaries preserved.
- **UX:** No changes needed. Dashboard backtest page is unaffected.

### Technical Impact

- 4 files modified, all within `modules/backtesting/engine/`:
  - `backtest-engine.service.ts` — contract filtering, re-enable timeouts
  - `backtest-data-loader.service.ts` — bounded depth loading, lazy LRU fallback
  - `backtest-portfolio.service.ts` — bound closedPositions, downsample capitalSnapshots
  - `fill-model.service.ts` — adapt to native number depth levels
- Type change: `NormalizedHistoricalDepth` bid/ask levels change from `Decimal` to `number`
- All existing simulation logic preserved unchanged
- No schema migrations required
- No cross-module dependency changes

---

## 3. Recommended Approach

**Selected path:** Direct Adjustment — add Story 10-9-3b to Epic 10.9.

**Rationale:**
- Fix is surgically scoped to depth loading within 4 files in the same module
- Root causes are well-understood with precise memory calculations
- Contract filtering alone may reduce depth load by 80-90% (most pairs inactive per chunk)
- Native `number` for depth levels cuts per-record memory by ~60%
- Combined effect should bring per-chunk depth cache well under 1 GB

**Alternatives considered:**
- **Rollback (Option 2):** Not viable. Rolling back 10-9-3a would revert to single-query full materialization — catastrophically worse.
- **MVP Review (Option 3):** Not needed. This is a bug fix, not a scope question.

**Effort estimate:** Low-Medium
**Risk level:** Low
**Timeline impact:** Adds one story to Epic 10.9 completion.

---

## 4. Detailed Change Proposals

### 4.1 New Story: 10-9-3b (Backtest Depth Loading Memory Fix)

**As an** operator,
**I want** the backtest engine depth loading to operate within bounded memory,
**So that** production-scale backtests complete without V8 heap exhaustion.

**Problem Context:**
Story 10-9-3a introduced chunked pipeline loading but `preloadDepthsForChunk` still loads ALL depth snapshots for ALL 5,640 contract IDs per 1-day chunk (~573K records -> ~37.8M `Decimal` objects -> ~5.7 GB). Additionally, timeout checks were commented out during development and never re-enabled.

**Acceptance Criteria:**

**Given** a backtest configuration with a date range spanning days to months of historical data
**When** the pipeline executes
**Then:**
1. Depth data is loaded only for contracts that have aligned price data in the current chunk (not all approved pairs)
2. Depth cache memory is bounded — peak depth cache size does not exceed configurable limit (default: 100K records per chunk)
3. If a chunk's depth data exceeds the bound, depths are loaded lazily per-contract via LRU cache (bounded size, e.g., 500 entries) instead of eager full pre-load
4. Depth level parsing uses native `number` for price/size instead of `decimal.js` `Decimal` (depth levels are used for VWAP fill estimation, not financial settlement)
5. Timeout checks are re-enabled at chunk boundaries and within the simulation loop
6. `closedPositions` array is bounded — positions are flushed to a chunked buffer or aggregate metrics accumulated to prevent unbounded growth
7. `capitalSnapshots` are downsampled to fixed intervals (e.g., 1 per hour) rather than 1 per open/close event
8. All existing backtest simulation tests continue to pass
9. A 7-day backtest with 2,933 approved pairs at 1-day chunk size completes without OOM (peak RSS < 1 GB)

**Technical Notes:**
- **Contract filtering (AC#1):** After `loadAlignedPricesForChunk`, extract distinct `kalshiContractId` and `polymarketContractId` from `chunkTimeSteps`. Pass only those IDs to `preloadDepthsForChunk`. Expected reduction: 5,640 -> <500 per chunk.
- **Bounded depth cache (AC#2-3):** Add `maxDepthRecordsPerChunk` constant. If query count exceeds threshold, fall back to lazy per-contract loading with LRU cache.
- **Native numbers for depth (AC#4):** Replace `Decimal` in `NormalizedHistoricalDepth.bids[].price`/`.size` and `.asks[].price`/`.size` with `number`. Update `parseJsonDepthLevels`, `adaptDepthToOrderBook`, `findNearestDepthFromCache`. Memory reduction: ~60% per depth record (~120 bytes/Decimal -> 8 bytes/number).
- **Re-enable timeouts (AC#5):** Uncomment 3 timeout blocks in `backtest-engine.service.ts`. Use `timeoutSeconds` from config.
- **closedPositions bounding (AC#6):** Accumulate aggregate metrics in-memory. Write individual positions to DB in batches at chunk boundaries. `persistResults` reads from DB.
- **capitalSnapshots downsampling (AC#7):** Fixed-interval sample (1 per hour) instead of every open/close event.

**Dependencies:** Story 10-9-3a (already done)
**Blocked by:** None
**Blocks:** Production-scale calibration runs, Epic 10.9 closure

**Tasks:**
1. Filter `contractIds` in `executePipeline` to only contracts present in `chunkTimeSteps` after loading aligned prices
2. Add depth record count check and implement fallback lazy loading with LRU cache in `BacktestDataLoaderService`
3. Convert `NormalizedHistoricalDepth` bid/ask levels from `Decimal` to native `number`; update `parseJsonDepthLevels`, `adaptDepthToOrderBook`, `findNearestDepthFromCache`
4. Uncomment and verify all 3 timeout check blocks in `backtest-engine.service.ts`
5. Bound `closedPositions` — flush to DB at chunk boundaries or switch to streaming aggregate metrics
6. Downsample `capitalSnapshots` to fixed intervals
7. Unit test: contract filtering reduces depth loading to chunk-active contracts only
8. Unit test: depth cache fallback to lazy LRU when record count exceeds threshold
9. Integration test: 7-day backtest with full pair set completes within memory bounds (peak RSS < 1 GB)
10. Unit test: timeout correctly halts pipeline when exceeded

### 4.2 Story 10-9-3a Scope Boundary Note

**OLD:**
```
10-9-3a-backtest-pipeline-scalable-data-loading: done # P0. Completed 2026-04-01. Refactor executePipeline data loading...
```

**NEW:**
```
10-9-3a-backtest-pipeline-scalable-data-loading: done # P0. Completed 2026-04-01. ... NOTE: Chunked architecture correct; depth data density per chunk underestimated (573K records/day -> 5.7GB). Depth cache memory fix deferred to 10-9-3b.
```

**Rationale:** Documents the known limitation and links to the follow-up story.

---

## 5. Implementation Handoff

**Change scope:** Minor — Direct implementation by dev team.

**Handoff:**

- **Dev team:** Implement Story 10-9-3b following TDD workflow. All changes scoped to `modules/backtesting/engine/` (4 files). Contract filtering (task 1) is the highest-impact, lowest-risk change — start there.
- **SM (Bob):** Sprint-status.yaml updated. Monitor for scope creep beyond 10 tasks.

**Success criteria:**
1. 7-day backtest with 2,933 approved pairs completes without OOM
2. Peak RSS stays under 1 GB
3. All existing tests continue to pass
4. Timeouts correctly halt runaway runs
5. No cross-module changes required

**Priority order for implementation:**
1. Contract filtering (AC#1) — highest impact, lowest risk, likely resolves OOM alone
2. Re-enable timeouts (AC#5) — circuit breaker, trivial change
3. Native numbers for depth (AC#4) — 60% memory reduction per record
4. Bounded depth cache with LRU fallback (AC#2-3) — safety net
5. closedPositions bounding (AC#6) — secondary memory concern
6. capitalSnapshots downsampling (AC#7) — minor optimization
