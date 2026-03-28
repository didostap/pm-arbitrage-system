---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-31'
storyFile: '_bmad-output/implementation-artifacts/10-9-3a-backtest-pipeline-scalable-data-loading.md'
storyId: 10-9-3a
detectedStack: fullstack
generationMode: ai-generation
inputDocuments:
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/config.yaml
---

# ATDD Checklist: Story 10-9-3a — Backtest Pipeline Scalable Data Loading

## Test Strategy Summary

- **Test framework:** Vitest 4 + unplugin-swc (NestJS decorator metadata)
- **Test levels:** Unit (pure functions, edge cases) + Integration (service interactions, event wiring)
- **No E2E browser tests** for the backend engine; dashboard frontend changes are a separate concern
- **TDD phase:** RED — all items below are acceptance criteria the dev agent must cover with failing tests before implementation

## Priority Legend

| Priority | Criteria |
|----------|----------|
| P0 | Financial data integrity, simulation correctness, backward compatibility |
| P1 | Core chunked pipeline functionality, timeout enforcement |
| P2 | Progress events, dashboard integration, diagnostics |
| P3 | Edge cases with low probability |

---

## AC #1: Chunked Price Loading (replaces monolithic loadPrices)

### Unit Tests — BacktestConfigDto (backtest-config.dto.spec.ts)

- [ ] `10-9-3a-UNIT-001` [P0] `chunkWindowDays` defaults to `1` when not provided
- [ ] `10-9-3a-UNIT-002` [P1] `chunkWindowDays` accepts valid integer values (1, 7, 15, 30)
- [ ] `10-9-3a-UNIT-003` [P1] `chunkWindowDays` rejects value `0` (below @Min(1))
- [ ] `10-9-3a-UNIT-004` [P1] `chunkWindowDays` rejects value `31` (above @Max(30))
- [ ] `10-9-3a-UNIT-005` [P1] `chunkWindowDays` rejects non-integer values (e.g., 1.5)
- [ ] `10-9-3a-UNIT-006` [P2] `chunkWindowDays` rejects negative values

### Unit Tests — IBacktestConfig (type-level)

- [ ] `10-9-3a-UNIT-007` [P0] `IBacktestConfig` interface includes `chunkWindowDays: number` (compile-time check via test that constructs a config object with the field)

### Unit Tests — BacktestDataLoaderService.generateChunkRanges()

- [ ] `10-9-3a-UNIT-008` [P0] Generates correct day-aligned chunk ranges for exact multi-day range (e.g., 7-day range with chunkWindowDays=1 → 7 ranges)
- [ ] `10-9-3a-UNIT-009` [P0] Last chunk is shorter when date range is not evenly divisible by chunkWindowDays (e.g., 10 days with chunkWindowDays=3 → 4 ranges, last is 1 day)
- [ ] `10-9-3a-UNIT-010` [P1] Single-day range with chunkWindowDays=1 → exactly 1 range
- [ ] `10-9-3a-UNIT-011` [P1] chunkWindowDays larger than date range → 1 range covering entire range
- [ ] `10-9-3a-UNIT-012` [P2] Chunk ranges are contiguous with no gaps or overlaps (end of chunk N === start of chunk N+1)

### Integration Tests — BacktestDataLoaderService.loadPricesForChunk()

- [ ] `10-9-3a-INT-001` [P0] Returns only HistoricalPrice records within the specified chunk timestamp range (gte/lte)
- [ ] `10-9-3a-INT-002` [P1] Returns records ordered by `timestamp ASC`
- [ ] `10-9-3a-INT-003` [P1] Returns empty array when no records exist in the chunk range
- [ ] `10-9-3a-INT-004` [P2] Does NOT return records outside the chunk range (boundary precision)

### Integration Tests — BacktestDataLoaderService.loadPairs()

- [ ] `10-9-3a-INT-005` [P1] Loads ContractMatch pairs using existing logic (moved from BacktestEngineService)
- [ ] `10-9-3a-INT-006` [P2] Returns empty array when no pairs match config criteria

---

## AC #2: Per-Chunk Alignment (alignPrices operates per-chunk)

### Integration Tests — Pipeline chunk loop (backtest-engine.service.spec.ts)

- [ ] `10-9-3a-INT-007` [P0] `alignPrices()` is called once per chunk (not once for all data) — verify call count matches chunk count
- [ ] `10-9-3a-INT-008` [P0] Only the current chunk's time steps are passed to `runSimulationLoop` — verify timeSteps argument per invocation
- [ ] `10-9-3a-INT-009` [P1] `alignPrices()` receives only the current chunk's prices (not accumulated prices from prior chunks)

---

## AC #3: Batch Depth Pre-Loading (eliminates N+1)

### Unit Tests — BacktestDataLoaderService.preloadDepthsForChunk()

- [ ] `10-9-3a-UNIT-013` [P0] Returns `Map<string, ParsedHistoricalDepth[]>` keyed by `${platform}:${contractId}`
- [ ] `10-9-3a-UNIT-014` [P0] Depths per key are sorted by timestamp DESC
- [ ] `10-9-3a-UNIT-015` [P1] contractIds derived from both kalshiContractId and polymarketClobTokenId (deduplicated)
- [ ] `10-9-3a-UNIT-016` [P1] Uses single `findMany` with `IN` clause on contractIds + timestamp range (verify Prisma call args)
- [ ] `10-9-3a-UNIT-017` [P2] Returns empty Map when no depth records exist for the chunk range
- [ ] `10-9-3a-UNIT-018` [P2] Depth cache includes `/** Cleanup:` strategy comment (code review item — verify in source)

### Unit Tests — findNearestDepthFromCache() (pure function)

- [ ] `10-9-3a-UNIT-019` [P0] Returns the depth with `timestamp <= queryTimestamp` (nearest earlier snapshot — conservative)
- [ ] `10-9-3a-UNIT-020` [P0] Returns exact match when query timestamp equals a snapshot timestamp
- [ ] `10-9-3a-UNIT-021` [P0] Returns `null` when query timestamp is before all snapshots in cache
- [ ] `10-9-3a-UNIT-022` [P0] Returns `null` when cache has no entry for the given platform:contractId key
- [ ] `10-9-3a-UNIT-023` [P1] Multiple contracts in cache are keyed independently (lookup for contract A does not return contract B data)
- [ ] `10-9-3a-UNIT-024` [P1] Function is a pure standalone export (not a service method — verify no `this` usage, no DI deps)
- [ ] `10-9-3a-UNIT-025` [P1] Between two snapshots, returns the earlier one (binary search correctness with >2 entries)
- [ ] `10-9-3a-UNIT-026` [P2] Handles single-entry cache correctly (query after → returns it, query before → null)

### Integration Tests — FillModelService.modelFill() with depthCache

- [ ] `10-9-3a-INT-010` [P0] When `depthCache` is provided, uses `findNearestDepthFromCache()` — no `prisma.historicalDepth.findFirst` calls
- [ ] `10-9-3a-INT-011` [P0] When `depthCache` is NOT provided, falls back to existing `findNearestDepth()` DB query
- [ ] `10-9-3a-INT-012` [P1] Cache miss (no depth for contract) returns null gracefully, fill model handles null depth correctly
- [ ] `10-9-3a-INT-013` [P1] FillModelService constructor dep count stays at 1 (PrismaService) — no new injected deps

### Unit Tests — parseJsonDepthLevels() utility

- [ ] `10-9-3a-UNIT-027` [P1] Parses JSON `{ price: string; size: string }[]` → `{ price: Decimal; size: Decimal }[]`
- [ ] `10-9-3a-UNIT-028` [P2] Handles empty array input → returns empty array
- [ ] `10-9-3a-UNIT-029` [P2] Handles malformed JSON depth levels gracefully (e.g., missing price field)

---

## AC #4: Walk-Forward Chunked Routing

### Unit Tests — Walk-forward date boundary computation

- [ ] `10-9-3a-UNIT-030` [P0] `trainEndDate` computed as `dateRangeStart + (dateRangeEnd - dateRangeStart) * walkForwardTrainPct`, aligned to UTC day boundary
- [ ] `10-9-3a-UNIT-031` [P1] Boundary alignment: `trainEndDate` has `HH:MM:SS = 00:00:00` (UTC midnight)

### Integration Tests — Chunk routing to train/test headless simulations

- [ ] `10-9-3a-INT-014` [P0] Chunk entirely within train period → `runSimulationLoop` called with `headlessTrainRunId`
- [ ] `10-9-3a-INT-015` [P0] Chunk entirely within test period → `runSimulationLoop` called with `headlessTestRunId`
- [ ] `10-9-3a-INT-016` [P0] Chunk spanning train/test boundary → timeSteps correctly split at `trainEndDate`, each half routed to appropriate headless sim
- [ ] `10-9-3a-INT-017` [P1] Headless portfolios initialized at pipeline start with IDs `${mainRunId}-wf-train` and `${mainRunId}-wf-test`
- [ ] `10-9-3a-INT-018` [P1] `closeRemainingPositions` called for both headless runs after all chunks complete
- [ ] `10-9-3a-INT-019` [P1] Headless portfolios destroyed in `finally` block (even on error)
- [ ] `10-9-3a-INT-020` [P1] Walk-forward train/test metrics correctly aggregated from respective headless portfolios
- [ ] `10-9-3a-INT-021` [P2] `WalkForwardService.splitTimeSteps()` still exists and is callable (backward compat)

---

## AC #5 + AC #9: Chunk Progress Events + Dashboard WebSocket

### Unit Tests — BacktestPipelineChunkCompletedEvent

- [ ] `10-9-3a-UNIT-032` [P1] Event class constructed with all required fields: `runId`, `chunkIndex`, `totalChunks`, `chunkDateStart`, `chunkDateEnd`, `elapsedMs`, `positionsOpenedInChunk`, `positionsClosedInChunk`
- [ ] `10-9-3a-UNIT-033` [P2] Event name `backtesting.pipeline.chunk.completed` registered in `event-catalog.ts`

### Integration Tests — Event emission in pipeline

- [ ] `10-9-3a-INT-022` [P1] After each chunk completes, `BacktestPipelineChunkCompletedEvent` is emitted with correct `chunkIndex` and `totalChunks`
- [ ] `10-9-3a-INT-023` [P1] Correct number of chunk events emitted (e.g., 7 events for 7-day range with chunkWindowDays=1)
- [ ] `10-9-3a-INT-024` [P2] Event includes accurate `positionsOpenedInChunk` and `positionsClosedInChunk` deltas

### Integration Tests — DashboardGateway handler wiring

- [ ] `10-9-3a-INT-025` [P1] `expectEventHandled()` test verifies `@OnEvent('backtesting.pipeline.chunk.completed')` handler is wired in DashboardGateway
- [ ] `10-9-3a-INT-026` [P1] Gateway handler broadcasts `{ event: 'backtest-chunk-progress', data: { runId, chunkIndex, totalChunks, chunkDateStart, chunkDateEnd } }` to WebSocket clients
- [ ] `10-9-3a-INT-027` [P1] New handler method added to `allGatewayMethods` array in `event-wiring-audit.spec.ts`

### Frontend Tests — Dashboard (pm-arbitrage-dashboard/, separate repo)

- [ ] `10-9-3a-FE-001` [P2] `WsBacktestChunkProgressPayload` type defined in `src/types/ws-events.ts`
- [ ] `10-9-3a-FE-002` [P2] BacktestDetailPage subscribes to `backtest-chunk-progress` WS event
- [ ] `10-9-3a-FE-003` [P2] Chunk progress indicator renders "Processing day {N} of {total}" with progress bar when state is `SIMULATING`
- [ ] `10-9-3a-FE-004` [P2] Graceful fallback: if no chunk events within 5s of `SIMULATING`, shows only `BacktestStatusBadge`
- [ ] `10-9-3a-FE-005` [P2] Chunk progress hidden when state transitions to `GENERATING_REPORT` or `COMPLETE`

---

## AC #6: Memory Bound (512MB RSS for 90-day, 500+ pairs)

### Integration Tests — Architectural memory patterns

- [ ] `10-9-3a-INT-028` [P0] `loadPricesForChunk` called once per chunk (not once for all data) — verify chunked loading pattern
- [ ] `10-9-3a-INT-029` [P0] No service retains references to chunk data after processing (prices, depthCache, chunkTimeSteps go out of scope per iteration)
- [ ] `10-9-3a-INT-030` [P1] `preloadDepthsForChunk` called once per chunk (not accumulated across chunks)
- [ ] `10-9-3a-INT-031` [P1] Pipeline state that persists across chunks is bounded: `pairs` (small, loaded once), portfolio state (grows with closed positions but lightweight)

> **Note:** AC #6's 512MB RSS target is validated via manual testing with production-scale dataset. CI tests verify the chunked architecture pattern, not actual RSS measurement.

---

## AC #7: Existing Test Backward Compatibility

### Integration Tests — Regression guard

- [ ] `10-9-3a-INT-032` [P0] All existing `backtest-engine.service.spec.ts` tests pass with refactored pipeline (no modification to existing test assertions)
- [ ] `10-9-3a-INT-033` [P0] All existing `fill-model.service.spec.ts` tests pass with added `depthCache` parameter (backward compat via optional param)
- [ ] `10-9-3a-INT-034` [P0] All existing `backtest-portfolio.service.spec.ts` tests pass unchanged

### Integration Tests — Cross-chunk portfolio continuity

- [ ] `10-9-3a-INT-035` [P0] Position opened in chunk N is correctly evaluated for exit in chunk N+1 (2-day fixture: entry day 1, exit day 2)
- [ ] `10-9-3a-INT-036` [P0] Equity curve and drawdown tracking are continuous across chunk boundaries (no reset between chunks)
- [ ] `10-9-3a-INT-037` [P1] `closeRemainingPositions()` called AFTER the chunk loop completes (not per-chunk)

---

## AC #8: Cross-Chunk Timeout Enforcement

### Integration Tests — Timeout across chunks

- [ ] `10-9-3a-INT-038` [P0] Timeout checked at end of each chunk iteration: `Date.now() - pipelineStartTime > config.timeoutSeconds * 1000`
- [ ] `10-9-3a-INT-039` [P0] When timeout is exceeded mid-pipeline, state transitions to `FAILED` with error code `4210 BACKTEST_TIMEOUT`
- [ ] `10-9-3a-INT-040` [P1] Timeout is NOT reset per chunk (cumulative across entire pipeline)
- [ ] `10-9-3a-INT-041` [P1] Short timeout (e.g., 1 second) with multi-chunk range triggers `FAILED` transition

---

## Additional: Module & Wiring

### Integration Tests — EngineModule providers

- [ ] `10-9-3a-INT-042` [P1] `BacktestDataLoaderService` is in `EngineModule` providers (6 total: BacktestEngineService, BacktestStateMachineService, BacktestPortfolioService, FillModelService, ExitEvaluatorService, BacktestDataLoaderService)
- [ ] `10-9-3a-INT-043` [P1] `BacktestEngineService` constructor has 9 deps with mandatory rationale comment

### Integration Tests — Empty chunk handling

- [ ] `10-9-3a-INT-044` [P1] Empty chunk (no aligned time steps after `alignPrices`) → progress event emitted with zero positions, simulation skipped via `continue`
- [ ] `10-9-3a-INT-045` [P2] Empty chunk is NOT excluded from `totalChunks` count (chunk still counted in progress)

### Integration Tests — Per-chunk position tracking

- [ ] `10-9-3a-INT-046` [P1] `positionsOpenedInChunk` computed as delta of open position count before/after simulation
- [ ] `10-9-3a-INT-047` [P1] `positionsClosedInChunk` computed as delta of closed position count before/after simulation

### Integration Tests — 90-day chunked backtest (Task 8)

- [ ] `10-9-3a-INT-048` [P0] 90-day date range with `chunkWindowDays: 1` → pipeline completes, 90 chunk progress events emitted
- [ ] `10-9-3a-INT-049` [P0] `loadPricesForChunk` called 90 times, `preloadDepthsForChunk` called 90 times
- [ ] `10-9-3a-INT-050` [P1] Aggregate metrics (total PnL, Sharpe, max drawdown) computed correctly across chunked processing
- [ ] `10-9-3a-INT-051` [P1] Timeout enforcement works across 90 chunks (short timeout triggers FAILED)

---

## Coverage Summary

| Priority | Count | Categories |
|----------|-------|------------|
| P0 | 24 | Chunk generation, depth cache correctness, fill model paths, backward compat, portfolio continuity, timeout, memory patterns |
| P1 | 29 | DTO validation, chunk routing, event wiring, module wiring, position tracking, walk-forward |
| P2 | 14 | Edge cases, empty chunks, dashboard frontend, diagnostics |
| P3 | 0 | — |
| **Total** | **67** | |

### Test Level Distribution

| Level | Count | Scope |
|-------|-------|-------|
| Unit | 33 | Pure functions (chunk ranges, binary search, depth cache, DTO, event construction, JSON parsing) |
| Integration | 29 | Service interactions (pipeline orchestration, event wiring, FillModelService cache path, module providers, 90-day integration) |
| Frontend | 5 | Dashboard WS subscription, progress rendering, fallback (separate repo) |

---

## TDD Red Phase Guidance

All checklist items above are **acceptance tests the dev agent must write as failing tests BEFORE implementing the corresponding production code**. The TDD cycle per item:

1. **Red** — Write the test for the checklist item. It should fail (service/function doesn't exist yet or lacks the new behavior).
2. **Green** — Write the minimum production code to make the test pass.
3. **Refactor** — Clean up while keeping tests green.

### Implementation Order (recommended by dependency)

1. **Task 1** → UNIT-001 through UNIT-007 (DTO + interface — foundational types)
2. **Task 2** → UNIT-008 through UNIT-029, INT-001 through INT-006 (BacktestDataLoaderService + findNearestDepthFromCache)
3. **Task 4** → INT-010 through INT-013 (FillModelService depthCache parameter)
4. **Task 3** → INT-007 through INT-009, INT-028 through INT-031, INT-038 through INT-041, INT-044 through INT-047 (pipeline refactor, timeout, empty chunks, position tracking)
5. **Task 5** → INT-035 through INT-037 (cross-chunk portfolio continuity)
6. **Task 7** → UNIT-030, UNIT-031, INT-014 through INT-021 (walk-forward chunked routing)
7. **Task 6** → UNIT-032, UNIT-033, INT-022 through INT-027, FE-001 through FE-005 (events + dashboard)
8. **Task 10** → INT-042, INT-043 (module wiring)
9. **Task 8** → INT-048 through INT-051 (90-day integration test)
10. **Task 9** → covered by UNIT-019 through UNIT-026 (depth pre-loading unit tests — written in Task 2)

### Post-Implementation Verification

After all tasks complete:
- [ ] INT-032 through INT-034: Run full existing test suite — confirm zero regressions
- [ ] `pnpm lint` passes
- [ ] `pnpm test` passes (all 1774+ existing tests + new tests)
