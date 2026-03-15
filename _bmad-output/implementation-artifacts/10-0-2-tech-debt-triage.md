# Story 10-0-2: Tech Debt Triage — Full 28-Item Disposition

Generated: 2026-03-16
Source: Epic 9 Retrospective (2026-03-15) — 8 new items + 20 carry-forward

## Epic 9 New Items (8)

| # | Item | Disposition | Rationale |
|---|------|------------|-----------|
| E9-1 | WebSocket subscriptions never established | **CLOSED** | Resolved in Story 10-0-1. `subscribeToContracts()` added to `IPlatformConnector`, both connectors implement, divergence monitoring active. |
| E9-2 | Correlation tracker cache not mode-separated (paper/live) | **Carry forward** | Not blocking Epic 10. Mode separation only matters when paper mode exercises the risk validation pipeline's cluster exposure path, which it doesn't currently. Becomes relevant if Story 10.3 auto-management runs in paper mode. |
| E9-3 | Dashboard per-mode capital display (paper vs live) | **Carry forward** | Not blocking. Paper-only operation doesn't need visual separation. Revisit when live trading begins. |
| E9-4 | 4 P2 UX items from audit (sparklines, dynamic thresholds, drill-down) | **Carry forward** | Low-priority UX polish from Story 9-21 audit. Not blocking any feature. |
| E9-5 | `processOverride()` uses unadjusted base size | **Carry forward** | Overrides are operator-initiated safety valve with low frequency. Confidence adjustment on overrides is an enhancement, not a correctness fix. |
| E9-6 | Kalshi WS client staleness check parity with Polymarket | **Carry forward** | Low priority now that WS subscriptions work (10-0-1). Both connectors have staleness detection; parity is a completeness issue. |
| E9-7 | Per-pair staleness Telegram alerts | **Carry forward** | Platform-level alerts exist. Per-pair granularity is nice-to-have for debugging. |
| E9-8 | `correlation-tracker.service.spec.ts` not updated for `updateBankroll()` | **During Epic 10** | Low-effort test gap. Include in whichever story next touches the correlation tracker (likely 10.2 or 10.3). |

## Carry-Forward from Prior Epics (20)

| # | Item | Disposition | Rationale |
|---|------|------------|-----------|
| CF-1 | `handleSingleLeg` 17-param → `SingleLegContext` interface | **ADDRESS NOW** | Directly blocks Story 10.3 (Automatic Single-Leg Management). Epic AC explicitly requires this. |
| CF-2 | Event constructor parameter sprawl → options objects | **Carry forward** | No Epic 10 story depends on this. Events work correctly, just verbose constructors. Pattern change would touch 30+ event emission sites. |
| CF-3 | `realizedPnl` column on OpenPosition | **ADDRESS NOW** | Directly blocks Story 10.2 (Five-Criteria Model-Driven Exit Logic) criterion tracking. |
| CF-4 | Event payload enrichment (contractId, fees, gas on OrderFilledEvent) | **During Epic 10** | Relevant to Story 10.1 (continuous edge recalculation needs fee/gas data from events). Include in 10.1 story scope. |
| CF-5 | `resolutionDate` has no write path | **ADDRESS NOW (partial)** | Auto-discovered matches already populate from platform APIs (Epic 8 + 10-0-2b). Remaining gap: YAML pairs + dashboard update path. Blocks 10.2 time-decay criterion for YAML-configured pairs. |
| CF-6 | `entryPrices` stale after single-leg resolution | **Carry forward** | Edge case: entry prices could mismatch after retry resolves single-leg exposure. Low frequency, not blocking. |
| CF-7 | `force_close` in reconciliation doesn't capture real P&L | **Carry forward** | Emergency path. Normal close paths get `realizedPnl` in this story. Reconciliation force_close is a separate concern. |
| CF-8 | Error code catalog reconciliation — PRD vs codebase | **Carry forward** | Documentation debt. Error codes work correctly in practice. |
| CF-9 | Polymarket order book minor duplication | **Carry forward** | Performance not an issue at current scale. |
| CF-10 | `forwardRef` for ConnectorModule ↔ DataIngestionModule | **Carry forward** | Works correctly. `forwardRef` is the NestJS-recommended solution for circular deps. |
| CF-11 | PrismaService direct import in DashboardModule | **Carry forward** | Convention debt. Module works correctly via `PersistenceModule` exports. |
| CF-12 | Error severity defaults on error classes (code range mapping) | **During Epic 10** | Relevant to Story 10.3/10.4 autonomous actions where error severity drives automated decisions. Include in 10.3. |
| CF-13 | CI-generated Swagger client as tested contract | **Carry forward** | Process improvement. Manual regeneration works. |
| CF-14 | Fire-and-forget correlation ID propagation | **Carry forward** | Logging quality improvement. AsyncLocalStorage context works for synchronous chains. |
| CF-15 | `LLM_TIMEOUT_MS` not wired to SDK calls (AbortController) | **Carry forward** | LLM calls work with HTTP-layer timeout. AbortController is an enhancement. |
| CF-16 | Category alignment across platforms | **Carry forward** | Cluster classification handles mismatches via LLM fallback (Story 9-1). |
| CF-17 | No circuit breaker for persistent LLM API failures | **Carry forward** | Rate limiter + retry exist. Circuit breaker is an enhancement for when LLM call volume increases. |
| CF-18 | Polymarket `getContractResolution()` null conflated with API errors | **Carry forward** | Resolution poller works in practice. Null = unresolved is the common case. |
| CF-19 | Snapshot historical confidence at resolution time | **Carry forward** | Analytics enhancement. Current confidence scoring is live-only. |
| CF-20 | Wrap `getResolutionContext()` queries in transaction | **Carry forward** | Read-only queries. Consistency risk minimal. |

## Triage Summary

| Disposition | Count | Items |
|------------|-------|-------|
| **Address Now** | 3 | CF-1, CF-3, CF-5 (partial) |
| **During Epic 10** | 3 | CF-4 (in 10.1), CF-12 (in 10.3), E9-8 (next touch) |
| **Carry Forward** | 21 | E9-2 through E9-7, CF-2, CF-6 through CF-11, CF-13 through CF-20 |
| **Closed** | 1 | E9-1 (done in 10-0-1) |
| **Total** | 28 | |

## Newly Identified Debt (from 10-0-1, 10-0-2a, 10-0-2b — not part of original 28)

- `determineRejectionReason` not mode-aware (from 10-0-2a)
- `CorrelationTrackerService` getters not mode-parameterized (from 10-0-2a)
- Frontend `WsAlertNewPayload.type` missing 2 backend alert types (from 10-0-2a)

These are tracked for awareness but not triaged as part of this story's 28-item mandate.
