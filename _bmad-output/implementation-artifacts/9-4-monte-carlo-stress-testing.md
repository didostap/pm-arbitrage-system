# Story 9.4: Monte Carlo Stress Testing

Status: done

## Story

As an operator,
I want the system to run stress tests against historical and synthetic scenarios,
So that I can validate my risk parameters aren't calibrated too loosely.

## Acceptance Criteria

1. **Given** the current portfolio state and risk parameters, **When** Monte Carlo simulation runs (triggered manually via `POST /api/risk/stress-test` or on weekly schedule), **Then** it simulates 1000+ scenarios using historical price movements and synthetic adverse scenarios, **And** results include: probability of drawdown >15%, >20%, >25%; expected worst-case loss; portfolio VaR at 95% and 99% confidence. [Source: epics.md#Story-9.4, prd.md#FR-RM-09]

2. **Given** stress test results indicate risk parameters are too loose, **When** probability of >20% drawdown exceeds 5%, **Then** an alert is emitted recommending parameter tightening with specific suggestions. [Source: epics.md#Story-9.4]

## Tasks / Subtasks

- [x] **Task 1: Add `simple-statistics` dependency** (AC: #1)
  - [x] `pnpm add simple-statistics` in `pm-arbitrage-engine/`
  - [x] Verify TypeScript types resolve (package has built-in declarations)

- [x] **Task 2: Create `StressTestRun` Prisma model + migration** (AC: #1)
  - [x] Add model to `prisma/schema.prisma` with top-level metric columns + JSON detail fields
  - [x] Run `pnpm prisma migrate dev --name add-stress-test-run`
  - [x] Run `pnpm prisma generate`

- [x] **Task 3: Add stress test types and events** (AC: #1, #2)
  - [x] Add `StressTestResult` interface to `common/types/risk.type.ts`
  - [x] Add `STRESS_TEST_COMPLETED` and `STRESS_TEST_ALERT` to `common/events/event-catalog.ts`
  - [x] Add `StressTestCompletedEvent` and `StressTestAlertEvent` classes to `common/events/risk.events.ts`

- [x] **Task 4: Implement `StressTestService`** (AC: #1, #2)
  - [x] Create `modules/risk-management/stress-test.service.ts`
  - [x] Implement historical volatility estimation from `OrderBookSnapshot` midpoints
  - [x] Implement bounded price shock Monte Carlo simulation (1000+ scenarios)
  - [x] Implement synthetic adverse scenarios (cluster-correlated shocks, correlation-1 stress)
  - [x] Calculate drawdown probabilities (>15%, >20%, >25%), VaR (95%, 99%), worst-case loss
  - [x] Persist results to `StressTestRun`
  - [x] Emit `STRESS_TEST_COMPLETED` event on every run
  - [x] Emit `STRESS_TEST_ALERT` event when >20% drawdown probability exceeds 5%
  - [x] Add `@Cron('0 0 0 * * 0', { timeZone: 'UTC' })` weekly schedule (Sunday midnight)

- [x] **Task 5: Implement `StressTestController`** (AC: #1)
  - [x] Create `modules/risk-management/stress-test.controller.ts`
  - [x] `POST /api/risk/stress-test` — trigger manual run (auth-guarded)
  - [x] `GET /api/risk/stress-test/latest` — retrieve most recent result (auth-guarded)
  - [x] Create DTOs: `StressTestResponseDto`, `StressTestTriggerResponseDto`
  - [x] Swagger decorators, standard response wrappers

- [x] **Task 6: Register in `RiskManagementModule`** (AC: #1)
  - [x] Add `StressTestService` to providers
  - [x] Add `StressTestController` to controllers

- [x] **Task 7: Add environment configuration** (AC: #1)
  - [x] Add `STRESS_TEST_SCENARIOS` (default: `1000`), `STRESS_TEST_DEFAULT_DAILY_VOL` (default: `0.03`), `STRESS_TEST_MIN_SNAPSHOTS` (default: `30`) to env schema
  - [x] Update `.env.example` and `.env.development`

- [x] **Task 8: Tests** (AC: #1, #2)
  - [x] `stress-test.service.spec.ts` — Monte Carlo simulation logic:
    - Runs configured number of scenarios (default 1000)
    - Calculates correct drawdown probabilities from simulated P&L distribution
    - Calculates VaR at 95% and 99% confidence levels
    - Reports worst-case loss across all scenarios
    - Emits `STRESS_TEST_COMPLETED` event with results
    - Emits `STRESS_TEST_ALERT` when >20% drawdown probability > 5%
    - Does NOT emit alert when >20% drawdown probability <= 5%
    - Uses historical volatility when sufficient snapshots exist (>= `STRESS_TEST_MIN_SNAPSHOTS`)
    - Falls back to `STRESS_TEST_DEFAULT_DAILY_VOL` when insufficient history
    - Applies correlated shocks to positions in same cluster
    - Includes correlation-1 synthetic scenario (all clusters adverse simultaneously)
    - Synthetic adverse shocks are per-position directional (buy = price down, sell = price up)
    - Bounded price model: prices clamped to [0, 1] after shock
    - Position sizes parsed from `sizes` JSON as USD values
    - All financial math uses `decimal.js`
    - Persists `StressTestRun` to database
    - Weekly cron triggers with `withCorrelationId()`
    - Returns empty/neutral result when no open positions exist
  - [x] `stress-test.controller.spec.ts` — endpoint tests:
    - `POST /api/risk/stress-test` triggers simulation, returns results
    - `GET /api/risk/stress-test/latest` returns most recent `StressTestRun`
    - `GET /api/risk/stress-test/latest` returns 404 when no runs exist
    - Auth guard applied to all endpoints
    - Standard response wrapper format

## Dev Notes

### Architecture Context

This story implements FR-RM-09, the final story in Epic 9 (Advanced Risk & Portfolio Management). It adds Monte Carlo stress testing as a standalone analytical service within the risk management module. Unlike the hot-path risk checks (Stories 9.1-9.3 which run on every opportunity), stress testing is an offline analysis tool — it does NOT gate execution. It runs on-demand or weekly to validate that current risk parameters produce acceptable tail-risk profiles. [Source: epics.md#Epic-9, prd.md#FR-RM-09]

### Monte Carlo Simulation Design

**Why bounded price shocks (not GBM):** Prediction market prices are bounded [0, 1] — they represent probabilities. Geometric Brownian Motion assumes unbounded log-normal distributions and is inappropriate. Instead, apply additive normal shocks clamped to [0, 1]. [Source: product-brief#Risk-Management]

**Simulation methodology:**

```
For each scenario s in [1..numScenarios]:
  1. For each open position p:
     a. Estimate volatility for each leg (historical or default)
     b. Generate correlated random price shocks:
        - Positions in same cluster share a common factor shock
        - shock_leg = cluster_factor * ρ + idiosyncratic * √(1-ρ²)
     c. Apply shock to current price: new_price = clamp(current_price + shock, 0, 1)
     d. Calculate position P&L (sizes are USD — from risk module's position sizing):
        - For buy side: (new_price - entry_price) * size_usd
        - For sell side: (entry_price - new_price) * size_usd
        - Where size_usd = position.sizes[platform] (stored as USD string in JSON)
     e. Net position P&L = polymarket_leg_pnl + kalshi_leg_pnl
  2. Portfolio P&L for scenario s = sum of all position P&Ls
  3. Drawdown for scenario s = -portfolio_pnl / bankroll (if negative)

After all scenarios:
  - Sort portfolio P&Ls ascending
  - VaR(95%) = -quantile(portfolio_pnls, 0.05)  // loss at 5th percentile
  - VaR(99%) = -quantile(portfolio_pnls, 0.01)  // loss at 1st percentile
  - Worst-case loss = -min(portfolio_pnls)
  - P(drawdown > X%) = count(drawdown > X%) / numScenarios

VaR sign convention: portfolio_pnls contains positive (gain) and negative (loss) values.
quantile(pnls, 0.05) returns the 5th percentile — typically negative for risky portfolios.
Negating gives positive VaR in USD. Example: pnls = [-500, -200, 0, 100, 300] →
quantile(0.05) ≈ -500 → VaR(95%) = 500 (you could lose up to $500 with 95% confidence).
```

**Synthetic adverse scenarios (appended to random scenarios):** [Source: product-brief#Risk-Management — "platform outage during high volatility, simultaneous adverse movement of correlated positions"]

1. **Correlation-1 stress:** All positions move adversely simultaneously — each position is shocked in its **worst-case direction** (buys get -3σ price drop, sells get +3σ price rise). This catches the "everything goes wrong at once" tail. **Critical:** "adverse" is per-position, not a uniform direction — a buy loses on price down, a sell loses on price up.
2. **Single-cluster blowup:** Each cluster in turn gets adverse 3σ shocks (per-position worst-case direction) while others get random shocks.
3. **Liquidity gap:** All positions suffer a 2x volatility shock in their adverse direction (simulates sudden spread widening).

These synthetic scenarios are always included regardless of `STRESS_TEST_SCENARIOS` count (they supplement the random scenarios).

### Historical Volatility Estimation

```typescript
// For each contract, query OrderBookSnapshot midpoints over trailing 7 days
// midpoint = (best_bid + best_ask) / 2
// Calculate daily returns: r_t = midpoint_t - midpoint_{t-1}  (additive, not log — bounded domain)
// daily_vol = standardDeviation(returns)
// If snapshots < STRESS_TEST_MIN_SNAPSHOTS → use STRESS_TEST_DEFAULT_DAILY_VOL
```

**All volatilities are daily.** No annualization — the simulation produces a single-day stress snapshot of the portfolio. The `STRESS_TEST_DEFAULT_DAILY_VOL` default of 0.03 represents typical daily volatility for prediction market prices (~3% daily standard deviation of midpoint changes). Prediction markets trade 24/7 — no weekend gap handling needed.

Query: `OrderBookSnapshot` filtered by `platform + contract_id`, ordered by `created_at DESC`, limited to trailing 7 days. Parse `bids`/`asks` JSON to extract best bid/ask for midpoint. [Source: prisma/schema.prisma lines 36-48]

### Correlation Between Positions

Positions sharing a `CorrelationCluster` (via `ContractMatch.clusterId`) get correlated shocks. Correlation coefficient ρ = 0.7 (configurable as constant, not env var — rarely needs tuning). Positions in different clusters or with no cluster get independent shocks.

**Implementation:** Generate one standard normal sample per cluster (the "common factor"). Each position's shock = `clusterFactor * ρ + independentNormal * √(1 - ρ²)`, scaled by the position's estimated volatility.

### `StressTestRun` Prisma Model

```prisma
model StressTestRun {
  id                        String   @id @default(cuid())
  timestamp                 DateTime @db.Timestamptz
  numScenarios              Int      @map("num_scenarios")
  numPositions              Int      @map("num_positions")
  bankrollUsd               Decimal  @map("bankroll_usd") @db.Decimal(20, 8)
  var95                     Decimal  @db.Decimal(20, 8)
  var99                     Decimal  @db.Decimal(20, 8)
  worstCaseLoss             Decimal  @map("worst_case_loss") @db.Decimal(20, 8)
  drawdown15PctProbability  Decimal  @map("drawdown_15pct_probability") @db.Decimal(10, 6)
  drawdown20PctProbability  Decimal  @map("drawdown_20pct_probability") @db.Decimal(10, 6)
  drawdown25PctProbability  Decimal  @map("drawdown_25pct_probability") @db.Decimal(10, 6)
  alertEmitted              Boolean  @default(false) @map("alert_emitted")
  suggestions               Json?    // string[] — parameter tightening suggestions when alert fires
  scenarioDetails           Json     @map("scenario_details") // { percentiles, syntheticResults, volatilities }
  triggeredBy               String   @map("triggered_by") // "cron" | "operator"
  createdAt                 DateTime @default(now()) @map("created_at") @db.Timestamptz

  @@index([timestamp])
  @@map("stress_test_runs")
}
```

Key metrics (var95, var99, drawdown probabilities) are top-level columns for queryable trend analysis. `scenarioDetails` JSON stores **summary statistics only** — P&L distribution percentiles, named synthetic scenario results, and per-contract volatilities used. It does NOT store all 1000 individual scenario P&Ls (that would bloat the JSON). Follows the `CalibrationRun` pattern. [Source: prisma/schema.prisma lines 266-281, CalibrationRun model]

### `StressTestResult` Interface

```typescript
export interface StressTestResult {
  numScenarios: number;
  numPositions: number;
  bankrollUsd: Decimal;
  var95: Decimal;           // Value at Risk at 95% confidence
  var99: Decimal;           // Value at Risk at 99% confidence
  worstCaseLoss: Decimal;   // Maximum loss across all scenarios
  drawdown15PctProbability: Decimal;  // P(drawdown > 15%)
  drawdown20PctProbability: Decimal;  // P(drawdown > 20%)
  drawdown25PctProbability: Decimal;  // P(drawdown > 25%)
  alertEmitted: boolean;
  suggestions: string[];    // Parameter tightening recommendations
  scenarioDetails: {
    percentiles: Record<string, string>;  // p5, p10, p25, p50, p75, p90, p95, p99
    syntheticResults: { name: string; portfolioPnl: string }[];
    volatilities: { contractId: string; platform: string; vol: string; source: string }[];
  };
}
```

### Alert Logic (AC #2)

```typescript
if (drawdown20PctProbability.greaterThan(new Decimal('0.05'))) {
  const suggestions = this.generateSuggestions(exposure, clusterExposures, positions);
  this.eventEmitter.emit(EVENT_NAMES.STRESS_TEST_ALERT, new StressTestAlertEvent({
    var95, var99, worstCaseLoss, drawdown20PctProbability, suggestions
  }));
}
```

**Suggestion generation heuristics** (rule-based, deterministic):

1. **High cluster concentration:** If any cluster exposure > 10% (soft limit), suggest: `"Cluster '{name}' at {pct}% exposure — reduce correlated positions to lower tail risk"`
2. **Large position sizes:** If `maxPositionPct > 0.02` and VaR99 > 10% of bankroll, suggest: `"Reduce RISK_MAX_POSITION_PCT from {current}% to 2% — large positions drive tail losses"`
3. **Many open pairs:** If `openPairCount > maxOpenPairs * 0.8`, suggest: `"At {count}/{max} open pairs — consider reducing RISK_MAX_OPEN_PAIRS to limit portfolio complexity"`
4. **High total deployment:** If `totalCapitalDeployed / bankroll > 0.5`, suggest: `"Capital deployment at {pct}% of bankroll — reduce overall exposure"`

Each rule independently checks its condition and appends to the `suggestions[]` array. At least one suggestion will always be generated when the alert fires — if no specific rule triggers, emit a generic: `"Current risk parameters produce >5% probability of 20%+ drawdown — review position sizing and concentration limits"`. [Source: epics.md#Story-9.4 AC#2]

### Event Definitions

Add to `event-catalog.ts`:
```typescript
// [Story 9.4] Stress Testing Events
STRESS_TEST_COMPLETED: 'risk.stress_test.completed',
STRESS_TEST_ALERT: 'risk.stress_test.alert',
```

Event classes extend `BaseEvent` with relevant payload. Follow existing patterns in `risk.events.ts`. [Source: common/events/event-catalog.ts, common/events/base.event.ts]

### Controller Design

```
POST /api/risk/stress-test       → Trigger manual run, return StressTestResult
GET  /api/risk/stress-test/latest → Return most recent StressTestRun (404 if none)
```

Both endpoints require `AuthTokenGuard`. Use standard response wrappers: `{ data: T, timestamp: string }`. Follow `RiskOverrideController` patterns for error handling and Swagger decorators. [Source: risk-override.controller.ts, CLAUDE.md#API-Response-Format]

### Environment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `STRESS_TEST_SCENARIOS` | `1000` | Number of random Monte Carlo scenarios per run |
| `STRESS_TEST_DEFAULT_DAILY_VOL` | `0.03` | Default daily volatility when insufficient history (typical prediction market daily vol ~2-5%) |
| `STRESS_TEST_MIN_SNAPSHOTS` | `30` | Minimum `OrderBookSnapshot` count for historical vol |

Add Zod validation in existing env schema (Story 9-0-2 pattern). All are optional with defaults. [Source: env schema validation pattern from Story 9-0-2]

### `simple-statistics` Usage

Functions needed from `simple-statistics` (v7.8.9, zero deps, built-in TS types):
- `quantile(data, p)` — for VaR calculation (percentile of P&L distribution)
- `standardDeviation(data)` — for historical volatility from midpoint returns
- `probit(p)` — inverse normal CDF for generating normal random samples: `probit(Math.random())` produces standard normal variates
- `mean(data)` — for expected portfolio P&L

**Critical:** `simple-statistics` operates on `number[]`, not `Decimal`. Convert `Decimal` → `number` for statistical calculations only (percentile computation). All intermediate financial P&L math remains `decimal.js`. The precision loss from `Decimal.toNumber()` for percentile ranking is acceptable — we're computing probabilities, not exact monetary amounts. [Source: CLAUDE.md#Domain-Rules — financial math uses decimal.js]

### Key Implementation Details

**No hot-path impact.** `StressTestService` is a standalone service. It reads position data and risk state but never writes to `RiskState` or gates execution. It lives in `risk-management/` module but is architecturally separate from the `validatePosition()` pipeline.

**Cron pattern:** `@Cron('0 0 0 * * 0', { timeZone: 'UTC' })` — Sunday midnight UTC. Wrapped in `withCorrelationId()` for structured logging. [Source: existing cron patterns in scheduler.service.ts, audit-log-retention.service.ts]

**Empty portfolio handling:** When no open positions exist, return a neutral result (all drawdown probabilities = 0, VaR = 0, worstCaseLoss = 0, numPositions = 0). Still persist the `StressTestRun` — operators want to see that the cron ran even when no positions were open.

**Zero bankroll guard:** `RiskManagerService.validateConfig()` enforces `bankroll > 0` at startup, so division by zero in drawdown calculation cannot occur in practice. Nonetheless, add a defensive guard: if `bankrollUsd <= 0`, skip simulation and return neutral result with a warning log.

**Performance:** 1000 scenarios × N positions. For typical portfolios (≤25 positions), this completes in milliseconds. The DB query for historical volatility is the bottleneck — batch by platform, limit to 7-day window. Consider running in a `setTimeout` (non-blocking) for the cron path to avoid blocking the event loop during large simulations.

**Module dependency:** `StressTestService` injects `PrismaService` (position + order book data), `ConfigService` (risk params + stress test config), `EventEmitter2` (events), and `IRiskManager` via `RISK_MANAGER_TOKEN` (for `getCurrentExposure()`). No new cross-module dependencies. [Source: CLAUDE.md#Module-Dependency-Rules]

### Existing Infrastructure to Reuse

| Component | Location | What to Reuse |
|-----------|----------|---------------|
| `PositionRepository.findActivePositions()` | `persistence/repositories/position.repository.ts` | Open position data with pair + orders |
| `getCurrentExposure()` | `risk-manager.service.ts` | Bankroll, capital deployed, cluster exposures |
| `CorrelationTrackerService.getClusterExposures()` | `correlation-tracker.service.ts` | Cluster membership for correlated shocks |
| `OrderBookSnapshot` model | `prisma/schema.prisma` | Historical price data for volatility |
| `CalibrationRun` model pattern | `prisma/schema.prisma` | DB model structure for periodic results |
| `@Cron` + `withCorrelationId()` | `audit-log-retention.service.ts` | Cron scheduling pattern |
| `AuthTokenGuard` | `common/guards/auth-token.guard.ts` | Endpoint authentication |
| `BaseEvent` | `common/events/base.event.ts` | Event class base |
| `FinancialDecimal` | `common/utils/financial-math.ts` | All monetary arithmetic |
| `RiskOverrideController` | `risk-override.controller.ts` | Controller + Swagger pattern |
| Env schema validation | `common/config/env-schema.ts` (Story 9-0-2) | Zod config validation |

### Testing Strategy

Co-located specs using Vitest 4 + `unplugin-swc`. Mock `PrismaService`, `ConfigService`, `EventEmitter2`, and `RISK_MANAGER_TOKEN`.

**Baseline:** 1963 tests, 112 files, all green.

**Key test design notes:**
- Mock `Math.random()` with deterministic seeds for reproducible scenarios in tests
- Use small scenario counts (10-50) in tests for speed, verify logic correctness
- Verify statistical calculations against hand-computed expected values
- Test the cron handler triggers simulation and wraps in `withCorrelationId()`
- For alert tests: construct portfolios where drawdown probability deterministically exceeds/falls below 5% threshold

### Previous Story Intelligence (Story 9.3)

- **`extractPairContext()` pattern** provides cluster info from opportunity data — but stress testing reads directly from DB positions, not opportunities. Use `ContractMatch.clusterId` from the position's pair relation.
- **`FinancialDecimal` wrapper** used consistently — continue pattern for all P&L calculations.
- **Config pattern:** Read from `ConfigService` as strings, validate with Zod, convert to numbers. [Source: Story 9.3 dev notes, Story 9-0-2]
- **Test count progression:** 1963 → expect ~1990+ after this story.

### Project Structure Notes

All files align with established module structure. New files created:

- `src/modules/risk-management/stress-test.service.ts` — simulation logic
- `src/modules/risk-management/stress-test.service.spec.ts` — co-located tests
- `src/modules/risk-management/stress-test.controller.ts` — REST endpoints
- `src/modules/risk-management/stress-test.controller.spec.ts` — co-located tests
- `src/modules/risk-management/dto/stress-test.dto.ts` — request/response DTOs

Modified files:

- `prisma/schema.prisma` — add `StressTestRun` model
- `src/common/events/event-catalog.ts` — add 2 events
- `src/common/events/risk.events.ts` — add 2 event classes
- `src/common/types/risk.type.ts` — add `StressTestResult` interface
- `src/modules/risk-management/risk-management.module.ts` — register service + controller
- `.env.example`, `.env.development` — add 3 config vars
- Env schema file — add Zod validation for new vars

[Source: CLAUDE.md#Architecture, CLAUDE.md#Naming-Conventions]

### References

- [Source: epics.md#Story-9.4] — Acceptance criteria and business rules
- [Source: prd.md#FR-RM-09] — "System shall run Monte Carlo stress testing against historical and synthetic scenarios to validate portfolio risk parameters"
- [Source: product-brief#Risk-Management] — "Monte Carlo stress testing against historical and synthetic scenarios (platform outage during high volatility, simultaneous adverse movement of correlated positions)"
- [Source: CLAUDE.md#Domain-Rules] — All financial math uses decimal.js
- [Source: CLAUDE.md#Module-Dependency-Rules] — Allowed imports
- [Source: CLAUDE.md#API-Response-Format] — Standard response wrappers
- [Source: prisma/schema.prisma lines 36-48] — OrderBookSnapshot model (historical price data)
- [Source: prisma/schema.prisma lines 200-232] — OpenPosition model (position data)
- [Source: prisma/schema.prisma lines 266-281] — CalibrationRun model (persistence pattern)
- [Source: codebase risk-manager.service.ts#getCurrentExposure] — Portfolio state accessor
- [Source: codebase position.repository.ts#findActivePositions] — Active position query
- [Source: codebase correlation-tracker.service.ts#getClusterExposures] — Cluster exposure data
- [Source: codebase risk-override.controller.ts] — Controller + Swagger pattern
- [Source: codebase audit-log-retention.service.ts] — Cron + withCorrelationId pattern
- [Source: codebase common/events/event-catalog.ts] — Event naming conventions
- [Source: Story 9.3 dev notes] — FinancialDecimal, extractPairContext, config patterns
- [Source: Story 9-0-2] — Zod env schema validation pattern
- [Source: npm simple-statistics@7.8.9] — Statistical functions (quantile, probit, standardDeviation)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None.

### Completion Notes List

- **Test baseline:** 1963 tests (112 files) → 1992 tests (114 files), +29 tests, all green
- **Lint:** Clean, no warnings or errors in new files
- **E2E:** All passing (DI fix required — `PrismaService` injected by class reference, not string token)
- **Migration:** `20260313125158_add_stress_test_run` applied successfully
- **Dependency:** `simple-statistics@7.8.9` (zero deps, built-in TS types)
- **Code review (Lad MCP):** Primary reviewer (kimi-k2.5) returned 4 critical, 4 high, 4 medium findings. All findings evaluated and disagreed — each either contradicts explicit story Dev Notes (e.g., additive returns, number for probabilities), follows established codebase patterns (cron error handling, @HttpCode(200)), or is out of scope. No code changes made from review.
- **Code review #2 (BMAD Dev Agent):** fixed 4 MEDIUM issues: (1) non-deterministic alert tests — mocked `Math.random` for reproducible results, lowered bankroll for guaranteed >20% drawdown, removed conditional assertions; (2) DTOs imported as `type` in controller — changed to value import + added `type` to `@ApiResponse` decorators for Swagger; (3) shared `configDefaults` mutation — replaced with per-test `mockConfigService.get.mockImplementation()`; (4) weak `withCorrelationId` test — now verifies event `correlationId` is a non-empty string. 3 LOW issues noted (redundant DTO wrappers, module-level `normalRandom`, error code 4008 range).
- **Key design decision:** `StressTestController` injects `PrismaService` directly (global module) rather than through string token — consistent with other controllers in the codebase
- **Synthetic scenarios:** 3 types always appended: correlation-1-stress (all adverse), cluster-blowup-{id} (per-cluster), liquidity-gap (2x vol). These supplement the configurable random scenario count.
- **Volatility cache:** Per-contract cache avoids duplicate DB queries when multiple positions share a contract

### File List

**New files:**
- `src/modules/risk-management/stress-test.service.ts` — Monte Carlo simulation, cron, volatility estimation, alert logic
- `src/modules/risk-management/stress-test.service.spec.ts` — 24 tests
- `src/modules/risk-management/stress-test.controller.ts` — POST trigger + GET latest endpoints
- `src/modules/risk-management/stress-test.controller.spec.ts` — 5 tests
- `src/modules/risk-management/dto/stress-test.dto.ts` — Response DTOs with Swagger decorators
- `prisma/migrations/20260313125158_add_stress_test_run/migration.sql` — StressTestRun table

**Modified files:**
- `prisma/schema.prisma` — Added `StressTestRun` model (17 columns, timestamp index)
- `src/common/events/event-catalog.ts` — Added `STRESS_TEST_COMPLETED`, `STRESS_TEST_ALERT`
- `src/common/events/risk.events.ts` — Added `StressTestCompletedEvent`, `StressTestAlertEvent` classes
- `src/common/types/risk.type.ts` — Added `StressTestResult` interface
- `src/modules/risk-management/risk-management.module.ts` — Registered `StressTestService` + `StressTestController`
- `src/common/config/env.schema.ts` — Added 3 Zod-validated env vars
- `.env.example` — Added stress test config section
- `.env.development` — Added stress test config section
- `package.json` / `pnpm-lock.yaml` — Added `simple-statistics@7.8.9`
