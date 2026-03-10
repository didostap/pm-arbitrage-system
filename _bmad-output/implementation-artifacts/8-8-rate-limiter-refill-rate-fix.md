# Story 8.8: Rate Limiter Refill Rate Fix

Status: done

<!-- Course Correction story — added 2026-03-11 after Epic 8 completion.
     Triggered by: Kalshi read rate limit utilization 99.8% with 29 active pairs.
     Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11-rate-limiter.md -->

## Story

As an operator,
I want the rate limiter to refill tokens at the actual platform-published rate (with safety buffer) instead of a hardcoded 1 token/sec,
So that API utilization operates at ~15-20% instead of 99.8%, providing comfortable headroom for scaling to more pairs without rate limit stalls or false utilization alerts.

## Acceptance Criteria

1. **Given** the `RateLimiter` class is constructed with explicit `readRefillRatePerSec` and `writeRefillRatePerSec` parameters
   **When** time elapses and `refill()` runs
   **Then** the read bucket refills at `readRefillRatePerSec` and the write bucket refills at `writeRefillRatePerSec` independently
   **And** the constructor has NO default values for refill rate parameters — callers must provide explicit values
   **And** `waitIfNeeded()` uses the bucket-specific refill rate to calculate wait duration
   [Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Edit-1; FR-PI-03 "enforce platform-specific rate limits"]

2. **Given** a known tier name (e.g., `'BASIC'`) is passed to `RateLimiter.fromTier()`
   **When** the limiter is created
   **Then** bucket sizes are `Math.ceil(tierLimit × BURST_MULTIPLIER)` where `BURST_MULTIPLIER = 1.5`
   **And** refill rates are `tierLimit × SAFETY_BUFFER` where `SAFETY_BUFFER = 0.8`
   **And** `fromTier()` delegates to `fromLimits()` internally (single code path for limit application)
   **And** an unknown tier name still throws `"Unknown rate limit tier: <name>"`
   [Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Edit-1; architecture.md#NFR-I2 "rate limit compliance with 20% safety buffer"]

3. **Given** raw `readLimit` and `writeLimit` numbers (e.g., from an API response)
   **When** `RateLimiter.fromLimits(readLimit, writeLimit, logger)` is called
   **Then** it creates a limiter with the same safety buffer and burst multiplier logic as `fromTier()`
   **And** `fromTier('BASIC')` and `fromLimits(20, 10)` produce equivalent limiters (same bucket sizes, same refill rates)
   [Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Edit-1]

4. **Given** the Kalshi connector starts up with `KALSHI_API_KEY_ID` configured
   **When** `onModuleInit()` runs
   **Then** `initializeRateLimiterFromApi()` calls `AccountApi.getAccountApiLimits()` before `connect()`
   **And** on success, the rate limiter is replaced with `RateLimiter.fromLimits(response.read_limit, response.write_limit)`
   **And** the response field for tier name is `usage_tier` (NOT `tier` — verified against `kalshi-typescript@3.8.0` SDK model `GetAccountApiLimitsResponse`)
   [Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Edit-2; kalshi-typescript@3.8.0 GetAccountApiLimitsResponse model]

5. **Given** the `GET /account/limits` call fails (network error, auth failure, timeout)
   **When** `initializeRateLimiterFromApi()` catches the error
   **Then** a structured warning log is emitted with the error context
   **And** the constructor's default rate limiter (`RateLimiter.fromTier(KALSHI_API_TIER || 'BASIC')`) is kept
   **And** the fallback hierarchy is: API response → `KALSHI_API_TIER` env var → `'BASIC'` default
   **And** when `KALSHI_API_KEY_ID` is not configured, `initializeRateLimiterFromApi()` is skipped entirely (no API call attempted)
   [Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Edit-2, Section 3 item 2]

6. **Given** the Polymarket connector is constructed
   **When** the rate limiter is initialized
   **Then** it uses `RateLimiter.fromLimits()` with Polymarket's known rate limits instead of hardcoded `new RateLimiter(20, 4, 1, ...)`
   **And** refill rates correctly reflect Polymarket's published limits × SAFETY_BUFFER (not hardcoded 1 token/sec)
   [Source: Investigation finding — polymarket.connector.ts:79 has same refillRatePerSec=1 bug; constructor signature change forces update; user-approved scope expansion 2026-03-11]

7. **Given** a rate limiter is configured via `fromTier()` or `fromLimits()`
   **When** initialization completes
   **Then** a structured info log is emitted: `"Rate limiter configured"` with data fields `readBurst`, `writeBurst`, `readSustained`, `writeSustained`
   **And** the Kalshi connector logs this at construction (default) and again at onModuleInit if API upgrade succeeds
   [Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Edit-1]

8. **Given** the fix is deployed with 29 active pairs at Kalshi BASIC tier (read: 20/s, write: 10/s)
   **When** a 30-second polling cycle runs
   **Then** Kalshi read utilization operates at ~15-20% (down from 99.8%)
   **And** the 70% utilization alert (FR-PI-04) fires only when genuinely approaching limits — not constantly
   **And** zero 429 rate limit errors are maintained (same as before, now with proper headroom)
   [Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Section-5 Success Criteria; prd.md FR-PI-04]

9. **Given** all code changes are complete
   **When** the test suite and linter run
   **Then** all existing tests pass (1744+ baseline), 7+ new tests are added across rate-limiter.spec.ts and kalshi.connector.spec.ts and polymarket.connector.spec.ts
   **And** `pnpm lint` reports zero errors
   **And** no new `decimal.js` violations are introduced
   [Source: Project DoD gates; CLAUDE.md post-edit workflow]

## Tasks / Subtasks

- [x] **Task 1: Fix `RateLimiter` class** (AC: #1, #2, #3, #7)
  - [x] 1.1 Add `BURST_MULTIPLIER = 1.5` constant after existing `ALERT_THRESHOLD` at `src/common/utils/rate-limiter.ts:16`
  - [x] 1.2 Replace single `refillRatePerSec` constructor param (line 31) with `readRefillRatePerSec: number` and `writeRefillRatePerSec: number` — NO default values
  - [x] 1.3 Update `refill()` method (lines 103-119) to use `readRefillRatePerSec` for read bucket and `writeRefillRatePerSec` for write bucket (currently both use single `refillRatePerSec`)
  - [x] 1.4 Update `waitIfNeeded()` method (lines 95-101) to accept a `refillRate: number` parameter; callers (`acquireRead`, `acquireWrite`) pass the appropriate rate
  - [x] 1.5 Add `static fromLimits(readLimit: number, writeLimit: number, logger?: Logger): RateLimiter` factory — applies `Math.ceil(limit × BURST_MULTIPLIER)` to bucket sizes and `limit × SAFETY_BUFFER` to refill rates. Use `Math.ceil` (not `Math.floor`) for buckets — `ceil` prevents problematic rounding for small limits (e.g., `floor(1.6 × 1.5) = 2` vs `ceil(1.6 × 1.5) = 3`)
  - [x] 1.6 Refactor `fromTier()` (lines 43-54) to delegate to `fromLimits()` — single code path for limit derivation
  - [x] 1.7 Add startup config log in `fromLimits()`: `this.logger.log({ message: 'Rate limiter configured', data: { readBurst, writeBurst, readSustained, writeSustained } })` — or emit from constructor if logger is provided
  - [x] 1.8 Update barrel export in `src/common/utils/index.ts:2` if any new exports are needed (currently exports `RateLimiter` and `RATE_LIMIT_TIERS` — both sufficient)

- [x] **Task 2: Fix `KalshiConnector`** (AC: #4, #5)
  - [x] 2.1 Remove `readonly` from `rateLimiter` property at `src/connectors/kalshi/kalshi.connector.ts:72` (`private readonly` → `private`)
  - [x] 2.2 Replace constructor line 127 `new RateLimiter(24, 10, 1, this.logger)` with `RateLimiter.fromTier(this.configService.get<string>('KALSHI_API_TIER', 'BASIC'), this.logger)`
  - [x] 2.3 Add `private readonly accountApi: AccountApi` property — instantiate directly in constructor using the same `Configuration` object (lines 102-106), same pattern as `MarketApi`/`OrdersApi`. No NestJS module provider registration needed — `AccountApi` is not DI-injected, it's constructed inline like the other SDK API classes
  - [x] 2.4 Add `import { AccountApi } from 'kalshi-typescript'` to imports
  - [x] 2.5 Add `private async initializeRateLimiterFromApi(): Promise<void>` method:
    - Call `this.accountApi.getAccountApiLimits()`
    - On success: extract `response.data.read_limit` and `response.data.write_limit` (SDK returns AxiosResponse)
    - **Validate response**: if `read_limit <= 0` or `write_limit <= 0` or `isNaN(read_limit)` or `isNaN(write_limit)`, log warning and keep `fromTier()` default (do not create a broken limiter from invalid/malformed API data — SDK types say `number` but defensive coding against NaN/undefined from malformed responses)
    - Replace `this.rateLimiter` with `RateLimiter.fromLimits(readLimit, writeLimit, this.logger)`
    - Log: `"Rate limiter upgraded from API"` with `usage_tier`, `read_limit`, `write_limit`
    - On failure: log warning with error context, keep existing `fromTier()` default
    - **Timing**: This runs before `connect()` in `onModuleInit()` — no in-flight `acquireRead/Write()` calls exist during the swap. The polling loop has not started yet, so there is no race condition
  - [x] 2.6 Update `onModuleInit()` (lines 129-158) — call `await this.initializeRateLimiterFromApi()` before `await this.connect()`, but only if `apiKeyId` is configured (inside the existing early-return guard)

- [x] **Task 3: Fix `PolymarketConnector`** (AC: #6)
  - [x] 3.1 Replace constructor line 79 `new RateLimiter(20, 4, 1, this.logger)` in `src/connectors/polymarket/polymarket.connector.ts` with `RateLimiter.fromLimits(2, 2, this.logger)`
  - [x] 3.2 Polymarket rate limits: 2/s read, 2/s write (derived from ~100 req/min Cloudflare-enforced public limit, rounded up from 1.67/s). These are accepted baseline values — no further verification needed
  - [x] 3.3 Update the inline code comment to reflect `fromLimits()` initialization, the source of the 2/s values, and add: `// Note: bucket size (3 tokens) is sized for post-batch-migration read patterns (~1-3 reads/cycle). If batch order book fetch (Story 6-5-2a) is reverted or read patterns increase (e.g., retry storms), revisit these limits. withRetry() exponential backoff provides additional mitigation.`
  - [x] 3.4 `PolymarketConnector.rateLimiter` stays `readonly` — no dynamic upgrade needed (unlike Kalshi, Polymarket has no `GET /account/limits` equivalent)

- [x] **Task 4: Update `rate-limiter.spec.ts`** (AC: #1, #2, #3, #7)
  - [x] 4.1 Update `beforeEach` constructor call (line 12): `new RateLimiter(16, 8, 1, logger)` → `new RateLimiter(16, 8, 16, 8, logger)` (4 refill params, explicit read/write)
  - [x] 4.2 Add test: `fromLimits()` factory creates limiter with correct bucket sizes and refill rates (verify via `getUtilization()` after known token consumption)
  - [x] 4.3 Add test: `fromTier('BASIC')` and `fromLimits(20, 10)` produce equivalent behavior (same utilization after same operations)
  - [x] 4.4 Add test: asymmetric refill rates — high read refill + low write refill; verify read bucket recovers faster than write bucket after partial drain
  - [x] 4.5 Add test: startup configuration log emitted — spy on logger and verify `"Rate limiter configured"` message with `readBurst`, `writeBurst`, `readSustained`, `writeSustained` fields

- [x] **Task 5: Update `kalshi.connector.spec.ts`** (AC: #4, #5)
  - [x] 5.1 Add `AccountApi` to the `kalshi-typescript` mock (alongside existing `MarketApi`, `OrdersApi`, etc.) with a `mockGetAccountApiLimits` spy
  - [x] 5.2 Add `KALSHI_API_TIER` to the existing config mock (alongside `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PATH`, etc.)
  - [x] 5.3 Add test: API limits success — `getAccountApiLimits` resolves with `{ data: { usage_tier: 'BASIC', read_limit: 20, write_limit: 10 } }`, verify rate limiter is reconfigured (check via `getUtilization()` or spy on `RateLimiter.fromLimits`)
  - [x] 5.4 Add test: API limits failure — `getAccountApiLimits` rejects, verify warning log emitted and `fromTier()` default preserved
  - [x] 5.5 Add test: skip when `KALSHI_API_KEY_ID` is empty — verify `getAccountApiLimits` is NOT called

- [x] **Task 6: Update `polymarket.connector.spec.ts`** (AC: #6)
  - [x] 6.1 Verify existing constructor test still passes with updated `fromLimits()` initialization
  - [x] 6.2 Add test (if not covered): Polymarket rate limiter initialized with correct refill rates — verify via utilization check or constructor spy

- [x] **Task 7: Add env vars** (AC: #5)
  - [x] 7.1 Add to `.env.example` after `KALSHI_API_BASE_URL` line: `KALSHI_API_TIER=BASIC` with comment `# API tier: BASIC|ADVANCED|PREMIER|PRIME (fallback if GET /account/limits unavailable)`
  - [x] 7.2 Add to `.env.development` after `KALSHI_API_BASE_URL` line: `KALSHI_API_TIER=BASIC`

- [x] **Task 8: Lint + full test suite** (AC: #9)
  - [x] 8.1 Run `cd pm-arbitrage-engine && pnpm lint` — fix any errors
  - [x] 8.2 Run `pnpm test` — verify all existing tests pass + new tests pass
  - [x] 8.3 Confirm test count: baseline 1744 passed + new tests ≥ 7 = 1751+ passed
  - [x] 8.4 Note: 1 pre-existing e2e failure in `test/logging.e2e-spec.ts` (unrelated — `AssertionError: expected undefined to be defined` at line 88, event timestamp check)

## Dev Notes

### Implementation Sequence — FOLLOW THIS ORDER

1. **Task 1** (RateLimiter class) — Foundation change. All other tasks depend on this.
2. **Task 4** (rate-limiter.spec.ts) — Verify the foundation immediately.
3. **Task 2** (KalshiConnector) — Primary motivating fix.
4. **Task 5** (kalshi.connector.spec.ts) — Verify Kalshi changes.
5. **Task 3** (PolymarketConnector) — Secondary fix forced by constructor change.
6. **Task 6** (polymarket.connector.spec.ts) — Verify Polymarket changes.
7. **Task 7** (env vars) — Config files.
8. **Task 8** (lint + full suite) — Final validation.

### Critical: SDK Response Field Name Correction

The sprint change proposal (Section 4, Dev Notes) assumed the API response field is `tier`. **The actual SDK model is `usage_tier`.**

Verified from `kalshi-typescript@3.8.0`:
```typescript
// node_modules/kalshi-typescript/dist/models/get-account-api-limits-response.d.ts
export interface GetAccountApiLimitsResponse {
    'usage_tier': string;   // ← NOT 'tier'
    'read_limit': number;
    'write_limit': number;
}
```

The SDK method is `AccountApi.getAccountApiLimits()`, returning `AxiosResponse<GetAccountApiLimitsResponse>`. Access the data via `response.data.usage_tier`, `response.data.read_limit`, `response.data.write_limit`.

[Source: pm-arbitrage-engine/node_modules/kalshi-typescript/dist/models/get-account-api-limits-response.d.ts; pm-arbitrage-engine/node_modules/kalshi-typescript/dist/api/account-api.d.ts]

### Critical: Constructor Must NOT Have Defaults

The entire point of this fix is that the old `refillRatePerSec = 1` default silently produced broken behavior. The new constructor signature must force callers to be explicit:

```typescript
// CORRECT — no defaults
constructor(
    private readonly maxReadTokens: number,
    private readonly maxWriteTokens: number,
    private readonly readRefillRatePerSec: number,
    private readonly writeRefillRatePerSec: number,
    logger?: Logger,
) { ... }
```

All callers should use `fromTier()` or `fromLimits()` factories rather than raw constructor. Direct constructor use is acceptable in tests only.

[Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Section-3 item 1; Section 4 Dev Notes]

### Polymarket Rate Limits — Accepted Baseline

The existing code comment states: `"~100 req/min public, 300 req/10s for /books"`. Polymarket enforces rate limits via Cloudflare throttling (no formal tier system like Kalshi).

**Accepted baseline values**: `fromLimits(2, 2, logger)`
- Read: 2/s (≈100 req/min = 1.67/s, rounded up conservatively)
- Write: 2/s (conservative — Polymarket does not publish a separate write limit)

**Resulting limiter configuration:**
- readBucket: `ceil(2 × 1.5)` = 3 tokens, readRefill: `2 × 0.8` = 1.6/s
- writeBucket: `ceil(2 × 1.5)` = 3 tokens, writeRefill: `2 × 0.8` = 1.6/s

**Why this is safe:** Post batch order book migration (Story 6-5-2a), Polymarket reads are ~1-3 per 30s cycle. The 3-token bucket fully refills (~1.9s to full) between cycles. Order submissions (writes) are rare — at most 1-2 per detected opportunity.

**Note on bucket size decrease:** The current code uses `new RateLimiter(20, 4, 1, ...)` (20-token read bucket). With `fromLimits(2, 2)`, the read bucket drops to 3 tokens. This is correct — the 20-token bucket was oversized for the pre-batch era (8 sequential reads/cycle). Post-batch, 3 tokens with 1.6/s refill provides adequate headroom.

**No dynamic API detection for Polymarket** — their API has no equivalent of Kalshi's `GET /account/limits`. Static initialization only. `PolymarketConnector.rateLimiter` stays `readonly`.

[Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts:77-79 code comment; Story 6-5-2a batch migration; docs.polymarket.com/api-reference/rate-limits (Cloudflare-enforced)]

### Bucket Size Formula Change — Intentional

The current `fromTier()` uses `Math.floor(tierLimit × SAFETY_BUFFER)` for bucket sizes (0.8x multiplier). The fix changes this to `Math.floor(tierLimit × BURST_MULTIPLIER)` (1.5x multiplier). This is a **deliberate increase** in burst capacity:

| Tier | Current Bucket | New Bucket | Change |
|------|---------------|------------|--------|
| BASIC read (20/s) | `floor(20×0.8)` = 16 | `ceil(20×1.5)` = 30 | +87% |
| BASIC write (10/s) | `floor(10×0.8)` = 8 | `ceil(10×1.5)` = 15 | +87% |

**Why this is correct:** The old formula used `SAFETY_BUFFER` (0.8) for BOTH bucket size AND refill rate, which conflated two distinct concepts. The fix separates them:
- **Bucket size** (burst capacity): uses `BURST_MULTIPLIER` (1.5) — allows short bursts above the sustained rate (e.g., startup, reconnection scenarios)
- **Refill rate** (sustained throughput): uses `SAFETY_BUFFER` (0.8) — enforces the 20% headroom below published limits (FR-PI-03)

The larger buckets do NOT increase sustained API pressure — that's controlled solely by the refill rate. They only allow more burst headroom before the limiter starts queueing.

[Source: sprint-change-proposal-2026-03-11-rate-limiter.md#Edit-1; rationale: BURST_MULTIPLIER=1.5 allows 1.5× the per-second limit as instant burst capacity]

### Startup Log Field Mapping

AC #7 requires the log fields `readBurst`, `writeBurst`, `readSustained`, `writeSustained`. These map to implementation values:

| Log Field | Implementation Value | Example (BASIC tier) |
|-----------|---------------------|---------------------|
| `readBurst` | `maxReadTokens` (bucket capacity) | 30 |
| `writeBurst` | `maxWriteTokens` (bucket capacity) | 15 |
| `readSustained` | `readRefillRatePerSec` | 16.0 |
| `writeSustained` | `writeRefillRatePerSec` | 8.0 |

### Current Code — Verified Line References

**`src/common/utils/rate-limiter.ts`** (120 lines):
- Lines 1-16: Imports, `RateLimitTier` interface, `RATE_LIMIT_TIERS` constant (BASIC/ADVANCED/PREMIER/PRIME), `SAFETY_BUFFER = 0.8`, `ALERT_THRESHOLD = 0.7`
- Lines 22-38: `RateLimiter` class, constructor with `maxReadTokens`, `maxWriteTokens`, `refillRatePerSec = 1` (THE BUG), optional `logger`
- Lines 43-54: `fromTier()` — passes `1` as refill rate (THE BUG — line 52)
- Lines 56-68: `acquireRead()`, `acquireWrite()` — decrement tokens, call `checkUtilization()`
- Lines 70-76: `getUtilization()` — returns read/write utilization percentages
- Lines 78-93: `checkUtilization()` — warns at ≥70% utilization
- Lines 95-101: `waitIfNeeded()` — waits `1/refillRatePerSec` seconds if tokens < 1
- Lines 103-119: `refill()` — adds `elapsed × refillRatePerSec` to BOTH buckets using SAME rate (BUG: should be separate)

**`src/connectors/kalshi/kalshi.connector.ts`**:
- Line 30: `import { RateLimiter } from '../../common/utils/rate-limiter.js'`
- Line 72: `private readonly rateLimiter: RateLimiter` (must remove `readonly`)
- Line 127: `this.rateLimiter = new RateLimiter(24, 10, 1, this.logger)` (THE BUG)
- Lines 129-158: `onModuleInit()` — needs `initializeRateLimiterFromApi()` call

**`src/connectors/polymarket/polymarket.connector.ts`**:
- Line 30: `import { RateLimiter } from '../../common/utils/rate-limiter.js'`
- Line 46: `private readonly rateLimiter: RateLimiter`
- Line 79: `this.rateLimiter = new RateLimiter(20, 4, 1, this.logger)` (SAME BUG)

**`src/common/utils/index.ts`** line 2: `export { RateLimiter, RATE_LIMIT_TIERS } from './rate-limiter.js'`

**All RateLimiter callers (non-test, verified via codebase search):**
- `kalshi.connector.ts` (constructor)
- `polymarket.connector.ts` (constructor)
- `trade-export.controller.ts` line 345: `resetRateLimiter()` — **unrelated** (this is a different, local rate limiter for CSV export throttling, not a `RateLimiter` class instance)

### RATE_LIMIT_TIERS — Current Values

```typescript
export const RATE_LIMIT_TIERS: Record<string, RateLimitTier> = {
  BASIC: { read: 20, write: 10 },
  ADVANCED: { read: 30, write: 30 },
  PREMIER: { read: 100, write: 100 },
  PRIME: { read: 400, write: 400 },
};
```

These are Kalshi-specific tiers. Values represent per-second limits. Polymarket does not use this map — it uses `fromLimits()` directly.

[Source: pm-arbitrage-engine/src/common/utils/rate-limiter.ts:8-13]

### AccountApi Integration Pattern

The `kalshi-typescript@3.8.0` SDK provides `AccountApi` alongside the existing `MarketApi` and `OrdersApi`. It uses the same `Configuration` object:

```typescript
import { AccountApi } from 'kalshi-typescript';

// In constructor (same config as MarketApi/OrdersApi):
this.accountApi = new AccountApi(config);

// In initializeRateLimiterFromApi():
const response = await this.accountApi.getAccountApiLimits();
const { read_limit, write_limit, usage_tier } = response.data;
```

The SDK uses axios internally. The response wraps in `AxiosResponse<GetAccountApiLimitsResponse>`.

[Source: pm-arbitrage-engine/node_modules/kalshi-typescript/dist/api/account-api.d.ts lines 55-62]

### What This Story Does NOT Change

- `RATE_LIMIT_TIERS` values — tiers stay the same, only how they're used changes
- `SAFETY_BUFFER` (0.8) and `ALERT_THRESHOLD` (0.7) constants — unchanged
- `IPlatformConnector` interface — unchanged
- `RateLimiter` public API (`acquireRead`, `acquireWrite`, `getUtilization`) — unchanged signatures
- Monitoring event emissions — unchanged
- Trade-export controller's local rate limiter — different mechanism, not affected
- Prisma schema — no changes
- No new dependencies

### Pre-Existing Test Failure

1 pre-existing e2e failure: `test/logging.e2e-spec.ts` line 88 — `"should emit events with correlation ID"` — `AssertionError: expected undefined to be defined` (event.timestamp). This is unrelated to rate limiting and has existed since at least Story 8.7 (baseline: 1744 passed, 1 failed, 2 todo).

[Source: Verified via `pnpm test --run` on 2026-03-11]

### Previous Story Intelligence

**From Story 8.7 (LLM Batch Parallelization — immediately prior):**
- Test baseline: 1745 passed → current run shows 1744 passed (minor variance from timing-sensitive tests)
- Env var pattern: add to both `.env.example` and `.env.development` in the same location
- Constructor config pattern: `this.configService.get<string>('KEY', 'DEFAULT')`
- Lad MCP review caught a default value bug (`|| 10` vs `|| 1`) — precedent for careful default handling
- All 25 existing tests passed unchanged after core refactor

[Source: 8-7-discovery-llm-batch-parallelization.md — Completion Notes]

### Testing Strategy

- **Framework:** Vitest 4, co-located specs (`*.spec.ts` next to source)
- **Mock setup:** Manual DI mocks (not `@golevelup/ts-vitest`)
- **Baseline:** 101 test files, 1744 passed, 1 failed (pre-existing), 2 todo
- **Existing rate-limiter tests:** 7 tests — all construct with `new RateLimiter(16, 8, 1, logger)`, must update to 4-param constructor
- **Existing kalshi.connector tests:** ~10 describe blocks, mock `MarketApi`/`OrdersApi`/`KalshiAuth` — add `AccountApi` mock
- **New test targets:**
  - `rate-limiter.spec.ts`: +4 tests (fromLimits, fromTier/fromLimits equivalence, asymmetric refill, startup log)
  - `kalshi.connector.spec.ts`: +3 tests (API success, API failure fallback, skip when unconfigured)
  - `polymarket.connector.spec.ts`: +1 test (correct refill rate initialization)

### Project Structure Notes

- All modified files are within existing module boundaries — no new modules, no new directories
- `RateLimiter` stays in `common/utils/` — correct placement per architecture (shared utility)
- `AccountApi` integration is inside `connectors/kalshi/` — connector-internal concern, no module boundary violation
- Barrel export `common/utils/index.ts` already exports `RateLimiter` and `RATE_LIMIT_TIERS` — no changes needed unless `BURST_MULTIPLIER` is exported (unlikely — internal constant)

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11-rate-limiter.md] — Full change proposal: problem statement, impact analysis, 5 edit proposals, success criteria
- [Source: _bmad-output/planning-artifacts/prd.md#FR-PI-03] — "Enforce platform-specific rate limits with 20% safety buffer"
- [Source: _bmad-output/planning-artifacts/prd.md#FR-PI-04] — "Track API rate limit utilization, alert at 70%"
- [Source: _bmad-output/planning-artifacts/architecture.md#NFR-I2] — "Rate limit enforcement with 20% buffer"
- [Source: pm-arbitrage-engine/src/common/utils/rate-limiter.ts] — Current RateLimiter class (120 lines, bug at lines 31, 52, 107)
- [Source: pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts] — KalshiConnector (bug at line 127)
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts] — PolymarketConnector (bug at line 79)
- [Source: pm-arbitrage-engine/node_modules/kalshi-typescript/dist/models/get-account-api-limits-response.d.ts] — SDK response model (usage_tier, read_limit, write_limit)
- [Source: pm-arbitrage-engine/node_modules/kalshi-typescript/dist/api/account-api.d.ts] — AccountApi.getAccountApiLimits() method
- [Source: 8-7-discovery-llm-batch-parallelization.md] — Previous story context and test baseline
- [Source: docs.kalshi.com/changelog] — "New endpoint: GET /account/limits" (retrieved via web search)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Lint error: `AccountApi` barrel import from `kalshi-typescript` produced `@typescript-eslint/no-unsafe-call` — resolved by using deep import path (`kalshi-typescript/dist/api/account-api.js`) matching existing `OrdersApi` pattern
- Test mock gap: `AccountApi` mock on barrel path didn't apply to deep import — added separate `vi.mock('kalshi-typescript/dist/api/account-api.js')` block
- Timing-sensitive test (`degradation-detection.service.spec.ts`) flaked once on full suite — pre-existing, not related to changes

### Completion Notes

- **Baseline**: 1744 passed, 1 failed (pre-existing e2e), 2 todo
- **Final**: 1753 passed (+9 new tests), 0 failed, 2 todo
- **New tests**: 4 in `rate-limiter.spec.ts`, 3 in `kalshi.connector.spec.ts`, 1 in `polymarket.connector.spec.ts`, 1 implicit (fromTier now exercises fromLimits)
- **Lint**: 0 errors, 0 warnings
- **Lad MCP review**: Primary reviewer (kimi-k2.5) confirmed all AC met, no actionable findings. Secondary reviewer (glm-5) timed out.
- **Deviation from story**: Task 2.4 specified `import { AccountApi } from 'kalshi-typescript'` but the barrel export has unresolved generic types causing lint errors. Used deep import path `kalshi-typescript/dist/api/account-api.js` instead, matching the existing `OrdersApi` pattern. Also added a local `KalshiAccountApi` interface (same pattern as `KalshiOrdersApi`) to avoid unsafe type propagation from the SDK.

### Code Review Fixes (Amelia — Claude Opus 4.6)

**3 MEDIUM issues fixed:**
1. **M1 — Weak test assertion for Kalshi API success path**: Changed mock to use PREMIER limits (100/100) instead of BASIC (20/10) so bucket size change is observable. Added `acquireRead()` + utilization check proving bucket is 150 (PREMIER), not 30 (BASIC).
2. **M2 — Untested invalid API data validation branch**: Added test with `read_limit: 0` verifying warning log and default limiter preservation.
3. **M3 — `fromLimits()` missing input validation**: Added guard throwing on non-positive `readLimit`/`writeLimit`, with test covering zero, negative, and both-negative cases.

**2 LOW issues accepted (no fix):**
- L1: Polymarket test bucket size assertion — acceptable given `fromLimits()` is tested thoroughly in `rate-limiter.spec.ts`.
- L2: Triple startup log — documented behavior per AC #7; reducing would require API change.

**Post-fix results:** 1755 passed, 0 failed, 2 todo, 0 lint errors.

### File List

- `src/common/utils/rate-limiter.ts` — Added `BURST_MULTIPLIER`, split refill rates, added `fromLimits()`, refactored `fromTier()`
- `src/common/utils/rate-limiter.spec.ts` — Updated constructor, added 4 new tests
- `src/connectors/kalshi/kalshi.connector.ts` — Added `AccountApi`, `initializeRateLimiterFromApi()`, `fromTier()` init, `KalshiAccountApi` interface
- `src/connectors/kalshi/kalshi.connector.spec.ts` — Added `AccountApi` mocks (barrel + deep), added 3 new tests
- `src/connectors/polymarket/polymarket.connector.ts` — Replaced hardcoded `RateLimiter` with `fromLimits(2, 2)`
- `src/connectors/polymarket/polymarket.connector.spec.ts` — Added 1 new test
- `.env.example` — Added `KALSHI_API_TIER`
- `.env.development` — Added `KALSHI_API_TIER`
