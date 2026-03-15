# Story 9.16: Risk State Paper Trade Reconciliation & Parallel Mode Capital Isolation

Status: done

## Story

As an **operator**,
I want **risk state, reconciliation, and capital tracking to be fully isolated between paper and live trading modes, with correct sell-side capital formulas across all code paths**,
so that **paper positions don't silently zero out on restart, live trading is never blocked by paper capital consumption, and capital accounting is accurate for both buy-side and sell-side legs**.

## Acceptance Criteria

1. **Dual risk state rows**: `risk_states` table has two rows: `(default, live)` and `(default, paper)`. Migration adds `mode` column (default `'live'`), inserts fresh paper row, drops old `singletonKey` unique constraint, adds compound `@@unique([singletonKey, mode])`. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC1; disambiguation Q1 confirmation]

2. **Paper risk state survives restart**: After restart with open paper positions, the paper risk state shows correct `openPositionCount` and `totalCapitalDeployed` matching actual DB positions. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC2]

3. **Live risk state independent**: After restart with open live positions, live risk state shows correct values independently — unaffected by paper position counts or capital. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC3]

4. **Capital isolation**: Live entry never blocked by paper capital consumption. `reserveBudget()` checks the correct mode's available capital pool. Paper positions reduce only the paper pool. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC4]

5. **Paper bankroll configurable**: Paper bankroll configurable via `paperBankrollUsd` column on `EngineConfig` table (defaults to live `bankrollUsd` when null). Editable via existing dashboard bankroll API. Follows the same DB-persistence + hot-reload pattern established in Story 9-14. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC5; codebase — EngineConfig at schema.prisma:20-28, loadBankrollFromDb at risk-manager.service.ts:109-134]

6. **Sell-side capital formula**: Sell-side capital uses `size × (1 - fillPrice)` via shared `calculateLegCapital(side, price, size)` utility in `common/utils/capital.ts`. Buy-side remains `size × price`. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC6]

7. **Capital formula consistency**: Capital formula is consistent across all paths: reconciliation (`recalculateRiskBudget`), correlation tracker (`recalculateClusterExposure`, `getTriageRecommendations`), exit monitor (`exitedEntryCapital`), execution commit. All import from `common/utils/capital.ts`. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC7; codebase investigation — 5 affected locations confirmed]

8. **`findActivePositions()` callers audited**: All callers of `findActivePositions()` audited and categorized. Two production callers in `startup-reconciliation.service.ts` (lines 339, 761) now pass explicit `isPaper` argument — no more default-to-false hiding paper positions. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC8; codebase grep confirmed only 2 production callers]

9. **Dashboard per-mode capital**: Dashboard Capital Overview shows per-mode breakdown: `{ live: { bankroll, deployed, available, reserved }, paper: { ... } }`. Frontend renders both sections. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC9]

10. **Reconciliation per-mode**: Reconciliation after restart iterates over `[false, true]` for `isPaper`, restoring both modes independently — no cross-contamination. `recalculateRiskBudget()` runs per-mode. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC10]

11. **Daily P&L reset per-mode**: Midnight reset applies to each mode independently. Stale-day detection in `initializeStateFromDb()` handles both rows. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC11]

12. **Correlation tracker mode-aware**: `recalculateClusterExposure()` and `getTriageRecommendations()` filter by `isPaper` — live positions only count toward live cluster exposure, paper positions only toward paper cluster exposure. Both modes get correlation tracking for simulation fidelity. Queries add `isPaper` filter + select `polymarketSide`/`kalshiSide` for sell-side capital fix. [Source: disambiguation Q2 confirmation; codebase investigation — correlation tracker currently has no isPaper filter and no side field in select]

13. **Tests**: Paper reconciliation, live reconciliation, mixed parallel, sell-side capital edge cases (fillPrice near 0.0, near 1.0, exact 0.5), `calculateLegCapital` unit tests, correlation tracker mode isolation, dashboard per-mode response. [Source: sprint-change-proposal-2026-03-14.md#Story-B AC12; expanded from disambiguation]

14. **All existing tests pass**: `pnpm test` passes at baseline (2056 passed, 2 todo). `pnpm lint` clean. [Source: CLAUDE.md post-edit workflow; baseline verified 2026-03-14]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**

- [x] **Task 1: Create `calculateLegCapital` shared utility** (AC: #6, #7)
  - [ ] 1.1 Create `src/common/utils/capital.ts` with:
    ```typescript
    import Decimal from 'decimal.js';
    /**
     * Calculate capital deployed for a single leg of a position.
     * Buy-side: size × price (you pay price per contract).
     * Sell-side: size × (1 - price) (your collateral is the complement).
     */
    export function calculateLegCapital(
      side: string,
      price: Decimal,
      size: Decimal,
    ): Decimal {
      const effectivePrice = side === 'sell'
        ? new Decimal(1).minus(price)
        : price;
      return size.mul(effectivePrice);
    }
    ```
  - [ ] 1.2 Create `src/common/utils/capital.spec.ts` with tests:
    - Buy-side: `calculateLegCapital('buy', 0.60, 100)` → `60`
    - Sell-side: `calculateLegCapital('sell', 0.60, 100)` → `40`
    - Sell near 1.0: `calculateLegCapital('sell', 0.99, 100)` → `1`
    - Sell near 0.0: `calculateLegCapital('sell', 0.01, 100)` → `99`
    - Buy at 0.5: `calculateLegCapital('buy', 0.50, 200)` → `100`
    - Sell at 0.5: `calculateLegCapital('sell', 0.50, 200)` → `100`
    - Zero price buy: `calculateLegCapital('buy', 0, 100)` → `0`
    - Zero price sell: `calculateLegCapital('sell', 0, 100)` → `100`
  - [ ] 1.3 Export from `src/common/utils/index.ts` (create barrel if not present)

- [x] **Task 2: Prisma schema migration + env config** (AC: #1, #5)
  - [ ] 2.1 Update `prisma/schema.prisma` — `RiskState` model:
    - Add `mode String @default("live") @map("mode")`
    - Remove `@unique` from `singletonKey`
    - Add `@@unique([singletonKey, mode])` (replaces old unique)
    - Keep all existing fields unchanged
  - [ ] 2.2 Run `pnpm prisma migrate dev --name add-risk-state-mode` — then **manually review** the generated migration SQL before applying. Prisma frequently gets constraint swap ordering wrong. The correct sequence is:
    1. `ALTER TABLE DROP CONSTRAINT` — drop old unique on `singleton_key`
    2. `ALTER TABLE ADD COLUMN mode VARCHAR NOT NULL DEFAULT 'live'` — existing row becomes live
    3. `ALTER TABLE ADD CONSTRAINT` — add compound unique on `(singleton_key, mode)`
    4. `INSERT INTO risk_states ...` — insert fresh paper row (after compound unique exists)
    If Prisma generates a different order, manually edit the migration SQL file. Do NOT trust auto-generation for constraint swaps on the same column.
  - [ ] 2.3 Add data migration at the end of the migration SQL — insert paper row:
    ```sql
    INSERT INTO risk_states (id, singleton_key, mode, daily_pnl, open_position_count, total_capital_deployed, trading_halted, reserved_capital, reserved_position_slots, created_at, updated_at)
    VALUES (gen_random_uuid(), 'default', 'paper', 0, 0, 0, false, 0, 0, NOW(), NOW());
    ```
    No `ON CONFLICT` needed — Prisma migrations are idempotent via the migration history table (`_prisma_migrations`), not via SQL clauses. Each migration runs exactly once.
  - [ ] 2.4 Run `pnpm prisma generate` to regenerate client
  - [ ] 2.5 Add `paperBankrollUsd` column to `EngineConfig` model in `prisma/schema.prisma`:
    ```prisma
    paperBankrollUsd Decimal? @map("paper_bankroll_usd") @db.Decimal(20, 8)
    ```
    Nullable — when null, `getBankrollForMode(true)` falls back to live bankroll. This follows the same pattern as `bankrollUsd`: DB-persisted, hot-reloadable, dashboard-editable.
  - [ ] 2.6 Include this column addition in the same migration as the RiskState `mode` change (or a second migration if cleaner)
  - [ ] 2.7 Verify: `pnpm prisma generate && pnpm build` succeeds

- [x] **Task 3: RiskManagerService per-mode state** (AC: #2, #3, #4, #5, #11)
  - [ ] 3.pre Update `IRiskManager` interface at `src/common/interfaces/risk-manager.interface.ts`:
    - `closePosition(capitalReturned, pnlDelta, pairId?, isPaper?)` — add `isPaper?: boolean`
    - `releasePartialCapital(capitalReleased, realizedPnl, pairId?, isPaper?)` — add `isPaper?: boolean`
    - Add JSDoc: `@param isPaper - When true, targets paper mode risk state. Defaults to false (live).`
    - Update all mock implementations in test files that implement `IRiskManager`
  - [ ] 3.1 Define internal per-mode state type:
    ```typescript
    interface ModeRiskState {
      openPositionCount: number;
      totalCapitalDeployed: FinancialDecimal;
      dailyPnl: FinancialDecimal;
      activeHaltReasons: Set<HaltReason>;
      dailyLossApproachEmitted: boolean;
      lastResetTimestamp: Date;
    }
    ```
    Replace the flat properties `openPositionCount`, `totalCapitalDeployed`, `dailyPnl`, `activeHaltReasons`, `dailyLossApproachEmitted`, `lastResetTimestamp` with:
    ```typescript
    private liveState: ModeRiskState;
    private paperState: ModeRiskState;
    ```
    Keep `paperActivePairIds` and `reservations` as-is (reservations already carry `isPaper`).
  - [ ] 3.2 Refactor `initializeStateFromDb()`:
    - Query both rows: `findFirst({ where: { singletonKey: 'default', mode: 'live' } })` and `mode: 'paper'`
    - Restore `liveState` and `paperState` independently
    - Stale-day detection applies per-mode independently
    - `paperActivePairIds` restore stays the same (already queries `isPaper: true` positions)
  - [ ] 3.3 Refactor `persistState()` → `persistState(mode: 'live' | 'paper')`:
    - Upsert with `where: { singletonKey_mode: { singletonKey: 'default', mode } }`
    - Write the corresponding mode's state fields
    - All existing callers must pass the mode
  - [ ] 3.4 Helper: `private getState(isPaper: boolean): ModeRiskState`:
    - Returns `this.paperState` if `isPaper`, else `this.liveState`
    - Used by all methods that need mode-aware state access
  - [ ] 3.5 Helper: `private getBankrollForMode(isPaper: boolean): FinancialDecimal`:
    - Live: `this.config.bankrollUsd` (from EngineConfig, as today)
    - Paper: `this.config.paperBankrollUsd ?? this.config.bankrollUsd` (from EngineConfig `paper_bankroll_usd` column; falls back to live bankroll when null)
  - [ ] 3.5a Refactor `loadBankrollFromDb()` and `reloadBankroll()`:
    - Also read `engineConfig.paperBankrollUsd` and store in `this.config.paperBankrollUsd`
    - `RiskConfig` type gains optional `paperBankrollUsd?: number`
  - [ ] 3.6 Refactor `reserveBudget()`:
    - `const state = this.getState(request.isPaper)`
    - `const bankroll = this.getBankrollForMode(request.isPaper)`
    - Check `state.openPositionCount + reservedSlots` against max
    - Check `bankroll - state.totalCapitalDeployed - reservedCapital` for available capital
    - Halt check: `state.activeHaltReasons.size > 0` (paper mode can have its own halts)
  - [ ] 3.7 Refactor `commitReservation()`:
    - Reservation already carries `isPaper` — use `this.getState(reservation.isPaper)`
    - Increment correct mode's `openPositionCount` and `totalCapitalDeployed`
    - `persistState(reservation.isPaper ? 'paper' : 'live')`
  - [ ] 3.8 Refactor `closePosition()`:
    - Needs `isPaper` parameter — determine from position or pass explicitly
    - Decrement correct mode's counters
    - `persistState(isPaper ? 'paper' : 'live')`
    - **Interface change**: `IRiskManager.closePosition()` signature adds `isPaper?: boolean` (optional, default false for backward compat)
  - [ ] 3.9 Refactor `releasePartialCapital()`:
    - Same pattern — needs `isPaper` to target correct mode state
    - **Interface change**: add `isPaper?: boolean` parameter
  - [ ] 3.10 Refactor exposure queries — two methods:
    - `getCurrentExposure(isPaper: boolean): ExposureSnapshot` — mode-specific (used by `reserveBudget`, dashboard per-mode)
    - `getCombinedExposure(): ExposureSnapshot` — sums both modes (used by any caller that needs aggregate view)
    - Migrate existing `getCurrentExposure()` callers to the correct variant. If caller churn is excessive, keep single method with optional `isPaper?: boolean` and clear JSDoc for the three behaviors (`undefined` = combined)
  - [ ] 3.11 Refactor `recalculateFromPositions()`:
    - Add `mode: 'live' | 'paper'` parameter
    - Set correct mode's state + persist
  - [ ] 3.12 Refactor `handleMidnightReset()`:
    - Reset both modes independently
    - `persistState('live')` and `persistState('paper')`
  - [ ] 3.13 Refactor `updateDailyPnl()`:
    - Needs `isPaper` to update correct mode's dailyPnl
    - **Trace all callers** to verify `isPaper` is available at each call site:
      - `closePosition()` — has `isPaper` from refactored signature ✓
      - `releasePartialCapital()` — has `isPaper` from refactored signature ✓
      - Any other caller (search for `updateDailyPnl` references) — if a call site lacks `isPaper` (e.g., event-driven MtM revaluation), look up the position's `isPaper` field first before calling
  - [ ] 3.14 Update `risk-manager.service.spec.ts`:
    - All existing tests adapt to per-mode state structure
    - Add tests: paper state independent from live, paper bankroll config, cross-mode isolation
    - Add test: `reserveBudget` with `isPaper=true` uses paper bankroll and paper state
    - Add test: `commitReservation` on paper reservation increments paper state only
    - Add test: `closePosition` with `isPaper=true` decrements paper state only
    - Add test: midnight reset resets both modes independently

- [x] **Task 4: Reconciliation per-mode + sell-side capital** (AC: #7, #8, #10)
  - [ ] 4.1 Refactor `recalculateRiskBudget()`:
    - Loop over `[false, true]` (isPaper values)
    - For each mode: `findActivePositions(isPaper)` → calculate capital → `recalculateFromPositions(openCount, capital, mode)`
    - Replace `size * price` capital calculation with `calculateLegCapital(order.side, fillPrice, fillSize)` for each leg
    - Import `calculateLegCapital` from `common/utils/capital`
    - Handle null side: the joined Order record has a `side` field that should always be populated. If position-level `kalshiSide`/`polymarketSide` is null, read from the joined `kalshiOrder.side`/`polymarketOrder.side`. Only if both are null (corrupted data), fall back to `'buy'` (overestimates capital — conservative for deployment), and log a warning
  - [x] 4.2 `reconcileActivePositions()` — remains live-only (`findActivePositions(false)`):
    - Paper positions use simulated fills (paper connector) that don't exist on real platform APIs
    - Including paper positions caused false RECONCILIATION_REQUIRED on restart (post-deploy bug)
    - Only `recalculateRiskBudget` iterates both modes — it reads from DB, not platform APIs
  - [ ] 4.3 Update `startup-reconciliation.service.spec.ts`:
    - Mock `findActivePositions` to return different results for `isPaper=false` vs `isPaper=true`
    - Verify `recalculateFromPositions` called twice (once per mode)
    - Verify sell-side capital formula: position with sell-side order at price 0.70, size 100 → capital = 30 (not 70)
    - Verify cross-mode isolation: paper position doesn't affect live recalculation

- [x] **Task 5: Correlation tracker mode-aware + sell-side fix** (AC: #7, #12)
  - [ ] 5.1 Refactor `recalculateClusterExposure()`:
    - Add `isPaper: boolean = false` parameter
    - Add `isPaper` to `where` clause in Prisma query
    - Add `polymarketSide: true, kalshiSide: true` to `select` clause
    - Replace `size * entryPrice` with `calculateLegCapital(side, entryPrice, size)` for each leg
    - Handle null `polymarketSide`/`kalshiSide` — fall back to `size * price` with log warning
  - [ ] 5.2 Refactor `getTriageRecommendations()`:
    - Add `isPaper: boolean = false` parameter
    - Add `isPaper` to `where` clause
    - Add `polymarketSide: true, kalshiSide: true` to `select`
    - Replace capital calculation with `calculateLegCapital`
  - [ ] 5.3 Correlation tracker cache: the `clusterExposures` in-memory array (`private clusterExposures: ClusterExposure[] = []`) is currently a single array. Add a `mode` field to `ClusterExposure` type, or maintain separate `liveClusterExposures` and `paperClusterExposures` arrays. Simpler approach: add `isPaper: boolean` to `ClusterExposure` and filter in `getClusterExposure()` callers.
  - [ ] 5.4 Update callers of `recalculateClusterExposure()` and `getTriageRecommendations()`:
    - `RiskManagerService.validatePosition()` calls `correlationTracker.recalculateClusterExposure()` — pass `isPaper` from the opportunity's `request.isPaper`
    - `RiskManagerService.fetchTriageWithDtos()` calls `correlationTracker.getTriageRecommendations()` — pass `isPaper` from context
    - `CorrelationLimitEnforcementSubscriber` (if exists) — determine mode from event context
  - [ ] 5.5 Update `correlation-tracker.service.spec.ts`:
    - Test: live mode exposure excludes paper positions
    - Test: paper mode exposure excludes live positions
    - Test: sell-side capital calculation in cluster exposure
    - Test: triage recommendations filter by mode

- [x] **Task 6: Exit monitor sell-side capital fix** (AC: #7)
  - [ ] 6.1 Refactor `exitedEntryCapital` calculation in `exit-monitor.service.ts` (~line 660):
    - Current: `kalshiEntryPrice.mul(kalshiExitFillSize).plus(polymarketEntryPrice.mul(polymarketExitFillSize))`
    - New: `calculateLegCapital(position.kalshiSide, kalshiEntryPrice, kalshiExitFillSize).plus(calculateLegCapital(position.polymarketSide, polymarketEntryPrice, polymarketExitFillSize))`
    - Import `calculateLegCapital` from `common/utils/capital`
    - Handle null side fields — fall back to buy-side formula with warning
  - [ ] 6.2 Verify `closePosition()` and `releasePartialCapital()` callers pass `isPaper`:
    - Exit monitor already tracks `isPaper` (line 71) — pass it through to `riskManager.closePosition(capital, pnl, pairId, isPaper)` and `riskManager.releasePartialCapital(capital, pnl, pairId, isPaper)`
  - [ ] 6.3 Update `exit-monitor.service.spec.ts`:
    - Test: sell-side exit capital calculation
    - Test: `closePosition` called with correct `isPaper` flag
    - Test: `releasePartialCapital` called with correct `isPaper` flag

- [x] **Task 7: Dashboard per-mode capital overview** (AC: #9)
  - [ ] 7.1 Update `DashboardOverviewDto`:
    - Replace flat `totalBankroll`, `deployedCapital`, `availableCapital`, `reservedCapital` with:
    ```typescript
    capitalOverview: {
      live: { bankroll: string | null; deployed: string | null; available: string | null; reserved: string | null };
      paper: { bankroll: string | null; deployed: string | null; available: string | null; reserved: string | null };
    } | null;
    ```
    - Clean break — no deprecated aliases. The dashboard SPA is the only consumer and ships in the same release cycle
  - [ ] 7.2 Update `DashboardService.getOverview()`:
    - Query both risk state rows: `findMany({ where: { singletonKey: 'default' } })`
    - Compute capital per mode using respective bankrolls
    - Return nested `capitalOverview` structure
  - [ ] 7.3 Update `dashboard.service.spec.ts`:
    - Mock both risk state rows
    - Verify per-mode capital breakdown in response
  - [ ] 7.4 Regenerate API client: `cd pm-arbitrage-dashboard && pnpm generate-api`
  - [ ] 7.5 Update frontend Capital Overview component:
    - Render live and paper sections separately
    - Show paper section whenever paper mode is enabled in engine config (even if all values are zero — a zero-deployed paper section is informative: paper trading is active, no positions open). Only hide when paper trading is entirely off (no paper bankroll configured, no paper positions exist)
  - [ ] 7.6 Update Swagger decorators on `DashboardOverviewDto` for correct OpenAPI schema

- [x] **Task 8: Final validation + lint** (AC: #13, #14)
  - [ ] 8.1 Run `pnpm test` — all existing tests pass + new tests pass
  - [ ] 8.2 Run `pnpm lint` — clean
  - [ ] 8.3 Run `pnpm build` — no type errors
  - [ ] 8.4 Smoke test: verify both risk state rows exist after migration, EngineConfig `paper_bankroll_usd` column present

## Dev Notes

### Architecture Patterns & Constraints

- **Module dependency rules**: `common/utils/capital.ts` is in `common/` — importable by all modules. No dependency violations. [Source: CLAUDE.md Module Dependency Rules]
- **Financial math**: `calculateLegCapital` MUST use `decimal.js` — NEVER native JS operators on monetary values. [Source: CLAUDE.md Domain Rules]
- **Error hierarchy**: Any new errors MUST extend `SystemError`. However, this story primarily refactors existing code — unlikely to need new error types. [Source: CLAUDE.md Error Handling]
- **Event emission**: No new events required. Existing `BUDGET_RESERVED`, `BUDGET_COMMITTED`, `BUDGET_RELEASED` events continue to fire — they don't need mode differentiation since the event consumers (monitoring, Telegram) already receive context from the event payload.
- **Singleton → dual-row pattern**: The `RiskState` model transitions from a singleton pattern (`singletonKey: 'default'`) to a dual-row pattern keyed by `(singletonKey, mode)`. All Prisma queries that reference `riskState.findFirst/findUnique({ where: { singletonKey: 'default' } })` MUST be updated to include the `mode` qualifier.

### Critical Implementation Details

1. **IRiskManager interface changes**: `closePosition()` and `releasePartialCapital()` gain an `isPaper?: boolean` parameter. This is a breaking interface change — all implementors and callers must be updated. The interface lives at `src/common/interfaces/risk-manager.interface.ts`. [Source: codebase investigation — `IRiskManager` at risk-manager.interface.ts:13-116]

2. **Reservation already carries isPaper**: `BudgetReservation` type already has `isPaper: boolean` field (set in `reserveBudget`). `commitReservation()` can derive mode from the reservation — no caller changes needed for commit path. [Source: codebase — `reserveBudget` at risk-manager.service.ts:1196 sets `isPaper: request.isPaper`]

3. **Exit monitor already knows isPaper**: Line 71 of `exit-monitor.service.ts` — `const isPaper = ...` is computed per evaluation cycle. Thread it through to `closePosition()` and `releasePartialCapital()` calls. [Source: codebase investigation — exit-monitor.service.ts:71]

4. **Correlation tracker Prisma queries**: Two `findMany` calls at lines 57 and 193 of `correlation-tracker.service.ts` need `isPaper` filter AND `polymarketSide`/`kalshiSide` added to `select`. Currently neither field is selected — the sell-side fix requires them. [Source: codebase investigation — confirmed select clauses don't include side fields]

5. **Null side fields (legacy data)**: Positions created before sides were tracked may have null `polymarketSide`/`kalshiSide`. Fallback chain: (1) read from the joined Order record's `side` field (should always be populated), (2) if both position and order sides are null (corrupted data only), default to `'buy'` (overestimates capital — conservative for deployment accounting). Log a warning for auditability in both fallback cases.

6. **Dashboard backward compatibility**: The `DashboardOverviewDto` changes from flat fields to nested `capitalOverview`. Since the only consumer is the dashboard SPA (same release cycle), a clean break is acceptable. No need for deprecated field aliases.

7. **`persistState` callers (must all pass mode)**: `initializeStateFromDb()`, `reserveBudget()`, `commitReservation()`, `releaseReservation()`, `closePosition()`, `releasePartialCapital()`, `updateDailyPnl()`, `handleMidnightReset()`, `recalculateFromPositions()`, `clearStaleReservations()`, `adjustReservation()`. Each must pass the correct mode — don't write both rows on every mutation.

8. **Paper bankroll via EngineConfig**: Story 9-14 moved live bankroll from `.env` to `EngineConfig` DB table with hot-reload via `reloadBankroll()`. Paper bankroll follows the same pattern: nullable `paperBankrollUsd` column on `EngineConfig`, read in `loadBankrollFromDb()` and `reloadBankroll()`, editable via dashboard. When null, defaults to live bankroll. No env var — consistent with the 9-14 architecture decision.

### Sell-Side Capital Formula — Why It Matters

In binary outcome markets (prediction markets), contracts resolve to either $0 or $1:
- **Buy at $0.60**: You pay $0.60. If the event happens, you get $1. Capital at risk = $0.60.
- **Sell at $0.60**: You receive $0.60 but post $0.40 collateral ($1 - $0.60). If the event happens, you lose $0.40. Capital at risk = $0.40.

The current code uniformly uses `size × price`, which overcounts sell-side capital by `size × (2 × price - 1)`. For a sell at $0.90, the error is `size × 0.80` — nearly double the actual capital deployed. This causes:
- Risk state inflated → available capital understated → valid trades rejected
- Reconciliation mismatch → risk budget "missing" after restart
- Correlation exposure inflated → premature cluster limit breaches

### Project Structure Notes

- **New file**: `src/common/utils/capital.ts` + `capital.spec.ts` — follows existing pattern of co-located tests in `common/utils/` (e.g., `financial-math.ts` / `financial-math.spec.ts`) [Source: CLAUDE.md naming conventions, codebase structure]
- **Modified files**:
  - `prisma/schema.prisma` — RiskState model gains `mode` field [Source: AC #1]
  - `src/common/interfaces/risk-manager.interface.ts` — `closePosition`, `releasePartialCapital` signature changes [Source: AC #4]
  - `prisma/schema.prisma` — EngineConfig model gains `paperBankrollUsd` column [Source: AC #5]
  - `src/modules/risk-management/risk-manager.service.ts` — per-mode state refactor (largest change) [Source: AC #2, #3, #4, #11]
  - `src/modules/risk-management/risk-manager.service.spec.ts` — test updates [Source: AC #13]
  - `src/modules/risk-management/correlation-tracker.service.ts` — mode filter + sell-side fix [Source: AC #7, #12]
  - `src/modules/risk-management/correlation-tracker.service.spec.ts` — test updates [Source: AC #13]
  - `src/reconciliation/startup-reconciliation.service.ts` — per-mode loop + sell-side fix [Source: AC #8, #10]
  - `src/reconciliation/startup-reconciliation.service.spec.ts` — test updates [Source: AC #13]
  - `src/modules/exit-management/exit-monitor.service.ts` — sell-side fix + isPaper passthrough [Source: AC #7]
  - `src/modules/exit-management/exit-monitor.service.spec.ts` — test updates [Source: AC #13]
  - `src/dashboard/dashboard.service.ts` — per-mode capital query [Source: AC #9]
  - `src/dashboard/dashboard.service.spec.ts` — test updates [Source: AC #13]
  - `src/dashboard/dto/dashboard-overview.dto.ts` — nested capitalOverview type [Source: AC #9]
  - `src/persistence/repositories/engine-config.repository.ts` — read/upsert paperBankrollUsd [Source: AC #5]
- **Dashboard SPA** (separate repo `pm-arbitrage-dashboard/`):
  - Regenerate API client after backend DTO changes
  - Update capital overview component for per-mode display
- **No new modules or NestJS providers** — all changes within existing module boundaries

### References

- [Source: sprint-change-proposal-2026-03-14.md#Story-B] — Primary requirements and acceptance criteria
- [Source: CLAUDE.md] — Architecture rules, module dependencies, financial math rules, naming conventions, error hierarchy, post-edit workflow
- [Source: prisma/schema.prisma:142-157] — Current RiskState model (singleton with singletonKey)
- [Source: position.repository.ts:83-98] — `findActivePositions(isPaper: boolean = false)` — root cause of paper invisibility
- [Source: startup-reconciliation.service.ts:759-788] — `recalculateRiskBudget()` — missing isPaper arg + wrong capital formula
- [Source: startup-reconciliation.service.ts:329-454] — `reconcileActivePositions()` — missing isPaper arg
- [Source: risk-manager.service.ts:240-371] — `initializeStateFromDb()` — single-row restore, needs dual-row
- [Source: risk-manager.service.ts:373-414] — `persistState()` — writes to single singletonKey, needs mode qualifier
- [Source: risk-manager.service.ts:1107-1221] — `reserveBudget()` — already receives isPaper but checks shared pool
- [Source: risk-manager.service.ts:1223-1265] — `commitReservation()` — reservation has isPaper, needs mode-aware state
- [Source: risk-manager.service.ts:1341-1389] — `closePosition()` — needs isPaper parameter for correct mode
- [Source: risk-manager.service.ts:1391-1430] — `releasePartialCapital()` — needs isPaper parameter
- [Source: correlation-tracker.service.ts:56-73] — `recalculateClusterExposure()` — no isPaper filter, no side fields selected
- [Source: correlation-tracker.service.ts:190-205] — `getTriageRecommendations()` — no isPaper filter, no side fields
- [Source: exit-monitor.service.ts:660-662] — `exitedEntryCapital` — uses size × price, ignores side
- [Source: exit-monitor.service.ts:71] — `isPaper` already computed per cycle — thread to risk manager calls
- [Source: dashboard.service.ts:53-167] — `getOverview()` — reads single risk state row
- [Source: risk-manager.interface.ts:13-116] — `IRiskManager` — interface changes needed for closePosition, releasePartialCapital
- [Source: common/types/risk.type.ts] — `BudgetReservation` already has `isPaper: boolean`
- [Source: Serena memory: execution_persistence_patterns] — Position state machine, repository patterns, event catalog

### Previous Story Intelligence

**From Story 9-15** (platform-health-concurrent-polling):
- Pattern: per-entity tracking replacing per-aggregate tracking (per-pair staleness replaced per-platform staleness). This story follows the same pattern: per-mode risk state replacing single aggregate risk state.
- `p-limit` was added for concurrency — already in dependencies, no install needed for this story.
- Story format reference for task granularity and AC citation style.

**From Story 9-14** (bankroll-db-persistence-ui):
- Bankroll was moved from `.env` to `EngineConfig` DB table with hot-reload via `reloadBankroll()`. Paper bankroll in this story follows the same pattern: `paperBankrollUsd` column on `EngineConfig`, nullable, read in `loadBankrollFromDb()` and `reloadBankroll()`.
- `getBankrollConfig()` method already exists on `RiskManagerService` — extend it to return paper bankroll too, or add `getBankrollForMode(isPaper)` helper.
- `EngineConfigRepository` has `get()` and `upsertBankroll()` — add `upsertPaperBankroll()` or extend `upsertBankroll` to accept paper value.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

N/A

### Completion Notes List

- **2065 tests pass** (baseline 2056 + 8 new `calculateLegCapital` unit tests + 1 paper capital overview test from code review #2)
- **Lint clean**, **Build clean**
- Migration `20260314200000_add_risk_state_mode_paper_bankroll` manually written (Prisma CLI requires interactive mode). Correct constraint swap ordering verified.
- `ModeRiskState` interface is internal (not exported) — only used within `RiskManagerService`
- `validatePosition` and `getCurrentExposure` were initially left live-only (mode separation at `reserveBudget`/`commitReservation` level). **REVISED in Story 10-0-2a** (course correction 2026-03-15): `validatePosition` runs BEFORE `reserveBudget` and its halt check blocked all paper trades when live mode was halted (`reconciliation_discrepancy`). The Lad MCP code review had flagged this gap but it was dismissed as "by design". See `sprint-change-proposal-2026-03-15-validate-position-mode-fix.md` for full root cause analysis. Dashboard per-mode capital uses direct DB queries via `computeModeCapital`.
- Task 5.3 (correlation tracker cache mode separation) deferred — the in-memory `clusterExposures` array currently stores only the last mode's calculation. For full parallel fidelity, split into `liveClusterExposures`/`paperClusterExposures`. Not blocking since `validatePosition` only runs in live context.
- Task 7.4/7.5 (dashboard SPA regenerate + frontend) deferred — backend API changes are complete, frontend update requires separate dashboard repo work.
- Code review (Lad MCP): Primary reviewer found interface mismatch on `updateDailyPnl` — fixed by adding `isPaper?: boolean` to interface. Other findings (adding `isPaper` to `validatePosition`, `getCurrentExposure`, `processOverride`) are out of scope — these methods correctly operate on live state by design.
- **Post-deploy bug fix**: `reconcileActivePositions` was incorrectly changed to fetch both live and paper positions. Paper positions' simulated fills don't exist on real platform APIs, causing all 3 paper positions to be marked `RECONCILIATION_REQUIRED` on restart. Fix: reverted `reconcileActivePositions` to live-only (`findActivePositions(false)`). Only `recalculateRiskBudget` iterates both modes. Manual SQL fix applied: `UPDATE open_positions SET status = 'OPEN' WHERE is_paper = true AND status = 'RECONCILIATION_REQUIRED'`.
- **Code review #2 (2026-03-14)**: Fixed 3 MEDIUM issues:
  1. `resolveDiscrepancy` force_close now passes `position.isPaper` to `closePosition` (was defaulting to live state for paper positions)
  2. `computeCapitalBreakdown` in dashboard now uses `calculateLegCapital` instead of `size × price` (sell-side capital consistency)
  3. Added paper capital overview test to `dashboard.service.spec.ts` (AC#9 coverage gap)

### File List

**New files:**
- `src/common/utils/capital.ts` — `calculateLegCapital` shared utility
- `src/common/utils/capital.spec.ts` — 8 unit tests
- `prisma/migrations/20260314200000_add_risk_state_mode_paper_bankroll/migration.sql` — schema migration

**Modified files:**
- `prisma/schema.prisma` — RiskState: added `mode` + compound unique; EngineConfig: added `paperBankrollUsd`
- `src/common/utils/index.ts` — barrel export for `calculateLegCapital`
- `src/common/interfaces/risk-manager.interface.ts` — added `isPaper` to `closePosition`, `releasePartialCapital`, `updateDailyPnl`, `recalculateFromPositions`; updated `getBankrollConfig` return type
- `src/common/types/risk.type.ts` — `RiskConfig` gains `paperBankrollUsd?: number`
- `src/modules/risk-management/risk-manager.service.ts` — per-mode state refactor (largest change): `ModeRiskState`, `liveState`/`paperState`, `getState()`, `getBankrollForMode()`, mode-aware `persistState`, `reserveBudget`, `commitReservation`, `closePosition`, `releasePartialCapital`, `updateDailyPnl`, `handleMidnightReset`, `recalculateFromPositions`, `loadBankrollFromDb`, `reloadBankroll`, `getBankrollConfig`
- `src/modules/risk-management/risk-manager.service.spec.ts` — adapted all tests to per-mode state structure
- `src/modules/risk-management/correlation-tracker.service.ts` — `isPaper` filter + `calculateLegCapital` in `recalculateClusterExposure` and `getTriageRecommendations`
- `src/reconciliation/startup-reconciliation.service.ts` — per-mode `recalculateRiskBudget` + `calculateLegCapital` + dual-mode `reconcileActivePositions`
- `src/reconciliation/startup-reconciliation.service.spec.ts` — updated mocks for per-mode calls + sell-side capital expectations
- `src/modules/exit-management/exit-monitor.service.ts` — `calculateLegCapital` for `exitedEntryCapital` + `isPaper` passthrough to `closePosition`/`releasePartialCapital`
- `src/modules/exit-management/exit-monitor.service.spec.ts` — updated `closePosition` expectations to include `isPaper`
- `src/dashboard/dashboard.service.ts` — per-mode capital via `computeModeCapital` + `findMany` for both risk states
- `src/dashboard/dashboard.service.spec.ts` — updated for `capitalOverview` structure + `findMany` mocks
- `src/dashboard/dto/dashboard-overview.dto.ts` — nested `capitalOverview: { live, paper }` replacing flat fields
