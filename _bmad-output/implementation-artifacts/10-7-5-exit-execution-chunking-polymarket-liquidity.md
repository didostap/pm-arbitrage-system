# Story 10.7.5: Exit Execution Chunking & Polymarket Liquidity Handling

Status: done

## Story

As an operator,
I want exit orders split into smaller chunks matching available liquidity,
so that single-leg exposure on exit is reduced.

## Context

**Problem:** 235 single-leg exposure events in paper trading. Pattern: Kalshi exits fill but Polymarket fails with "Partial exit — remainder contracts unexited" (ExecutionError code 2008). Root cause: `executeExit()` submits the FULL residual size as a single order. When Polymarket book depth is 5-10 contracts but position size is 50-100, the order fails outright.

**Current flow (single-shot):** `executeExit()` computes `exitSize = min(primaryDepth, secondaryDepth, primaryEffective, secondaryEffective)` and submits ONE order per leg. If `exitSize < positionSize`, only a partial exit occurs. If depth is zero on either side, exit is deferred entirely.

**Target flow (chunked):** When position size exceeds available depth, loop through multiple chunks within a single `executeExit()` call. Each chunk submits both legs at depth-matched size before proceeding to the next chunk. If any chunk's secondary leg fails, exposure is limited to chunk size (not full position).

**Depends on:** 10-7-3 (corrected depth metric with tolerance band in `getAvailableExitDepth()`), 10-7-4 (`updateStatusWithAccumulatedPnl()` for per-chunk PnL accumulation).

## Acceptance Criteria

1. **AC-1: Depth-matched chunking**
   - **Given** an exit is triggered for a position
   - **When** the exit execution prepares orders
   - **Then** available depth on both platforms is checked before submitting exit orders
   - **And** if available depth on either platform is less than the position's remaining size, the exit is chunked into smaller orders matching available depth
   - **And** each chunk attempts both legs before proceeding to the next

2. **AC-2: Residual position tracking**
   - **Given** a partial chunked exit completes (some chunks succeeded but position not fully exited)
   - **When** the next exit evaluation cycle runs
   - **Then** the position size reflects the remaining (unexited) contracts via existing `getResidualSize()` logic
   - **And** the exit monitor continues evaluating the residual position for subsequent chunked exits

3. **AC-3: Chunk-level single-leg exposure**
   - **Given** a chunked exit where one leg fills but the other fails within a chunk
   - **When** single-leg exposure occurs at the chunk level
   - **Then** the exposure is limited to the chunk size (not the full position)
   - **And** existing auto-unwind logic (Story 10-3) handles chunk-level exposure via `handlePartialExit()`

4. **AC-4: Configurable maximum chunk size**
   - **Given** configurable chunking
   - **When** the operator sets `EXIT_MAX_CHUNK_SIZE`
   - **Then** exit orders never exceed this size (default: 0 = unlimited, backward-compatible)
   - **And** `EXIT_MAX_CHUNK_SIZE` is loaded from EngineConfig DB, appears in dashboard Settings under "Exit Strategy" group, and hot-reloads via `CONFIG_SETTINGS_UPDATED`

## Tasks / Subtasks

### Task 1: Add `EXIT_MAX_CHUNK_SIZE` config setting (AC: #4)

- [x] 1.1 `src/common/config/env.schema.ts` — Add `EXIT_MAX_CHUNK_SIZE: z.coerce.number().int().min(0).default(0)` adjacent to `EXIT_DEPTH_SLIPPAGE_TOLERANCE` (~line 265)
- [x] 1.2 `src/common/config/config-defaults.ts` — Add `exitMaxChunkSize: { envKey: 'EXIT_MAX_CHUNK_SIZE', defaultValue: 0 }` after `exitDepthSlippageTolerance` (~line 290)
- [x] 1.3 `src/common/config/settings-metadata.ts` — Add metadata: group `SettingsGroup.ExitStrategy`, type `'integer'`, label `'Exit Max Chunk Size'`, description `'Maximum contracts per exit chunk. 0 = unlimited (full depth-matched size).'`, min: 0. Place after `exitDepthSlippageTolerance` entry (~line 710)
- [x] 1.4 `src/dashboard/dto/update-settings.dto.ts` — Add `@IsOptional() @IsInt() @Min(0) exitMaxChunkSize?: number;` after `exitDepthSlippageTolerance` field (~line 403)
- [x] 1.5 `src/common/config/effective-config.types.ts` — Add `exitMaxChunkSize: number;` after `exitDepthSlippageTolerance` (~line 129)
- [x] 1.6 `prisma/schema.prisma` — Add `exitMaxChunkSize Int? @map("exit_max_chunk_size")` to EngineConfig model after `exitDepthSlippageTolerance` (~line 138)
- [x] 1.7 Create Prisma migration: `pnpm prisma migrate dev --name add-exit-max-chunk-size`
- [x] 1.8 `src/persistence/repositories/engine-config.repository.ts` — Add to resolve chain: `exitMaxChunkSize: resolve('exitMaxChunkSize') as number,` after `exitDepthSlippageTolerance` (~line 182)
- [x] 1.9 `prisma/seed-config.ts` — No explicit INT_FIELDS exists; integer fallback parseInt handles it. Verified NOT in FLOAT_FIELDS.

### Task 2: Wire config into ExitMonitorService (AC: #4)

- [x] 2.1 Add `private exitMaxChunkSize: number` field after `exitDepthSlippageTolerance` (~line 69)
- [x] 2.2 Initialize in constructor: `this.exitMaxChunkSize = this.configService.get<number>('EXIT_MAX_CHUNK_SIZE', 0);` after `exitDepthSlippageTolerance` init (~line 119)
- [x] 2.3 Add `exitMaxChunkSize?: number` to `reloadConfig()` settings parameter after `exitDepthSlippageTolerance` (~line 137)
- [x] 2.4 Add reload handler: `if (settings.exitMaxChunkSize !== undefined) this.exitMaxChunkSize = settings.exitMaxChunkSize;` after `exitDepthSlippageTolerance` handler (~line 158)

### Task 3: Wire hot-reload in settings.service.ts (AC: #4)

- [x] 3.1 Add `exitMaxChunkSize: ['exit-monitor']` to `SERVICE_RELOAD_MAP` after `exitDepthSlippageTolerance` (~line 97)
- [x] 3.2 Add `exitMaxChunkSize: cfg.exitMaxChunkSize` to the exit-monitor reload handler call after `exitDepthSlippageTolerance` (~line 166)

### Task 4: Update config test files (AC: #4)

- [x] 4.1 `src/common/config/config-defaults.spec.ts` — Add `'exitMaxChunkSize'` to ordered key list, `exitMaxChunkSize: 'EXIT_MAX_CHUNK_SIZE'` to envKey mapping, and `'exitMaxChunkSize'` to ordered keys array. Update count assertion (72 → 73)
- [x] 4.2 `src/common/config/config-accessor.service.spec.ts` — Add `exitMaxChunkSize: 0` to `buildMockEffectiveConfig()` after `exitDepthSlippageTolerance`
- [x] 4.3 `src/dashboard/settings.service.spec.ts` — Update settings count 74 → 75
- [x] 4.4 `prisma/seed-config.spec.ts` — Add `exitMaxChunkSize` to mock row

### Task 5: Refactor `executeExit()` with chunking loop (AC: #1, #2, #3)

This is the core change. Replace the single-shot submission (current lines ~909-1355) with a chunking loop.

**Key clarifications:**
- **`closePrice` is constant** across all chunks within one `executeExit()` call. Use the originally evaluated exit prices (`kalshiClosePrice`, `polymarketClosePrice`) for all chunks — do NOT recalculate per-chunk. These prices triggered the exit criteria and must remain consistent.
- **`getResidualSize()`** is a utility function in `exit-monitor.service.ts` (used at line ~400 in `evaluatePosition()`). Signature: `getResidualSize(position, allPairOrders) → { kalshi: Decimal, polymarket: Decimal, floored: boolean }`. It subtracts ALL persisted exit order fill sizes from entry fill sizes. Each chunk's orders are persisted immediately via `orderRepository.create()`, so on resume (next 30s cycle), `getResidualSize()` correctly reflects all prior exit fills — no double-counting risk.
- **PnL formula per-chunk:** Replicate the existing inline formula from `executeExit()` (lines ~1007-1119). Per-leg: `pnl = (exitFilledPrice - entryPrice) × exitFillSize` (direction-adjusted by side). Exit fees: `fee = exitFilledPrice × exitFillSize × takerFeeRate(price)`. Chunk PnL: `kalshiPnl + polyPnl - kalshiFee - polyFee`. Use exact same `FinancialMath.calculateTakerFeeRate()` call.
- **Safety guard:** Add `MAX_EXIT_CHUNK_ITERATIONS = 50` constant (private class field or local const). Break the loop if iterations exceed this limit. Log a warning if hit — indicates unexpectedly deep fragmentation.
- **Paper/live:** Chunking logic is mode-agnostic. The `isPaper` and `mixedMode` flags are passed through to `handlePartialExit()` and events unchanged. No mode-specific branching needed in the chunking loop itself.

- [x] 5.1 Write failing test: when position size exceeds both-leg depth and `exitMaxChunkSize=0`, multiple chunks are submitted matching depth on each iteration. Verify `submitOrder` called N times per leg where N = ceil(positionSize / min(depth_per_chunk)).
- [x] 5.2 Write failing test: when position size <= depth on both legs, single chunk submitted (backward-compatible, identical to current behavior).
- [x] 5.3 Implement chunking loop in `executeExit()`:
  - Track `remainingKalshi` and `remainingPoly` (start from effective sizes)
  - Track `accumulatedPnl` (start from `new Decimal(position.realizedPnl?.toString() ?? '0')`)
  - Track `chunksCompleted` counter and `iterations` counter
  - **Pre-loop guard:** If `remainingKalshi.lte(0) || remainingPoly.lte(0)`, log warn and return
  - **Loop** while `remainingKalshi.gt(0) && remainingPoly.gt(0) && iterations < MAX_EXIT_CHUNK_ITERATIONS`:
    a. `iterations++`
    b. Fetch fresh depth for both legs via `getAvailableExitDepth()` using the ORIGINAL `closePrice` (each chunk gets fresh book state)
    c. Compute `chunkSize = Decimal.min(primaryDepth, secondaryDepth, remainingPrimary, remainingSecondary)`
    d. If `this.exitMaxChunkSize > 0`: `chunkSize = Decimal.min(chunkSize, new Decimal(this.exitMaxChunkSize))`
    e. If `chunkSize.isZero()`: break (no depth, defer remaining to next cycle)
    f. Submit primary leg for `chunkSize`
    g. If primary fails: break (stop chunking, position stays current state)
    h. Persist primary exit order via `orderRepository.create()`
    i. Submit secondary leg for `chunkSize`
    j. If secondary fails: call `handlePartialExit()` with chunk-level `failedAttemptedSize = chunkSize` (NOT full position size) → break
    k. Persist secondary exit order via `orderRepository.create()`
    l. Compute chunk P&L: per-leg `(exitFilledPrice - entryPrice) × filledQuantity` (direction-adjusted), minus per-leg exit fees via `FinancialMath.calculateTakerFeeRate()`, using `decimal.js` `.mul()/.minus()/.plus()`
    m. Accumulate: `accumulatedPnl = accumulatedPnl.plus(chunkPnl)`
    n. Reduce residuals using actual fill quantities from results: `remainingKalshi = remainingKalshi.minus(kalshiExitFillSize)`, same for poly
    o. `chunksCompleted++`
  - **After loop — if iterations hit MAX_EXIT_CHUNK_ITERATIONS:** Log warning `'Exit chunking hit iteration limit'` with positionId, chunksCompleted, remaining sizes
  - **After loop — final state transition:**
    - If `remainingKalshi.lte(0) && remainingPoly.lte(0)`: Full exit → `positionRepository.closePosition(positionId, accumulatedPnl)`, release full capital via `riskManager.closePosition(capitalReturned, new Decimal(0), pairId, isPaper)`, emit `EXIT_TRIGGERED` with `chunksCompleted` in event data
    - Elif `chunksCompleted > 0`: Partial exit → `positionRepository.updateStatusWithAccumulatedPnl(positionId, 'EXIT_PARTIAL', accumulatedPnl.minus(existingPnl), existingPnl)`. Release partial capital: `partialCapital = totalEntryCapital.mul(new Decimal(contractsExited).div(totalContracts))` via `riskManager.releasePartialCapital(partialCapital, pairId, isPaper)`. Emit exit partial event with chunksCompleted
    - Else: No chunks completed → position unchanged (deferred to next cycle, no status change, no event)
  - Wrap `riskManager.closePosition()` and `releasePartialCapital()` in try-catch with `RiskStateDivergenceEvent` emission on failure (pattern from 10-7-4)
- [x] 5.4 Verify failing tests pass

### Task 6: Chunk-level single-leg exposure tests (AC: #3)

- [x] 6.1 Write test: secondary leg fails on chunk 2 (after chunk 1 succeeds) — verify `handlePartialExit()` called with chunk-level `failedAttemptedSize` (chunk size, not full position)
- [x] 6.2 Write test: secondary leg fails on chunk 1 — verify exposure equals chunk size, not full position size
- [x] 6.3 Write test: primary leg fails on a chunk — verify no `handlePartialExit()` called (no single-leg exposure since primary didn't fill), position stays at current state

### Task 7: Residual continuation and PnL accumulation tests (AC: #2)

- [x] 7.1 Write test: 3-chunk exit where all chunks succeed — verify `closePosition()` called with correct accumulated PnL (sum of all chunk PnLs)
- [x] 7.2 Write test: 2 of 3 chunks complete, depth exhausted on 3rd — verify `updateStatusWithAccumulatedPnl('EXIT_PARTIAL', ...)` called with accumulated PnL from 2 chunks
- [x] 7.3 Write test: EXIT_PARTIAL position from prior cycle re-enters `executeExit()` with reduced effective sizes via `getResidualSize()` — verify chunk sizes respect residual, not original entry size

### Task 8: Backward compatibility and config tests (AC: #4)

- [x] 8.1 Write test: `exitMaxChunkSize=0` (unlimited) with depth >= position size — single chunk, identical to pre-story behavior
- [x] 8.2 Write test: `exitMaxChunkSize=10` limits each chunk to 10 contracts even when depth is 50
- [x] 8.3 Write test: config hot-reload changes `exitMaxChunkSize` mid-session — verify new value used on next exit

### Task 9: Depth fetch per chunk test (AC: #1)

- [x] 9.1 Write test: depth decreases between chunks (mock `getOrderBook` to return less depth on 2nd call) — verify chunk 2 is smaller than chunk 1
- [x] 9.2 Write test: depth drops to zero on either leg between chunks — verify loop terminates and position transitions to EXIT_PARTIAL with accumulated PnL from completed chunks

### Task 10: Final verification (AC: #1-4)

- [x] 10.1 `pnpm lint` — all modified files clean (0 errors, 62 pre-existing warnings)
- [x] 10.2 `pnpm test` — all 2720 tests pass, 0 regressions
- [x] 10.3 Verify no bare `toHaveBeenCalled()` assertions without argument verification in new tests

## Dev Notes

### Architecture Compliance

- **Module boundary:** All logic changes are within `exit-management/` module. No new cross-module imports. Connectors are called through existing `IPlatformConnector` interface.
- **Hot path:** Exit evaluation is on a 30-second polling cycle, NOT the detection → risk → execution hot path. Multiple depth fetches per exit (one per chunk) are acceptable.
- **Error hierarchy:** No new error types needed. Existing `ExecutionError` with code 2008 (`PARTIAL_EXIT_FAILURE`) handles chunk-level failures. Depth fetch failures handled by existing try-catch fallback.
- **Financial math:** All PnL computation uses `decimal.js` — chunk PnL accumulation uses `.plus()`, `.minus()`, `.mul()`. Use `.toDecimalPlaces(8)` for Prisma persistence (matching `updateStatusWithAccumulatedPnl`).
- **Events:** No new event types. `EXIT_TRIGGERED` for full exit and `SINGLE_LEG_EXPOSURE` for chunk-level failures reuse existing event classes. Consider adding `chunksCompleted` and `totalChunks` fields to the `EXIT_TRIGGERED` event data object for operator visibility.
- **God Object awareness:** `exit-monitor.service.ts` is ~1547 lines with 9 constructor deps. Epic 10-8-2 will extract `ExitExecutionService`. For this story, keep the chunking logic tight within `executeExit()`. Do NOT extract a new service — that's 10-8-2's job.

### Chunking Design Decisions

**Why loop within `executeExit()` (not one-chunk-per-cycle):**
- One chunk per 30s cycle could take 5+ minutes to exit a 100-contract position against 10-contract-deep books
- The operator needs timely exits when criteria fire — chunking should complete as fast as depth allows
- Fresh depth fetch per chunk ensures each chunk reflects current book state

**Why depth-matched (not fixed-size):**
- Fixed-size chunks ignore actual liquidity — a 10-contract chunk against 3-contract depth still fails
- Depth-matched chunks guarantee each chunk can fill (within tolerance band from 10-7-3)
- `EXIT_MAX_CHUNK_SIZE` provides an optional upper bound for operator control

**Cross-leg equalization per chunk:**
- Each chunk submits the SAME `chunkSize` to both legs (matching current design)
- `chunkSize = Decimal.min(primaryDepth, secondaryDepth, remainingPrimary, remainingSecondary, exitMaxChunkSize?)`
- This ensures no leg gets ahead of the other within a chunk

**PnL accumulation pattern:**
- Uses `positionRepository.updateStatusWithAccumulatedPnl()` from story 10-7-4
- `pnlDelta` = sum of all chunk PnLs in this cycle
- `existingPnl` = position.realizedPnl from prior partial exits
- After all chunks: status set to EXIT_PARTIAL (if residual > 0) or CLOSED (if fully exited)
- NaN guard in `updateStatusWithAccumulatedPnl()` protects against corrupt PnL

**Partial capital release per chunk batch:**
- After all chunks complete (not per-chunk), release capital proportional to total exited amount
- Use `riskManager.releasePartialCapital()` for EXIT_PARTIAL, `riskManager.closePosition()` for CLOSED
- Risk state divergence handling via try-catch + `RiskStateDivergenceEvent` (from 10-7-4)

### Key File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/modules/exit-management/exit-monitor.service.ts` | **MODIFY** | Add chunking loop to `executeExit()`, add `exitMaxChunkSize` config field |
| `src/modules/exit-management/exit-monitor-chunking.spec.ts` | **ADD** | New focused test file for chunking behavior (Tasks 5-9) |
| `src/common/config/env.schema.ts` | **MODIFY** | Add `EXIT_MAX_CHUNK_SIZE` validator |
| `src/common/config/config-defaults.ts` | **MODIFY** | Add `exitMaxChunkSize` entry |
| `src/common/config/config-defaults.spec.ts` | **MODIFY** | Add to key lists, count 72 → 73 |
| `src/common/config/settings-metadata.ts` | **MODIFY** | Add metadata under Exit Strategy |
| `src/common/config/effective-config.types.ts` | **MODIFY** | Add `exitMaxChunkSize: number` |
| `src/common/config/config-accessor.service.spec.ts` | **MODIFY** | Add to mock effective config |
| `src/dashboard/dto/update-settings.dto.ts` | **MODIFY** | Add DTO field |
| `src/dashboard/settings.service.ts` | **MODIFY** | Add to SERVICE_RELOAD_MAP + handler |
| `src/dashboard/settings.service.spec.ts` | **MODIFY** | Settings count 74 → 75 |
| `src/persistence/repositories/engine-config.repository.ts` | **MODIFY** | Add to resolve chain |
| `prisma/schema.prisma` | **MODIFY** | Add EngineConfig column |
| `prisma/seed-config.ts` | **MODIFY** | Add to INT_FIELDS |
| `prisma/seed-config.spec.ts` | **MODIFY** | Add to mock row |
| `src/modules/exit-management/exit-monitor.test-helpers.ts` | **MODIFY** | May need mock updates if new test setup patterns needed |

### Files to NOT Modify

| File | Reason |
|------|--------|
| `src/connectors/kalshi/kalshi.connector.ts` | Connector submits single orders — chunking is caller's responsibility |
| `src/connectors/polymarket/polymarket.connector.ts` | Same — no connector changes needed |
| `src/common/interfaces/platform-connector.interface.ts` | `submitOrder(OrderParams)` interface unchanged — chunking loops over it |
| `src/common/types/platform.type.ts` | `OrderParams` and `OrderResult` types unchanged |
| `src/modules/exit-management/threshold-evaluator.service.ts` | Threshold evaluation triggers exit — not involved in execution |
| `src/modules/execution/position-close.service.ts` | Manual close path — not affected by exit monitor chunking |
| `src/modules/execution/single-leg-resolution.service.ts` | Handles single-leg exposure after detection — chunking doesn't change resolution |
| `src/persistence/repositories/position.repository.ts` | `closePosition()` and `updateStatusWithAccumulatedPnl()` already support chunked PnL (from 10-7-4) |

### What NOT To Do

- Do NOT add a `submitOrders(chunks[])` batch method to `IPlatformConnector` — loop over `submitOrder()` instead. Connector interface stays simple; chunking is exit-monitor's concern.
- Do NOT create a new `ExitChunkingService` — that decomposition belongs to Epic 10-8-2. Keep logic in `executeExit()` as a loop.
- Do NOT release capital per-chunk — aggregate all successful chunks and release once at the end. Per-chunk capital release adds complexity and race conditions with the risk manager.
- Do NOT persist intermediate EXIT_PARTIAL status between chunks within one `executeExit()` call — only persist final state after the loop ends. Crash recovery between chunks is acceptable loss (30s polling will re-evaluate).
- Do NOT add depth check retry logic — if a depth fetch fails for a chunk, fall back to remaining effective size (matching current single-shot fallback behavior).
- Do NOT modify the P&L formula — reuse the existing per-leg direction-adjusted formula. Only change is computing it per-chunk and accumulating.
- Do NOT add new event classes — reuse `ExitTriggeredEvent` for full exit and `SingleLegExposureEvent` for chunk failures. Add chunk metadata (chunksCompleted, chunkSize) to event data objects.

### Test File Organization

- **New file: `exit-monitor-chunking.spec.ts`** — All chunking-specific tests (Tasks 5-9). Uses `createExitMonitorTestModule()` from test helpers.
- **Existing files:** No modifications to existing test files needed. The chunking tests are additive. Existing tests verify single-shot behavior which remains correct when `exitMaxChunkSize=0` and depth >= position size.

### Test Mock Patterns

**Mock `getOrderBook` to simulate decreasing depth across chunks:**
```typescript
const kalshiConnector = ctx.kalshiConnector;
let kalshiCallCount = 0;
kalshiConnector.getOrderBook.mockImplementation(() => {
  kalshiCallCount++;
  // Chunk 1: 20 contracts available, Chunk 2: 15, Chunk 3: 0 (exhausted)
  const depthByCall = [20, 15, 0];
  const depth = depthByCall[Math.min(kalshiCallCount - 1, depthByCall.length - 1)];
  return Promise.resolve({
    bids: [{ price: 0.60, quantity: depth }],
    asks: [{ price: 0.62, quantity: depth }],
  });
});
```

**Mock `submitOrder` to return chunk-level fills:**
```typescript
kalshiConnector.submitOrder.mockImplementation((params) => {
  return Promise.resolve({
    orderId: asOrderId(`exit-kalshi-${Date.now()}`),
    platformId: PlatformId.KALSHI,
    status: 'filled',
    filledQuantity: params.quantity, // Full fill at chunk size
    filledPrice: params.price,
    timestamp: new Date(),
  });
});
```

**Verify chunk count via `submitOrder` call count:**
```typescript
// 50-contract position, 20-contract depth → expect 3 chunks (20 + 20 + 10)
expect(kalshiConnector.submitOrder).toHaveBeenCalledTimes(3);
expect(polymarketConnector.submitOrder).toHaveBeenCalledTimes(3);

// Verify chunk sizes
expect(kalshiConnector.submitOrder).toHaveBeenNthCalledWith(1, expect.objectContaining({ quantity: 20 }));
expect(kalshiConnector.submitOrder).toHaveBeenNthCalledWith(2, expect.objectContaining({ quantity: 20 }));
expect(kalshiConnector.submitOrder).toHaveBeenNthCalledWith(3, expect.objectContaining({ quantity: 10 }));
```

### Config Pipeline Pattern (Copy from 10-7-3)

**env.schema.ts:** `EXIT_MAX_CHUNK_SIZE: z.coerce.number().int().min(0).default(0)`
**config-defaults.ts:** `exitMaxChunkSize: { envKey: 'EXIT_MAX_CHUNK_SIZE', defaultValue: 0 }`
**settings-metadata.ts:**
```typescript
exitMaxChunkSize: {
  group: SettingsGroup.ExitStrategy,
  label: 'Exit Max Chunk Size',
  description: 'Maximum contracts per exit chunk. 0 = unlimited (full depth-matched size).',
  type: 'integer',
  envDefault: CONFIG_DEFAULTS.exitMaxChunkSize.defaultValue,
  min: 0,
},
```
**DTO:** `@IsOptional() @IsInt() @Min(0) exitMaxChunkSize?: number;`
**Prisma:** `exitMaxChunkSize Int? @map("exit_max_chunk_size")` (Int, not Float)
**seed-config.ts:** Add to `INT_FIELDS` array (not FLOAT_FIELDS)

### Previous Story Intelligence

**From 10-7-3 (exit depth slippage tolerance):**
- Config pipeline is mechanical — follow the exact same pattern across 15 files
- Settings count test: 74 → 75 (was 73 → 74 in 10-7-3)
- Config defaults count: 72 → 73 (was 71 → 72 in 10-7-3)
- `seed-config.ts` has separate arrays for INT_FIELDS and FLOAT_FIELDS — `exitMaxChunkSize` is an integer
- `config-accessor.service.spec.ts` `buildMockEffectiveConfig()` must include the new field

**From 10-7-4 (realized PnL fix):**
- `positionRepository.closePosition(positionId, realizedPnl)` with NaN guard — use for full exit after all chunks
- `positionRepository.updateStatusWithAccumulatedPnl(positionId, status, pnlDelta, existingPnl)` — use for EXIT_PARTIAL after partial chunks
- Risk state divergence handling: wrap `riskManager.closePosition()` and `releasePartialCapital()` in try-catch, emit `RiskStateDivergenceEvent` on failure
- PrismaService already injected in ExitMonitorService constructor (line 83)
- `exit-monitor.test-helpers.ts` already mocks `closePosition` and `updateStatusWithAccumulatedPnl`

**From 10-7-4 post-review fixes:**
- `sumClosedPnlByDateRange` with `COALESCE(realized_pnl, expected_edge)` handles historic NULLs — no impact on this story
- All CLOSED transitions in exit-monitor now use `positionRepository.closePosition()` — chunking should use the same

### Git Commit Context

- Most recent commit: `a01e7e4` (story 10-7-4 — realized PnL computation fix with follow-up deferred items)
- Current test count: **2,706 tests**, ~155 test files, 0 failures
- Settings count: 74, config defaults: 72

### Scope Boundary — What This Story Does NOT Do

- **No connector changes** — chunking loops over existing `submitOrder()` interface
- **No new event classes** — reuse existing events with optional chunk metadata
- **No new service files** — chunking lives in `executeExit()` (extraction deferred to 10-8-2)
- **No entry path changes** — chunking applies only to exit execution
- **No schema changes beyond config** — no new position fields or order fields
- **No dashboard UI changes** — chunked exit events flow through existing event → dashboard pipeline
- **No changes to manual close path** (`position-close.service.ts`) — only automatic exit monitor path
- **No changes to single-leg resolution** — existing handlers work at chunk level since `handlePartialExit()` reports chunk-level sizes

### Project Structure Notes

- All changes align with `src/modules/exit-management/` module scope (except config pipeline which touches `src/common/config/`, `src/dashboard/dto/`, `src/dashboard/settings.service.ts`, `src/persistence/repositories/`, and `prisma/`)
- No module boundary violations
- No new module registrations needed
- New test file `exit-monitor-chunking.spec.ts` follows co-located test pattern

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10.7, Story 10-7-5]
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts — executeExit() lines 821-1356, getAvailableExitDepth() lines 1364-1402, handlePartialExit() lines 1405-1503, evaluatePosition() EXIT_PARTIAL handling lines 396-450]
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.test-helpers.ts — createExitMonitorTestModule(), createMockPosition()]
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts — closePosition() lines 76-95, updateStatusWithAccumulatedPnl() lines 96-115]
- [Source: pm-arbitrage-engine/src/common/events/system.events.ts — RiskStateDivergenceEvent]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts — EVENT_NAMES.EXIT_TRIGGERED, SINGLE_LEG_EXPOSURE]
- [Source: pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts — submitOrder() lines 347-426]
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts — submitOrder() lines 521-656]
- [Source: _bmad-output/implementation-artifacts/10-7-3-c5-exit-depth-slippage-band-correction.md — Config pipeline pattern, tolerance band implementation]
- [Source: _bmad-output/implementation-artifacts/10-7-4-realized-pnl-computation-investigation-fix.md — PnL accumulation pattern, closePosition/updateStatusWithAccumulatedPnl]
- [Source: CLAUDE.md#Architecture — Module dependency rules, financial math, error handling, God Object limits]
- [Source: CLAUDE.md#Testing — Assertion depth, event wiring, co-located tests, paper/live boundary]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Tasks 1-4: Config pipeline for `EXIT_MAX_CHUNK_SIZE` (env schema, config defaults, settings metadata, DTO, effective config types, Prisma schema + migration, engine config repository, seed config, settings service reload map). All 15 config files updated. Settings count 74→75, config defaults 72→73.
- Task 5: Replaced single-shot `executeExit()` (lines 917-1364) with chunking loop. Key design: while loop with MAX_EXIT_CHUNK_ITERATIONS=50 safety, fresh depth fetch per chunk via `getAvailableExitDepth()`, cross-leg equalization per chunk, per-chunk PnL accumulation using existing `decimal.js` formula, post-loop state transition (CLOSED if fully exited, EXIT_PARTIAL if partially).
- Tasks 6-9: 13 new tests in `exit-monitor-chunking.spec.ts` covering: multi-chunk depth-matched exit (AC-1), single-chunk backward compatibility (AC-1), chunk-level single-leg exposure on secondary failure (AC-3), primary failure without handlePartialExit (AC-3), 3-chunk full exit with accumulated PnL (AC-2), partial chunked exit (AC-2), residual continuation from EXIT_PARTIAL (AC-2), exitMaxChunkSize=0 backward compat (AC-4), exitMaxChunkSize cap (AC-4), hot-reload (AC-4), decreasing depth per chunk (AC-1), depth exhaustion to EXIT_PARTIAL (AC-1).
- Updated 3 existing test files to accommodate chunking loop behavior: depth-check, partial-fills, partial-reevaluation. Key change: added 0-depth fallback after chunk 1 to prevent loop from continuing. Updated SingleLegExposureEvent test — event is no longer emitted for both-leg partial fills (reserved for actual single-leg exposure via handlePartialExit).
- Behavior change: Old code emitted SingleLegExposureEvent when both legs filled partially (overloaded usage). New code correctly reserves it for actual single-leg exposure only.

### File List

- `src/common/config/env.schema.ts` — MODIFIED: Added EXIT_MAX_CHUNK_SIZE validator
- `src/common/config/config-defaults.ts` — MODIFIED: Added exitMaxChunkSize entry
- `src/common/config/settings-metadata.ts` — MODIFIED: Added metadata under Exit Strategy
- `src/common/config/effective-config.types.ts` — MODIFIED: Added exitMaxChunkSize: number
- `src/common/config/config-defaults.spec.ts` — MODIFIED: Added to key lists, count 72→73
- `src/common/config/config-accessor.service.spec.ts` — MODIFIED: Added to mock effective config
- `src/dashboard/dto/update-settings.dto.ts` — MODIFIED: Added DTO field
- `src/dashboard/settings.service.ts` — MODIFIED: Added to SERVICE_RELOAD_MAP + handler
- `src/dashboard/settings.service.spec.ts` — MODIFIED: Settings count 74→75
- `src/persistence/repositories/engine-config.repository.ts` — MODIFIED: Added to resolve chain
- `prisma/schema.prisma` — MODIFIED: Added EngineConfig column
- `prisma/migrations/20260324015044_add_exit_max_chunk_size/migration.sql` — ADDED: Migration
- `prisma/seed-config.spec.ts` — MODIFIED: Added exitMaxChunkSize to mock row
- `src/modules/exit-management/exit-monitor.service.ts` — MODIFIED: Chunking loop in executeExit(), exitMaxChunkSize config field + reload
- `src/modules/exit-management/exit-monitor-chunking.spec.ts` — ADDED: 13 chunking tests
- `src/modules/exit-management/exit-monitor-depth-check.spec.ts` — MODIFIED: Added 0-depth fallback for chunking compat
- `src/modules/exit-management/exit-monitor-partial-fills.spec.ts` — MODIFIED: Added 0-depth fallback, updated SingleLegExposureEvent test
- `src/modules/exit-management/exit-monitor-partial-reevaluation.spec.ts` — MODIFIED: Added 0-depth fallback for chunking compat
