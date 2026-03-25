# Sprint Change Proposal: Backtesting & System Calibration

**Date:** 2026-03-25
**Triggered by:** Post-Epic 10.7 analysis — 0% paper trading profitability across 202 positions revealed unvalidated system parameters
**Scope:** Moderate — new epic (10.9) with PRD, architecture, and epic document updates
**Mode:** Incremental (each edit reviewed and approved individually)

---

## Section 1: Issue Summary

### Problem Statement

The PM Arbitrage System has no mechanism to validate trading parameters against historical market data. Paper trading showed systemic unprofitability (0% across 202 positions), and while Epic 10.7 addressed individual formula/logic bugs (9 stories), the underlying parameter calibration remains theoretical. Without backtesting against historical cross-platform price data, there is no empirical basis for: minimum edge thresholds, position sizing ratios, exit criteria weights, trading window selection, or expected opportunity frequency.

### Context

- **Discovery:** Post-Epic 10.7 (Paper Trading Profitability Sprint), March 2026
- **PRD history:** Backtesting was explicitly scoped out of the system (PRD line 338: "Backtesting (Outside System Scope)"). The product brief originally planned backtesting validation as Phase A (weeks 7-12) but the PRD descoped it pragmatically.
- **Evidence:** 202 paper trading positions with 0% profitability. Epic 10.7 fixed formula-level bugs but parameters remain unvalidated. The PRD's own success criteria require empirical validation: "Execution Quality Ratio: Realized edge ÷ expected edge at entry, Target: >0.7" and "Validates that actual execution matches backtested assumptions."

### Research Findings (Data Source Viability)

Three parallel research tracks confirmed viable data sources:

**Cross-platform matched pairs:**
- **OddsPipe** (oddspipe.com) — 2,500+ auto-matched Polymarket↔Kalshi pairs, OHLCV at 1m/5m/1h/1d, spread detection. Free tier: 100 req/min, 30 days history. Pro ($99/mo): full archive.
- **Predexon** (predexon.com) — 99%+ accuracy cross-platform matching, 5+ years historical data. Free tier: 1 req/sec, 1,000 req/month. Paid: $49/mo.

**Historical price/trade data:**
- Kalshi `/candlesticks` — full OHLC with bid/ask/volume/OI, 1-min granularity, no auth required
- Polymarket `/prices-history` — time/price pairs, 1-min fidelity, no auth required
- Kalshi `/historical/trades` — cursor-paginated, full history since 2021
- Polymarket Goldsky subgraph — complete on-chain trade history via GraphQL
- poly_data (GitHub, 647 stars) — pre-built Polymarket trade snapshot, saves 2+ days of collection

**Historical orderbook depth (critical gap resolved):**
- **PMXT Archive** (archive.pmxt.dev/Polymarket) — free hourly Polymarket L2 orderbook snapshots in Parquet format. Resolves the "no historical orderbook" limitation from both platforms.
- Own `OrderBookSnapshot` collection — 30s intervals, going forward

**Reference architecture:**
- prediction-market-backtesting (GitHub, 31 stars) — NautilusTrader-based framework with Kalshi + Polymarket adapters. Python/Rust (reference only, not adopted). Study strategy patterns and fill modeling.

**Parked:**
- FinFeedAPI (CoinAPI team) — enterprise-grade normalized data with order book snapshots. Enterprise pricing, overkill for solo operator. Future option if higher fidelity needed.

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| **10.8** (God Object Decomposition) | In-progress | **Not affected.** Pure refactoring. Completes independently. Creates extraction opportunity for shared math in `common/financial-math/`. |
| **10.9** (Backtesting & Calibration) | **NEW** | Added as new epic. 7 stories (4 P0, 2 P1, 1 retrospective). Slots between 10.8 and 11. |
| **11** (Platform Extensibility) | Backlog | **Sequencing changed.** Was next after 10.8. Now follows 10.9. Epic 10.9 added as hard gate. |
| **12** (Advanced Compliance) | Backlog | **Not affected.** Remains last in sequence. |

### Artifact Updates Required

| Artifact | Change Type | Status |
|----------|------------|--------|
| **PRD** (prd.md) | Scope update — backtesting moved from "Outside System Scope" to Phase 1 | Approved |
| **Epics** (epics.md) | New epic 10.9 with 7 stories inserted between 10.8 and 11 | Approved |
| **Sprint Status** (sprint-status.yaml) | New epic 10.9 entries, updated sequencing, corrected statistics | Approved |
| **Architecture** (architecture.md) | Module list, dependency graph, data flow — backtesting module added | Approved |

### Technical Impact

- **New NestJS module:** `src/modules/backtesting/` following existing module patterns
- **New Prisma models:** Historical data tables + `BacktestRun` (analogous to `CalibrationRun`/`StressTestRun`)
- **Shared math extraction:** Pure calculation functions (edge, VWAP, fees, sizing) extracted to `common/financial-math/` — consumed by both live pipeline and backtest engine. Eliminates calibration drift.
- **New dashboard page:** Backtest configuration, execution, and result visualization
- **External integrations:** OddsPipe API, Predexon API ($49/mo), PMXT Archive (Parquet), Goldsky subgraph (GraphQL)
- **No changes to live trading pipeline.** Backtesting is read-only, offline, and isolated.

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment (Option 1)

**Add Epic 10.9 within existing plan structure. No rollbacks, no scope reduction.**

**Rationale:**

1. **Clean insertion point.** Epic 10.8 is in-progress, 10.9 slots after it with zero dependency conflicts. Epics 11/12 are untouched backlog.
2. **Existing patterns reduce risk.** `CalibrationRun` persistence model, Monte Carlo simulation infrastructure, `IPlatformConnector` interface, `OrderBookSnapshot` model, Settings page, dashboard page patterns — all reusable.
3. **Data sources are viable.** Three independent research tracks confirmed: OddsPipe, PMXT Archive, Predexon, direct platform APIs. No showstoppers.
4. **Directly addresses root cause.** Backtesting provides the empirical foundation the PRD's success criteria demand.
5. **Low blast radius.** New module, new epic, no modification to existing production code paths.

**Effort:** Medium | **Risk:** Low | **Timeline:** +1 epic before Epic 11

### Scope Decision

**Calibration-focused (Scope A)** — NOT a full replay engine.

The module answers parameter calibration questions ("what minimum edge threshold maximizes profit factor over the last 6 months?") by analyzing historical price/depth data against parameterized detection + execution cost models. It does NOT replay through the live pipeline via a ReplayConnector (Scope B — deferred to Phase 2).

Key capabilities:
- Historical data ingestion from 5+ sources
- Cross-platform pair matching validation against OddsPipe + Predexon
- Parameterized backtest simulation with conservative fill assumptions
- Calibration reports with confidence intervals, sensitivity analysis (parameter sweep with profit factor/drawdown/Sharpe), and walk-forward out-of-sample validation
- Known limitations explicitly documented in every report

---

## Section 4: Detailed Change Proposals

### Edit Proposal #1: PRD Scope Update ✅ Approved

**Change 1a** — Line 338: Replace "Backtesting (Outside System Scope)" with "Backtesting & System Calibration [Phase 1]" including ingestion, calibration reports with confidence intervals and sensitivity analysis, and dashboard page.

**Change 1b** — Lines 333-336: Update "Out of scope" to retain only "Full historical replay engine (ReplayConnector through live pipeline)" as deferred.

### Edit Proposal #2: Epics — Add Epic 10.9 ✅ Approved (Revised)

7 stories inserted between Epic 10.8 and Epic 11:

| Story | Priority | Description |
|-------|----------|-------------|
| **10-9-1a** | P0 | Platform API Price & Trade Ingestion — Kalshi /candlesticks + /historical/trades, Polymarket /prices-history + Goldsky subgraph, poly_data bootstrap, common schema, PostgreSQL persistence, idempotency, rate limiting, data quality checks |
| **10-9-1b** | P0 | Depth Data & Third-Party Ingestion — PMXT Archive Parquet (hourly L2), OddsPipe OHLCV, coverage gap detection, freshness tracking |
| **10-9-2** | P0 | Cross-Platform Pair Matching Validation — Cross-ref our matches vs OddsPipe (2,500+ pairs) + Predexon (99%+ accuracy). Validation report: confirmed, our-only, external-only, conflicts |
| **10-9-3** | P0 | Backtest Simulation Engine Core — Parameterized replay: detection + VWAP sizing + fee-adjusted cost model + exit criteria. Conservative fills (taker-only, no market impact). Resolution-date force-close |
| **10-9-4** | P0 | Calibration Report with Sensitivity Analysis — Summary metrics, recommended params, bootstrap CIs, parameter sweep, degradation boundaries, walk-forward OOS validation (70/30 default), overfit detection (>30% degradation), known limitations section |
| **10-9-5** | P1 | Backtest Dashboard Page — Configure/trigger/review backtests, sensitivity charts, walk-forward mode, overfit warnings, run comparison |
| **10-9-6** | P1 | Historical Data Freshness & Incremental Updates — Daily cron, incremental fetch, stale data warnings, dashboard freshness indicators |

10-9-1 was split from a single story per Agreement #25 (sizing gate: ≤3 integration boundaries).

### Edit Proposal #3: Sprint Status YAML ✅ Approved (Revised)

- Epic 10.9 block added after 10.8, before 11
- Epic 11 hard gate comment updated to include 10.9
- Summary statistics corrected: 20 epics, 143 stories, 17 backlog
- Sequencing updated: 10.8 → 10.9 → 11 → 12

### Edit Proposal #4: Architecture Doc ✅ Approved (Revised)

**Change 4a** — Module list updated to include `backtesting/` (plus `exit-management/` and `contract-matching/` which were missing).

**Change 4b** — Dependency graph: `modules/backtesting/ → common/financial-math/ (shared with live pipeline), persistence/, common/types/`. Pure calculation functions (edge, VWAP, fees, sizing) extracted to `common/financial-math/` — both live pipeline and backtest engine import identical math. Eliminates calibration drift.

**Change 4c** — Data flow: New "CALIBRATION PATH" added as third data flow alongside ENTRY PATH and EXIT PATH. Entirely separate from live trading: reads from external data sources, writes to own persistence tables, produces reports for dashboard.

---

## Section 5: Implementation Handoff

### Change Scope Classification: Moderate

Requires backlog reorganization (new epic, sequencing change) and artifact updates across 4 documents.

### Handoff Plan

| Role | Responsibility |
|------|---------------|
| **Scrum Master (Bob)** | Apply all 4 edit proposals to project artifacts. Update sprint-status.yaml. |
| **Architect** | Review shared math extraction (`common/financial-math/`) during Epic 10.8 decomposition — identify functions to extract. Produce design sketch for backtesting module data model (Agreement #27). |
| **Dev Agent** | Implement Epic 10.9 stories following TDD cycle. Maintain adversarial data quality mindset per operator guidance. |
| **Operator (Arbi)** | Sign up for Predexon API ($49/mo). Verify OddsPipe free tier access. Review calibration reports and adjust parameters. |

### Implementation Notes (carry-forward for story authors)

1. **Sensitivity analysis ACs must be specific:** Parameter sweep across defined range with profit factor, max drawdown, and Sharpe ratio computed at each point. No vague "include sensitivity analysis" checkboxes.
2. **Adversarial data quality mindset:** Survivorship bias, timezone misalignment, PMXT coverage gaps, OddsPipe/Predexon matching errors as explicit risks addressed in implementation.
3. **Resolution-date force-close:** Story 10-9-3 engine must handle contract resolution as a distinct exit path — force-close at resolution price on resolution date, not continue evaluating exit criteria past resolution.
4. **Shared math, not reimplemented math:** `common/financial-math/` functions are shared between live pipeline and backtest engine. Same math, different data sources. Eliminates calibration drift.
5. **prediction-market-backtesting repo:** Reference only (Python/Rust, not adopted). Study strategy patterns and fill modeling approach.
6. **poly_data bootstrap:** First step in data ingestion story — pre-built snapshot saves days of initial Polymarket subgraph collection.

### Success Criteria

- All 4 P0 stories complete: historical data ingested, matching validated, simulation engine operational, calibration reports generated
- Calibration report answers: "what minimum edge threshold would have been profitable over the last 6 months?" with confidence intervals
- Walk-forward out-of-sample validation shows <30% degradation vs in-sample (no overfitting)
- Operator can adjust system parameters via existing Settings page based on calibration recommendations
- Parameters are empirically grounded before Epic 11's production hardening begins

---

## Approval Record

| Edit Proposal | Version | Decision | Date |
|--------------|---------|----------|------|
| #1: PRD Scope Update | v1 | Approved | 2026-03-25 |
| #2: Epics — Epic 10.9 | v2 (revised: 10-9-1 split, walk-forward validation, known limitations) | Approved | 2026-03-25 |
| #3: Sprint Status YAML | v2 (revised: backlog count corrected 16→17) | Approved | 2026-03-25 |
| #4: Architecture Doc | v2 (revised: shared math pattern replaces reimplementation) | Approved | 2026-03-25 |
