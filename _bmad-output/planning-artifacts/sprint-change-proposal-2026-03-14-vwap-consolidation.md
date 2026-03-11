# Sprint Change Proposal — 2026-03-14: VWAP Dashboard Pricing, Calculation Consolidation, Staleness & UX

**Author:** Bob (Scrum Master)
**Date:** 2026-03-14
**Epic:** Epic 9 — Advanced Risk & Portfolio Management (Phase 1)
**Scope Classification:** Minor — Direct implementation by development team
**Proposed Stories:** `9-19`, `9-20`, `9-21`

---

## Section 1: Issue Summary

During paper trading validation of the Israel-Lebanon normalization contract (position `7574e8b2`), the operator dashboard displayed Take Profit proximity at 100% (PnL $14.81 vs TP threshold $12.94) while the engine's exit monitor did not trigger an automated exit.

**Root cause:** The dashboard's `PriceFeedService.getCurrentClosePrice()` returns top-of-book price without considering position size. The engine's `ExitMonitorService.getClosePrice()` correctly uses VWAP across order book depth for the full position size. For this 151.65-share position, the Kalshi bid side had only 1 share at best bid (0.14) — the realistic VWAP across 151.65 shares is ~0.116, producing a net PnL of ~$6-7, well below the $12.94 TP threshold.

**Underlying design issue:** Position P&L, close pricing, threshold evaluation, and exit proximity calculations are duplicated between `ThresholdEvaluatorService` (engine hot path) and `PositionEnrichmentService` (dashboard enrichment path), with divergent implementations. Story 9-18 began consolidation by extracting `computeTakeProfitThreshold()` into a shared function — this proposal extends that pattern to all position calculations.

**Secondary issues discovered during investigation:**
- Platform health indicators show "stale" approximately 70% of the time in the UI, despite Story 9-15's concurrent polling fix having shipped.
- Dashboard UX has general clarity gaps — no tooltips explaining calculations, no contextual help for the operator.

**Causal chain:** The engine did not exit because its VWAP-based PnL (~$6-7) was correctly below the $12.94 TP threshold. The dashboard's top-of-book PnL ($14.81) made it appear as though the engine failed to act — but the engine was right. The dashboard's pricing was wrong. This is a display accuracy bug, not an execution bug.

**Evidence:**
- DB query: Position `7574e8b2` (pair `af9e06fb`, is_paper=true) — entry Kalshi buy @ 0.150075, Polymarket sell @ 0.289565, size 151.65
- Order book snapshot (22:00 UTC): Kalshi bids = [0.14×1, 0.13×36, 0.12×17, 0.11×503, ...]; Polymarket asks = [0.17×46.37, 0.20×17, 0.21×20.13, 0.22×81.32, ...]
- Dashboard PnL (top-of-book): $14.81 — Engine PnL (VWAP): ~$6-7
- Zero automated exit events in audit_logs for this position — confirms the engine's VWAP-based evaluation never reached the TP threshold, consistent with the ~$6-7 PnL being below $12.94

---

## Section 2: Impact Analysis

### Epic Impact

**Epic 9 (in-progress):** 3 course correction stories added. No structural change. Epic 9 has already absorbed 14 course corrections (9-5 through 9-18) — this follows the established pattern.

**Epic 10 (backlog — Model-Driven Exits):** Positive indirect impact. The shared position calculation module from Story 9-19 provides a clean foundation for Epic 10's continuous edge recalculation (Story 10-1) and five-criteria exit logic (Story 10-2).

**All other epics:** No impact.

### Story Impact

| New Story | Priority | Scope |
|---|---|---|
| 9-19: VWAP-Aware Dashboard Pricing & Position Calculation Consolidation | P0 — Highest | T1 + T2 combined |
| 9-20: Platform Staleness Investigation & Remediation | P1 — High | T4 |
| 9-21: Dashboard UX Clarity Audit | P2 — Normal | T3 |

No existing stories are modified or removed.

### Artifact Conflicts

**PRD:** No conflicts. Fix aligns implementation with FR-EM-01 (threshold exits), FR-MA-04 (dashboard morning scan), NFR-P4 (dashboard update latency). PRD requirements are sound — the implementation diverged.

**Architecture:** No conflicts. Shared pure functions in `common/utils/` and `common/constants/` follow established module dependency rules. No forbidden imports created.

**UX Specification:** Minor update needed — add note that close prices reflect VWAP for actual position size, not top-of-book. Story 9-21 will produce additional UX spec amendments.

**Prisma Schema / API Contracts / Infrastructure:** No changes. `EnrichedPosition` DTO fields remain identical — values become more accurate.

### Technical Impact

**Operational note:** After Story 9-19 ships, WebSocket push events will reflect VWAP-aware values. Positions that appeared near TP will show lower proximity. A one-time Telegram notification should accompany deployment to prevent operator confusion.

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — Modify/add stories within Epic 9's existing structure.

### Rationale

The issues are implementation-level fixes, not architectural pivots. The codebase already has the correct pattern: shared pure functions in `common/`, established by Story 9-18's extraction of `computeTakeProfitThreshold()`. The bug fix and consolidation are the same work — extracting the shared module IS the fix.

### Alternatives Considered

| Option | Verdict | Why |
|---|---|---|
| **Direct Adjustment** | **Selected** | Low risk, medium effort, high long-term value. Proven pattern. |
| **Rollback** | Not viable | The bug predates 9-18. Rolling back 9-18 reintroduces the TP floor-to-zero bug. |
| **MVP Review** | Not applicable | MVP shipped in Epic 7. These are Phase 1 polish items. |

### Effort & Risk

| Story | Effort | Risk | Conditional |
|---|---|---|---|
| 9-19 | Medium | Low | — |
| 9-20 | Low-Medium | Low | Ceiling bumps to Medium if architectural issue found in health composite aggregation |
| 9-21 | Low | Low | — |

### Timeline Impact

None. These are additive course corrections within an epic that has 18 stories already done. No resequencing of other work.

---

## Section 4: Detailed Change Proposals

### Story 9-19: VWAP-Aware Dashboard Pricing & Position Calculation Consolidation

**Problem:** Dashboard shows misleading P&L and exit proximity because it uses top-of-book pricing. Engine uses VWAP. Calculation logic is duplicated across two services with divergent implementations.

**Approach:** Extract shared pure functions, wire both services to use them, fix the dashboard pricing bug as a natural consequence.

**Artifact changes:**

| File | Change | Type |
|---|---|---|
| `common/utils/financial-math.ts` | Add `calculateVwapClosePrice(orderBook, side, positionSize): Decimal \| null`. Returns `null` when the order book has zero depth on the relevant side (no bids for sell-to-close, no asks for buy-to-close). **Design decision for story author:** When enrichment receives `null`, recommended approach is to fall back to top-of-book with a depth-insufficient flag, so the dashboard can surface it visually (e.g., "estimated — thin book") rather than showing "N/A" or skipping enrichment entirely. | New function |
| `common/utils/financial-math.ts` | Add `calculatePositionPnl(side, entryPrice, closePrice, size): Decimal` | New function |
| `common/constants/exit-thresholds.ts` | Add `calculateExitProximity(currentPnl, baseline, threshold): Decimal` | New function |
| `common/interfaces/price-feed-service.interface.ts` | **Design decision for story author:** Add optional `positionSize` param to `getCurrentClosePrice()` OR add separate `getVwapClosePrice()` method. Separate method recommended — keeps top-of-book available for non-position contexts (match indicative pricing). |
| `modules/data-ingestion/price-feed.service.ts` | Implement VWAP-aware close price using shared `calculateVwapClosePrice()` | Modify |
| `dashboard/position-enrichment.service.ts` | Pass position size to close price method; delegate P&L and proximity to shared functions | Refactor |
| `modules/exit-management/exit-monitor.service.ts` | Delegate `getClosePrice()` body to shared `calculateVwapClosePrice()` | Refactor |
| `modules/exit-management/threshold-evaluator.service.ts` | Delegate `calculateLegPnl()` to shared `calculatePositionPnl()` | Refactor |
| All modified services | Update test mocks and assertions | Test updates |

**What NOT To Do:**
- Do NOT import `PriceFeedService` from `exit-management`. `ExitMonitorService` calls the pure function from `financial-math.ts` with the order book it already fetches from the connector. No cross-module dependency.
- Do NOT remove `ThresholdEvaluatorService.calculateLegPnl()` or `ExitMonitorService.getClosePrice()` as methods — they can delegate to the shared functions while retaining their method signatures for test stability.

**Operational requirement:** Ship with a one-time Telegram notification explaining that dashboard pricing is now VWAP-aware and exit proximity values will be more conservative (accurate).

---

### Story 9-20: Platform Staleness Investigation & Remediation

**Problem:** Platform health indicators show "stale" ~70% of the time in the UI despite Story 9-15's concurrent polling fix.

**Approach:** Investigation-first. Root cause determines fix scope.

**Investigation checklist:**
1. Verify whether 70% stale rate is from before or after Story 9-15 landed
2. Check staleness threshold configuration vs actual polling cycle time for current contract count
3. Investigate dashboard health composite — how per-contract staleness (9-15's model) aggregates into the platform-level health indicator displayed in the UI
4. Check WebSocket reconnection gap handling — do reconnection windows register as stale?
5. Review `PlatformHealthService` polling interval vs `STALENESS_THRESHOLD_MS` ratio

**Possible outcomes:**
- **Config tuning** (Low effort): Staleness threshold too aggressive for contract count → adjust threshold
- **Aggregation logic fix** (Medium effort): Dashboard health composite incorrectly aggregates per-contract staleness into platform-level indicator → fix aggregation
- **WebSocket gap handling** (Medium effort): Reconnection windows cause false staleness → add grace period

---

### Story 9-21: Dashboard UX Clarity Audit

**Problem:** Dashboard lacks explanatory context — no tooltips, no calculation explanations, no contextual help for the operator.

**Approach:** Systematic page-by-page review producing concrete recommendations.

**Scope:**
1. Review all dashboard pages: System Health, Positions (Open/All), Matches (Approved/Pending/Rejected), Match Detail, Stress Test, Settings
2. For each page: identify missing context, confusing labels, unexplained calculations, missing state explanations
3. Prioritize findings (P0: misleading without explanation, P1: unclear but not misleading, P2: nice-to-have polish)
4. Implement P0 and P1 items (tooltips, labels, information hierarchy)
5. Document P2 items for future sprints

**Deliverable format:** The audit phase produces a markdown document (`_bmad-output/implementation-artifacts/9-21-ux-audit-findings.md`) listing each finding in a structured table with columns: Page, Element, Current State, Recommended Change, Priority (P0/P1/P2). This document serves as both the implementation checklist and the artifact for Arbi's review before implementation begins.

**Note:** This story should execute AFTER 9-19 completes, so the audit covers accurate VWAP-aware data rather than the pre-fix state.

---

## Section 5: Implementation Handoff

**Scope classification:** Minor — Direct implementation by development team.

| Role | Responsibility |
|---|---|
| **Developer agent** | Implement 9-19, 9-20, 9-21 in sequence per TDD workflow |
| **Scrum Master** | Create story files via CS workflow, update sprint-status.yaml |
| **Operator (Arbi)** | Validate dashboard accuracy post-9-19, confirm staleness improvement post-9-20, review UX recommendations from 9-21 |

**Sequencing:**
1. **9-19** first (P0) — fixes the trust-breaking dashboard bug and establishes shared calculation module
2. **9-20** second (P1) — independent investigation, may be quick config fix
3. **9-21** third (P2) — depends on 9-19 completion for accurate audit baseline

**Dependency note:** 9-21 depends on 9-19 (audit should cover accurate VWAP-aware data). 9-20 has no dependency on 9-19 and could run in parallel if capacity allows — the sequential recommendation is about priority, not technical dependency.

**Success criteria:**
- 9-19: Dashboard PnL and exit proximity match engine's VWAP-based calculations within rounding tolerance. No duplicated P&L/pricing/proximity logic remains across services.
- 9-20: Platform staleness indicator shows stale <20% of the time under normal operating conditions (both platforms healthy). **Measurement methodology:** Measured over a 1-hour window with both platforms in healthy state, sampled from the dashboard's health composite WebSocket events. The developer agent should log staleness state transitions with timestamps to enable this verification.
- 9-21: All P0/P1 UX findings implemented. Operator can understand every number on the dashboard without referencing documentation.
