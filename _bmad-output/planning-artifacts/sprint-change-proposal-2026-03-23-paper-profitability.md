# Sprint Change Proposal — Paper Trading Profitability & Execution Quality

**Date:** 2026-03-23
**Triggered by:** Comprehensive analysis of all 202 positions opened during paper trading (Mar 16–22, 2026)
**Scope Classification:** Major
**Approved:** Yes — 2026-03-23

---

## Section 1: Issue Summary

**Problem Statement:** The system has opened 202 paper trading positions over 6 days. Zero out of 198 closed positions achieved a positive recalculated edge at exit. Average expected edge at entry (+3.4%) consistently collapses to -17.5% at exit. The system is not profitable and cannot be moved to live trading in its current state.

**Discovery Context:** Full database analysis of `open_positions`, `orders`, and `audit_logs` tables on 2026-03-23. Analysis included position lifecycle, exit criteria triggers, order failures, single-leg exposure events, and pair concentration.

**Evidence:**

| Metric | Value |
|--------|-------|
| Total positions | 202 (all paper) |
| Closed with positive recalc edge | **0 / 198 (0%)** |
| Avg expected edge at entry | +3.39% |
| Avg recalculated edge at exit | -17.45% |
| Avg edge decay | -20.83% |
| Median hold time | 40 seconds |
| C5 (liquidity_deterioration) trigger rate | 93.4% of all exits |
| Order failures (Polymarket liquidity) | 605 (99.7% of all failures) |
| Single-leg exposure events | 235 |
| Pair concentration | 2 pairs = 92% of trades |
| `realized_pnl` column | NULL for all 198 closed positions (bug) |
| Shadow comparison audit logs | 979 events, all decision fields NULL (bug) |

**Root Cause Chain:**

1. **Detection sees phantom edges** — price gaps between platforms that aren't executable at target size due to thin Polymarket books
2. **Pre-trade gate is too permissive** — FR-EX-03/6-5-5b allows entry with 25% minimum fill threshold, but doesn't verify both legs simultaneously or account for VWAP slippage
3. **Positions enter against 1–6 contract deep books** with 47-contract target sizes
4. **Edge collapses immediately** — recalculated VWAP-based edge embeds the thin-book slippage
5. **C5 fires prematurely** — confirmed modeling tension: VWAP walks the full book but C5 depth only counts contracts at prices ≥ VWAP, systematically understating executable depth
6. **Exit fails on Polymarket** — Kalshi leg closes, Polymarket leg can't find liquidity, creating single-leg exposure
7. **No P&L tracking** — `realized_pnl` persistence (Story 10-0-2) is broken; all values NULL

---

## Section 2: Impact Analysis

### Epic Impact

- **Epic 10.5 (in-progress):** No modifications to existing stories. Remaining backlog stories (10-5-5 through 10-5-8) proceed as planned.
- **New Epic 10.7** created: "Paper Trading Profitability & Execution Quality Sprint"
  - Slots after Epic 10.5, before Epic 11
  - Must complete before live trading consideration
  - No dependency on 10-5-5 through 10-5-8 (can run in parallel if desired)
- **Epic 11 (backlog):** Not modified, but Epic 10.7 adds an additional hard gate before Epic 11
- **Epic 12 (backlog):** Not affected

### Story Impact

- No existing stories modified
- 9 new stories added in Epic 10.7 (see Section 4)
- **Capacity Budget:** 9 base stories. Applying 30-40% correction buffer → expect 12-13 total stories

### Artifact Conflicts

- **PRD:**
  - FR-EX-03 amendment needed: strengthen "minimum fill threshold" from 25% to require dual-leg depth verification at VWAP-estimated fill prices
  - FR-EX-03a amendment: expand gas-only re-validation to full VWAP slippage-aware edge re-validation
  - New FR-EX-09: per-pair position cooldown and concentration limits
  - Slippage risk section (existing): already identifies this risk, now being addressed
- **Architecture:**
  - §"Execution Position Sizing Model" update: dual-leg pre-flight depth verification before either leg is submitted
  - §"Exit Management" update: C5 depth metric slippage band
  - No structural changes — these are refinements to existing components
- **UX Design:**
  - No new pages required
  - Existing positions/dashboard views benefit from `realized_pnl` fix (already has display slots)

### Technical Impact

- **Modules touched:** `arbitrage-detection`, `execution`, `exit-management`, `monitoring`, `risk-management`
- **Prisma schema:** No migrations expected (columns already exist)
- **Config:** 3-5 new settings keys (slippage tolerance, cooldown interval, min dual-leg depth, dynamic edge floor, trading window hours) — all via existing EngineConfig DB pattern from Epic 10.5
- **Dashboard:** Minimal — `realized_pnl` display already wired, just needs non-null values

---

## Section 3: Recommended Approach

**Selected Path:** Option 1 — Direct Adjustment

**Rationale:**
- No rollback needed — all completed stories are correct in isolation; the issue is a systemic quality gap in the entry/exit pipeline
- PRD MVP remains valid — these are execution quality improvements, not scope changes
- The existing architecture supports all proposed changes (VWAP utilities, depth-aware sizing, configurable thresholds, event-driven monitoring)
- Stories 10-0-2 (realizedPnl) and 10-2 (five-criteria exits) established the wiring — fixes are targeted patches, not rewrites
- Proven change velocity: Epic 10 delivered 9 stories with 30-40% correction buffer; same pattern applies here

**Effort Estimate:** Medium-High (9 stories, mix of investigation/fix and new capability)
**Risk Level:** Medium — touches hot-path execution code; mitigated by comprehensive test coverage (2,594 tests) and paper mode validation
**Timeline Impact:** Adds one epic cycle before Epic 11. No impact on completed work.

**Alternatives Considered:**
- **Option 2 (Rollback):** Not viable — no completed work to revert; the issue is missing capability
- **Option 3 (MVP Review):** Not warranted — the PRD goals are correct; the implementation needs strengthening

---

## Section 4: Detailed Change Proposals

### New Epic 10.7: Paper Trading Profitability & Execution Quality Sprint

System enters positions only when both platforms can support the trade, calculates edge using realistic VWAP fill prices, monitors exits with accurate depth metrics, and tracks P&L for every closed position.

**FRs covered:** FR-EX-03 (strengthened), FR-EX-03a (expanded), FR-EX-09 (new), FR-EM-03 (C5 fix)
**Additional:** realized_pnl bug fix, shadow comparison fix, dynamic edge threshold, trading windows

**Prerequisite:** Epic 10.5 stories 10-5-4 (event wiring guards) should ideally complete first since it establishes the `expectEventHandled()` pattern used in new story tests.

---

#### Story 10-7-1: Pre-Trade Dual-Leg Liquidity Gate [P0]

As an operator,
I want the system to verify sufficient order book depth on **both** platforms before entering any position,
So that positions are only opened when both legs can realistically execute at target size.

**Context:** Current implementation (FR-EX-03 / Story 6-5-5b) checks depth per-leg sequentially — primary leg is submitted before secondary depth is verified. Position sizes of 47 contracts were entered against Polymarket books with 1-6 contracts of total depth. 99.7% of 605 order failures were Polymarket insufficient liquidity.

**Acceptance Criteria:**

**Given** an opportunity passes risk validation and is locked for execution
**When** the execution service prepares to submit orders
**Then** order book depth is fetched for BOTH platforms before EITHER leg is submitted
**And** the minimum total book depth across both legs is compared against the target position size
**And** if either leg has total depth < `DUAL_LEG_MIN_DEPTH_RATIO` × target size (configurable, default: 1.0), the opportunity is rejected
**And** rejection emits `execution.opportunity.filtered` with reason `"insufficient dual-leg depth"` and depth details per platform

**Given** both legs pass the dual-leg depth check
**When** depth is sufficient but asymmetric (e.g., Kalshi: 100, Polymarket: 15)
**Then** position size is capped to the minimum of both legs' available depth (constrained by existing `MIN_FILL_THRESHOLD_RATIO`)
**And** if the capped size falls below the minimum fill threshold, the opportunity is rejected

**Given** the dual-leg gate is in place
**When** a depth check API call fails on either platform
**Then** the opportunity is rejected (fail-closed)
**And** a `execution.depth-check.failed` event is emitted with error context

**Given** the pre-trade depth gate configuration
**When** the engine starts
**Then** `DUAL_LEG_MIN_DEPTH_RATIO` is loaded from EngineConfig DB (default: 1.0)
**And** the setting appears in the dashboard Settings page under "Execution" group

**PRD Impact:** FR-EX-03 amended — dual-leg verification before either leg is submitted.

---

#### Story 10-7-2: VWAP Slippage-Aware Opportunity Edge Calculation [P0]

As an operator,
I want the system to calculate expected edge using VWAP fill prices at target position size (not best-bid/ask),
So that the displayed edge accurately reflects what execution would actually achieve.

**Context:** Expected edge at entry averaged +3.4% but collapsed to -17.5% on recalculation. The detection pipeline uses best-level prices to compute edge, but execution fills across multiple levels at worse prices. The existing `calculateVwapClosePrice()` utility in `financial-math.ts` already walks the book — it should be reused at the detection stage.

**Acceptance Criteria:**

**Given** an opportunity is detected with a cross-platform price gap
**When** the edge calculator computes net edge
**Then** it uses `calculateVwapClosePrice()` to estimate fill prices for BOTH legs at the target position size
**And** the VWAP-estimated prices replace best-bid/ask in the edge formula
**And** the edge includes estimated fees and gas at the VWAP-estimated prices

**Given** order book depth is insufficient to VWAP-price the full target size
**When** the VWAP calculation returns a partial fill (less than position size available in book)
**Then** the edge is calculated at the partial fill VWAP
**And** if the partial fill is below minimum fill threshold, the opportunity is filtered before risk validation

**Given** a computed VWAP-based edge
**When** it falls below the minimum edge threshold (FR-AD-03)
**Then** the opportunity is filtered with reason `"VWAP-adjusted edge below threshold"`
**And** both the best-level edge and VWAP-adjusted edge are logged for comparison

**Given** the system operates with the new VWAP-based edge
**When** positions are entered and later recalculated
**Then** the gap between entry edge and recalculated edge narrows significantly compared to the historical -20.83% average decay

---

#### Story 10-7-3: C5 Exit Depth Slippage Band Correction [P0]

As an operator,
I want the C5 liquidity_deterioration criterion to count depth within a configurable slippage band around VWAP (not only at prices better than VWAP),
So that the depth metric doesn't systematically understate executable liquidity due to the VWAP circularity.

**Context:** Confirmed code-level modeling tension: `calculateVwapClosePrice()` walks the entire book, blending worse price levels into the average. `getAvailableExitDepth()` then uses that VWAP as a hard cutoff, excluding the very liquidity that produced it. C5 fired on 93.4% of exits. Typical detail: `"Min depth 1 vs required 5"` — only the best level passes the VWAP hurdle.

**Acceptance Criteria:**

**Given** a position is being evaluated for exit by the C5 criterion
**When** `getAvailableExitDepth()` computes available depth
**Then** the price cutoff is `closePrice × (1 + EXIT_DEPTH_SLIPPAGE_TOLERANCE)` for buy-close (asks)
**And** the price cutoff is `closePrice × (1 - EXIT_DEPTH_SLIPPAGE_TOLERANCE)` for sell-close (bids)
**And** `EXIT_DEPTH_SLIPPAGE_TOLERANCE` defaults to 0.02 (2%) and is configurable via EngineConfig DB

**Given** the slippage band is applied
**When** depth is computed
**Then** levels at prices within the tolerance band of VWAP are included in the depth count
**And** levels beyond the tolerance band are excluded (preserving the "executable at near-modeled price" intent)

**Given** the old behavior
**When** compared to the new behavior on historical data
**Then** the C5 trigger rate decreases from 93.4% to a level that reflects genuine liquidity problems rather than metric artifacts
**And** the exit detail message includes the tolerance used: `"Min depth {depth} vs required {minDepth} (tolerance: {pct}%)"`

**Given** the configuration
**When** the engine starts
**Then** `EXIT_DEPTH_SLIPPAGE_TOLERANCE` appears in the dashboard Settings page under "Exit Strategy" group
**And** a value of 0.0 restores the original strict-VWAP behavior (backward-compatible)

---

#### Story 10-7-4: Realized P&L Computation Investigation & Fix [P0]

As an operator,
I want `realized_pnl` accurately computed and persisted for every closed position,
So that I can evaluate the system's actual profitability.

**Context:** Story 10-0-2 (2026-03-16) claims `realizedPnl DB persistence (3 close paths)` was implemented. However, database analysis on 2026-03-23 shows `realized_pnl = NULL` for ALL 198 closed positions. This is a bug in the existing implementation, not a missing feature.

**Acceptance Criteria:**

**Given** the existing `realized_pnl` computation code (from Story 10-0-2)
**When** this story is investigated
**Then** the root cause of all-NULL values is documented (investigation-first pattern per Epic 9 retro)
**And** the investigation findings are recorded before any code changes

**Given** the root cause is identified
**When** the fix is applied
**Then** `realized_pnl` is populated for every position closed via: model-driven exit, shadow exit, manual close, auto-unwind, and close-all
**And** the formula is: `Σ (exit_proceeds - entry_cost - fees)` across both legs
**And** all financial calculations use `decimal.js` (domain rule)

**Given** positions are closed in paper mode
**When** paper fills are simulated
**Then** `realized_pnl` is still computed using the simulated fill prices
**And** paper and live positions are distinguishable in P&L reporting

**Given** the fix is deployed
**When** new positions are closed
**Then** `realized_pnl` is non-null for every closed position
**And** the dashboard position detail page displays the actual P&L value

---

#### Story 10-7-5: Exit Execution Chunking & Polymarket Liquidity Handling [P1]

As an operator,
I want exit orders to be split into smaller chunks matching available liquidity rather than attempting full-size exits against thin books,
So that single-leg exposure on exit is reduced.

**Context:** 235 single-leg exposure events during paper trading. Pattern: Kalshi exit leg fills, Polymarket leg fails with `"Partial exit — remainder contracts unexited"` (error code 2008). Polymarket CLOB books are structurally thinner than Kalshi for the same markets.

**Acceptance Criteria:**

**Given** an exit is triggered for a position
**When** the exit execution prepares orders
**Then** available depth on both platforms is checked before submitting exit orders
**And** if available depth on either platform is less than position size, the exit is chunked into multiple smaller orders matching available depth
**And** each chunk attempts both legs before proceeding to the next

**Given** a partial exit completes (some contracts exited, remainder still open)
**When** the next exit evaluation cycle runs
**Then** the position size reflects the remaining (unexited) contracts
**And** the exit monitor continues evaluating the residual position
**And** the position status remains `OPEN` until fully closed

**Given** a chunked exit attempt where one leg fills but the other fails
**When** single-leg exposure occurs at the chunk level
**Then** the exposure is limited to the chunk size (not the full position)
**And** existing auto-unwind logic (Story 10-3) handles the chunk-level exposure

**Given** configurable chunking
**When** the operator sets `EXIT_MAX_CHUNK_SIZE`
**Then** exit orders never exceed this size regardless of available depth
**And** default is unlimited (no chunking) to preserve backward compatibility until tuned

---

#### Story 10-7-6: Per-Pair Position Cooldown & Concentration Limits [P1]

As an operator,
I want per-pair position frequency limits and concentration caps,
So that the system doesn't repeatedly hammer the same thin order books.

**Context:** 2 pairs accounted for 92% of all 202 positions. The xAI/Text Arena pair alone had 116 positions (57%), with 162 single-leg exposure events. The system kept re-entering the same illiquid market.

**Acceptance Criteria:**

**Given** a position was recently opened for a specific pair
**When** a new opportunity is detected for the same pair within `PAIR_COOLDOWN_MINUTES` (configurable, default: 30)
**Then** the opportunity is filtered before risk validation
**And** an `OpportunityFilteredEvent` is emitted with reason `"pair cooldown active"`

**Given** a pair has `PAIR_MAX_CONCURRENT_POSITIONS` open positions (configurable, default: 2)
**When** a new opportunity is detected for the same pair
**Then** the opportunity is filtered before risk validation

**Given** position diversity requirements
**When** total open positions across all pairs exceeds `PAIR_DIVERSITY_THRESHOLD` (configurable, default: 5)
**Then** new positions are only allowed for pairs with fewer than the average positions-per-pair
**And** this prevents any single pair from dominating the portfolio

**Given** the per-pair settings
**When** the engine starts
**Then** all three settings are in EngineConfig DB and visible in the dashboard Settings page under "Risk Management" group

---

#### Story 10-7-7: Shadow Exit Comparison Event Payload Fix [P1]

As an operator,
I want the shadow exit comparison audit logs to contain actual decision data,
So that I can evaluate whether the shadow exit engine would make better decisions than the model.

**Context:** Story 10-2 implemented shadow mode comparison. 979 `execution.exit.shadow_comparison` audit log entries exist, but all have NULL for `shadowDecision`, `modelDecision`, and `agreement` fields. The event is emitted but the payload isn't populated.

**Acceptance Criteria:**

**Given** the shadow comparison service evaluates a position
**When** it emits the `execution.exit.shadow_comparison` event
**Then** the event payload includes: `shadowDecision` (hold/exit + criteria), `modelDecision` (hold/exit + triggered criteria), `agreement` (boolean), `positionId`, `pairId`, `currentEdge`
**And** no fields are null when the comparison completes

**Given** shadow and model disagree
**When** the comparison is logged
**Then** the divergence detail includes which criteria each mode triggered and the proximity values
**And** the `execution.exit.shadow_daily_summary` event aggregates agreement rate and divergence patterns

**Given** historical null entries
**When** this fix is deployed
**Then** new shadow comparison entries have fully populated payloads
**And** existing null entries are not backfilled (no retroactive fix needed)

---

#### Story 10-7-8: Dynamic Minimum Edge Threshold Based on Book Depth [P2]

As an operator,
I want the minimum edge threshold to scale dynamically based on order book depth,
So that the system demands higher edges for illiquid markets where slippage risk is greater.

**Context:** Current minimum edge is ~1.3% (FR-AD-03 specifies 0.8% default). Positions entering at 1.5-2% edge are almost guaranteed underwater after fees and slippage on thin books. The threshold should be higher when books are thin.

**Acceptance Criteria:**

**Given** an opportunity passes the base minimum edge threshold (0.8%)
**When** the effective edge threshold is calculated
**Then** it scales inversely with available depth: `effectiveMinEdge = baseMinEdge × (1 + DEPTH_EDGE_SCALING_FACTOR / min(kalshiDepth, polymarketDepth))`
**And** `DEPTH_EDGE_SCALING_FACTOR` is configurable (default: 5.0), producing higher thresholds for thinner books
**And** the effective threshold is capped at `MAX_DYNAMIC_EDGE_THRESHOLD` (default: 0.05, i.e., 5%)

**Given** a deeply liquid market (depth >> scaling factor)
**When** the dynamic threshold is calculated
**Then** it converges to the base minimum edge threshold (no penalty for liquid markets)

**Given** the configuration
**When** the engine starts
**Then** `DEPTH_EDGE_SCALING_FACTOR` and `MAX_DYNAMIC_EDGE_THRESHOLD` appear in Settings under "Detection" group
**And** setting `DEPTH_EDGE_SCALING_FACTOR` to 0 disables dynamic scaling (backward-compatible)

---

#### Story 10-7-9: Trading Window Analysis & Time-of-Day Filtering [P2]

As an operator,
I want the system to analyze and optionally restrict trading to hours with adequate market liquidity,
So that trades are only placed when books are deep enough to support them.

**Context:** 90% of positions opened between 15:00-21:00 UTC. Liquidity profiles may vary by time of day. This story has an investigation component (analyze data) and an implementation component (configurable trading windows).

**Acceptance Criteria:**

**Given** the existing position and order book data
**When** a time-of-day analysis is performed
**Then** the analysis documents: average book depth per hour (UTC), fill success rate per hour, single-leg exposure rate per hour, and edge decay correlation with time of day
**And** findings are recorded in an investigation document before implementation

**Given** the analysis identifies suboptimal trading hours
**When** trading windows are implemented
**Then** `TRADING_WINDOW_START_UTC` and `TRADING_WINDOW_END_UTC` are configurable (default: 0-24, i.e., no restriction)
**And** opportunities outside the trading window are filtered with reason `"outside trading window"`
**And** existing open positions continue to be monitored and exited regardless of window

**Given** the configuration
**When** the operator adjusts trading windows
**Then** changes take effect at the next detection cycle (no restart required)
**And** settings appear in the dashboard Settings page under "Detection" group

---

## Section 5: Implementation Handoff

### Change Scope: Major

This proposal adds a new epic with 9 stories touching 5 modules across the execution pipeline. The changes are implementation refinements (not architectural changes) but affect the hot path.

### Handoff Plan

| Role | Responsibility |
|------|---------------|
| **Scrum Master (Bob)** | Create stories in sprint-status.yaml, sequence stories, track completion |
| **Architect** | Review stories 10-7-1 (dual-leg gate), 10-7-2 (VWAP edge), 10-7-3 (C5 fix) for architectural alignment |
| **Developer** | Implement all 9 stories following TDD workflow |
| **QA/Test Architect** | Validate that P0 stories (10-7-1 through 10-7-4) measurably improve paper trading metrics |

### Sequencing

```
P0 (must complete before live trading):
  10-7-4 (realized_pnl fix) ─── can start immediately, investigation-first
  10-7-1 (dual-leg gate) ────── can start immediately
  10-7-2 (VWAP edge) ─────────── depends on 10-7-1 (shares depth-fetching pattern)
  10-7-3 (C5 depth fix) ──────── independent, can start immediately

P1 (high priority):
  10-7-5 (exit chunking) ─────── after 10-7-3 (uses corrected depth metric)
  10-7-6 (pair cooldown) ──────── independent, can start immediately
  10-7-7 (shadow payload fix) ── independent, can start immediately

P2 (medium priority):
  10-7-8 (dynamic edge) ──────── after 10-7-2 (builds on VWAP edge)
  10-7-9 (trading windows) ───── independent, investigation-first
```

### Success Criteria

After Epic 10.7 completion, a 7-day paper trading validation run should show:
1. **Recalculated edge decay < 5%** (vs. current -20.83%)
2. **C5 trigger rate < 30%** (vs. current 93.4%)
3. **Single-leg exposure events < 10% of positions** (vs. current ~116%)
4. **`realized_pnl` populated for 100% of closed positions** (vs. current 0%)
5. **Position concentration: no pair > 25% of total positions** (vs. current 57%)

---

## Appendix: Checklist Completion Record

### Section 1: Trigger & Context
- [x] 1.1 — Triggering event: Paper trading analysis of 202 positions (2026-03-23)
- [x] 1.2 — Core problem: Systemic unprofitability (0% success rate) due to thin-book phantom edges, C5 metric circularity, and missing P&L tracking
- [x] 1.3 — Evidence: Full database analysis with 10+ aggregate queries, code-level verification of VWAP/C5 tension

### Section 2: Epic Impact
- [x] 2.1 — Current epic (10.5): Not affected, proceeds as planned
- [x] 2.2 — New Epic 10.7 created with 9 stories
- [x] 2.3 — Future epics reviewed: Epic 11 gains an additional prerequisite (10.7)
- [x] 2.4 — No existing epics invalidated
- [x] 2.5 — Epic ordering: 10.5 → 10.7 → 11 → 12

### Section 3: Artifact Conflict
- [x] 3.1 — PRD: FR-EX-03 strengthened, FR-EX-03a expanded, FR-EX-09 added
- [x] 3.2 — Architecture: Execution sizing model and exit management sections updated
- [x] 3.3 — UX: No new pages needed
- [x] 3.4 — Secondary artifacts: EngineConfig schema (3-5 new settings keys), Settings page metadata

### Section 4: Path Forward
- [x] 4.1 — Direct Adjustment: Viable ✓ (Medium effort, Medium risk)
- [x] 4.2 — Rollback: Not viable (nothing to revert)
- [x] 4.3 — MVP Review: Not warranted (PRD goals correct)
- [x] 4.4 — Selected: Option 1 — Direct Adjustment

### Section 5: Sprint Change Proposal
- [x] 5.1 — Issue summary complete
- [x] 5.2 — Epic impact and artifact adjustment documented
- [x] 5.3 — Recommended path with rationale
- [x] 5.4 — PRD MVP impact: No scope change, strengthens existing requirements
- [x] 5.5 — Handoff plan defined

### Section 6: Final Review & Handoff
- [x] 6.1 — Checklist completion review
- [x] 6.2 — Proposal accuracy verified
- [x] 6.3 — User approval: **Yes — 2026-03-23**
- [x] 6.4 — sprint-status.yaml updated: Epic 10.7 added (9 stories, backlog), summary stats updated
- [x] 6.5 — epics.md updated: Epic 10.7 definition + 9 stories added, FR-EX-09 added to coverage map, Epic 11 prerequisites updated
