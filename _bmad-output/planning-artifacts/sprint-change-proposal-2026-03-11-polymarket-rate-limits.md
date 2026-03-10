# Sprint Change Proposal: Polymarket Rate Limiter Configuration Fix

**Date:** 2026-03-11
**Triggered by:** Operational warning — 77.4% Polymarket read rate limit utilization with 29 active pairs
**Scope Classification:** Minor — Direct implementation by dev team

---

## Section 1: Issue Summary

### Problem Statement

The Polymarket connector's rate limiter is configured with `RateLimiter.fromLimits(2, 2)` based on an incorrect assumption of "~100 req/min (~1.67/s)". Polymarket's actual published per-endpoint limits are 25-75x higher. The tiny 3-token read bucket (from `ceil(2 × 1.5)`) drains after 2-3 rapid reads, triggering false 70% utilization alerts (FR-PI-04) that mask genuine rate pressure.

### Discovery Context

- **When:** 2026-03-11 14:01:55 UTC+1, during live trading operations with 29 active pairs
- **How:** Structured warning log from `PolymarketConnector`: `utilization: "77.4%"`, `tokensRemaining: 0.6784`
- **Root cause:** The code comment at `polymarket.connector.ts:77` cites "~100 req/min" with no source URL. This number appears to originate from the old unauthenticated public endpoint limit (referenced in third-party docs like Nautilus Trader's Polymarket integration). Polymarket has since increased their CLOB API limits significantly.

### Evidence

- Warning log math: `1 - 0.678/3 = 77.4%` — matches reported utilization exactly
- With exit monitor + batch ingestion running in the same cycle, 2-3 `acquireRead()` calls happen in quick succession, draining the 3-token bucket
- **Verified Polymarket rate limits** (source: `https://docs.polymarket.com/api-reference/rate-limits`, fetched 2026-03-11):

| Endpoint | Published Limit | Per-Second |
|---|---|---|
| `GET /book` (single) | 1,500 req / 10s | 150/s |
| `GET /books` (batch) | 500 req / 10s | 50/s |
| `GET /price` | 1,500 req / 10s | 150/s |
| `POST /order` | 3,500 req / 10s burst; 36,000 / 10min sustained | 350/s burst; 60/s sustained |
| `DELETE /order` | 3,000 req / 10s burst; 30,000 / 10min sustained | 300/s burst; 50/s sustained |
| General CLOB | 9,000 req / 10s | 900/s |

- **Historical context:** A Scribd-hosted snapshot of the Polymarket rate limits page (document #952835520) shows earlier, lower limits (`/book`: 200/10s, `/books`: 80/10s), confirming Polymarket increased limits at some point (also referenced in their changelog: "Increased API Rate Limits"). The "~100 req/min" comment in our code predates both sets of numbers and likely reflects the old unauthenticated public endpoint rate (Nautilus Trader docs reference "100 req/min per IP" for public endpoints, "300 req/min per key" for authenticated reads).

---

## Section 2: Impact Analysis

### Epic Impact

- **No epics affected.** This is a configuration correction to existing code, not scoped to any epic.
- **Epic 10** (Model-Driven Exits): **Unblocked** — continuous edge recalculation (Story 10-1) would increase Polymarket read frequency. Correct limits prevent future false alerts.
- **Epic 9** (Advanced Risk): No dependency — proceeds as planned.

### Story Impact

- **Story 8-8** (rate-limiter-refill-rate-fix): Already delivered. That story fixed the Kalshi refill rate bug and updated Polymarket to use `fromLimits(2, 2)`, but accepted `2/s` as correct based on the uncited "~100 req/min" assumption. This proposal corrects that accepted baseline.

### Artifact Conflicts

**No planning artifact changes required.** The PRD requirements are correct as written — the implementation doesn't match them:

| Requirement | PRD Spec | Current State | After Fix |
|---|---|---|---|
| FR-PI-03 | Platform-specific rate limits with 20% safety buffer | Buffer exists (0.8×) but applied to wrong baseline (2/s vs 50/s) | Refill at 50 × 0.8 = 40/s — correct enforcement |
| FR-PI-04 | Alert at 70% of published limits | Fires at 77.4% based on fictitious 2/s limit | Will fire only when genuinely approaching the real 50/s limit |
| NFR-I2 | Zero rate limit violations | Not violated yet, but zero headroom for scaling | Comfortable headroom (~0.25% utilization at 29 pairs) |

### Technical Impact

- **Files modified:** 2 (1 source, 1 test)
- **No new files, no new dependencies, no Prisma schema changes**
- **Interface unchanged:** `IPlatformConnector` and `RateLimiter` public API preserved
- **Backward-compatible:** Only the numeric arguments to `fromLimits()` change

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

Single corrective story slotted after Story 8-8, implementing:

1. **Update `fromLimits(2, 2)` → `fromLimits(50, 50)`** in `polymarket.connector.ts`
2. **Replace code comment** with cited source and rationale
3. **Update test** to verify new configuration

### Rationale

- **Effort:** Very low (~30 minutes)
- **Risk:** Very low — only numeric arguments change; `fromLimits()` infrastructure from Story 8-8 handles all safety buffer / burst multiplier logic
- **Timeline impact:** None — Epic 9 hasn't started
- **Modeling approach:** `fromLimits(50, 50)` models the tightest relevant endpoint (`GET /books` at 500/10s = 50/s). After safety buffer: refill = 40/s, bucket = 75 tokens. Our actual consumption (~5-10 reads per 30s cycle) puts utilization well under 1%, maintaining the 20% safety buffer the PRD requires.
- **Write limit:** `POST /order` burst is 350/s, sustained is 60/s. Using 50/s for writes is conservative and safe — our write frequency is negligible (0-4 per cycle).
- **Alternatives rejected:**
  - Per-endpoint buckets (separate limits for `/book` vs `/books`): Over-engineering for current usage patterns. Revisit if we approach 50/s sustained.
  - WebSocket migration: Eliminates REST read overhead entirely but is a larger architectural change. Appropriate for Epic 10+, not a config fix.

---

## Section 4: Detailed Change Proposals

### Edit 1: `src/connectors/polymarket/polymarket.connector.ts`

**Section:** Constructor rate limiter initialization (lines 77-83)

**OLD:**
```typescript
    // Polymarket rate limits: ~100 req/min (~1.67/s), no published write limit.
    // fromLimits(2, 2) → readBucket: 3 tokens (ceil(2×1.5)), readRefill: 1.6/s (2×0.8)
    // Note: bucket size (3 tokens) is sized for post-batch-migration read patterns (~1-3 reads/cycle).
    // If batch order book fetch (Story 6-5-2a) is reverted or read patterns increase
    // (e.g., retry storms), revisit these limits. withRetry() exponential backoff provides
    // additional mitigation.
    this.rateLimiter = RateLimiter.fromLimits(2, 2, this.logger);
```

**NEW:**
```typescript
    // Polymarket CLOB API rate limits (verified 2026-03-11):
    //   Source: https://docs.polymarket.com/api-reference/rate-limits
    //   GET /books (batch): 500 req/10s = 50/s (tightest relevant endpoint)
    //   GET /book (single): 1,500 req/10s = 150/s
    //   POST /order: 3,500 req/10s burst, 36,000/10min sustained
    // Modeled against GET /books (50/s) as the conservative baseline.
    // fromLimits(50, 50) → readBucket: 75 tokens, readRefill: 40/s (50×0.8 safety buffer)
    // At current load (~5-10 reads/30s cycle): utilization < 1%.
    this.rateLimiter = RateLimiter.fromLimits(50, 50, this.logger);
```

**Rationale:** Replace uncited "~100 req/min" with verified, sourced limits. Model against the tightest relevant endpoint (`GET /books` at 50/s) per FR-PI-03.

### Edit 2: `src/connectors/polymarket/polymarket.connector.spec.ts`

**Section:** Existing test for Polymarket rate limiter initialization

**Change:** Update the assertion that verifies `fromLimits()` is called with `(50, 50)` instead of `(2, 2)`.

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by the dev agent as a standalone corrective story.

### Handoff

- **Recipient:** Dev agent
- **Deliverable:** Story file with ACs, tasks, and dev notes (to be created via Create Story workflow)
- **Story ID:** `8-9-polymarket-rate-limit-config-fix` (slots after Story 8-8)

### Success Criteria

- Polymarket read utilization drops from ~77.4% to <1% with 29 active pairs
- 70% utilization alert (FR-PI-04) fires only when genuinely approaching the real 50/s limit
- Code comment includes source URL (`https://docs.polymarket.com/api-reference/rate-limits`) and verification date
- All existing tests pass; test updated to verify new configuration
- Zero 429 errors maintained
- `pnpm lint` reports zero errors
