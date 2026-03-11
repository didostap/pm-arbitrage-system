# Story 9.6: Audit Log Retention & Pruning

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the system to automatically prune old audit log entries beyond a configurable retention window,
So that the `audit_logs` table does not grow unbounded, keeping database queries performant and storage costs manageable.

## Acceptance Criteria

1. **Given** `AUDIT_LOG_RETENTION_DAYS` is set to a positive integer (e.g., 7), **When** the daily pruning cron fires at 03:00 UTC, **Then** all `audit_logs` rows with `created_at` older than the retention window are deleted and a structured log entry records the count of pruned rows. [Source: sprint-change-proposal-2026-03-13-audit-log-retention.md#4.1]

2. **Given** `AUDIT_LOG_RETENTION_DAYS` is set to `0`, **When** the daily pruning cron fires, **Then** no rows are deleted and the cron exits early with a debug log indicating pruning is disabled. [Source: sprint-change-proposal-2026-03-13-audit-log-retention.md#4.1]

3. **Given** pruning has removed rows before the retained window, **When** `verifyChain(startDate, endDate)` is called and `findJustBefore()` returns `null` for the oldest retained entry, **Then** the oldest retained row is treated as the chain anchor (its `previousHash` is trusted, not compared against `GENESIS_HASH`) and verification succeeds for the retained range. [Source: sprint-change-proposal-2026-03-13-audit-log-retention.md#Technical Impact; Derived from: codebase `audit-log.service.ts:90-94` — current code compares against GENESIS_HASH when no prior entry exists, which would produce a false break post-pruning]

4. **Given** a pruning operation completes with rows deleted (count > 0), **When** the operation finishes, **Then** a `monitoring.audit.pruned` event is emitted with the count of pruned rows, cutoff date, and retention days. [Source: sprint-change-proposal-2026-03-13-audit-log-retention.md#4.1]

5. **Given** zero rows match the pruning criteria, **When** the cron completes, **Then** no event is emitted and only a debug log is written. [Derived from: event emission best practices — avoid noisy zero-count events]

6. **Given** the pruning cron encounters a database error, **When** the error is caught, **Then** the error is logged with structured JSON (module, error code, correlationId) and the system continues operating without interruption to the trading hot path. [Derived from: CLAUDE.md error handling, DailySummaryService pattern at `monitoring/daily-summary.service.ts:49-56`]

## Tasks / Subtasks

- [x] Task 1: Add `AUDIT_LOG_RETENTION_DAYS` to env schema and env files (AC: #1, #2)
  - [x] Add `AUDIT_LOG_RETENTION_DAYS: z.coerce.number().int().min(0).default(7)` to `envSchema` in `common/config/env.schema.ts`
  - [x] Add entry to `.env.example` and `.env.development` with comment `# 0 = disabled (for Phase 1+ 7-year retention compliance)`

- [x] Task 2: Add `deleteOlderThan()` to `AuditLogRepository` (AC: #1)
  - [x] Implement `async deleteOlderThan(cutoffDate: Date): Promise<number>` using `this.prisma.auditLog.deleteMany({ where: { createdAt: { lt: cutoffDate } } })`
  - [x] Return `.count` from the Prisma `BatchPayload`

- [x] Task 3: Add `AuditLogPrunedEvent` and register in event catalog (AC: #4)
  - [x] Create `AuditLogPrunedEvent` class in `common/events/monitoring.events.ts` matching `AuditLogFailedEvent` style (plain class, not BaseEvent):
    ```typescript
    export class AuditLogPrunedEvent {
      constructor(
        public readonly prunedCount: number,
        public readonly cutoffDate: string,
        public readonly retentionDays: number,
        public readonly timestamp: Date = new Date(),
      ) {}
    }
    ```
  - [x] Register `AUDIT_LOG_PRUNED: 'monitoring.audit.pruned'` in `event-catalog.ts` alongside existing `AUDIT_LOG_FAILED` and `AUDIT_CHAIN_BROKEN`

- [x] Task 4: Create `AuditLogRetentionService` with daily cron (AC: #1, #2, #4, #5, #6)
  - [x] Create `audit-log-retention.service.ts` in `modules/monitoring/`
  - [x] Inject `ConfigService`, `AuditLogRepository`, `EventEmitter2`
  - [x] Implement `@Cron('0 3 * * *', { timeZone: 'UTC' })` method `handlePruning()` wrapped in `withCorrelationId()`
  - [x] Read `AUDIT_LOG_RETENTION_DAYS` from config; if 0, log debug and return early
  - [x] Calculate cutoff: `new Date(Date.now() - retentionDays * 86_400_000)`
  - [x] Call `auditLogRepository.deleteOlderThan(cutoffDate)`, get count
  - [x] If count > 0: emit `AuditLogPrunedEvent`, log info with count/cutoff/retentionDays
  - [x] If count === 0: log debug only, no event
  - [x] Wrap in try/catch — log error with `MONITORING_ERROR_CODES.AUDIT_LOG_PRUNE_FAILED`, never re-throw

- [x] Task 5: Add error code for pruning failure (AC: #6)
  - [x] Add `AUDIT_LOG_PRUNE_FAILED: 4013` to `MONITORING_ERROR_CODES` in `monitoring-error-codes.ts`

- [x] Task 6: Fix `verifyChain()` post-pruning false break (AC: #3)
  - [x] In `AuditLogService.verifyChain()`, after `findJustBefore()` returns null: instead of using `GENESIS_HASH` unconditionally, check if the first entry's `previousHash !== GENESIS_HASH` — if so, the prior entries were pruned and this entry is the chain anchor; skip its `previousHash` check and start verification from its `currentHash` forward
  - [x] See Dev Notes for exact code change

- [x] Task 7: Register `AuditLogRetentionService` in `MonitoringModule` (AC: #1)
  - [x] Add to `providers` array in `monitoring.module.ts` (`AuditLogRepository` is already provided — used by `AuditLogService`)

- [x] Task 8: Tests (AC: #1, #2, #3, #4, #5, #6)
  - [x] `audit-log-retention.service.spec.ts` (co-located in `modules/monitoring/`):
    - Prunes rows older than retention window, emits event with correct count/cutoff/retentionDays
    - Skips pruning when `AUDIT_LOG_RETENTION_DAYS=0`, no deleteMany call, no event
    - Does not emit event when 0 rows pruned
    - Handles repository error gracefully (logs with error code 4013, does not throw)
    - Calculates correct cutoff date from config value
    - Uses `withCorrelationId()` wrapper
  - [x] `audit-log.repository.spec.ts` — add `deleteOlderThan()` test:
    - Calls `prisma.auditLog.deleteMany` with correct `{ createdAt: { lt: cutoffDate } }` clause
    - Returns count from BatchPayload
  - [x] `audit-log.service.spec.ts` — add post-pruning chain verification tests:
    - `verifyChain()` succeeds when `findJustBefore()` returns null and first entry's `previousHash !== GENESIS_HASH` (pruned scenario — anchor is trusted)
    - `verifyChain()` still works normally when `findJustBefore()` returns null and first entry has `GENESIS_HASH` (fresh database — no pruning)
    - `verifyChain()` still detects genuine chain breaks within the retained window

## Dev Notes

### Architecture Context

This story adds configurable retention pruning to the `audit_logs` table, which currently grows without bound. `EventConsumerService` writes one audit log entry per domain event (excluding `monitoring.audit.*` to prevent recursion), producing thousands of rows per day. 133K+ rows were observed as early as Epic 7.5.2. [Source: sprint-change-proposal-2026-03-13-audit-log-retention.md#1]

The 7-year retention requirement (NFR-S3, NFR-R5) is a Phase 1+ concern addressed in Epic 12. Current phase (pre-revenue paper/early-live trading) only needs recent history for debugging and operations. Setting `AUDIT_LOG_RETENTION_DAYS=0` disables pruning entirely, enabling seamless transition to indefinite retention when Epic 12 arrives. [Source: sprint-change-proposal-2026-03-13-audit-log-retention.md#Context]

**Hot path impact: ZERO.** Pruning runs on a daily `@Cron` schedule (3:00 AM UTC), completely outside the execution pipeline. No interaction with detection, risk, or execution modules. [Source: sprint-change-proposal-2026-03-13-audit-log-retention.md#Technical Impact]

### Hash Chain Impact — CRITICAL

The audit log uses SHA-256 hash chaining (`previousHash` → `currentHash`) for tamper-evident logging. Pruning removes rows referenced by `previousHash` of retained rows.

**Post-pruning false break in `verifyChain()`**: The current code at `audit-log.service.ts:90-94`:
```typescript
const entryBefore = await this.auditLogRepository.findJustBefore(entries[0]!.createdAt);
let expectedPreviousHash = entryBefore?.currentHash ?? GENESIS_HASH;
```

When all entries before the retained window are pruned, `findJustBefore()` returns `null`. The code falls back to `GENESIS_HASH` (`'0'.repeat(64)`). But the oldest retained entry's `previousHash` was set to the hash of a now-pruned entry — NOT `GENESIS_HASH`. This produces a **false chain break**.

**Required fix** (Task 6): When `entryBefore` is null AND the first entry's `previousHash !== GENESIS_HASH`, the prior entries were pruned. Trust the first entry as the chain anchor — skip its `previousHash` check and start chain verification from its `currentHash` forward:

```typescript
const entryBefore = await this.auditLogRepository.findJustBefore(entries[0]!.createdAt);

if (entryBefore) {
  // Normal case — verify first entry chains from the prior entry
  expectedPreviousHash = entryBefore.currentHash;
} else if (entries[0]!.previousHash === GENESIS_HASH) {
  // Fresh database — first entry ever, verify against genesis
  expectedPreviousHash = GENESIS_HASH;
} else {
  // Post-pruning — prior entries deleted, oldest retained = chain anchor
  // Setting expected = actual effectively SKIPS validation for this entry only.
  // The anchor's previousHash pointed to a now-pruned row — we can't verify it,
  // so we trust it and start chain verification from entry[1] onward.
  expectedPreviousHash = entries[0]!.previousHash;
}
```

Three-state logic:
1. **`entryBefore` exists** → Normal: verify first entry chains from prior entry
2. **`entryBefore` null, `previousHash === GENESIS_HASH`** → Fresh DB: first entry ever
3. **`entryBefore` null, `previousHash !== GENESIS_HASH`** → Post-pruning: skip first entry validation, trust as anchor

This preserves existing behavior for fresh databases and non-pruned ranges, while correctly handling the pruned scenario. [Source: codebase `audit-log.service.ts:75-148`]

### Key Implementation Details

**Service pattern**: Follow `DailySummaryService` exactly — `@Injectable()`, `@Cron()` method, `withCorrelationId()` wrapper (import from `common/services/correlation-context.ts`), try/catch that logs but never re-throws, structured JSON logging with `Logger`. [Source: codebase `monitoring/daily-summary.service.ts:15-57`]

**Config access**: `this.configService.get<number>('AUDIT_LOG_RETENTION_DAYS', 7)`. The `env.schema.ts` Zod validation ensures the value is a non-negative integer at startup. [Source: codebase `common/config/env.schema.ts`]

**Cutoff date calculation**:
```typescript
const cutoffDate = new Date(Date.now() - retentionDays * 86_400_000);
```
Simple and correct — `created_at` uses `@db.Timestamptz` (UTC-aware), so no timezone conversion needed. [Source: Prisma schema `audit_logs.created_at`]

**Prisma deleteMany**: Returns `Prisma.BatchPayload` (`{ count: number }`). Generates a single atomic `DELETE FROM audit_logs WHERE created_at < $1` query — PostgreSQL handles this efficiently with the existing `idx_audit_logs_created_at` btree index. At expected daily volume (~7-14K rows pruned), no batching needed. Note: if daily volume ever exceeds 100K rows, consider chunked deletes to avoid extended table locks. [Source: Prisma schema indexes]

**`lastHash` cache safety**: `AuditLogService` caches the most recent entry's hash in `this.lastHash` (line 35). Pruning targets old rows (`createdAt < cutoff`), never the latest entry — so the cache remains valid. No coordination between `AuditLogRetentionService` and `AuditLogService` is needed. [Source: codebase `audit-log.service.ts:35,150-177`]

**Event emission timing**: `EventEmitter2.emit()` is synchronous fire-and-forget. The event fires after `deleteOlderThan()` returns (i.e., after the Prisma `deleteMany` completes and commits). This is the standard pattern used throughout the codebase. [Source: codebase event emission pattern]

**Event namespace**: `monitoring.audit.pruned` follows the existing `monitoring.audit.*` namespace (`write_failed`, `chain_broken`). `EventConsumerService` skips events starting with `monitoring.audit.` (line 230-231 of `event-consumer.service.ts`), so the pruning event will NOT be written back to the audit log — this is correct (no infinite recursion, no auditing our own pruning). [Source: codebase `event-consumer.service.ts:230-231`]

**Error code**: Next available in `MONITORING_ERROR_CODES` is `4013` (after `INVALID_DATE_RANGE: 4012`). [Source: codebase `monitoring/monitoring-error-codes.ts`]

### Existing Infrastructure to Reuse

| Component | Location | What to Reuse |
|-----------|----------|---------------|
| `AuditLogRepository` | `persistence/repositories/audit-log.repository.ts` | Add `deleteOlderThan()` — follows existing method patterns |
| `AuditLogFailedEvent` | `common/events/monitoring.events.ts` | Pattern for `AuditLogPrunedEvent` (plain class, no BaseEvent) |
| `EVENT_NAMES.AUDIT_LOG_FAILED` | `common/events/event-catalog.ts:147-150` | Pattern for `AUDIT_LOG_PRUNED` registration |
| `DailySummaryService` | `monitoring/daily-summary.service.ts` | Pattern: `@Cron`, `withCorrelationId()`, try/catch, structured logging |
| `MONITORING_ERROR_CODES` | `monitoring/monitoring-error-codes.ts` | Add code `4013` |
| `MonitoringModule` | `monitoring/monitoring.module.ts` | Register new provider |
| `envSchema` | `common/config/env.schema.ts` | Add new config var (follow `z.coerce.number()` pattern) |
| `GENESIS_HASH` | `monitoring/audit-log.service.ts:30` | Referenced in verifyChain fix — `'0'.repeat(64)` |

### Module Boundaries

- `modules/monitoring/audit-log-retention.service.ts` — **NEW** service, owns pruning cron logic
- `modules/monitoring/audit-log.service.ts` — **MODIFY** `verifyChain()` for post-pruning anchor handling
- `persistence/repositories/audit-log.repository.ts` — **MODIFY** add `deleteOlderThan()` method
- `common/events/monitoring.events.ts` — **MODIFY** add `AuditLogPrunedEvent` class
- `common/events/event-catalog.ts` — **MODIFY** add `AUDIT_LOG_PRUNED` event name
- `common/config/env.schema.ts` — **MODIFY** add `AUDIT_LOG_RETENTION_DAYS`
- `modules/monitoring/monitoring-error-codes.ts` — **MODIFY** add `AUDIT_LOG_PRUNE_FAILED: 4013`
- `modules/monitoring/monitoring.module.ts` — **MODIFY** register `AuditLogRetentionService`

No forbidden imports introduced. `AuditLogRetentionService` lives in `monitoring/` and accesses `AuditLogRepository` via DI (same pattern as `AuditLogService`). [Source: CLAUDE.md module dependency rules]

### Testing Strategy

Co-located specs using Vitest 4 + `unplugin-swc`. Mock `PrismaService`, `ConfigService`, `EventEmitter2`.

**Baseline:** 1927 tests across 111 files, all green (2 todo).

**Key test scenarios:**

| Scenario | Service | Expected Behavior |
|----------|---------|-------------------|
| Happy path (retention=7, old rows exist) | RetentionService | deleteOlderThan called, event emitted with count |
| Disabled (retention=0) | RetentionService | Early return, no deleteMany, no event, debug log |
| No rows to prune (count=0) | RetentionService | No event emission, debug log only |
| Repository error | RetentionService | Error logged with code 4013, no re-throw |
| Cutoff calculation | RetentionService | cutoffDate = now - (retentionDays * 86400000) |
| withCorrelationId wrapper | RetentionService | correlationId set for the cron execution |
| deleteOlderThan Prisma call | Repository | Correct `where: { createdAt: { lt: cutoffDate } }`, returns count |
| Post-pruning chain (anchor) | AuditLogService | findJustBefore=null, previousHash≠GENESIS → trusted anchor, verify succeeds |
| Fresh DB chain (genesis) | AuditLogService | findJustBefore=null, previousHash=GENESIS → GENESIS_HASH check, verify succeeds |
| Genuine break in retained window | AuditLogService | findJustBefore returns entry, hash mismatch → break detected correctly |

### Previous Story Intelligence

Story 9-2 (most recent completed) established patterns for:
- Adding new events to `event-catalog.ts` and `monitoring.events.ts` or `risk.events.ts`
- Wiring events through `EventConsumerService` (though pruning event is in `monitoring.audit.*` namespace and will be auto-skipped)
- Error code additions in their respective constants files
- Test count: 1927 (Story 9-2 baseline: 1910 → 1927, +17 tests)

[Source: Story 9-2 completion notes]

### Project Structure Notes

All files align with established module structure. New service co-located in `modules/monitoring/` alongside `AuditLogService`. No new modules or directories needed. [Source: codebase exploration, CLAUDE.md architecture]

### References

- [Source: sprint-change-proposal-2026-03-13-audit-log-retention.md] — Full proposal with impact analysis, rationale, acceptance criteria preview
- [Source: CLAUDE.md#Architecture] — Module dependency rules, error handling, event patterns
- [Source: Prisma schema `audit_logs` model, lines 235-249] — Table structure, indexes, hash chain fields
- [Source: codebase `monitoring/audit-log.service.ts:30`] — `GENESIS_HASH = '0'.repeat(64)`
- [Source: codebase `monitoring/audit-log.service.ts:75-148`] — `verifyChain()` implementation with chain anchor logic
- [Source: codebase `monitoring/audit-log.service.ts:31-220`] — Full `AuditLogService` (no pruning exists)
- [Source: codebase `persistence/repositories/audit-log.repository.ts:4-49`] — Repository methods (no delete exists)
- [Source: codebase `monitoring/daily-summary.service.ts:15-160`] — `@Cron` + `withCorrelationId()` + try/catch pattern
- [Source: codebase `monitoring/event-consumer.service.ts:230-231`] — `monitoring.audit.*` skip logic
- [Source: codebase `common/events/event-catalog.ts:147-150`] — Existing audit event names
- [Source: codebase `common/events/monitoring.events.ts`] — `AuditLogFailedEvent`, `AuditChainBrokenEvent` patterns
- [Source: codebase `common/config/env.schema.ts`] — Config variable patterns
- [Source: codebase `monitoring/monitoring-error-codes.ts`] — Error codes 4006-4012, next: 4013
- [Source: epics.md#NFR-S3] — 7-year retention requirement (Phase 1+, not current phase)
- [Source: architecture.md#Audit Log Architecture] — Append-only hash chain design, retention-phase annotation needed
- [Source: architecture.md#Data Architecture] — Database schema strategy, audit log as one of six data domains

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — clean implementation, no blockers encountered.

### Completion Notes List

- All 8 tasks implemented via strict TDD (red→green→refactor).
- Baseline: 1927 tests (111 files). Final: 1937 tests (112 files). +10 tests, +1 test file.
- Test breakdown: 6 new in `audit-log-retention.service.spec.ts`, 1 new in `audit-log.repository.spec.ts`, 3 new in `audit-log.service.spec.ts`.
- Lad MCP code review: 1 Medium finding accepted (added debug log for post-pruning anchor in `verifyChain()`). 5 Low findings evaluated and skipped as out-of-scope or already covered by existing patterns/documentation.
- No deviations from Dev Notes guidance. All patterns followed exactly (DailySummaryService for cron, AuditLogFailedEvent for event class, existing error code numbering).
- Pre-existing flaky e2e test (`test/logging.e2e-spec.ts` — "should emit events with correlation ID") intermittently fails. Not related to this story.
- Lint clean. All AC verified.

### File List

**New files:**
- `src/modules/monitoring/audit-log-retention.service.ts` — Retention pruning cron service
- `src/modules/monitoring/audit-log-retention.service.spec.ts` — 6 tests

**Modified files:**
- `src/common/config/env.schema.ts` — Added `AUDIT_LOG_RETENTION_DAYS`
- `src/common/events/event-catalog.ts` — Added `AUDIT_LOG_PRUNED`
- `src/common/events/monitoring.events.ts` — Added `AuditLogPrunedEvent`
- `src/modules/monitoring/audit-log.service.ts` — Fixed `verifyChain()` with 3-state post-pruning anchor logic + debug log
- `src/modules/monitoring/audit-log.service.spec.ts` — Added 3 post-pruning chain verification tests
- `src/modules/monitoring/monitoring-error-codes.ts` — Added `AUDIT_LOG_PRUNE_FAILED: 4013`
- `src/modules/monitoring/monitoring.module.ts` — Registered `AuditLogRetentionService`
- `src/persistence/repositories/audit-log.repository.ts` — Added `deleteOlderThan()`
- `src/persistence/repositories/audit-log.repository.spec.ts` — Added 1 test for `deleteOlderThan()`
- `.env.example` — Added `AUDIT_LOG_RETENTION_DAYS=7`
- `.env.development` — Added `AUDIT_LOG_RETENTION_DAYS=7`

### Senior Developer Review (AI) — 2026-03-13

**Reviewer:** Amelia (Dev Agent CR)
**Model:** Claude Opus 4.6

**Findings:** 0 HIGH, 2 MEDIUM, 3 LOW — all fixed.

| # | Severity | Issue | Fix Applied |
|---|----------|-------|-------------|
| M1 | MEDIUM | `vi.useFakeTimers()` cleanup not in `afterEach` — test pollution risk on assertion failure | Added `afterEach(() => vi.useRealTimers())` in both spec files, removed manual cleanup calls |
| M2 | MEDIUM | `withCorrelationId` test verified nothing — removing the wrapper wouldn't break it | Mocked `withCorrelationId` via `vi.mock`, test now asserts `toHaveBeenCalledOnce()` |
| L1 | LOW | `AUDIT_LOG_PRUNED` in event-catalog lacked Story 9.6 attribution | Added `[Story 9.6]` to JSDoc comment |
| L2 | LOW | `String(error)` loses stack trace in error logging | Changed to `error instanceof Error ? (error.stack ?? error.message) : String(error)` |
| L3 | LOW | No max bound on `AUDIT_LOG_RETENTION_DAYS` — extreme values accepted | Added `.max(3650)` (10 years) to Zod schema |

**AC Verification:** All 6 ACs confirmed IMPLEMENTED with code evidence.
**Task Audit:** All 8 tasks marked [x] confirmed DONE.
**Test Count:** 1937 tests, 112 files — unchanged (fixes were test structure improvements, no new test cases).
**Verdict:** APPROVED → done
