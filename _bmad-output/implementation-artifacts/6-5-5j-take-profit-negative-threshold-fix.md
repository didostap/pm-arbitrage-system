# Story 6-5.5j: Take-Profit Negative Threshold Fix

Status: done

## Story

As a **system operator**,
I want the take-profit threshold to never produce a negative value that triggers position closure at a realized loss,
so that positions whose profit path is resolution are not prematurely exited, destroying convergence profit.

## Acceptance Criteria

1. **Journey-based TP formula:** The take-profit threshold uses the journey formula `max(0, entryCostBaseline + 0.80 * (scaledInitialEdge - entryCostBaseline))` in both `ThresholdEvaluatorService.evaluate()` and `PositionEnrichmentService.enrich()`.
2. **No negative TP triggers:** No position triggers `take_profit` exit when `currentPnl < 0`. The `max(0, ...)` floor guarantees this.
3. **Legacy regression-safe:** Positions with `entryCostBaseline = 0` (null entry close prices) produce **identical** thresholds to the current formula. Verify: `max(0, 0 + 0.80 * (edge - 0)) = 0.80 * edge`.
4. **Real-position validation:** Given `entryCostBaseline = -$5.73` and `scaledInitialEdge = $1.65`, the formula produces `+$0.17` (not `-$4.41`).
5. **Extreme-spread floor:** Given `entryCostBaseline = -$20` and `scaledInitialEdge = $1.00`, the formula produces `$0.00` (floor activates).
6. **Normal-position behavior:** Moderate-spread positions (e.g., baseline = -$1.00, edge = $3.00) produce threshold $2.20 (increased from $1.40 under old formula).
7. **SL unchanged:** Stop-loss threshold formula is NOT modified. Existing SL tests continue to pass without changes.
8. **6.5.5i supersession note:** A supersession note is appended to `_bmad-output/implementation-artifacts/6-5-5i-exit-threshold-calibration-fix.md` at the "Design Note — Take-Profit via Early Exit" section, pointing to this story's corrected analysis.
9. **All tests pass:** `pnpm test` passes. `pnpm lint` reports zero errors.

## Tasks / Subtasks

- [x] Task 1: Fix TP formula in `ThresholdEvaluatorService.evaluate()` (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] 1.1 Write failing test: negative baseline + small edge produces positive TP threshold (AC 4: baseline=-5.73, edge=1.65, expect +0.17)
  - [x] 1.2 Write failing test: extreme spread activates floor (AC 5: baseline=-20, edge=1.00, expect 0.00)
  - [x] 1.3 Write failing test: moderate spread produces higher threshold (AC 6: baseline=-1.00, edge=3.00, expect 2.20)
  - [x] 1.4 Update TP formula to journey-based with floor
  - [x] 1.5 Verify existing legacy tests still pass unchanged (AC 3)
  - [x] 1.6 Verify existing SL tests still pass unchanged (AC 7)
- [x] Task 2: Mirror TP formula fix in `PositionEnrichmentService.enrich()` (AC: 1, 2, 3)
  - [x] 2.1 Write failing test: negative baseline produces positive TP threshold in enrichment
  - [x] 2.2 Write failing test: extreme spread activates floor in enrichment
  - [x] 2.3 Update TP formula to journey-based with floor
  - [x] 2.4 Verify existing enrichment tests pass unchanged
  - [x] 2.5 Verify TP proximity calculation remains correct with new threshold values
- [x] Task 3: Update existing negative-threshold tests (AC: 1, 2)
  - [x] 3.1 Update threshold-evaluator test "should use zero spread when close prices equal fill prices" — update comments only: TP threshold changes from -0.14 to +1.892 (`max(0, 0.20*(-2.54) + 0.80*3.00) = 1.892`). Assertion `triggered=false` is unchanged (currentPnl=-0.54 is still below new threshold).
  - [x] 3.2 Update threshold-evaluator test "should handle Kalshi dynamic fee at different entry price tier" — TP threshold changes from -1.135 to +1.373 (`max(0, 0.20*(-3.135) + 0.80*2.50) = 1.373`). **Assertion flips:** `triggered=true, type='take_profit'` becomes `triggered=false` (currentPnl=0.0 < 1.373). This test directly demonstrates the bug fix.
  - [x] 3.3 Update enrichment test "offsets exit proximity with entry cost baseline" — TP threshold changes from -5.04 to 0.00 (floor activates: `max(0, 0.20*(-6.0) + 0.80*1.2) = max(0, -0.24) = 0`). TP proximity changes from ~0.04167 to ~0.00667 (`0.04 / 6.0`).
  - [x] 3.4 Update enrichment test "P&L at TP threshold with non-zero baseline: TP proximity = 100%" — TP threshold changes from -1.04 to +0.56 (`max(0, 0.20*(-2.0) + 0.80*1.2) = 0.56`). Must recraft current prices so `currentPnl = 0.56` to maintain 100% proximity intent: `kalshiClose - polyClose = 0.1056` (e.g., kalshi=0.5528, poly=0.4472 with 0% exit fee rate).
- [x] Task 4: Append supersession note to 6.5.5i story (AC: 8)
  - [x] 4.1 Append to `_bmad-output/implementation-artifacts/6-5-5i-exit-threshold-calibration-fix.md` immediately after the "Design Note — Take-Profit via Early Exit" paragraph (line ~247): `> **Superseded by Story 6.5.5j** — The design note above incorrectly concluded that negative TP thresholds are "expected and correct." Story 6.5.5j replaces the formula with a journey-based calculation floored at zero. Positions whose profit path is resolution now correctly avoid premature TP exits at a loss. See 6-5-5j-take-profit-negative-threshold-fix.md for the corrected analysis.`
- [x] Task 5: Final validation (AC: 9)
  - [x] 5.1 Run `pnpm test` — all tests pass
  - [x] 5.2 Run `pnpm lint` — zero errors

## Dev Notes

### Formula Change (CRITICAL)

**OLD (current, flawed):**
```typescript
const takeProfitThreshold = entryCostBaseline.plus(
  scaledInitialEdge.mul(new Decimal('0.80')),
);
```

**NEW (journey-based with floor):**
```typescript
const takeProfitThreshold = Decimal.max(
  new Decimal(0),
  entryCostBaseline.plus(
    scaledInitialEdge.minus(entryCostBaseline).mul(new Decimal('0.80')),
  ),
);
```

Mathematically: `max(0, 0.20 * entryCostBaseline + 0.80 * scaledInitialEdge)`

The key insight: the old formula added 80% of the convergence edge to the baseline, but the edge and baseline live in different frames of reference. The journey formula measures "80% of the total improvement from entry MtM to convergence" which is `scaledInitialEdge - entryCostBaseline`.

### Root Cause

Story 6.5.5i introduced `entryCostBaseline` (the MtM deficit from bid-ask spreads + exit fees at entry time) and offset TP/SL thresholds by it. The TP formula `entryCostBaseline + 0.80 * scaledInitialEdge` treats the edge as an additive improvement from baseline, but the edge is measured from zero (convergence profit), not from the baseline (early-exit reality). When `|entryCostBaseline| > 0.80 * scaledInitialEdge`, the threshold goes negative, causing TP to fire at a loss.

### Behavior Change Matrix

| Scenario | Baseline | Edge | Old TP | New TP | Change |
|----------|----------|------|--------|--------|--------|
| Legacy (no baseline) | $0 | $3.00 | $2.40 | $2.40 | None |
| Moderate spread | -$1.00 | $3.00 | $1.40 | $2.20 | Higher (+$0.80) |
| Real position (bug) | -$5.73 | $1.65 | **-$4.41** | **+$0.17** | Fixed |
| Extreme spread | -$20 | $1.00 | -$19.20 | **$0.00** | Floor |

### Files to Modify

1. **`src/modules/exit-management/threshold-evaluator.service.ts`** — Core fix: TP formula in `evaluate()` method, lines ~158-161
2. **`src/modules/exit-management/threshold-evaluator.service.spec.ts`** — New tests + update 2 existing tests with negative thresholds
3. **`src/dashboard/position-enrichment.service.ts`** — Mirror fix: TP formula in `enrich()` method, lines ~211-213
4. **`src/dashboard/position-enrichment.service.spec.ts`** — New tests + update 2-3 existing tests with negative thresholds
5. **`_bmad-output/implementation-artifacts/6-5-5i-exit-threshold-calibration-fix.md`** — Supersession note (non-code)

### Files NOT to Modify

- `src/common/utils/financial-math.ts` — Tech debt extraction of `computeTakeProfitThreshold()` is explicitly deferred (see sprint change proposal Section 5, line 214-216). Do NOT extract in this story.
- `prisma/schema.prisma` — No schema changes.
- Any module boundary or event definitions — No new events, no new error codes.
- Stop-loss formula — SL is correct and untouched.

### Architecture Compliance

- **Module boundaries:** Changes are internal to `exit-management` and `dashboard` modules. No new cross-module imports.
- **Financial math:** All calculations use `decimal.js` (`Decimal.max()`, `.plus()`, `.minus()`, `.mul()`). Never native JS operators.
- **Error hierarchy:** No new errors introduced. Existing `SystemError` hierarchy unchanged.
- **Events:** No new events. Existing `exit.take-profit.triggered` event unchanged in structure.

### Testing Approach

- **Direct instantiation:** Both services use `new ThresholdEvaluatorService()` and `new PositionEnrichmentService(priceFeed)` — no NestJS testing module needed.
- **`makeInput()` helper** in threshold-evaluator spec: accepts `Partial<ThresholdEvalInput>` overrides. Entry cost baseline fields are injected as top-level properties (`entryClosePriceKalshi`, `entryClosePricePolymarket`, `entryKalshiFeeRate`, `entryPolymarketFeeRate`).
- **`createMockPosition()` helper** in enrichment spec: accepts `Record<string, unknown>` overrides. Entry close prices injected as objects with `toString()` method: `{ toString: () => '0.53' }`.
- **`createMockPriceFeed()`** in enrichment spec: provides `getCurrentClosePrice` and `getTakerFeeRate` as `vi.fn()`.
- **Existing tests that will need updating** (their expected threshold values change):
  - `threshold-evaluator.service.spec.ts`: "should use zero spread when close prices equal fill prices" (TP was -0.14), "should handle Kalshi dynamic fee at different entry price tier" (TP was -1.135)
  - `position-enrichment.service.spec.ts`: "offsets exit proximity with entry cost baseline" (TP threshold was -5.04), "P&L at TP threshold with non-zero baseline" (threshold was -1.04)

### Proximity Formula Impact

The enrichment service's TP proximity formula: `clamp(0, 1, (currentPnl - baseline) / (tpThreshold - baseline))`

With the journey formula, `tpThreshold` will always be >= 0, and `baseline` is always <= 0, so `tpThreshold - baseline` will always be positive (no division-by-zero risk unless both are exactly 0, which is already guarded). The proximity semantics remain correct: 0 = at baseline (just opened), 1 = at TP threshold.

### Previous Story Intelligence (6.5.5i)

- Used strict TDD throughout — follow same pattern
- All financial math via `decimal.js` — confirmed working
- `computeEntryCostBaseline()` in `financial-math.ts` handles nullable fields with zero-fallback — this utility is unchanged
- Entry close prices stored as nullable Prisma Decimal on OpenPosition model — convert via `new Decimal(value.toString())`
- `legSize = kalshiSize` convention established in 6.5.5h, used throughout
- Total test count after 6.5.5i: ~1,398

### Project Structure Notes

- Both modified source files are in their correct module locations per architecture
- No new files created — only modifications to existing files
- Change is additive constraint (floor) — no existing correct behavior removed

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-05-tp-negative-threshold.md] — Approved change proposal with full analysis
- [Source: _bmad-output/implementation-artifacts/6-5-5i-exit-threshold-calibration-fix.md] — Previous story that introduced the flawed formula
- [Source: _bmad-output/implementation-artifacts/7-5-exit-proximity-display-fix.md] — Dashboard proximity fix (code remains correct)
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:158-170] — TP threshold formula to fix
- [Source: pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts:211-213] — Mirror formula to fix
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts:131-202] — computeEntryCostBaseline utility (unchanged)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
N/A — clean implementation, no debugging needed.

### Completion Notes List
- Strict TDD: wrote 6 new failing tests (4 threshold-evaluator, 2 enrichment) before implementing formula change
- Formula change is 2 lines in each service: `Decimal.max(0, entryCostBaseline.plus(scaledInitialEdge.minus(entryCostBaseline).mul(new Decimal('0.80'))))`
- Updated 4 existing tests whose expected values changed (2 threshold-evaluator, 2 enrichment)
- AC6 differentiator test: PnL=1.80 between old threshold (1.40) and new threshold (2.20) — only triggers with old formula
- AC5 enrichment test: validates TP proximity = 0.95 when floor activates (baseline=-20, threshold=0, currentPnl=-1.0)
- Lad MCP review: both reviewers confirmed formula correctness. Formula duplication concern noted but extraction explicitly deferred per story scope.
- All 1410 tests pass (6 new tests added). 0 lint errors.

### File List
- `pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts` — TP formula updated (lines 158-165)
- `pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.spec.ts` — 4 new tests + 2 updated tests
- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts` — TP formula updated (lines 211-217)
- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.spec.ts` — 2 new tests + 2 updated tests
- `_bmad-output/implementation-artifacts/6-5-5i-exit-threshold-calibration-fix.md` — Supersession note appended
