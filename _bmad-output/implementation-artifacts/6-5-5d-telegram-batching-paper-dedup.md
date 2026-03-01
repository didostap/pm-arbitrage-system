# Story 6.5.5d: Telegram Notification Batching & Paper Mode Dedup

Status: done

## Story

As an operator,
I want the monitoring layer to suppress duplicate Telegram notifications for already-notified opportunity pairs in paper mode and to batch same-type Telegram messages within a configurable window,
so that the Telegram channel maintains a high signal-to-noise ratio during paper trading validation instead of flooding with repeated identical alerts every ~5s cycle.

## Background / Root Cause

Two related notification issues discovered during paper trading validation:

**Issue A — Paper mode duplicate notifications:**
`EdgeCalculatorService.processSingleDislocation()` emits `OPPORTUNITY_IDENTIFIED` on every profitable dislocation. In paper mode, simulated fills don't consume order book liquidity, so the same dislocation persists across detection cycles. Each cycle re-detects the same opportunity → fires `OPPORTUNITY_IDENTIFIED` → Telegram alert. Story 6-5-5c correctly blocks re-execution at the risk layer (`reserveBudget()` throws `BUDGET_RESERVATION_FAILED`), but the notification fires _before_ that check — `EventConsumerService.handleEvent()` dispatches to Telegram on every event with no awareness of paper mode or prior notifications.

**Issue B — Same-type event batching:**
When a single detection cycle produces N opportunities (e.g., 3 pairs above threshold), the system fires N separate `OPPORTUNITY_IDENTIFIED` events, each triggering a separate `sendMessage()` call to Telegram. Due to Telegram rate limiting (429 responses) and the circuit breaker, only some actually deliver. Similar problem applies to any event type that fires multiple times per cycle.

**Why these are monitoring-layer problems:**

- Story 6-5-5c fixed the _execution path_ (risk layer blocks re-execution). This story fixes the _notification path_ (monitoring layer blocks repeat alerts).
- The execution layer is correct; only the observability fan-out is noisy.

## Acceptance Criteria

1. **Given** the engine is running in paper mode (either platform in paper mode)
   **When** an `OPPORTUNITY_IDENTIFIED` event fires for pair X and a Telegram notification was already sent for pair X in this session
   **Then** the event is still logged and audited as before
   **But** no Telegram notification is sent for that pair
   **And** the suppression is logged at debug level
   **And** the suppression is recorded in the audit trail via `AuditLogService`

2. **Given** the engine is running in paper mode
   **When** a position for pair X closes (`EXIT_TRIGGERED` or `SINGLE_LEG_RESOLVED` event received)
   **Then** pair X is removed from the notified set
   **And** subsequent `OPPORTUNITY_IDENTIFIED` events for pair X will send a Telegram notification again

3. **Given** the engine is running in live mode (both platforms live)
   **When** multiple `OPPORTUNITY_IDENTIFIED` events fire for the same pair
   **Then** all events send Telegram notifications as before (zero behavioral change in live mode)

4. **Given** multiple same-type events arrive within the batch window (`TELEGRAM_BATCH_WINDOW_MS`, default 3000ms)
   **When** the batch window expires
   **Then** a single consolidated Telegram message is sent with a count header and individual summaries
   **And** each summary is truncated to fit within Telegram's 4096 character limit

5. **Given** only one message for a given event type arrives within the batch window
   **When** the window expires
   **Then** the message is sent as-is (no consolidation wrapper, identical to current behavior)

6. **Given** a critical event (any event in `CRITICAL_EVENTS` set) is dispatched to `enqueueAndSend()`
   **When** the message reaches the batching layer
   **Then** the message is sent immediately (zero batching delay)
   **And** it does NOT flush or disrupt any pending batch windows for other event types

7. **Given** a batch window timer is active
   **When** the service is destroyed (`onModuleDestroy`)
   **Then** all pending batch windows are flushed immediately (no message loss on shutdown)

8. **Given** all existing tests pass before the change
   **When** the changes are implemented
   **Then** all existing 1,219+ passing tests continue to pass
   **And** new tests cover all acceptance criteria above
   **And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Add paper-mode notification dedup to `EventConsumerService` (AC: #1, #2, #3)
  - [x] 1.1 Inject `ConfigService` into `EventConsumerService` constructor (new dependency)
  - [x] 1.2 Add `private notifiedOpportunityPairs = new Set<string>()` class field
  - [x] 1.3 Add `private readonly isPaperMode: boolean` field, initialized in constructor from `ConfigService`
  - [x] 1.4 Add `private readonly MAX_NOTIFIED_PAIRS = 1000` constant with overflow clear
  - [x] 1.5 Add type-safe `extractPairIdFromEvent()` private helper method
  - [x] 1.6 Paper dedup guard in `handleEvent()` before Telegram delegation
  - [x] 1.7 Clear pair from notified set on EXIT_TRIGGERED / SINGLE_LEG_RESOLVED
  - [x] 1.8 10 paper dedup tests written and passing

- [x] Task 2: Add cycle-scoped message batching to `TelegramAlertService` (AC: #4, #5, #6, #7)
  - [x] 2.1 Add `private readonly batchWindowMs: number` field from ConfigService
  - [x] 2.2 Add `private batchBuffer` Map keyed by event name
  - [x] 2.3 Create `addToBatch()` — critical bypass, severity escalation
  - [x] 2.4 Create `flushBatch()` — single pass-through, multi consolidation
  - [x] 2.5 Create `consolidateMessages()` — header, truncation, 10-msg cap, HTML-safe
  - [x] 2.6 Modified `handleEvent()` to route through `addToBatch()` instead of `enqueueAndSend()`
  - [x] 2.7 Implemented `async onModuleDestroy()` with `Promise.allSettled()`
  - [x] 2.8 10 batching tests written and passing

- [x] Task 3: Update `MonitoringModule` if needed (AC: #1)
  - [x] 3.1 Verified `ConfigModule` already imported in `MonitoringModule` — no changes needed
  - [x] 3.2 No other module changes needed

- [x] Task 4: Verify no regressions (AC: #8)
  - [x] 4.1 `pnpm test` — 1,239 tests passing (1,219 existing + 20 new)
  - [x] 4.2 `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries:** All changes within `src/modules/monitoring/` — no forbidden imports introduced.
- **Event flow unchanged:** Events still flow through `EventEmitter2 → EventConsumerService → TelegramAlertService`. The dedup is a filter in `EventConsumerService`; the batching is a timing layer in `TelegramAlertService`.
- **Connectors untouched.** Detection untouched. Risk management untouched.
- **No new modules, no new files, no schema changes, no new dependencies.**
- **No financial math affected** — this is purely notification-layer logic.
- **Error hierarchy:** No new error types needed. `SystemHealthError` with `TELEGRAM_SEND_FAILED` already exists for Telegram failures.

### Key Design Decisions

1. **Paper dedup lives in `EventConsumerService`, NOT `TelegramAlertService`.** The dedup decision requires paper-mode awareness and event-type knowledge. `EventConsumerService` already classifies events by severity and decides which get Telegram treatment. Adding paper-mode gating here is natural. `TelegramAlertService` stays generic — it doesn't care about paper mode.

2. **`isPaperMode` is read once in constructor, not per-event.** Paper mode is a startup configuration — it cannot change at runtime without restarting the engine. Reading it once is correct and avoids per-event config lookups.

3. **`ConfigService` env vars:** `PLATFORM_MODE_KALSHI` and `PLATFORM_MODE_POLYMARKET` (not the old `KALSHI_PAPER_MODE`/`POLYMARKET_PAPER_MODE` which don't exist). These are the actual env vars used by `ConnectorModule.validatePlatformMode()`. Default is `'live'`.

4. **Batching lives in `TelegramAlertService`.** It's a generic message-timing concern that applies to all event types, not just opportunities. The service already manages buffers, circuit breaker, and retry logic — batching fits naturally here.

5. **Critical events bypass batching.** Operator-critical alerts (single-leg exposure, limit breached, trading halted, etc.) must have zero additional delay. The `CRITICAL_EVENTS` set from `EventConsumerService` determines severity, which is passed through to `addToBatch()`.

6. **Batch window is event-type-scoped.** Each event type gets its own batch window. This prevents unrelated events from being consolidated together. Example: 3 `OPPORTUNITY_IDENTIFIED` events batch together; a `PLATFORM_HEALTH_RECOVERED` event in the same window gets its own batch.

7. **`notifiedOpportunityPairs` cleared on position close events.** When `EXIT_TRIGGERED` or `SINGLE_LEG_RESOLVED` fires, the pair is removed from the notified set. This allows re-notification if the same opportunity appears again after the position closes. The pair ID is extracted from the event's `pairId` field (available on both event types).

8. **Type-safe `pairId` extraction via dedicated helper.** All event field access goes through `extractPairIdFromEvent()` which uses `typeof` validation instead of raw type casts. Returns `null` for missing, non-string, or malformed values — preventing silent failures if event shapes change in future refactors.

9. **Max size cap on `notifiedOpportunityPairs` (1000).** Prevents unbounded memory growth over long-running sessions. On overflow, the entire set is cleared with a warning log. This is conservative — clearing allows re-notification for all pairs, which is the safe default (a few duplicate notifications are better than a memory leak).

10. **Audit trail for suppressed notifications.** Suppressed duplicates are recorded via `AuditLogService.append()` with `eventType: 'monitoring.telegram.suppressed'`. This provides operator visibility into how many duplicates were suppressed during paper validation, which debug-level logs alone wouldn't provide in production.

11. **HTML-safe truncation in consolidated messages.** After slicing message text, any partial HTML tag at the end (e.g., `<b>tex`) is stripped via regex before appending the ellipsis. Prevents Telegram parse errors that would cause the entire consolidated message to fail sending.

12. **Async `onModuleDestroy()` with `Promise.allSettled()`.** Shutdown flush awaits all pending sends rather than fire-and-forget (`void`). This prevents silent message loss during graceful shutdown — especially important for warning-level batched alerts that may contain actionable information.

### File Structure — Exact Files to Modify

| File                                                    | Change                                                                                                                                                          |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/modules/monitoring/event-consumer.service.ts`      | Inject `ConfigService`, add `notifiedOpportunityPairs` Set, `isPaperMode` flag, paper dedup guard in `handleEvent()`, clear on exit events                      |
| `src/modules/monitoring/event-consumer.service.spec.ts` | New tests: paper dedup suppress repeat, allow after clear, live mode unaffected, pairId extraction                                                              |
| `src/modules/monitoring/telegram-alert.service.ts`      | Add `batchWindowMs` config, `batchBuffer` Map, `addToBatch()`, `flushBatch()`, `consolidateMessages()`, modify `sendEventAlert()` flow, add `onModuleDestroy()` |
| `src/modules/monitoring/telegram-alert.service.spec.ts` | New tests: single message passthrough, multi-message consolidation, critical bypass, window timing, shutdown flush                                              |

**No new files.** No schema changes. No new dependencies. No migration needed.

### Current `EventConsumerService` Constructor

```typescript
constructor(
    private readonly eventEmitter: EventEmitter2,
    private readonly telegramAlertService: TelegramAlertService,
    @Optional()
    @Inject(CsvTradeLogService)
    private readonly csvTradeLogService?: CsvTradeLogService,
    @Optional()
    @Inject(AuditLogService)
    private readonly auditLogService?: AuditLogService,
  ) {}
```

**After:** Add `ConfigService` as first parameter (before `eventEmitter`):

```typescript
constructor(
    private readonly configService: ConfigService,
    private readonly eventEmitter: EventEmitter2,
    private readonly telegramAlertService: TelegramAlertService,
    @Optional()
    @Inject(CsvTradeLogService)
    private readonly csvTradeLogService?: CsvTradeLogService,
    @Optional()
    @Inject(AuditLogService)
    private readonly auditLogService?: AuditLogService,
  ) {
    const kalshiMode = configService.get<string>('PLATFORM_MODE_KALSHI', 'live');
    const polymarketMode = configService.get<string>('PLATFORM_MODE_POLYMARKET', 'live');
    this.isPaperMode = kalshiMode === 'paper' || polymarketMode === 'paper';

    this.logger.log({
      message: `Paper mode notification dedup: ${this.isPaperMode ? 'ENABLED' : 'disabled'}`,
      module: 'monitoring',
      data: { kalshiMode, polymarketMode },
    });
  }
```

**Note:** `ConfigService` is provided by `ConfigModule` which `MonitoringModule` already imports (verified: `@Module({ imports: [ConfigModule, PersistenceModule], ... })`).

### Type-Safe `extractPairIdFromEvent()` Helper

Add this private method to `EventConsumerService`. Uses `typeof` validation instead of raw casts:

```typescript
private extractPairIdFromEvent(eventName: string, event: BaseEvent): string | null {
    const e = event as unknown as Record<string, unknown>;

    if (eventName === EVENT_NAMES.OPPORTUNITY_IDENTIFIED) {
        const opp = e['opportunity'];
        if (typeof opp === 'object' && opp !== null && 'pairId' in opp) {
            const pairId = (opp as Record<string, unknown>)['pairId'];
            return typeof pairId === 'string' ? pairId : null;
        }
        return null;
    }

    if (
        eventName === EVENT_NAMES.EXIT_TRIGGERED ||
        eventName === EVENT_NAMES.SINGLE_LEG_RESOLVED
    ) {
        const pairId = e['pairId'];
        return typeof pairId === 'string' ? pairId : null;
    }

    return null;
}
```

### Current `handleEvent()` — Paper Dedup Insertion Point

The dedup check goes BEFORE the existing `shouldSendTelegram` logic (around line 155):

```typescript
private readonly MAX_NOTIFIED_PAIRS = 1000;

// Paper mode notification dedup — prevent repeated Telegram for same pair
let shouldSendTelegram =
    severity === 'critical' ||
    severity === 'warning' ||
    TELEGRAM_ELIGIBLE_INFO_EVENTS.has(eventName);

if (shouldSendTelegram && this.isPaperMode) {
    if (eventName === EVENT_NAMES.OPPORTUNITY_IDENTIFIED) {
        const pairId = this.extractPairIdFromEvent(eventName, event);
        if (pairId && this.notifiedOpportunityPairs.has(pairId)) {
            shouldSendTelegram = false;
            this.logger.debug({
                message: 'Paper mode: suppressing duplicate Telegram for already-notified pair',
                module: 'monitoring',
                data: { pairId, eventName },
            });
            // Audit trail for suppressed notifications
            if (this.auditLogService) {
                void this.auditLogService
                    .append({
                        eventType: 'monitoring.telegram.suppressed',
                        module: 'monitoring',
                        correlationId: event?.correlationId,
                        details: { reason: 'paper_mode_dedup', pairId },
                    })
                    .catch(() => {});
            }
        } else if (pairId) {
            // Evict if set is at capacity (prevents unbounded memory growth)
            if (this.notifiedOpportunityPairs.size >= this.MAX_NOTIFIED_PAIRS) {
                this.notifiedOpportunityPairs.clear();
                this.logger.warn({
                    message: 'Notified pairs set overflow, cleared',
                    module: 'monitoring',
                    data: { maxSize: this.MAX_NOTIFIED_PAIRS },
                });
            }
            this.notifiedOpportunityPairs.add(pairId);
        }
    }
}

// Clear pair from notified set when position closes
if (
    this.isPaperMode &&
    (eventName === EVENT_NAMES.EXIT_TRIGGERED ||
        eventName === EVENT_NAMES.SINGLE_LEG_RESOLVED)
) {
    const pairId = this.extractPairIdFromEvent(eventName, event);
    if (pairId) {
        this.notifiedOpportunityPairs.delete(pairId);
    }
}
```

### Current `TelegramAlertService.sendEventAlert()` → `handleEvent()` Flow

Current flow:

1. `sendEventAlert(eventName, event)` formats the message
2. Calls private `handleEvent(eventName, formatFn, severity, correlationId)`
3. `handleEvent()` calls `formatFn()` then `enqueueAndSend(msg, severity)`

**New flow:**

1. `sendEventAlert(eventName, event)` formats the message — **unchanged**
2. Calls private `handleEvent(eventName, formatFn, severity, correlationId)` — **unchanged**
3. `handleEvent()` calls `formatFn()` then `addToBatch(eventName, msg, severity)` — **changed: routes through batching**
4. `addToBatch()` either sends immediately (critical) or buffers with timer
5. Timer expires → `flushBatch()` → `enqueueAndSend()` (single or consolidated)

### `addToBatch()` Implementation Sketch

```typescript
private addToBatch(eventName: string, text: string, severity: AlertSeverity): void {
    // Critical events bypass batching entirely
    if (severity === 'critical') {
        void this.enqueueAndSend(text, severity);
        return;
    }

    const existing = this.batchBuffer.get(eventName);
    if (existing) {
        existing.messages.push(text);
        // Escalate severity if needed
        if (SEVERITY_PRIORITY[severity] > SEVERITY_PRIORITY[existing.severity]) {
            existing.severity = severity;
        }
    } else {
        const timer = setTimeout(() => {
            this.flushBatch(eventName);
        }, this.batchWindowMs);
        this.batchBuffer.set(eventName, {
            messages: [text],
            timer,
            severity,
        });
    }
}
```

### `consolidateMessages()` Implementation Sketch

```typescript
private readonly MAX_MESSAGES_PER_BATCH = 10;

private consolidateMessages(eventName: string, messages: string[]): string {
    const MAX_TELEGRAM_LENGTH = 4096;
    const displayCount = Math.min(messages.length, this.MAX_MESSAGES_PER_BATCH);
    const overflow = messages.length - displayCount;
    const overflowNote = overflow > 0 ? `\n\n...and ${overflow} more` : '';

    const header = `📦 <b>${messages.length}x ${eventName}</b>\n`;
    let result = header;
    const maxPerMessage = Math.floor(
        (MAX_TELEGRAM_LENGTH - header.length - overflowNote.length) / displayCount,
    ) - 10; // 10 chars for separator/numbering

    for (let i = 0; i < displayCount; i++) {
        const truncated =
            messages[i].length > maxPerMessage
                ? this.truncateHtmlSafe(messages[i], maxPerMessage)
                : messages[i];
        result += `\n${i + 1}/${messages.length}:\n${truncated}`;
    }

    return (result + overflowNote).slice(0, MAX_TELEGRAM_LENGTH);
}

/**
 * Truncate text to maxLength, stripping any unclosed HTML tags
 * that result from the cut to prevent Telegram parse errors.
 */
private truncateHtmlSafe(text: string, maxLength: number): string {
    const sliced = text.slice(0, maxLength);
    // Strip any partial HTML tag at the end (e.g., "<b>tex" or "<co")
    const cleaned = sliced.replace(/<[^>]*$/, '');
    return cleaned + '…';
}
```

### `onModuleDestroy()` for Batch Flush

Uses `Promise.allSettled()` to await all pending sends, preventing silent message loss on shutdown:

```typescript
async onModuleDestroy(): Promise<void> {
    const flushPromises: Promise<void>[] = [];
    for (const [eventName, entry] of this.batchBuffer.entries()) {
        clearTimeout(entry.timer);
        this.batchBuffer.delete(eventName);
        if (entry.messages.length === 1) {
            flushPromises.push(this.enqueueAndSend(entry.messages[0], entry.severity));
        } else if (entry.messages.length > 1) {
            const consolidated = this.consolidateMessages(eventName, entry.messages);
            flushPromises.push(this.enqueueAndSend(consolidated, entry.severity));
        }
    }
    await Promise.allSettled(flushPromises);
}
```

### `SEVERITY_PRIORITY` Constant

`TelegramAlertService` already has this constant defined (line ~56-60):

```typescript
const SEVERITY_PRIORITY: Record<AlertSeverity, number> = {
  critical: 3,
  warning: 2,
  info: 1,
};
```

This can be reused for severity escalation in `addToBatch()`.

### `OpportunityIdentifiedEvent` Structure

The `opportunity` field is `Record<string, unknown>` containing:

```typescript
{
  netEdge: number,
  grossEdge: number,
  buyPlatformId: string,
  sellPlatformId: string,
  buyPrice: number,
  sellPrice: number,
  pairId: string,           // ← This is what we use for dedup
  positionSizeUsd: number,
  feeBreakdown: { ... },
  liquidityDepth: { ... },
  enrichedAt: Date,
}
```

`pairId` is set to `dislocation.pairConfig.eventDescription` in `EdgeCalculatorService.processSingleDislocation()` (line ~231).

### `EXIT_TRIGGERED` and `SINGLE_LEG_RESOLVED` Event Structure

Both carry `pairId` as a top-level field on the event object (confirmed from `buildTradeLogRecord()` at line 282: `pairId: this.str(e['pairId'])`).

### EventConsumerService Spec Test Setup

Current test setup mocks `TelegramAlertService` with `sendEventAlert`:

```typescript
mockTelegramService = {
  sendEventAlert: vi.fn().mockResolvedValue(undefined),
};
```

For paper dedup tests, also need to provide `ConfigService`:

```typescript
const mockConfigService = {
    get: vi.fn().mockImplementation((key: string, defaultValue: string) => {
        if (key === 'PLATFORM_MODE_KALSHI') return 'paper';
        if (key === 'PLATFORM_MODE_POLYMARKET') return 'live';
        return defaultValue;
    }),
};
// In providers:
{ provide: ConfigService, useValue: mockConfigService },
```

### TelegramAlertService Spec — Batch Timer Handling

Tests that involve `setTimeout` need Vitest fake timers:

```typescript
beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});
```

Use `vi.advanceTimersByTime(3000)` to trigger batch flush, and verify `sendMessage` call count and content.

### Testing Requirements

**EventConsumerService — Paper Dedup Tests:**

| Test                                                | Description                                                                                                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Paper dedup: suppresses repeat notification         | Paper mode, emit `OPPORTUNITY_IDENTIFIED` twice for same pairId → `sendEventAlert` called once                                                         |
| Paper dedup: allows different pairs                 | Paper mode, emit for pair X then pair Y → both send Telegram                                                                                           |
| Paper dedup: allows after EXIT_TRIGGERED clear      | Paper mode, emit for pair X, emit `EXIT_TRIGGERED` with pairId X, emit `OPPORTUNITY_IDENTIFIED` for X again → Telegram sent twice                      |
| Paper dedup: allows after SINGLE_LEG_RESOLVED clear | Same as above but with `SINGLE_LEG_RESOLVED`                                                                                                           |
| Paper dedup: live mode unaffected                   | Live mode, emit `OPPORTUNITY_IDENTIFIED` twice for same pairId → both send Telegram                                                                    |
| Paper dedup: handles missing pairId gracefully      | Paper mode, emit `OPPORTUNITY_IDENTIFIED` with no pairId → sends Telegram (no crash, no dedup)                                                         |
| Paper dedup: handles non-string pairId gracefully   | Paper mode, emit `OPPORTUNITY_IDENTIFIED` with `pairId: 123` (number) → sends Telegram (no crash, `extractPairIdFromEvent` returns null)               |
| Paper dedup: records suppression in audit trail     | Paper mode, suppress duplicate → `auditLogService.append()` called with `eventType: 'monitoring.telegram.suppressed'` and `reason: 'paper_mode_dedup'` |
| Paper dedup: logs paper mode status at startup      | Constructor runs → logger.log called with `'Paper mode notification dedup: ENABLED'` or `'disabled'`                                                   |
| Paper dedup: evicts on overflow                     | Paper mode, add 1000 pairs to set, add one more → set is cleared with warning log, new pair is added                                                   |

**TelegramAlertService — Batching Tests:**

| Test                                          | Description                                                                                              |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Batch: single message sent as-is              | One info-level message → after window expires → `sendMessage` called with original text (no wrapper)     |
| Batch: multiple messages consolidated         | 3 info-level messages for same event → after window → single `sendMessage` call with consolidated format |
| Batch: critical bypasses batching             | Critical message → `sendMessage` called immediately, no timer started                                    |
| Batch: different event types batch separately | 2 messages for event A + 1 for event B → 2 separate consolidated sends                                   |
| Batch: severity escalation                    | Info message + warning message in same batch → consolidated sent with warning severity                   |
| Batch: message truncation respects 4096 limit | 10 long messages → consolidated message is ≤ 4096 characters                                             |
| Batch: HTML-safe truncation                   | Message with `<b>long text</b>` truncated mid-tag → unclosed `<b>` stripped, no broken HTML sent         |
| Batch: max 10 messages per batch              | 15 messages → consolidated shows first 10 + "...and 5 more" note                                         |
| Batch: onModuleDestroy flushes and awaits     | Start batch, don't wait for timer, call destroy → messages sent, promise resolves after `allSettled`     |
| Batch: window timing                          | Send message, advance timer by 2999ms → no send; advance 1ms more → send                                 |

### Previous Story Intelligence (Story 6.5.5c)

- Story 6-5-5c added paper dedup at the **risk layer** (`paperActivePairIds` in `RiskManagerService`). This story adds the **notification layer** companion.
- `isPaper` flag flows through `ReservationRequest` and `BudgetReservation` types — this story doesn't need those types, it reads config directly.
- Test count after 6-5-5c: 1,219 passing.
- `PLATFORM_MODE_KALSHI`/`PLATFORM_MODE_POLYMARKET` are the correct env var names (confirmed from `ConnectorModule`).

### Git Intelligence

Recent engine commits:

```
8d6a8de Merge remote-tracking branch 'origin/main' into epic-7
711fa31 feat: enhance risk management by adding isPaper flag
4a8edf3 feat: introduce depth-aware reservation adjustment
612d195 feat: update detection service to use best bid for sell leg
6ba25e1 feat: add dashboard module with WebSocket support
```

**Relevant:**

- `711fa31`: Story 6-5-5c — paper dedup at risk layer. This story is the notification-layer companion.
- `6ba25e1`: Dashboard module — uses events but doesn't affect monitoring internals.

### Scope Guard

This story is strictly scoped to:

1. Paper-mode notification dedup in `EventConsumerService` (suppress repeat Telegram for same pair)
2. Cycle-scoped message batching in `TelegramAlertService` (consolidate same-type messages within window)
3. Critical event bypass (zero batching delay for operator-critical alerts)
4. Clean shutdown (flush pending batches on destroy)

Do NOT:

- Modify detection layer (detection stays purely about market data)
- Modify risk management (6-5-5c already handles execution dedup)
- Modify connectors
- Add database columns or tables
- Add new error types
- Modify the event catalog or create new events
- Change the format of existing Telegram messages (only add consolidation wrapper for batched groups)

### Project Structure Notes

- All changes within `pm-arbitrage-engine/src/modules/monitoring/` — no root repo changes
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- No new modules, no new files, no new dependencies

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03.md] — Sprint change proposal with full problem analysis and detailed change specs
- [Source: _bmad-output/implementation-artifacts/6-5-5c-paper-mode-duplicate-opportunity-prevention.md] — Previous story (risk-layer dedup companion)
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts, lines 121-204] — `handleEvent()` current implementation
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts, lines 84-93] — Constructor (needs ConfigService injection)
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts, lines 48-55] — `TELEGRAM_ELIGIBLE_INFO_EVENTS` set
- [Source: pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts, lines 268-322] — `enqueueAndSend()` current implementation
- [Source: pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts, lines 332-359] — `sendEventAlert()` current implementation
- [Source: pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts, lines 363-387] — Private `handleEvent()` method
- [Source: pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts, lines 167-182] — Constructor (config reading pattern)
- [Source: pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.ts, line 3] — `AlertSeverity` type definition
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts, lines 220-240] — `OpportunityIdentifiedEvent` emission with `pairId`
- [Source: pm-arbitrage-engine/src/connectors/connector.module.ts, lines 16-28] — `validatePlatformMode()` confirming env var names
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts] — `EVENT_NAMES` constant

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None required.

### Completion Notes List

- `sendEventAlert()` and `handleEvent()` in both `EventConsumerService` and `TelegramAlertService` changed from async to synchronous. Batching defers sends via `setTimeout`, so the methods no longer need to `await` anything. This is a minor interface change but all callers updated and tested.
- `ConfigService` injected as `@Optional()` in `EventConsumerService` to preserve backward compatibility with existing tests that don't provide it (defaults to live mode).
- Existing test assertions updated: `mockResolvedValue` → `vi.fn()` for mock, `await expect().resolves` → `expect().not.toThrow()`, `mockRejectedValueOnce` → `mockImplementationOnce(() => { throw })`.
- 20 new tests total: 10 for paper dedup, 10 for batching.

### File List

| File                                                                        | Change                                                                                                                                                                                                                 |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts`      | Added ConfigService injection, isPaperMode flag, notifiedOpportunityPairs Set, extractPairIdFromEvent helper, paper dedup logic in handleEvent(), pair clear on exit events. Changed handleEvent() from async to sync. |
| `pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.spec.ts` | Added ConfigService import, 10 paper dedup tests. Updated existing tests for sync handleEvent()/sendEventAlert().                                                                                                      |
| `pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts`      | Added OnModuleDestroy, batchWindowMs config, batchBuffer Map, addToBatch(), flushBatch(), consolidateMessages(), truncateHtmlSafe(), onModuleDestroy(). Changed sendEventAlert()/handleEvent() from async to sync.     |
| `pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.spec.ts` | Added 10 batching tests. Updated existing sendEventAlert dispatch tests with timer advancement for batched events.                                                                                                     |
