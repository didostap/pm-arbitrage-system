# Story 6.2: Event Consumer & Monitoring Hub

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want a centralized monitoring service that subscribes to all domain events and routes them to the right outputs,
So that I have a single, reliable system for observability across all modules.

## Acceptance Criteria

1. **Given** the `EventConsumerService` is initialized
   **When** it registers with EventEmitter2
   **Then** it subscribes to ALL domain event types in the event catalog (currently 27 events)
   **And** uses wildcard patterns (`execution.*`, `risk.*`, `detection.*`, `platform.*`, `system.*`, `degradation.*`, `orderbook.*`, `time.*`) for comprehensive coverage
   **And** any new events added to the catalog in future stories are automatically captured

2. **Given** an event is received by the EventConsumerService
   **When** the consumer routes it by severity
   **Then** Critical events → Telegram alert + structured log (level `error`) + metrics increment
   **And** Warning events → Telegram alert + structured log (level `warn`) + metrics increment
   **And** Info events → structured log (level `log`) + metrics increment
   **And** severity mapping is centralized and consistent with the existing `getEventSeverity()` mapping in `telegram-message.formatter.ts`

3. **Given** the `EventConsumerService` replaces direct `@OnEvent` subscriptions in `TelegramAlertService`
   **When** events flow through the system
   **Then** `TelegramAlertService` no longer has `@OnEvent` decorators — it receives events only via `EventConsumerService` calling its public API
   **And** `TelegramAlertService`'s existing formatting and circuit breaker logic is preserved unchanged
   **And** the behavior is functionally identical to the current direct-subscription model (all 14 Telegram-alerted events still produce the same alerts)

4. **Given** the global exception filter (`SystemErrorFilter`) is in place
   **When** an unhandled `SystemError` is caught by NestJS
   **Then** it is routed through the same severity-based pipeline as domain events
   **And** the error code, severity, and retry strategy are included in the structured log output
   **And** Critical severity errors emit a `SystemHealthCriticalEvent` for Telegram alerting
   **And** the HTTP response follows the standard error format: `{ error: { code, message, severity }, timestamp }`

5. **Given** the `EventConsumerService` is running
   **When** any event handler throws an error
   **Then** the error is caught and logged but NEVER propagates back to the event emitter
   **And** system operation continues uninterrupted
   **And** the failed event is logged with full context (event name, correlationId, error message)

6. All existing tests pass, `pnpm lint` reports zero errors
7. New unit tests cover: wildcard event routing, severity classification, Telegram delegation, exception filter behavior, metrics tracking, error isolation

## Tasks / Subtasks

- [x] Task 0: Spike — Validate EventEmitter2 wildcard behavior with NestJS @OnEvent (AC: #1) — MUST COMPLETE BEFORE Task 1
  - [x] 0.1 Create a minimal test in `event-consumer.service.spec.ts` that verifies whether `@OnEvent('**', { async: true })` passes the event name as the first argument to the handler. EventEmitter2 wildcard listeners receive `(eventName, value)` natively, but NestJS's `@OnEvent` decorator may strip the event name and only pass the payload.
  - [x] 0.2 Test approach: use `Test.createTestingModule` with `EventEmitterModule.forRoot({ wildcard: true, delimiter: '.' })`, create a test service with `@OnEvent('**')` that captures `...args`, emit a known event, verify `args[0]` is the event name string and `args[1]` is the payload.
  - [x] 0.3 **If event name IS available:** proceed with single `@OnEvent('**')` wildcard handler (Task 1.3 primary approach)
  - [x] 0.4 **If event name is NOT available:** use per-namespace explicit handlers instead: `@OnEvent('execution.**')`, `@OnEvent('risk.**')`, `@OnEvent('detection.**')`, `@OnEvent('platform.**')`, `@OnEvent('system.**')`, `@OnEvent('degradation.**')`, `@OnEvent('orderbook.**')`, `@OnEvent('time.**')` — each handler receives the event name from a hardcoded map or by using EventEmitter2's `this.event` property (verify availability). As a last resort, register handlers programmatically in `onModuleInit()` via direct EventEmitter2 API: `this.eventEmitter.onAny((eventName, event) => this.handleEvent(eventName, event))`

- [x] Task 1: Create `EventConsumerService` in `src/modules/monitoring/` (AC: #1, #2, #5)
  - [x] 1.1 Create `event-consumer.service.ts` with `@Injectable()` NestJS service
  - [x] 1.2 Inject `TelegramAlertService` (via constructor DI — same module, direct injection is fine) and `Logger`
  - [x] 1.3 Implement wildcard event subscriptions using `@OnEvent('**', { async: true })` — a single catch-all handler that receives ALL events. This is cleaner than maintaining 27+ individual handlers and automatically captures future events.
    - Alternative if `**` is unreliable: use specific wildcard patterns: `@OnEvent('execution.*', { async: true })`, `@OnEvent('risk.*', { async: true })`, `@OnEvent('detection.*', { async: true })`, `@OnEvent('platform.*', { async: true })`, `@OnEvent('system.*', { async: true })`, `@OnEvent('degradation.*', { async: true })`, `@OnEvent('orderbook.*', { async: true })`, `@OnEvent('time.*', { async: true })`
    - **IMPORTANT:** Verify EventEmitter2 wildcard behavior with `{ wildcard: true, delimiter: '.' }` config already in AppModule. The `**` glob should match all dot-separated event names.
  - [x] 1.4 Implement `handleEvent(eventName: string, event: BaseEvent): Promise<void>` — the central routing method:
    - Determine severity from event name using `classifyEventSeverity(eventName)` (see Task 1.5)
    - Increment in-memory metrics counters: `eventCounts[eventName]++`, `severityCounts[severity]++`
    - Route by severity + eligibility (hybrid approach):
      - **Critical:** structured log at `error` level + ALWAYS delegate to Telegram (any critical event, even without a formatter, sends a generic critical alert)
      - **Warning:** structured log at `warn` level + ALWAYS delegate to Telegram (same — generic alert for unformatted warning events)
      - **Info:** structured log at `log` level + delegate to Telegram ONLY if in `TELEGRAM_ELIGIBLE_INFO_EVENTS` set (the subset of info events that have formatters: ORDER_FILLED, EXIT_TRIGGERED, SINGLE_LEG_RESOLVED, OPPORTUNITY_IDENTIFIED, PLATFORM_HEALTH_RECOVERED, SYSTEM_TRADING_RESUMED)
    - This hybrid approach ensures new Critical/Warning events automatically get Telegram alerts without code changes, while Info events are opt-in to avoid flooding from high-frequency events like `orderbook.updated`
    - All structured logs include: `{ eventName, severity, correlationId, module: 'monitoring', data: <event payload summary> }`
    - Entire handler wrapped in try-catch — errors logged but NEVER re-thrown
  - [x] 1.5 Implement `classifyEventSeverity(eventName: string): AlertSeverity` — centralized severity mapping:
    - Extract and consolidate the severity mapping currently in `telegram-message.formatter.ts` (`getEventSeverity()`) into this service
    - Map ALL 27 events (not just the 14 Telegram-alerted ones):
      - Critical: `execution.single_leg.exposure`, `risk.limit.breached`, `system.trading.halted`, `system.health.critical`, `system.reconciliation.discrepancy`, `time.drift.halt`
      - Warning: `execution.order.failed`, `risk.limit.approached`, `platform.health.degraded`, `time.drift.critical`, `time.drift.warning`, `degradation.protocol.activated`
      - Info: everything else (`execution.order.filled`, `execution.exit.triggered`, `execution.single_leg.resolved`, `execution.single_leg.exposure_reminder`, `detection.opportunity.identified`, `detection.opportunity.filtered`, `platform.health.updated`, `platform.health.recovered`, `platform.health.disconnected`, `orderbook.updated`, `risk.override.applied`, `risk.override.denied`, `risk.budget.reserved`, `risk.budget.committed`, `risk.budget.released`, `degradation.protocol.deactivated`, `system.reconciliation.complete`, `system.trading.resumed`, `platform.gas.updated`)
    - Default: unknown events → `info` severity (safe default, never blocks)
  - [x] 1.6 Implement Telegram delegation — only for events that have formatters:
    - Maintain a `Set<string>` of Telegram-eligible event names (the 14 events currently handled by TelegramAlertService)
    - For eligible events: call `telegramAlertService.enqueueAndSend(formattedMessage, severity)` — reuse existing formatters from `telegram-message.formatter.ts`
    - For non-eligible events (e.g., `orderbook.updated`, `budget.reserved`): skip Telegram, only log
    - This preserves the exact current Telegram behavior while routing ALL events through a single hub
  - [x] 1.7 Implement `getMetrics(): EventConsumerMetrics` — expose in-memory counters for dashboard/health endpoints. **IMPORTANT: Return shallow copies** of `eventCounts` and `severityCounts` objects (`{ ...this.eventCounts }`) to prevent external mutation of internal state:
    ```typescript
    interface EventConsumerMetrics {
      totalEventsProcessed: number;
      eventCounts: Record<string, number>; // per event name (copy)
      severityCounts: Record<AlertSeverity, number>; // per severity (copy)
      lastEventTimestamp: Date | null;
      errorsCount: number; // handler errors caught
    }
    ```
  - [x] 1.8 Implement `resetMetrics(): void` — for testing and periodic reset (called via daily cron or on-demand)
  - [x] 1.9 Add `EVENT_CONSUMER_HANDLER_FAILED` error code (4007) to `monitoring-error-codes.ts`. Use `SystemHealthError(4007)` with `component: 'event-consumer'` when handler errors are caught.

- [x] Task 2: Refactor `TelegramAlertService` — remove `@OnEvent` decorators (AC: #3)
  - [x] 2.1 Remove all 14 `@OnEvent()` decorators from TelegramAlertService methods
  - [x] 2.2 Convert event handler methods to public methods callable by EventConsumerService:
    - Keep `handleEvent()` private helper as-is (already has try-catch + fallback)
    - Expose a single public method: `sendEventAlert(eventName: string, event: BaseEvent): Promise<void>` that dispatches to the appropriate formatter + enqueueAndSend based on event name
    - This replaces the 14 individual `@OnEvent` handlers with one dispatch method
  - [x] 2.3 Move the event-name-to-formatter mapping from individual methods into a registry `Map<string, (event: BaseEvent) => string>` for cleaner dispatch
  - [x] 2.4 Keep the daily test alert `@Cron` decorator — this is NOT event-driven and stays on TelegramAlertService
  - [x] 2.5 Keep `enqueueAndSend`, `sendMessage`, circuit breaker, buffer — all unchanged
  - [x] 2.6 Update `TelegramAlertService` imports: remove event class type imports that are no longer needed as direct handler parameters (they're accessed via BaseEvent now)
  - [x] 2.7 Export `TELEGRAM_ELIGIBLE_EVENTS` constant (the Set of 14 event names) so EventConsumerService can check eligibility

- [x] Task 3: Create global exception filter `SystemErrorFilter` (AC: #4)
  - [x] 3.1 Create `src/common/filters/system-error.filter.ts` implementing `ExceptionFilter`
  - [x] 3.2 Use `@Catch(SystemError)` decorator to catch all SystemError subclasses
  - [x] 3.3 Implement `catch(error: SystemError, host: ArgumentsHost)`:
    - **CRITICAL: Check context type first** — call `host.getType()` before accessing context. Only call `host.switchToHttp()` if type is `'http'`. For non-HTTP contexts (Cron jobs, WebSocket, microservices), skip HTTP response but still log + emit event. This prevents crashes when SystemErrors are thrown from `@Cron` handlers or WebSocket gateways.
    - For HTTP context: Map severity to HTTP status: critical → 500, error → 500, warning → 400
    - Build standard error response: `{ error: { code: error.code, message: error.message, severity: error.severity }, timestamp: new Date().toISOString() }`
    - Structured log with error details: code, severity, component (if SystemHealthError), retryStrategy, stack trace
    - For critical severity: emit `SystemHealthCriticalEvent` via EventEmitter2 → this triggers Telegram alert through EventConsumerService
    - **CIRCULAR LOOP PROTECTION:** Use a re-entrancy guard (`private emitting = false`) to prevent infinite loops. If the filter is already mid-emit when another SystemError arrives (e.g., Telegram fails → SystemHealthError → filter catches → tries to emit again), skip the event emission and only log. This breaks the cycle: Filter → emit event → EventConsumer → Telegram fails → error logged (NOT re-thrown) → no recursion. The guard is a safety net in case EventConsumer's try-catch is somehow bypassed.
  - [x] 3.4 Create `src/common/filters/system-error.filter.spec.ts` — co-located tests
  - [x] 3.5 Register as global filter in `AppModule` using `APP_FILTER` provider:
    ```typescript
    { provide: APP_FILTER, useClass: SystemErrorFilter }
    ```
    **NOTE:** This catches SystemError subclasses only. Other errors (NestJS built-in HttpException, raw Error) pass through to NestJS default handler. This is intentional — we only route our typed errors through the severity pipeline.

- [x] Task 4: Update `MonitoringModule` wiring (AC: #1, #3)
  - [x] 4.1 Add `EventConsumerService` to `MonitoringModule` providers
  - [x] 4.2 Export `EventConsumerService` (for future dashboard integration in Epic 7)
  - [x] 4.3 Verify `TelegramAlertService` is still a provider (not removed — still needed by EventConsumer)
  - [x] 4.4 No new module imports needed — `ConfigModule` already imported, `EventEmitter2` is global

- [x] Task 5: Write unit tests (AC: #6, #7)
  - [x] 5.1 `event-consumer.service.spec.ts` — co-located in `src/modules/monitoring/`
    - Test: wildcard subscription receives all event types
    - Test: critical events route to both structured log AND TelegramAlertService
    - Test: warning events route to both structured log AND TelegramAlertService
    - Test: info events route to structured log ONLY (no Telegram)
    - Test: non-Telegram-eligible events (e.g., `orderbook.updated`) are logged but NOT sent to Telegram
    - Test: severity classification covers all 27 events
    - Test: unknown event names default to `info` severity
    - Test: handler errors are caught and logged, never propagate
    - Test: metrics increment correctly for each event and severity
    - Test: `resetMetrics()` clears all counters
    - Test: correlationId is included in structured logs
  - [x] 5.2 Update `telegram-alert.service.spec.ts`:
    - Remove tests for `@OnEvent` decorator behavior (decorators removed)
    - Add tests for new `sendEventAlert(eventName, event)` public dispatch method
    - Keep all existing tests for `enqueueAndSend`, `sendMessage`, circuit breaker, buffer, daily test alert
    - Verify TELEGRAM_ELIGIBLE_EVENTS constant matches the 14 expected events
  - [x] 5.3 `system-error.filter.spec.ts` — co-located in `src/common/filters/`
    - Test: SystemError subclasses are caught and produce correct HTTP response
    - Test: critical severity maps to 500 + emits SystemHealthCriticalEvent
    - Test: warning severity maps to 400 + structured log only
    - Test: error code, severity, message present in response body
    - Test: non-SystemError exceptions are NOT caught (pass through)
    - Test: standard error format: `{ error: { code, message, severity }, timestamp }`
    - Test: non-HTTP context (e.g., 'ws' or 'rpc') does NOT call switchToHttp() — logs + emits event only
    - Test: re-entrancy guard prevents circular event emission (emit during emit → skip second emit)
    - Test: Cron-originated SystemError is handled gracefully (no HTTP response, just log + event)
  - [x] 5.4 Update `monitoring.module.spec.ts` — verify module provides both TelegramAlertService and EventConsumerService
  - [x] 5.5 Ensure all existing tests remain green

- [x] Task 6: Lint and final validation (AC: #6)
  - [x] 6.1 Run `pnpm lint` — zero errors
  - [x] 6.2 Run `pnpm test` — all pass

## Dev Notes

### Architecture Compliance

- **Module placement:** `EventConsumerService` lives in `src/modules/monitoring/` — per architecture: "event-consumer.service.ts — EventEmitter2 subscriber, routes to outputs" [Source: _bmad-output/planning-artifacts/architecture.md, line 518]
- **Fan-out pattern:** All event subscriptions MUST use `{ async: true }` — per architecture: "Fan-out (async EventEmitter2) — NEVER BLOCK EXECUTION. Telegram API timeout never delays the next execution cycle." [Source: _bmad-output/planning-artifacts/architecture.md, line 161]
- **Global exception filter:** `SystemErrorFilter` lives in `src/common/filters/` — per architecture: "common/filters/ — Global exception filter (routes by severity)" and "Global exception filter routes by severity: Critical → high-priority event (Telegram + audit + potential halt). Warning → dashboard update + log. Info → log only." [Source: _bmad-output/planning-artifacts/architecture.md, lines 176, 457]
- **Dependency rules respected:** `monitoring/` imports only from `common/` (events, errors, types, config). EventConsumerService calls TelegramAlertService via same-module DI — this is allowed. No imports from `connectors/` or other `modules/`.
- **Error hierarchy:** SystemErrorFilter handles all `SystemError` subclasses. Uses `SystemHealthError` for monitoring-specific errors (4000-4999 range). NEVER throws raw `Error`.
- **No new npm dependencies.** Uses existing `@nestjs/event-emitter` (`@OnEvent`), `@nestjs/core` (`APP_FILTER`, `ExceptionFilter`), and `nestjs-pino` (Logger).

### Key Technical Decisions

1. **Wildcard subscription (`@OnEvent('**')`) vs individual handlers:** The architecture describes EventConsumerService as a centralized subscriber. Using a single wildcard handler `@OnEvent('**', { async: true })`with EventEmitter2's`wildcard: true`config (already in AppModule) is the cleanest approach — it automatically captures all current and future events. If wildcard`**` doesn't match as expected, fall back to per-namespace patterns (`execution._`, `risk._`, etc.).

2. **Refactoring TelegramAlertService subscriptions:** Currently, TelegramAlertService directly subscribes to 14 events. Story 6.2 introduces EventConsumerService as the single hub. To avoid duplicate event handling, the `@OnEvent` decorators are REMOVED from TelegramAlertService and replaced by EventConsumerService calling TelegramAlertService's new `sendEventAlert()` method. This centralizes routing logic while preserving all existing Telegram formatting and delivery behavior.

3. **Severity classification as single source of truth:** The severity mapping currently exists in `telegram-message.formatter.ts` (`getEventSeverity()`). Story 6.2 moves this to `EventConsumerService.classifyEventSeverity()` as the canonical source. The old `getEventSeverity()` can be retained as a thin wrapper or removed (EventConsumerService passes severity to TelegramAlertService).

4. **Hybrid Telegram routing (severity + allowlist):** Critical and Warning events ALWAYS get Telegram alerts automatically — even new events without dedicated formatters get a generic alert. Info events use an explicit allowlist (`TELEGRAM_ELIGIBLE_INFO_EVENTS`) for the 6 info events that have formatters and are operationally important (ORDER_FILLED, OPPORTUNITY_IDENTIFIED, etc.). High-volume info events like `orderbook.updated` are logged only. This ensures new critical events (e.g., a future `risk.circuit.breaker.open`) automatically alert without code changes.

5. **Global exception filter scope:** `@Catch(SystemError)` catches ONLY SystemError subclasses. NestJS built-in HttpException and raw Error pass through to the default exception handler. This is intentional — we route only typed errors through our severity pipeline. Unknown errors get NestJS default 500 response with generic message.

6. **Metrics are in-memory only:** Simple counters — no Prometheus, no StatsD. Metrics are exposed via `getMetrics()` for the dashboard REST endpoint (Epic 7). Counters reset on app restart or via `resetMetrics()`. This is sufficient for MVP; persistent metrics can be added in Phase 1 if needed.

7. **AuditLogService placeholder:** The epic AC mentions "audit log (via AuditLogService from Story 6.5)". Since AuditLogService doesn't exist yet, EventConsumerService's routing code should have a clear extension point (e.g., `// TODO: Story 6.5 — auditLogService.log(event)` comment) but NOT create a stub service. When Story 6.5 is implemented, it will inject AuditLogService into EventConsumerService.

8. **Formatting ownership:** `EventConsumerService` does NOT import formatters directly. It delegates to `TelegramAlertService.sendEventAlert(eventName, event)` which owns the format-selection logic. TelegramAlertService remains the formatting + transport layer; EventConsumerService is the routing + classification layer. This keeps formatting concerns inside the Telegram service and avoids duplicating the formatter registry.

9. **Type safety in dispatch:** `TelegramAlertService.sendEventAlert()` uses a `switch` on `eventName` to cast `BaseEvent` to the specific event type before calling the formatter. This preserves type safety at the dispatch boundary — the same pattern as the current `handleEvent()` helper, just consolidated into one method. The casts are safe because the event name guarantees the payload type (events are emitted with their correct class by the source module).

10. **maxListeners consideration:** AppModule sets `maxListeners: 20`. After refactoring, EventConsumerService adds 1-8 wildcard listeners (depending on spike result) while TelegramAlertService removes 14. Net change is a significant reduction. If using per-namespace approach (8 handlers), total listener count stays well under 20. No config change needed.

### EventEmitter2 Wildcard Behavior

- AppModule config: `EventEmitterModule.forRoot({ wildcard: true, delimiter: '.', maxListeners: 20 })`
- With `wildcard: true`, patterns like `execution.*` match `execution.order.filled` but NOT `execution.single_leg.exposure` (single `*` matches one segment only)
- Use `execution.**` or `**` to match any depth. The double-star `**` matches zero or more segments.
- EventEmitter2 passes the event name as the first argument to wildcard handlers only if configured — verify behavior in tests. If event name is not passed, use `this.event` (EventEmitter2 stores current event name on the emitter instance in some versions). Alternative: check if `@OnEvent` in NestJS passes the event name — it may not with wildcards. If event name is not available, consider per-namespace handlers instead.
- **CRITICAL:** Test wildcard behavior in the first unit test to confirm event name is accessible before building the full routing logic.

### Interaction Between EventConsumerService and TelegramAlertService

**Before (Story 6.1):**

```
EventEmitter2 → [14 @OnEvent handlers in TelegramAlertService] → format → enqueueAndSend → Telegram API
```

**After (Story 6.2):**

```
EventEmitter2 → [wildcard @OnEvent in EventConsumerService] → classifySeverity → structuredLog
                                                             → (if Telegram-eligible) → TelegramAlertService.sendEventAlert() → format → enqueueAndSend → Telegram API
```

### Previous Story Intelligence (Story 6.1)

**Directly reusable patterns from Story 6.1:**

- **`handleEvent()` private helper pattern:** TelegramAlertService has a `handleEvent(eventName, formatFn, severity, correlationId)` method that wraps try-catch + fallback. EventConsumerService will have a similar central handler.
- **`{ async: true }` on all `@OnEvent` decorators:** Mandatory. Without it, handlers run synchronously in the emitter's call chain.
- **Formatter registry:** Story 6.1 created individual format functions. These remain unchanged — EventConsumerService delegates to TelegramAlertService which calls them.
- **Error code 4006 for monitoring failures:** Already in `monitoring-error-codes.ts`. May need 4007 for event consumer failures if a new error code is warranted.
- **Code review findings from 6.1:** Key lesson — "NEVER throw raw `Error`, NEVER log without error codes, ALWAYS use SystemError subclasses." Also: decimal.js for any financial values in formatters.
- **`withCorrelationId()`:** Used by TelegramAlertService's daily cron. EventConsumerService handlers already receive correlationId from BaseEvent — no need to wrap.

### Global Exception Filter Details

NestJS exception filter reference:

```typescript
import { Catch, ExceptionFilter, ArgumentsHost } from '@nestjs/common';
import { APP_FILTER } from '@nestjs/core';

@Catch(SystemError)
export class SystemErrorFilter implements ExceptionFilter {
  catch(exception: SystemError, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse();
    // ... build response
  }
}
```

Registration in AppModule:

```typescript
providers: [{ provide: APP_FILTER, useClass: SystemErrorFilter }];
```

**Important:** `APP_FILTER` allows multiple global filters. Adding our filter does NOT remove NestJS's default `HttpExceptionFilter`. Our filter catches `SystemError` specifically; other exceptions fall through.

For critical severity errors, the filter should emit a `SystemHealthCriticalEvent` via `EventEmitter2` so it flows through the EventConsumerService → Telegram pipeline. Inject `EventEmitter2` into the filter.

### Project Structure Notes

**Files to create:**

- `src/modules/monitoring/event-consumer.service.ts` — centralized event routing hub
- `src/modules/monitoring/event-consumer.service.spec.ts` — co-located tests
- `src/common/filters/system-error.filter.ts` — global exception filter
- `src/common/filters/system-error.filter.spec.ts` — co-located tests

**Files to modify:**

- `src/modules/monitoring/telegram-alert.service.ts` — remove @OnEvent decorators, add `sendEventAlert()` dispatch method, export TELEGRAM_ELIGIBLE_EVENTS
- `src/modules/monitoring/telegram-alert.service.spec.ts` — update tests for new dispatch pattern
- `src/modules/monitoring/monitoring.module.ts` — register EventConsumerService
- `src/modules/monitoring/monitoring.module.spec.ts` — update module compilation test
- `src/modules/monitoring/formatters/telegram-message.formatter.ts` — possibly export `getEventSeverity` for reuse or move severity mapping to EventConsumerService
- `src/app.module.ts` — register SystemErrorFilter via APP_FILTER provider

**Files to verify (existing tests must pass):**

- All existing spec files — this story refactors monitoring event flow and must not break anything
- Specifically: `telegram-alert.service.spec.ts` (most affected by refactor), `monitoring.module.spec.ts`

### Event Catalog — Complete Severity Mapping

| Event Name                               | Severity | Telegram? |
| ---------------------------------------- | -------- | --------- |
| `execution.single_leg.exposure`          | Critical | Yes       |
| `risk.limit.breached`                    | Critical | Yes       |
| `system.trading.halted`                  | Critical | Yes       |
| `system.health.critical`                 | Critical | Yes       |
| `system.reconciliation.discrepancy`      | Critical | Yes       |
| `time.drift.halt`                        | Critical | No (new)  |
| `execution.order.failed`                 | Warning  | Yes       |
| `risk.limit.approached`                  | Warning  | Yes       |
| `platform.health.degraded`               | Warning  | Yes       |
| `time.drift.critical`                    | Warning  | No (new)  |
| `time.drift.warning`                     | Warning  | No (new)  |
| `degradation.protocol.activated`         | Warning  | No (new)  |
| `execution.order.filled`                 | Info     | Yes       |
| `execution.exit.triggered`               | Info     | Yes       |
| `execution.single_leg.resolved`          | Info     | Yes       |
| `execution.single_leg.exposure_reminder` | Info     | No        |
| `detection.opportunity.identified`       | Info     | Yes       |
| `detection.opportunity.filtered`         | Info     | No        |
| `platform.health.updated`                | Info     | No        |
| `platform.health.recovered`              | Info     | Yes       |
| `platform.health.disconnected`           | Info     | No        |
| `orderbook.updated`                      | Info     | No        |
| `risk.override.applied`                  | Info     | No        |
| `risk.override.denied`                   | Info     | No        |
| `risk.budget.reserved`                   | Info     | No        |
| `risk.budget.committed`                  | Info     | No        |
| `risk.budget.released`                   | Info     | No        |
| `degradation.protocol.deactivated`       | Info     | No        |
| `system.reconciliation.complete`         | Info     | No        |
| `system.trading.resumed`                 | Info     | Yes       |
| `platform.gas.updated`                   | Info     | No        |

**"Yes" Telegram column:** These 14 events match the current TelegramAlertService subscriptions from Story 6.1. They have formatters.

### Existing Infrastructure to Leverage

- **EventEmitter2:** Already configured in `AppModule` with `wildcard: true`, `delimiter: '.'`, `maxListeners: 20`
- **Event classes:** All event classes in `src/common/events/*.events.ts` extend `BaseEvent` with `timestamp` and `correlationId`
- **Event catalog:** All event names in `src/common/events/event-catalog.ts` — import `EVENT_NAMES` constant
- **`@OnEvent()` decorator:** From `@nestjs/event-emitter` — already used throughout codebase
- **`TelegramAlertService`:** Fully implemented in Story 6.1 — `enqueueAndSend()`, `sendMessage()`, circuit breaker, buffer, formatters
- **`SystemError` hierarchy:** 5 error classes with codes 1000-4999
- **`SystemHealthError`:** Has `component?: string` field — use for monitoring-specific errors
- **`MONITORING_ERROR_CODES`:** Already has `TELEGRAM_SEND_FAILED: 4006`
- **Structured logging:** `nestjs-pino` — all log entries must include `timestamp`, `level`, `module`, `correlationId`, `message`, `data`
- **`APP_FILTER`:** NestJS `@nestjs/core` token for registering global exception filters
- **`@Catch()` decorator:** From `@nestjs/common` — used on exception filters

### Design Review Notes (LAD Review — Addressed)

**Reviewers:** kimi-k2-thinking + glm-4.7 via LAD MCP

**Issues Found:** 2 Critical, 2 High, 4 Medium
**All Addressed** — incorporated into story tasks and dev notes.

**C1 ACCEPTED:** `@OnEvent('**')` may not pass event name to handler. NestJS decorator may strip it. Added Task 0 (mandatory spike test) with fallback to per-namespace handlers or `eventEmitter.onAny()` programmatic registration.

**C2 ACCEPTED:** Circular event loop — SystemErrorFilter emits SystemHealthCriticalEvent → EventConsumer → Telegram fails → SystemHealthError → filter catches again. Added re-entrancy guard (`private emitting = false`) in filter + EventConsumer's try-catch prevents error propagation.

**H1 ACCEPTED:** Severity vs. Telegram eligibility mismatch — new Critical events like `time.drift.halt` wouldn't get Telegram alerts under pure eligibility-set approach. Switched to hybrid: Critical/Warning ALWAYS alert Telegram, Info uses explicit allowlist for the 6 operationally important info events.

**H2 ACCEPTED:** SystemErrorFilter assumes HTTP context — `host.switchToHttp()` crashes on Cron/WebSocket errors. Added `host.getType()` check before accessing HTTP response.

**M1 ACCEPTED:** Metrics `getMetrics()` returns references — external consumers could mutate internal state. Added shallow copy requirement: `{ ...this.eventCounts }`.

**M2 ACCEPTED:** Formatting ownership unclear. Clarified: EventConsumerService owns routing/classification, TelegramAlertService owns formatting/transport. EventConsumer calls `sendEventAlert(eventName, event)`, not formatters directly.

**M3 NOTED:** maxListeners=20 — after refactor, net listener reduction (remove 14, add 1-8). No config change needed.

**M4 ACCEPTED:** Type safety loss with generic BaseEvent dispatch. TelegramAlertService.sendEventAlert() uses switch + typed casts, same safety level as current individual handlers.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.2, line 1217] — Story definition and acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md, line 518] — EventConsumerService architecture spec
- [Source: _bmad-output/planning-artifacts/architecture.md, line 161] — Fan-out async EventEmitter2 pattern
- [Source: _bmad-output/planning-artifacts/architecture.md, line 176] — Global exception filter severity routing
- [Source: _bmad-output/planning-artifacts/architecture.md, line 457] — common/filters/ directory spec
- [Source: _bmad-output/planning-artifacts/architecture.md, line 594] — Monitoring module dependency rules
- [Source: _bmad-output/planning-artifacts/prd.md, line 775] — FR-MA-01 Telegram alerts within 2 seconds
- [Source: _bmad-output/planning-artifacts/prd.md, line 1332] — Error code catalog with severity classifications
- [Source: _bmad-output/planning-artifacts/prd.md, line 1379] — Alerting channels and fallback strategy
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts] — Complete event name constants (27 events)
- [Source: pm-arbitrage-engine/src/common/events/base.event.ts] — BaseEvent with correlationId
- [Source: pm-arbitrage-engine/src/common/errors/system-error.ts] — SystemError base class
- [Source: pm-arbitrage-engine/src/common/errors/system-health-error.ts] — SystemHealthError (codes 4000-4999)
- [Source: pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts] — Current TelegramAlertService with @OnEvent decorators
- [Source: pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.ts] — Event formatters and getEventSeverity()
- [Source: pm-arbitrage-engine/src/modules/monitoring/monitoring-error-codes.ts] — MONITORING_ERROR_CODES
- [Source: pm-arbitrage-engine/src/app.module.ts] — Current module registrations

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- Spike test confirmed `@OnEvent('**')` does NOT pass event name — only payload. Fallback: `eventEmitter.onAny()` which correctly passes `(eventName, payload)`.
- Re-entrancy guard initially wrapped entire `handleEvent()` — caused sequential events to be skipped. Fixed by wrapping only Telegram delegation section.

### Completion Notes List

- All 7 ACs verified and passing
- 968 tests pass (up from 924 baseline), 63 test files (up from 61)
- Lint clean (0 errors)
- Lad code review completed — findings assessed, no in-scope issues requiring changes
- Adversarial code review (Amelia) — 7 findings (2H, 4M, 1L), all fixed:
  - H1: Synced EVENT_SEVERITY_MAP in formatter with EventConsumerService (added 6 missing events: time.drift.*, degradation.protocol.activated)
  - H2: Added @internal JSDoc to handleEvent() clarifying public-for-testing-only
  - M1: Added missing beforeAll import in monitoring.module.spec.ts
  - M2: Clarified TELEGRAM_ELIGIBLE_EVENTS JSDoc — not used by EventConsumerService routing
  - M3: Added severity exhaustiveness comment in SystemErrorFilter
  - M4: Stopped filtering timestamp from summarizeEvent (correlationId still filtered)
  - L1: Generic Telegram alerts now use severity-appropriate emoji (red/yellow/blue)
- Task 0 spike confirmed `onAny()` approach; `@OnEvent('**')` strips event name in NestJS
- Hybrid Telegram routing: Critical/Warning ALWAYS alert, Info uses allowlist (6 operationally important events)
- `getEventSeverity()` in formatter retained for message formatting; `classifyEventSeverity()` in EventConsumerService is routing authority

### File List

**Created:**

- `src/modules/monitoring/event-consumer.service.ts` — centralized event routing hub
- `src/modules/monitoring/event-consumer.service.spec.ts` — 27 tests
- `src/common/filters/system-error.filter.ts` — global exception filter
- `src/common/filters/system-error.filter.spec.ts` — 13 tests

**Modified:**

- `src/modules/monitoring/telegram-alert.service.ts` — removed 14 @OnEvent decorators, added sendEventAlert() dispatch + FORMATTER_REGISTRY
- `src/modules/monitoring/telegram-alert.service.spec.ts` — rewritten for dispatch pattern (49 tests)
- `src/modules/monitoring/monitoring.module.ts` — added EventConsumerService provider + export
- `src/modules/monitoring/monitoring.module.spec.ts` — added EventConsumerService availability test
- `src/modules/monitoring/monitoring-error-codes.ts` — added EVENT_CONSUMER_HANDLER_FAILED: 4007
- `src/modules/monitoring/formatters/telegram-message.formatter.ts` — synced EVENT_SEVERITY_MAP with EventConsumerService (6 events added)
- `src/app.module.ts` — registered SystemErrorFilter via APP_FILTER
