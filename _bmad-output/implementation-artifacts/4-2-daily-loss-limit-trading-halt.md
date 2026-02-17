# Story 4.2: Daily Loss Limit & Trading Halt

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want trading to halt automatically when my daily loss limit is reached,
so that a bad day can't spiral into catastrophic losses.

**FRs covered:** FR-RM-03 (halt trading at 5% daily loss limit with high-priority alert)

## Acceptance Criteria

### AC1: Daily Loss Limit Halts Trading

**Given** the risk manager is tracking daily P&L
**When** cumulative daily losses reach 5% of bankroll (FR-RM-03)
**Then** all trading is halted immediately by setting `tradingHalted = true` in the risk manager state
**And** a `LimitBreachedEvent` with `limitType: 'dailyLoss'` and critical severity is emitted via EventEmitter2
**And** the halt is logged with daily P&L, bankroll amount, loss percentage, and timestamp
**And** the updated risk state (including `dailyPnl` and halt flag) is persisted to the `risk_states` table
**And** `validatePosition()` rejects ALL subsequent opportunities with reason `"Trading halted: daily loss limit breached"` — short-circuiting before open-pairs or position sizing checks
**And** no `RiskLimitError` is thrown on halt rejection (rejection is returned in `RiskDecision`, not thrown)

### AC2: Daily Loss Limit Approach Warning (Fire-Once Per Day)

**Given** the risk manager is tracking daily P&L
**When** losses reach 80% of the daily limit (i.e., 4% of bankroll) **for the first time that day**
**Then** a `LimitApproachedEvent` with `limitType: 'dailyLoss'` and warning severity is emitted
**And** the event includes current loss amount, daily loss limit, and `percentUsed`
**And** a `dailyLossApproachEmitted` flag is set to prevent repeated emission on subsequent `updateDailyPnl` calls while in the 80-100% range
**And** the flag resets at midnight UTC along with the daily P&L counter

### AC3: Daily P&L Update Method

**Given** the `IRiskManager` interface needs a way for execution to report realized P&L
**When** this story is implemented
**Then** the interface exposes `updateDailyPnl(pnlDelta: Decimal): Promise<void>`
**And** calling `updateDailyPnl` with a negative delta accumulates losses in the in-memory `dailyPnl` tracker
**And** calling `updateDailyPnl` with a positive delta accumulates gains
**And** after each update, the daily loss limit check runs (AC1 and AC2 logic)
**And** the updated `dailyPnl` is persisted to the `risk_states` table

> **Note:** Until Epic 5 execution integration, no caller invokes `updateDailyPnl()`. This story creates the method and tests it; Epic 5 will call it after trade settlement.

### AC4: Midnight UTC Daily Reset

**Given** trading was halted due to daily loss limit (or daily P&L accumulated over the day)
**When** UTC midnight arrives
**Then** the daily P&L counter resets to 0
**And** the `tradingHalted` flag is cleared (if it was set due to daily loss)
**And** the `lastResetTimestamp` is updated to the current UTC midnight time
**And** the reset is logged with previous day's final P&L
**And** the updated state is persisted to the `risk_states` table

### AC5: Daily Loss Limit Configuration

**Given** the daily loss limit percentage is configured via environment
**When** the engine starts
**Then** `RISK_DAILY_LOSS_PCT` is loaded from environment config (default: 0.05 = 5%)
**And** invalid values (negative, zero, or >1.0) are rejected at startup via `ConfigValidationError`
**And** the daily loss limit in USD is calculated as `bankrollUsd * dailyLossPct`
**And** the validated config is logged at startup

### AC6: Persistence Failure Resilience

**Given** `persistState()` is called after a daily P&L update or midnight reset
**When** the database write fails
**Then** the error is logged with full context (operation, current state, error details)
**And** the in-memory state is NOT rolled back (the in-memory state remains the source of truth)
**And** the service continues operating with in-memory state
**And** the next `persistState()` call will attempt to write the current state again

> **Rationale:** Rolling back in-memory state on DB failure would create a dangerous inconsistency where the risk manager believes it has more budget than it actually does. It's safer to keep the stricter in-memory state and retry persistence.

### AC7: Risk State Initialization on Startup

**Given** the engine restarts
**When** `onModuleInit` runs
**Then** `dailyPnl` and `lastResetTimestamp` are restored from the `risk_states` table
**And** if `lastResetTimestamp` is before today's UTC midnight, a reset is performed (clearing `dailyPnl` to 0 and updating the timestamp)
**And** if `lastResetTimestamp` is null but `dailyPnl` is non-zero, treat as corrupted state: reset `dailyPnl` to 0, clear halt, set `lastResetTimestamp` to today's midnight, and log a warning
**And** if `dailyPnl` is at or beyond the loss limit (same day), `tradingHalted` is set to `true`

### AC8: RiskExposure and RiskConfig Updated

**Given** dashboard and other consumers query risk exposure
**When** `getCurrentExposure()` is called
**Then** it includes `dailyPnl` and `dailyLossLimitUsd` fields
**And** the `RiskConfig` type includes `dailyLossPct`

### AC9: Prisma Schema — Add tradingHalted Column

**Given** the halt state needs to survive restarts
**When** this story is implemented
**Then** a `trading_halted` boolean column (default `false`) is added to the `risk_states` table via Prisma migration
**And** the `halt_reason` text column (nullable) is added to record why trading was halted

### AC10: All Tests Pass

**Given** all Story 4.2 changes are complete
**When** `pnpm test` runs
**Then** all existing tests continue to pass (397 baseline from Story 4.1)
**And** new tests for daily loss limit add 15+ test cases
**And** `pnpm lint` passes with no errors

## Tasks / Subtasks

- [x] Task 1: Prisma Migration — Add halt columns to risk_states (AC: #9)
  - [x]1.1 Add `tradingHalted Boolean @default(false) @map("trading_halted")` to `RiskState` model
  - [x]1.2 Add `haltReason String? @map("halt_reason")` to `RiskState` model
  - [x]1.3 Run `pnpm prisma migrate dev --name add-trading-halt-columns`
  - [x]1.4 Run `pnpm prisma generate`

- [x] Task 2: Update RiskConfig and RiskExposure Types (AC: #5, #8)
  - [x]2.1 Add `dailyLossPct: number` to `RiskConfig` in `common/types/risk.type.ts`
  - [x]2.2 Add `dailyPnl: Decimal` and `dailyLossLimitUsd: Decimal` to `RiskExposure`
  - [x]2.3 Add `dailyPnl?: Decimal` (optional) to `RiskDecision` — optional to avoid breaking existing Story 4.1 tests that return `RiskDecision` without this field

- [x] Task 3: Update IRiskManager Interface (AC: #3)
  - [x]3.1 Add `updateDailyPnl(pnlDelta: unknown): Promise<void>` to `IRiskManager` in `common/interfaces/risk-manager.interface.ts`
  - [x]3.2 Add `isTradingHalted(): boolean` to `IRiskManager`

> **Note:** Parameter type is `unknown` to avoid importing `Decimal` in `common/interfaces/` — the service implementation casts to `Decimal`.

- [x] Task 4: Add Environment Config Variable (AC: #5)
  - [x]4.1 Add `RISK_DAILY_LOSS_PCT=0.05` to `.env.example` with comment
  - [x]4.2 Add `RISK_DAILY_LOSS_PCT=0.05` to `.env.development`
  - [x]4.3 Add to all e2e test env setups (`test/app.e2e-spec.ts`, `test/core-lifecycle.e2e-spec.ts`, `test/logging.e2e-spec.ts`)

- [x] Task 5: Implement Daily Loss Logic in RiskManagerService (AC: #1, #2, #3, #6, #7)
  - [x]5.1 Add `dailyPnl: FinancialDecimal`, `tradingHalted: boolean`, `haltReason: string | null`, and `dailyLossApproachEmitted: boolean` to in-memory state
  - [x]5.2 Add `dailyLossPct` to config validation in `onModuleInit` (reject <=0 or >1.0)
  - [x]5.3 Update `initializeStateFromDb()` to restore `dailyPnl`, `lastResetTimestamp`, `tradingHalted`, `haltReason` from DB
  - [x]5.4 Add stale-day detection in `initializeStateFromDb()`: if `lastResetTimestamp` < today's UTC midnight, reset `dailyPnl` to 0 and clear halt
  - [x]5.5 Implement `updateDailyPnl(pnlDelta)`: accumulate delta, check 80% approach threshold (AC2), check 100% breach threshold (AC1)
  - [x]5.6 On breach: set `tradingHalted = true`, `haltReason = 'daily_loss_limit'`, emit `LimitBreachedEvent`, persist state
  - [x]5.7 On approach (80%): emit `LimitApproachedEvent` with `limitType: 'dailyLoss'` only if `!dailyLossApproachEmitted`, then set flag to `true`
  - [x]5.8 Update `validatePosition()`: add halt check as FIRST check before open-pairs and position sizing
  - [x]5.9 Implement `isTradingHalted()`: return `this.tradingHalted`
  - [x]5.10 Update `getCurrentExposure()` to include `dailyPnl` and `dailyLossLimitUsd`
  - [x]5.11 Update `persistState()` to write `dailyPnl`, `lastResetTimestamp`, `tradingHalted`, `haltReason`

- [x] Task 6: Implement Midnight UTC Reset (AC: #4)
  - [x]6.1 Verify `@nestjs/schedule` is in `package.json` — if missing, run `pnpm add @nestjs/schedule`
  - [x]6.2 Check `AppModule` first for `ScheduleModule.forRoot()` (NestJS convention). If not there, check `CoreModule`. Add to `AppModule` if neither has it. Do NOT register `.forRoot()` twice.
  - [x]6.3 Add `@Cron('0 0 0 * * *', { timeZone: 'UTC' })` method `handleMidnightReset()` to `RiskManagerService`
  - [x]6.4 In `handleMidnightReset()`: log previous day's P&L, reset `dailyPnl` to 0, reset `dailyLossApproachEmitted` to false, clear `tradingHalted` if `haltReason === 'daily_loss_limit'`, update `lastResetTimestamp`, persist state

- [x] Task 7: Write Tests (AC: #10)
  - [x]7.1 Test: `updateDailyPnl` accumulates negative delta correctly
  - [x]7.2 Test: `updateDailyPnl` accumulates positive delta correctly
  - [x]7.3 Test: trading halts when daily loss reaches 5% of bankroll
  - [x]7.4 Test: `LimitBreachedEvent` emitted with `limitType: 'dailyLoss'` on breach
  - [x]7.5 Test: `LimitApproachedEvent` emitted at 80% of daily loss limit
  - [x]7.6 Test: `LimitApproachedEvent` NOT emitted below 80%
  - [x]7.6b Test: `LimitApproachedEvent` NOT emitted on second call while still in 80-100% range (debounce flag)
  - [x]7.7 Test: `validatePosition` rejects all opportunities when trading halted
  - [x]7.8 Test: `validatePosition` short-circuits (no open-pairs check) when halted
  - [x]7.9 Test: midnight reset clears `dailyPnl` and `tradingHalted`
  - [x]7.10 Test: midnight reset logs previous day's P&L
  - [x]7.11 Test: startup stale-day detection resets if `lastResetTimestamp` is yesterday
  - [x]7.12 Test: startup restores halt state if `dailyPnl` exceeds limit and same day
  - [x]7.13 Test: config validation rejects invalid `RISK_DAILY_LOSS_PCT` (negative, zero, >1.0)
  - [x]7.14 Test: `getCurrentExposure` includes `dailyPnl` and `dailyLossLimitUsd`
  - [x]7.15 Test: `isTradingHalted` returns correct boolean
  - [x]7.16 Test: `persistState` writes `dailyPnl`, `lastResetTimestamp`, `tradingHalted`, `haltReason` to DB
  - [x]7.17 Test: `persistState` failure is logged but does not roll back in-memory state
  - [x]7.18 Test: startup with null `lastResetTimestamp` and non-zero `dailyPnl` resets P&L (corrupted state)
  - [x]7.19 Run full regression: `pnpm test` — all tests pass

- [x] Task 8: Lint & Final Check (AC: #10)
  - [x]8.1 Run `pnpm lint` and fix any issues
  - [x]8.2 Verify no import boundary violations per CLAUDE.md rules

## Dev Notes

### Known Deviation: Error Code Numbering vs PRD

The PRD error catalog lists `3001 = Daily Loss Limit Exceeded` and `3003 = Position Count Limit Reached`. Story 4.1 implemented a different numbering: `3001 = Position Size Exceeded`, `3002 = Max Open Pairs Exceeded`, `3003 = Daily Loss Limit Breached`. Since 4.1 is already shipped with 397 passing tests, this story follows 4.1's numbering (code 3003 for daily loss). This is a known, accepted deviation from the PRD error catalog.

### halt_reason as Typed Constant

The `halt_reason` DB column is `text` for flexibility, but in code treat it as a typed constant. Define a `HALT_REASONS` constant in the service:

```typescript
const HALT_REASONS = {
  DAILY_LOSS_LIMIT: 'daily_loss_limit',
} as const;
type HaltReason = (typeof HALT_REASONS)[keyof typeof HALT_REASONS] | null;
```

Story 4.3 (operator override) may add additional halt reasons. Using a constant now prevents magic strings and makes future extension clean.

### Architecture Constraints

- `RiskManagerService` lives in `src/modules/risk-management/` — same file modified from Story 4.1
- Allowed imports per CLAUDE.md dependency rules:
  - `modules/risk-management/` -> `common/` (interfaces, errors, events, types)
  - `modules/risk-management/` -> `persistence/` (via globally exported PrismaService)
  - `core/` -> `modules/risk-management/` (orchestrates via IRiskManager interface)
- **FORBIDDEN:** `risk-management/` must NOT import from `connectors/`, `modules/execution/`, or any other module directly
- The `@Cron` decorator from `@nestjs/schedule` is used directly in the service — no separate scheduler service needed for this story

### Daily Loss Limit Logic (Implementation Guide)

The daily loss check integrates into the existing `validatePosition()` as the **first check** before open-pairs and position sizing:

```typescript
async validatePosition(opportunity: unknown): Promise<RiskDecision> {
  // FIRST: Check daily loss halt (Story 4.2)
  if (this.tradingHalted) {
    return {
      approved: false,
      reason: 'Trading halted: daily loss limit breached',
      maxPositionSizeUsd: new FinancialDecimal(0),
      currentOpenPairs: this.openPositionCount,
      dailyPnl: this.dailyPnl,
    };
  }

  // THEN: Existing open-pairs check (Story 4.1)
  // THEN: Position sizing (Story 4.1)
  // ...
}
```

### updateDailyPnl Implementation Pattern

```typescript
async updateDailyPnl(pnlDelta: unknown): Promise<void> {
  const delta = new FinancialDecimal(pnlDelta as Decimal);
  this.dailyPnl = this.dailyPnl.add(delta);

  const dailyLossLimitUsd = new FinancialDecimal(this.config.bankrollUsd)
    .mul(new FinancialDecimal(this.config.dailyLossPct));

  // Check approach threshold (80%)
  const absLoss = this.dailyPnl.isNegative() ? this.dailyPnl.abs() : new FinancialDecimal(0);
  const percentUsed = absLoss.div(dailyLossLimitUsd).toNumber();

  if (percentUsed >= 1.0 && !this.tradingHalted) {
    this.tradingHalted = true;
    this.haltReason = 'daily_loss_limit';
    this.eventEmitter.emit(
      EVENT_NAMES.LIMIT_BREACHED,
      new LimitBreachedEvent('dailyLoss', absLoss.toNumber(), dailyLossLimitUsd.toNumber()),
    );
    this.logger.log({
      message: 'TRADING HALTED: Daily loss limit breached',
      data: { dailyPnl: this.dailyPnl.toString(), limit: dailyLossLimitUsd.toString(), percentUsed },
    });
  } else if (percentUsed >= 0.8 && percentUsed < 1.0 && !this.dailyLossApproachEmitted) {
    this.dailyLossApproachEmitted = true;
    this.eventEmitter.emit(
      EVENT_NAMES.LIMIT_APPROACHED,
      new LimitApproachedEvent('dailyLoss', absLoss.toNumber(), dailyLossLimitUsd.toNumber(), percentUsed),
    );
  }

  await this.persistState();
}
```

### Midnight Reset Implementation Pattern

```typescript
@Cron('0 0 0 * * *', { timeZone: 'UTC' })
async handleMidnightReset(): Promise<void> {
  const previousPnl = this.dailyPnl.toString();
  this.dailyPnl = new FinancialDecimal(0);
  this.lastResetTimestamp = new Date();

  this.dailyLossApproachEmitted = false;

  if (this.haltReason === HALT_REASONS.DAILY_LOSS_LIMIT) {
    this.tradingHalted = false;
    this.haltReason = null;
    this.logger.log({ message: 'Trading halt cleared by midnight reset' });
  }

  this.logger.log({
    message: 'Daily P&L reset at UTC midnight',
    data: { previousDayPnl: previousPnl, newDailyPnl: '0' },
  });

  await this.persistState();
}
```

### Stale-Day Detection on Startup

```typescript
// In initializeStateFromDb(), after loading from DB:
if (state.lastResetTimestamp) {
  const todayMidnight = new Date();
  todayMidnight.setUTCHours(0, 0, 0, 0);

  if (state.lastResetTimestamp < todayMidnight) {
    // Stale day — reset
    this.dailyPnl = new FinancialDecimal(0);
    this.tradingHalted = false;
    this.haltReason = null;
    this.lastResetTimestamp = todayMidnight;
    this.logger.log({ message: 'Stale-day detected on startup, daily P&L reset' });
    await this.persistState();
  }
} else {
  // No lastResetTimestamp — first run or corrupted state
  const todayMidnight = new Date();
  todayMidnight.setUTCHours(0, 0, 0, 0);
  this.lastResetTimestamp = todayMidnight;

  // Safety: if dailyPnl is non-zero with null timestamp, treat as corrupted — reset
  if (!this.dailyPnl.isZero()) {
    this.logger.warn({
      message: 'Corrupted state: non-zero dailyPnl with null lastResetTimestamp, resetting',
      data: { dailyPnl: this.dailyPnl.toString() },
    });
    this.dailyPnl = new FinancialDecimal(0);
    this.tradingHalted = false;
    this.haltReason = null;
    await this.persistState();
  }
}
```

### ScheduleModule Setup

Check `AppModule` **first** (NestJS convention for `.forRoot()` calls), then `CoreModule`. Add to `AppModule` if neither has it:

```typescript
import { ScheduleModule } from '@nestjs/schedule';

@Module({
  imports: [
    ScheduleModule.forRoot(),
    // ... existing imports
  ],
})
export class CoreModule {}
```

If `ScheduleModule.forRoot()` is already registered at the app level, do NOT register it again — just use `@Cron` directly in the service.

### DI Token Pattern (Unchanged from Story 4.1)

The `IRiskManager` token pattern from Story 4.1 remains — no changes needed to the module provider registration. The new `updateDailyPnl()` and `isTradingHalted()` methods are added to the interface but the DI wiring is already correct.

### What NOT to Do (Scope Guard)

- Do NOT implement operator risk override endpoint — that's Story 4.3
- Do NOT implement execution locking or budget reservation — that's Story 4.4
- Do NOT implement correlation cluster tracking — that's Epic 9
- Do NOT implement actual P&L calculation from trade fills — that's Epic 5 (this story only creates the `updateDailyPnl` method)
- Do NOT implement max drawdown tracking (25% hard limit from PRD) — that's a future story
- Do NOT create REST endpoints for risk state — that's Epic 7
- Do NOT add Telegram alerting for limit breach events — that's Epic 6 (monitoring subscribes to events)
- Do NOT modify the trading engine pipeline — the halt check is inside `validatePosition()`, not a new pipeline step
- Do NOT implement daily CSV summary at midnight — that's Story 6.3

### Existing Codebase Patterns to Follow

- **File naming:** kebab-case (`risk-manager.service.ts`)
- **Module registration:** See `risk-management.module.ts` (already exists from Story 4.1)
- **Logging:** NestJS `Logger` with structured JSON: `this.logger.log({ message, correlationId, data })`
- **Config access:** `ConfigService` from `@nestjs/config` (follow existing risk config validation pattern in `onModuleInit`)
- **Prisma access:** Inject `PrismaService` directly (globally available via `@Global()`)
- **Event emission:** `this.eventEmitter.emit(EVENT_NAMES.LIMIT_BREACHED, new LimitBreachedEvent(...))`
- **Error class:** `RiskLimitError` with `RISK_ERROR_CODES.DAILY_LOSS_LIMIT_BREACHED` (3003) — already defined
- **Test framework:** Vitest + `Test.createTestingModule()` from `@nestjs/testing`
- **Decimal math:** Use `FinancialDecimal` from `common/utils/financial-math.ts` for all monetary calculations
- **Cron jobs:** `@Cron` from `@nestjs/schedule` with UTC timezone

### Dependencies

| Package | Purpose | Installed In |
|---------|---------|-------------|
| `@nestjs/schedule` | `@Cron` decorator for midnight reset | Architecture spec (verify in package.json) |
| All other deps | Same as Story 4.1 | Already installed |

If `@nestjs/schedule` is not yet in `package.json`, run `pnpm add @nestjs/schedule`.

### Previous Story Intelligence (4.1)

- **397 tests passing** — regression gate baseline
- `RiskManagerService` demonstrates `OnModuleInit` + config validation + `PrismaService` upsert pattern
- `initializeStateFromDb()` loads from DB but currently ignores `dailyPnl` and `lastResetTimestamp` — extend it
- `persistState()` upserts but currently writes only `openPositionCount` and `totalCapitalDeployed` — extend it
- `RISK_ERROR_CODES.DAILY_LOSS_LIMIT_BREACHED = 3003` already defined
- `LimitBreachedEvent` already defined and exported, never emitted — this story wires it up
- `EVENT_NAMES.LIMIT_BREACHED = 'risk.limit.breached'` already in event catalog
- `risk_states` table already has `daily_pnl` and `last_reset_timestamp` columns from Story 4.1 migration
- `IRiskManager` uses `unknown` param type to avoid importing from `modules/` into `common/interfaces/`
- Dev notes from 4.1: `ConfigService.get` returns strings — use `Number()` conversion
- Dev notes from 4.1: `PrismaService` import path is `../../common/prisma.service` (not `../../persistence/`)

### Code Review Fixes (Post-Implementation)

- **M1 fix**: `handleMidnightReset` now sets `lastResetTimestamp` to UTC midnight (was `new Date()` which could be 00:00:02, causing stale-day detection failure on next startup)
- **M2 fix**: `validatePosition` halt check moved before `maxPositionSizeUsd` computation (avoids wasted allocation when halted)
- **L1 fix**: Added boundary test for `RISK_DAILY_LOSS_PCT=1.0` (valid boundary)
- **L2 fix**: Added comment explaining eslint-disable pragmas in spec file
- **M3 fix**: Corrected test count in Dev Agent Record (423 tests, not 405)

### Git Intelligence

Recent engine commits follow pattern: `feat: <description>`. Story 4.2 should use:
- `feat: add daily loss limit tracking and automatic trading halt`

Last commit: `feat: implement risk management module with configuration validation, state tracking, and position validation logic` (Story 4.1)

### Testing Strategy

- Extend existing `risk-manager.service.spec.ts` with new `describe` blocks for daily loss
- Mock `PrismaService` with mock `riskState` methods (`findFirst`, `upsert`) — same pattern as Story 4.1
- Mock `ConfigService.get()` to return `RISK_DAILY_LOSS_PCT` in addition to existing risk config
- Mock `EventEmitter2.emit()` to verify both `LimitBreachedEvent` and `LimitApproachedEvent` emission
- Test `handleMidnightReset()` by calling it directly (don't test the cron scheduling itself)
- Use `vi.useFakeTimers()` for stale-day detection tests AND midnight reset tests to control `Date.now()` and validate "previous day P&L" logging
- Test `persistState` failure by making the mock `prisma.riskState.upsert` reject — verify in-memory state is NOT rolled back
- Do NOT use a real database — unit tests only with mocked Prisma

### Project Structure Notes

Modified files:
```
prisma/schema.prisma                                    (add tradingHalted, haltReason columns)
prisma/migrations/<timestamp>_add_trading_halt_columns/migration.sql  (auto-generated)
src/common/types/risk.type.ts                           (add dailyLossPct, dailyPnl, dailyLossLimitUsd fields)
src/common/interfaces/risk-manager.interface.ts         (add updateDailyPnl, isTradingHalted)
src/modules/risk-management/risk-manager.service.ts     (daily loss logic, midnight reset, state init)
src/modules/risk-management/risk-manager.service.spec.ts (15+ new test cases)
src/core/core.module.ts                                 (add ScheduleModule.forRoot() if not already present)
.env.example                                            (add RISK_DAILY_LOSS_PCT)
.env.development                                        (add RISK_DAILY_LOSS_PCT)
test/app.e2e-spec.ts                                    (add RISK_DAILY_LOSS_PCT env var)
test/core-lifecycle.e2e-spec.ts                         (add RISK_DAILY_LOSS_PCT env var)
test/logging.e2e-spec.ts                                (add RISK_DAILY_LOSS_PCT env var)
```

No new files created — all changes extend existing Story 4.1 files.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2 — acceptance criteria, BDD scenarios]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3 — daily loss halt cannot be overridden (downstream constraint)]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4 — risk budget reservation interacts with daily capital (downstream)]
- [Source: _bmad-output/planning-artifacts/prd.md#FR-RM-03 — halt trading at 5% daily loss limit]
- [Source: _bmad-output/planning-artifacts/prd.md#Error Catalog — code 3001 Daily Loss Limit Exceeded, Critical, Halt all trading]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Taxonomy — RiskLimitError 3000-3999]
- [Source: _bmad-output/planning-artifacts/architecture.md#scheduler.service.ts — @nestjs/schedule for cron jobs]
- [Source: _bmad-output/planning-artifacts/architecture.md#Technology Stack — @nestjs/schedule confirmed]
- [Source: pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts — existing service to extend]
- [Source: pm-arbitrage-engine/src/common/errors/risk-limit-error.ts — DAILY_LOSS_LIMIT_BREACHED: 3003]
- [Source: pm-arbitrage-engine/src/common/events/risk.events.ts — LimitBreachedEvent already defined]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts — LIMIT_BREACHED event name]
- [Source: pm-arbitrage-engine/src/common/types/risk.type.ts — RiskConfig, RiskExposure, RiskDecision to extend]
- [Source: pm-arbitrage-engine/src/common/interfaces/risk-manager.interface.ts — IRiskManager to extend]
- [Source: pm-arbitrage-engine/prisma/schema.prisma — RiskState model with dailyPnl, lastResetTimestamp already present]
- [Source: _bmad-output/implementation-artifacts/4-1-position-sizing-portfolio-limits.md — previous story patterns, dev notes, file list]
- [Source: CLAUDE.md#Module Dependency Rules — risk-management allowed imports]
- [Source: CLAUDE.md#Error Handling — SystemError hierarchy]
- [Source: CLAUDE.md#Domain Rules — 5% daily loss limit]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None.

### Completion Notes List

- Task 1: Added `trading_halted` (Boolean, default false) and `halt_reason` (String?, nullable) columns to `RiskState` model in Prisma schema. Created manual migration SQL since DB was offline. Ran `prisma generate` successfully.
- Task 2: Extended `RiskConfig` with `dailyLossPct`, `RiskExposure` with `dailyPnl` + `dailyLossLimitUsd`, `RiskDecision` with optional `dailyPnl`.
- Task 3: Added `updateDailyPnl(pnlDelta: unknown): Promise<void>` and `isTradingHalted(): boolean` to `IRiskManager` interface. Parameter type is `unknown` per architecture constraint (no Decimal import in common/interfaces).
- Task 4: Added `RISK_DAILY_LOSS_PCT=0.05` to `.env.example`, `.env.development`, and all 3 e2e test files.
- Task 5: Implemented full daily loss logic in `RiskManagerService`: in-memory state tracking (`dailyPnl`, `tradingHalted`, `haltReason`, `dailyLossApproachEmitted`), config validation for `dailyLossPct`, stale-day detection on startup, corrupted state handling, halt check as first gate in `validatePosition()`, `updateDailyPnl()` with 80% approach warning and 100% breach halt, `isTradingHalted()`, extended `getCurrentExposure()` and `persistState()`. Added try/catch to `persistState()` per AC6 (no in-memory rollback on DB failure).
- Task 6: Added `@Cron('0 0 0 * * *', { timeZone: 'UTC' })` midnight reset method. `ScheduleModule.forRoot()` already registered in `AppModule` — removed duplicate from `CoreModule`.
- Task 7: 24 new test cases (39 total, up from 15). All pass. Covers: config validation (3 new), halt rejection + short-circuit (2), updateDailyPnl accumulation/breach/approach/debounce (7), isTradingHalted (2), midnight reset (3), startup stale-day/halt-restore/corrupted-state (3), getCurrentExposure fields (1), persistState writes + failure resilience (2).
- Task 8: `pnpm lint` passes clean. No import boundary violations. 423 tests passing (31 test files, 0 failures).

### File List

- `prisma/schema.prisma` — Added `tradingHalted`, `haltReason` to `RiskState` model
- `prisma/migrations/20260217100000_add_trading_halt_columns/migration.sql` — New migration
- `src/common/types/risk.type.ts` — Added `dailyLossPct` to `RiskConfig`, `dailyPnl`/`dailyLossLimitUsd` to `RiskExposure`, optional `dailyPnl` to `RiskDecision`
- `src/common/interfaces/risk-manager.interface.ts` — Added `updateDailyPnl()`, `isTradingHalted()`
- `src/modules/risk-management/risk-manager.service.ts` — Daily loss logic, midnight reset, state init, halt check
- `src/modules/risk-management/risk-manager.service.spec.ts` — 24 new test cases (39 total)
- `src/core/core.module.ts` — Removed duplicate `ScheduleModule.forRoot()` (already in `AppModule`)
- `.env.example` — Added `RISK_DAILY_LOSS_PCT=0.05`
- `.env.development` — Added `RISK_DAILY_LOSS_PCT=0.05`
- `test/app.e2e-spec.ts` — Added `RISK_DAILY_LOSS_PCT` env var
- `test/core-lifecycle.e2e-spec.ts` — Added `RISK_DAILY_LOSS_PCT` env var
- `test/logging.e2e-spec.ts` — Added `RISK_DAILY_LOSS_PCT` env var
