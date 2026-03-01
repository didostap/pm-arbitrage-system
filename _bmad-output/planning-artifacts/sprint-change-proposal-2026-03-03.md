# Sprint Change Proposal — Telegram Notification Batching & Paper Mode Dedup

**Date:** 2026-03-03
**Triggered by:** Operational observation during Epic 6.5 paper trading validation
**Scope classification:** Minor — Direct implementation by dev team
**Status:** Approved

## Section 1: Issue Summary

### Problem Statement

Two related notification issues discovered during paper trading validation:

**Issue A — Paper mode duplicate notifications:**
`EdgeCalculatorService.processSingleDislocation()` emits `OPPORTUNITY_IDENTIFIED` on every profitable dislocation. In paper mode, simulated fills don't consume order book liquidity, so the same dislocation persists across detection cycles. Each cycle re-detects the same opportunity → fires `OPPORTUNITY_IDENTIFIED` → Telegram alert. Story 6-5-5c correctly blocks re-execution at the risk layer (`reserveBudget()` throws `BUDGET_RESERVATION_FAILED`), but the notification fires before that check. Result: operator receives the same "Opportunity Identified" Telegram message every ~5s cycle.

**Issue B — Same-type event batching:**
When a single detection cycle produces N opportunities (e.g., 3 pairs above threshold), the system fires N separate `OPPORTUNITY_IDENTIFIED` events, each triggering a separate `sendMessage()` call to Telegram. Due to Telegram rate limiting (429 responses) and the circuit breaker, only some actually deliver. Similar problem applies to any event type that fires multiple times per cycle.

### Discovery Context

Observed during Epic 6.5 paper trading validation runs. The Telegram channel becomes cluttered with repeated identical notifications, reducing operational signal-to-noise ratio.

### Evidence

- Code: `processSingleDislocation()` (edge-calculator.service.ts:220-240) emits per-opportunity with no cycle-level dedup
- Code: `EventConsumerService.handleEvent()` calls `telegramAlertService.sendEventAlert()` synchronously per event — no aggregation
- Code: `TelegramAlertService.enqueueAndSend()` calls `sendMessage()` immediately per call — no batching window
- User report: "only one message actually sent" — consistent with Telegram 429 rate limiting on rapid sequential sends

## Section 2: Impact Analysis

### Epic Impact

- **Epic 6.5 (Paper Trading Validation) — in-progress:** Adds one new story. No existing stories affected.
- **All other epics:** No impact.

### Story Impact

- **Story 6-5-5c (done):** No rollback needed. The risk-layer dedup guard is correct and stays. This proposal adds the missing notification-layer companion.
- **Story 6-5-5 (backlog):** Paper execution validation will benefit from cleaner Telegram output.

### Artifact Conflicts

- **PRD:** None — Telegram alerting already specified, batching/dedup is implementation improvement.
- **Architecture:** None — changes contained within monitoring module, event flow unchanged.
- **UI/UX:** N/A.

### Technical Impact

- **Files affected:** 2-3 files in `src/modules/monitoring/`
- **No schema changes, no new modules, no new dependencies**
- **Backward compatible:** critical events still sent immediately, existing circuit breaker/buffer untouched

## Section 3: Recommended Approach

**Selected path:** Direct Adjustment — new story in Epic 6.5

**Rationale:**
- Both issues are contained within the monitoring module
- Story 6-5-5c correctly fixed the execution path; this fixes the notification path
- Low effort (2-3 files), low risk (additive, non-breaking)
- No architectural changes required

**Effort estimate:** Low
**Risk level:** Low
**Timeline impact:** None — fits within current sprint

## Section 4: Detailed Change Proposals

### Change 1: Paper Mode Notification Dedup in EventConsumerService

**File:** `src/modules/monitoring/event-consumer.service.ts`

**What:** Add a `notifiedOpportunityPairs: Set<string>` that tracks which pair IDs have already had an `OPPORTUNITY_IDENTIFIED` Telegram notification sent. Before sending to Telegram:
- If paper mode AND pairId already in set → skip Telegram (still log + audit)
- If first notification for this pair → add to set, send Telegram
- Clear pair from set when position closes (`EXIT_TRIGGERED`, `SINGLE_LEG_RESOLVED`)

**Paper-mode gating:** `isPaperMode` derived from `ConfigService` (check `KALSHI_PAPER_MODE` / `POLYMARKET_PAPER_MODE` env vars). Guard is completely inert in live mode.

**Constraint honored:** Zero behavioral change in live mode.

### Change 2: Cycle-Scoped Telegram Message Batching in TelegramAlertService

**File:** `src/modules/monitoring/telegram-alert.service.ts`

**What:** Add a flush-window batching layer upstream of `enqueueAndSend()`. Instead of sending each message immediately:
1. Buffer messages by event name for a configurable window (`TELEGRAM_BATCH_WINDOW_MS`, default 3000ms)
2. When window expires: if 1 message → send as-is; if N messages → consolidate into single message with count header + individual summaries
3. **Critical events bypass batching** — sent immediately (zero delay for operator-critical alerts)

**Key config:** `TELEGRAM_BATCH_WINDOW_MS` (env var, default `3000`)

**Telegram limit compliance:** Consolidated messages truncated to fit Telegram's 4096 char limit.

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by development team. No backlog reorganization needed.

### Deliverable

One new story: **Story 6-5-5d: Telegram Notification Batching & Paper Mode Dedup**

Placed in Epic 6.5, sequenced after 6-5-5c (done) and before 6-5-5 (Paper Execution Validation, backlog).

### Files to Modify

| File | Change |
|------|--------|
| `src/modules/monitoring/event-consumer.service.ts` | Paper-mode notification dedup: `notifiedOpportunityPairs` Set, `isPaperMode` config check, skip Telegram for already-notified pairs, clear on position close |
| `src/modules/monitoring/telegram-alert.service.ts` | Batch window: `batchBuffer` Map, `addToBatch()`, `flushBatch()`, `consolidateMessages()`, critical event bypass |
| `src/modules/monitoring/event-consumer.service.spec.ts` | Tests for paper dedup: suppress repeat, allow after clear, live mode unaffected |
| `src/modules/monitoring/telegram-alert.service.spec.ts` | Tests for batching: single message passthrough, multi-message consolidation, critical bypass, window timing |

### Success Criteria

1. Paper mode: first `OPPORTUNITY_IDENTIFIED` for a pair sends Telegram; subsequent cycles for same pair do NOT send Telegram (until position closes)
2. Live mode: all `OPPORTUNITY_IDENTIFIED` events send Telegram as before (zero behavioral change)
3. Multiple same-type events within batch window → single consolidated Telegram message
4. Critical events always sent immediately (no batching delay)
5. All existing tests pass, new tests cover both features
6. `pnpm lint` reports zero errors

### Sprint Status Update

Add to `sprint-status.yaml`:
```yaml
6-5-5d-telegram-batching-paper-dedup: backlog
```
