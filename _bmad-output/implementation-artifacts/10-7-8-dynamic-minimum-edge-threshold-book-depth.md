# Story 10-7.8: Dynamic Minimum Edge Threshold Based on Book Depth

Status: done

## Story

As an operator,
I want the minimum edge threshold to scale dynamically with order book depth,
So that higher edges are demanded for illiquid markets and positions are not entered at thin-book edges that collapse on execution.

## Context

Positions entering at 1.5-2% edge are underwater after slippage on thin books. Story 10-7-2 introduced VWAP-based edge calculation, which accurately prices slippage into the edge. However, the static 0.8% minimum threshold treats all markets equally — a 1% edge on a 5-contract-deep book is fundamentally riskier than a 1% edge on a 500-contract-deep book. This story adds depth-sensitive scaling so the system demands proportionally more edge when liquidity is thin.

**Dependencies:** 10-7-2 (VWAP edge calculation — already implemented). Builds on the VWAP fill results that already expose `totalQtyAvailable` per leg.

## Acceptance Criteria

1. **AC-1: Dynamic threshold formula.** Given an opportunity passes the base minimum edge threshold (0.8%), when the effective threshold is calculated, then `effectiveMinEdge = baseMinEdge × (1 + DEPTH_EDGE_SCALING_FACTOR / min(buyTotalDepth, sellTotalDepth))`, where `buyTotalDepth` = `buyVwapResult.totalQtyAvailable` (asks on buy platform) and `sellTotalDepth` = `sellVwapResult.totalQtyAvailable` (bids on sell platform). The result is capped at `MAX_DYNAMIC_EDGE_THRESHOLD` (default: 0.05 = 5%). All arithmetic uses `decimal.js`.

2. **AC-2: Deep liquidity convergence.** Given deeply liquid markets (e.g., depth > 1000 contracts), when the threshold is calculated, then it converges to the base minimum (scaling term approaches zero, no meaningful penalty).

3. **AC-3: Backward compatibility.** Given configuration, when `DEPTH_EDGE_SCALING_FACTOR` is set to 0, then `effectiveMinEdge = baseMinEdge × (1 + 0) = baseMinEdge` — dynamic scaling is disabled and behavior matches pre-story static threshold.

4. **AC-4: Config pipeline.** Both `DEPTH_EDGE_SCALING_FACTOR` (default: 10, type: decimal) and `MAX_DYNAMIC_EDGE_THRESHOLD` (default: 0.05, type: decimal) are registered through the full config pipeline (env.schema → config-defaults → settings-metadata → effective-config → Prisma → repository → DTO → settings.service) and appear in the dashboard Settings page under "Detection & Edge" group. Hot-reload via `CONFIG_SETTINGS_UPDATED` event.

5. **AC-5: Observability.** When an opportunity is filtered by the dynamic threshold, the `OpportunityFilteredEvent` and `FilteredDislocation` carry the dynamically-computed `threshold` value (not the static base). When an opportunity passes, `EnrichedOpportunity` includes `effectiveMinEdge: Decimal` so the dashboard and audit logs show the threshold that was applied. `OpportunityIdentifiedEvent` payload includes `effectiveMinEdge: number`.

6. **AC-6: Degradation multiplier interaction.** The dynamic threshold is computed first, capped, and then the degradation multiplier is applied on top: `finalThreshold = min(dynamicThreshold, maxCap) × degradationMultiplier`. This preserves the degradation protocol's ability to widen thresholds during platform health issues.

7. **AC-7: Startup validation.** `onModuleInit()` validates both config values: `DEPTH_EDGE_SCALING_FACTOR >= 0` (zero allowed for disable), `MAX_DYNAMIC_EDGE_THRESHOLD > 0 and <= 1.0`. Invalid values throw `ConfigValidationError`.

## Tasks / Subtasks

- [x] Task 1: Config pipeline — add 2 new settings (AC: #4, #7)
  - [x] 1.1 `env.schema.ts` — add `DEPTH_EDGE_SCALING_FACTOR: decimalString('10')` and `MAX_DYNAMIC_EDGE_THRESHOLD: decimalString('0.05')` in the Detection Depth section
  - [x] 1.2 `config-defaults.ts` — add `depthEdgeScalingFactor: { envKey: 'DEPTH_EDGE_SCALING_FACTOR', defaultValue: '10' }` and `maxDynamicEdgeThreshold: { envKey: 'MAX_DYNAMIC_EDGE_THRESHOLD', defaultValue: '0.05' }` under Detection Depth section
  - [x] 1.3 `settings-metadata.ts` — add both to `SettingsGroup.DetectionEdge` with label, description, type: 'decimal', envDefault. `depthEdgeScalingFactor` min: 0. `maxDynamicEdgeThreshold` min: 0.001, max: 1.0
  - [x] 1.4 `effective-config.types.ts` — add `depthEdgeScalingFactor: string` and `maxDynamicEdgeThreshold: string` under Edge Detection section
  - [x] 1.5 `prisma/schema.prisma` — add `depthEdgeScalingFactor Decimal? @map("depth_edge_scaling_factor") @db.Decimal(20, 8)` and `maxDynamicEdgeThreshold Decimal? @map("max_dynamic_edge_threshold") @db.Decimal(20, 8)` to EngineConfig model
  - [x] 1.6 Run `pnpm prisma migrate dev --name add-dynamic-edge-threshold`
  - [x] 1.7 `engine-config.repository.ts` — add both fields to the `resolve()` chain in `getEffectiveConfig()`
  - [x] 1.8 `update-settings.dto.ts` — add both as optional `@IsString() @Matches(DECIMAL_REGEX)` fields
  - [x] 1.9 `settings.service.ts` — extend the `'detection'` reload handler to pass `depthEdgeScalingFactor` and `maxDynamicEdgeThreshold` from cfg to `svc.reloadConfig()`
  - [x] 1.10 Update settings count test in `config-defaults.spec.ts` from 76 → 78

- [x] Task 2: EdgeCalculatorService — dynamic threshold logic (AC: #1, #2, #3, #6, #7)
  - [x] 2.1 Add private instance fields: `depthEdgeScalingFactor: Decimal` (init from config) and `maxDynamicEdgeThreshold: Decimal` (init from config)
  - [x] 2.2 Add `validateDepthEdgeScalingFactor()` and `validateMaxDynamicEdgeThreshold()` private methods, call from `onModuleInit()`
  - [x] 2.3 Extend `reloadConfig()` signature to accept `depthEdgeScalingFactor?: string` and `maxDynamicEdgeThreshold?: string`, with validation + Decimal conversion
  - [x] 2.4 Add private method `computeDynamicThreshold(minDepth: Decimal): Decimal` implementing the formula: `baseMinEdge.mul(new FinancialDecimal(1).plus(this.depthEdgeScalingFactor.div(minDepth)))` capped at `this.maxDynamicEdgeThreshold`
  - [x] 2.5 In `processSingleDislocation()`, after VWAP computation and before threshold filtering: compute `minDepth = Decimal.min(buyVwapResult.totalQtyAvailable, sellVwapResult.totalQtyAvailable)`. If `depthEdgeScalingFactor > 0` and `minDepth > 0`, call `computeDynamicThreshold(minDepth)` to get `dynamicBase`. Then: `effectiveThreshold = dynamicBase.mul(multiplier)`. If scaling factor is 0, fall through to existing static behavior. Log both base and dynamic thresholds in debug output.
  - [x] 2.6 Guard: if `minDepth` is zero, treat as static threshold (no division by zero)

- [x] Task 3: Type extensions for observability (AC: #5)
  - [x] 3.1 `enriched-opportunity.type.ts` — add `effectiveMinEdge: Decimal` to `EnrichedOpportunity` interface
  - [x] 3.2 In `processSingleDislocation()`, populate `effectiveMinEdge` in the `EnrichedOpportunity` object
  - [x] 3.3 In `OpportunityIdentifiedEvent` emission, add `effectiveMinEdge: effectiveThreshold.toNumber()` to the opportunity payload
  - [x] 3.4 `FilteredDislocation.threshold` already carries the effective threshold string — confirmed it receives the dynamic value

- [x] Task 4: Tests (AC: #1-7)
  - [x] 4.1 Dynamic threshold calculation: base case (scalingFactor=10, depth=5 → effectiveMinEdge = 0.008 × 3 = 0.024)
  - [x] 4.2 Deep liquidity convergence: depth=10000 → effectiveMinEdge ≈ 0.008 (scaling term negligible)
  - [x] 4.3 Backward compatibility: scalingFactor=0 → effectiveMinEdge = baseMinEdge exactly
  - [x] 4.4 Max cap enforcement: very thin book (depth=1) → capped at MAX_DYNAMIC_EDGE_THRESHOLD (0.05)
  - [x] 4.5 Asymmetric depth: buyDepth=10000, sellDepth=200 → uses min(10000,200)=200
  - [x] 4.6 Degradation multiplier interaction: dynamic threshold × degradation multiplier
  - [x] 4.7 Opportunity that passes static threshold but fails dynamic threshold is filtered with correct reason and dynamic threshold value
  - [x] 4.8 Opportunity that passes dynamic threshold includes `effectiveMinEdge` in enriched output
  - [x] 4.9 Config validation: negative scalingFactor throws ConfigValidationError
  - [x] 4.10 Config validation: maxDynamicEdgeThreshold > 1.0 throws ConfigValidationError
  - [x] 4.11 Config validation: maxDynamicEdgeThreshold = 0 throws ConfigValidationError
  - [x] 4.12 Hot-reload: reloadConfig updates depthEdgeScalingFactor and maxDynamicEdgeThreshold
  - [x] 4.13 Hot-reload: invalid values logged as warning, current values preserved
  - [x] 4.14 Paper/live mode boundary: dynamic threshold applies identically in both modes (no mode-dependent branching added)

## Dev Notes

### Architecture & Insertion Point

The core change is in `EdgeCalculatorService.processSingleDislocation()` (612 lines, `src/modules/arbitrage-detection/edge-calculator.service.ts`). The insertion point is between VWAP net edge computation (line ~303) and threshold filtering (line ~315):

```
Current flow:
  VWAP computation → bestLevelNetEdge → vwapNetEdge → threshold filter → capital efficiency → enrich

New flow:
  VWAP computation → bestLevelNetEdge → vwapNetEdge → [DYNAMIC THRESHOLD] → threshold filter → capital efficiency → enrich
```

The dynamic threshold replaces the static `this.minEdgeThreshold` in the existing threshold filter block. The existing `effectiveThreshold` variable (line ~320) should be computed from the dynamic base instead of the static base.

### Depth Data Source

Use `buyVwapResult.totalQtyAvailable` and `sellVwapResult.totalQtyAvailable` from the VWAP computation (already available at the insertion point, computed at line ~245). These represent fillable-side depth: asks on the buy platform, bids on the sell platform — exactly the depth that determines execution quality.

Do NOT use `buildLiquidityDepth()` output (computed later at line ~374) — it would require reordering and is semantically the same data.

### Formula Implementation

```typescript
// In computeDynamicThreshold():
const scalingTerm = this.depthEdgeScalingFactor.div(minDepth);
const dynamicBase = this.minEdgeThreshold.mul(new FinancialDecimal(1).plus(scalingTerm));
return Decimal.min(dynamicBase, this.maxDynamicEdgeThreshold);
```

All arithmetic MUST use `decimal.js` — never native JS operators on these values.

### Config Pipeline Pattern

Follow the exact pattern from story 10-7-2 (`DETECTION_MIN_FILL_RATIO`). The pipeline is:

1. `env.schema.ts` — Zod validation with `decimalString()` helper
2. `config-defaults.ts` — `{ envKey, defaultValue }` entry
3. `settings-metadata.ts` — `{ group, label, description, type, envDefault }` entry
4. `effective-config.types.ts` — typed field
5. `prisma/schema.prisma` — nullable Decimal column on EngineConfig
6. Prisma migration
7. `engine-config.repository.ts` — `resolve()` in `getEffectiveConfig()`
8. `update-settings.dto.ts` — DTO with `@IsOptional() @IsString() @Matches(DECIMAL_REGEX)`
9. `settings.service.ts` — pass to `svc.reloadConfig()` in the `'detection'` handler

The `'detection'` handler in `settings.service.ts` (line ~173) already calls `EdgeCalculatorService.reloadConfig()` — extend the object passed to include the 2 new fields.

### Instance Fields vs Getters

`detectionMinFillRatio` uses a private instance field (set in `onModuleInit`, updated in `reloadConfig`). Follow the same pattern for `depthEdgeScalingFactor` and `maxDynamicEdgeThreshold`. Do NOT use config getters (like `minEdgeThreshold` getter) — instance fields enable hot-reload.

However, `minEdgeThreshold` itself is a getter that reads from `configService` on every call (line ~127). This is fine for the base threshold since it comes from env vars (not DB-backed). The dynamic settings are DB-backed and must use the instance field pattern.

### Event Payloads

- `OpportunityFilteredEvent` constructor takes `threshold: Decimal` — pass the dynamic `effectiveThreshold` (already the case since the existing code uses `effectiveThreshold` variable)
- `OpportunityIdentifiedEvent` takes `Record<string, unknown>` — add `effectiveMinEdge: effectiveThreshold.toNumber()` to the object literal
- `FilteredDislocation` has `threshold: string` — already receives `effectiveThreshold.toString()` (line ~328)

### Testing Patterns

- Framework: **Vitest** (not Jest)
- Co-located: `edge-calculator.service.spec.ts` in same directory
- Use `expect.objectContaining({...})` for event payload verification
- Use `FinancialDecimal` for test assertions on Decimal values
- Mock `configService.get()` for the 2 new env vars
- The existing test factory `makeDislocation()` builds order books — use default (10000 quantity) for deep-book tests, override with small books for thin-book tests
- Settings count test: `config-defaults.spec.ts` line ~209 currently expects 76 → update to 78

### Files to Modify

| # | File | Change |
|---|------|--------|
| 1 | `src/common/config/env.schema.ts` | +2 env var definitions |
| 2 | `src/common/config/config-defaults.ts` | +2 config default entries |
| 3 | `src/common/config/settings-metadata.ts` | +2 settings metadata entries |
| 4 | `src/common/config/effective-config.types.ts` | +2 typed fields |
| 5 | `prisma/schema.prisma` | +2 columns on EngineConfig |
| 6 | `prisma/migrations/*/migration.sql` | Auto-generated migration |
| 7 | `src/persistence/repositories/engine-config.repository.ts` | +2 resolve entries |
| 8 | `src/dashboard/dto/update-settings.dto.ts` | +2 DTO fields |
| 9 | `src/dashboard/settings.service.ts` | Extend detection reload handler |
| 10 | `src/modules/arbitrage-detection/edge-calculator.service.ts` | Core dynamic threshold logic |
| 11 | `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts` | +1 field (`effectiveMinEdge`) |
| 12 | `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` | ~14 new tests |
| 13 | `src/common/config/config-defaults.spec.ts` | Settings count 76→78 |

### Existing Code Reuse

- `FinancialDecimal` and `FinancialMath` from `src/common/utils/financial-math.ts`
- `ConfigValidationError` from `src/common/errors/`
- `decimalString()` Zod helper from `env.schema.ts`
- `DECIMAL_REGEX` from `update-settings.dto.ts`
- `VwapFillResult.totalQtyAvailable` from `calculateVwapWithFillInfo()` return type
- `DegradationProtocolService.getEdgeThresholdMultiplier()` — unchanged, applied after dynamic calc

### Anti-Patterns to Avoid

- Do NOT create a new service for this — it's a focused extension of `EdgeCalculatorService` (~20 lines of logic)
- Do NOT add a new NestJS module — this lives entirely within `arbitrage-detection`
- Do NOT modify `detection.service.ts` — the dynamic threshold is internal to edge calculation
- Do NOT modify `OpportunityFilteredEvent` class — the existing `threshold` parameter already carries the effective value
- Do NOT use native JS division for the formula — use `Decimal.div()`
- Do NOT add `depthEdgeScalingFactor` to the `minEdgeThreshold` getter — keep the getter returning the static base; dynamic calculation is a separate concern

### Project Structure Notes

- All changes align with existing module boundaries (detection module, common config, persistence, dashboard)
- No new cross-module dependencies introduced
- Config pipeline follows established 10-7-1/10-7-2 pattern exactly
- EnrichedOpportunity extension is backward-compatible (new field, no removed fields)

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10.7, Story 10-7-8]
- [Source: _bmad-output/planning-artifacts/architecture.md — Edge Calculation, Configuration Management]
- [Source: _bmad-output/planning-artifacts/prd.md — FR-AD-03, FR-EX-03a, Edge Compression Risk]
- [Source: _bmad-output/implementation-artifacts/10-7-2-vwap-slippage-aware-edge-calculation.md — VWAP pattern, config pipeline]
- [Source: src/modules/arbitrage-detection/edge-calculator.service.ts — insertion point lines 303-320]
- [Source: src/common/config/config-defaults.ts — config registration pattern]
- [Source: src/dashboard/settings.service.ts — detection reload handler line 173]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- Existing test "exact_threshold_boundary" required `DEPTH_EDGE_SCALING_FACTOR=0` override because dynamic scaling (+0.008) pushes threshold above the exact 0.008 boundary edge
- Existing test "uses configurable threshold" required same override — static 0.5 threshold was being capped by MAX_DYNAMIC_EDGE_THRESHOLD (0.05)
- Test 4.1/4.4: thin book tests (depth=5) needed DETECTION_POSITION_SIZE_USD=2 and DETECTION_GAS_ESTIMATE_USD=0 to pass VWAP fill ratio check (otherwise target=667 contracts vs 5 available)
- Test 4.5: adjusted from depth 5/100 to 200/10000 — original depths failed VWAP fill ratio with default position size
- Settings count tests: config-defaults.spec.ts 76→78, settings.service.spec.ts 78→80

### Completion Notes List
- Task 1: Full config pipeline for DEPTH_EDGE_SCALING_FACTOR and MAX_DYNAMIC_EDGE_THRESHOLD (env.schema → config-defaults → settings-metadata → effective-config → Prisma → repository → DTO → settings.service). Migration applied.
- Task 2: Dynamic threshold logic in EdgeCalculatorService — computeDynamicThreshold(), validation, reloadConfig, processSingleDislocation integration. Formula: baseMinEdge × (1 + scalingFactor/minDepth), capped at maxDynamicEdgeThreshold, then × degradationMultiplier.
- Task 3: effectiveMinEdge added to EnrichedOpportunity type, enriched object, and OpportunityIdentifiedEvent payload.
- Task 4: 15 new tests (14 dynamic threshold + 1 max cap variant). 2 existing tests adapted.
- All 2814 tests pass. 0 lint errors.
- Code review (kimi-k2.5): 7 findings, 2 patch (weak test 4.4 replaced with deterministic cap test, added minDepth=0 fallback comment), 5 reject (state pollution — false positive due to beforeEach; reloadConfig throw vs warn — by design; toString vs toNumber — codebase convention).

### Change Log
- 2026-03-24: Implemented story 10-7-8. 15 new tests, 13 files modified/created.

### File List
- `src/common/config/env.schema.ts` — +2 env var definitions
- `src/common/config/config-defaults.ts` — +2 config default entries
- `src/common/config/settings-metadata.ts` — +2 settings metadata entries (DetectionEdge group)
- `src/common/config/effective-config.types.ts` — +2 typed fields
- `prisma/schema.prisma` — +2 columns on EngineConfig
- `prisma/migrations/20260324141117_add_dynamic_edge_threshold/migration.sql` — auto-generated migration
- `src/persistence/repositories/engine-config.repository.ts` — +2 resolve entries
- `src/dashboard/dto/update-settings.dto.ts` — +2 DTO fields
- `src/dashboard/settings.service.ts` — +2 SERVICE_RELOAD_MAP entries, extended detection handler
- `src/modules/arbitrage-detection/edge-calculator.service.ts` — dynamic threshold logic, validation, reloadConfig, observability
- `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts` — +effectiveMinEdge field
- `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` — +15 tests, 2 existing tests adapted
- `src/common/config/config-defaults.spec.ts` — count 76→78, +2 CATEGORY_B_FIELDS, +2 env key mappings
- `src/dashboard/settings.service.spec.ts` — count 78→80, +2 mock fields
