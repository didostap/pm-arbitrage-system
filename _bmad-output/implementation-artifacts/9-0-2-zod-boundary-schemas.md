# Story 9.0.2: Zod Boundary Schemas

Status: DONE

<!-- Pre-Epic 9 Tech Debt Sprint (Part 2 of 2).
     Source: sprint-status.yaml line 166 — "Tech debt: runtime validation at system boundaries (env vars, JSON fields, API responses)"
     Split rationale: Story 9-0-1 addressed compile-time type safety (branded IDs) and calibration persistence;
     this story addresses runtime validation at untrusted-data boundaries. Independent concerns. -->

## Story

As an operator and developer,
I want runtime validation via Zod schemas at every system boundary where untrusted data enters the application (environment variables, Prisma JSON fields, external API responses),
So that malformed configuration fails fast at startup, corrupted database JSON is caught before it propagates, and unexpected platform API responses throw structured errors instead of silently producing undefined values — hardening the system before Epic 9's complex correlation tracking.

## Acceptance Criteria

### Part A: Environment Variable Validation (Fail-Fast at Startup)

1. **Given** a Zod schema exists at `src/common/config/env.schema.ts` defining every environment variable used by the application (~60 variables across 13 config groups)
   **When** `ConfigModule.forRoot()` is configured with `validate: (env) => envSchema.parse(env)`
   **Then** the NestJS application fails to start with a clear `ZodError` listing every invalid/missing variable
   **And** the schema uses `z.coerce.number()` for numeric env vars, `z.enum()` for constrained strings, `z.string().url()` for URLs, and `z.string().min(1)` for required secrets
   [Source: app.module.ts lines 28-31 — current ConfigModule has no validate function; architecture.md directory tree — prescribes `validation.schema.ts` (Joi/Zod); .env.example — complete list of 60+ env vars]

2. **Given** typed config interfaces exist at `src/common/config/env.types.ts` inferred from the Zod schema via `z.infer<typeof envSchema>`
   **When** services access config via `ConfigService`
   **Then** `configService.get('RISK_BANKROLL_USD')` returns the Zod-coerced type (e.g., `string` for Decimal-destined values, `number` for integer values)
   **And** all 60+ `configService.get<Type>()` calls across the codebase are type-safe against the inferred schema type
   [Source: Investigation found 60+ untyped `configService.get()` calls across 40+ files]

3. **Given** a `TypedConfigService` type alias exists (`ConfigService<Env, true>`) and new config access patterns use it
   **When** a developer adds a new env var to the application but forgets to add it to `env.schema.ts`
   **Then** TypeScript compilation catches the missing key when `typedConfigService.get('NEW_VAR')` is used (the key is not in the inferred type)
   **And** a typed config helper `getEnvConfig(configService: ConfigService): Env` is available for one-shot access
   **Note:** Migrating all 60+ existing `configService.get()` calls to the typed variant is recommended but NOT required in this story — new code and modified files should use the typed pattern; remaining calls can be migrated incrementally.
   [Source: architecture.md line ~457 — prescribes `config.types.ts` for typed config interfaces]

### Part B: Prisma JSON Field Validation

4. **Given** Zod schemas exist for every Prisma JSON field structure used in the codebase (entryPrices, sizes, tiers, boundaryAnalysis, recommendations, reconciliationContext, haltReason, bids/asks, details)
   **When** services read JSON fields from Prisma query results
   **Then** each JSON field is validated through its Zod schema before use, replacing bare `as` type casts
   **And** validation failures throw `SystemHealthError` (code 4500) with severity `critical` — appropriate for financial data corruption where wrong JSON shapes could produce incorrect position sizes or P&L calculations
   **And** the calling service emits a `system.data-corruption.detected` event (via `DataCorruptionDetectedEvent` class) with field name, model, record ID, and raw value
   [Source: dashboard.service.ts lines 355/418/592 — `entryPrices as { kalshi: string; polymarket: string }`; calibration.service.ts lines 88-93 — `tiers as unknown as CalibrationResult['tiers']`; single-leg-resolution.service.ts line 99 — `sizes as { kalshi: string; polymarket: string }`; risk-manager.service.ts line 176 — `JSON.parse(state.haltReason)`; Story 9-0-1 completion note #3: "Story 9-0-2 (Zod) will add runtime validation for these JSON fields"]

5. **Given** the `CalibrationRun` model has 3 JSON fields (tiers, boundaryAnalysis, recommendations)
   **When** `CalibrationService.onModuleInit()` hydrates `latestResult` from DB
   **Then** each JSON field is validated against its Zod schema before assignment to the typed `CalibrationResult`
   **And** the `as unknown as CalibrationResult['tiers']` double cast in `calibration.service.ts` is replaced with `calibrationTiersSchema.parse(run.tiers)`
   [Source: calibration.service.ts lines 88-90, 265-267; Story 9-0-1 completion note #3]

### Part C: External API Response Validation

6. **Given** Zod schemas exist for Kalshi REST API response shapes (order status, order submission, account limits)
   **When** `KalshiConnector` receives a response from the Kalshi API
   **Then** the response is validated through its Zod schema before extracting fields
   **And** validation failures throw `PlatformApiError` (code 1007: "Unexpected API Response Schema") with the raw response attached for debugging
   [Source: kalshi.connector.ts lines 127-132 — `as unknown as KalshiOrdersApi`; PRD error code 1007 — Critical, "No retry, halt trading"]

7. **Given** Zod schemas exist for Polymarket REST API response shapes (order status, order data, catalog events/markets)
   **When** `PolymarketConnector` receives a response from the Polymarket API
   **Then** the response is validated through its Zod schema before extracting fields, replacing the chain of `(orderStatus as { status?: string }).status` casts
   **And** validation failures throw `PlatformApiError` (code 1007) with the raw response attached
   [Source: polymarket.connector.ts lines 519-530 — `(orderStatus as { status?: string }).status`; lines 638-656 — `(orderData as { status?: string }).status`; polymarket-catalog-provider.ts line 74 — `as PolymarketEvent[]`]

8. **Given** Zod schemas exist for Kalshi and Polymarket WebSocket message shapes (snapshots, deltas, price changes)
   **When** a WebSocket message is parsed from JSON
   **Then** the parsed object is validated through its Zod schema before processing
   **And** validation failures log a warning and skip the message (do NOT disconnect — transient bad messages should not crash the feed)
   [Source: kalshi-websocket.client.ts line 205 — `JSON.parse(raw) as KalshiWebSocketMessage`; polymarket-websocket.client.ts lines 177-202 — chain of `as unknown as` casts]

9. **Given** Zod schemas exist for third-party API responses (CoinGecko gas price, Telegram Bot API)
   **When** `GasEstimationService` or `TelegramAlertService` receives a response
   **Then** the response is validated before extracting values
   **And** validation failures use the existing fallback mechanisms (gas: `GAS_POL_PRICE_FALLBACK_USD`; Telegram: log + skip)
   [Source: gas-estimation.service.ts line 251 — `as { 'polygon-ecosystem-token': { usd: number } }`; telegram-alert.service.ts lines 289-300 — `as { ok: boolean }`]

### Part D: Baseline

10. **Given** all code changes are complete
    **When** the test suite and linter run
    **Then** all existing tests pass (1774+ baseline), all new tests pass
    **And** `pnpm lint` reports zero errors
    **And** no bare `as` casts remain for JSON field reads or API response extractions in modified files (verified by grep)
    [Source: Test baseline 2026-03-12: 1774 passed, 0 failed, 2 todo, 16 skipped; CLAUDE.md post-edit workflow]

## Tasks / Subtasks

### Part A: Env Var Validation (Foundation)

- [x] **Task 1: Add Zod dependency** (AC: #1)
  - [x]1.1 `pnpm add zod@^3.24.0` — use Zod 3.24.x for stability (Zod 3.25.x bundles Zod 4 internally causing TS issues; Zod 4 has import path changes). Zod 3.24 is the last clean 3.x release.
  - [x]1.2 Verify `import { z } from 'zod'` works in a test file

- [x] **Task 2: Create env schema + types** (AC: #1, #2, #3)
  - [x]2.1 Create `src/common/config/env.schema.ts` — single Zod schema covering all 60+ env vars across 13 groups (see Dev Notes for full schema)
  - [x]2.2 Create `src/common/config/env.types.ts` — `export type Env = z.infer<typeof envSchema>;` and `export type TypedConfigService = ConfigService<Env, true>;`
  - [x]2.3 Create `src/common/config/env.schema.spec.ts` — tests: valid config passes, missing required var fails, numeric coercion works, invalid enum rejects, URL validation rejects bad URLs, financial string coercion works

- [x] **Task 3: Integrate with ConfigModule + typed config access** (AC: #1, #2, #3)
  - [x]3.1 Update `src/app.module.ts` — add `validate: (env) => envSchema.parse(env)` to `ConfigModule.forRoot()`
  - [x]3.2 In `src/common/config/env.types.ts`, export `getEnvConfig(configService: ConfigService): Env` helper that does `configService.get('ENV')` or equivalent — provides one-shot typed access for services
  - [x]3.3 Update services in files modified by this story (dashboard.service.ts, calibration.service.ts, risk-manager.service.ts, single-leg-resolution.service.ts) to use `TypedConfigService` or `getEnvConfig()` for any config accesses in those files — demonstrates the pattern for future migrations
  - [x]3.4 **Boolean breakage check:** In all modified files, grep for `=== 'true'` or `=== 'false'` comparisons on config values that are now Zod-transformed booleans (e.g., `CSV_ENABLED`, `ALLOW_MIXED_MODE`, `DISCOVERY_ENABLED`, etc.). After Zod transform, these are `boolean`, not `string` — any `configService.get('CSV_ENABLED') === 'true'` would silently evaluate to `false`. Fix to direct boolean check: `configService.get('CSV_ENABLED')`.
  - [x]3.5 Verify app starts with current `.env.development` (smoke test)
  - [x]3.6 Verify app fails to start with missing required env var (remove `DATABASE_URL`, confirm ZodError)

### Part B: Prisma JSON Field Schemas

- [x] **Task 4: Create JSON field schemas + validation utility** (AC: #4)
  - [x]4.1 Create `src/common/schemas/prisma-json.schema.ts` — Zod schemas for: `EntryPricesJson`, `SizesJson`, `CalibrationTiersJson`, `BoundaryAnalysisJson`, `RecommendationsJson`, `ReconciliationContextJson`, `HaltReasonJson`, `OrderBookBidsAsksJson`, `AuditLogDetailsJson` (see Dev Notes for exact shapes)
  - [x]4.2 Create `src/common/schemas/parse-json-field.ts` — helper: `parseJsonField<T>(schema: ZodSchema<T>, value: unknown, context: { model: string; field: string; recordId?: string }): T` — on success returns parsed value; on failure throws `SystemHealthError(4500)` with Zod error details. The helper does NOT emit events — the calling service is responsible for event emission (keeps `common/` free of EventEmitter2 dependency).
  - [x]4.3 Add error code 4500 (`DATA_CORRUPTION_DETECTED`) to `src/common/errors/` constants if an error catalog exists. Verify 4500 is unused in the 4000-4999 range.
  - [x]4.4 Create `DataCorruptionDetectedEvent` class in `src/common/events/system.events.ts` — payload: `{ model: string; field: string; recordId?: string; rawValue: unknown; zodErrors: ZodIssue[] }`. Add `SYSTEM.DATA_CORRUPTION_DETECTED` to `EVENT_NAMES` in `event-catalog.ts`.
  - [x]4.5 Create `src/common/schemas/prisma-json.schema.spec.ts` — tests for each schema: valid data passes, missing field fails, wrong type fails
  - [x]4.6 Create `src/common/schemas/parse-json-field.spec.ts` — tests: success returns value, failure throws SystemHealthError(4500) with zodErrors in context

- [x] **Task 5: Apply JSON validation to services** (AC: #4, #5)
  - [x]5.1 `src/dashboard/dashboard.service.ts` — replace `pos.entryPrices as { ... }` with `parseJsonField(entryPricesSchema, pos.entryPrices, { model: 'OpenPosition', field: 'entryPrices', recordId: pos.id })` at lines 355, 418, 592; same for `sizes` reads. Wrap in try-catch: emit `DataCorruptionDetectedEvent` via `this.eventEmitter`, then re-throw.
  - [x]5.2 `src/modules/contract-matching/calibration.service.ts` — replace `run.tiers as unknown as CalibrationResult['tiers']` with `parseJsonField(calibrationTiersSchema, run.tiers, ...)` at lines 88-93, 265-267; same for `boundaryAnalysis` and `recommendations`. Emit event + re-throw on failure.
  - [x]5.3 `src/modules/execution/single-leg-resolution.service.ts` — replace `position.sizes as { ... }` with `parseJsonField(sizesSchema, position.sizes, ...)` at line 99. Emit event + re-throw on failure.
  - [x]5.4 `src/modules/risk-management/risk-manager.service.ts` — replace `JSON.parse(state.haltReason)` with `parseJsonField(haltReasonSchema, JSON.parse(state.haltReason), ...)` at line 176. Emit event + re-throw on failure.
  - [x]5.5 **PRIORITY — Do this FIRST before wiring up parse calls.** Verify JSON schema shapes against write-side code: check `execution.service.ts` for entryPrices/sizes shape, `calibration.service.ts` for tiers write, `risk-manager.service.ts` for haltReason write. If the actual write shape includes fields not in the schema (e.g., an optional `timestamp`), add them as `.optional()` to the schema. Schema/reality mismatch will break existing reads.
  - [x]5.6 Update corresponding spec files for new imports and any changed error paths

### Part C: External API Response Schemas

- [x] **Task 6: Create connector response schemas** (AC: #6, #7, #8, #9)
  - [x]6.1 Create `src/connectors/kalshi/kalshi-response.schema.ts` — Zod schemas for: `KalshiOrderResponseSchema`, `KalshiAccountLimitsSchema`, `KalshiWebSocketMessageSchema` (snapshot + delta)
  - [x]6.2 Create `src/connectors/polymarket/polymarket-response.schema.ts` — Zod schemas for: `PolymarketOrderStatusSchema`, `PolymarketOrderDataSchema`, `PolymarketCatalogEventSchema`, `PolymarketWebSocketMessageSchema` (book_snapshot + price_change)
  - [x]6.3 Create `src/connectors/common/parse-api-response.ts` — helper: `parseApiResponse<T>(schema: ZodSchema<T>, data: unknown, context: { platform: PlatformId; operation: string }): T` — on failure throws `PlatformApiError(1007)` with raw data attached
  - [x]6.4 Create `src/connectors/common/parse-ws-message.ts` — helper: `parseWsMessage<T>(schema: ZodSchema<T>, data: unknown, context: { platform: PlatformId }): T | null` — on failure logs warning and returns `null` (skip message, don't disconnect)
  - [x]6.5 Create spec files for all schemas and helpers

- [x] **Task 7: Apply response validation to connectors** (AC: #6, #7, #8, #9)
  - [x]7.1 `src/connectors/kalshi/kalshi.connector.ts` — replace `as KalshiOrderResponse` with `parseApiResponse(kalshiOrderResponseSchema, data, { platform: PlatformId.KALSHI, operation: 'getOrderStatus' })` at order status/submission call sites
  - [x]7.2 `src/connectors/kalshi/kalshi-websocket.client.ts` — replace `JSON.parse(raw) as KalshiWebSocketMessage` with `parseWsMessage(kalshiWsMessageSchema, JSON.parse(raw), ...)` — if null, skip processing
  - [x]7.3 `src/connectors/polymarket/polymarket.connector.ts` — replace `(orderStatus as { status?: string }).status` chain at lines 519-530 and 638-656 with `parseApiResponse(polymarketOrderStatusSchema, orderStatus, ...)`
  - [x]7.4 `src/connectors/polymarket/polymarket-websocket.client.ts` — replace `as unknown as PolymarketOrderBookMessage` at lines 200-202 with `parseWsMessage(polymarketWsMessageSchema, msg, ...)` — if null, skip
  - [x]7.5 `src/connectors/polymarket/gas-estimation.service.ts` — replace `as { 'polygon-ecosystem-token': { usd: number } }` at line 251 with Zod parse; on failure use `GAS_POL_PRICE_FALLBACK_USD` (existing fallback)
  - [x]7.6 `src/modules/monitoring/telegram-alert.service.ts` — replace `as { ok: boolean }` at lines 289-300 with Zod parse; on failure log warning (non-critical)
  - [x]7.7 `src/connectors/polymarket/polymarket-catalog-provider.ts` — replace `as PolymarketEvent[]` at line 74 and `as PolymarketResolutionMarket[]` at line 124 with Zod array parse
  - [x]7.8 Update all corresponding spec files

### Part D: Validation

- [x] **Task 8: Lint + full test suite** (AC: #10)
  - [x]8.1 Run `pnpm build` — verify zero TypeScript errors
  - [x]8.2 Run `pnpm lint` — fix any errors
  - [x]8.3 Run `pnpm test` — verify all existing tests pass (1774+ baseline) + all new tests pass
  - [x]8.4 Grep for remaining bare `as` casts in modified files: `grep -rn ' as {' src/dashboard/dashboard.service.ts src/modules/contract-matching/calibration.service.ts src/connectors/` — ensure none remain for JSON/response extraction (acceptable: branded type boundary casts, Prisma `where` casts)

## Dev Notes

### Implementation Sequence

**Phase 1 (Tasks 1-3):** Zod dependency + env schema + ConfigModule integration. This is the foundation — validates at startup before anything runs. Highest ROI for safety. Test by temporarily removing a required env var.

**Phase 2 (Tasks 4-5):** Prisma JSON field schemas + validation utility. Replace all `as` casts on JSON field reads. The `parseJsonField` helper centralizes error handling (emit event + throw).

**Phase 3 (Tasks 6-7):** Connector response schemas + validation. Replace all `as` casts on API response extractions. Two helpers: `parseApiResponse` (strict, throws PlatformApiError) and `parseWsMessage` (lenient, returns null on failure).

**Phase 4 (Task 8):** Full validation pass.

### Zod Version Choice

Install `zod@^3.24.0` (Zod 3.24.x). Rationale:

- **Zod 3.25.x** bundles Zod 4 internally within the 3.x package, which doubled the package size and broke builds for projects using TypeScript <5.5 (see [GitHub issue #4923](https://github.com/colinhacks/zod/issues/4923)). Not a compatibility problem for us (TS 5.9.3) but the bundling approach is unstable — best avoided.
- **Zod 4.x** (4.3.6 latest on npm) is stable and uses the same `import { z } from 'zod'` import. However, the NestJS ecosystem (`@nestjs/config` `validate` examples, community guides) is tested against Zod 3.x. Using Zod 3 avoids any edge-case API differences.
- **Zod 3.24.x** is the last clean 3.x release before the 3.25 bundling changes. The `z.object()`, `z.string()`, `z.number()`, `z.enum()`, `z.coerce`, `z.infer` API is identical to what we need. Zero risk.

Since `pnpm add zod` installs 4.x by default (latest tag), pin explicitly: `pnpm add zod@3.24.3`.

[Source: npm registry — `zod@latest` is 4.3.6, `zod@3` latest is 3.25.76; GitHub issue colinhacks/zod#4923 — Zod 3.25.x bundling problems; TypeScript 5.9.3 in package.json]

### ConfigModule Integration Pattern

```typescript
// src/app.module.ts — CHANGE
ConfigModule.forRoot({
  isGlobal: true,
  envFilePath: `.env.${process.env.NODE_ENV || 'development'}`,
  validate: (env) => envSchema.parse(env),  // ← ADD THIS
}),
```

The `validate` function receives `process.env` (merged with `.env` file) and must return the validated object. `envSchema.parse()` throws `ZodError` on failure, which NestJS surfaces as a startup error with the full error list.

[Source: @nestjs/config docs — `validate` option; NestJS + Zod integration pattern from web research]

### Env Schema Design (Complete)

```typescript
// src/common/config/env.schema.ts
import { z } from 'zod';

// Reusable refinement for env vars destined for new Decimal()
const decimalString = (defaultVal: string) =>
  z
    .string()
    .default(defaultVal)
    .refine(val => /^-?\d+(\.\d+)?$/.test(val), {
      message: 'Must be a valid decimal number string (e.g., "0.008", "10000")',
    });

export const envSchema = z.object({
  // Application
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().int().positive().default(8080),

  // Database
  DATABASE_URL: z.string().min(1),

  // Trading Engine
  POLLING_INTERVAL_MS: z.coerce.number().int().positive().default(30000),

  // Kalshi
  KALSHI_API_KEY_ID: z.string().default(''),
  KALSHI_PRIVATE_KEY_PATH: z.string().default('./secrets/key.pem'),
  KALSHI_API_BASE_URL: z.string().url().default('https://demo-api.kalshi.co'),
  KALSHI_API_TIER: z.enum(['BASIC', 'ADVANCED', 'PREMIER', 'PRIME']).default('BASIC'),

  // Polymarket
  POLYMARKET_PRIVATE_KEY: z.string().default(''),
  POLYMARKET_CLOB_API_URL: z.string().url().default('https://clob.polymarket.com'),
  POLYMARKET_WS_URL: z.string().url().default('wss://ws-subscriptions-clob.polymarket.com/ws/market'),
  POLYMARKET_CHAIN_ID: z.coerce.number().int().positive().default(137),
  POLYMARKET_RPC_URL: z.string().url().default('https://polygon-rpc.com'),
  POLYMARKET_GAMMA_API_URL: z.string().url().default('https://gamma-api.polymarket.com'),

  // Edge Calculation (String → Decimal)
  DETECTION_MIN_EDGE_THRESHOLD: decimalString('0.008'),
  DETECTION_GAS_ESTIMATE_USD: decimalString('0.30'),
  DETECTION_POSITION_SIZE_USD: decimalString('300'),

  // Gas Estimation
  GAS_BUFFER_PERCENT: z.coerce.number().int().min(0).max(100).default(20),
  GAS_POLL_INTERVAL_MS: z.coerce.number().int().positive().default(30000),
  GAS_POL_PRICE_FALLBACK_USD: decimalString('0.40'),
  POLYMARKET_SETTLEMENT_GAS_UNITS: z.coerce.number().int().positive().default(150000),

  // Execution Depth (String → Decimal)
  EXECUTION_MIN_FILL_RATIO: decimalString('0.25'),

  // Risk Management (String → Decimal)
  RISK_BANKROLL_USD: decimalString('10000'),
  RISK_MAX_POSITION_PCT: decimalString('0.03'),
  RISK_MAX_OPEN_PAIRS: z.coerce.number().int().positive().default(10),
  RISK_DAILY_LOSS_PCT: decimalString('0.05'),

  // Operator Auth
  OPERATOR_API_TOKEN: z.string().min(1).default('dev-token-change-me'),

  // Platform Modes
  PLATFORM_MODE_KALSHI: z.enum(['live', 'paper']).default('live'),
  PLATFORM_MODE_POLYMARKET: z.enum(['live', 'paper']).default('live'),
  PAPER_FILL_LATENCY_MS_KALSHI: z.coerce.number().int().nonnegative().default(150),
  PAPER_SLIPPAGE_BPS_KALSHI: z.coerce.number().int().nonnegative().default(5),
  PAPER_FILL_LATENCY_MS_POLYMARKET: z.coerce.number().int().nonnegative().default(800),
  PAPER_SLIPPAGE_BPS_POLYMARKET: z.coerce.number().int().nonnegative().default(15),
  ALLOW_MIXED_MODE: z
    .string()
    .transform(v => v === 'true')
    .default('false'),

  // Telegram
  TELEGRAM_BOT_TOKEN: z.string().default(''),
  TELEGRAM_CHAT_ID: z.string().default(''),
  TELEGRAM_TEST_ALERT_CRON: z.string().default('0 8 * * *'),
  TELEGRAM_TEST_ALERT_TIMEZONE: z.string().default('UTC'),
  TELEGRAM_SEND_TIMEOUT_MS: z.coerce.number().int().positive().default(2000),
  TELEGRAM_MAX_RETRIES: z.coerce.number().int().nonnegative().default(3),
  TELEGRAM_BUFFER_MAX_SIZE: z.coerce.number().int().positive().default(100),
  TELEGRAM_CIRCUIT_BREAK_MS: z.coerce.number().int().positive().default(60000),

  // CSV Logging
  CSV_TRADE_LOG_DIR: z.string().default('./data/trade-logs'),
  CSV_ENABLED: z
    .string()
    .transform(v => v === 'true')
    .default('true'),

  // Compliance
  COMPLIANCE_MATRIX_CONFIG_PATH: z.string().default('config/compliance-matrix.yaml'),

  // Dashboard
  DASHBOARD_ORIGIN: z.string().url().default('http://localhost:5173'),

  // LLM Scoring
  LLM_PRIMARY_PROVIDER: z.enum(['gemini', 'anthropic']).default('gemini'),
  LLM_PRIMARY_MODEL: z.string().min(1).default('gemini-2.5-flash'),
  LLM_PRIMARY_API_KEY: z.string().default(''),
  LLM_ESCALATION_PROVIDER: z.enum(['gemini', 'anthropic']).default('anthropic'),
  LLM_ESCALATION_MODEL: z.string().min(1).default('claude-haiku-4-5-20251001'),
  LLM_ESCALATION_API_KEY: z.string().default(''),
  LLM_ESCALATION_MIN: z.coerce.number().int().min(0).max(100).default(60),
  LLM_ESCALATION_MAX: z.coerce.number().int().min(0).max(100).default(84),
  LLM_AUTO_APPROVE_THRESHOLD: z.coerce.number().int().min(0).max(100).default(85),
  LLM_MIN_REVIEW_THRESHOLD: z.coerce.number().int().min(0).max(100).default(40),
  LLM_MAX_TOKENS: z.coerce.number().int().positive().default(1024),
  LLM_TIMEOUT_MS: z.coerce.number().int().positive().default(30000),

  // Discovery
  DISCOVERY_ENABLED: z
    .string()
    .transform(v => v === 'true')
    .default('true'),
  DISCOVERY_RUN_ON_STARTUP: z
    .string()
    .transform(v => v === 'true')
    .default('false'),
  DISCOVERY_CRON_EXPRESSION: z.string().default('0 0 8,20 * * *'),
  DISCOVERY_PREFILTER_THRESHOLD: decimalString('0.25'),
  DISCOVERY_SETTLEMENT_WINDOW_DAYS: z.coerce.number().int().positive().default(7),
  DISCOVERY_MAX_CANDIDATES_PER_CONTRACT: z.coerce.number().int().positive().default(20),
  DISCOVERY_LLM_CONCURRENCY: z.coerce.number().int().positive().default(10),

  // Resolution Polling
  RESOLUTION_POLLER_ENABLED: z
    .string()
    .transform(v => v === 'true')
    .default('true'),
  RESOLUTION_POLLER_CRON_EXPRESSION: z.string().default('0 0 6 * * *'),
  RESOLUTION_POLLER_BATCH_SIZE: z.coerce.number().int().positive().default(100),

  // Calibration
  CALIBRATION_ENABLED: z
    .string()
    .transform(v => v === 'true')
    .default('true'),
  CALIBRATION_CRON_EXPRESSION: z.string().default('0 0 7 1 */3 *'),
});
```

**CRITICAL — Financial values stay as `string`:** Values destined for `new Decimal()` (bankroll, thresholds, prices) MUST remain `z.string()` — NOT `z.coerce.number()`. Reason: env vars are strings; `z.coerce.number()` would convert `"0.008"` → `0.008` (JS float) before it reaches `new Decimal()`, defeating the precision guarantee. Keep them as validated strings and let `new Decimal(value)` handle precision. Use comments `// String → Decimal` to document this intent.

**Add decimal refinement:** Financial string env vars should validate that the value is parseable as a decimal number. Define a reusable refinement:

```typescript
const decimalString = z
  .string()
  .refine(val => /^-?\d+(\.\d+)?$/.test(val), {
    message: 'Must be a valid decimal number string (e.g., "0.008", "10000")',
  });
```

Apply to: `DETECTION_MIN_EDGE_THRESHOLD`, `DETECTION_GAS_ESTIMATE_USD`, `DETECTION_POSITION_SIZE_USD`, `GAS_POL_PRICE_FALLBACK_USD`, `EXECUTION_MIN_FILL_RATIO`, `RISK_BANKROLL_USD`, `RISK_MAX_POSITION_PCT`, `RISK_DAILY_LOSS_PCT`, `DISCOVERY_PREFILTER_THRESHOLD`. This catches typos like `"0.oo8"` at startup instead of when `new Decimal()` throws mid-trade.

[Source: CLAUDE.md domain rules — "ALL financial calculations MUST use decimal.js"; .env.example — complete variable list]

### Boolean Env Var Pattern

NestJS `ConfigModule` reads env vars as strings. Zod `z.boolean()` doesn't coerce `"true"/"false"` strings. Use:

```typescript
z.string()
  .transform(v => v === 'true')
  .default('false');
```

This handles the string→boolean conversion cleanly.

### Prisma JSON Field Schemas

```typescript
// src/common/schemas/prisma-json.schema.ts
import { z } from 'zod';

// OpenPosition.entryPrices — { kalshi: string; polymarket: string }
export const entryPricesSchema = z.object({
  kalshi: z.string(),
  polymarket: z.string(),
});

// OpenPosition.sizes — { kalshi: string; polymarket: string }
export const sizesSchema = z.object({
  kalshi: z.string(),
  polymarket: z.string(),
});

// CalibrationRun.tiers — { autoApprove: CalibrationBand, pendingReview: CalibrationBand, autoReject: CalibrationBand }
const calibrationBandSchema = z.object({
  count: z.number(),
  divergenceRate: z.number(),
  avgConfidence: z.number(),
});
export const calibrationTiersSchema = z.object({
  autoApprove: calibrationBandSchema,
  pendingReview: calibrationBandSchema,
  autoReject: calibrationBandSchema,
});

// CalibrationRun.boundaryAnalysis — BoundaryAnalysisEntry[]
export const boundaryAnalysisSchema = z.array(
  z.object({
    threshold: z.number(),
    matchesAbove: z.number(),
    matchesBelow: z.number(),
    divergenceRateAbove: z.number(),
    divergenceRateBelow: z.number(),
  }),
);

// CalibrationRun.recommendations — string[]
export const recommendationsSchema = z.array(z.string());

// RiskState.haltReason — parsed JSON from string field
export const haltReasonSchema = z
  .object({
    reason: z.string(),
    timestamp: z.string(),
  })
  .passthrough(); // Allow additional fields

// OpenPosition.reconciliationContext — flexible JSON
export const reconciliationContextSchema = z.record(z.unknown()).nullable();

// OrderBookSnapshot.bids/asks — PriceLevel[]
export const orderBookLevelsSchema = z.array(
  z.object({
    price: z.number(),
    size: z.number(),
  }),
);

// AuditLog.details — flexible JSON object
export const auditLogDetailsSchema = z.record(z.unknown());
```

**Note:** These schemas must match the ACTUAL data written to DB by the application. Verify against write-side code (execution.service.ts for entryPrices/sizes, calibration.service.ts for tiers, etc.) before finalizing.

[Source: dashboard.service.ts lines 355/418 — entryPrices shape; calibration-completed.event.ts — CalibrationBand/BoundaryAnalysisEntry interfaces; prisma/schema.prisma — JSON field declarations]

### parseJsonField Helper Pattern

```typescript
// src/common/schemas/parse-json-field.ts
import { ZodSchema } from 'zod';
import { SystemHealthError } from '../errors/system-health-error';

export function parseJsonField<T>(
  schema: ZodSchema<T>,
  value: unknown,
  context: { model: string; field: string; recordId?: string },
): T {
  const result = schema.safeParse(value);
  if (result.success) return result.data;

  throw new SystemHealthError(
    4500,
    `Prisma JSON field validation failed: ${context.model}.${context.field}` +
      (context.recordId ? ` (id: ${context.recordId})` : ''),
    'critical',
    { model: context.model, field: context.field, recordId: context.recordId, zodErrors: result.error.issues },
  );
}
```

**Design decision:** `parseJsonField` ONLY throws — it does NOT emit events. The calling service handles event emission:

```typescript
// In service (has EventEmitter2 injected):
try {
  const tiers = parseJsonField(calibrationTiersSchema, run.tiers, { model: 'CalibrationRun', field: 'tiers', recordId: run.id });
} catch (error) {
  this.eventEmitter.emit(EVENT_NAMES.SYSTEM.DATA_CORRUPTION_DETECTED, new DataCorruptionDetectedEvent({ ... }));
  throw error; // re-throw after emitting
}
```

This keeps `common/schemas/` free of framework dependencies (EventEmitter2) — only the service layer handles event emission, which aligns with the architecture's module dependency rules.

**Error code 4500** (`DATA_CORRUPTION_DETECTED`) is a new code in the SystemHealthError range (4000-4999). Verify it's unused before defining. The severity is `critical` because corrupted JSON fields in a financial trading system could produce incorrect position sizes, P&L calculations, or risk state — all with real monetary consequences.

[Source: common/errors/system-health-error.ts — SystemHealthError constructor; common/events/event-catalog.ts — EVENT_NAMES; architecture.md — error severity routing: Critical → Telegram + audit + potential halt]

### API Response Validation Helpers

```typescript
// src/connectors/common/parse-api-response.ts
import { ZodSchema } from 'zod';
import { PlatformApiError } from '../../common/errors/platform-api-error';
import { PlatformId } from '../../common/types/platform.type';

export function parseApiResponse<T>(
  schema: ZodSchema<T>,
  data: unknown,
  context: { platform: PlatformId; operation: string },
): T {
  const result = schema.safeParse(data);
  if (result.success) return result.data;

  throw new PlatformApiError(
    1007,
    `Unexpected API response schema from ${context.platform} (${context.operation})`,
    'critical',
    { platform: context.platform, operation: context.operation, zodErrors: result.error.issues, rawData: data },
  );
}

// src/connectors/common/parse-ws-message.ts
import { ZodSchema } from 'zod';
import { Logger } from '@nestjs/common';
import { PlatformId } from '../../common/types/platform.type';

const logger = new Logger('WsMessageParser');

export function parseWsMessage<T>(schema: ZodSchema<T>, data: unknown, context: { platform: PlatformId }): T | null {
  const result = schema.safeParse(data);
  if (result.success) return result.data;

  logger.warn(
    `Invalid WebSocket message from ${context.platform}: ${result.error.issues.map(i => i.message).join(', ')}`,
  );
  return null;
}
```

**Critical design:** WebSocket validation returns `null` on failure instead of throwing. This prevents a single malformed message from disconnecting the feed. The caller checks for null and skips processing:

```typescript
const msg = parseWsMessage(schema, JSON.parse(raw), { platform: PlatformId.KALSHI });
if (!msg) return; // skip invalid message
```

[Source: PRD error code 1007 — "Unexpected API Response Schema", Critical, "No retry, halt trading"; PRD NFR-I1 — "Defensive parsing: Handle unexpected API responses without crashing"]

### What This Story Does NOT Change

- **No changes to class-validator DTOs** — REST request validation already works via class-validator. Replacing with Zod would be scope creep; both systems serve different layers.
- **No inter-module validation** — architecture prescribes an inter-module trust model. Zod is only for system boundaries.
- **No YAML config overhaul** — `compliance-config-loader.service.ts` already has manual validation. Migrating to Zod is out of scope.
- **No LLM response schema** — `llm-scoring.strategy.ts` already validates manually (score range, confidence enum). Adding Zod is marginal value for working code.
- **No branded type changes** — already done in Story 9-0-1.
- **No Prisma query input validation** — TypeScript handles this; Zod is for data coming IN from external sources.
- **No `connectors/` directory restructuring** — new schema files live alongside their connectors.

### Connector Response Schema Notes

**Schema strictness pattern — apply consistently:**

- **External API schemas (connectors):** Use `.passthrough()` — forward-compatible with API changes that add new fields. We validate the fields we need; extra fields are ignored, not rejected. This prevents breakage when Kalshi/Polymarket add response fields.
- **Internal schemas (Prisma JSON):** Use strict (no `.passthrough()`) — these fields are written by OUR code. If the shape is wrong, it's data corruption, not an API change.

**Kalshi order response** — define schema from the `KalshiOrderResponse` interface already in `kalshi.types.ts`. Use `.passthrough()`.

**Polymarket order status** — the current code does `(orderStatus as { status?: string }).status`. The Zod schema should use `.optional()` for fields that may be absent and `.nullable()` where the API might return null. Use `.passthrough()`.

**WebSocket messages** — use `z.discriminatedUnion()` on the message `type` field for Kalshi (types: `orderbook_snapshot`, `orderbook_delta`) and on `event_type` for Polymarket (types: `book`, `price_change`). This gives precise validation per message type. Use `.passthrough()` on each variant.

[Source: kalshi.types.ts — KalshiOrderResponse, KalshiWebSocketMessage interfaces; polymarket.types.ts — PolymarketOrderBookMessage, PolymarketPriceChangeMessage interfaces]

### `as` Cast Audit Strategy

After completing all tasks, run:

```bash
grep -rn ' as {' src/dashboard/dashboard.service.ts src/modules/contract-matching/calibration.service.ts src/modules/execution/single-leg-resolution.service.ts src/modules/risk-management/risk-manager.service.ts src/connectors/ src/modules/monitoring/telegram-alert.service.ts
```

Any remaining `as {` casts in these files should be justified (e.g., branded type boundary) or eliminated.

### Previous Story Intelligence

**From Story 9-0-1 (Branded Types & Calibration Persistence):**

- Branded type factory functions (`asPositionId()` etc.) live in `src/common/types/branded.type.ts` — these are system-boundary wrappers similar to what Zod schemas provide. The two patterns are complementary: branded types ensure compile-time type safety, Zod ensures runtime data integrity.
- CalibrationService persistence uses `JSON.parse(JSON.stringify(result.tiers))` for Prisma writes and `as unknown as CalibrationResult['tiers']` for reads — completion note #3 explicitly says "Story 9-0-2 (Zod) will add runtime validation for these JSON fields."
- ESLint `no-unsafe-assignment` warning on `JSON.parse()` returns `any` — Zod `.parse()` returns a typed value, eliminating this lint issue. The `// eslint-disable-next-line` comments added in 9-0-1 can be removed once Zod validation is in place.
- Compiler-driven migration strategy worked well — follow the same pattern: change the helper signatures, let TypeScript errors guide remaining fixes.
- Test count: 1774 passed. New Zod tests will add ~40-60 tests (9 schema files + 4 helper files, each with positive/negative cases).

[Source: 9-0-1-branded-types-calibration-persistence.md — completion notes #3, #4]

### Pre-Existing Test Failures

3 pre-existing e2e test file failures (unrelated to this story):

- `test/app.e2e-spec.ts` — Prisma connection in test environment
- `test/logging.e2e-spec.ts` — event timestamp check
- `test/data-ingestion.e2e-spec.ts` — Prisma connection in test environment

These are NOT regressions from this story.

[Source: Test baseline 2026-03-12: 1774 passed, 0 failed, 2 todo, 16 skipped]

### Test Strategy

- **Env schema tests:** Valid config passes; missing required var fails; invalid types rejected; coercion works
- **JSON schema tests:** Each schema validates correct shape; rejects wrong types; rejects missing required fields
- **parseJsonField tests:** Returns parsed value on success; throws SystemHealthError(4500) on failure; emits event on failure
- **parseApiResponse tests:** Returns parsed value on success; throws PlatformApiError(1007) on failure with raw data
- **parseWsMessage tests:** Returns parsed value on success; returns null on failure; logs warning on failure
- **Integration smoke test (manual):** Remove a required env var from `.env.development`, confirm app fails to start with clear error

### Project Structure Notes

**New files (12-13):**

- `src/common/config/env.schema.ts` — Zod env var schema
- `src/common/config/env.types.ts` — Inferred types + TypedConfigService + getEnvConfig helper
- `src/common/config/env.schema.spec.ts` — Env schema tests
- `src/common/schemas/prisma-json.schema.ts` — Prisma JSON field Zod schemas
- `src/common/schemas/parse-json-field.ts` — JSON field validation helper
- `src/common/schemas/prisma-json.schema.spec.ts` — JSON schema tests
- `src/common/schemas/parse-json-field.spec.ts` — parseJsonField tests
- `src/connectors/kalshi/kalshi-response.schema.ts` — Kalshi API + WS Zod schemas
- `src/connectors/polymarket/polymarket-response.schema.ts` — Polymarket API + WS Zod schemas
- `src/connectors/common/parse-api-response.ts` — API response validation helper
- `src/connectors/common/parse-ws-message.ts` — WS message validation helper
- Spec files for connector schemas and helpers

**Modified files (estimated 12-15):**

- `src/app.module.ts` — ConfigModule validate integration
- `src/dashboard/dashboard.service.ts` — JSON field validation (entryPrices, sizes, details)
- `src/modules/contract-matching/calibration.service.ts` — JSON field validation (tiers, boundaryAnalysis, recommendations)
- `src/modules/execution/single-leg-resolution.service.ts` — JSON field validation (sizes)
- `src/modules/risk-management/risk-manager.service.ts` — JSON field validation (haltReason)
- `src/connectors/kalshi/kalshi.connector.ts` — API response validation
- `src/connectors/kalshi/kalshi-websocket.client.ts` — WS message validation
- `src/connectors/polymarket/polymarket.connector.ts` — API response validation
- `src/connectors/polymarket/polymarket-websocket.client.ts` — WS message validation
- `src/connectors/polymarket/gas-estimation.service.ts` — CoinGecko response validation
- `src/connectors/polymarket/polymarket-catalog-provider.ts` — Gamma API response validation
- `src/modules/monitoring/telegram-alert.service.ts` — Telegram API response validation
- `package.json` — zod dependency added
- Corresponding spec files for modified services

All changes within existing module boundaries — no new modules, no new directories except `src/common/schemas/` and `src/connectors/common/`.

### References

- [Source: sprint-status.yaml line 166] — "9-0-2-zod-boundary-schemas: backlog # Tech debt: runtime validation at system boundaries (env vars, JSON fields, API responses)"
- [Source: architecture.md directory tree] — `config/validation.schema.ts` prescribed as "Joi/Zod config validation at startup"
- [Source: architecture.md "Process Patterns > Validation"] — "Validate at system boundaries only: Platform API responses, Dashboard API inputs, Configuration at startup. No redundant validation between internal modules."
- [Source: PRD error code 1007] — "Unexpected API Response Schema", severity Critical, "No retry, halt trading"
- [Source: PRD NFR-I1] — "Defensive parsing: Handle unexpected API responses without crashing"
- [Source: app.module.ts lines 28-31] — current ConfigModule has no validate function
- [Source: .env.example] — complete list of 60+ environment variables
- [Source: 9-0-1-branded-types-calibration-persistence.md completion note #3] — "Story 9-0-2 (Zod) will add runtime validation for these JSON fields"
- [Source: dashboard.service.ts lines 355/418/592] — `entryPrices as { kalshi: string; polymarket: string }` unsafe casts
- [Source: calibration.service.ts lines 88-93] — `tiers as unknown as CalibrationResult['tiers']` unsafe casts
- [Source: polymarket.connector.ts lines 519-530] — `(orderStatus as { status?: string }).status` unsafe casts
- [Source: kalshi-websocket.client.ts line 205] — `JSON.parse(raw) as KalshiWebSocketMessage` unsafe cast
- [Source: gas-estimation.service.ts line 251] — CoinGecko response unsafe cast
- [Source: package.json] — Zod not yet a direct dependency; TypeScript 5.9.3; @nestjs/config ^4.0.3

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes

1. **Story Dev Notes had 4 schema shape mismatches vs actual write-side code** — discovered during Task 5.5 (write-side verification). Fixed before wiring up parse calls:
   - `CalibrationRun.tiers`: Story had `{ count, divergenceRate, avgConfidence }` but actual is `{ range, matchCount, divergedCount, divergenceRate }`
   - `CalibrationRun.boundaryAnalysis`: Story had `{ matchesBelow, divergenceRateBelow }` but actual is `{ divergedAbove, recommendation }`
   - `RiskState.haltReason`: Story had `{ reason, timestamp }` object but actual is `string[]` (serialized Set)
   - `OrderBookSnapshot`: Story used `size` but actual field is `quantity`

2. **Boolean breakage — found 6 affected services** (story listed 3): `csv-trade-log.service.ts`, `engine-lifecycle.service.ts`, `candidate-discovery.service.ts` (2 vars), `resolution-poller.service.ts`, `calibration.service.ts`. All `=== 'true'` string comparisons converted to direct boolean usage with appropriate `?? true/false` defaults.

3. **SystemHealthError/PlatformApiError constructor signatures** differed from story Dev Notes. Adapted `parseJsonField` and `parseApiResponse` to match actual constructors (positional args, not options objects).

4. **Legacy haltReason compatibility preserved** — `risk-manager.service.ts` retains fallback for legacy single-string format alongside new `haltReasonSchema` validation.

5. **Test count: 1774 → 1836** (+62 new tests from Zod schemas, helpers, and updated service specs). All pass. Lint clean.

6. **`as` cast audit**: All bare `as` casts for JSON field reads and API response extractions replaced with Zod validation in modified files. Remaining `as` casts are legitimate internal type narrowing (event details, enum narrowing, Prisma Decimal → decimal.js, error handling).

### Files Created

- `src/common/config/env.schema.ts` — Zod schema for 60+ env vars
- `src/common/config/env.types.ts` — Inferred types, TypedConfigService, getEnvConfig helper
- `src/common/config/env.schema.spec.ts` — 13 tests
- `src/common/schemas/prisma-json.schema.ts` — Zod schemas for all Prisma JSON fields
- `src/common/schemas/parse-json-field.ts` — parseJsonField helper (throws SystemHealthError 4500)
- `src/common/schemas/prisma-json.schema.spec.ts` — 22 tests
- `src/common/schemas/parse-json-field.spec.ts` — 3 tests
- `src/connectors/kalshi/kalshi-response.schema.ts` — Kalshi REST + WS Zod schemas
- `src/connectors/kalshi/kalshi-response.schema.spec.ts` — 7 tests
- `src/connectors/polymarket/polymarket-response.schema.ts` — Polymarket REST + WS + CoinGecko + Telegram schemas
- `src/connectors/polymarket/polymarket-response.schema.spec.ts` — 12 tests
- `src/connectors/common/parse-api-response.ts` — parseApiResponse helper (throws PlatformApiError 1007)
- `src/connectors/common/parse-api-response.spec.ts` — 2 tests
- `src/connectors/common/parse-ws-message.ts` — parseWsMessage helper (returns null on failure)
- `src/connectors/common/parse-ws-message.spec.ts` — 3 tests

### Files Modified

- `src/app.module.ts` — Added `validate: (env) => envSchema.parse(env)` to ConfigModule
- `src/common/events/system.events.ts` — Added DataCorruptionDetectedEvent class
- `src/common/events/event-catalog.ts` — Added DATA_CORRUPTION_DETECTED event name
- `src/dashboard/dashboard.service.ts` — Replaced 3 entryPrices `as` casts with parseJsonField
- `src/modules/contract-matching/calibration.service.ts` — Replaced `as unknown as` casts with parseJsonField + event emission
- `src/modules/execution/single-leg-resolution.service.ts` — Replaced sizes `as` cast with parseJsonField
- `src/modules/risk-management/risk-manager.service.ts` — Replaced JSON.parse with haltReasonSchema validation
- `src/connectors/kalshi/kalshi.connector.ts` — Added parseApiResponse for getOrder/getAccountApiLimits
- `src/connectors/kalshi/kalshi-websocket.client.ts` — Replaced `as KalshiWebSocketMessage` with parseWsMessage
- `src/connectors/polymarket/polymarket.connector.ts` — Replaced orderStatus `as` casts with parseApiResponse
- `src/connectors/polymarket/polymarket-websocket.client.ts` — Replaced `as unknown as` casts with parseWsMessage
- `src/connectors/polymarket/gas-estimation.service.ts` — Replaced CoinGecko response cast with Zod parse
- `src/connectors/polymarket/polymarket-catalog-provider.ts` — Replaced `as PolymarketEvent[]` with parseApiResponse
- `src/modules/monitoring/telegram-alert.service.ts` — Replaced `as { ok: boolean }` with Zod safeParse
- `src/core/engine-lifecycle.service.ts` — Fixed boolean config access
- `src/modules/monitoring/csv-trade-log.service.ts` — Fixed boolean config access
- `src/modules/contract-matching/candidate-discovery.service.ts` — Fixed boolean config access (2 vars)
- `src/modules/contract-matching/resolution-poller.service.ts` — Fixed boolean config access
- 6 corresponding spec files updated for boolean mock value changes
