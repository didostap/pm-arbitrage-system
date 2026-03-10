# Sprint Change Proposal — Candidate Discovery Pipeline Filtering Fixes

**Date:** 2026-03-10
**Triggered by:** Operational issues discovered in Epic 8 candidate discovery pipeline (Story 8.4)
**Scope classification:** Minor — Direct implementation by development team
**Author:** Bob (Scrum Master), reviewed with Arbi

---

## Section 1: Issue Summary

### Problem Statement

The candidate discovery pipeline (Story 8.4) produces an excessive volume of false-positive candidate pairs, wasting LLM API calls and cluttering the match review interface. Of 693 total matches in the database, 688 (99.3%) are auto-rejected garbage — primarily caused by a data quality bug in the Kalshi date field mapping that silently drops settlement dates, combined with a permissive null-date bypass in the settlement window filter.

### Discovery Context

Issues identified during post-implementation operational use of the discovery pipeline. Three symptoms observed:

1. **Mismatched event pairing** — Completely unrelated events paired as candidates (e.g., "Jared Polis wins 2028 Democratic nomination" ↔ "Polish general election 2027")
2. **Text length inconsistency** — Polymarket descriptions avg 490 chars vs. Kalshi avg 180 chars (acknowledged, lower priority)
3. **Missing pagination** — Match review page shows only first 20 results with no navigation controls

### Evidence

| Metric | Value |
|--------|-------|
| Total matches in DB | 693 |
| Score = 0 (auto-rejected) | 653 (94.2%) |
| Score 1–39 (auto-rejected) | 35 (5.1%) |
| Score 40–84 (pending review) | 4 (0.6%) — **all legitimate** |
| Score ≥ 85 (auto-approved) | 0 (0%) |
| Worst offenders | 11 Kalshi contracts with null dates, 60+ matches each |
| LLM calls wasted on score-0 pairs | **653** |
| Distinct Polymarket contracts in matches | 142 |
| Distinct Kalshi contracts in matches | 36 |

### Root Cause Analysis

**Primary (B0):** The hand-written `KalshiMarketDetail` type declaration (added in Story 8.4) only declares `close_time?: string`, missing `expiration_time` (required in SDK) and `expected_expiration_time` (optional). The `mapToContractSummary` method reads `market.close_time`, which represents when **trading closes**, not when the market **settles/resolves**. For far-future Kalshi events (Polish elections, gubernatorial races), `close_time` is null while `expiration_time` is populated. Result: 11 Kalshi contracts ingested with null settlement dates.

**Secondary (B1):** `isWithinSettlementWindow()` returns `true` when either date is undefined (`if (!dateA || !dateB) return true`). This permissive default causes every dateless contract to match against the entire opposite-platform catalog. The 11 null-date Kalshi contracts generated ~660 of the 688 garbage matches.

**Tertiary (B2):** Pre-filter TF-IDF threshold at 0.15 is too low for political markets with shared vocabulary ("win", "election", "Democratic"). Defense-in-depth issue — less impactful once B0+B1 are fixed, but still needed for cases where both contracts have dates within the 7-day window but are semantically unrelated.

**Dashboard (C):** Backend `listMatches` already supports `page`/`limit` query params. Frontend `useDashboardMatches` hook doesn't pass them. `MatchesPage.tsx` has no pagination UI.

---

## Section 2: Impact Analysis

### Epic Impact

- **Epic 8 (current, in-progress):** No epic-level modification needed. Fixes are refinements to Story 8.4's implementation quality. New story 8.6 added within Epic 8.
- **Story 8.3 (Resolution Feedback Loop, backlog):** Benefits from B0 fix — accurate settlement dates from both platforms required for resolution comparison.
- **Epic 9 (Story 9.3):** Uses `confidenceScore` for position sizing. Not affected by pre-filter changes. Cross-epic note (divide by 100) already documented.
- **Epics 10–12:** No dependency on candidate discovery pipeline.

### Artifact Conflicts

- **PRD:** No conflict. Fixes improve quality of FR-CM-05, don't change requirements.
- **Architecture:** No structural changes. Module boundaries unchanged.
- **UI/UX:** Pagination is an implicit UX requirement at scale. Dashboard pagination follows existing patterns.

---

## Section 3: Recommended Approach

**Path: Direct Adjustment** — Modify existing code within Epic 8 scope + add dashboard pagination. One new story (8.6).

**Rationale:**
- No rollback needed (auto-reject safety net prevented any bad trades)
- No MVP scope change (MVP already complete)
- Low effort, low risk, high impact
- All changes are backward-compatible

**Effort:** Low (1 story, ~4-6 hours estimated)
**Risk:** Low (with before/after validation against existing 693 matches)
**Timeline impact:** None — fits within current Epic 8 sprint

---

## Section 4: Detailed Change Proposals

### B0 — Fix Kalshi Date Mapping at Source

**B0.1:** Add `expiration_time`, `expected_expiration_time`, `latest_expiration_time` to `KalshiMarketDetail` in `kalshi-sdk.d.ts`

**B0.2:** Update `mapToContractSummary` in `kalshi-catalog-provider.ts` to use fallback chain:
- `expected_expiration_time` → use it (best semantic match for settlement)
- `expiration_time` → use it (`expiration_time` is required per the Kalshi SDK — this is the expected normal path when `expected_expiration_time` is absent)
- `close_time` → use it **with structured warning log** (`kalshi.mapping.expiration-fallback` + market ticker). Reaching this path is an anomaly — it means the API response lacks both `expected_expiration_time` and `expiration_time`, contradicting the SDK contract.
- All three missing → `undefined` (caught by B1 downstream)

**AC language for dev agent:** "Given `expiration_time` is required per the Kalshi SDK, when a market response lacks both `expected_expiration_time` and `expiration_time`, then a structured warning is emitted with the market ticker so the anomaly is visible in operational logs."

**B0.3:** Tests: date field priority chain + warning emission on `close_time` fallback

### B1 — Settlement Window Null Defense-in-Depth

`isWithinSettlementWindow`: `if (!dateA || !dateB) return true` → `return false`

Tests: null source date, null candidate date, both null → all return `false`

### B2 — Pre-Filter Threshold Adjustment (Pending Validation)

Default threshold from `0.15` → value TBD after B0+B1 analysis. Starting hypothesis: `0.30`.

**Validation requirement:** Before/after analysis against existing 693 matches:
- Must preserve all 4 legitimate matches (scores 40–55)
- Must verify no legitimate candidate has pre-filter TF-IDF score in 0.15–0.30 range
- Let the data decide the final value

### C — Match Review Page Pagination

**C1:** `useDashboardMatches` hook: add `page`/`limit` params, include in query key, add `placeholderData: (prev) => prev` for flicker prevention

**C2:** `MatchesPage.tsx`: add `page` state, prev/next buttons, page indicator, reset to page 1 on filter change

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by development team. No backlog reorganization or architectural review needed.

### Implementation Order

1. **B0** — Kalshi date mapping fix (source-level fix)
2. **B1** — `isWithinSettlementWindow` null → false (defense-in-depth)
3. **Re-run candidate analysis** — Measure surviving candidates with proper dates
4. **B2** — Calibrate pre-filter threshold based on data
5. **B3** — Full test suite (null handling, date mapping, warning emission, threshold)
6. **C1+C2** — Dashboard pagination

### New Story

**Story 8.6: Candidate Discovery Filtering Fixes & Match Page Pagination**

To be created via the Create Story workflow after this proposal is approved.

### Files Modified (Expected)

**pm-arbitrage-engine/:**
- `src/connectors/kalshi/kalshi-sdk.d.ts` — Add date fields to `KalshiMarketDetail`
- `src/connectors/kalshi/kalshi-catalog-provider.ts` — Date fallback chain + warning log
- `src/connectors/kalshi/kalshi-catalog-provider.spec.ts` — Date mapping tests
- `src/modules/contract-matching/candidate-discovery.service.ts` — Null bypass fix + threshold
- `src/modules/contract-matching/candidate-discovery.service.spec.ts` — Null date tests + threshold

**pm-arbitrage-dashboard/:**
- `src/hooks/useDashboard.ts` — Pagination params
- `src/pages/MatchesPage.tsx` — Pagination UI + state

### Success Criteria

- [ ] All 4 legitimate matches (scores 40–55) survive the tighter filter
- [ ] ≥90% reduction in garbage LLM calls (from 653 → <65)
- [ ] Zero false negatives on real matches (before/after validation)
- [ ] Before/after candidate analysis documented in dev agent record with exact counts (permanent record of filtering improvement)
- [ ] Match review page navigable with prev/next at any scale
- [ ] Warning log emitted if `close_time` fallback is ever triggered (anomaly — `expiration_time` is required per SDK)
- [ ] All existing tests pass + new tests for date mapping and null handling

### Problem A Decision Criteria

Problem A (text length inconsistency between Polymarket ~490 chars and Kalshi ~180 chars) is **deferred**. Only pursue if the post-B0+B1+B2 analysis shows remaining garbage matches where description asymmetry is a contributing factor. If the numbers look clean after the filtering fixes, skip it entirely — don't gold-plate.

### The 4 Legitimate Matches (Must Preserve)

| Match | Poly | Kalshi | Score |
|-------|------|--------|-------|
| Trump crypto capital gains | "Trump eliminates capital gains tax on crypto in 2025?" | "Will Trump eliminate capital gains taxes on crypto? Before 2026" | 55 |
| Starmer out by April 30 | "Starmer out by April 30, 2026?" | "Keir Starmer Out? Before Jul 1, 2026" | 50 |
| Starmer out by March 31 | "Starmer out by March 31, 2026?" | "Keir Starmer Out? Before Jul 1, 2026" | 45 |
| Starmer out by June 30 | "Starmer out by June 30, 2026?" | "Keir Starmer Out? Before Jul 1, 2026" | 40 |
