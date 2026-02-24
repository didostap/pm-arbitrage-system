# Story 6.5: Audit Trail & Tax Report Export

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want a tamper-evident audit trail and annual tax report export,
So that my legal counsel and tax advisor have exactly what they need without manual reconstruction.

## Acceptance Criteria

1. **Given** the `audit_logs` table needs to be created
   **When** this story is implemented
   **Then** a Prisma migration creates the `audit_logs` table with fields: `id` (UUID PK), `created_at` (TIMESTAMPTZ), `event_type` (VARCHAR), `module` (VARCHAR), `correlation_id` (VARCHAR), `details` (JSONB), `previous_hash` (VARCHAR(64)), `current_hash` (VARCHAR(64))
   **And** this story is the canonical owner of the `audit_logs` table — no other story creates it
   **And** indexes are created on `created_at`, `event_type`, and `correlation_id` for efficient querying

2. **Given** the `AuditLogService` is implemented
   **When** any auditable event occurs (trade, manual intervention, risk override, system error, reconciliation)
   **Then** the entry includes SHA-256 hash of the previous entry's hash + current data, creating a verifiable chain (NFR-S3)
   **And** the service is available for injection by all modules (monitoring hub from 6.2, reconciliation from 5.5, etc.)
   **And** audit log writes are serialized to maintain hash chain integrity (no concurrent writes)

3. **Given** Story 5.5's reconciliation logging used structured JSON as interim
   **When** Story 6.5 is deployed
   **Then** the reconciliation service is updated to route results through `AuditLogService` for tamper-evident persistence

4. **Given** the operator requests an annual tax report
   **When** they call `GET /api/exports/tax-report?year=2026`
   **Then** the system generates a CSV with: complete trade log, P&L summaries by platform and quarter, cost basis tracking, and transaction categorization (on-chain vs. regulated exchange) (FR-DE-02)
   **And** Polymarket trades are categorized as "on-chain" and Kalshi trades as "regulated-exchange"

5. **Given** the audit trail is queried
   **When** any entry's hash chain is verified
   **Then** the chain is provably intact (each entry's hash matches recalculation from previous entry + current data)
   **And** any tampering would break the chain and be detectable

6. All existing tests pass, `pnpm lint` reports zero errors
7. New unit tests cover: audit log creation with hash chaining, hash chain verification, `AuditLogService` serialized writes, `EventConsumerService` audit log integration, reconciliation service audit routing, tax report generation with platform categorization and quarterly P&L, export endpoint validation

## Tasks / Subtasks

- [x] Task 1: Create Prisma migration for `audit_logs` table (AC: #1)
  - [x]1.1 Add `AuditLog` model to `prisma/schema.prisma`:
    ```prisma
    model AuditLog {
      id            String   @id @default(uuid())
      createdAt     DateTime @default(now()) @map("created_at") @db.Timestamptz
      eventType     String   @map("event_type")
      module        String
      correlationId String?  @map("correlation_id")
      details       Json
      previousHash  String   @map("previous_hash") @db.VarChar(64)
      currentHash   String   @map("current_hash") @db.VarChar(64)

      @@index([createdAt], map: "idx_audit_logs_created_at")
      @@index([eventType], map: "idx_audit_logs_event_type")
      @@index([correlationId], map: "idx_audit_logs_correlation_id")
      @@map("audit_logs")
    }
    ```
  - [x]1.2 Run `pnpm prisma migrate dev --name add-audit-logs-table` to create the migration
  - [x]1.3 Run `pnpm prisma generate` to regenerate the Prisma client
  - [x]1.4 Verify the migration SQL creates the correct table structure with indexes

- [x] Task 2: Create `AuditLogRepository` in `src/persistence/repositories/` (AC: #1, #2, #5)
  - [x]2.1 Create `src/persistence/repositories/audit-log.repository.ts` — `@Injectable()` NestJS service:
    ```typescript
    @Injectable()
    export class AuditLogRepository {
      constructor(private readonly prisma: PrismaService) {}

      async create(data: Prisma.AuditLogCreateInput): Promise<AuditLog> {
        return this.prisma.auditLog.create({ data });
      }

      async findLast(): Promise<AuditLog | null> {
        return this.prisma.auditLog.findFirst({
          orderBy: { createdAt: 'desc' },
        });
      }

      async findByDateRange(startDate: Date, endDate: Date): Promise<AuditLog[]> {
        return this.prisma.auditLog.findMany({
          where: {
            createdAt: { gte: startDate, lte: endDate },
          },
          orderBy: { createdAt: 'asc' },
        });
      }

      async findByEventType(eventType: string, startDate?: Date, endDate?: Date): Promise<AuditLog[]> {
        return this.prisma.auditLog.findMany({
          where: {
            eventType,
            ...(startDate && endDate ? { createdAt: { gte: startDate, lte: endDate } } : {}),
          },
          orderBy: { createdAt: 'asc' },
        });
      }

      async findJustBefore(date: Date): Promise<AuditLog | null> {
        return this.prisma.auditLog.findFirst({
          where: { createdAt: { lt: date } },
          orderBy: { createdAt: 'desc' },
        });
      }
    }
    ```
  - [x]2.2 Follow the exact same pattern as `OrderRepository` — inject `PrismaService`, use `Prisma.AuditLogCreateInput` for typed input
  - [x]2.3 The `findLast()` method is critical for hash chaining — it retrieves the most recent entry's `currentHash` to use as `previousHash` for the next entry

- [x] Task 3: Create `AuditLogService` in `src/modules/monitoring/` (AC: #2, #5)
  - [x]3.1 Create `src/modules/monitoring/audit-log.service.ts` with `@Injectable()` NestJS service
  - [x]3.2 Inject: `AuditLogRepository`, `Logger`
  - [x]3.3 Implement hash chain logic using Node.js built-in `crypto.createHash('sha256')` (already used in `kalshi-websocket.client.ts` — no new dependency needed):
    ```typescript
    import { createHash } from 'crypto';

    private computeHash(previousHash: string, eventType: string, details: Record<string, unknown>, timestamp: string): string {
      const canonicalDetails = JSON.stringify(details, Object.keys(details).sort());
      const payload = previousHash + '|' + eventType + '|' + timestamp + '|' + canonicalDetails;
      return createHash('sha256').update(payload).digest('hex');
    }
    ```
  - [x]3.4 Genesis entry: when no previous entry exists, use `previousHash = '0'.repeat(64)` (64 zero characters — the conventional "null hash" for chain genesis)
  - [x]3.5 Implement write serialization via a Promise queue to ensure hash chain integrity:
    ```typescript
    private writeQueue: Promise<void> = Promise.resolve();
    private lastHash: string | null = null; // In-memory cache of last hash

    async append(entry: AuditLogEntry): Promise<void> {
      return new Promise((resolve, reject) => {
        this.writeQueue = this.writeQueue
          .then(async () => {
            await this.doAppend(entry);
            resolve();
          })
          .catch((err) => {
            this.handleWriteError(err);
            reject(err);
          });
      });
    }
    ```
  - [x]3.6 The `doAppend()` method:
    - If `this.lastHash` is null (first call after startup), fetch from DB via `auditLogRepository.findLast()` and cache the `currentHash`. If no entry exists, use genesis hash.
    - Compute `currentHash` from `previousHash + '|' + eventType + '|' + timestamp + '|' + JSON.stringify(details, sortedKeys)` (deterministic serialization with sorted keys and pipe delimiters)
    - Create entry via `auditLogRepository.create()`
    - Update `this.lastHash` cache
    - **Important:** The in-memory `lastHash` cache eliminates a DB read per write after startup. Thread safety is guaranteed by the Promise queue serialization.
  - [x]3.7 Define `AuditLogEntry` interface:
    ```typescript
    export interface AuditLogEntry {
      eventType: string;
      module: string;
      correlationId?: string;
      details: Record<string, unknown>;
    }
    ```
  - [x]3.8 Implement `verifyChain(startDate: Date, endDate: Date): Promise<ChainVerificationResult>`:
    ```typescript
    export interface ChainVerificationResult {
      valid: boolean;
      entriesChecked: number;
      brokenAtId?: string;
      brokenAtTimestamp?: string;
      expectedHash?: string;
      actualHash?: string;
    }
    ```
    - Fetch all entries in the date range (ordered by `createdAt ASC`)
    - For the first entry in the range, verify against its `previousHash` (may need the entry just before the range)
    - For each subsequent entry, recompute hash from `previous entry's currentHash + current entry data` and compare
    - Return result with first broken link if any
  - [x]3.9 Error handling: wrap all DB operations in try-catch. On failure, log `SystemHealthError(4010)` with `component: 'audit-log'`. Audit log write failure is `severity: 'critical'` — emit a high-priority event so the operator is notified that the tamper-evident chain may be compromised. But NEVER halt the engine — audit log failure must not block trading.
  - [x]3.10 Implement `onModuleInit()`: load the last hash from DB and cache it. This ensures the first `append()` call after restart doesn't need an extra DB query.

- [x] Task 4: Add error codes and events (AC: #2)
  - [x]4.1 Add to `MONITORING_ERROR_CODES` in `src/modules/monitoring/monitoring-error-codes.ts`:
    ```typescript
    /** Audit log DB write failed — hash chain may be compromised */
    AUDIT_LOG_WRITE_FAILED: 4010,
    /** Audit hash chain integrity check failed — tampering detected */
    AUDIT_HASH_CHAIN_BROKEN: 4011,
    ```
  - [x]4.2 Add to `EVENT_NAMES` in `src/common/events/event-catalog.ts`:
    ```typescript
    // [Story 6.5] Audit Events
    /** Emitted when audit log write fails */
    AUDIT_LOG_FAILED: 'monitoring.audit.write_failed',
    /** Emitted when hash chain integrity check fails */
    AUDIT_CHAIN_BROKEN: 'monitoring.audit.chain_broken',
    ```
  - [x]4.3 Create audit event classes in `src/common/events/monitoring.events.ts` (or add to existing monitoring events file if one exists):
    ```typescript
    export class AuditLogFailedEvent {
      constructor(
        public readonly error: string,
        public readonly eventType: string,
        public readonly module: string,
        public readonly timestamp: Date = new Date(),
      ) {}
    }

    export class AuditChainBrokenEvent {
      constructor(
        public readonly brokenAtId: string,
        public readonly expectedHash: string,
        public readonly actualHash: string,
        public readonly timestamp: Date = new Date(),
      ) {}
    }
    ```

- [x] Task 5: Integrate `AuditLogService` into `EventConsumerService` (AC: #2)
  - [x]5.1 Inject `AuditLogService` into `EventConsumerService` using `@Optional()` decorator (same pattern as `CsvTradeLogService` — backward compatible for testing):
    ```typescript
    constructor(
      // ... existing injections
      @Optional() private readonly auditLogService?: AuditLogService,
    ) {}
    ```
  - [x]5.2 In `handleEvent()`, after existing routing logic, add audit log entry for ALL events EXCEPT `monitoring.audit.*` (to prevent circular logging — audit failures must not trigger re-auditing):
    ```typescript
    // Audit trail — log ALL events for tamper-evident persistence
    // IMPORTANT: Skip monitoring.audit.* events to prevent infinite recursion
    if (this.auditLogService && !eventName.startsWith('monitoring.audit.')) {
      void this.auditLogService.append({
        eventType: eventName,
        module: this.extractModule(eventName), // e.g., 'execution' from 'execution.order.filled'
        correlationId: event?.correlationId,
        details: this.sanitizeEventForAudit(event),
      }).catch(() => {}); // Error already handled internally by AuditLogService
    }
    ```
  - [x]5.3 Implement `extractModule(eventName: string): string` — returns the first segment of the dot-notation event name (e.g., `'execution'` from `'execution.order.filled'`)
  - [x]5.4 Implement `sanitizeEventForAudit(event: unknown): Record<string, unknown>` — safely converts event payload to a plain object for JSON storage. Handle edge cases: circular references (shouldn't exist but defensive), Decimal objects (convert to string), Date objects (convert to ISO string). Use `JSON.parse(JSON.stringify(event))` as a simple deep-clone strategy, with try-catch fallback to `{ raw: String(event) }`.
  - [x]5.5 Audit log calls are fire-and-forget (`void` prefix) — audit log write failure must never block event routing. The `AuditLogService.append()` handles errors internally and emits alerts.

- [x] Task 6: Update reconciliation service to use `AuditLogService` (AC: #3)
  - [x]6.1 Add `AuditLogService` injection to `StartupReconciliationService` constructor:
    ```typescript
    constructor(
      // ... existing injections
      @Optional() private readonly auditLogService?: AuditLogService,
    ) {}
    ```
  - [x]6.2 In `reconcile()` completion (the method that produces the reconciliation report), add audit log call:
    ```typescript
    if (this.auditLogService) {
      void this.auditLogService.append({
        eventType: 'reconciliation.completed',
        module: 'reconciliation',
        correlationId,
        details: {
          positionsChecked: result.positionsChecked,
          discrepanciesFound: result.discrepancies.length,
          discrepancies: result.discrepancies,
          timestamp: new Date().toISOString(),
        },
      });
    }
    ```
  - [x]6.3 In `resolveDiscrepancy()` (operator resolution action), add audit log call with resolution context
  - [x]6.4 Keep existing `this.logger.log/error()` calls — they serve structured logging (pino). AuditLogService provides the tamper-evident persistence layer. Both are needed: pino for real-time observability, audit log for legal/compliance record.
  - [x]6.5 Update `ReconciliationModule` to import `MonitoringModule`:
    ```typescript
    @Module({
      imports: [ConnectorModule, RiskManagementModule, MonitoringModule, ...],
      // ...
    })
    ```
    **Circular dependency check:** `MonitoringModule` does NOT import `ReconciliationModule`, so no cycle exists. `MonitoringModule` exports `AuditLogService` → `ReconciliationModule` imports `MonitoringModule` → safe.

- [x] Task 7: Create tax report export endpoint (AC: #4)
  - [x]7.1 Create `src/modules/monitoring/dto/tax-report-query.dto.ts`:
    ```typescript
    export class TaxReportQueryDto {
      @Type(() => Number)
      @IsInt()
      @Min(2024)
      @Max(2100)
      year!: number;

      @IsIn(['csv'])
      @IsOptional()
      format: 'csv' = 'csv';
    }
    ```
  - [x]7.2 Add `GET /api/exports/tax-report` handler to existing `TradeExportController`:
    ```typescript
    @Get('tax-report')
    @UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
    async exportTaxReport(
      @Query() query: TaxReportQueryDto,
      @Res() reply: FastifyReply,
    ) { ... }
    ```
  - [x]7.3 The tax report handler queries:
    - **Complete trade log:** `OrderRepository.findByDateRange(yearStart, yearEnd)` — all orders for the year
    - **P&L by platform and quarter:** For each quarter (Q1-Q4) and each platform (KALSHI, POLYMARKET):
      - Query `PositionRepository` for positions closed in that quarter on that platform
      - Sum realized P&L (use `sumClosedEdgeByDateRange()` pattern from Story 6.3, or create a new `sumPnlByPlatformAndDateRange()` method)
    - **Cost basis tracking:** For each position, include entry prices and sizes. Cost basis = entry price × size. MVP: simple trade-by-trade tracking (no FIFO/LIFO — each arbitrage position is an independent pair).
    - **Transaction categorization:**
      - POLYMARKET → `"on-chain"` (blockchain-based CLOB)
      - KALSHI → `"regulated-exchange"` (CFTC-regulated)
  - [x]7.4 Tax report CSV columns:
    ```
    Section: TRADE LOG
    date,platform,transaction_type,contract_id,side,price,size,fill_price,fees,gas,cost_basis,proceeds,pnl,position_id,pair_id,is_paper,correlation_id

    Section: QUARTERLY P&L SUMMARY
    quarter,platform,total_trades,total_pnl,transaction_type

    Section: ANNUAL SUMMARY
    year,total_trades,total_pnl,kalshi_pnl,polymarket_pnl,kalshi_trades,polymarket_trades
    ```
  - [x]7.5 The CSV uses section headers (rows starting with `#` or blank separator lines) to delineate the three sections. This is a standard pattern for multi-section CSV reports. Include a disclaimer row at the top: `# DISCLAIMER: P&L figures are based on expected edge at trade entry, not realized gains. Consult tax advisor for official filings.`
  - [x]7.6 Set response headers: `Content-Type: text/csv`, `Content-Disposition: attachment; filename="${year}-tax-report.csv"`
  - [x]7.7 Rate limiting: reuse the existing in-memory rate limiter in `TradeExportController` (from Story 6.3). Both endpoints share the 5 req/min limit.
  - [x]7.8 **Financial math:** P&L aggregation queries return Prisma `Decimal`. Convert to string via `.toString()` for CSV output. Do NOT perform arithmetic in the controller — all aggregation is done in the repository/DB layer. If a new `sumPnlByPlatformAndDateRange()` method is needed, implement it in `PositionRepository`.
  - [x]7.9 **Known limitation (MVP):** The `OpenPosition` model has `expectedEdge` but no dedicated `realizedPnl` column (per Story 6.3 code review finding). P&L in the tax report uses `expectedEdge` from closed positions as a proxy. A dedicated `realizedPnl` column requires a schema migration deferred to Phase 1. Document this limitation in the response and code comments.

- [x] Task 8: Wire services into modules (AC: #2, #3)
  - [x]8.1 Add `AuditLogRepository` and `AuditLogService` to `MonitoringModule` providers
  - [x]8.2 Add `AuditLogService` to `MonitoringModule` exports (so `ReconciliationModule` and future modules can inject it)
  - [x]8.3 Update `ReconciliationModule` imports to include `MonitoringModule`
  - [x]8.4 **No circular dependency:** `MonitoringModule` does NOT import `ReconciliationModule`. Safe.

- [x] Task 9: Write unit tests (AC: #6, #7)
  - [x]9.1 `src/persistence/repositories/audit-log.repository.spec.ts`:
    - Test: creates audit log entry with all fields
    - Test: `findLast()` returns most recent entry
    - Test: `findByDateRange()` returns entries in ascending order
    - Test: `findByEventType()` filters correctly
    - Test: `findLast()` returns null when table is empty
  - [x]9.2 `src/modules/monitoring/audit-log.service.spec.ts`:
    - Test: first entry uses genesis hash (`'0'.repeat(64)`) as `previousHash`
    - Test: subsequent entries chain correctly (entry N's `previousHash` === entry N-1's `currentHash`)
    - Test: hash is deterministic (same inputs → same hash)
    - Test: changing any field produces a different hash
    - Test: hash is deterministic regardless of object key insertion order (sorted keys)
    - Test: concurrent `append()` calls are serialized (writes don't interleave)
    - Test: `onModuleInit()` loads last hash from DB
    - Test: write failure emits `AUDIT_LOG_FAILED` event and logs `SystemHealthError(4010)`
    - Test: write failure does not break serialization queue (subsequent writes still work)
    - Test: `verifyChain()` returns valid for intact chain
    - Test: `verifyChain()` detects tampered entry (modified details)
    - Test: `verifyChain()` detects missing entry (gap in chain)
  - [x]9.3 Update `src/modules/monitoring/event-consumer.service.spec.ts`:
    - Test: audit log `append()` called for every event type
    - Test: `extractModule()` extracts first dot-notation segment
    - Test: `sanitizeEventForAudit()` converts event to plain object
    - Test: audit log failure does not block event routing
    - Test: works when `AuditLogService` is not injected (`@Optional()`)
    - Test: `monitoring.audit.*` events are NOT audited (circular logging prevention)
  - [x]9.4 `src/modules/monitoring/trade-export.controller.spec.ts` (update existing):
    - Test: tax report endpoint returns CSV with correct headers
    - Test: tax report includes trade log section, quarterly P&L section, annual summary section
    - Test: Polymarket trades categorized as "on-chain"
    - Test: Kalshi trades categorized as "regulated-exchange"
    - Test: invalid year returns 400
    - Test: rate limit applies to tax report endpoint
  - [x]9.5 Update reconciliation service tests:
    - Test: `AuditLogService.append()` called on reconciliation completion
    - Test: `AuditLogService.append()` called on discrepancy resolution
    - Test: reconciliation works when `AuditLogService` is not injected
  - [x]9.6 Update `monitoring.module.spec.ts` — verify `AuditLogService` and `AuditLogRepository` are registered
  - [x]9.7 Ensure all existing tests remain green

- [x] Task 10: Lint and final validation (AC: #6)
  - [x]10.1 Run `pnpm lint` — zero errors
  - [x]10.2 Run `pnpm test` — all pass

## Dev Notes

### Architecture Compliance

- **Module placement:** `AuditLogService` lives in `src/modules/monitoring/` per architecture: "monitoring/ → persistence/ (audit logs, reports)" [Source: architecture.md line 594] and the explicit listing of `audit-log.service.ts` in the monitoring module [Source: architecture.md line 522].
- **Repository placement:** `AuditLogRepository` lives in `src/persistence/repositories/` per architecture: "audit-log.repository.ts" listed in the persistence layer [Source: architecture.md line 569].
- **Hash chain per architecture:** "Append-only table with SHA-256 cryptographic chaining. Each audit log entry includes hash of previous entry, creating a verifiable chain satisfying PRD's 'tamper-evident logging' requirement (NFR-S3)" [Source: architecture.md line 138].
- **Fan-out pattern respected:** Audit log writes are fire-and-forget from `EventConsumerService`. They MUST NOT block the hot path (detection → risk → execution). AuditLogService handles serialization internally.
- **Dependency rules:** `monitoring/` → `persistence/` (allowed), `monitoring/` → `common/` (allowed). `ReconciliationModule` → `MonitoringModule` (new but no cycle — MonitoringModule does not import ReconciliationModule).
- **Error hierarchy:** Uses `SystemHealthError` (4010, 4011) — audit failures are system health concerns, not execution or risk errors.

### Key Technical Decisions

1. **SHA-256 hash chain algorithm with deterministic serialization:**
   ```
   canonicalDetails = JSON.stringify(details, sortedKeys)  // Sorted keys for determinism
   payload = previousHash + '|' + eventType + '|' + timestamp.toISOString() + '|' + canonicalDetails
   currentHash = SHA256(payload).hex()
   genesis: previousHash = '0'.repeat(64)
   ```
   Uses Node.js built-in `crypto.createHash('sha256')` — already used in `kalshi-websocket.client.ts` for HMAC authentication. Zero new dependencies. **Critical:** `JSON.stringify()` does not guarantee key order across JS engines. Using `JSON.stringify(obj, Object.keys(obj).sort())` ensures deterministic serialization. For deeply nested objects, implement a recursive sorted-keys serializer. Pipe (`|`) delimiters prevent ambiguous field concatenation that could enable collision attacks.

2. **Write serialization via Promise queue:** The audit log MUST be serialized to maintain hash chain integrity. Two concurrent writes would both read the same `previousHash` and produce entries that don't chain correctly. The Promise queue pattern (same as `CsvTradeLogService`'s per-file write queue from Story 6.3) ensures serial execution. An in-memory `lastHash` cache eliminates the DB read per write — only the initial startup requires a `findLast()` query.

3. **`@Optional()` injection pattern:** Both `EventConsumerService` and `StartupReconciliationService` inject `AuditLogService` as `@Optional()`. This ensures:
   - Existing tests don't break (they don't need to mock `AuditLogService`)
   - The service degrades gracefully if audit logging is unavailable
   - Follows the same pattern as `CsvTradeLogService` in `EventConsumerService` (Story 6.3)

4. **Audit log captures ALL events, not just critical:** The architecture states "all state changes are already logged explicitly through the Monitoring module" and "Hash chain provides cryptographic proof of ordering and completeness for legal review." Completeness means every event, not just critical ones. The `EventConsumerService.handleEvent()` processes all events — each one gets an audit entry.

5. **Tax report P&L uses `expectedEdge` as proxy:** The `OpenPosition` model lacks a dedicated `realizedPnl` column. Story 6.3's code review renamed `sumPnlByDateRange` → `sumClosedEdgeByDateRange` for honesty. The tax report clearly labels this as "expected edge" P&L, not realized P&L. A schema migration to add `realizedPnl` is deferred to Phase 1.

6. **Tax report sections in single CSV:** The CSV contains three sections separated by blank lines and section headers. This is a pragmatic choice for MVP — a tax advisor can easily parse this in Excel. Alternative: three separate CSV files or a ZIP download (over-engineering for MVP).

7. **Transaction categorization is platform-based:** Polymarket = on-chain (blockchain-based CLOB on Polygon), Kalshi = regulated-exchange (CFTC-regulated DCM). This categorization is fixed per platform, not per trade. Simple and accurate for current two-platform setup.

8. **Circular logging prevention:** `AuditLogService` emits `monitoring.audit.write_failed` and `monitoring.audit.chain_broken` events on failure. `EventConsumerService.handleEvent()` must skip `monitoring.audit.*` events to prevent infinite recursion (audit failure → event emitted → EventConsumer tries to audit → failure → event emitted → ...). The skip check is a simple `eventName.startsWith('monitoring.audit.')` guard.

9. **No `crypto.ts` utility file:** The architecture planned a `common/utils/crypto.ts` for "keystore decryption, audit log hash chaining." However, the hash computation is a 3-line function specific to audit logging. Creating a separate utility file for one function used by one service is unnecessary. Keep the hash logic in `AuditLogService`. If Phase 1 adds more crypto utilities, extract then.

### Compliance Check Placement — Audit Log in Event Flow

```
Any module emits domain event via EventEmitter2
  ↓ (async fan-out, { async: true })
EventConsumerService.handleEvent()
  ├── Severity classification
  ├── Telegram alert (if critical/warning/info-eligible)
  ├── CSV trade log (if trade event — Story 6.3)
  └── ★ AUDIT LOG ★ (ALL events — Story 6.5)
      ├── AuditLogService.append()
      │   ├── Serialized via Promise queue
      │   ├── Compute SHA-256 hash chain
      │   └── Write to audit_logs table
      └── Fire-and-forget (void) — never blocks routing
```

### Reconciliation Integration

```
StartupReconciliationService.reconcile()
  ├── ... existing reconciliation logic ...
  ├── this.logger.log(result)          ← KEEP (pino structured logging)
  └── this.auditLogService.append()    ← ADD (tamper-evident persistence)

StartupReconciliationService.resolveDiscrepancy()
  ├── ... existing resolution logic ...
  ├── this.logger.log(resolution)      ← KEEP
  └── this.auditLogService.append()    ← ADD
```

### Tax Report CSV Structure

```csv
# TRADE LOG
date,platform,transaction_type,contract_id,side,price,size,fill_price,fees,gas,cost_basis,proceeds,pnl,position_id,pair_id,is_paper,correlation_id
2026-01-15T10:30:00Z,KALSHI,regulated-exchange,KALSHI-BTC-100K,buy,0.65,100,0.65,0.01,0,65.00,0,0,pos-uuid,pair-uuid,false,corr-uuid
2026-01-15T10:30:01Z,POLYMARKET,on-chain,0xabc...def,sell,0.38,100,0.38,0,0.002,38.20,0,0,pos-uuid,pair-uuid,false,corr-uuid
...

# QUARTERLY P&L SUMMARY
quarter,platform,transaction_type,total_trades,total_pnl
Q1 2026,KALSHI,regulated-exchange,45,123.45
Q1 2026,POLYMARKET,on-chain,45,89.12
Q2 2026,KALSHI,regulated-exchange,52,156.78
...

# ANNUAL SUMMARY
year,total_trades,total_pnl,kalshi_pnl,polymarket_pnl,kalshi_trades,polymarket_trades
2026,194,502.35,280.23,222.12,97,97
```

### Previous Story Intelligence (Stories 6.0-6.4)

**Directly reusable patterns:**

- **`EventConsumerService.handleEvent()` routing pattern (Story 6.2):** Audit logging hooks into existing event routing. After Telegram + CSV delegation, add audit log for ALL events. Same fire-and-forget pattern.
- **`@Optional()` injection for new service (Story 6.3):** `CsvTradeLogService` is `@Optional()` in `EventConsumerService`. Follow same pattern for `AuditLogService`.
- **Promise queue serialization (Story 6.3):** `CsvTradeLogService` uses per-file `Map<string, Promise<void>>` write queue. Same serialization concept for audit log, but simpler — single queue since there's one chain.
- **Error code pattern (Stories 6.1-6.4):** `MONITORING_ERROR_CODES` already has 4006-4009. Add 4010, 4011.
- **`TradeExportController` export pattern (Story 6.3):** Existing controller with rate limiter, `@UseGuards(AuthTokenGuard)`, Fastify response handling. Tax report endpoint follows exact same pattern.
- **Repository pattern (all stories):** Inject `PrismaService`, use `Prisma.<Model>CreateInput` types, follow established naming.
- **`OrderRepository.findByDateRange()` (Story 6.3):** Tax report reuses this for complete trade log export.
- **`PositionRepository.sumClosedEdgeByDateRange()` (Story 6.3):** Tax report needs similar aggregation by platform and quarter.
- **Node.js `crypto.createHash('sha256')` (existing):** Already used in `kalshi-websocket.client.ts` for HMAC. No new dependency for SHA-256.

### Git Intelligence

Recent commits (engine repo):

- `a639988` — Story 6.4: Compliance validation & trade gating
- `6587379` — Story 6.3: CSV trade logging and daily summaries
- `05e1744` — Story 6.2: SystemErrorFilter + EventConsumerService
- `418baff` — Story 6.1: Telegram alerting
- `3e44e7b` — Story 6.0: Gas estimation

Key patterns:
- New services follow: `@Injectable()` + inject `ConfigService`/`PrismaService` + `onModuleInit()` for startup initialization
- Error codes added sequentially to `monitoring-error-codes.ts` (4006 → 4007 → 4008 → 4009 → next: 4010)
- Events added to `EVENT_NAMES` in `event-catalog.ts` + event class in appropriate events file
- Module registration: providers + exports + optional controller
- Test baseline: ~1039 tests across 63+ files (after Story 6.4)

### Financial Math

**Tax report only:** P&L aggregation uses Prisma aggregate queries that return `Prisma.Decimal`. Convert to string via `.toString()` for CSV output. Do NOT perform arithmetic in controller or service code — all aggregation happens in the DB layer via Prisma.

For `cost_basis` calculation: `cost_basis = price × size`. This IS arithmetic — use `decimal.js`:
```typescript
import Decimal from 'decimal.js';
const costBasis = new Decimal(order.price.toString()).mul(new Decimal(order.size.toString()));
```

Do not use native JS `*` operator. This is the only financial calculation in this story.

### Project Structure Notes

**Files to create:**

- `prisma/migrations/YYYYMMDDHHMMSS_add_audit_logs_table/migration.sql` — auto-generated by Prisma
- `src/persistence/repositories/audit-log.repository.ts` — append-only repository
- `src/persistence/repositories/audit-log.repository.spec.ts` — repository tests
- `src/modules/monitoring/audit-log.service.ts` — hash chain service
- `src/modules/monitoring/audit-log.service.spec.ts` — service tests
- `src/modules/monitoring/dto/tax-report-query.dto.ts` — validation DTO
- `src/common/events/monitoring.events.ts` — audit event classes (or add to existing file if present)

**Files to modify:**

- `prisma/schema.prisma` — add `AuditLog` model
- `src/modules/monitoring/monitoring.module.ts` — register `AuditLogRepository`, `AuditLogService`, export `AuditLogService`
- `src/modules/monitoring/monitoring.module.spec.ts` — verify new providers
- `src/modules/monitoring/event-consumer.service.ts` — inject `AuditLogService`, add audit logging for all events
- `src/modules/monitoring/event-consumer.service.spec.ts` — add audit log tests
- `src/modules/monitoring/monitoring-error-codes.ts` — add 4010, 4011
- `src/modules/monitoring/trade-export.controller.ts` — add tax report endpoint
- `src/modules/monitoring/trade-export.controller.spec.ts` — add tax report tests
- `src/common/events/event-catalog.ts` — add `AUDIT_LOG_FAILED`, `AUDIT_CHAIN_BROKEN`
- `src/reconciliation/startup-reconciliation.service.ts` — inject `AuditLogService`, add audit calls
- `src/reconciliation/startup-reconciliation.service.spec.ts` — add audit tests
- `src/reconciliation/reconciliation.module.ts` — import `MonitoringModule`
- `src/persistence/repositories/position.repository.ts` — add `sumPnlByPlatformAndDateRange()` if needed

**Files to verify (existing tests must pass):**

- All existing spec files
- Specifically: `event-consumer.service.spec.ts`, `monitoring.module.spec.ts`, `startup-reconciliation.service.spec.ts`, `trade-export.controller.spec.ts`

### Existing Infrastructure to Leverage

- **`PrismaService` (global):** Available via `@Global()` `PersistenceModule`. No additional import needed for repository access.
- **`crypto.createHash('sha256')`:** Node.js built-in. Already used in `kalshi-websocket.client.ts` for HMAC.
- **`EventEmitter2`:** Configured with `wildcard: true`, `delimiter: '.'`, `maxListeners: 20`.
- **`EventConsumerService.handleEvent()`:** Central event routing hub — audit log hooks in here.
- **`TradeExportController`:** Existing export controller with rate limiter and auth guard.
- **`OrderRepository.findByDateRange()`:** Existing method for trade log date range queries.
- **`PositionRepository.sumClosedEdgeByDateRange()` / `countClosedByDateRange()`:** Existing P&L aggregation methods.
- **`AuthTokenGuard`:** Existing guard for dashboard authentication.
- **`SystemHealthError`:** Error class for 4000-4999 range with `component` field.
- **Structured logging via `nestjs-pino`:** All log entries include `timestamp`, `level`, `module`, `correlationId`, `message`, `data`.
- **`class-validator` / `class-transformer`:** Already dependencies for DTO validation.
- **`@nestjs/schedule`:** Already registered for cron jobs.

### Design Review Notes (LAD Review — Addressed)

**Reviewer:** kimi-k2-thinking via LAD MCP (glm-4.7 timed out)

**Issues Found:** 5 Critical, 5 Major
**Issues Accepted:** 3 (C1, C4, M9 — incorporated into story)
**Issues Noted:** 1 (C5 — disclaimer added)
**Issues Rejected:** 6 (C2, C3, M6, M7, M8, M10 — see rationale below)

**C1 ACCEPTED (Critical):** "Non-deterministic `JSON.stringify()` for hashing." Valid — JS spec doesn't guarantee key order. Fixed: use `JSON.stringify(obj, Object.keys(obj).sort())` for deterministic serialization. Added pipe delimiters between fields to prevent ambiguous concatenation.

**C2 REJECTED (Critical):** "Write serialization lacks timeout — stuck DB write blocks queue." The DB connection pool has its own timeout (Prisma default 15s). Adding `p-limit` is a new npm dependency for one queue. The catch handler on the Promise queue handles failures. Over-engineering for MVP.

**C3 REJECTED (Critical):** "In-memory `lastHash` cache risky on crash." Single-instance system per architecture. On crash/restart, `onModuleInit()` reloads from DB via `findLast()`. No multi-instance scenario exists in MVP. Cache is always rebuilt from DB state.

**C4 ACCEPTED (Critical):** "Stub `verifyChain()` in repository returning `{ valid: true }`." Fixed: removed stub from repository. Added `findJustBefore()` helper method instead. Chain verification logic lives entirely in `AuditLogService.verifyChain()`.

**C5 NOTED (Critical):** "Tax report uses `expectedEdge` as P&L proxy — legal/compliance risk." Already documented as known limitation. Added CSV disclaimer row: "P&L figures are based on expected edge at trade entry, not realized gains." Schema migration for `realizedPnl` column deferred to Phase 1.

**M6 REJECTED (Major):** "Silent failure mode — no retry." Not silent — audit failures emit `AUDIT_LOG_FAILED` event → `EventConsumerService` routes to Telegram. Adding retry with backoff for a non-blocking fire-and-forget write is over-engineering. The next `append()` call effectively retries the chain.

**M7 REJECTED (Major):** "No table partitioning." At MVP scale (~50-200 audit events/day), partitioning is premature. Architecture uses partitioning for order_book_snapshots (~2.5M rows/day). Audit logs are 4 orders of magnitude smaller.

**M8 REJECTED (Major):** "No encryption for sensitive data in JSONB." PostgreSQL handles encryption at rest. MVP binds to localhost (SSH tunnel). Application-layer encryption prevents JSONB querying. Phase 1 concern.

**M9 ACCEPTED (Major):** "Circular logging risk — `AuditLogService` emits events → `EventConsumerService` re-audits → infinite loop." Real bug. Fixed: `EventConsumerService` skips `monitoring.audit.*` events before calling `AuditLogService.append()`.

**M10 REJECTED (Major):** "No event volume protection — high-frequency events overwhelm audit." Order book updates are NOT domain events routed through `EventConsumerService`. Only discrete domain events (fills, exits, risk breaches, etc.) reach the audit trail — ~50-200/day at MVP scale. No throttling needed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.5, line 1287] — Story definition and acceptance criteria
- [Source: _bmad-output/planning-artifacts/prd.md#NFR-S3, lines 1662-1667] — 7-year tamper-evident audit trail requirement
- [Source: _bmad-output/planning-artifacts/prd.md#FR-DE-02, line 833] — Annual tax report CSV specification
- [Source: _bmad-output/planning-artifacts/prd.md, line 697] — Tax advisor stakeholder use case with export format details
- [Source: _bmad-output/planning-artifacts/architecture.md, line 138] — Audit log architecture: append-only + SHA-256 chaining
- [Source: _bmad-output/planning-artifacts/architecture.md, line 522] — `audit-log.service.ts` planned in monitoring module
- [Source: _bmad-output/planning-artifacts/architecture.md, line 569] — `audit-log.repository.ts` planned in persistence layer
- [Source: _bmad-output/planning-artifacts/architecture.md, line 594] — `monitoring/ → persistence/` dependency allowed
- [Source: _bmad-output/planning-artifacts/architecture.md, line 255] — `audit_logs` table naming convention
- [Source: _bmad-output/planning-artifacts/architecture.md, line 258] — Index naming: `idx_audit_logs_<columns>`
- [Source: pm-arbitrage-engine/src/modules/monitoring/monitoring.module.ts] — Current module structure to extend
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts] — Event routing hub for audit integration
- [Source: pm-arbitrage-engine/src/modules/monitoring/trade-export.controller.ts] — Existing export endpoint pattern
- [Source: pm-arbitrage-engine/src/modules/monitoring/monitoring-error-codes.ts] — Error codes 4006-4009 allocated
- [Source: pm-arbitrage-engine/src/persistence/repositories/order.repository.ts] — Repository pattern and `findByDateRange()`
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts] — P&L aggregation methods
- [Source: pm-arbitrage-engine/src/reconciliation/startup-reconciliation.service.ts] — Reconciliation service to update
- [Source: pm-arbitrage-engine/src/reconciliation/reconciliation.module.ts] — Module to update with MonitoringModule import
- [Source: pm-arbitrage-engine/prisma/schema.prisma] — Current schema (8 models, audit_logs not yet present)
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts] — Event catalog to extend
- [Source: pm-arbitrage-engine/src/common/errors/system-health-error.ts] — SystemHealthError class for 4000+ codes

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 via Claude Code CLI

### Debug Log References

None — all tests passed on first implementation (only lint fixes required for 4 issues).

### Completion Notes List

- All 10 tasks completed in order with TDD (test-first for each component)
- Baseline: 1042 tests → Final: 1076 tests (34 new tests)
- 70 test files, all passing, zero lint errors
- Tax report P&L uses `expectedEdge` split 50/50 between platforms (documented MVP limitation)
- `PositionRepository` gained 2 new methods: `countOrdersByPlatformAndDateRange`, `findClosedByDateRangeWithOrders`
- No circular dependencies introduced (verified: MonitoringModule does not import ReconciliationModule)
- E2E tests required migration to be applied (`pnpm prisma migrate dev --name add-audit-logs-table`)

### File List

**Created:**
- `prisma/migrations/20260224095535_add_audit_logs_table/migration.sql`
- `src/persistence/repositories/audit-log.repository.ts`
- `src/persistence/repositories/audit-log.repository.spec.ts`
- `src/modules/monitoring/audit-log.service.ts`
- `src/modules/monitoring/audit-log.service.spec.ts`
- `src/modules/monitoring/dto/tax-report-query.dto.ts`
- `src/common/events/monitoring.events.ts`

**Modified:**
- `prisma/schema.prisma` — added AuditLog model
- `src/modules/monitoring/monitoring.module.ts` — registered AuditLogService, AuditLogRepository; exported AuditLogService
- `src/modules/monitoring/monitoring.module.spec.ts` — added AuditLogService registration test
- `src/modules/monitoring/event-consumer.service.ts` — injected AuditLogService, added audit trail for all events, added extractModule + sanitizeEventForAudit helpers
- `src/modules/monitoring/event-consumer.service.spec.ts` — 6 new tests for audit integration
- `src/modules/monitoring/monitoring-error-codes.ts` — added 4010, 4011
- `src/modules/monitoring/trade-export.controller.ts` — added tax report endpoint, injected PositionRepository
- `src/modules/monitoring/trade-export.controller.spec.ts` — 5 new tests for tax report
- `src/common/events/event-catalog.ts` — added AUDIT_LOG_FAILED, AUDIT_CHAIN_BROKEN
- `src/common/events/index.ts` — re-exported monitoring.events
- `src/reconciliation/startup-reconciliation.service.ts` — injected AuditLogService, added audit calls to reconcile() and resolveDiscrepancy()
- `src/reconciliation/startup-reconciliation.service.spec.ts` — 3 new tests for audit integration
- `src/reconciliation/reconciliation.module.ts` — imported MonitoringModule
- `src/persistence/repositories/position.repository.ts` — added countOrdersByPlatformAndDateRange, findByOrderIds (replaced unused findClosedByDateRangeWithOrders)

### Senior Developer Review (AI)

**Reviewer:** Claude Opus 4.6 via Claude Code CLI
**Date:** 2026-02-24
**Pre-fix tests:** 1076 | **Post-fix tests:** 1078

**Issues Found:** 3 HIGH, 3 MEDIUM, 2 LOW

**Fixes Applied (6):**

1. **[H1] Tax report positionId always N/A** — Added `findByOrderIds()` to PositionRepository, build orderId→positionId lookup map in tax report endpoint. Trade log now populates `position_id` from actual position data.
2. **[H2] Tax report correlationId always N/A** — Added code comment documenting that Order model does not store correlationId (data model gap). No code fix possible without schema migration.
3. **[H3] Tax report proceeds/pnl misleadingly `0`** — Changed from `'0'` to `'N/A'` with explanatory comments. `0` implies zero proceeds (wrong); `N/A` honestly signals data unavailability.
4. **[M1] `findClosedByDateRangeWithOrders()` dead code** — Removed and replaced with `findByOrderIds()` which is actually used by the tax report.
5. **[M3] 50/50 P&L split undocumented** — Added detailed code comment explaining the MVP simplification and that proper per-leg attribution requires Phase 1 schema migration.
6. **[M4] Missing `verifyChain()` empty range test** — Added test asserting `{ valid: true, entriesChecked: 0 }` for empty date range.

**Accepted as-is (2 LOW):**
- L1: Redundant `format` query param (only 'csv') — harmless, extensible for future formats.
- L2: `sanitizeEventForAudit` relies on Decimal's `toJSON()` — works correctly, explicit handling deferred.

**Other notes:**
- M5 (`INVALID_DATE_RANGE` code 4012): Pre-existing from Story 6.3 error handling, not newly introduced. No action needed.
- Flaky property-based test in `financial-math.property.spec.ts` observed (fast-check randomness) — passes in isolation, not related to this story.
