# Sprint Change Proposal: Rate Limiter Refill Rate Bug Fix

**Date:** 2026-03-11
**Triggered by:** Operational incident — 99.8% Kalshi read rate limit utilization with 29 active pairs
**Scope Classification:** Minor — Direct implementation by dev team

---

## Section 1: Issue Summary

### Problem Statement

The `RateLimiter` class in `src/common/utils/rate-limiter.ts` hardcodes `refillRatePerSec = 1` regardless of the configured API tier. The Kalshi BASIC tier allows 20 reads/sec and 10 writes/sec, but with a refill rate of 1 token/sec, the system's sustained throughput is only 1 read/sec — **5% of the available API capacity**.

With 29 active pairs, each 30-second polling cycle requires 29 sequential `getOrderBook()` calls. The 24-token read bucket drains after the 24th call, and each subsequent read stalls for ~1 second waiting on the trickle refill. This causes 5+ seconds of artificial delay per cycle.

### Discovery Context

- **When:** 2026-03-11 12:03:45 UTC+1, during live trading operations
- **How:** Structured warning log from `KalshiConnector`: `utilization: "99.8%"`, `tokensRemaining: 0.042`
- **Root cause confirmed by:** Code inspection of `rate-limiter.ts:52` (`fromTier()` hardcodes refill to 1) and `kalshi.connector.ts:127` (`new RateLimiter(24, 10, 1, ...)`)

### Evidence

- Warning log: `1 - 0.042/24 = 99.825%` — matches reported 99.8% exactly
- Kalshi API docs confirm BASIC tier = 20 read/s, 10 write/s (verified 2026-03-11)
- The bug has existed since Epic 1 Story 1-3 (Kalshi connector) but was masked by low pair counts (~8 pairs during early epics)

---

## Section 2: Impact Analysis

### Epic Impact

- **No epics affected.** This is a cross-cutting infrastructure bug fix to existing code, not scoped to any epic.
- **Epic 9** (Advanced Risk, next in backlog): No dependency — proceeds as planned.
- **Epic 10** (Model-Driven Exits): **Unblocked** by this fix — continuous edge recalculation (Story 10-1) would immediately saturate the limiter without correct refill rates.
- **Epic 11** (Platform Extensibility): **Prevented** — fixing `fromTier()` now stops the bug from propagating to future connector implementations.

### Artifact Conflicts

**No planning artifact changes required.** The PRD requirements (FR-PI-03, FR-PI-04, NFR-I2) are correct — the implementation doesn't match them:

| Requirement | PRD Spec | Current State | After Fix |
|---|---|---|---|
| FR-PI-03 | 20% safety buffer, queue when approaching limits | Buffer exists (0.8) but refill=1 negates it | Refill at tier rate x 0.8 = correct enforcement |
| FR-PI-04 | Alert at 70% utilization | Fires constantly at 99.8% | Will fire rarely, as intended |
| NFR-I2 | Zero rate limit violations | Operating at 99.8% — one pair from stalls | Comfortable headroom (~15-20% utilization) |

### Technical Impact

- **Files modified:** 5 (2 source, 2 test, 2 env)
- **No new files, no new dependencies, no Prisma schema changes**
- **Interface unchanged:** `IPlatformConnector` and `RateLimiter` public API preserved
- **Backward-compatible:** `RateLimiter` constructor signature changes (callers must provide explicit refill rates), but all callers are internal

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

Single corrective story slotted before Epic 9, implementing:

1. **Fix `RateLimiter` class** — Split single `refillRatePerSec` into separate `readRefillRatePerSec` and `writeRefillRatePerSec`. Fix `fromTier()` to derive refill rates from tier config x safety buffer. Add `fromLimits()` factory for dynamic API-driven initialization. Add `BURST_MULTIPLIER = 1.5` constant. Add startup configuration log.

2. **Fix `KalshiConnector`** — Replace hardcoded `new RateLimiter(24, 10, 1)` with `RateLimiter.fromTier(defaultTier)`. Add `initializeRateLimiterFromApi()` calling `GET /account/limits` at startup. Fallback hierarchy: API response -> `KALSHI_API_TIER` env var -> `'BASIC'` default.

3. **Update tests** — 7 new test cases across 2 spec files covering: separate refill rates, `fromLimits()` factory, `fromTier()`/`fromLimits()` equivalence, startup logging, API-driven initialization, graceful fallback, skip-when-unconfigured.

4. **Add env var** — `KALSHI_API_TIER` in `.env.example` and `.env.development`.

### Rationale

- **Effort:** Low (~2-4 hours)
- **Risk:** Low — token bucket algorithm is well-understood, changes isolated inside connector boundary
- **Timeline impact:** None — Epic 9 hasn't started
- **Alternatives rejected:**
  - Hardcoding `refillRatePerSec = 16` (Option A): Fragile, same mistake recurs with new connectors/tiers
  - Rollback: Nothing to roll back — bug existed since Epic 1
  - MVP review: N/A — MVP already delivered

---

## Section 4: Detailed Change Proposals

### Edit 1: `src/common/utils/rate-limiter.ts`

- Add `BURST_MULTIPLIER = 1.5` constant alongside existing `SAFETY_BUFFER` and `ALERT_THRESHOLD`
- Replace single `refillRatePerSec` constructor param with explicit `readRefillRatePerSec` + `writeRefillRatePerSec` (no defaults — forcing callers to be explicit is the point of this fix)
- Fix `fromTier()` to delegate to new `fromLimits()` — both apply safety buffer to refill rate and burst multiplier to bucket size
- Add `static fromLimits(readLimit, writeLimit, logger)` factory for `GET /account/limits` integration
- Update `refill()` to use separate rates per bucket
- Update `waitIfNeeded()` to accept specific refill rate
- Add startup log: `"Rate limiter configured"` with `readBurst`, `writeBurst`, `readSustained`, `writeSustained`

### Edit 2: `src/connectors/kalshi/kalshi.connector.ts`

- Remove `readonly` from `rateLimiter` property (onModuleInit may replace it)
- Constructor: Replace `new RateLimiter(24, 10, 1, ...)` with `RateLimiter.fromTier(configService.get('KALSHI_API_TIER', 'BASIC'), ...)`
- `onModuleInit()`: Call `initializeRateLimiterFromApi()` before `connect()`
- New private method `initializeRateLimiterFromApi()`: Calls `GET /account/limits`, on success creates `RateLimiter.fromLimits(readLimit, writeLimit)`, on failure logs warning and keeps constructor default

### Edit 3: `src/common/utils/rate-limiter.spec.ts`

- Update `beforeEach` constructor: `new RateLimiter(16, 8, 16, 8, logger)` (4-param)
- New: `fromLimits()` factory test
- New: `fromTier`/`fromLimits` equivalence test
- New: Asymmetric refill rate verification (high read refill, low write refill)
- New: Startup configuration log assertion

### Edit 4: `src/connectors/kalshi/kalshi.connector.spec.ts`

- Add `mockGetAccountLimits` to SDK mock
- Add `KALSHI_API_TIER` to config mock
- New: API limits success — rate limiter reconfigured from API response
- New: API limits failure — graceful fallback to env var tier
- New: Skip when API key not configured

### Edit 5: `.env.example` + `.env.development`

- Add `KALSHI_API_TIER=BASIC` with comment documenting valid values (`BASIC|ADVANCED|PREMIER|PRIME`)

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by the dev agent as a standalone corrective story.

### Handoff

- **Recipient:** Dev agent
- **Deliverable:** Story file with full ACs, tasks, and dev notes (to be created via Create Story workflow)
- **Story ID:** `8-8-rate-limiter-refill-rate-fix` (slots after Epic 8 completion, before Epic 9)

### Success Criteria

- Kalshi read utilization drops from ~99.8% to ~15-20% with 29 active pairs at BASIC tier
- `GET /account/limits` called at startup; rate limiter configured from API response
- Startup log shows configured sustained/burst rates
- 70% utilization alert fires only when genuinely approaching limits
- All existing tests pass; 7 new tests added
- Zero 429 errors (maintained — was already true, now with proper headroom)

### Dev Notes for Story

- Verify whether `kalshi-typescript` SDK exposes `getAccountLimits()`; if not, add a raw HTTP call to `GET /account/limits` using the existing auth/request infrastructure
- ~~Verify the `GET /account/limits` response schema~~ **VERIFIED 2026-03-11**: SDK model `GetAccountApiLimitsResponse` has fields `usage_tier` (NOT `tier`), `read_limit`, `write_limit` — confirmed in `kalshi-typescript@3.8.0` at `dist/models/get-account-api-limits-response.d.ts`
- `RATE_LIMIT_TIERS`, `SAFETY_BUFFER`, `ALERT_THRESHOLD` constants stay as-is — only add `BURST_MULTIPLIER = 1.5`
- Constructor must NOT have default values for refill rate params — explicit is the fix
- `KALSHI_API_TIER` env var is a fallback, not a requirement. If `GET /account/limits` succeeds, use the API response; if it fails, fall back to env var or default BASIC
