# Sprint Change Proposal: Backtest Pipeline Scalable Data Loading

**Date:** 2026-03-31
**Triggered by:** Performance analysis of Story 10-9-3 (Backtest Simulation Engine)
**Scope classification:** Minor — Direct implementation by dev team
**Status:** Approved

---

## 1. Issue Summary

The `executePipeline` method in `backtest-engine.service.ts` loads all historical prices and trading pairs for the selected date range in a single Prisma query, materializing the entire result set in Node.js memory. With approximately 200GB of price and trading data in the database, this approach causes memory exhaustion (V8 heap overflow) and makes production-scale backtesting impossible.

Three specific anti-patterns were identified:

1. **Full materialization** — `loadPrices()` (line 592) executes a single `prisma.historicalPrice.findMany()` with no pagination or streaming. A 90-day backtest with 500+ pairs at 5-minute resolution generates tens of millions of price records (500 pairs × 2 platforms × 288 intervals/day × 90 days ≈ 25.9M records) loaded into memory simultaneously.

2. **N+1 depth queries** — `findNearestDepth()` is called twice per open position per time step during simulation. For 500 time steps with 10 concurrent positions, this produces ~10,000 individual database round-trips.

3. **Walk-forward amplification** — Walk-forward analysis runs 3 full simulations (train + test + canonical), tripling memory and compute cost on already-unscalable foundations.

**Evidence:** Direct code inspection of `backtest-engine.service.ts` lines 123-651, `fill-model.service.ts` lines 38-73. Confirmed by comparison with data-ingestion module, which already implements chunked processing for the same data types.

---

## 2. Impact Analysis

### Epic Impact

- **Epic 10.9** (Backtesting & System Calibration): All stories (10-9-0 through 10-9-7) are complete. A new story 10-9-3a is added to the epic for the pipeline optimization. Epic remains in-progress until 10-9-3a is done.

### Story Impact

- **10-9-3** (done): Scope boundary note added — simple data loading is intentional for development; production scale deferred to 10-9-3a.
- **10-9-3a** (new, backlog): Backtest Pipeline Scalable Data Loading. 10 tasks, P0 priority. Full story spec in epics.md.
- **10-9-4** (done): Calibration reports depend on full-scale backtest runs. Currently works with small datasets; production-scale runs blocked until 10-9-3a ships.
- **10-9-5** (done): Dashboard progress indicator for chunked pipeline folded into 10-9-3a's task list (task #6 event emission + dashboard consumption).

### Artifact Conflicts

- **PRD:** No conflict. MVP unaffected. Backtesting is Phase 1 scope.
- **Architecture:** No changes needed. Chunked processing follows established patterns (data-ingestion module). Module boundaries preserved — all changes within `modules/backtesting/`.
- **UX:** Minor enhancement (chunk progress indicator) folded into 10-9-3a. No UX redesign required.

### Technical Impact

- All existing simulation logic (opportunity detection, exit evaluation, portfolio management) is preserved unchanged.
- All 3,550+ existing tests (at time of writing) continue to pass.
- No schema migrations required.
- No cross-module dependency changes.

---

## 3. Recommended Approach

**Selected path:** Direct Adjustment — add Story 10-9-3a to Epic 10.9.

**Rationale:**

- The fix is surgically scoped to data retrieval methods (`loadPrices`, `loadPairs`, `alignPrices`, depth query batching).
- Proven patterns already exist in the codebase: data-ingestion module uses 7-day chunked windows, p-limit concurrency, batch operations.
- Industry best practices confirm: cursor-based pagination + time-window chunking is standard for backtesting engines processing large historical datasets.
- No rollback needed — simulation logic is correct and well-tested.
- No MVP scope impact — this is an implementation optimization.

**Alternatives considered:**

- **Rollback (Option 2):** Not viable. Simulation logic is sound; only data loading is problematic. Rolling back would discard working, tested code unnecessarily.
- **MVP Review (Option 3):** Not needed. MVP scope is unaffected — this is a performance optimization of an existing feature, not a scope reduction.

**Effort estimate:** Medium
**Risk level:** Low
**Timeline impact:** Adds one story (~1 sprint) to Epic 10.9 completion.

---

## 4. Detailed Change Proposals

### 4.1 New Story: 10-9-3a (Backtest Pipeline Scalable Data Loading)

Full story specification approved — see epics.md for complete ACs, tasks, and technical notes.

Key technical approach:

| Problem | Solution |
|---------|----------|
| Full price materialization | Time-window chunking (1-day default) via cursor-based Prisma queries |
| N+1 depth queries | Batch pre-load per chunk with `findMany` + `IN` clause |
| Walk-forward 3x amplification | Share pre-loaded chunks across headless simulations |
| Unbounded memory | Process-and-discard per chunk; accumulate only portfolio state |
| No progress visibility | Chunk-level EventEmitter2 events + dashboard WebSocket consumption |

### 4.2 Story 10-9-3 Scope Boundary Note

Added explicit note to Story 10-9-3: simple data loading (single-query `loadPrices`/`loadPairs`) is intentional for development and small-to-medium test datasets. Production-scale data loading is handled by Story 10-9-3a. This prevents reviewers flagging the simple pattern as a defect and prevents dev agents from attempting the optimization inline.

### 4.3 Story 10-9-5 Dashboard Enhancement

Chunked progress indicator folded into 10-9-3a task list (task #6). Dashboard displays chunk-level progress (e.g., "Processing day 15 of 90") via WebSocket gateway. Graceful fallback for pre-deployment runs (shows state machine status only without progress percentage).

### 4.4 Sprint Status Updates

- Added 10-9-3a as backlog story in Epic 10.9
- Updated summary statistics: total stories 146, done 151, backlog 7
- Updated CURRENT pointer to 10-9-3a as next story
- Corrected stale backlog counts (10-9-6, 10-9-7 already done)

---

## 5. Implementation Handoff

**Change scope:** Minor — Direct implementation by dev team.

**Handoff:**

- **Dev team:** Implement Story 10-9-3a following TDD workflow. All changes scoped to `modules/backtesting/engine/`. Use data-ingestion patterns (`polymarket-historical.service.ts` chunking, `incremental-fetch.service.ts` batch operations) as reference implementation.
- **SM (Bob):** Sprint-status.yaml updated. Monitor for scope creep beyond 10 tasks.

**Success criteria:**

1. 90-day backtest with 500+ pairs completes without memory exhaustion
2. Peak RSS stays under 512MB
3. All existing tests (3,550+ at time of writing) continue to pass
4. Chunk progress visible on dashboard during simulation
5. No cross-module changes required

**Follow-up candidates (deferred):**

- Chunk-level resume on failure (persist checkpoint to BacktestRun, allow restart from last successful chunk)
- PostgreSQL server-side cursors via `$queryRawUnsafe` for streaming (only if Prisma cursor pagination proves insufficient at scale)

---

## Research References

Industry best practices consulted during analysis:

- **Cursor-based pagination** over OFFSET for large PostgreSQL datasets (consistent O(1) performance vs O(N) degradation)
- **Node.js streaming pipelines** for NestJS batch processing (read → transform → batch → write, with backpressure)
- **Prisma connection pooling** with backpressure via semaphores (p-limit) to prevent pool exhaustion
- **DataLoader batching pattern** for eliminating N+1 queries (batch IDs, fetch once with `IN` clause)
- **Event-driven backtesting architecture** with time-step iteration and portfolio state accumulation
