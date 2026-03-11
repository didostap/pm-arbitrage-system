# Sprint Change Proposal — Kalshi Fixed-Point Migration & Orderbook Staleness Alerting

**Date:** 2026-03-12
**Triggered by:** External API breaking change (Kalshi Fixed-Point Migration)
**Scope classification:** Minor — Direct implementation by development team
**Status:** Approved

---

## Section 1: Issue Summary

**Problem statement:** Kalshi completed their "Fixed-Point Migration" on 2026-03-12, removing all legacy integer-based orderbook fields from REST and WebSocket APIs. The Kalshi connector is non-functional — `getOrderBook()` returns undefined, WebSocket snapshot/delta parsing fails silently. All Kalshi-side trading is blocked.

**Discovery context:** Discovered during live operation via runtime error at `kalshi.connector.ts:308`. The response now contains `{ orderbook_fp: { yes_dollars: [...], no_dollars: [...] } }` instead of `{ orderbook: { yes: [...], no: [...] } }`. Confirmed via web research that Kalshi's migration timeline had a hard cut on 2026-03-12.

**Secondary issue:** No automated alert fired when orderbook data stopped being valid. The failure was discovered manually via debugging. The existing `platform.health.degraded` event pathway does not cover orderbook data staleness — only WebSocket connection-level health.

**Evidence:**
- Runtime error: `response.data.orderbook` is `undefined`
- Debugger screenshots confirm `orderbook_fp` with `yes_dollars`/`no_dollars` string arrays
- Kalshi migration timeline: legacy fields deprecated Feb 21, removed Mar 12
- 6 source files affected in connector layer

---

## Section 2: Impact Analysis

### Epic Impact
- **Epic 9 (in-progress):** No impact. Risk management stories are orthogonal to connector layer.
- **Epics 10-12 (backlog):** No impact. All consume `NormalizedOrderBook` via interface — interface unchanged.
- **No epic restructuring needed.** Two course-correction stories added to Epic 9 sprint.

### Story Impact
- **9-1 (done):** Unaffected — completed before the API change.
- **9-2 (ready-for-dev):** Blocked until 9-1a completes. Cannot test risk management against live Kalshi data with a broken connector.
- **New stories:** 9-1a (Kalshi FP migration fix) and 9-1b (orderbook staleness alerting) inserted before 9-2.

### Artifact Conflicts
- **PRD:** No conflicts. Fix brings implementation closer to FR-DI-03 and NFR-I1 compliance.
- **Architecture:** No conflicts. Changes are internal to connector implementations. `IPlatformConnector` interface unchanged.
- **UI/UX:** No conflicts. Existing dashboard health indicators and Telegram alert infrastructure handle new events.

### Technical Impact
**Files affected by 9-1a (Kalshi FP migration):**
1. `connectors/kalshi/kalshi.connector.ts` — REST `getOrderBook()`: `response.data.orderbook` → `response.data.orderbook_fp`, field names `yes`/`no` → `yes_dollars`/`no_dollars`, types from `[number, number][]` to `[string, string][]`
2. `connectors/kalshi/kalshi-response.schema.ts` — Zod schemas: snapshot `yes`/`no` number tuples → `yes_dollars_fp`/`no_dollars_fp` string tuples; delta `price`/`delta` numbers → `price_dollars`/`delta_fp` strings
3. `connectors/kalshi/kalshi.types.ts` — TypeScript interfaces: `KalshiOrderbookSnapshotMsg`, `KalshiOrderbookDeltaMsg`, `LocalOrderbookState` field names and types
4. `connectors/kalshi/kalshi-websocket.client.ts` — WS client: snapshot handler, delta handler, `applyDelta()` method, `KalshiOrderBook` interface
5. `common/utils/kalshi-price.util.ts` — `normalizeKalshiLevels()`: remove `/100` cent-to-decimal conversion (prices now in dollars), accept string inputs
6. `common/utils/kalshi-price.util.spec.ts` — Tests updated for new input format

**Key conversion change:** Old format used integer cents (e.g., `42` = $0.42, required `/100`). New format uses dollar strings (e.g., `"0.4200"`, no division needed).

**Files affected by 9-1b (staleness alerting):**
- New event types in `common/events/`
- New Telegram message formatter
- Detection logic in `data-ingestion/` or `core/`
- Opportunity suppression guard in detection cycle

---

## Section 3: Recommended Approach

**Selected path:** Direct Adjustment — add two course-correction stories within current Epic 9 sprint.

**Rationale:**
- The connector fix is mechanical — mapping old field names/types to new ones with a known schema
- The staleness alert uses existing infrastructure (EventEmitter2 → Telegram alert service)
- No interface changes, no architectural changes, no epic restructuring
- Established precedent: stories 8-7, 8-8, 8-9 were added mid-epic during Epic 8 using the same pattern
- P0 priority — Kalshi connector is broken, blocking all live trading

**Effort estimate:** Low-Medium
**Risk level:** Low — changes confined to connector internals and monitoring fan-out
**Timeline impact:** 9-1a and 9-1b slot before 9-2; minimal delay to Epic 9 overall

---

## Section 4: Detailed Change Proposals

### 4.1: sprint-status.yaml — Add course-correction stories

Add to Epic 9 `development_status` section, between `9-1` (done) and `9-2` (ready-for-dev):
```yaml
9-1a-kalshi-fixed-point-api-migration: backlog
9-1b-orderbook-staleness-detection-alerting: backlog
```

Update summary statistics:
- Total Stories: 73 → 75
- Stories done: 67 → 68 (9-1 completed)
- Current: 9-1a (P0 hotfix)
- Next: 9-1b, then 9-2

### 4.2: epics.md — Add story definitions to Epic 9

Insert two new story blocks after Story 9.1, before Story 9.2:
- **Story 9.1a: Kalshi Fixed-Point API Migration** — Update connector REST/WS parsing, Zod schemas, TypeScript interfaces, and price normalization to match Kalshi's new `orderbook_fp` / `_dollars` / `_fp` response format.
- **Story 9.1b: Orderbook Staleness Detection & Alerting** — Detect when a platform's orderbook data goes stale (configurable threshold, default 90s), emit events, send Telegram alerts, suppress detection for stale platforms, send recovery notifications.

---

## Section 5: Implementation Handoff

**Change scope:** Minor — Direct implementation by development team.

**Execution order:**
1. **9-1a first** — Restore Kalshi trading capability (P0)
2. **9-1b second** — Close the observability gap (P1)
3. **Resume 9-2** — Continue Epic 9 planned work

**Handoff:** Development team via Create Story workflow for each story.

**Success criteria:**
- 9-1a: All existing Kalshi connector tests pass with updated response shapes; `getOrderBook()` returns valid `NormalizedOrderBook` from live Kalshi API; WebSocket orderbook updates parse and normalize correctly
- 9-1b: Telegram alert fires within 90s of orderbook data going stale; recovery notification fires when data resumes; stale-platform opportunities are suppressed in detection cycle
