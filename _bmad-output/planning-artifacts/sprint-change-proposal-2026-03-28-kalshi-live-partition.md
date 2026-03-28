# Sprint Change Proposal: Kalshi Live Endpoint Dual-Partition Routing

**Date:** 2026-03-28
**Triggered by:** Runtime investigation — Kalshi historical cutoff frozen at 2025-12-27, post-cutoff data inaccessible
**Status:** Approved
**Scope:** Minor — direct implementation by dev team

---

## Section 1: Issue Summary

The `KalshiHistoricalService` (Story 10-9-1a) only queries the **historical** partition endpoint (`/historical/markets/{ticker}/candlesticks`). Kalshi's live/historical data partition, introduced Feb 2026, places a cutoff at ~2025-12-27. Data after this date is only available through **live** candlestick endpoints, which use a different URL structure and response format. The code clamps `effectiveEnd` to the cutoff and returns 0 records for any post-cutoff date range — making ~3 months of Kalshi price data inaccessible for backtesting.

**Discovery:** Runtime investigation on 2026-03-28 revealed the `/historical/cutoff` returns `market_settled_ts: '2025-12-27T00:00:00Z'`. Any backtest targeting recent data gets zero Kalshi candlesticks.

**Evidence:**

- Cutoff response frozen at 2025-12-27 (by design — partition boundary)
- `ingestPrices()` lines 106-118: clamps end to cutoff, returns `recordCount: 0` when range is fully post-cutoff
- Same issue affects `ingestTrades()` (lines 199-211) — trades cutoff at `trades_created_ts`
- Design doc (10-9-0) correctly identified gotchas K1 (field naming divergence) and K3 (data removed from live endpoints) but Story 10-9-1a only implemented the historical side with a comment "use live endpoint or wait"

---

## Section 2: Impact Analysis

### Epic Impact — Epic 10.9 (in-progress)

| Story | Status | Impact |
|-------|--------|--------|
| 10-9-1a | done | **Root cause** — only historical partition implemented. Live endpoint routing deferred. |
| 10-9-3 | done | Backtest engine runs on incomplete Kalshi data (missing Jan-Mar 2026). Results may undercount Kalshi-side opportunities. |
| 10-9-4 | done | Calibration reports based on potentially skewed data (Polymarket has full coverage, Kalshi doesn't). Parameter recommendations may be biased. |
| 10-9-5 | done | Dashboard displays whatever data is available — correct UI, wrong underlying data. |
| 10-9-6 | backlog | Already mentions "Kalshi historical cutoff advancement" in AC — but this is incremental freshness, not the live endpoint gap. |

### Artifact Conflicts

- **Architecture doc (line 668):** References `Kalshi API (/candlesticks, /historical/trades)` — doesn't distinguish live vs historical candlestick endpoints. Needs update to document dual-endpoint routing.
- **Design doc (10-9-0, lines 119-123):** Gotchas K1/K3 correctly identified the risk and mitigation ("separate parsers per endpoint; normalization layer maps both to common schema") but this mitigation was never implemented.
- **Story 10-9-1a (lines 174-185):** Cutoff routing logic spec says "use live endpoint or wait" — the "wait" path is a dead end because the cutoff hasn't advanced in 3+ months.
- **PRD:** No direct conflict — backtesting requirement is met once data coverage is complete.
- **UI/UX:** No conflict — dashboard correctly renders available data.

### Technical Gaps

1. **Live candlestick endpoint URL:** `GET /series/{series_ticker}/markets/{ticker}/candlesticks` — requires `series_ticker` which is NOT stored in `ContractMatch`. Alternative: `GET /markets/candlesticks` batch endpoint (added Nov 2025, doesn't need series_ticker).
2. **Response format divergence:** Live uses `open_dollars`/`volume_fp`, historical uses `open`/`volume`. Need separate parser.
3. **Same issue for trades:** `ingestTrades()` has the same cutoff clamping. Live trades endpoint is `GET /markets/trades` (different from `/historical/trades`).

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — Add a new hotfix story to patch `KalshiHistoricalService` with dual-endpoint routing.

**Rationale:**

- **Contained scope:** Changes are isolated to `src/modules/backtesting/ingestion/kalshi-historical.service.ts` and its spec file. No module boundary changes.
- **No rollback needed:** Existing historical ingestion works correctly for pre-cutoff data. We're adding capability, not fixing broken logic.
- **Critical path:** Stories 10-9-3 and 10-9-4 already ran with incomplete data. Fixing ingestion enables re-running backtests with complete Kalshi coverage.
- **Effort:** Low — estimated 1 story (similar size to the original service ~350 lines, adding ~100-150 lines for live endpoint handling)
- **Risk:** Low — well-understood API change, documented in design doc gotchas
- **Timeline:** No impact on Epic 10.9 completion — this slots in before 10-9-6 (which already mentions cutoff handling)

**Alternatives considered:**

- **Rollback 10-9-1a:** Not viable. 10-9-3, 10-9-4, 10-9-5 all build on it. Would cascade.
- **Fold into 10-9-6:** 10-9-6 is about incremental freshness, not fixing a fundamental ingestion gap. Mixing concerns makes both harder.
- **MVP review:** Not needed — this is a bug fix, not a scope change.

---

## Section 4: Detailed Change Proposals

### Change 1: New Story — 10-9-1a-fix: Kalshi Live Endpoint Dual-Partition Routing

**Type:** Hotfix story (insert before 10-9-6)
**Priority:** P0 (blocks accurate backtesting)

```
As an operator,
I want Kalshi price and trade ingestion to fetch data from BOTH
the historical and live API partitions,
So that backtesting has complete Kalshi coverage across the full
date range (not just pre-cutoff).

Acceptance Criteria:

1. Given a date range spanning the cutoff boundary
   When ingestPrices() runs
   Then data before cutoff is fetched from /historical/markets/{ticker}/candlesticks
   And data after cutoff is fetched from the live candlestick endpoint
   And both datasets are normalized to the same schema and persisted

2. Given the live candlestick endpoint returns _dollars suffix fields
   When response is parsed
   Then open_dollars/high_dollars/low_dollars/close_dollars are mapped
   to the same Decimal columns as historical open/high/low/close
   And volume_fp maps to volume, open_interest_fp to openInterest

3. Given a date range entirely after the cutoff
   When ingestPrices() runs
   Then only the live endpoint is queried (no historical call)
   And records are persisted normally (not 0 records)

4. Given a date range entirely before the cutoff
   When ingestPrices() runs
   Then behavior is unchanged (historical endpoint only)

5. Given ingestTrades() has the same cutoff clamping
   When a date range spans the cutoff
   Then trades before cutoff use /historical/trades
   And trades after cutoff use the live trades endpoint

6. Given the live candlestick endpoint requires series_ticker
   When the system needs to resolve series_ticker for a market
   Then it uses the batch endpoint GET /markets/candlesticks
   (which does NOT require series_ticker) OR looks up
   series_ticker via GET /markets/{ticker} and caches it
```

### Change 2: Update Story 10-9-6 AC

```
Story: 10-9-6 (Historical Data Freshness)
Section: Acceptance Criteria

OLD:
And Kalshi historical cutoff advancement is handled
(data migrating from live to historical tier)

NEW:
And Kalshi historical cutoff advancement is handled
(as cutoff advances, previously-ingested live data is now
covered by the historical partition — no re-fetch needed,
data already persisted from live ingestion in 10-9-1a-fix)
```

**Rationale:** After 10-9-1a-fix, live data is already ingested. 10-9-6 only needs to handle incremental new data, not backfill the live-to-historical migration.

### Change 3: Update Design Doc 10-9-0

```
Section: 1.1 Kalshi Historical API -> Endpoints table

OLD:
| `/historical/cutoff` | GET | None | Returns partition boundary timestamps |
| `/historical/markets/{ticker}/candlesticks` | GET | None | OHLCV candlestick data |
| `/historical/trades` | GET | None | Cursor-paginated trade history |

NEW:
| `/historical/cutoff` | GET | None | Returns partition boundary timestamps |
| `/historical/markets/{ticker}/candlesticks` | GET | None | OHLCV candlestick data (pre-cutoff) |
| `/historical/trades` | GET | None | Cursor-paginated trade history (pre-cutoff) |
| `/markets/candlesticks` | GET | Auth | Batch OHLCV candlestick data (post-cutoff, live markets) |
| `/markets/trades` | GET | Auth | Trade history (post-cutoff, live markets) |
```

**Rationale:** Design doc is the authoritative source for API endpoint inventory. Must reflect dual-partition reality.

### Change 4: Update Architecture Doc

```
Section: Data flow diagram (line 668)

OLD:
├── Kalshi API (/candlesticks, /historical/trades)

NEW:
├── Kalshi API (/historical/candlesticks + /markets/candlesticks, /historical/trades + /markets/trades)
```

**Rationale:** Architecture doc should reflect actual data sources.

---

## Section 5: Implementation Handoff

**Scope Classification: Minor** — Direct implementation by dev team.

### Handoff

| Role | Responsibility |
|------|---------------|
| **SM (Bob)** | Create story file 10-9-1a-fix, update sprint-status.yaml |
| **Dev agent** | Implement dual-partition routing in KalshiHistoricalService, TDD |
| **Arbi** | Re-run backtests after fix to get accurate calibration |

### Sequencing

1. Implement 10-9-1a-fix (immediate — before 10-9-6)
2. Re-run ingestion for recent date ranges to backfill post-cutoff Kalshi data
3. Re-run backtest/calibration (10-9-3/10-9-4) with complete data
4. Continue with 10-9-6 (incremental freshness) as planned

### Success Criteria

- `ingestPrices()` returns >0 records for date ranges after 2025-12-27
- Backtest runs covering Jan-Mar 2026 include Kalshi candlestick data
- All existing tests pass + new tests for dual-endpoint routing

---

## Workflow Completion

- **Issue addressed:** Kalshi live/historical API partition — post-cutoff data inaccessible
- **Change scope:** Minor
- **Artifacts modified:** sprint-status.yaml, epics.md (10-9-6 AC), design doc (10-9-0), architecture doc
- **Routed to:** Dev agent for direct implementation
