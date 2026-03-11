# Sprint Change Proposal — 2026-03-14

## Section 1: Issue Summary

**Problem Statement:** Five production defects discovered during live paper trading with 389 matched pairs and 2 open paper positions. The defects span data freshness, risk state persistence, display accuracy, and scalability. All surfaced organically — no single story triggered them; they are latent bugs in delivered features from Epics 2, 4, 5, 5.5, 6.5, and 9.

**Discovery Context:** Operator observed via dashboard: TP showing $0.00 on a profitable position, bankroll not reflecting deployed capital, stale/fresh flip-flopping on platform health, and a 28% APR match not being entered. Database investigation confirmed root causes across 5 modules.

**Evidence:**
- `risk_states` table: `open_position_count = 0`, `total_capital_deployed = 0` with 2 open paper positions
- `platform_health_logs`: repeated `last_update = 1970-01-01` entries (epoch zero)
- `contract_matches` row `6beafb32`: `last_net_edge = -0.14%` alongside `last_annualized_return = 28.1%` (contradictory)
- Dashboard screenshots: TP = +$0.00, bankroll static at $10,000, stale/fresh oscillation

---

## Section 2: Impact Analysis

### Epic Impact
- **Epic 9 (in-progress):** All 18 stories done. These 4 new stories are course corrections within Epic 9, following the established pattern (9-1a, 9-1b, 9-5, 9-6, etc.). No disruption to completed work.
- **Epics 10-12 (backlog):** No conflicts. Epic 10's continuous edge recalculation benefits from per-pair staleness. Epic 11's platform extensibility benefits from configurable per-platform concurrency and rate limiting patterns.
- **No epics invalidated, added, removed, or resequenced.**

### Story Impact
4 new course correction stories added to Epic 9:
- `9-15` — Platform health + concurrent polling + per-pair staleness
- `9-16` — Risk state paper trade reconciliation + parallel mode + sell-side capital
- `9-17` — Stale APR display fix
- `9-18` — Take-profit threshold formula fix

### Artifact Conflicts
- **Architecture doc:** Minor updates needed post-implementation:
  - Document concurrent polling as degraded-mode strategy
  - Document `initializing` health state
  - Document per-pair staleness model (meaningful shift from per-platform)
  - Document rate-limiting layer (concurrency + token bucket composition)
- **UX spec:** Add `initializing` health state to dashboard display
- **PRD:** No conflicts. Fixes align with NFR-R2 (degradation), NFR-R4 (health detection), NFR-P2 (detection cycle)

### Technical Impact
- **Schema migration:** `risk_states` gains `mode` column (`live` | `paper`), unique constraint on `(singleton_key, mode)`
- **New dependency:** `p-limit` for concurrency control (or custom 15-line implementation)
- **New shared utility:** `common/utils/capital.ts` — `calculateLegCapital()` function
- **No infrastructure, deployment, or CI/CD changes**

---

## Section 3: Recommended Approach

**Selected Path: Direct Adjustment** — Add 4 course correction stories within Epic 9.

**Rationale:**
- All defects have clear root causes with database evidence and surgical fixes
- No architectural changes needed — targeted bug fixes + one scalability improvement
- Follows the established course correction pattern within Epic 9 (14 prior course corrections)
- Effort: Medium-High (4 stories, each 4-10h)
- Risk: Low (well-scoped, root-caused, no cascading changes)
- Timeline: No impact on Epic 10+ sequencing

**Alternatives Considered:**
- Rollback: Not viable — bugs are in existing code, not recent features
- MVP Review: Not applicable — MVP complete since Epic 7

---

## Section 4: Detailed Change Proposals

### Story A: `9-15-platform-health-concurrent-polling`

**Title:** Platform Health Initialization Fix, Concurrent Polling & Per-Pair Staleness
**Priority:** 1 (resolves Issues 2 + 4 — most operationally disruptive)
**Effort:** High

**Changes:**

1. **Epoch Zero Health Bug** — `platform-health.service.ts:296-350`
   - Add early return for `lastUpdate === 0` before staleness check
   - Return `status: 'initializing'` with `lastHeartbeat: null`
   - Add debug log for boot timing traceability

2. **Add `initializing` to PlatformHealth status enum** — `platform.type.ts`
   - All consumers handle defensively: detection (skip, don't degrade), dashboard (show "Waiting for first data"), Telegram (don't alert), risk gating (not ready to trade)
   - Distinction: `initializing` = don't trade AND don't alert; `degraded` = don't trade AND do alert

3. **Concurrent Polling with Rate Limiting** — `data-ingestion.service.ts:147-191`
   - Wrap sequential Kalshi polling loop with `p-limit(concurrency)` + `Promise.allSettled`
   - Concurrency configurable per platform: `KALSHI_POLLING_CONCURRENCY`, `POLYMARKET_POLLING_CONCURRENCY`
   - Existing token-bucket rate limiter in connector (`acquireRead()`) handles throughput control — no additional rate limiter needed
   - Architecture: `p-limit (parallelism) → connector.getOrderBook() → rateLimiter.acquireRead() (throughput) → API call`
   - Rejected promises: log with contract ID, no retry in same cycle, contract ages out via per-pair staleness
   - Verify and wire in Polymarket batch `getOrderBooks()` in degraded fallback path
   - Startup warning if `pair_count / effective_read_rate > 60` (approaching staleness threshold)

   **Rate Limit Research (Kalshi):**
   | Tier | Read/s | Effective (×0.8) | 389 pairs | 2000 pairs |
   |------|--------|------------------|-----------|------------|
   | Basic | 20 | 16 | ~24s | ~125s |
   | Advanced | 30 | 24 | ~16s | ~83s |
   | Premier | 100 | 80 | ~5s | ~25s |

   **Rate Limit Research (Polymarket):**
   - GET /book (single): 150/s — but batch endpoint preferred
   - GET /books (batch): 50/s — single call for multiple token IDs

4. **Per-Pair Staleness Model** — `platform-health.service.ts` + `detection.service.ts`
   - New `lastContractUpdateTime: Map<string, number>` for per-contract tracking
   - New `recordContractUpdate(platform, contractId, latencyMs)` method
   - New `getContractStaleness(platform, contractId)` method
   - Detection service checks per-pair staleness instead of per-platform
   - Cleanup: periodic sweep or TTL-based eviction for delisted pairs
   - Comment explaining why `lastUpdate === 0` returns `stale: false` (startup grace)

5. **Architecture Doc Update** — `architecture.md`
   - Concurrent polling, `initializing` state, per-pair staleness model, rate-limiting composition

**Acceptance Criteria:**
1. No `1970-01-01` timestamps in `platform_health_logs` after restart
2. Dashboard shows "Initializing" (not "Degraded") during boot window
3. No false Telegram degradation alerts on startup
4. Full polling cycle for 389 contracts completes within 30s at current tier; `polling_cycle_duration_ms` metric logged per cycle
5. Concurrency configurable per platform via env vars
6. Polymarket batch `getOrderBooks()` confirmed/wired in degraded fallback path; if unavailable, documented and tracked
7. Detection evaluates per-pair staleness — stale contract X does not block fresh contract Y
8. `getContractStaleness()` returns `stale: false` for contracts with no data yet (startup grace)
9. Architecture doc updated
10. Rejected promises logged with contract ID; no retry in same cycle
11. Startup warning if pair_count / effective_read_rate > 60
12. All existing tests pass; new tests cover: initializing state, concurrent polling, per-pair staleness, rejected promise handling

---

### Story B: `9-16-risk-state-paper-trade-reconciliation`

**Title:** Risk State Paper Trade Reconciliation & Parallel Mode Capital Isolation
**Priority:** 2 (resolves Issue 5 — bankroll not updating)
**Effort:** High

**Changes:**

1. **Separate Risk States Per Mode** — Schema + `risk-manager.service.ts`
   - `risk_states` gains `mode` column (`live` | `paper`), `@@unique([singletonKey, mode])`
   - Risk manager maintains per-mode state: `state.live` and `state.paper`, each with own `openPositionCount`, `totalCapitalDeployed`, `dailyPnl`, `reservations`
   - Live bankroll: `bankrollUsd` (real); Paper bankroll: `PAPER_BANKROLL_USD` (configurable, defaults to same)
   - Capital isolation: live pool never reduced by paper positions
   - `reserveBudget()` checks correct mode's available capital
   - `persistState(mode)` and `onModuleInit()` restore both independently
   - Daily midnight reset applies to each mode independently

2. **Caller Audit for `findActivePositions()`** — All callers categorized:
   - Mode-specific (exit management, execution commit/release): use position's own `isPaper`
   - Cross-mode (reconciliation, dashboard totals): query both, label per-mode
   - Resource-gating (budget checks, correlation limits): check correct mode's state exclusively

3. **Sell-Side Capital Formula** — Extract to `common/utils/capital.ts`
   - `calculateLegCapital(side, fillPrice, fillSize)`: buy → `size × price`, sell → `size × (1 - price)`
   - Shared utility imported by reconciliation, execution, P&L enrichment, exit release
   - Test edge case: `fillPrice` near 1.0 (e.g., 0.99 → collateral = 0.01 × size)

4. **Consistent Capital Across All Paths** — Audit execution, risk commit, P&L enrichment, exit release
   - All paths use shared `calculateLegCapital` utility
   - No divergence between real-time and recovery capital calculations

5. **Reconciliation Per-Mode** — `startup-reconciliation.service.ts`
   - Loop over `[false, true]` for isPaper, reconcile each mode independently
   - No cross-contamination between paper and live state

6. **Dashboard Per-Mode Capital Overview** — `dashboard.service.ts` + frontend
   - API returns `{ live: { bankroll, deployed, available, reserved }, paper: { ... } }`
   - Frontend shows per-mode breakdown in Capital Overview

**Acceptance Criteria:**
1. `risk_states` table has two rows: `(default, live)` and `(default, paper)`
2. After restart with open paper positions, paper risk state shows correct counts and capital
3. After restart with open live positions, live risk state shows correct values independently
4. Live entry never blocked by paper capital — full isolation
5. Paper bankroll configurable via `PAPER_BANKROLL_USD`
6. Sell-side capital uses `size × (1 - fillPrice)` via shared `calculateLegCapital` in `common/utils/capital.ts`
7. Capital formula consistent across reconciliation, execution, P&L enrichment, exit release
8. All callers of `findActivePositions()` audited and categorized
9. Dashboard Capital Overview shows per-mode breakdown
10. Reconciliation after restart restores both modes independently — no cross-contamination
11. Daily P&L reset at midnight resets each mode independently
12. Tests: paper reconciliation, live reconciliation, mixed parallel, sell-side capital, fillPrice near 1.0

---

### Story C: `9-17-stale-apr-display-fix`

**Title:** Stale APR Display Fix — Atomic Edge/APR Updates on Filtered Events
**Priority:** 3 (resolves Issue 3 — misleading 28% APR display)
**Effort:** Low

**Changes:**

1. **Null out `lastAnnualizedReturn` when absent from filtered event** — `match-apr-updater.service.ts:57-90`
   - When `event.annualizedReturn` is null (edge filtered before APR computed), set `lastAnnualizedReturn = null`
   - When `event.annualizedReturn` is provided (APR computed but below threshold), update to computed value
   - Covers all filter reasons uniformly: negative edge, below threshold, liquidity, size constraints

2. **Audit all `OpportunityFilteredEvent` emission sites** — `edge-calculator.service.ts` + any other emitters
   - Verify which sites pass `annualizedReturn` and which don't
   - Confirm the null-out-when-absent approach handles all paths correctly
   - Key invariant: every filtered event without a fresh APR clears the stale value

3. **Dashboard null APR rendering** — Frontend verification
   - Match table APR column: shows "—" when null
   - Match detail Capital Efficiency section: shows "—" when null
   - No NaN or undefined rendering

**Acceptance Criteria:**
1. Negative net edge → `lastAnnualizedReturn` set to null in DB
2. Below-threshold positive edge (no APR computed) → `lastAnnualizedReturn` set to null
3. Below-threshold APR (APR computed but too low) → `lastAnnualizedReturn` updated to computed value
4. All `OpportunityFilteredEvent` emission sites audited and documented
5. Dashboard shows "—" for null APR (table + detail page)
6. No stale APR/net-edge contradiction possible
7. All existing tests pass; new tests cover null-out paths and frontend rendering

---

### Story D: `9-18-take-profit-threshold-formula-fix`

**Title:** Take-Profit Threshold Formula Fix — Edge-Relative TP When Baseline Exceeds Edge
**Priority:** 4 (resolves Issue 1 — TP = $0.00)
**Effort:** Low

**Changes:**

1. **Fix TP formula fallback** — `position-enrichment.service.ts:264-272`
   - Compute `journeyTp` using existing formula
   - If `journeyTp > 0`: use it (normal case, no behavior change)
   - If `journeyTp ≤ 0`: fallback to `max(0, scaledInitialEdge × TP_RATIO)`
   - Fallback expresses TP as 80% of expected edge profit, independent of MtM baseline
   - Verified safe: P&L at TP already accounts for exit fees (MtM basis); TP > 0 means net profit

   **Math verification (actual position):**
   - `thresholdBaseline = -$8.05` (spread $7.13 + exit fees $0.93, negated)
   - `scaledInitialEdge = $1.13` (edge 0.02536 × size 44.55)
   - Old: `max(0, -8.05 + (1.13 + 8.05) × 0.80)` = `max(0, -0.70)` = **$0.00** (bug)
   - New: `journeyTp = -0.70 ≤ 0` → fallback `max(0, 1.13 × 0.80)` = **$0.90** (correct)

2. **Verify TP proximity calculation** — lines 285-293
   - `tpDenom = 0.90 - (-8.05) = 8.95` — positive, no division issues
   - Proximity [0, 1] range preserved
   - `isZero()` guard still catches the edge case where `scaledInitialEdge ≤ 0`

3. **Update exit-thresholds.ts comment** — line 12
   - Document fallback behavior for high-fee/small-size positions

**Acceptance Criteria:**
1. TP never $0.00 when position has positive expected edge — fallback produces real profit target
2. Journey formula used when positive (no behavior change for existing positions)
3. Fallback activates only when `journeyTp ≤ 0`
4. TP never below $0 — `max(0, ...)` guard as final safety net
5. TP proximity in [0, 1] — no NaN, negative, or division by zero
6. SL formula and proximity unaffected
7. `exit-thresholds.ts` comment updated
8. Tests: normal journey, high-fee fallback (bug case), boundary (edge = |baseline|), very small edge, SL unchanged

---

## Section 5: Implementation Handoff

### Change Scope: **Moderate**

Stories A and B are medium-high effort with schema migration, risk manager refactor, and cross-module audit. Stories C and D are targeted low-effort fixes.

### Implementation Order
1. **Story A** (`9-15`) — Unblocks all detection and data freshness issues. Resolves the most operationally disruptive problem (stale data oscillation blocking 389 pairs).
2. **Story B** (`9-16`) — Fixes capital tracking and enables parallel paper/live. Requires schema migration.
3. **Story C** (`9-17`) — Quick fix once Story A stabilizes data freshness. Eliminates misleading APR display.
4. **Story D** (`9-18`) — Independent fix. Can be done in any order after Story A.

### Handoff
- **Development team:** All 4 stories — direct implementation via dev agent
- **Scrum Master (Bob):** Update sprint-status.yaml with new stories; create story files via CS workflow
- **Architecture doc:** Minor updates post-implementation (documented in Story A AC #9)

### Success Criteria
- All 389 pairs evaluate without false staleness flags
- Capital overview reflects actual deployed capital per mode after restart
- No contradictory APR/edge displays on any match
- No $0.00 TP on positions with positive expected edge
- All existing 2000+ tests pass; ~40-60 new tests added across 4 stories
