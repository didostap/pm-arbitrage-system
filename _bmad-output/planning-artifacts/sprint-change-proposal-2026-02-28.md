# Sprint Change Proposal — Polymarket Batch Order Book Migration

**Date:** 2026-02-28
**Triggered by:** Rate limit utilization at 91.8% with 8 configured pairs
**Current Epic:** 6.5 (Paper Trading Validation)
**Scope Classification:** Minor — Direct dev implementation

---

## 1. Issue Summary

The Polymarket connector calls `getOrderBook(tokenId)` sequentially for each configured contract pair inside `DataIngestionService.ingestCurrentOrderBooks()`. With 8 active pairs and a rate limiter bucket of 8 read tokens, the bucket drains to zero every polling cycle, triggering high-utilization warnings well above the 70% threshold (FR-PI-04).

This creates three compounding problems:
1. **Rate limit exhaustion** — 91.8% utilization with only 8 pairs; no headroom for retries, health checks, or order polling
2. **Data staleness** — ~960ms spread between first and last order book fetch creates phantom dislocations (false positives) and masks real opportunities (false negatives) in arbitrage detection
3. **Linear scaling** — adding pairs linearly degrades rate budget and latency

The `@polymarket/clob-client` SDK already exposes `getOrderBooks(params: BookParams[])` supporting up to 500 tokens per request, reducing consumption to 1 token per cycle regardless of pair count.

**Discovery context:** Observed during Epic 6.5 operational readiness analysis, post story 6-5-2 (Deployment Runbook).

---

## 2. Impact Analysis

### Epic Impact
- **Epic 6.5 (in-progress):** One new story (6-5-2a) inserted after 6-5-2, before 6-5-3. All subsequent validation stories benefit from running against the batch pipeline.
- **All other epics:** No impact. Epics 7-12 consume normalized data downstream and are unaffected by ingestion method changes.

### Story Impact
- **New story 6-5-2a:** Polymarket Batch Order Book Migration + Health Log Optimization
- **Existing stories 6-5-3 through 6-5-6:** No changes needed; they benefit from improved data quality and rate limit headroom
- **No completed stories affected** — no rework required

### Artifact Conflicts
- **PRD:** No conflicts. Change improves compliance with FR-PI-03, FR-PI-04, FR-DI-02, NFR-P2.
- **Architecture:** No conflicts. `IPlatformConnector` unchanged — batch method stays Polymarket-specific since Kalshi has no equivalent.
- **UI/UX:** No impact (backend-only).

### Technical Impact
- `PolymarketConnector` — new `getOrderBooks()` method (~30 lines)
- `DataIngestionService` — replace sequential Polymarket loop with batch call (~20 lines changed)
- `PlatformHealthService` — guard DB write to status transitions only (~5 lines)
- Tests — update `polymarket.connector.spec.ts` and `data-ingestion.service.spec.ts` (~60-80 lines)
- No schema migrations, no new dependencies, no env var changes

---

## 3. Recommended Approach

**Path: Direct Adjustment** — add story 6-5-2a to Epic 6.5.

### Rationale
- **Effort:** Low. SDK method exists; implementation is mechanical (wrap, call, normalize, test).
- **Risk:** Low. No architectural changes, no schema migrations, no new dependencies.
- **Timing:** Ideal. Inserting before validation stories means all paper trading validation reflects the production pipeline.
- **FR/NFR compliance:** Fixes FR-PI-03 (rate limit enforcement with 20% buffer) and FR-PI-04 (70% alert) violations. Improves FR-DI-02 (500ms normalization) and NFR-P2 (1s detection cycle).

### Alternatives Considered
| Option | Verdict | Reason |
|--------|---------|--------|
| Rollback | Not viable | Nothing broken, just suboptimal |
| MVP scope change | Not applicable | MVP already complete (Epics 1-6 done) |

### Performance Comparison

| Metric | Current (sequential) | Batch | Improvement |
|--------|---------------------|-------|-------------|
| HTTP round-trips (8 pairs) | 8 | 1 | 8x fewer |
| Ingestion latency (8 pairs) | ~960ms | ~150ms | ~6x faster |
| Rate limit tokens consumed | 8 | 1 | 8x fewer |
| Data consistency window | ~960ms spread | Single timestamp | Near-zero |
| Max pairs before rate limit | ~50 | 500 per request | 10x headroom |

---

## 4. Detailed Change Proposals

### 4a. PolymarketConnector — Add batch method

**File:** `src/connectors/polymarket/polymarket.connector.ts`

**Change:** Add `getOrderBooks(contractIds: string[])` method that:
- Calls `rateLimiter.acquireRead()` once
- Calls `clobClient.getOrderBooks(params)` with all token IDs as `BookParams[]`
- Normalizes each returned `OrderBookSummary` via `this.normalizer.normalizePolymarket()`
- Returns `NormalizedOrderBook[]`

**Interface:** `IPlatformConnector` unchanged. Batch method is Polymarket-specific.

### 4b. DataIngestionService — Use batch path

**File:** `src/modules/data-ingestion/data-ingestion.service.ts`

**Change:** In `ingestCurrentOrderBooks()`, replace the sequential Polymarket `for` loop with a single `getOrderBooks()` call, then iterate results for persistence and event emission.

### 4c. PlatformHealthService — Transition-only writes

**File:** `src/modules/data-ingestion/platform-health.service.ts`

**Change:** Guard `prisma.platformHealthLog.create()` to only persist on status transitions (e.g., `healthy → degraded`). The `previousStatus` map already tracks transitions — reuse it for the persistence guard. Eliminates ~99% of health log writes during normal operation (~5,760 rows/day → near zero).

### 4d. Tests

**Files:** `polymarket.connector.spec.ts`, `data-ingestion.service.spec.ts`

**Changes:**
- Add tests for batch `getOrderBooks()` (happy path, partial failures, empty results)
- Update ingestion tests for batch call path
- Add test for health log transition-only writes

---

## 5. Implementation Handoff

**Scope:** Minor — direct dev implementation

| Role | Action |
|------|--------|
| SM | Update `sprint-status.yaml` with 6-5-2a entry |
| SM | Add Story 6-5-2a to `epics.md` under Epic 6.5 |
| Dev agent | Implement via `/tdd` workflow with the story file |

**Sequencing:** 6-5-2 (done) → **6-5-2a** → 6-5-3 → 6-5-4 → 6-5-5 → 6-5-6

**Success criteria:**
- `pnpm test` passes with batch path coverage
- `pnpm lint` clean
- Rate limit consumption drops from 8 tokens/cycle to 1 token/cycle
- Health log writes occur only on status transitions
