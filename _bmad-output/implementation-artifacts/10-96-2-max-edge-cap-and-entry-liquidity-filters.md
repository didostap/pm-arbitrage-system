# Story 10-96.2: Max Edge Cap & Entry Liquidity Filters

Status: done

## Story

As an operator,
I want phantom edge signals and illiquid entries rejected before execution,
So that the live engine doesn't trade on data anomalies or stale pricing.

## Acceptance Criteria

1. **Given** `maxEdgeThresholdPct` config setting (default `0.35`) **when** `netEdge > maxEdgeThresholdPct` **then** the opportunity is rejected as a phantom signal with reason `'edge_cap_exceeded'` and an `OpportunityFilteredEvent` is emitted.

2. **Given** `minEntryPricePct` config setting (default `0.08`) **when** either platform's best-level price < threshold **then** the opportunity is rejected with reason `'min_entry_price_below_threshold'` and an `OpportunityFilteredEvent` is emitted. Setting to `0` disables this filter.

3. **Given** `maxEntryPriceGapPct` config setting (default `0.20`) **when** `|buyPrice - sellPrice| > threshold` **then** the opportunity is rejected with reason `'entry_price_gap_exceeded'` and an `OpportunityFilteredEvent` is emitted. Setting to `0` disables this filter.

4. **Given** any of the three new config settings **when** loaded at startup via `onModuleInit()` **then** each is validated (non-negative, max 1.0) and stored as `Decimal` private fields with startup log confirmation.

5. **Given** any of the three new settings **when** updated via dashboard hot-reload (`reloadConfig()`) **then** new values are validated and applied without restart; invalid values are logged as warnings and current values are kept.

6. **Given** the three new settings **when** the dashboard settings page is loaded **then** they appear under the "Detection & Edge" group with labels, descriptions, and min/max bounds.

7. **Given** the structural guard baseline **when** this story is complete **then** `configService.get<number>()` call count remains at 58 (new reads use `configService.get<string>()` for Decimal precision).

## Tasks / Subtasks

- [x] **Task 1: Add 3 config entries across the config stack** (AC: #6, prerequisite for #4)
  - [x] 1.1 `env.schema.ts` — Add `MAX_EDGE_THRESHOLD_PCT: decimalString('0.35')`, `MIN_ENTRY_PRICE_PCT: decimalString('0.08')`, `MAX_ENTRY_PRICE_GAP_PCT: decimalString('0.20')` in the "Detection Depth (String -> Decimal)" section (after `MAX_DYNAMIC_EDGE_THRESHOLD`, line 86).
  - [x] 1.2 `config-defaults.ts` — Add 3 entries under "Detection Depth" section (after `maxDynamicEdgeThreshold`, line 76).
  - [x] 1.3 `effective-config.types.ts` — Add 3 `string` fields under "Edge Detection" section: `maxEdgeThresholdPct`, `minEntryPricePct`, `maxEntryPriceGapPct`.
  - [x] 1.4 `settings-metadata.ts` — Add 3 entries in `SettingsGroup.DetectionEdge`.
  - [x] 1.5 `prisma/schema.prisma` — Add 3 optional `Decimal?` fields under "Edge Detection" section.
  - [x] 1.6 Create Prisma migration: `20260413215232_add_entry_filter_config`.
  - [x] 1.7 `prisma/seed-config.ts` — Add all 3 to `DECIMAL_FIELDS` set.
  - [x] 1.8 `engine-config.repository.ts` — Add 3 resolve mappings.
  - [x] 1.9 Run `pnpm prisma generate` after migration.
  - [x] 1.10 Write env.schema.spec.ts tests: 9 tests (3 per new env var).
  - [x] 1.11 `engine-config.repository.spec.ts` — Add test assertions for the 3 new resolve mappings.

- [x] **Task 2: Add entry price filters to EdgeCalculatorService** (AC: #2, #3)
  - [x] 2.1 Add 2 private Decimal fields: `minEntryPricePct` (default `0.08`), `maxEntryPriceGapPct` (default `0.20`).
  - [x] 2.2 Add validation in `onModuleInit()` via shared `validateDecimalFilter()` helper.
  - [x] 2.3 Add `reloadConfig()` support via shared `reloadDecimalFilter()` helper.
  - [x] 2.4 In `processSingleDislocation()`, BEFORE the zero-price VWAP guard, add entry price filter.
  - [x] 2.5 Immediately after the min-price filter, add price gap filter.
  - [x] 2.6 Add debug-level structured logging for both filter rejections.
  - [x] 2.7 Write TDD tests: 10 tests (min price, gap, disabled, events, priority).

- [x] **Task 3: Add edge cap filter to EdgeCalculatorService** (AC: #1)
  - [x] 3.1 Add private Decimal field: `maxEdgeThresholdPct` (default `0.35`).
  - [x] 3.2 Add validation in `onModuleInit()` via shared `validateDecimalFilter()`.
  - [x] 3.3 Add `reloadConfig()` support via shared `reloadDecimalFilter()`.
  - [x] 3.4 In `processSingleDislocation()`, AFTER dynamic threshold and BEFORE capital efficiency, add edge cap filter.
  - [x] 3.5 Write TDD tests: 6 tests (reject, allow, boundary, disabled, event, ordering).

- [x] **Task 4: Update `reloadConfig()` interface** (AC: #5)
  - [x] 4.1 Extend the `reloadConfig(settings)` parameter type to include 3 new optional string fields.
  - [x] 4.2 Add validation + assignment logic via `reloadDecimalFilter()`.
  - [x] 4.3 Write TDD tests: 5 tests (valid applies, invalid keeps, negative keeps, >1.0 keeps, undefined skips).

- [x] **Task 5: Update dashboard settings count and regenerate API client** (AC: #6)
  - [x] 5.1 `settings.service.spec.ts` — Update settings count expectation from `97` to `100`.
  - [x] 5.2 `settings-metadata.spec.ts` — No count assertion to update (only group count = 15, unchanged).
  - [x] 5.3 Regenerated dashboard API client via `swagger-typescript-api`.

- [x] **Task 6: Verify structural guards and run full test suite** (AC: #7)
  - [x] 6.1 `typed-config.guard.spec.ts` — `configService.get<number>()` baseline remains 58. Passed.
  - [x] 6.2 `typed-config.guard.spec.ts` — env schema completeness guard passes with 3 new keys. Passed.
  - [x] 6.3 Full test suite: 3886 passed (+27 from 3859 baseline). 2 pre-existing e2e failures (infrastructure).
  - [x] 6.4 Lint: 0 errors in modified files. Pre-existing errors in unrelated files.

## Dev Notes

### Implementation Site: `edge-calculator.service.ts`

All three filters belong in `EdgeCalculatorService.processSingleDislocation()`. This is where dislocations are enriched into opportunities with all existing filters (VWAP depth, fill ratio, net edge threshold, dynamic threshold, capital efficiency). Placing new filters here keeps the detection pipeline's filter chain in one service.

**Filter ordering within `processSingleDislocation()` (top to bottom):**

1. **MIN ENTRY PRICE FILTER (new)** — skip if either price < `minEntryPricePct` (cheapest check, before VWAP to save compute)
2. **ENTRY PRICE GAP FILTER (new)** — skip if `|buyPrice - sellPrice|` > `maxEntryPriceGapPct` (before VWAP)
3. Zero-price VWAP guard (existing, line 311) — skip if buyPrice or sellPrice is zero
4. VWAP computation (existing, lines 322-352)
5. Fill ratio check (existing, lines 354-369)
6. Net edge calculation (existing, lines 385-395)
7. Dynamic threshold check (existing, lines 407-474)
8. **EDGE CAP FILTER (new)** — skip if `netEdge > maxEdgeThresholdPct` (needs computed netEdge)
9. Capital efficiency gate (existing, lines 476-486)

Entry price filters go BEFORE VWAP because they only need best-level prices from the dislocation. This saves VWAP computation on clearly illiquid entries. Edge cap goes after netEdge is computed but before capital efficiency, matching the backtest pipeline order.

### Config Pattern (CRITICAL — 7 files per field)

Each new config field touches 7 files. Missing any one causes runtime failures or test regressions. Follow the exact pattern from story 10-96-1's `exitStopLossPct` addition (which was initially missing 4 files and required a hotfix in 10-96-1a).

| File | Type | Notes |
|------|------|-------|
| `src/common/config/env.schema.ts` | `decimalString('default')` | Preserves Decimal precision. NOT `z.coerce.number()`. |
| `src/common/config/config-defaults.ts` | `ConfigDefaultEntry` | `defaultValue` as string for decimal types. |
| `src/common/config/effective-config.types.ts` | `string` field | Decimal fields are `string` for safe transport. |
| `src/common/config/settings-metadata.ts` | `SettingsMetadataEntry` | Group: `DetectionEdge`. Type: `'decimal'`. |
| `prisma/schema.prisma` | `Decimal? @db.Decimal(20, 8)` | Optional with `@map("snake_case")`. |
| `prisma/seed-config.ts` | `DECIMAL_FIELDS` set | NOT `FLOAT_FIELDS`. Decimal stays as string for Prisma. |
| `src/persistence/repositories/engine-config.repository.ts` | `resolve() as string` | Same cast as `detectionMinEdgeThreshold`. |

### Structural Guard Preservation

- **`configService.get<number>()` baseline: 58.** Do NOT use `configService.get<number>()` for new reads. Use `configService.get<string>(key, default)` then construct `new FinancialDecimal(value)`. This is the same pattern as `minEdgeThreshold` (line 56 of edge-calculator.service.ts).
- **Settings count: 97 → 100.** Update `settings.service.spec.ts` count from 97 to 100.
- **Env schema completeness guard:** Adding entries to both `CONFIG_DEFAULTS` and `env.schema.ts` keeps the guard passing. The 17 allowlisted keys remain unchanged.

### Backtest Reference (what we're porting)

**From 10-95-8** (backtest-engine.service.ts:700-705):
- Edge cap: `if (netEdge.gt(maxEdgeThreshold)) { skip }` — default 0.15 in backtest, **0.35 in live** per epic spec.

**From 10-95-13** (backtest-engine.service.ts:666-685):
- Min entry price: `if (kalshiClose.lt(minEntryPrice) || polyClose.lt(minEntryPrice)) { skip }` — default 0.05 in backtest, **0.08 in live**.
- Max entry price gap: `if (priceGap.gt(maxEntryPriceGap)) { skip }` — default 0.25 in backtest, **0.20 in live**.

Live defaults are intentionally different from backtest defaults — calibrated values from the sprint change proposal. Story 10-96-4 may further adjust these.

### Event Emission Reasons

New filter reason strings for `OpportunityFilteredEvent`:
- `'edge_cap_exceeded'` — phantom signal (edge > max threshold)
- `'min_entry_price_below_threshold'` — illiquid entry (price < min)
- `'entry_price_gap_exceeded'` — stale one-sided pricing (gap > max)

These join existing reasons: `'below_threshold'`, `'negative_edge'`, `'insufficient_vwap_depth'`, `'no_resolution_date'`, `'resolution_date_passed'`, `'annualized_return_*_below_*_minimum'`, `'pair_cooldown_active'`, `'pair_max_concurrent_reached'`, `'pair_above_average_concentration'`.

### What NOT To Do

- Do NOT add filters to `detection.service.ts` — all enrichment/filtering logic belongs in `EdgeCalculatorService`.
- Do NOT use `getConfigNumber()` for these fields — they are Decimal-precision values loaded as strings.
- Do NOT add `configService.get<number>()` calls — this breaks the structural guard baseline of 58.
- Do NOT use `Float?` in Prisma schema — use `Decimal? @db.Decimal(20, 8)` for financial precision.
- Do NOT add these to `FLOAT_FIELDS` in seed-config.ts — add to `DECIMAL_FIELDS`.
- Do NOT modify `detection.service.ts`, `trading-engine.service.ts`, or `pair-concentration-filter.service.ts`.
- Do NOT change the `return;` on line 65 of `trading-engine.service.ts` — live engine stays disabled until Epic 10.96 is complete.
- Do NOT change defaults for existing config values — that's story 10-96-4.
- Do NOT add `FilteredDislocation.netEdge` as `Decimal` — existing pattern uses `string` (see line 443 of edge-calculator.service.ts).
- Do NOT add counter tracking (RunningAccumulators) — that's a backtest-specific pattern. Live pipeline uses event emission for observability.

### Previous Story Intelligence

**From 10-96-1 (entry fee / stop-loss):**
- `getConfigNumber` is MANDATORY for new number reads — but these are Decimal values, so use `configService.get<string>()` instead.
- Gas cost uses `DETECTION_GAS_ESTIMATE_USD` (shared config, default `'0.30'`). No separate gas config needed for filters.
- TDD cycle: Write failing test first, implement, refactor. Assertion depth: verify exact values with `expect.objectContaining()`.
- Financial math: All test fixtures use `new Decimal('...')` — NEVER native JS numbers.

**From 10-96-1a (startup/websocket fixes):**
- Prisma schema alignment is CRITICAL: any new config field must be added to ALL 7 files listed above. Story 10-96-1 missed 4 files (`settings-metadata.ts`, `engine-config.repository.ts`, `prisma/schema.prisma`, `seed-config.ts`) and required a hotfix.
- Settings count test must be updated when adding new CONFIG_DEFAULTS entries.

### Existing Filter Pipeline in `edge-calculator.service.ts`

Current filters in `processSingleDislocation()` (lines 292-545):
1. **L311:** Zero-price guard → `filterInsufficientVwapDepth()`
2. **L322-352:** VWAP computation (buy/sell target contracts, VWAP results, null check)
3. **L354-369:** Fill ratio vs `detectionMinFillRatio` (0.25) → `filterInsufficientVwapDepth()`
4. **L385-395:** VWAP gross edge + net edge computation via `FinancialMath.calculateNetEdge()`
5. **L407-474:** Dynamic threshold → `isAboveThreshold()` → `OpportunityFilteredEvent` with `'below_threshold'` or `'negative_edge'`
6. **L476-486:** Capital efficiency gate → `checkCapitalEfficiency()` → resolution date + annualized return
7. **L497-544:** Build `EnrichedOpportunity` + emit `OpportunityIdentifiedEvent`

### `FilteredDislocation` Type

When pushing to the `filtered` array, use the `FilteredDislocation` type (from `edge-calculation-result.type.ts`):
```typescript
interface FilteredDislocation {
  pairEventDescription: string;
  netEdge: string;
  threshold: string;
  reason: string;
  bestLevelNetEdge?: string;
}
```

For entry price filters (where netEdge hasn't been computed yet), use `netEdge: 'N/A'` — the opportunity was rejected before edge computation.

### Project Structure Notes

All new code goes in existing files — no new files, modules, or services needed:
- Config: 7 existing config stack files
- Filter logic: `src/modules/arbitrage-detection/edge-calculator.service.ts`
- Tests: `src/modules/arbitrage-detection/edge-calculator.service.spec.ts`, `src/common/config/env.schema.spec.ts`
- Migration: `prisma/migrations/<timestamp>_add_entry_filter_config/migration.sql` (auto-generated)

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10.96, Story 10-96-2]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-13-live-engine-alignment.md]
- [Source: _bmad-output/implementation-artifacts/10-96-1-entry-fee-aware-exit-pnl-and-percentage-stop-loss.md — Config pattern, "What NOT To Do"]
- [Source: _bmad-output/implementation-artifacts/10-96-1a-startup-performance-websocket-gas-fixes.md — Prisma schema alignment bugfix]
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts — Current filter pipeline]
- [Source: pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:666-705 — Backtest filter implementation to port]
- [Source: pm-arbitrage-engine/src/common/config/config-defaults.ts — CONFIG_DEFAULTS pattern]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- Baseline: 3859 tests passing, 2 pre-existing e2e failures (core-lifecycle)
- Final: 3886 tests passing (+27), same pre-existing e2e failures
- Structural guard `configService.get<number>()` baseline: 58 (preserved)
- Settings count: 97 → 100

### Completion Notes List
- **Task 1:** All 7 config stack files updated + Prisma migration `20260413215232_add_entry_filter_config`. 9 env.schema tests + 6 engine-config repo assertions added.
- **Task 2:** Min entry price + price gap filters added to `processSingleDislocation()` BEFORE the VWAP zero-price guard. Shared `validateDecimalFilter()` helper created. 10 tests added. Updated 1 existing test (zero-price dislocation now caught by min entry price filter before VWAP guard — correct per new filter ordering).
- **Task 3:** Edge cap filter added AFTER dynamic threshold, BEFORE capital efficiency. 6 tests added.
- **Task 4:** `reloadConfig()` extended with 3 fields via shared `reloadDecimalFilter()` helper. 5 reload tests added.
- **Task 5:** Settings count 97 → 100. Dashboard API client regenerated.
- **Task 6:** All structural guards pass. Full suite green (unit-only: 234 files, 3864 tests, 0 failures).

### Change Log
- 2026-04-13: Story 10-96-2 implemented. 3 entry/edge filters (min price, price gap, edge cap) added to live detection pipeline. Ports backtest fixes 10-95-8 + 10-95-13.

### File List
- `src/common/config/env.schema.ts` — 3 new `decimalString` env vars
- `src/common/config/env.schema.spec.ts` — 9 new tests
- `src/common/config/config-defaults.ts` — 3 new CONFIG_DEFAULTS entries
- `src/common/config/effective-config.types.ts` — 3 new string fields
- `src/common/config/settings-metadata.ts` — 3 new DetectionEdge entries
- `prisma/schema.prisma` — 3 new Decimal? columns on EngineConfig
- `prisma/migrations/20260413215232_add_entry_filter_config/migration.sql` — auto-generated
- `prisma/seed-config.ts` — 3 fields added to DECIMAL_FIELDS
- `src/persistence/repositories/engine-config.repository.ts` — 3 new resolve mappings
- `src/persistence/repositories/engine-config.repository.spec.ts` — assertions for 3 new fields
- `src/modules/arbitrage-detection/edge-calculator.service.ts` — 3 filters + validateDecimalFilter + reloadDecimalFilter + validateEntryFilters
- `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` — 21 new tests + 1 modified test
- `src/dashboard/settings.service.spec.ts` — count 97 → 100
- `pm-arbitrage-dashboard/src/api/generated/Api.ts` — regenerated
