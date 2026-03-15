# Story 10.0.3: Exit Monitor Architecture Review

Status: done

## Story

As an operator,
I want the ThresholdEvaluatorService refactor sketched out before implementing the five-criteria model,
So that the implementation approach is validated before code is written.

## Acceptance Criteria

1. **Given** the current ThresholdEvaluatorService architecture **When** this spike is completed **Then** a design document exists covering how the five criteria compose (independent evaluation, priority ordering, or weighted). [Source: epics.md#Epic-10, Story 10-0-3 AC1]

2. **Given** the design document **When** shadow mode is addressed **Then** the document explains how shadow mode comparison works: both modes (fixed-threshold MVP and model-driven) evaluate every cycle, one executes, the diff is logged for daily comparison summaries. [Source: epics.md#Epic-10, Story 10.2 AC2-AC3]

3. **Given** WebSocket data path established in 10-0-1 **When** the design addresses data flow **Then** the document explains how WebSocket-authoritative pricing feeds into continuous recalculation (Story 10.1) and the five-criteria evaluator (Story 10.2), including polling fallback semantics. [Source: epics.md#Epic-10, Story 10-0-3 AC1; architecture.md#Data-Flow]

4. **Given** the five criteria from Story 10.2 **When** new data source requirements are analyzed **Then** the document identifies which criteria need new data sources: model confidence changes (criterion #2), liquidity snapshots (criterion #5), and how existing data sources serve edge evaporation (#1), time decay (#3), and risk budget breach (#4). [Source: epics.md#Epic-10, Story 10.2 AC1]

5. **Given** the ExitMonitorService integration **When** interface changes are specified **Then** the document defines the interface changes needed for ExitMonitorService to consume the refactored evaluator, including the new `ThresholdEvalResult` shape and any new input parameters. [Source: epics.md#Epic-10, Story 10-0-3 AC1]

6. **Given** this is a spike **When** scope is evaluated **Then** no production code is written — output is a design document only. Follows the investigation-first pattern (Team Agreement from retro). [Source: epics.md#Epic-10, Story 10-0-3 AC2]

## Tasks / Subtasks

- [x] Task 1: Analyze current ThresholdEvaluatorService architecture (AC: #1, #5)
  - [x] 1.1 Document current `ThresholdEvalInput` / `ThresholdEvalResult` interfaces and their consumers
  - [x] 1.2 Document current three-criteria evaluation flow (stop-loss → take-profit → time-based) with priority semantics
  - [x] 1.3 Document `ExitMonitorService.evaluatePosition()` integration: how it builds input, consumes result, and triggers `executeExit()`
  - [x] 1.4 Document shared constants in `common/constants/exit-thresholds.ts` (`SL_MULTIPLIER`, `TP_RATIO`, `computeTakeProfitThreshold`, `calculateExitProximity`)
  - [x] 1.5 Document dashboard consumption via `PositionEnrichmentService.enrich()` which uses exit proximity for display

- [x] Task 2: Design five-criteria composition model (AC: #1, #4)
  - [x] 2.1 Define the five criteria with their data source requirements:
    - Criterion 1 (Edge evaporation): currentPnl-based — **existing data** (prices from WS/polling, fees from connectors)
    - Criterion 2 (Model confidence drop): confidence score from `ContractMatch.confidenceScore` — **existing DB field**, but needs change detection (delta since entry or since last evaluation)
    - Criterion 3 (Time decay): configurable decay curve using `resolutionDate` — **existing data** (resolved in 10-0-2), needs decay curve function (new)
    - Criterion 4 (Risk budget breach): portfolio-level risk state + per-position remaining edge — **existing data** via `IRiskManager.getCurrentExposure(isPaper)`
    - Criterion 5 (Liquidity deterioration): order book depth at exit prices — **existing data** from WS/polling, needs minimum executable threshold config (new)
  - [x] 2.2 Decide composition strategy: recommend independent evaluation with priority ordering (consistent with current architecture) vs. weighted scoring
  - [x] 2.3 Define per-criterion proximity calculation (extending `calculateExitProximity` pattern) for dashboard display
  - [x] 2.4 Define per-criterion configurable thresholds (env vars or DB-persisted config)

- [x] Task 3: Design shadow mode comparison mechanism (AC: #2)
  - [x] 3.1 Define dual-evaluation flow: both fixed-threshold and model-driven evaluate every cycle
  - [x] 3.2 Define execution gate: config flag selects which mode's `triggered` result drives `executeExit()`
  - [x] 3.3 Define diff logging: per-cycle comparison record (which mode would trigger, at what P&L, which criterion)
  - [x] 3.4 Define daily summary aggregation: cumulative P&L comparison, trigger count by criterion, advantage/disadvantage tracking
  - [x] 3.5 Define dashboard integration: shadow mode comparison table on performance page, exit mode indicator per position

- [x] Task 4: Design WebSocket data path integration for continuous recalculation (AC: #3)
  - [x] 4.1 Document how `subscribeToContracts()` (from 10-0-1) feeds price/depth updates to exit monitor
  - [x] 4.2 Define recalculation trigger: on every WS price update vs. on polling cycle with WS data as source
  - [x] 4.3 Define polling fallback: when WS data is stale/unavailable, fall back to polling with staleness indicator
  - [x] 4.4 Define data source tracking: per-evaluation log of whether WS or polling data was used
  - [x] 4.5 Address dual data path divergence contract (Team Agreement #23): exit monitor uses WS-authoritative data, divergence > threshold emits alert

- [x] Task 5: Design interface changes for ExitMonitorService (AC: #5)
  - [x] 5.1 Define new `ThresholdEvalInput` extensions (confidence score, liquidity depth, risk state context)
  - [x] 5.2 Define new `ThresholdEvalResult` extensions (per-criterion proximity, triggered criterion identity, shadow mode diff payload)
  - [x] 5.3 Define whether evaluator becomes stateful (needs previous evaluation for delta tracking) or remains stateless (caller provides deltas)
  - [x] 5.4 Define `ExitMonitorService` changes: new data fetching responsibilities, result consumption, event emission for new criteria types
  - [x] 5.5 Define `ExitTriggeredEvent.exitType` union expansion to include new criteria types

- [x] Task 6: Write design document (AC: #1-6)
  - [x] 6.1 Create design document at `_bmad-output/implementation-artifacts/10-0-3-exit-monitor-design.md`
  - [x] 6.2 Include: current state analysis, proposed interface changes (TypeScript type signatures), composition strategy rationale, shadow mode mechanism, data flow diagrams, migration path from fixed to model-driven
  - [x] 6.3 Include: risk assessment (what could go wrong, backward compatibility, testing strategy sketch)
  - [x] 6.4 Include: story dependency map (how this design informs 10.1 and 10.2 implementation)

## Dev Notes

### Current Architecture (Verified Against Codebase 2026-03-16)

**ThresholdEvaluatorService** (`src/modules/exit-management/threshold-evaluator.service.ts`, 213 lines):
- Single `evaluate(params: ThresholdEvalInput): ThresholdEvalResult` method
- Three criteria evaluated in fixed priority order: stop-loss (P1) → take-profit (P2) → time-based (P3)
- First criterion that triggers wins — short-circuit evaluation
- Stateless: no inter-cycle state, all inputs provided per call
- Entry cost baseline (6.5.5i) offsets thresholds by natural MtM deficit at entry
- Shared constants in `common/constants/exit-thresholds.ts`: `SL_MULTIPLIER = -2`, `TP_RATIO = 0.8`
- `computeTakeProfitThreshold()` implements journey-based TP with edge-relative fallback (9-18)
- `calculateExitProximity()` provides unified 0-1 proximity for both SL and TP (used by dashboard)
[Source: threshold-evaluator.service.ts:1-213; exit-thresholds.ts:1-68]

**ExitMonitorService** (`src/modules/exit-management/exit-monitor.service.ts`, ~989 lines):
- `@Interval(30_000)` polling cycle via `evaluatePositions()`
- Fetches OPEN + EXIT_PARTIAL positions each cycle
- Per-position: validates connector health → validates fill data → calculates effective sizes → fetches close prices → calls `thresholdEvaluator.evaluate()` → if triggered, calls `executeExit()`
- `executeExit()` is criteria-agnostic: once triggered, execution flow is identical regardless of which criterion fired
- Circuit breaker: 3 consecutive full evaluation failures → skip next cycle
- Dependencies: `IPlatformConnector` (both platforms), `IRiskManager`, `PositionRepository`, `OrderRepository`, `EventEmitter2`, `ThresholdEvaluatorService`
[Source: exit-monitor.service.ts:62-142 (evaluatePositions), 144-353 (evaluatePosition), 355-835 (executeExit)]

**Dashboard Integration** (`src/dashboard/position-enrichment.service.ts`):
- `PositionEnrichmentService.enrich()` computes exit proximity for each open position using the same `calculateExitProximity()` utility
- Displays SL proximity, TP proximity, and time-to-resolution on position cards
[Source: position-enrichment.service.ts:50-313]

**Module Registration** (`src/modules/exit-management/exit-management.module.ts`):
- Imports: `ConnectorModule`, `RiskManagementModule`
- Providers: `ExitMonitorService`, `ThresholdEvaluatorService`, `PositionRepository`, `OrderRepository`
- Exports: `ExitMonitorService` only (ThresholdEvaluatorService is internal)
[Source: exit-management.module.ts]

### Five Criteria from Story 10.2 (Epics Definition)

| # | Criterion | Data Source | Status |
|---|-----------|-------------|--------|
| 1 | **Edge evaporation** — recalculated edge below breakeven after costs | Live prices (WS/polling) + fee schedules + gas | **Existing** — current stop-loss is a simplified version of this |
| 2 | **Model confidence drop** — confidence score decreased below threshold | `ContractMatch.confidenceScore` field | **Existing field** — needs delta tracking (entry-time snapshot vs current) |
| 3 | **Time decay** — expected value diminishes as resolution approaches | `ContractMatch.resolutionDate` (resolved in 10-0-2) | **Existing field** — current time-based is binary 48h; needs configurable decay curve |
| 4 | **Risk budget breach** — portfolio risk limit approached, this position has lowest remaining edge | `IRiskManager.getCurrentExposure(isPaper)` + per-position edge ranking | **Existing data** — needs cross-position comparison logic |
| 5 | **Liquidity deterioration** — order book depth below minimum executable threshold | Order book from WS/polling | **Existing data** — needs minimum depth threshold config |

[Source: epics.md#Epic-10, Story 10.2 AC1]

### Key Design Decisions the Spike MUST Resolve

The following are open questions that this spike exists to answer. The design document must contain explicit decisions (with rationale) for each:

1. **Composition strategy**: Current architecture uses priority-ordered short-circuit (first trigger wins). Five criteria could use:
   - Same pattern (priority ordering) — simplest, consistent
   - Independent evaluation with all-criteria proximity reporting + highest-priority trigger — richer dashboard data
   - Weighted scoring — most complex, may not be needed for V1

2. **Shadow mode architecture**: Story 10.2 AC2-AC3 require both fixed and model-driven to evaluate simultaneously, with a config toggle for which one executes. Key design question: does the evaluator return BOTH results, or does the caller invoke two separate evaluator instances? Must also address:
   - When both modes trigger simultaneously with different criteria, which takes precedence?
   - Shadow mode diff logging must be non-blocking (async) — specify storage mechanism and retention policy
   - Performance budget: dual evaluation must fit within the 30s polling cycle with margin

3. **Evaluator statefulness**: Current evaluator is stateless. Criterion #2 (confidence delta) requires comparing entry-time confidence to current. Criterion #5 (depth degradation) may need previous-cycle depth for trend detection. Decision: caller provides all deltas (evaluator stays stateless) vs. evaluator maintains per-position state (needs eviction policy). If stateless: define where entry-time confidence snapshot is stored (new DB column on `OpenPosition`? Captured at execution time?).

4. **`ThresholdEvalResult` evolution**: Current result has `type?: 'stop_loss' | 'take_profit' | 'time_based'`. Needs expansion for 5 criteria + shadow mode. Must carry:
   - Per-criterion proximity array for dashboard display (extending `calculateExitProximity` pattern)
   - Data source indicator (`'websocket' | 'polling' | 'stale_fallback'`) for observability
   - Shadow mode diff payload when applicable

5. **`ExitTriggeredEvent.exitType` expansion**: Current union: `'take_profit' | 'stop_loss' | 'time_based' | 'manual'`. Must define new discriminants — proposed: `'edge_evaporation' | 'model_confidence' | 'time_decay' | 'risk_budget' | 'liquidity_deterioration'`. Event consumers (monitoring, dashboard, Telegram) must handle new types. Note: existing `'stop_loss'` / `'take_profit'` become the fixed-threshold-mode equivalents; new names are for model-driven mode.
[Source: execution.events.ts:83-103]

6. **EXIT_PARTIAL position handling**: Current evaluator already handles EXIT_PARTIAL via residual-size recalculation in `ExitMonitorService.evaluatePosition()` (lines 195-263). The design must specify how each of the five criteria applies to residual positions — particularly criterion #4 (risk budget) which may rank a partially-exited position differently, and criterion #1 (edge evaporation) where the entry cost baseline needs recomputation for residual size.
[Source: exit-monitor.service.ts:195-263]

7. **Risk budget breach cross-position logic**: Criterion #4 requires comparing THIS position's remaining edge against ALL other open positions to determine if it has the lowest edge when a portfolio risk limit is approached. Current evaluator evaluates positions in isolation. Design must specify: does ExitMonitorService pre-compute a per-position edge ranking and pass it as input, or does the evaluator gain access to portfolio state?

8. **WebSocket vs polling trigger semantics**: Current exit monitor runs on `@Interval(30_000)`. With WS real-time data available (10-0-1), design must decide: keep polling as the evaluation trigger (using WS data as source when fresh), or switch to event-driven evaluation on WS updates. If event-driven: must define throttle/debounce to prevent exit churn from price jitter.

9. **Time decay curve shape**: Current time-based criterion is binary (48h threshold). Model-driven criterion #3 needs a configurable decay curve. Design must propose curve function (linear, exponential, configurable exponent) and parameters.
[Source: threshold-evaluator.service.ts:182-195]

### Dependencies and Constraints

- **Blocks**: Story 10.1 (continuous edge recalculation) and Story 10.2 (five-criteria model) depend on this spike's output
- **Depends on**: Story 10-0-1 (WebSocket subscriptions — DONE), Story 10-0-2 (tech debt fixes — DONE)
- **No production code**: This is a design document only. All code examples in the document are illustrative type signatures, not implementation.
- **Team Agreement (Epic 9 Retro)**: Investigation-first pattern — spike produces documented findings before implementation begins
[Source: epics.md#Epic-10, Story 10-0-3 AC2; sprint-status.yaml]

### Architecture Compliance

- **Module boundary**: Design must keep `ThresholdEvaluatorService` internal to exit-management module (not exported). Shared types/constants go in `common/constants/` or `common/types/` as needed.
- **Interface stability**: `IPlatformConnector` already has `subscribeToContracts()` and `getOrderBook()`. No interface changes expected for connectors.
- **Event-driven fan-out**: New exit criteria types must emit via `ExitTriggeredEvent` (existing event class, extended union). Monitoring/dashboard consume events — no new event classes needed.
- **Financial math**: All threshold calculations must use `decimal.js` — same pattern as current `computeTakeProfitThreshold()`.
- **Progressive sophistication**: Architecture doc explicitly states MVP fixed thresholds must be replaceable by Phase 1 model-driven exits without system redesign. Design must honor this.
[Source: architecture.md#Module-Communication; CLAUDE.md#Architecture]

### Previous Story Intelligence

**Story 10-0-2 (most recent, 2026-03-16):**
- `realizedPnl` persistence now works for all close paths — design can assume `realizedPnl` is available for P&L tracking
- `resolutionDate` write path closed for YAML pairs and approval endpoint — time decay criterion has functional input
- `SingleLegContext` refactor complete — clean interface for Story 10.3 dependency
- Baseline: 2253 tests, 121 files, lint/build clean
[Source: 10-0-2-carry-forward-debt-triage-critical-fixes.md, Completion Notes]

**Story 10-0-1 (2026-03-15):**
- `IPlatformConnector.subscribeToContracts()` established — WS data path is live
- Divergence monitoring active between poll and WS data paths
- Data path contract: polling authoritative for entry, WebSocket authoritative for exit
- 5 CRITICAL code review findings fixed (dead gateway handler, untested divergence wiring, false alerts from empty books, paper rehydration gap, missing pendingSubscription guard)
[Source: sprint-status.yaml, Story 10-0-1 completion notes]

**Tech debt triage (10-0-2-tech-debt-triage.md):**
- CF-4 (event payload enrichment for fee/gas data) deferred to Story 10.1 — design should account for this
- CF-12 (error severity defaults) deferred to Story 10.3 — relevant for autonomous exit decisions
- E9-8 (correlation tracker spec gap) — low priority, include if touching tracker
[Source: 10-0-2-tech-debt-triage.md]

### Project Structure Notes

**Design document output location:** `_bmad-output/implementation-artifacts/10-0-3-exit-monitor-design.md`

**Key source files to reference in design:**
| File | Purpose | Lines |
|------|---------|-------|
| `src/modules/exit-management/threshold-evaluator.service.ts` | Current evaluator — refactor target | 213 |
| `src/modules/exit-management/exit-monitor.service.ts` | Primary consumer of evaluator | ~989 |
| `src/common/constants/exit-thresholds.ts` | Shared constants + utilities | 68 |
| `src/dashboard/position-enrichment.service.ts` | Dashboard proximity consumer | 327 |
| `src/common/events/execution.events.ts` | ExitTriggeredEvent definition | 157 |
| `src/common/types/platform.type.ts` | PlatformId, OrderParams, FeeSchedule | — |
| `src/modules/risk-management/risk-manager.service.ts` | IRiskManager implementation | — |

**No new files created in engine repo** — this is a design-only spike.

### References

- [Source: epics.md#Epic-10] — Full Epic 10 definition including all stories 10-0-1 through 10.4
- [Source: epics.md#Epic-10, Story 10-0-3] — Spike AC: design document covering five-criteria composition, shadow mode, WS data path, new data sources, interface changes
- [Source: epics.md#Epic-10, Story 10.2] — Five criteria definition, shadow mode requirements, dashboard vertical slice
- [Source: epics.md#Epic-10, Story 10.1] — Continuous edge recalculation requirements, WS/polling fallback
- [Source: architecture.md#Data-Flow] — Dual data path contract: polling for entry, WS for exit
- [Source: architecture.md#Module-Communication] — Hybrid sync DI + async EventEmitter2 pattern
- [Source: architecture.md#Progressive-Sophistication] — MVP fixed thresholds → Phase 1 model-driven without redesign
- [Source: CLAUDE.md#Architecture] — Module dependency rules, forbidden imports, event naming
- [Source: threshold-evaluator.service.ts:12-44] — ThresholdEvalInput/ThresholdEvalResult interfaces
- [Source: threshold-evaluator.service.ts:50-203] — evaluate() method: three-criteria priority evaluation
- [Source: exit-thresholds.ts:1-68] — SL_MULTIPLIER, TP_RATIO, computeTakeProfitThreshold, calculateExitProximity
- [Source: exit-monitor.service.ts:62-142] — evaluatePositions() polling loop
- [Source: exit-monitor.service.ts:144-353] — evaluatePosition() per-position flow
- [Source: exit-monitor.service.ts:355-835] — executeExit() criteria-agnostic execution
- [Source: execution.events.ts:83-103] — ExitTriggeredEvent with exitType union
- [Source: position-enrichment.service.ts:50-313] — Dashboard exit proximity display
- [Source: 10-0-2-carry-forward-debt-triage-critical-fixes.md] — Previous story: realizedPnl, resolutionDate, SingleLegContext
- [Source: 10-0-2-tech-debt-triage.md] — Tech debt: CF-4 (event payload enrichment deferred to 10.1), CF-12 (error severity to 10.3)
- [Source: sprint-status.yaml] — Story 10-0-1 done (WS subscriptions), 10-0-2 done (debt fixes)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

N/A — design-only spike, no tests or builds.

### Completion Notes List

**Implementation approach:** Investigated all 7 source files via Serena symbolic tools (get_symbols_overview, find_symbol with include_body=true). Read full method bodies for ThresholdEvaluatorService.evaluate(), ExitMonitorService.evaluatePositions/evaluatePosition/executeExit/getClosePrice, PositionEnrichmentService.enrich(). Read IPlatformConnector, IRiskManager, RiskExposure interfaces. Read ContractMatch and OpenPosition Prisma models. Read Epic 10 stories from epics.md (10-0-1 through 10.4).

**Key design decisions made:**
1. **Composition: independent evaluation + priority-ordered trigger** — evaluates all 5 criteria every cycle for dashboard visibility, but trigger uses fixed priority (risk budget > edge evaporation > liquidity > confidence > time decay).
2. **Shadow mode: strategy pattern facade** — FixedThresholdEvaluator + ModelDrivenEvaluator behind IExitEvaluator interface, ThresholdEvaluatorService as facade. EXIT_MODE config: fixed/model/shadow.
3. **Evaluator stays stateless** — caller provides all inputs including entry confidence snapshot and pre-computed edge rankings. No per-position state in evaluator.
4. **WS data as source, polling as trigger** — keep @Interval(30_000) cadence, consume freshest available data (WS or poll). No event-driven evaluation.
5. **Liquidity: absolute threshold** — `1 - availableDepth / MIN_DEPTH` (no entry-time depth capture needed). Reviewed reviewer flagged `entryDepth` issue and chose simpler absolute formula.
6. **Time decay: quadratic curve** — continuous proximity replacing binary 48h. Triggers at ~18h (intentionally later than current 48h — other criteria handle urgent cases).
7. **Edge evaporation multiplier: -1.0** (breakeven) — intentionally tighter than current SL's -2.0. Documented the distinction.

**Lad MCP code review (2026-03-16):**
- Primary reviewer (kimi-k2.5): 2 CRITICAL (liquidity entryDepth gap, risk ranking field discrepancy), 4 MEDIUM (time decay defaults, stale penalty application, shadow payload volume, confidence div-by-zero), 4 MINOR
- Secondary reviewer (glm-5): 14 findings including edge evaporation semantics, div-by-zero guards, risk ranking formula clarity, time decay timing, dual-evaluator error handling
- **Fixed in design doc:** liquidity → absolute threshold formula, division-by-zero guards added to all proximity formulas, edge ranking field clarified (expectedEdge before 10.1, recalculated after), stale penalty application specified (caller applies to criterion #1 only), shadow log volume optimization (compact summary when modes agree), dual-evaluator error handling added, time decay timing documented as intentional, dense ranking for ties
- **Declined:** risk budget proximity formula inversion claim (reviewer misread — rank 1 → proximity 1 is correct), per-unit edge division (currentEdge is already per-contract)

**Dev Agent CR (2026-03-16):**
- 0 CRITICAL, 0 HIGH, 4 MEDIUM, 3 LOW
- All ACs validated as IMPLEMENTED against design doc content
- All 28 subtasks verified — no false [x] claims
- Git vs story File List: 0 discrepancies (engine repo clean, design doc staged)
- **Fixed:** M1 (added data-fetching overhead risk row to §10), M2 (corrected dense ranking pseudocode rank++ vs i+1), M3 (added §5.6 dashboard enrichment data flow — persist CriterionResult[] on OpenPosition), M4 (clarified shadow counterfactual P&L semantics in §3.4)
- **Fixed (LOW):** L1 (Appendix A ShadowComparisonPayload consistency with §3.3), L2 (sprint-status "Lad MCP code review" prefix), L3 (confidence guard description — div-by-zero protection not "marginal entry")

### File List

**Design document (new):**
- `_bmad-output/implementation-artifacts/10-0-3-exit-monitor-design.md`

**Source files analyzed (read-only, not modified):**
- `pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts`
- `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts`
- `pm-arbitrage-engine/src/modules/exit-management/exit-management.module.ts`
- `pm-arbitrage-engine/src/common/constants/exit-thresholds.ts`
- `pm-arbitrage-engine/src/common/events/execution.events.ts`
- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts`
- `pm-arbitrage-engine/src/common/interfaces/risk-manager.interface.ts`
- `pm-arbitrage-engine/src/common/interfaces/platform-connector.interface.ts`
- `pm-arbitrage-engine/src/common/types/risk.type.ts`
- `pm-arbitrage-engine/prisma/schema.prisma`
