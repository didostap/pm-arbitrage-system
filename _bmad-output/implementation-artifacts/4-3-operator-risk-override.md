# Story 4.3: Operator Risk Override

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to manually approve trades that would exceed normal position limits when I have specific reasoning,
so that I can act on high-conviction opportunities while maintaining awareness of increased risk.

**FRs covered:** FR-RM-04 (operator can manually approve trades exceeding position limits with explicit confirmation)

## Acceptance Criteria

### AC1: Override Endpoint Approves Rejected Opportunities

**Given** an opportunity was rejected by `validatePosition()` due to position sizing or max open pairs limit
**When** the operator sends `POST /api/risk/override` with `{ opportunityId, rationale }` and a valid `Authorization: Bearer <token>` header
**Then** the risk manager internally re-runs the validation checks (halt check, open pairs check, position sizing) to determine the `originalRejectionReason`
**And** if the only rejection reasons are position sizing or max open pairs (not daily loss halt), the override is approved
**And** returns a `RiskDecision` with `approved: true`, `maxPositionSizeUsd` = `bankrollUsd * maxPositionPct` (full position cap, ignoring current capital deployed and open pairs), and `overrideApplied: true`
**And** an `OverrideAppliedEvent` is emitted via EventEmitter2 with operator rationale, original rejection reason, override amount, and timestamp
**And** the override is logged with: operator confirmation timestamp, original rejection reason, override amount, and operator rationale
**And** the response follows the standard API wrapper: `{ data: RiskDecision, timestamp: string }`

> **Design Note — originalRejectionReason:** The `processOverride` method internally re-runs the same validation logic as `validatePosition()` (halt check → open pairs check → position sizing check) to determine what *would* have failed. This avoids needing the operator to provide the reason and avoids storing/looking up previous rejections. The re-run is cheap (in-memory state only, no DB or API calls).

> **Design Note — opportunityId is trust-based (MVP):** The override does NOT verify that `opportunityId` refers to an actually-rejected opportunity. The operator is trusted (single-user system). They may override for any opportunity ID. This is acceptable for MVP — Epic 7's dashboard will add proper opportunity lookup when the UI wraps this endpoint. The story explicitly accepts this design choice.

### AC2: Daily Loss Halt Cannot Be Overridden

**Given** trading is halted due to daily loss limit breach (`tradingHalted === true` and `haltReason === 'daily_loss_limit'`)
**When** the operator sends `POST /api/risk/override`
**Then** the override is rejected with HTTP 403
**And** the response body is `{ error: { code: 3004, message: "Override denied: daily loss halt active", severity: "critical" }, timestamp: string }`
**And** the attempted override is logged as "denied: daily loss halt active" with the operator's rationale and opportunity ID
**And** no `OverrideAppliedEvent` is emitted

### AC3: Bearer Token Authentication

**Given** the dashboard API uses static Bearer token authentication (per architecture MVP decision)
**When** a request to `POST /api/risk/override` is missing the `Authorization` header or has an invalid token
**Then** the request is rejected with HTTP 401 `{ error: { code: 1001, message: "Unauthorized", severity: "error" }, timestamp: string }`
**And** no override processing occurs

**Given** the `OPERATOR_API_TOKEN` environment variable is configured
**When** the engine starts
**Then** the token is loaded via `@nestjs/config` and used by the `AuthTokenGuard` for all dashboard endpoints

### AC4: Override Request Validation

**Given** the operator sends `POST /api/risk/override`
**When** `opportunityId` is missing or empty
**Then** the request is rejected with HTTP 400 and validation error message
**When** `rationale` is missing, empty, or shorter than 10 characters
**Then** the request is rejected with HTTP 400 and validation error message explaining minimum rationale length

### AC5: Override Audit Trail

**Given** an override is processed (approved or denied)
**When** the processing completes
**Then** a `RiskOverrideLog` entry is persisted to the `risk_override_logs` table with:
  - `opportunityId`, `rationale`, `approved` (boolean), `originalRejectionReason`, `overrideAmountUsd` (if approved), `timestamp`, `denialReason` (if denied)
**And** the entry is queryable for future compliance review

### AC6: Override Event Emission

**Given** a successful override
**When** the risk decision is returned
**Then** an `OverrideAppliedEvent` is emitted with event name `risk.override.applied`
**And** the event contains: `opportunityId`, `rationale`, `originalLimit`, `overrideAmount`, `timestamp`

**Given** a denied override (daily loss halt)
**When** the denial is processed
**Then** an `OverrideDeniedEvent` is emitted with event name `risk.override.denied`
**And** the event contains: `opportunityId`, `rationale`, `denialReason`, `timestamp`

### AC7: RiskDecision Extended for Override

**Given** the `RiskDecision` type is returned from override processing
**When** an override is approved
**Then** the decision includes `overrideApplied: true` and `overrideRationale: string`
**And** the optional fields do not break existing non-override consumers (fields are optional)

### AC8: All Tests Pass

**Given** all Story 4.3 changes are complete
**When** `pnpm test` runs
**Then** all existing tests continue to pass (423 baseline from Story 4.2)
**And** new tests for operator risk override add 20+ test cases
**And** `pnpm lint` passes with no errors

## Tasks / Subtasks

- [x] Task 1: Prisma Migration — Add risk_override_logs table (AC: #5)
  - [x] 1.1 Add `RiskOverrideLog` model to `prisma/schema.prisma` with fields: `id` (autoincrement), `opportunityId String`, `rationale String`, `approved Boolean`, `originalRejectionReason String`, `overrideAmountUsd Decimal?`, `denialReason String?`, `createdAt DateTime @default(now()) @map("created_at")`
  - [x] 1.2 Map table to `risk_override_logs` via `@@map("risk_override_logs")`
  - [x] 1.3 Run `pnpm prisma migrate dev --name add-risk-override-logs`
  - [x] 1.4 Run `pnpm prisma generate`

- [x]Task 2: Add OPERATOR_API_TOKEN Environment Variable (AC: #3)
  - [x]2.1 Add `OPERATOR_API_TOKEN=dev-token-change-me` to `.env.example` with comment
  - [x]2.2 Add `OPERATOR_API_TOKEN=dev-token-change-me` to `.env.development`
  - [x]2.3 Add `OPERATOR_API_TOKEN=test-token` to all e2e test env setups (`test/app.e2e-spec.ts`, `test/core-lifecycle.e2e-spec.ts`, `test/logging.e2e-spec.ts`)

- [x]Task 3: Create AuthTokenGuard (AC: #3)
  - [x]3.1 Create `src/common/guards/auth-token.guard.ts` implementing `CanActivate`
  - [x]3.2 Inject `ConfigService`, read `OPERATOR_API_TOKEN` from config
  - [x]3.3 Extract `Authorization: Bearer <token>` from request header, compare against config token
  - [x]3.4 Return `false` (triggers 401) if missing or invalid
  - [x]3.5 Create `src/common/guards/auth-token.guard.spec.ts` with unit tests

- [x]Task 4: Add Override Event Classes (AC: #6)
  - [x]4.1 Add `OverrideAppliedEvent` class to `src/common/events/risk.events.ts` with fields: `opportunityId`, `rationale`, `originalLimit`, `overrideAmount`, `timestamp`
  - [x]4.2 Add `OverrideDeniedEvent` class to `src/common/events/risk.events.ts` with fields: `opportunityId`, `rationale`, `denialReason`, `timestamp`
  - [x]4.3 Add `OVERRIDE_APPLIED = 'risk.override.applied'` and `OVERRIDE_DENIED = 'risk.override.denied'` to event catalog (`src/common/events/event-catalog.ts`)

- [x]Task 5: Add Override Error Code (AC: #2)
  - [x]5.1 Add `OVERRIDE_DENIED_HALT_ACTIVE = 3004` to `RISK_ERROR_CODES` in `src/common/errors/risk-limit-error.ts`

- [x]Task 6: Extend RiskDecision Type (AC: #7)
  - [x]6.1 Add optional `overrideApplied?: boolean` and `overrideRationale?: string` to `RiskDecision` in `src/common/types/risk.type.ts`

- [x]Task 7: Create Override DTO (AC: #4)
  - [x]7.1 Create `src/modules/risk-management/dto/risk-override.dto.ts` with `class-validator` decorators
  - [x]7.2 Fields: `opportunityId: string` (`@IsString()`, `@IsNotEmpty()`), `rationale: string` (`@IsString()`, `@MinLength(10)`)
  - [x]7.3 Create `src/modules/risk-management/dto/risk-override.dto.spec.ts` with validation tests

- [x]Task 8: Add `processOverride` to IRiskManager Interface (AC: #1)
  - [x]8.1 Add `processOverride(opportunityId: string, rationale: string): Promise<RiskDecision>` to `IRiskManager` in `src/common/interfaces/risk-manager.interface.ts`

- [x]Task 9: Implement `processOverride` in RiskManagerService (AC: #1, #2, #5, #6)
  - [x]9.1 Add `processOverride(opportunityId: string, rationale: string): Promise<RiskDecision>` method
  - [x]9.2 Internally re-run validation checks to determine `originalRejectionReason`: check halt state, open pairs, position sizing — same logic as `validatePosition()` but capture rejection reason string instead of returning
  - [x]9.3 FIRST check: if `this.tradingHalted && this.haltReason === HALT_REASONS.DAILY_LOSS_LIMIT` → deny override, emit `OverrideDeniedEvent`, log to `risk_override_logs` (with `originalRejectionReason: 'Trading halted: daily loss limit breached'`), return denied decision
  - [x]9.4 If not halted: calculate override position size as `bankrollUsd * maxPositionPct` (full cap — always the maximum position size regardless of which limit was originally hit; ignores current capital deployed and open pairs count)
  - [x]9.5 Emit `OverrideAppliedEvent` with `originalRejectionReason` and override amount
  - [x]9.6 Log override to `risk_override_logs` table via Prisma (including `originalRejectionReason` from step 9.2)
  - [x]9.7 Return `RiskDecision` with `approved: true`, `overrideApplied: true`, `overrideRationale: rationale`

- [x]Task 10: Create RiskOverrideController (AC: #1, #2, #3, #4)
  - [x]10.1 Create `src/modules/risk-management/risk-override.controller.ts`
  - [x]10.2 Use `@Controller('api/risk')` at class level — sets the route prefix for all methods in this controller. This is the **first controller in risk module** and sets the pattern for future risk endpoints.
  - [x]10.3 Apply `@UseGuards(AuthTokenGuard)` at controller class level (all risk endpoints need auth)
  - [x]10.4 Implement `@Post('override')` with `@HttpCode(200)` — NestJS POST defaults to 201; we want 200 for override responses
  - [x]10.5 Use `@Body(new ValidationPipe({ whitelist: true }))` with `RiskOverrideDto`
  - [x]10.6 Inject `IRiskManager` via `@Inject(RISK_MANAGER_TOKEN)`
  - [x]10.7 Call `riskManager.processOverride(dto.opportunityId, dto.rationale)`
  - [x]10.8 On daily loss halt denial (detect via `decision.approved === false` and decision reason containing "daily loss"): return 403 with error wrapper `{ error: { code, message, severity }, timestamp }`
  - [x]10.9 On success: return 200 with `{ data: riskDecision, timestamp: new Date().toISOString() }`
  - [x]10.10 Add try/catch around the `processOverride` call — on unexpected errors (DB failure, etc.), return 500 with `{ error: { code: 4000, message: "Internal error processing override", severity: "error" }, timestamp }` and log the error
  - [x]10.11 Create `src/modules/risk-management/risk-override.controller.spec.ts` with unit tests

- [x]Task 11: Register Controller in RiskManagementModule (AC: #1)
  - [x]11.1 Add `RiskOverrideController` to `controllers` array in `risk-management.module.ts`
  - [x]11.2 Add `AuthTokenGuard` to `providers` if needed (or rely on global guard registration)

- [x]Task 12: Write Tests (AC: #8)
  - [x]12.1 Test: `processOverride` returns approved decision when no halt active
  - [x]12.2 Test: `processOverride` returns denied when daily loss halt active
  - [x]12.3 Test: `processOverride` emits `OverrideAppliedEvent` on success
  - [x]12.4 Test: `processOverride` emits `OverrideDeniedEvent` on daily loss denial
  - [x]12.5 Test: `processOverride` persists override log to DB on success
  - [x]12.6 Test: `processOverride` persists denial log to DB on denial
  - [x]12.7 Test: `processOverride` sets `overrideApplied: true` in returned decision
  - [x]12.8 Test: `processOverride` sets `overrideRationale` in returned decision
  - [x]12.8b Test: `processOverride` correctly derives `originalRejectionReason` by internal re-run (e.g., "Max open pairs exceeded" when open pairs at limit)
  - [x]12.8c Test: `processOverride` returns full position cap (`bankrollUsd * maxPositionPct`) regardless of current capital deployed
  - [x]12.9 Test: controller returns 403 when daily loss halt active
  - [x]12.10 Test: controller returns 401 when Bearer token missing
  - [x]12.11 Test: controller returns 401 when Bearer token invalid
  - [x]12.12 Test: controller returns 400 when opportunityId missing
  - [x]12.13 Test: controller returns 400 when rationale too short
  - [x]12.14 Test: controller returns 200 with standard wrapper on success
  - [x]12.14b Test: controller returns 500 with error wrapper when processOverride throws unexpected error
  - [x]12.15 Test: AuthTokenGuard allows valid token
  - [x]12.16 Test: AuthTokenGuard rejects missing Authorization header
  - [x]12.17 Test: AuthTokenGuard rejects invalid token
  - [x]12.18 Test: DTO validation rejects empty opportunityId
  - [x]12.19 Test: DTO validation rejects rationale < 10 chars
  - [x]12.20 Test: DTO validation accepts valid input
  - [x]12.21 Run full regression: `pnpm test` — all tests pass

- [x]Task 13: Lint & Final Check (AC: #8)
  - [x]13.1 Run `pnpm lint` and fix any issues
  - [x]13.2 Verify no import boundary violations per CLAUDE.md rules

## Dev Notes

### Architecture Constraints

- `RiskManagerService` lives in `src/modules/risk-management/` — same file modified from Stories 4.1 and 4.2
- `RiskOverrideController` is a NEW file in `src/modules/risk-management/` — this is the **first REST controller** in the risk module
- Allowed imports per CLAUDE.md dependency rules:
  - `modules/risk-management/` → `common/` (interfaces, errors, events, types, guards)
  - `modules/risk-management/` → `persistence/` (via globally exported PrismaService)
  - `core/` → `modules/risk-management/` (orchestrates via IRiskManager interface)
- **FORBIDDEN:** `risk-management/` must NOT import from `connectors/`, `modules/execution/`, or any other module directly
- The controller lives inside `risk-management/` module, NOT in `dashboard/` — this is a risk management endpoint, not a dashboard endpoint

### Authentication Pattern (MVP)

Per architecture doc (section "Authentication & Security"):
- Static Bearer token in `Authorization: Bearer <token>` header
- Token stored in `OPERATOR_API_TOKEN` environment variable
- Stateless validation on every request
- No login UI, no session management, no cookies
- **No auth guard exists yet** — `src/common/guards/` directory is empty. This story creates the first one.
- Phase 1 adds JWT with proper session management

Implementation:
```typescript
// src/common/guards/auth-token.guard.ts
@Injectable()
export class AuthTokenGuard implements CanActivate {
  constructor(private configService: ConfigService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const authHeader = request.headers['authorization'];
    if (!authHeader?.startsWith('Bearer ')) return false;
    const token = authHeader.slice(7);
    return token === this.configService.get<string>('OPERATOR_API_TOKEN');
  }
}
```

### Override Logic — What It Actually Does

The override does NOT re-run the full detection pipeline. It allows the operator to say "I've seen this rejected opportunity and I want to proceed anyway." The `processOverride` method:

1. **Internally re-runs validation checks** to determine `originalRejectionReason` — same checks as `validatePosition()` (halt → open pairs → position sizing) but captures the reason string instead of returning a rejection. This is cheap: all state is in-memory (no DB/API calls). Extract this logic into a private helper (e.g., `private determineRejectionReason(): string | null`) to avoid duplication with `validatePosition()`.
2. Checks if daily loss halt is active → if so, hard deny (no bypass allowed)
3. If not halted, returns an approved `RiskDecision` with:
   - `approved: true`
   - `maxPositionSizeUsd` = `bankrollUsd * maxPositionPct` — **always the full position cap**, regardless of which limit was originally hit. The override gives the operator the maximum allowed position size, ignoring current capital deployed and open pairs count.
   - `overrideApplied: true`
   - `overrideRationale: rationale`
4. Logs the override to `risk_override_logs` table (including the derived `originalRejectionReason`)
5. Emits appropriate event

> **Note:** The actual trade execution using this override decision happens in Epic 5. This story creates the mechanism; execution integration will wire it in.

### Controller Route Convention

Use NestJS class-level `@Controller('api/risk')` prefix pattern:
```typescript
@Controller('api/risk')
@UseGuards(AuthTokenGuard)
export class RiskOverrideController {
  @Post('override')
  async override(@Body(new ValidationPipe({ whitelist: true })) dto: RiskOverrideDto) { ... }
}
```
This sets the pattern for future risk endpoints (e.g., `GET /api/risk/exposure` in Epic 7). Method decorators use the sub-path only.

### Controller Error Handling

The controller wraps `processOverride` in try/catch for unexpected failures:
```typescript
try {
  const decision = await this.riskManager.processOverride(dto.opportunityId, dto.rationale);
  if (!decision.approved) {
    return res.status(403).send({ error: { code: 3004, message: decision.reason, severity: 'critical' }, timestamp: new Date().toISOString() });
  }
  return { data: decision, timestamp: new Date().toISOString() };
} catch (error) {
  this.logger.error({ message: 'Override processing failed', data: { opportunityId: dto.opportunityId, error: error.message } });
  return res.status(500).send({ error: { code: 4000, message: 'Internal error processing override', severity: 'error' }, timestamp: new Date().toISOString() });
}
```

### Daily Loss Halt Override Denial

Story 4.2 established `HALT_REASONS` as an extensible constant:
```typescript
const HALT_REASONS = {
  DAILY_LOSS_LIMIT: 'daily_loss_limit',
} as const;
```

The override denial check is specifically against `HALT_REASONS.DAILY_LOSS_LIMIT`. Future halt reasons (e.g., operator-initiated halt) may or may not be overridable — that's a future story decision.

### Error Code Assignment

- `RISK_ERROR_CODES.OVERRIDE_DENIED_HALT_ACTIVE = 3004` — new code for this story
- Existing codes: 3001 (Position Size Exceeded), 3002 (Max Open Pairs Exceeded), 3003 (Daily Loss Limit Breached)

### Prisma Schema — risk_override_logs Table

```prisma
model RiskOverrideLog {
  id                     Int      @id @default(autoincrement())
  opportunityId          String   @map("opportunity_id")
  rationale              String
  approved               Boolean
  originalRejectionReason String  @map("original_rejection_reason")
  overrideAmountUsd      Decimal? @map("override_amount_usd") @db.Decimal(18, 8)
  denialReason           String?  @map("denial_reason")
  createdAt              DateTime @default(now()) @map("created_at")

  @@map("risk_override_logs")
}
```

### NestJS Validation Setup

The project should already have `class-validator` and `class-transformer` installed (NestJS defaults). If not:
```bash
pnpm add class-validator class-transformer
```

For the DTO validation to work, ensure the `ValidationPipe` is applied either globally in `main.ts` or locally on the endpoint. Since this is the first REST endpoint with body validation, prefer local application via `@Body(new ValidationPipe({ whitelist: true }))`. No global pipe exists yet — do NOT add one (keep it local to avoid impacting other modules).

### Standard API Response Wrapper

Per architecture, all REST endpoints return:
```typescript
// Success
{ data: T, timestamp: string }

// Error
{ error: { code: number, message: string, severity: string }, timestamp: string }
```

The controller should handle this wrapping manually (no global interceptor for error responses yet — the `response-wrapper.interceptor.ts` referenced in architecture doesn't exist yet).

### What NOT to Do (Scope Guard)

- Do NOT implement execution locking or budget reservation — that's Story 4.4
- Do NOT implement correlation cluster tracking — that's Epic 9
- Do NOT implement the dashboard UI for overrides — that's Epic 7 (Story 7.3)
- Do NOT implement Telegram alerting for override events — that's Epic 6 (monitoring subscribes to events)
- Do NOT implement any WebSocket push for override events — that's Epic 7
- Do NOT implement max drawdown halt or other halt reasons — future stories
- Do NOT make the auth guard global — only apply to endpoints that need it
- Do NOT implement rate limiting on the override endpoint — future concern
- Do NOT add Swagger decorators — Epic 7 will add `@nestjs/swagger` when the full dashboard API is built

### Existing Codebase Patterns to Follow

- **File naming:** kebab-case (`risk-override.controller.ts`, `auth-token.guard.ts`)
- **Module registration:** See `risk-management.module.ts` — add controller to `controllers` array
- **Logging:** NestJS `Logger` with structured JSON: `this.logger.log({ message, correlationId, data })`
- **Config access:** `ConfigService` from `@nestjs/config`
- **Prisma access:** Inject `PrismaService` directly (globally available via `@Global()`)
- **Event emission:** `this.eventEmitter.emit(EVENT_NAMES.OVERRIDE_APPLIED, new OverrideAppliedEvent(...))`
- **Error class:** `RiskLimitError` with `RISK_ERROR_CODES.OVERRIDE_DENIED_HALT_ACTIVE` (3004)
- **Test framework:** Vitest + `Test.createTestingModule()` from `@nestjs/testing`
- **Decimal math:** Use `FinancialDecimal` from `common/utils/financial-math.ts` for monetary calculations
- **DI token:** `RISK_MANAGER_TOKEN` from existing module pattern
- **Dev notes from 4.2:** `ConfigService.get` returns strings — use `Number()` conversion
- **Dev notes from 4.2:** `PrismaService` import path is `../../common/prisma.service` (not `../../persistence/`)

### Dependencies

| Package | Purpose | Installed In |
|---------|---------|-------------|
| `class-validator` | DTO validation decorators | Verify in package.json, add if missing |
| `class-transformer` | DTO transformation | Verify in package.json, add if missing |
| All other deps | Same as Stories 4.1/4.2 | Already installed |

### Previous Story Intelligence (4.2)

- **423 tests passing** — regression gate baseline
- `HALT_REASONS` constant is extensible — future halt reasons can be added
- `tradingHalted` + `haltReason` infrastructure is in place
- `persistState()` handles DB failures gracefully (no rollback)
- `FinancialDecimal` used for all monetary calculations
- Midnight reset only clears halt if `haltReason === HALT_REASONS.DAILY_LOSS_LIMIT`
- `LimitBreachedEvent` and `LimitApproachedEvent` patterns established — follow same event class structure for override events
- `EVENT_NAMES` catalog pattern established — add override events to same file
- **Code review fixes from 4.2:** eslint-disable pragmas need comments explaining why

### Git Intelligence

Recent engine commits follow pattern: `feat: <description>`. Story 4.3 should use:
- `feat: add operator risk override endpoint with bearer token authentication`

Last commit: `feat: add daily loss limit configuration and trading halt functionality to risk management module` (Story 4.2)

### Testing Strategy

- **New test files:**
  - `src/common/guards/auth-token.guard.spec.ts` — unit tests for the guard
  - `src/modules/risk-management/risk-override.controller.spec.ts` — controller unit tests
  - `src/modules/risk-management/dto/risk-override.dto.spec.ts` — DTO validation tests
- **Extended test file:**
  - `src/modules/risk-management/risk-manager.service.spec.ts` — add `processOverride` tests
- Mock `PrismaService` with mock `riskOverrideLog.create` — same mock pattern as existing tests
- Mock `ConfigService.get()` to return `OPERATOR_API_TOKEN`
- Mock `EventEmitter2.emit()` to verify both `OverrideAppliedEvent` and `OverrideDeniedEvent` emission
- Test the controller with mocked `IRiskManager` — inject via `RISK_MANAGER_TOKEN`
- Test the guard with mocked `ConfigService` and `ExecutionContext`
- Do NOT use a real database — unit tests only with mocked Prisma

### Project Structure Notes

New files:
```
src/common/guards/auth-token.guard.ts                    (NEW — first auth guard)
src/common/guards/auth-token.guard.spec.ts               (NEW)
src/modules/risk-management/risk-override.controller.ts   (NEW — first controller in risk module)
src/modules/risk-management/risk-override.controller.spec.ts (NEW)
src/modules/risk-management/dto/risk-override.dto.ts      (NEW — first DTO in risk module)
src/modules/risk-management/dto/risk-override.dto.spec.ts (NEW)
prisma/migrations/<timestamp>_add_risk_override_logs/migration.sql (NEW)
```

Modified files:
```
prisma/schema.prisma                                    (add RiskOverrideLog model)
src/common/events/risk.events.ts                        (add OverrideAppliedEvent, OverrideDeniedEvent)
src/common/events/event-catalog.ts                      (add OVERRIDE_APPLIED, OVERRIDE_DENIED)
src/common/errors/risk-limit-error.ts                   (add OVERRIDE_DENIED_HALT_ACTIVE: 3004)
src/common/types/risk.type.ts                           (add overrideApplied?, overrideRationale? to RiskDecision)
src/common/interfaces/risk-manager.interface.ts         (add processOverride method)
src/modules/risk-management/risk-manager.service.ts     (implement processOverride)
src/modules/risk-management/risk-manager.service.spec.ts (add override tests)
src/modules/risk-management/risk-management.module.ts   (add controller registration)
.env.example                                            (add OPERATOR_API_TOKEN)
.env.development                                        (add OPERATOR_API_TOKEN)
test/app.e2e-spec.ts                                    (add OPERATOR_API_TOKEN env var)
test/core-lifecycle.e2e-spec.ts                         (add OPERATOR_API_TOKEN env var)
test/logging.e2e-spec.ts                                (add OPERATOR_API_TOKEN env var)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3 — acceptance criteria, lines 676-700]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2 — daily loss halt cannot be overridden constraint]
- [Source: _bmad-output/planning-artifacts/prd.md#FR-RM-04 — operator can manually approve trades exceeding position limits]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security — static Bearer token, OPERATOR_API_TOKEN, auth-token.guard.ts]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Wrapper — { data: T, timestamp } format]
- [Source: _bmad-output/planning-artifacts/architecture.md#Dashboard API — REST endpoint patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Validation — class-validator at system boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure — common/guards/auth-token.guard.ts planned]
- [Source: pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts — HALT_REASONS constant, tradingHalted infrastructure]
- [Source: pm-arbitrage-engine/src/common/interfaces/risk-manager.interface.ts — IRiskManager to extend]
- [Source: pm-arbitrage-engine/src/common/types/risk.type.ts — RiskDecision to extend]
- [Source: pm-arbitrage-engine/src/common/events/risk.events.ts — event class patterns to follow]
- [Source: pm-arbitrage-engine/src/modules/risk-management/risk-management.module.ts — module to add controller]
- [Source: _bmad-output/implementation-artifacts/4-2-daily-loss-limit-trading-halt.md — previous story patterns, dev notes, 423 test baseline]
- [Source: CLAUDE.md#Module Dependency Rules — risk-management allowed imports]
- [Source: CLAUDE.md#Error Handling — SystemError hierarchy]
- [Source: CLAUDE.md#API Response Format — standardized wrappers]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- BUDGET_RESERVATION_FAILED code conflict: existing code used 3004 (Story 4.4 placeholder). Reassigned to 3005, OVERRIDE_DENIED_HALT_ACTIVE takes 3004 per story spec.
- Circular import avoided: extracted RISK_MANAGER_TOKEN to `risk-management.constants.ts` to prevent controller↔module circular dependency.
- Controller uses HttpException throws (not @Res) for status codes — avoids Fastify type dependency.

### Completion Notes List

- All 13 tasks and subtasks completed
- 447 tests passing (423 baseline + 24 new: 9 processOverride, 5 guard, 6 DTO, 3 controller, 1 extra guard)
- Lint passes clean, no import boundary violations
- OverrideAppliedEvent field named `originalRejectionReason` (not `originalLimit` as in AC6) to match actual implementation — contains the rejection reason string, not a numeric limit

### Change Log

- 2026-02-17: Story 4.3 implementation complete — operator risk override endpoint with bearer token auth
- 2026-02-17: Code review fixes applied (H1: removed dead halt check in determineRejectionReason, M1: added dailyPnl to approved override return, M2: added riskOverrideLog mock to e2e tests, M3: eliminated double invocations in controller tests)

### File List

New files:
- pm-arbitrage-engine/src/common/guards/auth-token.guard.ts
- pm-arbitrage-engine/src/common/guards/auth-token.guard.spec.ts
- pm-arbitrage-engine/src/modules/risk-management/risk-override.controller.ts
- pm-arbitrage-engine/src/modules/risk-management/risk-override.controller.spec.ts
- pm-arbitrage-engine/src/modules/risk-management/dto/risk-override.dto.ts
- pm-arbitrage-engine/src/modules/risk-management/dto/risk-override.dto.spec.ts
- pm-arbitrage-engine/src/modules/risk-management/risk-management.constants.ts
- pm-arbitrage-engine/prisma/migrations/20260217095207_add_risk_override_logs/migration.sql

Modified files:
- pm-arbitrage-engine/prisma/schema.prisma (added RiskOverrideLog model)
- pm-arbitrage-engine/src/common/events/risk.events.ts (added OverrideAppliedEvent, OverrideDeniedEvent)
- pm-arbitrage-engine/src/common/events/event-catalog.ts (added OVERRIDE_APPLIED, OVERRIDE_DENIED)
- pm-arbitrage-engine/src/common/errors/risk-limit-error.ts (added OVERRIDE_DENIED_HALT_ACTIVE: 3004, bumped BUDGET_RESERVATION_FAILED to 3005)
- pm-arbitrage-engine/src/common/types/risk.type.ts (added overrideApplied?, overrideRationale? to RiskDecision)
- pm-arbitrage-engine/src/common/interfaces/risk-manager.interface.ts (added processOverride method)
- pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts (implemented processOverride, determineRejectionReason)
- pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.spec.ts (added 9 processOverride tests + riskOverrideLog mock)
- pm-arbitrage-engine/src/modules/risk-management/risk-management.module.ts (added controller, AuthTokenGuard provider, re-exported token)
- pm-arbitrage-engine/.env.example (added OPERATOR_API_TOKEN)
- pm-arbitrage-engine/.env.development (added OPERATOR_API_TOKEN)
- pm-arbitrage-engine/test/app.e2e-spec.ts (added OPERATOR_API_TOKEN env var)
- pm-arbitrage-engine/test/core-lifecycle.e2e-spec.ts (added OPERATOR_API_TOKEN env var)
- pm-arbitrage-engine/test/logging.e2e-spec.ts (added OPERATOR_API_TOKEN env var)
