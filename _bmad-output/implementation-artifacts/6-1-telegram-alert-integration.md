# Story 6.1: Telegram Alert Integration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want real-time Telegram alerts for all critical system events,
So that I'm immediately informed of opportunities, executions, risks, and errors wherever I am.

## Acceptance Criteria

1. **Given** a Telegram bot token and chat ID are configured via `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env vars
   **When** the `TelegramAlertService` initializes
   **Then** it validates both values are present (non-empty strings)
   **And** logs a warning if either is missing but does NOT halt the engine — alerting is optional

2. **Given** a critical or warning event is emitted via EventEmitter2 (any of: `OpportunityIdentifiedEvent`, `OrderFilledEvent`, `ExitTriggeredEvent`, `SingleLegExposureEvent`, `LimitBreachedEvent`, `LimitApproachedEvent`, `PlatformDegradedEvent`, `PlatformRecoveredEvent`, `SystemHealthCriticalEvent`, `ExecutionFailedEvent`, `ReconciliationDiscrepancyEvent`, `SingleLegResolvedEvent`, `TradingHaltedEvent`, `TradingResumedEvent`)
   **When** the `TelegramAlertService` receives the event
   **Then** a Telegram message is sent within 2 seconds of the event (FR-MA-01)
   **And** the message includes full context: event type, timestamp, affected contracts, P&L impact, and recommended actions where applicable
   **And** messages use HTML `parse_mode` for reliable formatting (bold headers, monospace values)

3. **Given** the Telegram API fails (HTTP error or timeout)
   **When** the initial send attempt fails (within 2s timeout)
   **Then** the message is buffered in-memory (priority queue capped at 100 messages, critical > warning > info)
   **And** buffer drain retries asynchronously using `withRetry()` with exponential backoff
   **And** after 3 consecutive send failures, the circuit breaker opens for 60s
   **And** each failure is logged as a `SystemHealthError(4006)` with severity `warning`
   **And** system operation continues — alerting failure NEVER blocks trading or any other module

4. **Given** the `@nestjs/schedule` daily cron trigger fires (configurable time via `TELEGRAM_TEST_ALERT_CRON`, default `0 8 * * *` = 8am UTC daily, timezone via `TELEGRAM_TEST_ALERT_TIMEZONE` default `UTC`)
   **When** the test alert fires
   **Then** a test message is sent to Telegram confirming alerting health
   **And** success/failure is logged for alerting health monitoring

5. All existing tests pass, `pnpm lint` reports zero errors
6. New unit tests cover: message formatting for each event type, send success, send failure with retry, buffer overflow cap, daily test alert, config validation (missing token/chat ID), circuit breaker behavior, rate limiting

## Tasks / Subtasks

- [x] Task 1: Create `TelegramAlertService` in `src/modules/monitoring/` (AC: #1, #2, #3)
  - [x]1.1 Create `telegram-alert.service.ts` with `@Injectable()` NestJS service
  - [x]1.2 Inject `ConfigService` for env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_TEST_ALERT_CRON` (default `0 8 * * *`), `TELEGRAM_TEST_ALERT_TIMEZONE` (default `UTC`), `TELEGRAM_SEND_TIMEOUT_MS` (default `2000`), `TELEGRAM_MAX_RETRIES` (default `3`), `TELEGRAM_BUFFER_MAX_SIZE` (default `100`)
  - [x]1.3 Implement `onModuleInit()`: validate config, log warning if token/chatId missing, set `this.enabled = false` if unconfigured — all subscription handlers check `this.enabled` before processing
  - [x]1.4 Implement `sendMessage(text: string): Promise<boolean>` — the single HTTP send attempt:
    - Use Node.js native `fetch()` (Node 20+ — confirmed runtime v20.19.2, same pattern as `GasEstimationService`)
    - `POST https://api.telegram.org/bot${token}/sendMessage`
    - Body: `{ chat_id, text, parse_mode: 'HTML', disable_web_page_preview: true }`
    - Content-Type: `application/json`
    - Timeout: `TELEGRAM_SEND_TIMEOUT_MS` (default 2000ms) via `AbortSignal.timeout()` (Node 20+)
    - Return `true` on success (`response.ok && body.ok`), `false` on failure
    - On Telegram 429 response: parse `retry_after` field and respect it in circuit breaker timing
    - **NO retries in sendMessage itself** — the event handler calls sendMessage once; on failure, buffer the message for async retry
  - [x]1.5 Implement `enqueueAndSend(text: string, severity: 'critical' | 'warning' | 'info'): Promise<void>` — the main entry point called by event handlers:
    - If circuit breaker is OPEN: buffer message (do NOT attempt HTTP call), return immediately
    - If circuit breaker is CLOSED/HALF_OPEN: call `sendMessage()`
    - On success: reset `consecutiveFailures` to 0, set circuit to CLOSED, trigger async buffer drain
    - On failure: increment `consecutiveFailures`, buffer the message, log `SystemHealthError(4006)`
  - [x]1.6 Implement priority message buffer:
    - Buffer type: `{ text: string, severity: 'critical' | 'warning' | 'info', timestamp: number }[]`
    - Cap at `TELEGRAM_BUFFER_MAX_SIZE` (default 100)
    - On overflow: drop lowest-priority messages first (info before warning before critical). Within same priority, drop oldest (FIFO)
    - **Async buffer drain:** On next successful send, drain buffer in background via `setImmediate()` — send one message per 1000ms (respects Telegram individual chat rate limit of 1 msg/sec). Use `withRetry()` from `src/common/utils/with-retry.ts` with strategy: `{ maxRetries: 2, initialDelayMs: 1000, maxDelayMs: 3000, backoffMultiplier: 2 }`
    - Drain highest-priority messages first
  - [x]1.7 Implement circuit breaker pattern (3-state: CLOSED → OPEN → HALF_OPEN):
    - Track `consecutiveFailures: number` and `circuitOpenUntil: number` (timestamp)
    - **CLOSED** (normal): all sends attempted
    - **OPEN** (after 3 consecutive failures): skip HTTP calls, buffer all messages, wait `TELEGRAM_CIRCUIT_BREAK_MS` (default `60000`). If Telegram returned 429 with `retry_after`, use `max(retry_after * 1000, TELEGRAM_CIRCUIT_BREAK_MS)` instead
    - **HALF_OPEN** (after break period expires): attempt one "probe" send. Success → CLOSED + drain buffer. Failure → OPEN + restart timer
    - Log state transitions via structured logging (NOT event catalog — these are internal operational logs)
    - **Thread safety note:** Since Node.js is single-threaded, no mutex needed. But ensure `enqueueAndSend` is not re-entrant during buffer drain — use a `draining: boolean` flag
  - [x]1.8 Add `TELEGRAM_SEND_FAILED` error code (4006) to a new `src/modules/monitoring/monitoring-error-codes.ts`. Use `SystemHealthError` (codes 4000-4999), NOT `PlatformApiError` — because `PlatformApiError` requires `platformId: PlatformId` and Telegram is not a trading platform. `SystemHealthError` has a `component: string` field which fits: `component: 'telegram-alerting'`

- [x]Task 2: Create message formatters in `src/modules/monitoring/formatters/telegram-message.formatter.ts` (AC: #2)
  - [x]2.1 Create `formatAlertMessage(event: BaseEvent, eventName: string): string` — main dispatcher
  - [x]2.2 Implement per-event-type formatters using HTML parse_mode:
    - `formatOpportunityIdentified(event)` — contracts, edge %, platforms, position size
    - `formatOrderFilled(event)` — order details, fill price, slippage, platform
    - `formatExecutionFailed(event)` — error code, reason, affected position
    - `formatSingleLegExposure(event)` — URGENT header, filled leg details, P&L scenarios, recommended actions
    - `formatSingleLegResolved(event)` — resolution method, outcome, P&L impact
    - `formatExitTriggered(event)` — exit type (TP/SL/time), position details, realized P&L
    - `formatLimitApproached(event)` — limit type, current value, threshold, % utilization
    - `formatLimitBreached(event)` — URGENT header, limit type, breach amount, auto-actions taken
    - `formatPlatformDegraded(event)` — platform, previous status, degradation details
    - `formatPlatformRecovered(event)` — platform, recovery details, downtime duration
    - `formatTradingHalted(event)` — URGENT header, halt reason, active positions
    - `formatTradingResumed(event)` — resume reason, halted duration
    - `formatReconciliationDiscrepancy(event)` — discrepancy details, affected positions
    - `formatSystemHealthCritical(event)` — component, diagnostic info, recommended actions
    - `formatTestAlert()` — timestamp, system uptime, "Alerting system healthy"
  - [x]2.3 All formatters produce HTML with:
    - Bold header line with emoji indicator: `🔴` critical, `🟡` warning, `🟢` info
    - Monospace values using `<code>` tags for prices, IDs, percentages
    - Timestamp in ISO format
    - CorrelationId when available
    - Max message length 4096 chars (Telegram limit) — smart truncation: preserve header (first 500 chars with event type + severity) and footer (last 200 chars with correlationId + timestamp), truncate middle body with `\n[...truncated...]\n`
  - [x]2.4 Implement `escapeHtml(text: string): string` utility to escape `<`, `>`, `&` in dynamic values before inserting into HTML templates

- [x]Task 3: Create `MonitoringModule` and wire event subscriptions (AC: #2)
  - [x]3.1 Create `src/modules/monitoring/monitoring.module.ts` — NestJS module
    - Import: `ConfigModule`, `ScheduleModule` (already registered in `AppModule` — do NOT re-register, just import for DI)
    - Providers: `TelegramAlertService`
    - Exports: `TelegramAlertService` (for future use by EventConsumer in Story 6.2)
  - [x]3.2 Register `MonitoringModule` in `AppModule` imports
  - [x]3.3 In `TelegramAlertService`, subscribe to events via `@OnEvent()` decorators:
    - `@OnEvent(EVENT_NAMES.OPPORTUNITY_IDENTIFIED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.ORDER_FILLED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.EXECUTION_FAILED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.SINGLE_LEG_EXPOSURE, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.SINGLE_LEG_RESOLVED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.EXIT_TRIGGERED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.LIMIT_APPROACHED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.LIMIT_BREACHED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.PLATFORM_HEALTH_DEGRADED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.PLATFORM_HEALTH_RECOVERED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.SYSTEM_TRADING_HALTED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.SYSTEM_TRADING_RESUMED, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.RECONCILIATION_DISCREPANCY, { async: true })` → format + send
    - `@OnEvent(EVENT_NAMES.SYSTEM_HEALTH_CRITICAL, { async: true })` → format + send
  - [x]3.4 **CRITICAL: All `@OnEvent` handlers MUST use `{ async: true }`** — this ensures event handling is non-blocking. The monitoring module subscribes to events on the fan-out path and MUST NEVER block the hot path (detection → risk → execution). If `sendMessage` throws or hangs, it must not propagate back to the emitter.
  - [x]3.5 Each event handler wraps the entire format+send in a try-catch that logs errors but never re-throws

- [x]Task 4: Implement daily test alert via `@nestjs/schedule` (AC: #4)
  - [x]4.1 Add `@Cron()` decorator on `handleTestAlert()` method using `TELEGRAM_TEST_ALERT_CRON` config value
    - Note: `@nestjs/schedule` is already a dependency (`^6.1.1`). `ScheduleModule.forRoot()` must be registered in `AppModule` if not already — check first
  - [x]4.2 `handleTestAlert()` sends formatted test message, logs success/failure
  - [x]4.3 Wrap in correlation context via `withCorrelationId()` for structured logging

- [x]Task 5: Update environment configuration (AC: #1)
  - [x]5.1 Add to `.env.example`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_TEST_ALERT_CRON`, `TELEGRAM_TEST_ALERT_TIMEZONE`, `TELEGRAM_SEND_TIMEOUT_MS`, `TELEGRAM_MAX_RETRIES`, `TELEGRAM_BUFFER_MAX_SIZE`, `TELEGRAM_CIRCUIT_BREAK_MS`
  - [x]5.2 Add to `.env.development` with empty/default values (empty token + chatId so alerts are disabled in dev by default)

- [x]Task 6: Write unit tests (AC: #5, #6)
  - [x]6.1 `telegram-alert.service.spec.ts` — co-located in `src/modules/monitoring/`
    - Test: service initializes with valid config
    - Test: service disables gracefully with missing token
    - Test: service disables gracefully with missing chat ID
    - Test: successful message send (mock `global.fetch`)
    - Test: message send failure buffers message immediately (no sync retries)
    - Test: buffer stores failed messages with priority (critical > warning > info)
    - Test: buffer overflow drops lowest priority first, then oldest within same priority
    - Test: buffer drains on successful send (1000ms between messages, highest priority first)
    - Test: buffer drain uses `withRetry()` with correct strategy
    - Test: circuit breaker opens after consecutive failures
    - Test: circuit breaker closes after successful probe
    - Test: event handlers call format + send (for each subscribed event)
    - Test: event handlers never throw (verify try-catch wrapping)
    - Test: daily test alert sends formatted message
    - Test: Telegram API timeout handled via AbortSignal.timeout (2000ms)
    - Test: Telegram 429 response sets circuit break to max(retry_after, default break)
    - Test: circuit breaker HALF_OPEN probe succeeds → CLOSED + drain
    - Test: circuit breaker HALF_OPEN probe fails → OPEN again
    - Test: CB OPEN state still buffers messages (does not drop them)
    - Test: SystemHealthError(4006) logged on failure (not PlatformApiError)
  - [x]6.2 `telegram-message.formatter.spec.ts` — co-located in `src/modules/monitoring/formatters/`
    - Test: each event type produces correct HTML structure
    - Test: HTML escaping prevents injection
    - Test: smart truncation at 4096 chars (header preserved, middle truncated, footer preserved)
    - Test: emoji severity indicators correct (🔴 critical, 🟡 warning, 🟢 info)
    - Test: correlationId included when present
    - Test: timestamps in ISO format
  - [x]6.3 `monitoring.module.spec.ts` — verify module compiles and provides TelegramAlertService
  - [x]6.4 Ensure all existing tests remain green

- [x]Task 7: Lint and final validation (AC: #5)
  - [x]7.1 Run `pnpm lint` — zero errors
  - [x]7.2 Run `pnpm test` — all pass

## Dev Notes

### Architecture Compliance

- **Module placement:** `TelegramAlertService` lives in `src/modules/monitoring/` — per architecture: "modules/monitoring/ → persistence/ (audit logs, reports), common/events/ (subscribes to all)." [Source: docs/architecture.md#Module-Dependency-Graph]
- **Fan-out pattern:** All event subscriptions use `{ async: true }` — per architecture: "Fan-out (async EventEmitter2) — NEVER BLOCK EXECUTION. Telegram API timeout never delays the next execution cycle." [Source: docs/architecture.md#API-Communication-Patterns]
- **Error hierarchy:** Uses `SystemHealthError` with code `4006` (TELEGRAM_SEND_FAILED), `component: 'telegram-alerting'`. Severity: `warning`. **NOT `PlatformApiError`** — that requires `platformId: PlatformId` and Telegram is not a trading platform. `SystemHealthError` (4000-4999 range) with its `component: string` field is the correct fit. **NEVER use raw `Error`.**
- **Dependency rules respected:** `monitoring/` imports only from `common/` (events, errors, types, config). No direct imports from other modules' services. No imports from `connectors/`.
- **No new npm dependencies.** Uses Node.js native `fetch()` for HTTP calls (same proven pattern as `GasEstimationService` in Story 6.0). No `node-telegram-bot-api`, no `telegraf`, no `nestjs-telegraf` — those libraries bring unnecessary complexity (polling, middleware, session management) when we only need a simple HTTP POST to `sendMessage`.

### Key Technical Decisions

1. **Native `fetch()` over Telegram bot libraries:** We only need `sendMessage` — a single HTTP POST endpoint. Libraries like `node-telegram-bot-api` (v0.67.0) and `telegraf` (v4.x) are designed for full bot development (polling, webhooks, middleware, sessions). Our use case is fire-and-forget alerting. Native `fetch()` has zero dependencies, is already proven in this codebase (Story 6.0 CoinGecko calls), and gives us full control over timeout/retry behavior.

2. **HTML parse_mode over MarkdownV2:** Telegram's MarkdownV2 requires escaping 18 special characters (`_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`). HTML only requires escaping `<`, `>`, `&`. HTML is more reliable and less error-prone for dynamic content (prices, contract IDs, error messages). Formatting tags: `<b>bold</b>`, `<i>italic</i>`, `<code>monospace</code>`, `<pre>code block</pre>`.

3. **Telegram Bot API details:**
   - Endpoint: `POST https://api.telegram.org/bot{token}/sendMessage`
   - Request body (JSON): `{ chat_id: string, text: string, parse_mode: "HTML", disable_web_page_preview: true }`
   - Response: `{ ok: boolean, result?: Message, description?: string, error_code?: number }`
   - Rate limits: 30 messages/second to same chat (group), 1 message/second per user chat. Our alert rate is far below this.
   - Max message length: 4096 characters (UTF-8)
   - Bot token format: `{bot_id}:{secret}` (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

4. **Circuit breaker pattern (3-state):** CLOSED → OPEN → HALF_OPEN. After 3 consecutive failures, enter OPEN state (skip HTTP, buffer only) for 60 seconds. On Telegram 429 response, respect `retry_after` field as minimum break duration. After break period, enter HALF_OPEN and probe with one send. Success → CLOSED + drain buffer. Failure → OPEN again. This protects the engine from wasting resources on failing HTTP calls. Node.js is single-threaded so no mutex needed, but use a `draining: boolean` flag to prevent re-entrant buffer drain.

5. **`@OnEvent({ async: true })` is mandatory:** Without `async: true`, EventEmitter2 runs the handler synchronously in the emitter's call chain. A slow Telegram API call (or timeout) would directly delay the detection→risk→execution hot path. `async: true` runs the handler in a microtask, fully decoupling it.

6. **`@nestjs/schedule` for daily test alert:** Already a project dependency (`^6.1.1`). Uses cron syntax. The `ScheduleModule.forRoot()` must be imported once in `AppModule`. Check if it's already registered — if not, add it.

### Telegram API Reference (Web Research)

- **sendMessage endpoint:** `POST https://api.telegram.org/bot{token}/sendMessage`
- **Required parameters:** `chat_id` (string or integer), `text` (string, 1-4096 chars)
- **Optional parameters:** `parse_mode` ("HTML" | "Markdown" | "MarkdownV2"), `disable_web_page_preview` (boolean), `disable_notification` (boolean)
- **Rate limits:** 30 messages/sec to groups, 1 msg/sec to individual chats
- **Error codes:** 400 (bad request), 401 (unauthorized/invalid token), 403 (bot blocked by user), 429 (too many requests — includes `retry_after` field)
- **Known IPv6 issue:** `node-telegram-bot-api` has an active bug with IPv6 (Node.js Happy Eyeballs). Not relevant to us since we use native `fetch()` with explicit timeout handling.

### Previous Story Intelligence (Story 6.0)

**Learnings from Story 6.0 that directly apply:**

- **Native `fetch()` pattern:** Story 6.0's `GasEstimationService` uses `fetch()` with `AbortController` for CoinGecko API calls. Same pattern applies here for Telegram API. Proven working in this codebase.
- **Timeout pattern:** 5s timeout via `AbortController` + `setTimeout` with cleanup in `finally` block. Reuse this pattern.
- **Error code placement:** Story 6.0 added error codes to connector-specific file (`polymarket-error-codes.ts`). For monitoring, create `monitoring-error-codes.ts` following the same pattern.
- **Module registration:** Story 6.0 registered `GasEstimationService` in `ConnectorModule`. Similarly, register `TelegramAlertService` in `MonitoringModule`.
- **Event emission pattern:** Story 6.0 added `PLATFORM_GAS_UPDATED` to the event catalog. No new catalog events needed for this story — we're subscribing to existing events, not emitting new ones. (Exception: may add `monitoring.telegram.circuit_open` / `monitoring.telegram.circuit_closed` as log events only, not catalog entries.)
- **Code review findings:** Story 6.0 had 3 medium issues — all about error hierarchy compliance. Lesson: **NEVER throw raw `Error`, NEVER log without error codes, ALWAYS use SystemError subclasses.**

### Git Intelligence

Recent commits show the codebase is mature (Sprint 5.5 complete, 6.0 done). Key patterns:

- Paper trading mode (`isPaper` flag) is in Order and OpenPosition models — event formatters should include this context where relevant
- Mixed mode (`mixedMode` flag) in execution events — formatters should display this
- Gas estimation service was the most recent implementation — follow its patterns for HTTP calls, config, testing

### Financial Math

No financial calculations in this story. The formatter will display monetary values (P&L, edge percentages) from event payloads but does NOT perform calculations. All financial values received from events are already computed using `decimal.js` by their source modules.

When displaying Decimal values in messages, convert via `.toFixed(4)` for prices and `.toFixed(2)` for percentages. Do NOT perform arithmetic on these values in the formatter.

### Project Structure Notes

**Files to create:**

- `src/modules/monitoring/monitoring.module.ts` — NestJS module definition
- `src/modules/monitoring/monitoring.module.spec.ts` — module compilation test
- `src/modules/monitoring/telegram-alert.service.ts` — Telegram alert service
- `src/modules/monitoring/telegram-alert.service.spec.ts` — co-located tests
- `src/modules/monitoring/monitoring-error-codes.ts` — error codes (4006+ in SystemHealthError range)
- `src/modules/monitoring/formatters/telegram-message.formatter.ts` — message formatters
- `src/modules/monitoring/formatters/telegram-message.formatter.spec.ts` — formatter tests

**Files to modify:**

- `src/app.module.ts` — register `MonitoringModule` in imports (and `ScheduleModule.forRoot()` if not already registered)
- `.env.example` — add Telegram env vars
- `.env.development` — add Telegram env vars (empty defaults)

**Files to delete:**

- `src/modules/monitoring/.gitkeep` — replaced by actual module files

**Files to verify (existing tests must pass):**

- All existing spec files — this story adds a new module and should not break anything
- Specifically verify: event emission from other modules still works after monitoring subscribes

### Event Type to Severity Mapping

| Event                        | Severity | Emoji |
| ---------------------------- | -------- | ----- |
| `SINGLE_LEG_EXPOSURE`        | Critical | 🔴    |
| `LIMIT_BREACHED`             | Critical | 🔴    |
| `SYSTEM_TRADING_HALTED`      | Critical | 🔴    |
| `SYSTEM_HEALTH_CRITICAL`     | Critical | 🔴    |
| `RECONCILIATION_DISCREPANCY` | Critical | 🔴    |
| `EXECUTION_FAILED`           | Warning  | 🟡    |
| `LIMIT_APPROACHED`           | Warning  | 🟡    |
| `PLATFORM_HEALTH_DEGRADED`   | Warning  | 🟡    |
| `EXIT_TRIGGERED`             | Info     | 🟢    |
| `ORDER_FILLED`               | Info     | 🟢    |
| `OPPORTUNITY_IDENTIFIED`     | Info     | 🟢    |
| `SINGLE_LEG_RESOLVED`        | Info     | 🟢    |
| `PLATFORM_HEALTH_RECOVERED`  | Info     | 🟢    |
| `SYSTEM_TRADING_RESUMED`     | Info     | 🟢    |

### Existing Infrastructure to Leverage

- **EventEmitter2:** Already configured in `AppModule` with `wildcard: true`, `delimiter: '.'`, `maxListeners: 20`
- **Event classes:** All event classes in `src/common/events/*.events.ts` extend `BaseEvent` with `timestamp` and `correlationId`
- **Event catalog:** All event names in `src/common/events/event-catalog.ts` — import `EVENT_NAMES` constant
- **`@OnEvent()` decorator:** From `@nestjs/event-emitter` — already used throughout codebase
- **`withRetry(fn, strategy, onRetry?)`:** Utility in `src/common/utils/with-retry.ts` — fully compatible. Signature: `withRetry<T>(fn: () => Promise<T>, strategy: RetryStrategy, onRetry?: (attempt, error) => void): Promise<T>`. Uses exponential backoff with jitter (0.5x-1.5x). Use for async buffer drain retries with strategy: `{ maxRetries: 2, initialDelayMs: 1000, maxDelayMs: 3000, backoffMultiplier: 2 }`
- **`withCorrelationId()`:** From `src/common/services/correlation-context.ts` — use for scheduled tasks
- **`getCorrelationId()`:** From same file — use in log entries
- **Structured logging:** `nestjs-pino` — all log entries must include `timestamp`, `level`, `module`, `correlationId`, `message`, `data`
- **`@nestjs/schedule`:** Dependency `^6.1.1` already in package.json — verify `ScheduleModule.forRoot()` is imported

### Design Review Notes (LAD Review — Addressed)

**Reviewers:** kimi-k2-thinking + glm-4.7 via LAD MCP

**Issues Found:** 2 Critical, 5 High-Priority, 3 Informational
**Issues Accepted:** 7 (all critical + high incorporated into story)
**Issues Rejected:** 3 (informational — see below)

**C1 ACCEPTED:** `PlatformApiError` requires `platformId: PlatformId` (enum: KALSHI, POLYMARKET). Telegram is not a trading platform. Switched to `SystemHealthError(4006)` with `component: 'telegram-alerting'`.

**C2 ACCEPTED:** Timeout/retry violates 2s FR-MA-01 requirement. Original design: 5s timeout + 3 retries = 12s worst case. Fixed: 2s timeout, single attempt on hot path. Failed messages buffered for async retry via `withRetry()`.

**H1 ACCEPTED:** Buffer drain rate 100ms exceeds individual chat rate limit (1 msg/sec). Fixed: 1000ms between drain messages.

**H2 ACCEPTED:** Circuit breaker OPEN state should still buffer messages, not drop them. Clarified in design.

**H3 ACCEPTED:** FIFO buffer drops critical alerts during overflow. Fixed: priority queue (critical > warning > info).

**H4 ACCEPTED:** Cron timezone ambiguous. Added `TELEGRAM_TEST_ALERT_TIMEZONE` env var (default UTC).

**H5 ACCEPTED:** Naive tail truncation hides critical data. Fixed: smart truncation preserving header + footer, truncating middle.

**I1 REJECTED:** "Node.js v18 compatibility risk with AbortSignal.timeout()" — Runtime confirmed as Node v20.19.2. Not an issue.

**I2 REJECTED:** "Add TELEGRAM to PlatformId enum" — Telegram is not a trading platform. Using SystemHealthError instead is the correct architectural choice.

**I3 REJECTED:** "Token format validation regex" — Over-engineering. Telegram returns 401 for invalid tokens, which we handle gracefully.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.1] — Story definition and acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#API-Communication-Patterns] — Fan-out pattern, EventEmitter2 async requirement
- [Source: _bmad-output/planning-artifacts/architecture.md#Module-Dependency-Graph] — Monitoring module allowed imports
- [Source: _bmad-output/planning-artifacts/architecture.md#Monitoring-Module-Directory-Structure] — Expected file structure
- [Source: _bmad-output/planning-artifacts/prd.md#FR-MA-01] — Telegram alerts within 2 seconds, full context
- [Source: _bmad-output/planning-artifacts/prd.md#Alerting-Channels-Fallback] — 3 consecutive failure detection, local buffer, never block trading
- [Source: _bmad-output/planning-artifacts/prd.md#Error-Codes] — Error code catalog, severity routing
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts] — Complete event name constants
- [Source: pm-arbitrage-engine/src/common/events/base.event.ts] — BaseEvent with correlationId
- [Source: pm-arbitrage-engine/src/connectors/polymarket/gas-estimation.service.ts] — fetch() + AbortController pattern to reuse
- [Source: pm-arbitrage-engine/src/common/utils/retry.utils.ts] — withRetry() utility
- [Source: pm-arbitrage-engine/src/common/services/correlation-context.ts] — Correlation context utilities

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- ESLint `@typescript-eslint/no-base-to-string` on `Record<string, unknown>` values in `formatOpportunityIdentified` — fixed with `str()` helper that type-narrows before `String()` conversion
- E2E test timeouts (pre-existing, not caused by this story): `logging.e2e-spec.ts`, `app.e2e-spec.ts`, `core-lifecycle.e2e-spec.ts` — require DB/connectors not available in unit test runs

### Completion Notes List

- All 14 event handlers implemented via `handleEvent()` private helper that includes fallback alert on formatter error (Lad review improvement)
- `SystemHealthCriticalEvent` class was missing from `common/events/system.events.ts` — created it as part of this story
- Circuit breaker respects Telegram 429 `retry_after` field as minimum break duration
- Buffer drain rate set to 1000ms between messages (respects Telegram 1 msg/sec individual chat rate limit)
- `@Cron` decorator uses `process.env.TELEGRAM_TEST_ALERT_CRON` with fallback `'0 8 * * *'` (NestJS limitation: decorator values must be static expressions)
- 885 unit tests pass, 0 lint errors at completion

### File List

**Created:**

- `pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts`
- `pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.spec.ts`
- `pm-arbitrage-engine/src/modules/monitoring/monitoring.module.ts`
- `pm-arbitrage-engine/src/modules/monitoring/monitoring.module.spec.ts`
- `pm-arbitrage-engine/src/modules/monitoring/monitoring-error-codes.ts`
- `pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.ts`
- `pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.spec.ts`

**Modified:**

- `pm-arbitrage-engine/src/app.module.ts` — added MonitoringModule import
- `pm-arbitrage-engine/src/common/events/system.events.ts` — added SystemHealthCriticalEvent class
- `pm-arbitrage-engine/.env.example` — added 8 Telegram env vars
- `pm-arbitrage-engine/.env.development` — added 8 Telegram env vars (disabled by default)

**Deleted:**

- `pm-arbitrage-engine/src/modules/monitoring/.gitkeep`

### Senior Developer Review (AI) — 2026-02-24

**Reviewer:** Claude Opus 4.6 (Adversarial Code Review)

**Issues Found:** 3 High, 4 Medium, 1 Low — **All Fixed**

**H1 FIXED:** Buffer drain did not use `withRetry()` as specified in Task 1.6. Replaced raw `sendMessage()` call in `drainBuffer()` with `withRetry()` using strategy `{ maxRetries: 2, initialDelayMs: 1000, maxDelayMs: 3000, backoffMultiplier: 2 }`.

**H2 FIXED:** Missing event handler tests. Added 18 tests covering: each of 14 `@OnEvent` handlers calls `enqueueAndSend` with correct format+severity, try-catch wrapping prevents propagation, fallback alert sent on formatter error, disabled service skips processing, and drain retry behavior with `withRetry`.

**H3 FIXED:** `formatOrderFilled` slippage calculation used native JS subtraction. Replaced with `new Decimal(event.fillPrice).minus(event.price).abs()`.

**M1 FIXED:** `formatLimitBreached` breach amount used native JS subtraction. Replaced with `new Decimal(event.currentValue).minus(event.threshold).toFixed(2)`.

**M2 FIXED:** Dead `this.testAlertCron` field removed from constructor (decorator reads `process.env` directly due to NestJS limitation).

**M3 FIXED:** `formatTestAlert()` now includes system uptime via `process.uptime()` as specified in Task 2.2.

**M4 FIXED:** `drainBuffer()` now sorts buffer once before the while loop instead of on every iteration.

**L1 FIXED:** Deduplicated `AlertSeverity` type — now exported from formatter and imported by service.

**Test Results:** 886 unit tests pass (18 new), 0 lint errors.
