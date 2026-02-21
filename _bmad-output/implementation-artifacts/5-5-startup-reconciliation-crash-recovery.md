# Story 5.5: Startup Reconciliation & Crash Recovery

Status: done

## Story

As an operator,
I want the system to reconcile its state against both platforms on startup,
So that I can trust the system after a restart or crash — especially if positions were open.

## Architecture Deviation

**ADR: `startup-reconciliation.service.ts` moved from `persistence/` to `src/reconciliation/`.**
The architecture spec places this file in `persistence/`. This story deviates intentionally — `PersistenceModule` is `@Global()` for `PrismaService` only, and adding `ConnectorModule` + `RiskManagementModule` imports to it would violate its single-responsibility boundary and risk circular DI. A dedicated `ReconciliationModule` at `src/reconciliation/` is the correct home. See Dev Notes → Architecture Constraints for full rationale. Future stories referencing reconciliation should use `src/reconciliation/`, not `persistence/`.

## Out of Scope

- **Audit log hash chaining** — Epic 6, Story 6.5. This story logs reconciliation results via structured JSON logging. Once `AuditLogService` exists, reconciliation results will be routed through it retroactively.
- **Automatic failover to standby host** — Phase 1 (PRD Deployment requirements). MVP requires manual restart.
- **Automatic single-leg management** (auto-close/hedge) — Epic 10, Story 10.3. Reconciliation detects discrepancies but does NOT auto-resolve.
- **Dashboard UI for reconciliation** — Epic 7. Endpoints are REST API only; no frontend.
- **Telegram alert integration** — Epic 6, Story 6.1. Events are emitted; Telegram consumption is a future subscriber.
- **Paper trading reconciliation** — Epic 5.5. Paper positions don't need platform-state reconciliation.
- **WAL-based continuous archiving** — Phase 1. Hourly `pg_dump` is the current backup strategy.

## Acceptance Criteria

1. **Given** the engine starts and `open_positions` records exist in the database with status `OPEN`, `SINGLE_LEG_EXPOSED`, or `EXIT_PARTIAL`
   **When** startup reconciliation runs (before the trading engine starts its first cycle)
   **Then** the system queries both Kalshi and Polymarket APIs for the current status of every order linked to those positions
   **And** API-reported fill statuses are compared against local order records
   **And** reconciliation runs AFTER platform connectors are connected but BEFORE trading cycles begin

2. **Given** the database contains `Order` records with status `PENDING` (Polymarket orders that timed out during execution — Story 5.1)
   **When** reconciliation checks pending orders
   **Then** the system queries the platform API for each pending order's current status via `getOrder(orderId)`
   **And** if the order is now `filled`, the local order record is updated to `FILLED` with fill price and size
   **And** if the associated position was `SINGLE_LEG_EXPOSED` and the now-filled order completes the second leg, the position transitions to `OPEN`
   **And** an `OrderFilledEvent` is emitted for the late-filled order
   **And** if the order is now `cancelled` or `rejected`, the local order record is updated accordingly (position status unchanged — it's already `SINGLE_LEG_EXPOSED`)

3. **Given** an order's fill status reported by the platform API does NOT match the local order record
   **When** a discrepancy is detected (e.g., local order shows `FILLED` but platform reports `cancelled`, or local order shows `FILLED` but platform returns 404/not found)
   **Then** a `SystemHealthError` (code 4005, critical severity) is emitted with discrepancy details
   **And** the position is flagged as `RECONCILIATION_REQUIRED` in the database
   **And** all new trading is halted (risk manager halt with reason `reconciliation_discrepancy`)
   **And** a `ReconciliationDiscrepancyEvent` is emitted with full context for operator review

4. **Given** no discrepancies are found
   **When** reconciliation completes cleanly
   **Then** "Reconciliation complete, no discrepancies" is logged at `log` level with summary (positions checked, orders verified, pending orders resolved)
   **And** existing `OPEN` positions resume exit monitoring (ExitMonitorService is already polling)
   **And** the risk budget is recalculated from current position state (openPositionCount, totalCapitalDeployed recounted from DB)
   **And** a `ReconciliationCompleteEvent` is emitted with summary statistics

5. **Given** positions are flagged as `RECONCILIATION_REQUIRED`
   **When** the operator sends `POST /api/reconciliation/:id/resolve` with `{ action: 'acknowledge' | 'force_close', rationale: string }` body
   **Then** for `acknowledge`: the position status is updated to the recommended status stored in the position's `reconciliationContext` JSONB column (e.g., `OPEN` if platform confirms fills, `CLOSED` if platform shows cancelled orders), the halt is cleared if no more `RECONCILIATION_REQUIRED` positions remain
   **And** for `force_close`: the position is marked `CLOSED`, risk budget is updated via `riskManager.closePosition()`, the halt is cleared if no more `RECONCILIATION_REQUIRED` positions remain
   **And** the resolution is logged with operator rationale

6. **Given** reconciliation results are produced
   **When** they are persisted
   **Then** results are written via structured JSON logging at `log` level (clean) or `error` level (discrepancies) with schema:
   ```json
   {
     "level": "log | error",
     "module": "StartupReconciliationService",
     "correlationId": "<startup-correlation-id>",
     "message": "Reconciliation complete" | "Reconciliation found discrepancies",
     "data": {
       "positionsChecked": 3,
       "ordersVerified": 6,
       "pendingOrdersResolved": 1,
       "discrepancies": [{ "positionId": "...", "type": "order_status_mismatch", "detail": "..." }],
       "startedAt": "2026-02-21T10:00:00Z",
       "completedAt": "2026-02-21T10:00:02Z",
       "durationMs": 2000,
       "platformStatus": { "kalshi": "connected", "polymarket": "connected" }
     }
   }
   ```

7. **Given** either platform connector fails to connect during startup
   **When** reconciliation cannot query that platform
   **Then** reconciliation is attempted for the connected platform only
   **And** positions involving the disconnected platform are flagged as `RECONCILIATION_REQUIRED` with reason "platform unavailable during reconciliation"
   **And** trading is halted until the disconnected platform recovers and operator triggers manual reconciliation via `POST /api/reconciliation/run`

## Tasks / Subtasks

- [x] Task 1: Add `getOrder(orderId)` to `IPlatformConnector` interface (AC: 1, 2)
  - [x] 1.1 Add `getOrder(orderId: string): Promise<OrderResult>` to `IPlatformConnector` in `src/common/interfaces/platform-connector.interface.ts`
  - [x] 1.2 Implement in `KalshiConnector`: call Kalshi REST API `GET /portfolio/orders/{order_id}`, map response to `OrderResult`, handle rate limiting via `rateLimiter.acquireRead()`
  - [x] 1.3 Implement in `PolymarketConnector`: call `clobClient.getOrder(orderId)`, map response to `OrderResult`, handle rate limiting
  - [x] 1.4 Update ALL existing `IPlatformConnector` mocks across the codebase to include `getOrder`. Search for `KALSHI_CONNECTOR_TOKEN` and `POLYMARKET_CONNECTOR_TOKEN` in test files — add `getOrder: vi.fn()` to each mock. **Checklist** (verify each file):
    - `execution.service.spec.ts`
    - `single-leg-resolution.service.spec.ts`
    - `exposure-alert-scheduler.service.spec.ts`
    - `exit-monitor.service.spec.ts`
    - `threshold-evaluator.service.spec.ts` (if it mocks connectors)
    - Any other files found via grep for `KALSHI_CONNECTOR_TOKEN` or `POLYMARKET_CONNECTOR_TOKEN`
  - [x] 1.5 Unit tests for both connector implementations (happy path, not-connected error, order not found)

- [x] Task 2: Create reconciliation event classes (AC: 3, 4)
  - [x] 2.1 Create `ReconciliationCompleteEvent` in `src/common/events/system.events.ts` (new file — verify no existing `system.events.ts` in the events directory; current files are `execution.events.ts`, `detection.events.ts`, `risk.events.ts`, etc.) extending `BaseEvent`
  - [x] 2.2 Payload: `positionsChecked`, `ordersVerified`, `pendingOrdersResolved`, `discrepanciesFound`, `durationMs`, `summary`
  - [x] 2.3 Create `ReconciliationDiscrepancyEvent` in same file
  - [x] 2.4 Payload: `positionId`, `pairId`, `discrepancyType` (`'order_status_mismatch' | 'order_not_found' | 'pending_filled' | 'platform_unavailable'`), `localState`, `platformState`, `recommendedAction`. Note: `getPositions()` is not implemented — reconciliation is **order-level verification only** via `getOrder()`. No position-level cross-reference against platform portfolios.
  - [x] 2.5 Add `RECONCILIATION_COMPLETE: 'system.reconciliation.complete'` and `RECONCILIATION_DISCREPANCY: 'system.reconciliation.discrepancy'` to `EVENT_NAMES` in `event-catalog.ts`. **Convention note:** existing events use module-based prefixes (`execution.*`, `risk.*`, `detection.*`). `system.*` is a deliberate deviation — reconciliation is cross-cutting and doesn't map to a single module directory. The `system.` prefix is appropriate here.
  - [x] 2.6 Unit tests for event construction

- [x] Task 3: Add error code 4005 for reconciliation discrepancy (AC: 3)
  - [x] 3.1 Add `RECONCILIATION_DISCREPANCY: 4005` to system health error codes in `src/common/errors/system-health-error.ts` (or a related constants file)
  - [x] 3.2 Verify `SystemHealthError` constructor accepts this code

- [x] Task 4: Add `reconciliation_discrepancy` halt reason to `RiskManagerService` (AC: 3, 5)
  - [x] 4.1 Add `RECONCILIATION_DISCREPANCY: 'reconciliation_discrepancy'` to `HALT_REASONS` constant
  - [x] 4.2 **Refactor halt state from single `haltReason: string` to `activeHaltReasons: Set<HaltReason>`** in `RiskManagerService`. This prevents the edge case where a reconciliation halt overwrites a daily loss halt (or vice versa), causing `resumeTrading()` to accidentally clear a safety halt. `isTradingHalted()` returns `activeHaltReasons.size > 0`. Persist as JSON array in `risk_states`. **Migration check:** verify whether `risk_states` currently stores halt as a single `halt_reason` string/enum column — if so, add a migration subtask to change to `active_halt_reasons Json` (JSONB array). If halt state is already in a JSONB column, just update the serialization logic.
  - [x] 4.3 Add `haltTrading(reason: HaltReason): void` method to `IRiskManager` interface — adds reason to `activeHaltReasons`, emits `SYSTEM_TRADING_HALTED`, persists state. This is a new public method; the existing internal daily-loss halt should also use this method (refactor the internal call site).
  - [x] 4.4 Implement `haltTrading()` in `RiskManagerService`
  - [x] 4.5 Add `resumeTrading(reason: HaltReason): void` method to `IRiskManager` — removes ONLY the specified reason from `activeHaltReasons`. Trading resumes only if the set is empty after removal. This ensures reconciliation resolution cannot accidentally clear a daily loss halt.
  - [x] 4.6 Implement `resumeTrading()` in `RiskManagerService`: remove reason, check if set is empty, emit event if trading actually resumes, persist state
  - [x] 4.7 Add `recalculateFromPositions(openCount: number, capitalDeployed: Decimal): void` to `IRiskManager` — force-sets position count and capital from reconciled state
  - [x] 4.8 Implement in `RiskManagerService`: overwrite `openPositionCount` and `totalCapitalDeployed`, persist state, log the override
  - [x] 4.9 Update ALL `IRiskManager` mocks to include `haltTrading`, `resumeTrading`, `recalculateFromPositions`. Known mock locations (search for `RISK_MANAGER_TOKEN`): `execution-queue.service.spec.ts`, `execution.service.spec.ts`, `single-leg-resolution.service.spec.ts`, `exit-monitor.service.spec.ts`, `exposure-alert-scheduler.service.spec.ts`
  - [x] 4.10 Unit tests for halt/resume/recalculate (including overlapping halt scenario: daily loss + reconciliation)

- [x] Task 5: Create `StartupReconciliationService` (AC: 1, 2, 3, 4, 6, 7)
  - [x] 5.1 Create `src/reconciliation/startup-reconciliation.service.ts` — in the dedicated `ReconciliationModule` (see Task 8)
  - [x] 5.2 Inject: `PrismaService`, Kalshi and Polymarket connectors (via tokens), `EventEmitter2`, `IRiskManager` (via `RISK_MANAGER_TOKEN`), `PositionRepository`, `OrderRepository`, `Logger`
  - [x] 5.3 Implement `reconcile(): Promise<ReconciliationResult>` — the main entry point
    - Step 1: Query DB for all non-CLOSED positions (`OPEN`, `SINGLE_LEG_EXPOSED`, `EXIT_PARTIAL`, `RECONCILIATION_REQUIRED`)
    - Step 2: Query DB for all PENDING orders
    - Step 3: Check connector health — if a connector is disconnected, flag positions involving that platform
    - Step 4: For each PENDING order: call `connector.getOrder(orderId)`, update local order record
    - Step 5: For PENDING orders that are now filled: check if this completes a single-leg position → transition to OPEN
    - Step 6: For each active position: verify linked orders against platform (both legs)
    - Step 7: Detect discrepancies — any mismatch between local and platform state
    - Step 8: If discrepancies: flag positions as RECONCILIATION_REQUIRED, write `reconciliationContext` JSONB with recommended status + discrepancy details, halt trading
    - Step 9: If clean: recalculate risk budget from position count + capital deployed
    - Step 10: Emit appropriate events and log results
  - [x] 5.4 Implement `reconcilePendingOrders(): Promise<PendingOrderResult[]>` — isolated pending order check
  - [x] 5.5 Implement `reconcileActivePositions(): Promise<PositionReconciliationResult[]>` — position cross-reference
  - [x] 5.6 All platform API calls wrapped in try/catch with 10s timeout — a single API failure should not crash reconciliation for other positions
  - [x] 5.7 Add overall reconciliation timeout of 60s. If exceeded, log warning with partial results (positions checked so far, remaining), flag unchecked positions as `RECONCILIATION_REQUIRED` with reason "reconciliation_timeout", halt trading. Emit `ReconciliationCompleteEvent` with `partial: true` in summary.
  - [x] 5.8 Use `Decimal` for all financial calculations (capital deployed recalculation)

- [x] Task 6: Create `ReconciliationController` — operator resolution endpoint (AC: 5, 7)
  - [x] 6.1 Create `src/reconciliation/reconciliation.controller.ts`
  - [x] 6.2 `@Controller('api/reconciliation')` with `@UseGuards(AuthTokenGuard)`
  - [x] 6.3 `POST :id/resolve` — accepts `ResolveReconciliationDto { action: 'acknowledge' | 'force_close', rationale: string }`
  - [x] 6.4 `POST run` — triggers manual reconciliation by re-executing the full `reconcile()` flow (same logic as startup). Primary use case: after a previously-disconnected platform recovers. Returns the `ReconciliationResult` directly. **Debounce:** reject with 429 if last run completed <30s ago (check `lastRunAt` on the service) to prevent accidental double-triggers hitting platform rate limits.
  - [x] 6.5 `GET status` — returns in-memory last-run result (stored as class field on `StartupReconciliationService`, resets to null on restart). Includes: `lastRunAt`, `durationMs`, `summary`, plus any outstanding `RECONCILIATION_REQUIRED` positions from DB query
  - [x] 6.6 Standardized response wrapper: `{ data: result, timestamp }` for success
  - [x] 6.7 HTTP status codes: 200 for success, 404 for position not found, 409 for position not in RECONCILIATION_REQUIRED state
  - [x] 6.8 DTO validation class `resolve-reconciliation.dto.ts`: `action` field uses `@IsIn(['acknowledge', 'force_close'])`, `rationale` field uses `@IsString() @IsNotEmpty() @MinLength(10)` (require meaningful rationale)

- [x] Task 7: Integrate reconciliation into startup sequence (AC: 1)
  - [x] 7.1 Modify `EngineLifecycleService.onApplicationBootstrap()` to call `StartupReconciliationService.reconcile()` AFTER NTP validation, BEFORE logging "Engine startup complete"
  - [x] 7.2 If reconciliation finds discrepancies, log at `error` level and set `TradingEngineService.isHalted = true` (via event)
  - [x] 7.3 If reconciliation fails entirely (e.g., both platforms unreachable) AND active positions exist in DB: log critical error, halt trading via `haltTrading('reconciliation_discrepancy')`, allow engine to start (operator triggers manual reconciliation once platforms recover). **Rationale:** stale risk state + active trading = potential over-allocation. If no active positions exist, skip halt — nothing to reconcile.
  - [x] 7.3.1 Log warning: "Risk state may be stale — reconciliation could not verify positions against platforms"
  - [x] 7.4 **Ordering decision (FIRM):** `RiskManagerService.initializeStateFromDb()` runs first during `onModuleInit()` (existing behavior — do NOT change). Reconciliation runs later during `onApplicationBootstrap()` and calls `recalculateFromPositions()` to overwrite any stale values. This means risk state is initialized twice: once from raw DB state, once from reconciled state. This is correct — reconciliation is the authoritative final pass.

- [x] Task 8: Create `ReconciliationModule` and register in AppModule (AC: all)
  - [x] 8.1 Create directory `src/reconciliation/` and `src/reconciliation/reconciliation.module.ts` — a **dedicated module** (do NOT add to `PersistenceModule`). `PersistenceModule` is `@Global()` for `PrismaService` only; adding `ConnectorModule` and `RiskManagementModule` imports to it would expand its dependency surface and risk circular DI errors.
  - [x] 8.2 `ReconciliationModule` imports: `PersistenceModule` (for `PrismaService`, repositories), `ConnectorModule` (for connector tokens), `RiskManagementModule` (for `RISK_MANAGER_TOKEN`)
  - [x] 8.3 `ReconciliationModule` providers: `StartupReconciliationService`, controllers: `ReconciliationController`
  - [x] 8.4 Export `StartupReconciliationService` (for `EngineLifecycleService` to call during bootstrap)
  - [x] 8.5 Add `ReconciliationModule` to `AppModule` imports
  - [x] 8.6 Inject `StartupReconciliationService` into `EngineLifecycleService` (CoreModule must import `ReconciliationModule` or use `@Global()` export)

- [x] Task 9: Add `reconciliation_context` JSONB column to `open_positions` (AC: 3, 5)
  - [x] 9.1 Create Prisma migration adding `reconciliation_context Json?` column to `open_positions` table (nullable, default null)
  - [x] 9.2 Column stores: `{ recommendedStatus: PositionStatus, discrepancyType: string, platformState: object, detectedAt: string }` — written when a position is flagged `RECONCILIATION_REQUIRED`, read by `resolveDiscrepancy()` for `acknowledge` action
  - [x] 9.3 Define `ReconciliationContext` TypeScript interface in `src/common/types/reconciliation.types.ts` (or inline in the reconciliation service). Explicit shape prevents drift between write (Phase 3) and read (resolve endpoint):
    ```typescript
    interface ReconciliationContext {
      recommendedStatus: PositionStatus;
      discrepancyType: 'order_status_mismatch' | 'order_not_found' | 'pending_filled' | 'platform_unavailable';
      platformState: Record<string, unknown>; // raw API response snapshot — intentionally unstructured for MVP. Future stories consuming this field may want a discriminated union per platform.
      detectedAt: string; // ISO 8601
    }
    ```
  - [x] 9.4 Run `pnpm prisma generate` after migration

- [x] Task 10: Add `PositionRepository` query methods (AC: 1, 2, 4)
  - [x] 10.1 Add `findActivePositions()` — returns positions with status in `[OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL, RECONCILIATION_REQUIRED]` with includes for `pair`, `kalshiOrder`, `polymarketOrder`. The order includes are REQUIRED for capital calculation (uses `order.fillPrice` × `order.fillSize`).
  - [x] 10.2 `findByStatus(status)` already exists — verify it works for arrays of statuses or add `findByStatuses(statuses[])`. **Note:** `findActivePositions()` is effectively `findByStatuses([...])` with mandatory order includes. The dedicated method is justified because it encapsulates both the status filter AND the includes (which are required for capital calculation). If the generic method is sufficient with an `include` parameter, skip the dedicated method and use `findByStatuses()` with explicit includes at the call site.

- [x] Task 11: Add `OrderRepository` query methods (AC: 2)
  - [x] 11.1 Add `findPendingOrders()` — returns all orders with status `PENDING`
  - [x] 11.2 Add `updateOrderStatus(orderId, status, fillPrice?, fillSize?)` — updates order with fill data

- [x] Task 12: Tests (all ACs)
  - [x] 12.1 Unit tests for `StartupReconciliationService.reconcile()`: clean path (no discrepancies), pending order resolved, discrepancy detected, platform unavailable
  - [x] 12.2 Unit tests for `reconcilePendingOrders()`: order now filled → position transitions SINGLE_LEG_EXPOSED → OPEN, order now cancelled → no position change, order still pending → no change
  - [x] 12.3 Unit tests for `reconcileActivePositions()`: all match → clean, status mismatch → flag, order not found on platform → flag
  - [x] 12.4 Unit tests for `ReconciliationController`: resolve with acknowledge, resolve with force_close, manual run trigger, wrong position state
  - [x] 12.5 Unit tests for `getOrder()` on both connectors
  - [x] 12.6 Unit tests for `haltTrading()`, `resumeTrading()`, `recalculateFromPositions()` on RiskManagerService
  - [x] 12.7 All existing tests continue to pass. Baseline: 647 → Final: 731 (84 new tests). 53 test files.

## Dev Notes

### Architecture Constraints

- **Reconciliation lives in a dedicated `ReconciliationModule`** at `src/reconciliation/`. Although the architecture spec originally placed `startup-reconciliation.service.ts` in `persistence/`, a dedicated module is the correct approach because: (1) `PersistenceModule` is `@Global()` for `PrismaService` only — adding connector/risk-management imports would expand its dependency surface; (2) reconciliation depends on `ConnectorModule` + `RiskManagementModule` which `PersistenceModule` should never import; (3) avoids circular DI risk.
- **Module dependency rules:**
  - `ReconciliationModule` imports `PersistenceModule` (for `PrismaService`, repositories)
  - `ReconciliationModule` imports `ConnectorModule` (for connector tokens to query platform APIs)
  - `ReconciliationModule` imports `RiskManagementModule` (for `RISK_MANAGER_TOKEN` — halt/resume/recalculate)
  - `ReconciliationModule` exports `StartupReconciliationService` (for `EngineLifecycleService` to call)
  - All other existing module dependency rules remain unchanged
- **Fan-out is async:** `ReconciliationDiscrepancyEvent` and `ReconciliationCompleteEvent` are on the EventEmitter2 async path. Future consumers (Telegram alerts in Epic 6) subscribe.
- **Startup ordering is CRITICAL:** Reconciliation must run AFTER connectors are connected but BEFORE trading cycles start. The NestJS lifecycle order: `onModuleInit()` (all modules) → `onApplicationBootstrap()` (all modules). Connectors connect during `onModuleInit()`. Reconciliation runs during `EngineLifecycleService.onApplicationBootstrap()`.

### Reconciliation Flow

```
EngineLifecycleService.onApplicationBootstrap()
    |
    v
1. Database connectivity check (existing)
2. Configuration validation (existing)
3. NTP validation (existing)
4. *** Startup Reconciliation (NEW) ***
    |
    v
StartupReconciliationService.reconcile()
    |
    ├── Check connector health (both platforms)
    |   - If both disconnected → log critical, allow startup, operator triggers manual reconciliation later
    |   - If one disconnected → reconcile available platform, flag unavailable platform positions
    |
    ├── Phase 1: Pending Order Reconciliation
    |   For each Order with status PENDING:
    |   ├── connector.getOrder(orderId) → get current platform status
    |   ├── If now FILLED:
    |   |   1. Update Order record (status, fillPrice, fillSize)
    |   |   2. If associated position is SINGLE_LEG_EXPOSED and this was the missing leg:
    |   |      → Link order to position, transition position to OPEN
    |   |   3. Emit OrderFilledEvent
    |   |   4. Log: "Pending order filled after timeout"
    |   ├── If now CANCELLED/REJECTED:
    |   |   1. Update Order record
    |   |   2. Log: "Pending order cancelled/rejected on platform"
    |   └── If still PENDING:
    |       1. Log warning: "Order still pending on platform after restart"
    |       2. Keep in DB as PENDING (operator may need to cancel manually)
    |
    ├── Phase 2: Active Position Order-Level Verification
    |   For each OpenPosition with status in [OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL]:
    |   ├── For each linked order (kalshiOrder, polymarketOrder):
    |   |   ├── connector.getOrder(orderId) → verify order fill status matches local record
    |   |   ├── If mismatch → flag as discrepancy (type: 'order_status_mismatch')
    |   |   └── If order not found on platform → flag as discrepancy (type: 'order_not_found')
    |   ├── NOTE: This is ORDER-LEVEL verification only. getPositions() is not implemented.
    |   |   We verify each order individually, not the position as a portfolio-level concept.
    |   └── If position has no discrepancies → mark as verified
    |
    ├── Phase 3: Discrepancy Handling
    |   If any discrepancies found:
    |   ├── Flag each affected position as RECONCILIATION_REQUIRED
    |   ├── Write `reconciliationContext` JSONB to each position: { recommendedStatus, discrepancyType, platformState, detectedAt }
    |   ├── Emit ReconciliationDiscrepancyEvent per discrepancy
    |   ├── Emit SystemHealthError(4005, critical)
    |   └── Call riskManager.haltTrading('reconciliation_discrepancy')
    |
    └── Phase 4: Risk Budget Recalculation
        If clean (or after pending orders resolved):
        ├── Count actual OPEN + SINGLE_LEG_EXPOSED + EXIT_PARTIAL positions
        ├── Sum total capital deployed from position sizes
        ├── Call riskManager.recalculateFromPositions(count, capital)
        └── Emit ReconciliationCompleteEvent

5. Log "Engine startup complete" (existing)
6. Trading cycles begin
```

### Pending Order Reconciliation — CRITICAL

Story 5.1 established this pattern: when a Polymarket order times out after 5 seconds of polling, it is persisted with status `PENDING` and a warning is logged. The order may still fill on-chain after the timeout. This is the **highest-priority reconciliation scenario** — a pending order that filled means:

1. The system has real exposure on Polymarket that it doesn't know about
2. The associated position was created as `SINGLE_LEG_EXPOSED` (only the primary leg was recorded)
3. If the pending order filled, the position should actually be `OPEN` (both legs filled)

**To find the associated position:** The pending order's `pairId` matches the position's `pairId`. The position's null order FK (kalshiOrderId or polymarketOrderId) indicates which leg was the pending one. Update the position's null FK to point to the now-filled order and transition status to `OPEN`.

### `getOrder()` Implementation Details

**Kalshi:** The Kalshi SDK's `MarketApi` should have a `getOrder(orderId)` method. Map the response to our `OrderResult` type:
```typescript
// Kalshi order status mapping:
// 'resting' → 'pending'
// 'canceled' → 'cancelled'
// 'executed' → 'filled'
// 'pending' → 'pending'
// 'partial' → 'partial'  // partially filled — treat as discrepancy for reconciliation (unexpected state)
```
Use `rateLimiter.acquireRead()` before the API call. Wrap in `withRetry()` with `RETRY_STRATEGIES.NETWORK_ERROR`.

**Polymarket:** The `@polymarket/clob-client` has `getOrder(orderId)` or similar. Map response to `OrderResult`:
```typescript
// Polymarket CLOB order status mapping:
// 'MATCHED' → 'filled'
// 'LIVE' → 'pending' (order on book, not yet matched)
// 'CANCELED' → 'cancelled'
```
Use `rateLimiter.acquireRead()` before the call.

**Error handling:** If the order is not found on the platform (404/not found), this IS a discrepancy — log it and include in reconciliation result. Do NOT throw.

### Risk Budget Recalculation

After reconciliation resolves pending orders and verifies positions, the risk state may be stale (e.g., position count in `risk_states` table doesn't match actual `open_positions` count). The reconciliation service must force-update the risk state:

```typescript
// Count active positions from DB (findActivePositions() includes kalshiOrder + polymarketOrder relations)
const activePositions = await positionRepository.findActivePositions();

// Position count: EXCLUDE RECONCILIATION_REQUIRED (they're in limbo, not tradable)
const openCount = activePositions.filter(p =>
  ['OPEN', 'SINGLE_LEG_EXPOSED', 'EXIT_PARTIAL'].includes(p.status)
).length;

// Capital deployed: INCLUDE ALL active positions including RECONCILIATION_REQUIRED
// Rationale: RECONCILIATION_REQUIRED positions still have real capital on platforms.
// Excluding them from capital would allow over-allocation (new trades could exceed bankroll).
const capitalDeployed = activePositions.reduce((sum, pos) => {
  // Capital per leg = order.fillSize × order.fillPrice
  const kalshiCapital = pos.kalshiOrder?.fillPrice && pos.kalshiOrder?.fillSize
    ? new Decimal(pos.kalshiOrder.fillSize.toString()).mul(new Decimal(pos.kalshiOrder.fillPrice.toString()))
    : new Decimal(0);
  const polyCapital = pos.polymarketOrder?.fillPrice && pos.polymarketOrder?.fillSize
    ? new Decimal(pos.polymarketOrder.fillSize.toString()).mul(new Decimal(pos.polymarketOrder.fillPrice.toString()))
    : new Decimal(0);
  return sum.plus(kalshiCapital).plus(polyCapital);
}, new Decimal(0));

await riskManager.recalculateFromPositions(openCount, capitalDeployed);
```

**IMPORTANT — Use `Decimal` (decimal.js) for capital calculations.** Convert Prisma `Decimal` fields via `new Decimal(value.toString())`. Capital MUST be computed from linked order `fillPrice`/`fillSize`, NOT from `position.entryPrices` — the orders are the source of truth for actual fill data.

**IMPORTANT — `RECONCILIATION_REQUIRED` positions are excluded from `openPositionCount` (they don't count toward position limits since they're in limbo) but INCLUDED in `totalCapitalDeployed` (their capital is still on platforms — excluding it would allow over-allocation).**

### Connector Token Access Pattern

Same pattern as Stories 5.3 and 5.4:
```typescript
@Inject(KALSHI_CONNECTOR_TOKEN) private readonly kalshiConnector: IPlatformConnector,
@Inject(POLYMARKET_CONNECTOR_TOKEN) private readonly polymarketConnector: IPlatformConnector,
```

Import tokens from `src/connectors/connector.constants.ts`.

### Error Codes

Add to system health error codes:
```typescript
RECONCILIATION_DISCREPANCY: 4005,  // Platform state doesn't match local state after restart
```

### Halt Reason

Add to existing halt reasons:
```typescript
RECONCILIATION_DISCREPANCY: 'reconciliation_discrepancy',  // Trading halted due to unresolved reconciliation discrepancy
```

This halt reason is DISTINCT from `DAILY_LOSS_LIMIT`. The halt system uses `Set<HaltReason>` (not a single field) so overlapping halts are tracked independently. `resumeTrading(reason)` removes only the specified reason; trading resumes only when the set is empty. This prevents reconciliation resolution from accidentally clearing a daily loss halt (and vice versa).

### Existing Code to Build On

**EngineLifecycleService (engine-lifecycle.service.ts):**
- `onApplicationBootstrap()` — insertion point for reconciliation call (after NTP, before "startup complete" log)

**RiskManagerService (risk-manager.service.ts):**
- `initializeStateFromDb()` — already rebuilds risk state from DB on startup. Reconciliation's `recalculateFromPositions()` will overwrite stale values after reconciliation completes.
- `isTradingHalted()` / `tradingHalted` — halt mechanism to block trading during discrepancy resolution

**PositionRepository (position.repository.ts):**
- `findByStatus()` — query positions by status
- `findByStatusWithOrders()` — query with order includes (from Story 5.4)
- `updateStatus()` — transition position status

**OrderRepository (order.repository.ts):**
- `create()` — not needed (orders already exist)
- `findById()` — fetch specific order
- `updateStatus()` — update order status

**ExecutionService (execution.service.ts):**
- Lines 257-275: Pending order persistence for reconciliation (Story 5.1 reference)

**Platform Connectors:**
- Both have `getHealth()` returning `PlatformHealth` — check before reconciliation queries
- Both have `submitOrder()` and `getOrderBook()` as reference for API call patterns (rate limiting, error mapping, retry)
- Both have `getPositions()` stub (throws "not implemented") — NOT needed for this story since we use `getOrder()` per-order instead

**RiskOverrideController (risk-override.controller.ts):**
- Pattern for controller structure: `@Controller`, `@UseGuards(AuthTokenGuard)`, `@Body(new ValidationPipe({ whitelist: true }))`, standardized response format

**Event catalog (event-catalog.ts):**
- No reconciliation events exist yet — this story adds them

### Operator Resolution Flow

```
Operator → POST /api/reconciliation/:id/resolve { action: 'acknowledge', rationale: 'Verified fill on Kalshi dashboard' }
    ↓
Controller validates DTO, calls StartupReconciliationService.resolveDiscrepancy()
    ↓
Service fetches position (RECONCILIATION_REQUIRED status check)
    ↓
For 'acknowledge':
  - Read `reconciliationContext` JSONB column from the position record
  - Update position to `reconciliationContext.recommendedStatus` (e.g., OPEN, CLOSED)
  - Clear `reconciliationContext` column (set to null)
  - Log resolution with rationale
    ↓
For 'force_close':
  - Update position to CLOSED
  - Call riskManager.closePosition(capitalReturned, pnlDelta=0) — P&L unknown, operator accepts loss. **Known limitation:** daily P&L tracking will be inaccurate (real losses not captured). Operator should manually reconcile P&L via future audit/compliance tooling (Epic 6/12). Acceptable at MVP.
  - Log resolution with rationale
    ↓
Check if any RECONCILIATION_REQUIRED positions remain
  - If none → call riskManager.resumeTrading()
  - If some remain → trading stays halted
    ↓
Return { success: true, positionId, newStatus, remainingDiscrepancies }
```

### DoD Gates (from Epic 4.5 Retro Action Items)

1. **Test isolation** — all new tests must mock platform API calls, no live HTTP
2. **Interface preservation** — do not rename existing interface methods; add new ones alongside if needed
3. **Normalization ownership** — order data from `getOrder()` uses same price normalization as `submitOrder()` (Kalshi cents÷100, Polymarket already decimal)

### Project Structure Notes

**New files:**
- `src/reconciliation/reconciliation.module.ts`
- `src/reconciliation/startup-reconciliation.service.ts`
- `src/reconciliation/startup-reconciliation.service.spec.ts`
- `src/reconciliation/reconciliation.controller.ts`
- `src/reconciliation/reconciliation.controller.spec.ts`
- `src/reconciliation/resolve-reconciliation.dto.ts`
- `src/common/events/system.events.ts` — ReconciliationCompleteEvent, ReconciliationDiscrepancyEvent
- `src/common/events/system.events.spec.ts`

**Modified files:**
- `src/common/interfaces/platform-connector.interface.ts` — add `getOrder()`
- `src/common/interfaces/risk-manager.interface.ts` — add `haltTrading()`, `resumeTrading()`, `recalculateFromPositions()`
- `src/common/events/event-catalog.ts` — add reconciliation event names
- `src/common/errors/system-health-error.ts` — add error code 4005 (if codes are in this file, else the constants file)
- `src/modules/risk-management/risk-manager.service.ts` — implement new IRiskManager methods, add halt reason
- `src/modules/risk-management/risk-manager.service.spec.ts` — tests for new methods
- `src/connectors/kalshi/kalshi.connector.ts` — implement `getOrder()`
- `src/connectors/kalshi/kalshi.connector.spec.ts` — tests for `getOrder()`
- `src/connectors/polymarket/polymarket.connector.ts` — implement `getOrder()`
- `src/connectors/polymarket/polymarket.connector.spec.ts` — tests for `getOrder()`
- `src/persistence/repositories/position.repository.ts` — add `findActivePositions()`
- `src/persistence/repositories/order.repository.ts` — add `findPendingOrders()`, `updateOrderStatus()`
- `src/core/engine-lifecycle.service.ts` — add reconciliation call to `onApplicationBootstrap()`
- `src/app.module.ts` — import `ReconciliationModule`
- Prisma schema — add `reconciliation_context Json?` column to `open_positions`
- Multiple test files — update IPlatformConnector and IRiskManager mocks

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5, Story 5.5]
- [Source: _bmad-output/planning-artifacts/prd.md#Recovery Scenarios]
- [Source: _bmad-output/planning-artifacts/prd.md#Startup Reconciliation Protocol]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture — State Management & Crash Recovery]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure — startup-reconciliation.service.ts in persistence/]
- [Source: _bmad-output/planning-artifacts/architecture.md#Module Dependency Graph]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling]
- [Source: _bmad-output/planning-artifacts/architecture.md#Event Emission]
- [Source: _bmad-output/implementation-artifacts/5-1-order-submission-position-tracking.md#Fill Confirmation Model — Polymarket pending orders]
- [Source: _bmad-output/implementation-artifacts/5-2-single-leg-exposure-detection-alerting.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/5-3-single-leg-resolution-operator-actions.md#Budget Accounting on Close]
- [Source: _bmad-output/implementation-artifacts/5-4-exit-monitoring-fixed-threshold-exits.md#Dev Notes]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Event Emission, #Domain Rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (team of 4 specialized agents)

### Debug Log References

None — clean implementation, no blocking issues.

### Completion Notes List

- **Task 1 (interface-lead):** Added `getOrder(orderId): Promise<OrderStatusResult>` to IPlatformConnector. Implemented in KalshiConnector (Kalshi REST API with cents÷100 normalization) and PolymarketConnector (CLOB client). Updated 4 mock files. 11 connector tests added.
- **Task 2 (interface-lead):** Created `ReconciliationCompleteEvent` and `ReconciliationDiscrepancyEvent` in system.events.ts. Added to EVENT_NAMES with `system.*` prefix. 11 event tests added.
- **Task 3 (interface-lead):** Added `SYSTEM_HEALTH_ERROR_CODES.RECONCILIATION_DISCREPANCY = 4005`. Verified SystemHealthError accepts it.
- **Task 4 (risk-engineer):** Refactored halt state from single `haltReason` to `activeHaltReasons: Set<HaltReason>`. Added `haltTrading()`, `resumeTrading()`, `recalculateFromPositions()` to IRiskManager + RiskManagerService. Added `SYSTEM_TRADING_RESUMED` event. Backward-compatible DB persistence. Updated 4 mock files. Overlapping halt scenario tested. ~45 new/updated risk tests.
- **Task 5 (recon-engineer):** Full 4-phase StartupReconciliationService: connector health check → pending order reconciliation → active position verification → discrepancy handling/risk recalculation. resolveDiscrepancy() for operator resolution. 10s per-call timeout, 60s overall. Decimal math throughout. 27 unit tests.
- **Task 6 (api-engineer):** ReconciliationController with POST :id/resolve, POST run (30s debounce), GET status. ResolveReconciliationDto with class-validator. Standardized response wrappers. 9 unit tests.
- **Task 7 (recon-engineer):** Integrated reconcile() into EngineLifecycleService.onApplicationBootstrap() after NTP validation. Halt-on-failure with active positions check. 3 lifecycle tests.
- **Task 8 (recon-engineer):** ReconciliationModule importing ConnectorModule + RiskManagementModule. Registered in AppModule + CoreModule.
- **Task 9 (recon-engineer):** Prisma migration for `reconciliation_context Json?` on open_positions. ReconciliationContext type in reconciliation.types.ts.
- **Task 10 (recon-engineer):** Added findActivePositions() to PositionRepository with order includes.
- **Task 11 (recon-engineer):** Added findPendingOrders() and updateOrderStatus() to OrderRepository.
- **Task 12:** All tests verified — 731 passing across 53 files (84 new tests from baseline 647). Lint clean.

### File List

**New files:**
- `src/reconciliation/reconciliation.module.ts`
- `src/reconciliation/startup-reconciliation.service.ts`
- `src/reconciliation/startup-reconciliation.service.spec.ts`
- `src/reconciliation/reconciliation.controller.ts`
- `src/reconciliation/reconciliation.controller.spec.ts`
- `src/reconciliation/dto/resolve-reconciliation.dto.ts`
- `src/common/events/system.events.ts`
- `src/common/events/system.events.spec.ts`
- `src/common/types/reconciliation.types.ts`
- `prisma/migrations/YYYYMMDD_add_reconciliation_context/migration.sql`

**Modified files:**
- `src/common/interfaces/platform-connector.interface.ts` — added `getOrder()`
- `src/common/interfaces/risk-manager.interface.ts` — added `haltTrading()`, `resumeTrading()`, `recalculateFromPositions()`
- `src/common/types/platform.type.ts` — added `OrderStatusResult` type
- `src/common/types/index.ts` — re-exports
- `src/common/events/event-catalog.ts` — added RECONCILIATION_COMPLETE, RECONCILIATION_DISCREPANCY, SYSTEM_TRADING_RESUMED
- `src/common/errors/system-health-error.ts` — added SYSTEM_HEALTH_ERROR_CODES.RECONCILIATION_DISCREPANCY (4005)
- `src/common/errors/index.ts` — re-exports
- `src/modules/risk-management/risk-manager.service.ts` — halt state refactor (Set), new methods, HALT_REASONS
- `src/modules/risk-management/risk-manager.service.spec.ts` — updated + new tests
- `src/connectors/kalshi/kalshi.connector.ts` — implemented `getOrder()`
- `src/connectors/kalshi/kalshi.connector.spec.ts` — getOrder tests
- `src/connectors/polymarket/polymarket.connector.ts` — implemented `getOrder()`
- `src/connectors/polymarket/polymarket.connector.spec.ts` — getOrder tests
- `src/persistence/repositories/position.repository.ts` — added `findActivePositions()`
- `src/persistence/repositories/order.repository.ts` — added `findPendingOrders()`, `updateOrderStatus()`
- `src/core/engine-lifecycle.service.ts` — startup reconciliation call
- `src/core/engine-lifecycle.service.spec.ts` — lifecycle tests
- `src/app.module.ts` — imported ReconciliationModule
- `prisma/schema.prisma` — added reconciliation_context column
- `src/modules/execution/execution.service.spec.ts` — updated mocks
- `src/modules/execution/execution-queue.service.spec.ts` — updated mocks
- `src/modules/execution/single-leg-resolution.service.spec.ts` — updated mocks
- `src/modules/exit-management/exit-monitor.service.spec.ts` — updated mocks
- `src/modules/exit-management/exposure-alert-scheduler.service.spec.ts` — updated mocks
- `src/modules/risk-management/risk-override.controller.spec.ts` — updated mocks
- `src/core/core.module.ts` — imported ReconciliationModule
- `src/common/errors/system-health-error.spec.ts` — updated tests
