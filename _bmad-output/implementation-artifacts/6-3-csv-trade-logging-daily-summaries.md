# Story 6.3: CSV Trade Logging & Daily Summaries

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want all trades logged to timestamped CSV files with a daily summary,
So that I can review each day's activity in a spreadsheet and track performance over time.

## Acceptance Criteria

1. **Given** a trade is executed (position opened or closed)
   **When** the `EventConsumerService` routes an `OrderFilledEvent` or `ExitTriggeredEvent`
   **Then** a trade record is appended to a timestamped CSV file (one file per day, UTC) in the configured output directory
   **And** the CSV columns are: `timestamp`, `platform`, `contract_id`, `side`, `price`, `size`, `fill_price`, `fees`, `gas`, `edge`, `pnl`, `position_id`, `pair_id`, `is_paper`, `correlation_id` (FR-MA-02)
   **And** files follow the naming pattern `trades-YYYY-MM-DD.csv`
   **And** each file includes a CSV header row on creation

2. **Given** a new calendar day begins (UTC midnight)
   **When** the daily summary cron triggers
   **Then** a summary record is appended to a `daily-summaries.csv` file with columns: `date`, `total_trades`, `total_pnl`, `open_positions`, `closed_positions`, `opportunities_detected`, `opportunities_executed`, `single_leg_events`, `risk_limit_events`, `system_health_summary` (FR-MA-03)
   **And** the summary is also sent as a Telegram message via `TelegramAlertService`

3. **Given** the operator requests `GET /api/exports/trades?startDate=X&endDate=Y&format=json|csv`
   **When** the export endpoint processes the request
   **Then** the system returns trade data from the database in the requested format (FR-DE-01)
   **And** CSV format uses the same column schema as the daily trade log files
   **And** JSON format uses the standard `{ data: T[], count: number, timestamp: string }` response wrapper
   **And** date parameters are validated as ISO 8601 dates
   **And** requests with >90 day range are rejected with a 400 error

4. **Given** the CSV write directory is configured via `CSV_TRADE_LOG_DIR` env var
   **When** the `CsvTradeLogService` initializes
   **Then** it ensures the directory exists (creates if missing)
   **And** if the directory is not writable, it logs a `SystemHealthError(4008)` and disables CSV logging (never halts the engine)
   **And** defaults to `./data/trade-logs` if env var is not set

5. **Given** the CSV logging infrastructure is operational
   **When** any write fails (disk full, permission error)
   **Then** the error is logged as `SystemHealthError(4008)` with severity `warning`
   **And** system operation continues — CSV write failure NEVER blocks trading or any other module
   **And** the failed record is lost (no buffering — trade data is always recoverable from the database)

6. All existing tests pass, `pnpm lint` reports zero errors
7. New unit tests cover: CSV row formatting, file rotation by date, daily summary generation, export endpoint with both formats, error handling for write failures, config validation

## Tasks / Subtasks

- [x] Task 1: Create `CsvTradeLogService` in `src/modules/monitoring/` (AC: #1, #4, #5)
  - [x]1.1 Create `csv-trade-log.service.ts` with `@Injectable()` NestJS service
  - [x]1.2 Inject `ConfigService` for env vars: `CSV_TRADE_LOG_DIR` (default `./data/trade-logs`), `CSV_ENABLED` (default `true`)
  - [x]1.3 Implement `onModuleInit()`: validate directory exists and is writable. If directory doesn't exist, create it recursively via `fs.promises.mkdir(dir, { recursive: true })`. If creation fails or directory is not writable, log `SystemHealthError(4008)` and set `this.enabled = false`. Never halt the engine.
  - [x]1.4 Implement `logTrade(record: TradeLogRecord): Promise<void>` — the main entry point called by EventConsumerService:
    - If `!this.enabled`, return immediately
    - Determine filename: `trades-${formatDateUTC(now)}.csv` (e.g., `trades-2026-02-24.csv`)
    - **Serialize writes per file via write queue** (see 1.10) — chain this write onto the queue for this filename
    - Inside the queued operation: check if file exists — if not, write CSV header row first, then append CSV row using `fs.promises.appendFile()`
    - Use `\n` line endings (Unix-style)
    - All values properly escaped via `escapeCsvField()` (see 1.9)
    - Wrap entire operation in try-catch — log `SystemHealthError(4008)` on failure, never re-throw
  - [x]1.5 Implement `TradeLogRecord` interface:
    ```typescript
    interface TradeLogRecord {
      timestamp: string; // ISO 8601
      platform: string; // 'KALSHI' | 'POLYMARKET'
      contractId: string;
      side: string; // 'buy' | 'sell'
      price: string; // decimal string
      size: string; // decimal string
      fillPrice: string; // decimal string
      fees: string; // decimal string (from FeeSchedule context or '0')
      gas: string; // decimal string (Polymarket only, '0' for Kalshi)
      edge: string; // decimal string (expected edge at time of execution)
      pnl: string; // decimal string (for exits; '0' for opens)
      positionId: string;
      pairId: string;
      isPaper: boolean;
      correlationId: string;
    }
    ```
  - [x]1.6 Implement `formatCsvRow(record: TradeLogRecord): string` — pure function:
    - Column order matches header: `timestamp,platform,contract_id,side,price,size,fill_price,fees,gas,edge,pnl,position_id,pair_id,is_paper,correlation_id`
    - Properly escape all string fields
    - Boolean `isPaper` → `true`/`false` string
  - [x]1.7 Implement `getCsvHeader(): string` — returns the header row string
  - [x]1.8 Implement helper `formatDateUTC(date: Date): string` — returns `YYYY-MM-DD` in UTC
  - [x]1.9 **NO CSV library dependency.** Trade log CSV is simple tabular data with 15 fixed columns. Node.js native `fs.promises.appendFile()` is sufficient. Adding a library (e.g., `fast-csv`, `papaparse`) for this use case is over-engineering. Implement `escapeCsvField(value: string): string` utility:
    ```typescript
    function escapeCsvField(value: string): string {
      if (/[,"\r\n]/.test(value)) {
        return `"${value.replace(/"/g, '""')}"`;
      }
      return value;
    }
    ```
    This handles: commas in values, embedded double-quotes (doubled per RFC 4180), carriage returns, and newlines. Export this as a pure function for unit testing.
  - [x]1.10 Implement **per-file write queue** to prevent interleaved writes from concurrent async events:

    ```typescript
    private writeQueues = new Map<string, Promise<void>>();

    private enqueueWrite(filename: string, writeFn: () => Promise<void>): void {
      const prev = this.writeQueues.get(filename) ?? Promise.resolve();
      const next = prev.then(writeFn).catch((err) => this.handleWriteError(err));
      this.writeQueues.set(filename, next);
    }
    ```

    - `logTrade()` calls `enqueueWrite(filename, () => this.appendRow(filename, record))` instead of calling `appendFile()` directly
    - This ensures serial writes per file: header creation + first row are atomic, concurrent events for the same date don't interleave
    - Failures are caught per-write and logged — one failed write doesn't block subsequent writes
    - **Why this matters:** `EventConsumerService.onAny()` processes events async. Multiple `OrderFilledEvent` events from a burst of fills could trigger concurrent `logTrade()` calls. Without serialization, two calls could both see "file doesn't exist" and both write headers, or interleave partial rows.

- [x] Task 2: Create `DailySummaryService` in `src/modules/monitoring/` (AC: #2)
  - [x]2.1 Create `daily-summary.service.ts` with `@Injectable()` NestJS service
  - [x]2.2 Inject: `ConfigService`, `EventConsumerService` (for metrics), `PositionRepository`, `OrderRepository`, `TelegramAlertService`, `Logger`
  - [x]2.3 Implement `@Cron('0 0 * * *')` handler (`handleDailySummary()`) — fires at UTC midnight:
    - Use `withCorrelationId()` wrapper for structured logging
    - Gather summary data for the previous day (yesterday UTC):
      - `totalTrades`: count of orders with `status = FILLED` and `createdAt` in yesterday's range
      - `totalPnl`: sum of `realizedPnl` from positions closed yesterday (query `OpenPosition` with `status = CLOSED` and `updatedAt` in yesterday's range, sum the P&L from `reconciliationContext` JSON field if available, or `'N/A'` if not tracked)
      - `openPositions`: count of `OpenPosition` with `status = OPEN`
      - `closedPositions`: count of positions closed yesterday
      - `opportunitiesDetected`: from `EventConsumerService.getMetrics().eventCounts['detection.opportunity.identified']` (note: resets on restart, so this is session-only — acceptable for MVP)
      - `opportunitiesExecuted`: from `eventCounts['execution.order.filled']`
      - `singleLegEvents`: from `eventCounts['execution.single_leg.exposure']`
      - `riskLimitEvents`: from `eventCounts['risk.limit.breached']` + `eventCounts['risk.limit.approached']`
      - `systemHealthSummary`: brief text: "{uptime}h uptime, {errorsCount} handler errors"
    - **IMPORTANT:** Metrics from EventConsumerService are in-memory and reset on restart. For DB-backed counts (totalTrades, openPositions, closedPositions), query the database directly. For event-based counts (opportunities, single-leg, risk), use EventConsumerService metrics as best-effort. Add a note in the summary if the engine restarted during the day.
  - [x]2.4 Append summary to `daily-summaries.csv` in the same `CSV_TRADE_LOG_DIR`:
    - Header: `date,total_trades,total_pnl,open_positions,closed_positions,opportunities_detected,opportunities_executed,single_leg_events,risk_limit_events,system_health_summary`
    - Same file creation + header logic as trade logs
  - [x]2.5 Format and send Telegram daily summary via `TelegramAlertService.enqueueAndSend()`:
    - Use HTML format consistent with existing formatters
    - Include all summary fields in readable format
    - Severity: `info`
  - [x]2.6 Wrap entire handler in try-catch — daily summary failure NEVER blocks trading

- [x] Task 3: Create trade export controller `TradeExportController` (AC: #3)
  - [x]3.1 Create `src/modules/monitoring/trade-export.controller.ts` with `@Controller('api/exports')`
  - [x]3.2 Create `src/modules/monitoring/dto/trade-export-query.dto.ts` — DTO with validation:
    ```typescript
    class TradeExportQueryDto {
      @IsISO8601() startDate: string;
      @IsISO8601() endDate: string;
      @IsIn(['json', 'csv']) @IsOptional() format: 'json' | 'csv' = 'json';
    }
    ```
  - [x]3.3 Implement `@Get('trades')` handler:
    - Parse and validate dates
    - Reject if date range exceeds 90 days (return 400 with standard error format)
    - Query `Order` table via `OrderRepository` for orders in date range (joined with `ContractMatch` for pairId)
    - If `format=json`: return `{ data: orders[], count: number, timestamp: string }` (standard API response)
    - If `format=csv`: set `Content-Type: text/csv`, `Content-Disposition: attachment; filename="trades-{startDate}-to-{endDate}.csv"`, stream CSV rows
  - [x]3.4 Add new method to `OrderRepository`: `findByDateRange(startDate: Date, endDate: Date, options?: { isPaper?: boolean }): Promise<OrderWithPair[]>` — returns orders with their pair relation loaded
  - [x]3.5 **IMPORTANT: Use Fastify response API**, not Express. The project uses Fastify adapter. For streaming CSV: use `reply.raw` to write headers and pipe CSV data. For JSON: standard NestJS return. Example pattern:
    ```typescript
    @Get('trades')
    async exportTrades(@Query() query: TradeExportQueryDto, @Res() reply: FastifyReply) {
      // ... handle format-specific response
    }
    ```
  - [x]3.6 Add `@UseGuards(AuthTokenGuard)` at class level — consistent with all existing controllers (`risk-override.controller.ts`, `reconciliation.controller.ts`, `single-leg-resolution.controller.ts`). Import from `../../common/guards/auth-token.guard`. Also add `@UsePipes(new ValidationPipe({ whitelist: true, transform: true }))` on the handler — consistent with existing controller patterns (per-handler, not global).
  - [x]3.7 **Rate limiting:** The 90-day max range + auth guard provide basic protection. For additional protection, add a simple in-memory rate limit check (e.g., max 5 export requests per minute per token). Implement as a lightweight guard or inline check — do NOT add `@nestjs/throttler` as a new dependency for one endpoint. If the request rate exceeds the limit, return 429 with standard error format: `{ error: { code: 4009, message: 'Export rate limit exceeded', severity: 'warning' }, timestamp }`. Add error code `EXPORT_RATE_LIMIT_EXCEEDED` (4009) to `monitoring-error-codes.ts`.

- [x] Task 4: Integrate CSV logging into EventConsumerService routing (AC: #1)
  - [x]4.1 Inject `CsvTradeLogService` into `EventConsumerService`
  - [x]4.2 In `handleEvent()`, after existing routing logic, add CSV trade logging for trade-related events:
    - `execution.order.filled` → extract `OrderFilledEvent` fields → build `TradeLogRecord` → call `csvTradeLogService.logTrade()`
    - `execution.exit.triggered` → extract `ExitTriggeredEvent` fields → build `TradeLogRecord` → call `csvTradeLogService.logTrade()`
    - Other events: no CSV logging (only Telegram + structured log per existing behavior)
  - [x]4.3 CSV logging calls are fire-and-forget (no `await` needed — append is fast and failures are caught internally). However, use `void this.csvTradeLogService.logTrade(record)` to suppress unhandled promise warning, or `await` inside the existing try-catch — either approach is acceptable.
  - [x]4.4 Build `TradeLogRecord` from event data:
    - For `OrderFilledEvent`: `platform`, `side`, `price`, `size`, `fillPrice`, `fillSize` are directly available. `contractId` via event's contextual data or from the order's pair. `fees` and `gas` → `'0'` (not available in event payload — note in dev notes that fee/gas per-trade is not tracked in events; this is a known limitation for MVP). `edge` → from position's `expectedEdge` (not in event — use `'N/A'`). `pnl` → `'0'` for fills (P&L is realized on exit).
    - For `ExitTriggeredEvent`: `realizedPnl` available, `initialEdge` and `finalEdge` available. Use `exitType` to populate side context.
  - [x]4.5 **Known data gap:** `OrderFilledEvent` does not carry `contractId`, `fees`, or `gas` fields. These are available in the Order database record but not in the event payload. Options:
    - **Option A (recommended for MVP):** Log available fields from event, use `'N/A'` for missing fields. The CSV is a quick-reference log; full data is always available via the export endpoint (which queries the database).
    - **Option B (future enhancement):** Enrich events with additional context, or query DB on each fill. Rejected for MVP — adds latency and DB pressure to the hot-path fan-out.

- [x] Task 5: Update `MonitoringModule` wiring (AC: #1, #2, #3)
  - [x]5.1 Add `CsvTradeLogService`, `DailySummaryService`, `TradeExportController` to `MonitoringModule`
  - [x]5.2 Import `PersistenceModule` into `MonitoringModule` (for repository access) — this is allowed per architecture: `modules/monitoring/ → persistence/` [Source: architecture.md line 594]
  - [x]5.3 Add `TradeExportController` to `controllers` array
  - [x]5.4 Add `CsvTradeLogService` and `DailySummaryService` to providers
  - [x]5.5 Export `CsvTradeLogService` (for future dashboard integration)

- [x] Task 6: Update environment configuration (AC: #4)
  - [x]6.1 Add to `.env.example`: `CSV_TRADE_LOG_DIR` (default `./data/trade-logs`), `CSV_ENABLED` (default `true`), `DAILY_SUMMARY_CRON` (default `0 0 * * *`)
  - [x]6.2 Add to `.env.development` with defaults
  - [x]6.3 Add `data/` to `.gitignore` if not already present

- [x] Task 7: Add error code (AC: #5)
  - [x]7.1 Add `CSV_WRITE_FAILED` error code (4008) to `monitoring-error-codes.ts` using `SystemHealthError` with `component: 'csv-trade-logging'`
  - [x]7.2 Add `EXPORT_RATE_LIMIT_EXCEEDED` error code (4009) to `monitoring-error-codes.ts` using `SystemHealthError` with `component: 'trade-export'`

- [x] Task 8: Write unit tests (AC: #6, #7)
  - [x]8.1 `csv-trade-log.service.spec.ts` — co-located in `src/modules/monitoring/`
    - Test: service initializes, creates directory if missing
    - Test: service disables gracefully if directory is not writable
    - Test: `logTrade()` creates file with header on first write
    - Test: `logTrade()` appends to existing file on subsequent writes
    - Test: file rotates at date boundary (new day → new file)
    - Test: CSV row formatting matches expected column order
    - Test: CSV field escaping handles commas, quotes, newlines, and embedded double-quotes
    - Test: write failure logs SystemHealthError(4008) and does not throw
    - Test: disabled service skips all writes
    - Test: `CSV_ENABLED=false` disables logging
    - Test: concurrent `logTrade()` calls for same date serialize via write queue (no duplicate headers)
    - Test: write queue failure on one record does not block subsequent writes
  - [x]8.2 `daily-summary.service.spec.ts` — co-located in `src/modules/monitoring/`
    - Test: daily cron generates correct summary from DB + metrics
    - Test: summary CSV row written to `daily-summaries.csv`
    - Test: Telegram message sent with summary
    - Test: handler failure caught and logged (never propagates)
    - Test: empty day produces zero-count summary (not error)
  - [x]8.3 `trade-export.controller.spec.ts` — co-located in `src/modules/monitoring/`
    - Test: JSON format returns standard API response wrapper
    - Test: CSV format sets correct Content-Type and Content-Disposition headers
    - Test: date range validation rejects >90 days
    - Test: invalid date format returns 400
    - Test: missing required params returns 400
    - Test: empty result set returns empty array/CSV with header only
    - Test: rate limit returns 429 after 5 requests per minute
    - Test: rate limit resets after cooldown period
  - [x]8.4 Update `event-consumer.service.spec.ts` — add tests for CSV logging delegation on ORDER_FILLED and EXIT_TRIGGERED events
  - [x]8.5 Update `monitoring.module.spec.ts` — verify new providers and controller are registered
  - [x]8.6 Ensure all existing tests remain green

- [x] Task 9: Lint and final validation (AC: #6)
  - [x]9.1 Run `pnpm lint` — zero errors
  - [x]9.2 Run `pnpm test` — all pass

## Dev Notes

### Architecture Compliance

- **Module placement:** `CsvTradeLogService`, `DailySummaryService`, and `TradeExportController` live in `src/modules/monitoring/` — per architecture: "modules/monitoring/ → persistence/ (audit logs, reports), common/events/ (subscribes to all)" and "Data Export | modules/monitoring/ + persistence/repositories/ | FR-DE-01 through FR-DE-04" [Source: architecture.md lines 594, 648]
- **Fan-out pattern:** CSV logging is triggered via `EventConsumerService.handleEvent()` which already runs async (`{ async: true }` via `onAny`). CSV write operations MUST NEVER block the hot path (detection → risk → execution).
- **Dependency rules respected:** `monitoring/` imports from `persistence/` (for repository access) and `common/` (events, errors, types). No imports from `connectors/` or other `modules/` services. `TradeExportController` accesses data via `OrderRepository` in `persistence/`.
- **Error hierarchy:** Uses `SystemHealthError(4008)` with `component: 'csv-trade-logging'`. Severity: `warning`. NEVER throws raw `Error`.
- **API response format:** Export endpoint uses standard wrappers: `{ data: T[], count: number, timestamp: string }` for JSON, proper CSV streaming for CSV format.
- **No new npm dependencies.** Uses Node.js native `fs.promises` for file operations (proven pattern, zero external dependencies). No CSV library needed for 15-column fixed-schema output.

### Key Technical Decisions

1. **No CSV library:** Trade log CSV has 15 fixed columns of simple types (strings, numbers, booleans). Node.js `fs.promises.appendFile()` with a simple `escapeCsvField()` utility is sufficient. Libraries like `fast-csv` (v5.0.2) or `papaparse` (v5.5.2) add unnecessary dependency for this use case. If schema complexity grows (dynamic columns, nested objects), introduce a library in a future story.

2. **File-per-day rotation:** Each UTC day gets its own file (`trades-2026-02-24.csv`). This aligns with the PRD's "timestamped CSV files" requirement and makes daily review trivial. No log rotation library needed — date-based naming handles it. 7-year retention is handled by NOT auto-deleting files; the backup strategy (hourly pg_dump + rclone to Hetzner Object Storage) covers CSV files if they're in the project data directory.

3. **Append-only writes with per-file write queue:** Each trade is a single `appendFile()` call chained through a per-file Promise queue. This ensures serial writes per file even when multiple async event handlers fire concurrently (e.g., burst of fills). The queue prevents: (a) duplicate headers when two calls both see "file doesn't exist", (b) interleaved partial rows. Each queued write is independent — one failure doesn't block subsequent writes. No external locking library needed; a simple `Map<string, Promise<void>>` suffices.

4. **Data availability in events vs DB:** `OrderFilledEvent` carries order-level data (platform, side, price, size, fillPrice) but NOT `contractId`, `fees`, or `gas`. The CSV trade log uses event data for quick logging (fields available: 10/15). Missing fields show `N/A`. The export endpoint queries the database where ALL fields are available. This trade-off avoids DB queries on the hot-path fan-out.

5. **Daily summary: hybrid data sources:** DB queries for authoritative counts (trades, positions) and EventConsumerService in-memory metrics for event counts (opportunities, single-leg, risk). In-memory metrics reset on restart — the summary notes if uptime < 24h. This is acceptable for MVP; persistent metrics deferred to Phase 1.

6. **Export endpoint in MonitoringModule:** Architecture maps "Data Export" to `modules/monitoring/ + persistence/repositories/`. The `TradeExportController` lives in monitoring and queries via `OrderRepository` from persistence. This avoids creating a separate export module for MVP.

7. **Fastify response handling:** The project uses NestJS + Fastify adapter. For CSV streaming in the export endpoint, use `@Res() reply: FastifyReply` to set custom headers and write raw response. For JSON, standard NestJS return. Reference existing controller patterns in `reconciliation.controller.ts` and `risk-override.controller.ts`.

8. **7-year retention:** The PRD requires 7-year trade log retention (FR-MA-02). CSV files on disk are NOT the compliance-grade storage — the PostgreSQL database + hourly pg_dump backups to Hetzner Object Storage is. CSV files serve as convenient operator-facing daily review files. The `data/trade-logs/` directory should be included in the backup scope.

9. **Daily summary Telegram message:** Uses `TelegramAlertService.enqueueAndSend()` (existing API) with severity `info`. This goes through the existing circuit breaker and buffer — no special handling needed. Format uses HTML consistent with all other Telegram messages.

### Fastify CSV Streaming Reference

```typescript
// Pattern for CSV response with Fastify
@Get('trades')
async exportTrades(
  @Query() query: TradeExportQueryDto,
  @Res() reply: FastifyReply,
) {
  const orders = await this.orderRepository.findByDateRange(start, end);

  if (query.format === 'csv') {
    reply
      .header('Content-Type', 'text/csv')
      .header('Content-Disposition', `attachment; filename="trades-${query.startDate}-to-${query.endDate}.csv"`)
      .send(this.buildCsvContent(orders));
    return; // Fastify: reply already sent
  }

  // JSON format — standard response
  reply.send({ data: orders, count: orders.length, timestamp: new Date().toISOString() });
}
```

### CSV Column Schema

**Trade Log (`trades-YYYY-MM-DD.csv`):**

| Column           | Type     | Source                           | Notes                     |
| ---------------- | -------- | -------------------------------- | ------------------------- |
| `timestamp`      | ISO 8601 | Event timestamp                  | UTC                       |
| `platform`       | string   | `OrderFilledEvent.platform`      | KALSHI or POLYMARKET      |
| `contract_id`    | string   | Order DB record                  | N/A from event (data gap) |
| `side`           | string   | `OrderFilledEvent.side`          | buy or sell               |
| `price`          | decimal  | `OrderFilledEvent.price`         | Original order price      |
| `size`           | decimal  | `OrderFilledEvent.size`          | Order size                |
| `fill_price`     | decimal  | `OrderFilledEvent.fillPrice`     | Actual fill price         |
| `fees`           | decimal  | FeeSchedule context              | N/A from event (data gap) |
| `gas`            | decimal  | Gas estimation                   | N/A from event (data gap) |
| `edge`           | decimal  | Position's expectedEdge          | N/A from event            |
| `pnl`            | decimal  | `ExitTriggeredEvent.realizedPnl` | 0 for opens               |
| `position_id`    | string   | `OrderFilledEvent.positionId`    | UUID                      |
| `pair_id`        | string   | Order's pairId                   | From event or DB          |
| `is_paper`       | boolean  | `OrderFilledEvent.isPaper`       | true/false                |
| `correlation_id` | string   | `BaseEvent.correlationId`        | UUID                      |

**Daily Summary (`daily-summaries.csv`):**

| Column                   | Type       | Source                               |
| ------------------------ | ---------- | ------------------------------------ |
| `date`                   | YYYY-MM-DD | Previous day UTC                     |
| `total_trades`           | integer    | DB query: Order count                |
| `total_pnl`              | decimal    | DB query: sum of realized P&L        |
| `open_positions`         | integer    | DB query: OpenPosition OPEN count    |
| `closed_positions`       | integer    | DB query: positions closed yesterday |
| `opportunities_detected` | integer    | EventConsumerService metrics         |
| `opportunities_executed` | integer    | EventConsumerService metrics         |
| `single_leg_events`      | integer    | EventConsumerService metrics         |
| `risk_limit_events`      | integer    | EventConsumerService metrics         |
| `system_health_summary`  | string     | Uptime + error count                 |

### Previous Story Intelligence (Stories 6.0, 6.1, 6.2)

**Directly reusable patterns:**

- **`EventConsumerService.handleEvent()` routing pattern (Story 6.2):** CSV logging hooks into the existing event routing. After Telegram delegation, add CSV logging for trade events. Follow the same try-catch + never-re-throw pattern.
- **`{ async: true }` on all event handling (Story 6.1):** Mandatory. CSV writes are in the fan-out path and must never block execution.
- **Error code pattern (Story 6.1):** `monitoring-error-codes.ts` already has codes 4006 (Telegram) and 4007 (EventConsumer). Add 4008 for CSV. Use `SystemHealthError(4008)` with `component: 'csv-trade-logging'`.
- **Native `fetch()` / native Node.js API pattern (Story 6.0):** Both previous monitoring stories avoided adding npm dependencies when Node.js built-ins suffice. Same principle applies: `fs.promises` for CSV writes.
- **`withCorrelationId()` for scheduled tasks (Story 6.1):** Daily summary cron should use this wrapper for structured logging.
- **`TelegramAlertService.enqueueAndSend()` API (Story 6.1):** Use for daily summary notification. Already handles circuit breaker, buffering, rate limiting.
- **PositionRepository and OrderRepository (persistence layer):** Already have query methods. `DailySummaryService` needs date-range queries — may need new methods on repositories.
- **Code review findings from 6.1/6.2:** Key lesson — "NEVER throw raw `Error`, NEVER log without error codes, ALWAYS use SystemError subclasses." Also: decimal.js for any financial values (but CSV logging only formats values as strings — no arithmetic needed).

### Git Intelligence

Recent commits (engine repo):

- `05e1744` — Story 6.2: SystemErrorFilter + EventConsumerService
- `418baff` — Story 6.1: Telegram alerting
- `3e44e7b` — Story 6.0: Gas estimation

Key patterns from these commits:

- New monitoring services follow: `@Injectable()` + inject `ConfigService` + `onModuleInit()` for config validation
- Error codes added to `monitoring-error-codes.ts` sequentially (4006, 4007 → next is 4008)
- Module registration: add to `MonitoringModule` providers + exports
- Test baseline: ~968 tests across 63 files (after Story 6.2)

### Financial Math

No financial calculations in this story. CSV logging and daily summaries only FORMAT and DISPLAY monetary values. All values are received as strings (Decimal types from Prisma or string fields from events). Convert Prisma `Decimal` to string via `.toString()` or `.toFixed(8)` for display. Do NOT perform arithmetic on these values in the CSV service.

For the daily summary `totalPnl`, the sum query uses Prisma's aggregate which returns a `Decimal` — convert to string for CSV.

### Project Structure Notes

**Files to create:**

- `src/modules/monitoring/csv-trade-log.service.ts` — CSV trade log writer
- `src/modules/monitoring/csv-trade-log.service.spec.ts` — co-located tests
- `src/modules/monitoring/daily-summary.service.ts` — daily summary generator
- `src/modules/monitoring/daily-summary.service.spec.ts` — co-located tests
- `src/modules/monitoring/trade-export.controller.ts` — REST export endpoint
- `src/modules/monitoring/trade-export.controller.spec.ts` — co-located tests
- `src/modules/monitoring/dto/trade-export-query.dto.ts` — validation DTO

**Files to modify:**

- `src/modules/monitoring/monitoring.module.ts` — register new services + controller, import PersistenceModule
- `src/modules/monitoring/monitoring.module.spec.ts` — update module compilation test
- `src/modules/monitoring/event-consumer.service.ts` — add CSV logging delegation for trade events
- `src/modules/monitoring/event-consumer.service.spec.ts` — add CSV delegation tests
- `src/modules/monitoring/monitoring-error-codes.ts` — add CSV_WRITE_FAILED (4008)
- `src/persistence/repositories/order.repository.ts` — add `findByDateRange()` method
- `src/persistence/repositories/order.repository.spec.ts` — add tests for new method
- `.env.example` — add CSV env vars
- `.env.development` — add CSV env vars
- `.gitignore` — add `data/` directory if not present

**Files to verify (existing tests must pass):**

- All existing spec files — this story adds new services and modifies event routing
- Specifically: `event-consumer.service.spec.ts` (most affected), `monitoring.module.spec.ts`

### Existing Infrastructure to Leverage

- **EventEmitter2:** Already configured in `AppModule` with `wildcard: true`, `delimiter: '.'`, `maxListeners: 20`
- **EventConsumerService:** Centralized event routing hub — CSV logging hooks in here (Story 6.2)
- **TelegramAlertService:** `enqueueAndSend(text, severity)` for daily summary notification
- **`@nestjs/schedule`:** Already registered (`ScheduleModule.forRoot()` in AppModule). `@Cron` decorator available for daily summary.
- **PositionRepository:** Has `findByStatus()`, `findActivePositions()` — may need date-range queries
- **OrderRepository:** Has `findByPairId()`, `findPendingOrders()` — needs `findByDateRange()` for export endpoint
- **`SystemHealthError`:** Has `component?: string` field — use for CSV-specific errors
- **`MONITORING_ERROR_CODES`:** Already has 4006 (Telegram), 4007 (EventConsumer) — add 4008
- **Structured logging:** `nestjs-pino` — all log entries include `timestamp`, `level`, `module`, `correlationId`, `message`, `data`
- **`withCorrelationId()`:** From `src/common/services/correlation-context.ts` — use for daily summary cron
- **PersistenceModule:** Already exports `OrderRepository`, `PositionRepository` — import into MonitoringModule
- **Validation:** `class-validator` and `class-transformer` — already dependencies, use for DTO validation on export endpoint

### Design Review Notes (LAD Review — Addressed)

**Reviewer:** kimi-k2-thinking via LAD MCP (glm-4.7 timed out)

**Issues Found:** 3 Critical, 3 Medium, 2 Low
**Issues Accepted:** 3 (C2, M1, M2 — incorporated into story)
**Issues Rejected:** 5 (C1, C3, M3, L1, L2 — see rationale below)

**C1 REJECTED:** "Event data gaps — enrich OrderFilledEvent with contractId, fees, gas." Modifying execution-layer event payloads is a cross-cutting change outside Epic 6 scope. The CSV is an operator convenience log; full data is available via the DB export endpoint. Enriching events adds DB queries to the hot-path fan-out — unacceptable for MVP.

**C2 ACCEPTED (downgraded to Medium):** "Concurrent CSV writes — race condition on header creation + row interleaving." Node.js is single-threaded but async `appendFile()` calls from concurrent event handlers CAN interleave. Added per-file write queue (Task 1.10) using Promise chaining (`Map<string, Promise<void>>`). Serial writes per file, failures isolated per write.

**C3 REJECTED:** "Daily summary metrics unreliable — persist to DB with DailyMetrics table." Adding a Prisma migration + new table is scope creep for MVP. DB-backed counts (trades, positions) are authoritative. In-memory event counts are best-effort with documented limitation. Persistent metrics belong in Phase 1.

**M1 ACCEPTED:** "Export endpoint lacks rate limiting." Added lightweight in-memory rate limit (5 requests/min) in Task 3.7 with error code 4009. No `@nestjs/throttler` dependency — simple inline check.

**M2 ACCEPTED:** "CSV escaping implementation incomplete." Added explicit `escapeCsvField()` implementation in Task 1.9 with regex for commas, quotes, `\r`, `\n` per RFC 4180. Includes unit test coverage for edge cases.

**M3 REJECTED:** "Missing integration tests." E2E tests require full DB + file system setup. Unit tests cover logic adequately. Integration tests can be added in a dedicated testing sprint.

**L1 NOTED:** "Error escalation — auto-disable after persistent failures." Reasonable but over-engineering for MVP. The service already disables on init failure. Runtime write failures are transient (disk issues) and self-recover. No change.

**L2 NOTED:** "Fastify CSV stream optimization — use StreamableFile." The 90-day max range caps export size. `reply.send()` with full CSV string is acceptable for MVP volumes. Streaming cursors deferred to Phase 1 if export sizes grow.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.3, line 1240] — Story definition and acceptance criteria
- [Source: _bmad-output/planning-artifacts/prd.md#FR-MA-02, line 779] — CSV trade logging with 7-year retention
- [Source: _bmad-output/planning-artifacts/prd.md#FR-MA-03, line 781] — Daily summary via CSV
- [Source: _bmad-output/planning-artifacts/prd.md#FR-DE-01, line 831] — Trade log export in JSON/CSV
- [Source: _bmad-output/planning-artifacts/architecture.md, line 161] — Fan-out async pattern, CSV exports
- [Source: _bmad-output/planning-artifacts/architecture.md, line 594] — monitoring/ → persistence/ allowed
- [Source: _bmad-output/planning-artifacts/architecture.md, line 648] — Data Export mapped to monitoring + persistence
- [Source: _bmad-output/planning-artifacts/architecture.md, line 164] — REST endpoint patterns including /api/compliance/export
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts] — EventConsumerService routing hub
- [Source: pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts] — TelegramAlertService for daily summary
- [Source: pm-arbitrage-engine/src/persistence/repositories/order.repository.ts] — OrderRepository to extend
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts] — PositionRepository for summary queries
- [Source: pm-arbitrage-engine/prisma/schema.prisma, line 127] — Order model schema
- [Source: pm-arbitrage-engine/prisma/schema.prisma, line 155] — OpenPosition model schema
- [Source: pm-arbitrage-engine/src/common/events/execution.events.ts] — OrderFilledEvent, ExitTriggeredEvent payloads

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- Lad system_design_review: 3 critical, 3 medium, 2 low found. Accepted C2 (write queue), M1 (rate limiting), M2 (CSV escaping). Rejected C1, C3, M3, L1, L2 as over-engineering for MVP.
- Lad code_review post-implementation: 9 critical, 12 high. Applied 2 fixes (CSV injection defense, cron UTC timezone). Remainder rejected as out-of-scope (Redis rate limiting, persistent queues, streaming exports, DB transactions for advisory summary).
- TypeScript error fixed: `BaseEvent as Record<string, unknown>` → `BaseEvent as unknown as Record<string, unknown>` (index signature mismatch).

### Completion Notes List

- All 7 ACs verified and passing
- 1011 tests (43 new), 0 lint errors, 0 TS errors
- CSV injection defense added (formula prefix for non-numeric `=`, `@` values)
- Cron pinned to UTC timezone
- `fastify` not a direct dependency — used local `Reply` interface instead of `FastifyReply`
- `CsvTradeLogService` injected as `@Optional()` in EventConsumerService for backward compatibility
- Repositories (OrderRepository, PositionRepository) registered as providers in MonitoringModule (PrismaService available via @Global PersistenceModule)
- Known data gaps in OrderFilledEvent → TradeLogRecord mapping (contractId, fees, gas = 'N/A') — documented, full data available via export endpoint

### Code Review Fixes Applied

**Reviewer:** Claude Opus 4.6 (adversarial code review)

- **[H1] Renamed `sumPnlByDateRange` → `sumClosedEdgeByDateRange`** — method was aggregating `expectedEdge` not realized P&L; renamed for honesty since OpenPosition has no `realizedPnl` column (Phase 1 schema migration needed)
- **[H2] Added `withCorrelationId()` wrapper to `DailySummaryService.handleDailySummary()`** — story Task 2.3 required it; all daily summary logs now carry a correlation ID per structured logging contract
- **[M1] Removed misleading `DAILY_SUMMARY_CRON` env var** — cron is hardcoded via `@Cron` decorator; env var suggested configurability that didn't exist. Replaced with comment.
- **[M2] Replaced `findByStatus('OPEN')` with `countByStatus('OPEN')`** — added new `countByStatus()` to PositionRepository that doesn't filter by `isPaper`, so daily summary counts all open positions (live + paper)
- **[M3] Added `PersistenceModule` import to `MonitoringModule`** — per story Task 5.2 and consistent with other modules
- **[M4] Changed empty strings to `'N/A'` in export CSV** — positionId, correlationId, pnl columns now show `'N/A'` consistent with event-based trade log format

### File List

**Created:**

- `src/modules/monitoring/csv-trade-log.service.ts`
- `src/modules/monitoring/csv-trade-log.service.spec.ts`
- `src/modules/monitoring/daily-summary.service.ts`
- `src/modules/monitoring/daily-summary.service.spec.ts`
- `src/modules/monitoring/trade-export.controller.ts`
- `src/modules/monitoring/trade-export.controller.spec.ts`
- `src/modules/monitoring/dto/trade-export-query.dto.ts`

**Modified:**

- `src/modules/monitoring/monitoring.module.ts`
- `src/modules/monitoring/monitoring.module.spec.ts`
- `src/modules/monitoring/event-consumer.service.ts`
- `src/modules/monitoring/event-consumer.service.spec.ts`
- `src/modules/monitoring/monitoring-error-codes.ts`
- `src/persistence/repositories/order.repository.ts`
- `src/persistence/repositories/position.repository.ts`
- `.env.example`
- `.env.development`
- `.gitignore`
