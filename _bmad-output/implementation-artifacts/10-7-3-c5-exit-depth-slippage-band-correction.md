# Story 10.7.3: C5 Exit Depth Slippage Band Correction

Status: done

## Story

As an operator,
I want the C5 liquidity_deterioration criterion to count depth within a configurable slippage band around VWAP,
so that the depth metric doesn't systematically understate executable liquidity.

## Context

**Root cause:** `getClosePrice()` (exit-monitor.service.ts:1395-1417) delegates to `calculateVwapClosePrice()` which walks the full order book, blending prices across multiple levels into a VWAP. Then `getAvailableExitDepth()` (exit-monitor.service.ts:1268-1293) uses that VWAP as a **hard price cutoff**, only counting levels at VWAP or better. This excludes the very liquidity that produced the VWAP — a circularity.

**Impact:** C5 fired on 93.4% of exits with detail `"Min depth 1 vs required 5"`. Only the single best-level quantity (typically 1 contract) passed the strict VWAP cutoff, while the rest of the fillable book was excluded.

**Fix:** Add a configurable tolerance band (`EXIT_DEPTH_SLIPPAGE_TOLERANCE`, default 2%) so the price cutoff includes levels slightly beyond VWAP. Value of 0.0 restores original strict behavior.

**Depends on:** 10-7-2 (completed — introduced `calculateVwapWithFillInfo()` and VWAP-based edge calculation).

## Acceptance Criteria

1. **AC-1: Tolerance band applied to depth cutoff**
   - **Given** a position is being evaluated for exit by the C5 criterion
   - **When** `getAvailableExitDepth()` computes available depth
   - **Then** for buy-close (consuming asks): price cutoff = `closePrice × (1 + EXIT_DEPTH_SLIPPAGE_TOLERANCE)`
   - **And** for sell-close (consuming bids): price cutoff = `closePrice × (1 - EXIT_DEPTH_SLIPPAGE_TOLERANCE)`
   - **And** levels at prices within the tolerance band are included in the depth count
   - **And** levels beyond the tolerance band are excluded

2. **AC-2: Configurable via EngineConfig DB**
   - **Given** the configuration
   - **When** the engine starts
   - **Then** `EXIT_DEPTH_SLIPPAGE_TOLERANCE` is loaded from EngineConfig DB (default: 0.02)
   - **And** the setting appears in the dashboard Settings page under "Exit Strategy" group
   - **And** hot-reload works via the `CONFIG_SETTINGS_UPDATED` event

3. **AC-3: Backward compatibility at zero tolerance**
   - **Given** `EXIT_DEPTH_SLIPPAGE_TOLERANCE` is set to 0.0
   - **When** depth is computed
   - **Then** behavior is identical to pre-story strict-VWAP cutoff (no band expansion)

## Tasks / Subtasks

- [x] **Task 1: Add `EXIT_DEPTH_SLIPPAGE_TOLERANCE` config setting** (AC: #2)
  - [x] 1.1 Add to `src/common/config/env.schema.ts` — `EXIT_DEPTH_SLIPPAGE_TOLERANCE: z.coerce.number().min(0).max(1).default(0.02)` (adjacent to `EXIT_MIN_DEPTH` at line 264)
  - [x] 1.2 Add to `src/common/config/config-defaults.ts` — `exitDepthSlippageTolerance: { envKey: 'EXIT_DEPTH_SLIPPAGE_TOLERANCE', defaultValue: 0.02 }` (after `exitMinDepth` at line 288)
  - [x] 1.3 Add to `src/common/config/settings-metadata.ts` — group: `SettingsGroup.ExitStrategy`, type: `'decimal'`, label: `'Exit Depth Slippage Tolerance'`, description: `'Fraction of VWAP close price to expand depth cutoff. 0 = strict VWAP, 0.02 = 2% band.'`, min: 0, max: 1. Place after `exitMinDepth` entry (after line 703)
  - [x] 1.4 Add to `src/dashboard/dto/update-settings.dto.ts` — `@IsOptional() @IsNumber() @Min(0) @Max(1) exitDepthSlippageTolerance?: number;` (after `exitMinDepth` field at line 401)
  - [x] 1.5 Add to `src/common/config/effective-config.types.ts` — `exitDepthSlippageTolerance: number;` (after `exitMinDepth` at line 128)
  - [x] 1.6 Add column to Prisma `EngineConfig` model in `prisma/schema.prisma` — `exitDepthSlippageTolerance Float? @map("exit_depth_slippage_tolerance")` (after `exitMinDepth` at line 137)
  - [x] 1.7 Create Prisma migration: `pnpm prisma migrate dev --name add-exit-depth-slippage-tolerance`
  - [x] 1.8 Add to `src/persistence/repositories/engine-config.repository.ts` resolve chain — `exitDepthSlippageTolerance: resolve('exitDepthSlippageTolerance') as number,` (after `exitMinDepth` at line 181)

- [x] **Task 2: Wire config into ExitMonitorService** (AC: #2)
  - [x] 2.1 Add `private exitDepthSlippageTolerance: number` field (after `exitMinDepth` at line 68)
  - [x] 2.2 Initialize in constructor: `this.exitDepthSlippageTolerance = this.configService.get<number>('EXIT_DEPTH_SLIPPAGE_TOLERANCE', 0.02);` (after `exitMinDepth` init at line 118)
  - [x] 2.3 Add `exitDepthSlippageTolerance?: number` to `reloadConfig()` settings parameter (after `exitMinDepth` at line 136)
  - [x] 2.4 Add reload handler: `if (settings.exitDepthSlippageTolerance !== undefined) this.exitDepthSlippageTolerance = settings.exitDepthSlippageTolerance;` (after `exitMinDepth` handler at line 157)

- [x] **Task 3: Wire hot-reload in settings.service.ts** (AC: #2)
  - [x] 3.1 Add `exitDepthSlippageTolerance: ['exit-monitor']` to `SERVICE_RELOAD_MAP` (after `exitMinDepth` at line 96)
  - [x] 3.2 Add `exitDepthSlippageTolerance: cfg.exitDepthSlippageTolerance` to the exit-monitor reload handler call (after `exitMinDepth` at line 165)

- [x] **Task 4: Modify `getAvailableExitDepth()` to apply tolerance band** (AC: #1, #3)
  - [x] 4.1 Add `slippageTolerance: number` parameter to `getAvailableExitDepth()` signature (after `closePrice`)
  - [x] 4.2 Compute adjusted cutoff at the top of the method:
    ```typescript
    // Apply slippage tolerance band (Story 10-7-3)
    // Buy-close (asks): accept prices up to closePrice × (1 + tolerance)
    // Sell-close (bids): accept prices down to closePrice × (1 - tolerance)
    const toleranceFraction = closeSide === 'buy'
      ? new Decimal(1).plus(slippageTolerance)
      : new Decimal(1).minus(slippageTolerance);
    const adjustedCutoff = closePrice.mul(toleranceFraction);
    ```
  - [x] 4.3 Replace `closePrice` with `adjustedCutoff` in the price comparison:
    ```typescript
    const priceOk =
      closeSide === 'buy'
        ? level.price <= adjustedCutoff.toNumber()
        : level.price >= adjustedCutoff.toNumber();
    ```
  - [x] 4.4 Update both call sites in `evaluatePosition()` (lines ~587-598) to pass `this.exitDepthSlippageTolerance`:
    ```typescript
    this.getAvailableExitDepth(
      this.kalshiConnector,
      position.pair.kalshiContractId,
      kalshiCloseSide,
      kalshiClosePrice,
      this.exitDepthSlippageTolerance,
    ),
    ```

- [x] **Task 5: Write unit tests for tolerance band** (AC: #1, #3)
  - [x] 5.1 Test: buy-close with 2% tolerance includes ask levels within band (e.g., VWAP=0.50, 2% band → accept asks up to 0.51)
  - [x] 5.2 Test: sell-close with 2% tolerance includes bid levels within band (e.g., VWAP=0.60, 2% band → accept bids down to 0.588)
  - [x] 5.3 Test: levels beyond the tolerance band are excluded
  - [x] 5.4 Test: tolerance=0.0 restores strict-VWAP behavior (no extra levels included)
  - [x] 5.5 Test: empty order book returns zero depth (unchanged behavior)
  - [x] 5.6 Test: all levels within band accumulates total depth correctly
  - [x] 5.7 Integration test: full evaluatePositions() cycle with tolerance — C5 does NOT trigger when sufficient depth exists within band
  - [x] 5.8 Integration test: C5 still triggers when depth is insufficient even with tolerance band

- [x] **Task 6: Update settings count test** (AC: #2)
  - [x] 6.1 Update `src/dashboard/settings.service.spec.ts` line 243: `expect(allSettings.length).toBe(74)` (was 73)

- [x] **Task 7: Update config-defaults spec** (AC: #2)
  - [x] 7.1 Add `'exitDepthSlippageTolerance'` to the ordered key list in `src/common/config/config-defaults.spec.ts` (after `'exitMinDepth'` at line 108)
  - [x] 7.2 Add `exitDepthSlippageTolerance: 'EXIT_DEPTH_SLIPPAGE_TOLERANCE'` to the envKey mapping (after `exitMinDepth` at line 185)
  - [x] 7.3 Add `'exitDepthSlippageTolerance'` to the ordered keys array (after `'exitMinDepth'` at line 393)

- [x] **Task 8: Update config-accessor spec** (AC: #2)
  - [x] 8.1 Add `exitDepthSlippageTolerance: 0.02` to `buildMockEffectiveConfig()` in `src/common/config/config-accessor.service.spec.ts` (after `exitMinDepth: 5` at line 82)

## Dev Notes

### Architecture Compliance

- **Module dependency rules:** `getAvailableExitDepth()` is a private method of ExitMonitorService — all changes are internal to the exit-management module. No new cross-module imports needed.
- **Error hierarchy:** No new errors thrown. The tolerance band is purely a filter adjustment. If `slippageTolerance` is negative (shouldn't happen due to env.schema validation), the band contracts — safe degradation.
- **Financial math:** The tolerance multiplication uses `Decimal` arithmetic (`.mul()`, `.plus()`, `.minus()`). `closePrice` is already `Decimal`. The `adjustedCutoff` comparison uses `.toNumber()` only for the final `level.price` comparison (level.price is already `number` in `NormalizedOrderBook`).
- **Hot path:** Exit evaluation is NOT in the detection → risk → execution hot path. It runs on a 30-second polling cycle. The added multiplication is O(1) — negligible overhead.

### The VWAP Circularity Problem (Why This Fix Works)

`getClosePrice()` calls `calculateVwapClosePrice()` which produces a VWAP by walking multiple price levels. Example:

```
Book asks: [0.50 × 1], [0.52 × 10], [0.55 × 20]
VWAP for 10 contracts = (0.50×1 + 0.52×9) / 10 = 0.518
```

Without tolerance: `getAvailableExitDepth(cutoff=0.518)` counts only the 0.50 level → depth = 1.
With 2% tolerance: cutoff = 0.518 × 1.02 = 0.528 → includes 0.50 (1) + 0.52 (10) → depth = 11.

The tolerance captures the bulk of the book that actually produced the VWAP.

### Source Tree — Files to Modify

| File | Change |
|------|--------|
| `src/common/config/env.schema.ts` | Add `EXIT_DEPTH_SLIPPAGE_TOLERANCE` validator |
| `src/common/config/config-defaults.ts` | Add `exitDepthSlippageTolerance` entry |
| `src/common/config/config-defaults.spec.ts` | Add to key list, envKey mapping, ordered keys |
| `src/common/config/settings-metadata.ts` | Add metadata under Exit Strategy group |
| `src/common/config/effective-config.types.ts` | Add `exitDepthSlippageTolerance: number` |
| `src/common/config/config-accessor.service.spec.ts` | Add to mock effective config |
| `src/dashboard/dto/update-settings.dto.ts` | Add DTO field with validators |
| `src/dashboard/settings.service.ts` | Add to SERVICE_RELOAD_MAP + exit-monitor handler |
| `src/dashboard/settings.service.spec.ts` | Settings count 73→74 |
| `src/persistence/repositories/engine-config.repository.ts` | Add to resolve chain |
| `prisma/schema.prisma` | Add column to EngineConfig |
| `src/modules/exit-management/exit-monitor.service.ts` | Add field, constructor init, reloadConfig, modify `getAvailableExitDepth()`, update call sites |
| `src/modules/exit-management/exit-monitor-depth-check.spec.ts` | New tolerance band tests |

### Source Tree — Files to Read (Reference Only)

| File | Why |
|------|-----|
| `src/modules/exit-management/exit-monitor.test-helpers.ts` | Test module setup and mock factories |
| `src/modules/exit-management/threshold-evaluator.service.ts` | C5 `evaluateLiquidityDeterioration()` — NOT modified, just consumes depth output |
| `src/common/types/exit-criteria.types.ts` | `CriterionResult` type, criterion priority |
| `src/common/constants/exit-thresholds.ts` | `EXIT_MIN_DEPTH_DEFAULT` constant |

### Key Code Patterns to Follow

**Config field initialization pattern (exit-monitor.service.ts:118):**
```typescript
this.exitMinDepth = this.configService.get<number>('EXIT_MIN_DEPTH', 5);
```
Follow identical pattern for `exitDepthSlippageTolerance`.

**Reload handler pattern (exit-monitor.service.ts:156-157):**
```typescript
if (settings.exitMinDepth !== undefined)
  this.exitMinDepth = settings.exitMinDepth;
```
Follow identical pattern for `exitDepthSlippageTolerance`.

**SERVICE_RELOAD_MAP pattern (settings.service.ts:96):**
```typescript
exitMinDepth: ['exit-monitor'],
```
Follow identical pattern for `exitDepthSlippageTolerance`.

**Settings metadata pattern (settings-metadata.ts:696-703):**
```typescript
exitMinDepth: {
  group: SettingsGroup.ExitStrategy,
  label: 'Min Exit Depth',
  description: 'Minimum orderbook depth required to execute exit.',
  type: 'integer',
  envDefault: CONFIG_DEFAULTS.exitMinDepth.defaultValue,
  min: 0,
},
```
Follow same structure but with `type: 'decimal'`, `min: 0`, `max: 1`.

**Test factory pattern (exit-monitor-depth-check.spec.ts):**
Tests use `createExitMonitorTestModule()` from test-helpers with mock connectors. Override `getOrderBook` mock returns to control book shape. Follow same mock setup patterns.

### What NOT To Do

- Do NOT modify `ThresholdEvaluatorService.evaluateLiquidityDeterioration()` — C5 consumes the depth value produced by `getAvailableExitDepth()`. The fix is entirely in how depth is measured, not how C5 evaluates it.
- Do NOT modify `getClosePrice()` — the VWAP calculation is correct. The problem is only in how the VWAP is used as a cutoff.
- Do NOT use `Decimal` for `exitDepthSlippageTolerance` storage — it's a `number` (consistent with all other exit config fields like `exitMinDepth`, `exitProfitCaptureRatio`). Only convert to `Decimal` for the multiplication in `getAvailableExitDepth()`.
- Do NOT add a new constant to `exit-thresholds.ts` — this setting is runtime-configurable via EngineConfig DB, not a compile-time constant.
- Do NOT use `FinancialDecimal` for the tolerance multiplication — `Decimal` is sufficient. `FinancialDecimal` is for monetary calculations where precision is critical. This is a dimensionless ratio multiplication.

### Previous Story Intelligence (10-7-2)

From 10-7-2 implementation:
- **Config pipeline pattern** is well-established: env.schema → config-defaults → settings-metadata → DTO → Prisma → effective-config → repository → settings.service reload map + handler. Follow exactly.
- **Settings count test** needs incrementing (currently 73, update to 74).
- **config-defaults.spec.ts** has three places to update: ordered key list, envKey mapping, and ordered keys array.
- **config-accessor.service.spec.ts** has a `buildMockEffectiveConfig()` helper that must include the new field.

### Testing Standards

- Co-located tests: `exit-monitor-depth-check.spec.ts` (existing file for depth tests)
- Framework: Vitest (NOT Jest) — use `vi.fn()`, `vi.spyOn()`, `describe`, `it`, `expect`
- Assertion depth: verify depth values with exact `Decimal` comparison — not just boolean triggered/not
- Event wiring: no new `@OnEvent` handlers → no `expectEventHandled()` tests needed
- Paper/live boundary: tolerance applies identically in both modes (depth calculation is mode-agnostic) → no boundary tests needed
- Collection lifecycle: no new Maps/Sets → no cleanup tests needed

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10-7-3] — Acceptance criteria
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts#getAvailableExitDepth] — Current strict-VWAP cutoff (lines 1268-1293)
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts#getClosePrice] — VWAP close price computation (lines 1395-1417)
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts#evaluateLiquidityDeterioration] — C5 criterion (lines 449-480)
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts#calculateVwapClosePrice] — Shared VWAP utility (lines 288-295)
- [Source: pm-arbitrage-engine/src/dashboard/settings.service.ts#SERVICE_RELOAD_MAP] — Hot-reload dispatch (lines 69-98)
- [Source: _bmad-output/implementation-artifacts/10-7-2-vwap-slippage-aware-edge-calculation.md] — Config pipeline pattern, previous story learnings
- [Source: CLAUDE.md#Architecture] — Module dependency rules, financial math, error handling
- [Source: CLAUDE.md#Testing] — Assertion depth, event wiring, co-located tests

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- seed-config.ts required adding `exitDepthSlippageTolerance` to `FLOAT_FIELDS` (Prisma Float, not Decimal) — missed in original story spec
- Integration tests needed `exitMode: 'model'` and `contractMatch.findUnique` mock — depth fetch is gated by model/shadow exit mode
- config-defaults.spec.ts count assertion updated 71→72 (CATEGORY_B_FIELDS minus bankrollUsd/paperBankrollUsd)

### Post-Review Fixes (Code Review 2026-03-23)

3-layer adversarial review (Blind Hunter + Edge Case Hunter + Acceptance Auditor), 26 raw findings triaged to 0 patch + 4 defer + 22 reject. Two deferred items fixed post-triage:

- **D1 (Decimal precision):** Replaced `adjustedCutoff.toNumber()` comparison with `new Decimal(level.price).lte(adjustedCutoff)` / `.gte()` in `getAvailableExitDepth()`. Keeps full Decimal precision chain instead of converting to native float at the comparison boundary.
- **D4 (quantity guard):** Added `level.quantity > 0` check inside the price-ok branch of `getAvailableExitDepth()`. Defensive guard against zero/negative quantities from malformed connector data. Nested inside `priceOk` to preserve the sorted-book early-break logic. Added 1 new unit test.
- **D2/D3 (God Object):** Deferred to Epic 10.8 story 10-8-2 (ExitMonitorService decomposition). File is ~1465 lines with 9 constructor deps.

### Completion Notes List

- AC-1: Tolerance band applied — buy-close uses `closePrice × (1 + tolerance)`, sell-close uses `closePrice × (1 - tolerance)` as cutoff
- AC-2: Full config pipeline wired — env.schema, config-defaults, settings-metadata, DTO, effective-config types, Prisma schema+migration, repository, SERVICE_RELOAD_MAP, ExitMonitorService field+constructor+reloadConfig
- AC-3: tolerance=0.0 produces strict-VWAP behavior — verified by unit test
- 10 new tests (7 unit + 1 hot-reload + 2 integration), all passing
- Total: 2685 tests pass (up from 2675 baseline), 154 test files, 0 errors

### File List

- `src/common/config/env.schema.ts` — Added EXIT_DEPTH_SLIPPAGE_TOLERANCE validator
- `src/common/config/config-defaults.ts` — Added exitDepthSlippageTolerance entry
- `src/common/config/config-defaults.spec.ts` — Added to key list, envKey mapping, ordered keys, count 71→72
- `src/common/config/settings-metadata.ts` — Added metadata under Exit Strategy group
- `src/common/config/effective-config.types.ts` — Added exitDepthSlippageTolerance: number
- `src/common/config/config-accessor.service.spec.ts` — Added to mock effective config
- `src/dashboard/dto/update-settings.dto.ts` — Added DTO field with validators
- `src/dashboard/settings.service.ts` — Added to SERVICE_RELOAD_MAP + exit-monitor handler
- `src/dashboard/settings.service.spec.ts` — Settings count 73→74
- `src/persistence/repositories/engine-config.repository.ts` — Added to resolve chain
- `prisma/schema.prisma` — Added exitDepthSlippageTolerance Float? column
- `prisma/migrations/20260323204957_add_exit_depth_slippage_tolerance/migration.sql` — Migration
- `prisma/seed-config.ts` — Added to FLOAT_FIELDS
- `prisma/seed-config.spec.ts` — Added to mock row
- `src/modules/exit-management/exit-monitor.service.ts` — Added field, constructor init, reloadConfig, modified getAvailableExitDepth() with tolerance band, updated 4 call sites. Post-review: replaced `.toNumber()` comparison with full Decimal precision (`new Decimal(level.price).lte()/gte()`), added `quantity > 0` guard against malformed connector data
- `src/modules/exit-management/exit-monitor-depth-check.spec.ts` — Added 10 new tests (7 tolerance band unit + 1 hot-reload + 2 integration)
