# Story 10.7.6: Per-Pair Position Cooldown & Concentration Limits

Status: done

## Story

As an operator,
I want per-pair position frequency limits and concentration caps,
so that the system stops hammering the same thin order books and distributes trades across pairs.

## Context

Analysis of 202 paper positions showed 92% concentration in 2 pairs (xAI/Text Arena = 57%, 162 single-leg events). The system repeatedly re-enters depleted books because no per-pair frequency or concentration controls exist. This story adds three complementary filters — cooldown, concurrent limit, diversity cap — applied **before** risk validation in the trading engine cycle.

**FR-EX-09 (new):** Per-pair concentration limits.

## Acceptance Criteria

### AC-1: Pair Cooldown (Time-Based Frequency Limit)

**Given** a position (any status) was opened for a pair within `PAIR_COOLDOWN_MINUTES` (configurable, default: 30)
**When** a new opportunity is detected for the same pair
**Then** the opportunity is filtered before risk validation
**And** an `OpportunityFilteredEvent` is emitted with reason `"pair_cooldown_active"`

**Given** the cooldown period has elapsed for a pair
**When** a new opportunity is detected for that pair
**Then** the opportunity passes the cooldown filter

### AC-2: Maximum Concurrent Positions Per Pair

**Given** a pair has reached or exceeded `PAIR_MAX_CONCURRENT_POSITIONS` open positions (configurable, default: 2; comparison: `openCount >= limit`)
**When** a new opportunity is detected for that pair
**Then** the opportunity is filtered before risk validation with reason `"pair_max_concurrent_reached"`

### AC-3: Portfolio Diversity Enforcement

**Given** total open positions across all pairs exceeds `PAIR_DIVERSITY_THRESHOLD` (configurable, default: 5)
**When** a new opportunity is detected for a pair with `pairCount >= average` (at-or-above; `average = totalOpen / uniquePairsWithOpenPositions`)
**Then** the opportunity is filtered with reason `"pair_above_average_concentration"`
**And** pairs below average are still allowed

**Example:** 5 total positions: Pair A=3, Pair B=2. Average=2.5. Pair A (3>=2.5) blocked. Pair B (2<2.5) allowed.

**Given** total open positions < `PAIR_DIVERSITY_THRESHOLD`
**When** any opportunity is detected
**Then** the diversity filter does not apply

### AC-4: Configuration & Dashboard Visibility

**Given** the engine starts
**Then** all three settings are persisted in EngineConfig with defaults:
- `pairCooldownMinutes`: 30
- `pairMaxConcurrentPositions`: 2
- `pairDiversityThreshold`: 5

**And** all three appear in the dashboard Settings page under "Risk Management" group
**And** changes take effect at next detection cycle (hot-reload, no restart)

### AC-5: Paper/Live Mode Isolation

**Given** paper mode has pair cooldown/concentration state
**When** live mode checks the same pair
**Then** paper state does not affect live decisions and vice versa
**And** cooldown timestamps, concurrent counts, and diversity calculations are tracked independently per mode (all queries scoped by `isPaper`)

### AC-6: Observability

**Given** any opportunity is filtered by concentration controls
**Then** an `OpportunityFilteredEvent` is emitted (reuse existing event class) with:
- `reason`: specific filter type string
- `matchId`: the pair's matchId
- `pairEventDescription`: from `pairConfig.eventDescription`
- `netEdge`: the opportunity's net edge
**And** monitoring logs the filtering decision for audit trail

### AC-7: Fail-Open on Repository Error

**Given** the position repository query fails during filter execution (DB timeout, connection error)
**When** the concentration filter is processing opportunities
**Then** all opportunities pass through to risk validation (fail-open — better to over-trade than silently halt)
**And** the error is logged at WARN level
**And** a `SystemHealthError` event is emitted (code 4xxx range)

## Tasks / Subtasks

- [x] Task 1: Config Pipeline — 3 new settings through established 15-file pattern (AC: #4)
  - [x] 1.1 `src/common/config/env.schema.ts` — Add `PAIR_COOLDOWN_MINUTES: z.coerce.number().int().min(0).default(30)`, `PAIR_MAX_CONCURRENT_POSITIONS: z.coerce.number().int().min(0).default(2)`, `PAIR_DIVERSITY_THRESHOLD: z.coerce.number().int().min(0).default(5)`
  - [x] 1.2 `src/common/config/config-defaults.ts` — Add 3 entries: `pairCooldownMinutes` (envKey `PAIR_COOLDOWN_MINUTES`, default 30), `pairMaxConcurrentPositions` (envKey `PAIR_MAX_CONCURRENT_POSITIONS`, default 2), `pairDiversityThreshold` (envKey `PAIR_DIVERSITY_THRESHOLD`, default 5). Update count assertions.
  - [x] 1.3 `src/common/config/settings-metadata.ts` — Add 3 entries under `SettingsGroup.RiskManagement`: type `'integer'`, min 0, with descriptive labels. Update count. Note: the dashboard SPA auto-renders settings from this metadata via the API — no frontend code changes needed.
  - [x] 1.4 `src/common/config/effective-config.types.ts` — Add `pairCooldownMinutes: number`, `pairMaxConcurrentPositions: number`, `pairDiversityThreshold: number`
  - [x] 1.5 `src/common/config/update-settings.dto.ts` — Add `@IsOptional() @IsInt() @Min(0) pairCooldownMinutes?: number`, same for other 2
  - [x] 1.6 `prisma/schema.prisma` — Add 3 nullable Int columns to EngineConfig: `pairCooldownMinutes Int? @map("pair_cooldown_minutes")`, etc.
  - [x] 1.7 Create Prisma migration: `pnpm prisma migrate dev --name add_pair_concentration_config`
  - [x] 1.8 `src/persistence/repositories/engine-config.repository.ts` — Add 3 fields to resolve chain
  - [x] 1.9 `src/dashboard/settings.service.ts` — SERVICE_RELOAD_MAP not needed; filter uses @OnEvent(config.settings.updated) for hot-reload directly
  - [x] 1.10 Update test files: `config-defaults.spec.ts` (count 73→76, key lists), `config-accessor.service.spec.ts` (mock effective config), `dashboard/settings.service.spec.ts` (count 75→78), `prisma/seed-config.spec.ts` (mock row)
- [x] Task 2: Position Repository Query Extensions (AC: #1, #2, #3, #5)
  - [x] 2.1 `src/persistence/repositories/position.repository.ts` — Add `getLatestPositionDateByPairIds(pairIds: string[], isPaper: boolean): Promise<Map<string, Date>>`. Raw query: `SELECT pair_id, MAX(created_at) as latest FROM open_positions WHERE pair_id IN (...) AND is_paper = $isPaper GROUP BY pair_id -- MODE-FILTERED`. Returns map of pairId→Date for cooldown checks across all statuses.
  - [x] 2.2 Same file — Add `getOpenPositionCountsByPair(isPaper: boolean): Promise<Map<string, number>>`. Query: `SELECT pair_id, COUNT(*) as count FROM open_positions WHERE status = 'OPEN' AND is_paper = $isPaper GROUP BY pair_id -- MODE-FILTERED`. Returns map of pairId→count for concurrent + diversity checks.
  - [x] 2.3 `src/persistence/repositories/position.repository.spec.ts` — Tests for both methods: empty results, single pair, multiple pairs, mode isolation (paper vs live return independent results)
- [x] Task 3: PairConcentrationFilterService — Core filtering logic (AC: #1, #2, #3, #5)
  - [x] 3.1 `src/common/interfaces/pair-concentration-filter.interface.ts` — Define interface + DI token:
    ```typescript
    export const PAIR_CONCENTRATION_FILTER_TOKEN = 'IPairConcentrationFilter';
    export interface IPairConcentrationFilter {
      filterOpportunities(opportunities: EnrichedOpportunity[], isPaper: boolean): Promise<ConcentrationFilterResult>;
    }
    export interface ConcentrationFilterResult {
      passed: EnrichedOpportunity[];
      filtered: FilteredOpportunityEntry[];
    }
    export interface FilteredOpportunityEntry {
      opportunity: EnrichedOpportunity;
      reason: string;
    }
    ```
  - [x] 3.2 Export from `src/common/interfaces/index.ts`
  - [x] 3.3 `src/modules/arbitrage-detection/pair-concentration-filter.service.ts` — Implement `IPairConcentrationFilter`:
    - Inject `PositionRepository`, `ConfigAccessorService`, `EventEmitter2`
    - Store 3 config values as private fields, hot-reload via `@OnEvent('settings.updated')`
    - `filterOpportunities()` method:
      1. Extract unique pairIds from opportunities via `opportunity.dislocation.pairConfig.matchId`
      2. Batch-fetch: `getLatestPositionDateByPairIds(pairIds, isPaper)` → Map<string, Date>
      3. Batch-fetch: `getOpenPositionCountsByPair(isPaper)` → Map<string, number>
      4. For each opportunity, apply 3 checks IN ORDER: cooldown → concurrent → diversity
      5. First failing check → add to `filtered[]` with reason, emit `OpportunityFilteredEvent`
      6. All checks pass → add to `passed[]`
    - Cooldown check: `Date.now() - latestDate.getTime() < cooldownMinutes * 60_000`
    - Concurrent check: `openCount >= maxConcurrent` (when maxConcurrent > 0)
    - Diversity check: `totalOpen >= threshold AND pairCount >= (totalOpen / uniquePairsCount)` — uses floating-point comparison since counts are integers and average may be fractional
    - Setting value 0 disables the respective check (backward-compatible)
  - [x] 3.4 `src/modules/arbitrage-detection/pair-concentration-filter.service.spec.ts` — Unit tests:
    - Cooldown: blocks within window, allows after window expires, allows when no prior position exists, disabled when config=0
    - Concurrent: blocks at limit, allows below limit, disabled when config=0
    - Diversity: blocks above-average pair when total >= threshold, allows below-average pair, allows all when total < threshold, handles new pair (count=0) correctly, disabled when config=0
    - Hot-reload: config changes take effect immediately
    - Mode isolation: paper and live state independent
    - Event emission: `OpportunityFilteredEvent` emitted with correct reason, matchId, netEdge for each filtered opportunity
    - Multiple opportunities: batch filtering processes all opportunities, different pairs filtered/passed independently
    - Fail-open: repository query failure returns all opportunities as passed + emits SystemHealthError (AC: #7)
  - [x] 3.5 `src/modules/arbitrage-detection/arbitrage-detection.module.ts` — Import `PersistenceModule`, register `PairConcentrationFilterService` as provider with token `PAIR_CONCENTRATION_FILTER_TOKEN`, add to exports
- [x] Task 4: Trading Engine Integration (AC: #1, #2, #3)
  - [x] 4.1 `src/core/trading-engine.service.ts` — Injected PAIR_CONCENTRATION_FILTER_TOKEN, filter call inserted between edge calc and risk validation loop
  - [x] 4.2 `src/core/core.module.ts` — Verified ArbitrageDetectionModule imported, PAIR_CONCENTRATION_FILTER_TOKEN available via export
  - [x] 4.3 `src/core/trading-engine.service.spec.ts` — 5 new tests: call order, filtered not reaching risk, passed proceeding, backward-compatible, zero executions
- [x] Task 5: Event Wiring & Monitoring (AC: #6)
  - [x] 5.1 `src/common/events/event-catalog.ts` — Added OPPORTUNITY_CONCENTRATION_FILTERED constant
  - [x] 5.2 EventConsumerService handles via onAny (no @OnEvent needed — existing architecture). Added to info events classification test.
  - [x] 5.3 `src/modules/monitoring/event-consumer.service.spec.ts` — 2 new tests: handleEvent without error, classifies as info severity
  - [x] 5.4 PairConcentrationFilterService emits events using EVENT_NAMES.OPPORTUNITY_CONCENTRATION_FILTERED (verified in service code)
- [x] Task 6: Paper/Live Boundary + Integration Tests (AC: #5)
  - [x] 6.1 `src/common/testing/paper-live-boundary/concentration-filter.boundary.spec.ts` — 10 tests: dual-mode matrix, cooldown/concurrent/diversity isolation
  - [x] 6.2 Integration-level test: trading-engine.service.spec.ts tests verify filtered opportunities don't reach execution

## Dev Notes

### Architecture & Integration Points

**Filtering location:** The concentration filter runs in the trading engine cycle (`TradingEngineService.executeCycle()`) BETWEEN edge calculation output and the risk validation loop. Currently at `trading-engine.service.ts:161-226`. Insert filter call before the `for (const opportunity of ...)` loop.

**Module placement:** New `PairConcentrationFilterService` in `modules/arbitrage-detection/` — this module already exports to `core/` and the filter is conceptually part of opportunity quality assessment. Add `PersistenceModule` to its imports for repository access.

**Dependency flow (all allowed):**
```
core/TradingEngine → (via IPairConcentrationFilter interface) → modules/arbitrage-detection/PairConcentrationFilterService
                                                                  ↓
                                                            persistence/PositionRepository
                                                            common/config/ConfigAccessorService
                                                            common/events/EventEmitter2
```

### Reuse — DO NOT Reinvent

- **OpportunityFilteredEvent** — Already exists at `src/common/events/detection.events.ts:21-37`. Constructor: `(pairEventDescription, netEdge, threshold, reason, correlationId?, opts?: { matchId?, annualizedReturn? })`. Reuse with new reason strings. Set `threshold` to the configured limit value as `new Decimal(configValue)`.
- **Config pipeline** — Follow the exact 15-file pattern established in stories 10-7-3 through 10-7-5. The pattern is mechanical; deviating breaks consistency.
- **Mode filtering** — Use `withModeFilter(isPaper)` from `src/persistence/repositories/mode-filter.helper.ts` or add `is_paper` filtering directly in raw queries with `-- MODE-FILTERED` comment.
- **Branded types** — Use `asPairId()` from `src/common/types/branded.type.ts` when converting `matchId` strings. Access pair ID via `opportunity.dislocation.pairConfig.matchId`.
- **Settings hot-reload** — Follow existing `@OnEvent('settings.updated')` handler pattern. Store config values as private fields, update on event.

### DO NOT Touch

- `risk-manager.service.ts` — Already a 1651-line God Object queued for decomposition in 10-8-1. Do NOT add concentration logic there.
- Existing `validatePosition()` flow — The concentration filter is a PRE-filter. Risk validation is unchanged.
- Any existing test files beyond what's needed for config count updates.

### Opportunity Type Access

```typescript
// From EnrichedOpportunity:
const pairId = asPairId(opportunity.dislocation.pairConfig.matchId);
const eventDesc = opportunity.dislocation.pairConfig.eventDescription;
const netEdge = opportunity.netEdge;           // Decimal
const annualizedReturn = opportunity.annualizedReturn; // Decimal | null
```

### Query Efficiency

The filter makes exactly **2 DB queries per cycle** regardless of opportunity count:
1. `getLatestPositionDateByPairIds` — batch cooldown check for all unique pairs in opportunities
2. `getOpenPositionCountsByPair` — batch concurrent + diversity check (all open positions by pair)

All per-opportunity filtering is then in-memory against the pre-fetched maps.

### Config Defaults & Disabling

Setting any config value to `0` disables that specific check (backward-compatible — no behavior change for existing deployments until explicitly configured).

### Event Naming

Use a distinct event name (`detection.opportunity.concentration_filtered`) rather than overloading the existing edge-based `OpportunityFilteredEvent` emission path. This allows monitoring to distinguish between "filtered because edge too low" and "filtered because of concentration limits" for analytics.

However, **reuse the same event CLASS** (`OpportunityFilteredEvent`) — the reason field differentiates the filter type.

### Project Structure Notes

- All new files follow kebab-case naming convention
- Service: `pair-concentration-filter.service.ts` + `.spec.ts` (co-located in `modules/arbitrage-detection/`)
- Interface: `pair-concentration-filter.interface.ts` in `common/interfaces/`
- Boundary tests: `concentration-filter.boundary.spec.ts` in `common/testing/paper-live-boundary/`
- No new module needed — extends existing `ArbitrageDetectionModule`

### Error Handling

This feature FILTERS opportunities — it does not throw errors. If repository queries fail:
- Log the error at `warn` level
- Return all opportunities as `passed` (fail-open for filtering — better to over-trade than silently halt)
- Emit a `SystemHealthError` event with appropriate code (4xxx range)

This is a conscious design choice: concentration filtering is a quality improvement, not a safety-critical gate like risk validation.

### Financial Math

Cooldown and concentration limits use integer comparisons (minutes, counts). No `Decimal` needed for the filter logic itself. Only the `OpportunityFilteredEvent` emission requires `Decimal` for `netEdge` and `threshold` fields (already Decimal in the event constructor).

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-23-paper-profitability.md] — Root cause analysis showing 92% pair concentration
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-10.7] — FR-EX-09, story 10-7-6 definition, BDD scenarios
- [Source: _bmad-output/planning-artifacts/architecture.md#Risk-Management] — Risk event patterns, module boundaries
- [Source: _bmad-output/planning-artifacts/prd.md#FR-RM-01-02] — Position limits, portfolio constraints
- [Source: pm-arbitrage-engine/src/common/events/detection.events.ts:21-37] — Existing OpportunityFilteredEvent class
- [Source: pm-arbitrage-engine/src/core/trading-engine.service.ts:161-226] — Risk pre-filter loop (insertion point)
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/arbitrage-detection.module.ts] — Current module providers
- [Source: pm-arbitrage-engine/src/common/config/settings-metadata.ts] — SettingsGroup.RiskManagement entries

### Previous Story Intelligence (10-7-5)

**Config pipeline pattern (15 files):** env.schema → config-defaults → settings-metadata → effective-config.types → update-settings.dto → prisma schema + migration → engine-config.repository → settings.service reload map → 5 test files (config-defaults count, config-accessor mock, settings.service count, seed-config mock). Counts: settings metadata 75→78, config defaults 73→76 after this story.

**Test patterns that worked:**
- Mock config values via `configAccessor.getEffective` mock
- Use `expect.objectContaining({...})` for event verification (never bare `toHaveBeenCalled()`)
- `describe.each([[true, 'paper'], [false, 'live']])` for dual-mode matrix
- `expectEventHandled()` from `src/common/testing/expect-event-handled.ts` for event wiring

**Code review findings from recent stories (avoid these issues):**
- Always add NaN guard for numeric config values
- Ensure config validation rejects invalid values at startup
- Use `Decimal.min()` / `Decimal.max()` not native `Math.min()` / `Math.max()` for financial values
- All raw SQL queries must include `-- MODE-FILTERED` comment marker

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List
- Task 1: Config pipeline (15-file pattern) — 3 new settings (pairCooldownMinutes, pairMaxConcurrentPositions, pairDiversityThreshold) added through env.schema → config-defaults → settings-metadata → effective-config.types → update-settings.dto → prisma schema + migration → engine-config.repository. Settings.service SERVICE_RELOAD_MAP not needed: filter uses @OnEvent for hot-reload. 5 test files updated (counts: config-defaults 73→76, settings 75→78). All 2729 tests pass.
- Task 2: PositionRepository.getLatestPositionDateByPairIds() and getOpenPositionCountsByPair() — raw SQL with MODE-FILTERED comments. 9 new tests. All 2738 tests pass.
- Task 3: PairConcentrationFilterService — 3 ordered filters (cooldown → concurrent → diversity), fail-open on repo error, event emission via OPPORTUNITY_CONCENTRATION_FILTERED. Used ConfigService (not ConfigAccessor) to avoid circular DI. PositionRepository registered as direct provider. 19 unit tests. All 2757 tests pass.
- Task 4: TradingEngine integration — filter call inserted between edge calc output and risk validation loop. 5 new tests. Updated event-wiring-audit.spec.ts with new token. All 2762 tests pass.
- Task 5: OPPORTUNITY_CONCENTRATION_FILTERED added to event-catalog.ts. EventConsumerService handles via onAny (existing pattern). CONCENTRATION_FILTER_FAILURE (4010) error code added. 2 new tests in event-consumer spec. All 2764 tests pass.
- Task 6: 10 boundary tests in concentration-filter.boundary.spec.ts. Integration covered by trading-engine spec. All 2774 tests pass.

### File List
- pm-arbitrage-engine/src/common/config/env.schema.ts (modified)
- pm-arbitrage-engine/src/common/config/config-defaults.ts (modified)
- pm-arbitrage-engine/src/common/config/config-defaults.spec.ts (modified)
- pm-arbitrage-engine/src/common/config/settings-metadata.ts (modified)
- pm-arbitrage-engine/src/common/config/effective-config.types.ts (modified)
- pm-arbitrage-engine/src/common/config/config-accessor.service.spec.ts (modified)
- pm-arbitrage-engine/src/dashboard/dto/update-settings.dto.ts (modified)
- pm-arbitrage-engine/src/dashboard/settings.service.spec.ts (modified)
- pm-arbitrage-engine/prisma/schema.prisma (modified)
- pm-arbitrage-engine/prisma/migrations/20260324101042_add_pair_concentration_config/migration.sql (new)
- pm-arbitrage-engine/prisma/seed-config.spec.ts (modified)
- pm-arbitrage-engine/src/persistence/repositories/engine-config.repository.ts (modified)
- pm-arbitrage-engine/src/persistence/repositories/engine-config.repository.spec.ts (modified)
- pm-arbitrage-engine/src/persistence/repositories/position.repository.ts (modified)
- pm-arbitrage-engine/src/persistence/repositories/position.repository.spec.ts (modified)
- pm-arbitrage-engine/src/common/interfaces/pair-concentration-filter.interface.ts (new)
- pm-arbitrage-engine/src/common/interfaces/index.ts (modified)
- pm-arbitrage-engine/src/modules/arbitrage-detection/pair-concentration-filter.service.ts (new)
- pm-arbitrage-engine/src/modules/arbitrage-detection/pair-concentration-filter.service.spec.ts (new)
- pm-arbitrage-engine/src/modules/arbitrage-detection/arbitrage-detection.module.ts (modified)
- pm-arbitrage-engine/src/core/trading-engine.service.ts (modified)
- pm-arbitrage-engine/src/core/trading-engine.service.spec.ts (modified)
- pm-arbitrage-engine/src/common/events/event-catalog.ts (modified)
- pm-arbitrage-engine/src/common/errors/system-health-error.ts (modified)
- pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.spec.ts (modified)
- pm-arbitrage-engine/src/common/testing/event-wiring-audit.spec.ts (modified)
- pm-arbitrage-engine/src/common/testing/paper-live-boundary/concentration-filter.boundary.spec.ts (new)
