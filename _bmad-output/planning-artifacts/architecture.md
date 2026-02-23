---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-02-10'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
workflowType: 'architecture'
project_name: 'pm-arbitrage-system'
user_name: 'Arbi'
date: '2026-02-10'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
60+ FRs across 8 modules: Data Ingestion (5), Arbitrage Detection (7), Execution (8), Risk Management (9), Monitoring & Alerting (9), Exit Management (3), Contract Matching (4), Platform Integration (7), Data Export (4). Requirements are phased MVP vs Phase 1, with MVP focused on proving the arbitrage edge exists and Phase 1 building institutional-grade sophistication.

Architecturally, the FRs describe a real-time event pipeline: platform data feeds → normalized order books → cross-platform detection → risk-gated execution → monitoring/alerting. Every module has clearly defined inputs, outputs, and interfaces specified in the PRD's System Architecture section.

**Non-Functional Requirements:**
14 NFRs across 4 categories driving architectural decisions:

- **Performance:** 500ms order book normalization (NFR-P1), 1s detection cycle (NFR-P2), <100ms between leg submissions (NFR-P3), 2s dashboard updates (NFR-P4)
- **Security:** Environment-variable credentials evolving to secrets manager (NFR-S1), zero-downtime key rotation (NFR-S2), 7-year audit trail with complete trade records (NFR-S3), authenticated access (NFR-S4)
- **Reliability:** 99% uptime during market hours (NFR-R1), per-platform graceful degradation (NFR-R2), 5s single-leg exposure timeout (NFR-R3), 30s platform health detection (NFR-R4), microsecond-timestamped persistence with 7-year retention (NFR-R5)
- **Integration:** Defensive API parsing (NFR-I1), rate limit enforcement with 20% buffer (NFR-I2), auto-reconnecting WebSockets (NFR-I3), transaction confirmation handling (NFR-I4 — scoped to on-chain settlement in Epic 5; MVP order execution is off-chain CLOB for both platforms)

**Scale & Complexity:**

- Primary domain: API backend (fintech/trading)
- Complexity level: High — real-time, multi-platform, stateful, regulated
- Estimated architectural components: 5 core modules + dashboard + alerting + persistence layer + platform connectors
- Single operator system — no multi-tenancy

### Technical Constraints & Dependencies

- **Single long-running stateful process** (MVP) with potential decomposition in Phase 1+
- **Heterogeneous platform integration:** Kalshi (REST/WebSocket exchange API) vs Polymarket (off-chain CLOB API via @polymarket/clob-client SDK + WebSocket; on-chain Polygon interactions limited to deposits/withdrawals/settlement in Epic 5)
- **SQLite** for structured state persistence (positions, orders, risk state, knowledge base); JSON files for configuration with atomic write-rename pattern
- **NTP synchronization** required for audit trail compliance (<100ms clock drift tolerance)
- **Blue/green deployment** for zero-downtime updates with 5-minute observation window and rollback capability
- **Startup reconciliation** against platform APIs to detect orphan fills after crash recovery
- **Single-server deployment** (MVP): Linux, 2 vCPU, 4GB RAM, 50GB SSD, <50ms latency to cloud regions

### Cross-Cutting Concerns Identified

1. **Platform Abstraction** — Every module touches platform-specific behavior (authentication, data formats, execution mechanics, fee structures). Clean abstraction boundary between platform connectors and core logic is the single most critical architectural decision.
2. **State Management & Crash Recovery** — Open positions, risk budgets, pending orders, and knowledge base must survive process restarts. Atomic persistence with SQLite rollback journals and JSON write-rename patterns. Startup reconciliation against live platform state.
3. **Observability & Audit** — All modules produce events consumed by monitoring, alerting, compliance reporting, and audit logging. Event-driven architecture must support multiple consumers without coupling producers to specific output channels.
4. **Error Handling & Degradation** — 30+ error codes with distinct severity levels, retry strategies, and operator actions. Centralized error taxonomy with per-platform degradation protocols (cancel pending, halt new trades, maintain monitoring, auto-recover).
5. **Configuration Management** — Contract pairs, compliance rules, risk parameters (position limits, correlation clusters, loss limits), platform credentials, alerting thresholds — all must be configurable without code changes.
6. **Progressive Sophistication** — MVP components (manual matching, sequential execution, fixed thresholds) must be replaceable by Phase 1 components (NLP matching, coordinated execution, model-driven exits) without system redesign. Module interfaces must be stable across this evolution.

## Starter Template Evaluation

### Primary Technology Domain

API backend (fintech/trading) — real-time event-driven system with lightweight operator dashboard.

### Technology Stack Decisions

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Language | TypeScript | 5.x (strict) | Event loop model matches PRD's "same event loop cycle" execution; best Ethereum/Polygon SDK ecosystem; shared types with dashboard |
| Runtime | Node.js | LTS | Single-threaded event loop aligns with sequential execution locking design |
| Framework | NestJS + Fastify | 11.x / 11.1.x | Module system maps 1:1 to PRD's 5-module architecture; DI enables testability; Fastify 2-3x faster than Express |
| ORM | Prisma | 6.x | Type-safe queries, migration tooling, PostgreSQL support for 7-year audit trail and correlation analytics |
| Database | PostgreSQL | 16+ | Query power for Phase 1 knowledge base, correlation analytics, 7-year retention; replaces PRD's SQLite suggestion |
| Blockchain | viem | Latest stable | TypeScript-native Polygon/Polymarket on-chain transactions; tree-shakable; modern alternative to ethers.js |
| Testing | Vitest | 4.x | Native TypeScript, Jest-compatible API, faster execution; SWC transform via unplugin-swc for decorator metadata |
| Dashboard | React (SPA) | 19.x | Shared TypeScript types with backend; lightweight single-user operator dashboard |
| Deployment | Docker on Hetzner VPS | — | Cost-effective single-server; Docker enables reproducible builds and blue/green deploys |
| CI/CD | GitHub Actions | — | Standard for solo developer; automated testing and deployment pipeline |

### Selected Starter: Official NestJS CLI (`nest new`)

**Rationale:** For a high-complexity fintech trading system requiring full control over every dependency, the official CLI scaffold provides a clean foundation without opinionated community boilerplate choices that may not match this architecture. Community starters carry risk of unused code, stale dependencies, and maintenance uncertainty.

**Initialization Command:**

```bash
# 1. Scaffold NestJS project
npx @nestjs/cli@latest new pm-arbitrage-system --strict --package-manager pnpm

# 2. Swap to Fastify adapter
pnpm add @nestjs/platform-fastify
pnpm remove @nestjs/platform-express

# 3. Add core dependencies
pnpm add prisma@6 @prisma/client@6 viem
pnpm add -D vitest unplugin-swc @swc/core @golevelup/ts-vitest
```

**Architectural Decisions Provided by Starter:**

- **Code Organization:** NestJS module system with DI container — maps directly to PRD's Data Ingestion, Arbitrage Detection, Execution, Risk Management, and Monitoring modules
- **HTTP Layer:** Fastify adapter for dashboard API endpoints and health checks
- **Build Tooling:** SWC for fast compilation, NestJS CLI for scaffolding and code generation
- **TypeScript:** Strict mode enabled, decorator metadata via SWC plugin

**Remaining Configuration (First Implementation Story):**

- Docker + docker-compose (PostgreSQL service, application container)
- Prisma schema initialization and first migration
- Vitest config with unplugin-swc for decorator metadata support
- ESLint + Prettier customization
- GitHub Actions CI/CD pipeline
- NestJS module structure matching PRD's 5 core modules
- Environment variable management (.env pattern)

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
All 5 categories decided — data architecture, security, communication patterns, frontend architecture, infrastructure. No deferred critical decisions.

**Deferred Decisions (Phase 1):**
- Secrets manager selection and migration (Phase 1, NFR-S1)
- Caddy reverse proxy + HTTPS + JWT session management (Phase 1, mobile dashboard)
- WAL-based continuous archiving for point-in-time recovery (Phase 1, if needed)
- Traefik or advanced routing (not needed — single-server, single-user)

### Data Architecture

**Database Schema Strategy:** Single PostgreSQL instance with logical separation via table prefixes or Prisma schema namespaces. Five data domains (positions/orders, contract matches, audit logs, risk state, platform health) in one database. Single backup strategy, single connection pool, single monitoring point. The data domains don't have different scaling characteristics at this scale.

**Audit Log Architecture:** Append-only table with SHA-256 cryptographic chaining. Each audit log entry includes hash of previous entry, creating a verifiable chain satisfying PRD's "tamper-evident logging" requirement (NFR-S3). No trigger-based capture — the system is the sole writer to trading tables, so all state changes are already logged explicitly through the Monitoring module. Hash chain provides cryptographic proof of ordering and completeness for legal review.

**Time-Series Data:** Plain PostgreSQL with monthly table partitioning for order book snapshots. No TimescaleDB extension dependency. At system scale (~2.5M rows/day for 20-30 contract pairs at 30-second snapshots), native PostgreSQL partitioning handles the volume. Retention policies via partition drops (older than 7 years). TimescaleDB justified only if data volumes increase significantly (Phase 2+ multi-platform).

**Caching Strategy:** In-memory only. Current order book state, risk budgets, platform health status, and detection cycle data live in Node.js process memory. Ephemeral data rebuilt from platform APIs on restart. 30-second polling cycle means stale cache is at most 30 seconds old. Redis adds operational dependency and network hop conflicting with sub-second latency requirements (NFR-P1, NFR-P2). No cross-process cache sharing needed in single-process design.

### Authentication & Security

**Dashboard Authentication (MVP):** Static API token in `Authorization: Bearer <token>` header, token stored in environment variable. Stateless validation on every request and WebSocket connection init. No login UI, no session management, no cookies. Phase 1 layers JWT with proper session management when mobile access is required.

**Platform Credential Management (MVP):** Structured environment variable namespacing with encrypted keystore for Polymarket private key.
- Kalshi credentials (`KALSHI_API_KEY`, `KALSHI_API_SECRET`): Plain `.env` file via `@nestjs/config`. Revocable API keys — rotate on Kalshi dashboard if compromised.
- Polymarket wallet private key: AES-256 encrypted keystore file, decrypted at startup with master password from `POLYMARKET_KEYSTORE_PASSWORD` environment variable. Filesystem access alone doesn't yield the raw private key.
- Phase 1 migrates all credentials to external secrets manager per PRD specification.

**API Security (MVP):** Localhost-only binding — Fastify binds to `127.0.0.1:8080`, accessible only via SSH tunnel (`ssh -L 8080:localhost:8080 vps`). Zero network attack surface, zero TLS configuration. Phase 1 adds Caddy reverse proxy with automatic HTTPS via Let's Encrypt for mobile dashboard access.

**Inter-Module Trust Model:** Interface contracts only — implicit in-process trust with compile-time enforcement via TypeScript interfaces. Modules interact through injected interfaces (e.g., `IRiskManager`, `IPlatformConnector`), not concrete classes. No runtime auth overhead. If modules are ever decomposed into separate services (Ring 2 productization), interfaces become API contracts with minimal refactoring.

### API & Communication Patterns

**Internal Module Communication:** Hybrid pattern — synchronous DI injection for the execution hot path, EventEmitter2 for observability fan-out.
- **Hot path (synchronous):** Detection → Risk validation → Execution. `detectionService.onOpportunity()` → `riskManager.validatePosition()` → `executionEngine.execute()`. Blocking is correct — never execute without risk validation completing.
- **Fan-out (async EventEmitter2):** Every module emits domain events (`OrderFilled`, `SingleLegExposure`, `LimitApproached`, `OpportunityIdentified`, etc.) that Monitoring subscribes to for dashboard updates, Telegram alerts, audit logging, and CSV exports. Telegram API timeout never delays the next execution cycle.

**Dashboard API:** REST endpoints (flat structure) + NestJS WebSocket gateway.
- REST: `/api/health`, `/api/positions`, `/api/positions/:id`, `/api/alerts`, `/api/matches/pending`, `/api/matches/:id/approve`, `/api/matches/:id/reject`, `/api/performance/weekly`, `/api/performance/daily`, `/api/compliance/export`. No deep nesting.
- WebSocket: NestJS WebSocket gateway subscribes to EventEmitter2 events, pushes to dashboard client. Event types: `position.update`, `alert.new`, `health.change`, `execution.complete`, `match.pending`. Native WebSocket with simple reconnection wrapper (exponential backoff). No Socket.IO dependency.
- API documentation via `@nestjs/swagger` — backend is single source of truth for API contracts.

**Error Handling:** Centralized typed error classes with NestJS exception filter routing. PRD error codes (1000–4999) map to error class hierarchy:
```
SystemError
  ├── PlatformApiError (1000-1999) — severity, retryStrategy, platformId
  ├── ExecutionError (2000-2999) — severity, retryStrategy, affectedPositionId
  ├── RiskLimitError (3000-3999) — severity, limitType, currentValue, threshold
  └── SystemHealthError (4000-4999) — severity, component, diagnosticInfo
```
Global exception filter routes by severity: Critical → high-priority event (Telegram + audit + potential halt). Warning → dashboard update + log. Info → log only.

**Platform Connector Interface:** Single unified `IPlatformConnector` interface. Both Kalshi and Polymarket implement the same interface — platform-specific concerns (gas estimation, wallet signing, REST auth, rate limit handling) encapsulated inside each connector implementation. Satisfies FR-DI-05 ("adding new platform connectors without modifying core modules"). Phase 1 third platform addition is a new connector implementation, not a system redesign.

```typescript
interface IPlatformConnector {
  submitOrder(params: OrderParams): Promise<OrderResult>
  cancelOrder(orderId: string): Promise<CancelResult>
  getOrderBook(contractId: string): Promise<NormalizedOrderBook>
  getPositions(): Promise<Position[]>
  getHealth(): PlatformHealth
  getPlatformId(): PlatformId
  getFeeSchedule(): FeeSchedule
  connect(): Promise<void>
  disconnect(): Promise<void>
  onOrderBookUpdate(callback: (book: NormalizedOrderBook) => void): void
}
```

### Frontend Architecture

**Project Structure:** Separate repositories — `pm-arbitrage-engine` (NestJS backend) and `pm-arbitrage-dashboard` (React SPA). API contract synchronization via Swagger-generated types: backend exposes OpenAPI spec via `@nestjs/swagger`, frontend generates TypeScript client using `swagger-typescript-api` from `/api/docs-json` endpoint. WebSocket event types (5-6 stable event types) maintained manually in dashboard repo.

**Build Tool:** Vite. No SSR, no SEO, no public-facing concerns.

**State Management:** React Query (TanStack Query) for REST data fetching/caching + WebSocket context provider for live updates that invalidate or patch React Query cache. No separate state store.

**UI Components:** shadcn/ui (Tailwind + Radix primitives). Production-quality components for tables, metrics, and status indicators without heavy framework dependency. Functional over beautiful — optimized for the 2-minute morning scan use case.

### Infrastructure & Deployment

**Docker Compose:** Three-service architecture — `postgres`, `engine`, `dashboard`. Dashboard container is nginx serving Vite static build. Independent rebuild/restart — dashboard redeploys don't touch the trading engine (critical when open positions exist). Docker Compose file lives in engine repo as deployment configuration.

**Blue/Green Deployment (MVP):** Manual bash script — pull new engine image → start green container on alternate port → health check `/api/health` → verify startup reconciliation completes → swap port binding in compose → 5-minute observation window with auto-rollback on health degradation. Phase 1 adds Caddy-based upstream swap when HTTPS is introduced.

**Monitoring & Health Checks:** Two independent failure detection layers:
1. Docker `HEALTHCHECK` on engine container — internal health endpoint, 3 consecutive failures (30-second intervals) triggers automatic restart. Covers "engine hung/crashed, VPS fine."
2. External ping service (Healthchecks.io or UptimeRobot) — hits `/api/health` every 60 seconds from outside. Alerts via Telegram + email on failure. Covers "entire VPS down" or "Docker daemon crashed."

**Backup Strategy:** Hourly `pg_dump` via sidecar container/cron, compressed and uploaded to Hetzner Object Storage (S3-compatible) via rclone. 7-day rolling window for hourly snapshots, monthly snapshots retained for 7 years (compliance). Weekly automated restore test to separate database with row count and timestamp validation, pass/fail reported via Telegram. WAL-based continuous archiving deferred to Phase 1 if point-in-time recovery needed.

**Environment Configuration:** Combination approach:
- `.env` files per environment (`.env.development`, `.env.production`): Non-sensitive config — polling intervals, edge thresholds, risk limits, feature flags, ports, database host/name. Loaded by `@nestjs/config` based on `NODE_ENV`.
- Docker secrets (production only): Kalshi API key/secret, Polymarket keystore password, dashboard API token, PostgreSQL password. Mounted as files, read at startup. Never in `.env`, compose files, or version control.
- Local development uses `.env.development` with Kalshi sandbox API and testnet wallet credentials.
- **Paper Trading Configuration (per-platform):**
  - `PLATFORM_MODE_KALSHI=live|paper` — platform operating mode (default: `live`)
  - `PLATFORM_MODE_POLYMARKET=live|paper` — platform operating mode (default: `live`)
  - `PAPER_FILL_LATENCY_MS_KALSHI=150` — simulated fill latency for Kalshi paper mode
  - `PAPER_SLIPPAGE_BPS_KALSHI=5` — simulated slippage in basis points for Kalshi paper mode
  - `PAPER_FILL_LATENCY_MS_POLYMARKET=800` — simulated fill latency for Polymarket paper mode (reflects on-chain confirmation)
  - `PAPER_SLIPPAGE_BPS_POLYMARKET=15` — simulated slippage in basis points for Polymarket paper mode
  - Mode is immutable at runtime — requires restart to change. PaperTradingConnector decorates the real connector, proxying data methods and intercepting execution methods with local simulation.

### Decision Impact Analysis

**Implementation Sequence:**
1. Project scaffold (NestJS + Fastify + Prisma + Docker Compose + PostgreSQL)
2. Database schema and first migration (positions, orders, audit log, contract matches, risk state)
3. Platform connector interface + Kalshi connector (REST API, simpler)
4. Platform connector interface + Polymarket connector (off-chain CLOB via SDK, wallet auth via private key)
5. Core module structure (Data Ingestion → Detection → Risk → Execution → Monitoring)
6. EventEmitter2 integration for fan-out path
7. Dashboard API (REST endpoints + WebSocket gateway + Swagger)
8. React dashboard (Vite + React Query + shadcn/ui)
9. Deployment pipeline (Docker, health checks, backup, blue/green script)

**Cross-Component Dependencies:**
- Platform connectors must be complete before Detection and Execution modules can function
- EventEmitter2 wiring must be in place before Monitoring module can consume events
- Prisma schema must be stable before any module can persist state
- Swagger spec must be published before dashboard can generate typed client
- Docker Compose must include PostgreSQL before any integration testing

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Database (Prisma Schema):**
- Tables: `snake_case` plural (`contract_matches`, `audit_logs`, `open_positions`, `risk_states`)
- Columns: `snake_case` (`contract_id`, `created_at`, `confidence_score`, `platform_health`)
- Foreign keys: `<referenced_table_singular>_id` (`position_id`, `match_id`)
- Indexes: `idx_<table>_<columns>` (`idx_audit_logs_created_at`, `idx_contract_matches_platform_ids`)
- Enums: `PascalCase` in Prisma schema (`PlatformId`, `OrderStatus`, `AlertSeverity`)
- Prisma maps `snake_case` DB columns to `camelCase` in TypeScript via `@map`

**API Endpoints:**
- Resources: `kebab-case` plural (`/api/positions`, `/api/alerts`, `/api/contract-matches`)
- Route params: `:id` (NestJS convention)
- Query params: `camelCase` (`startDate`, `platformId`)
- Actions as verbs on resources: `POST /api/matches/:id/approve`, `POST /api/matches/:id/reject`

**Code (TypeScript):**
- Files: `kebab-case` (`platform-connector.interface.ts`, `risk-manager.service.ts`, `kalshi.connector.ts`)
- Classes/Interfaces: `PascalCase` (`IPlatformConnector`, `RiskManagerService`, `KalshiConnector`)
- Functions/methods/variables: `camelCase` (`validatePosition`, `currentExposure`, `onOrderBookUpdate`)
- Constants: `UPPER_SNAKE_CASE` (`MAX_POSITION_SIZE`, `DEFAULT_EDGE_THRESHOLD`)
- NestJS module files: `<module-name>.module.ts`, `<module-name>.service.ts`, `<module-name>.controller.ts`

**Events (EventEmitter2):**
- Dot-notation domain events: `execution.order.filled`, `risk.limit.approached`, `detection.opportunity.identified`, `platform.health.degraded`
- Event class names: `PascalCase` (`OrderFilledEvent`, `LimitApproachedEvent`)

### Structure Patterns

**Test Location:** Co-located with source files. `risk-manager.service.ts` → `risk-manager.service.spec.ts` in the same directory. E2E tests in `/test/` at project root. NestJS convention.

**Module Organization:** Feature-based, matching PRD's 5 core modules:
```
src/
  modules/
    data-ingestion/
    arbitrage-detection/
    execution/
    risk-management/
    monitoring/
  connectors/
    kalshi/
    polymarket/
  common/
    interfaces/
    errors/
    events/
    config/
```

**Shared Code:** `common/` directory for cross-cutting concerns — interfaces, error classes, event definitions, configuration. No `utils/` grab-bag. Module-specific utilities live within that module.

### Format Patterns

**API Response Wrapper:**
```typescript
// Success
{ data: T, timestamp: string }

// Error
{ error: { code: number, message: string, severity: string }, timestamp: string }

// List
{ data: T[], count: number, timestamp: string }
```

No envelope for WebSocket events — typed by event name.

**Date/Time:** ISO 8601 strings in all API responses and JSON (`"2026-02-10T14:32:00.000Z"`). Millisecond precision. Stored as `timestamptz` in PostgreSQL.

**JSON Fields:** `camelCase` in all API responses. Prisma handles mapping from `snake_case` DB columns.

**Null Handling:** Explicit `null` for absent optional values in API responses (not `undefined`, not omitted). API contract is always explicit — frontend always knows the full shape.

### Process Patterns

**Logging:**
- Structured JSON logging via Pino (Fastify default) or NestJS Logger.
- Levels: `error` (system failures), `warn` (degradation, approaching limits), `log` (significant events — trades, alerts), `debug` (hot path details), `verbose` (everything).
- Every log entry includes: `timestamp`, `level`, `module` (which of the 5 modules), `correlationId` (links related events across an execution cycle), `message`, `data`.

**Retry Pattern:** Standardized retry utility with exponential backoff matching PRD error catalog. Each `SystemError` subclass carries its own `retryStrategy` (max retries, backoff intervals). Shared `withRetry(fn, strategy)` utility wraps retryable operations.

**Validation:** Validate at system boundaries only:
- Platform API responses: defensive parsing per NFR-I1
- Dashboard API inputs: NestJS `class-validator` + `class-transformer`
- Configuration at startup
- No redundant validation between internal modules (inter-module trust model)

### Enforcement Guidelines

**All AI Agents MUST:**
- Follow naming conventions exactly as documented — no creative variations
- Place new code in the correct module directory per the structure patterns
- Use the standardized API response wrapper for all REST endpoints
- Emit domain events via EventEmitter2 using dot-notation naming for any observable state change
- Extend `SystemError` hierarchy for all error conditions with appropriate error codes from PRD catalog
- Include `correlationId` in all log entries within an execution cycle
- Write co-located unit tests (`.spec.ts`) for all new services

**Anti-Patterns to Avoid:**
- Creating `utils/`, `helpers/`, or `shared/` directories outside of `common/`
- Mixing `snake_case` and `camelCase` in API responses
- Throwing raw `Error` instead of typed `SystemError` subclasses
- Direct module-to-module imports bypassing interfaces (e.g., importing `RiskManagerService` directly instead of `IRiskManager`)
- Synchronous calls on the fan-out path (Monitoring should never block Execution)
- Inline retry logic instead of using `withRetry()` utility

## Project Structure & Boundaries

### Repository Structure (Multi-Repo Strategy)

**Architecture Decision:** The project uses a **dual-repository structure** for separation of concerns:

1. **Main Repository** (`pm-arbitrage-system/`):
   - Planning artifacts (`_bmad-output/planning-artifacts/`: PRD, architecture, epics)
   - Implementation artifacts (`_bmad-output/implementation-artifacts/`: story files, sprint status)
   - Project documentation (`docs/`, `CLAUDE.md`)
   - BMAD workflow configuration (`_bmad/`)

2. **Engine Repository** (`pm-arbitrage-system/pm-arbitrage-engine/`):
   - **Nested git repository** with independent commit history
   - All implementation code (NestJS backend)
   - Tests, CI/CD pipelines, Docker configuration
   - Database migrations (Prisma)
   - **Not tracked in main repo** (appears as untracked directory `??`)

**Rationale:**
- **Clean separation** between planning/documentation (main repo) and implementation (engine repo)
- **Independent versioning** for engine releases vs documentation updates
- **Simplified engine deployment** (engine repo can be deployed without carrying planning artifacts)
- **BMAD workflow isolation** (BMAD agents work in main repo, code changes in engine repo)

**Important:** Changes in `pm-arbitrage-engine/` are **NOT tracked by main repo**. Story completion requires commits in **BOTH repos**:
1. Main repo: Story file, sprint status updates
2. Engine repo: Implementation code, tests

**Alternative Considered (Not Chosen):** Git submodule integration. Rejected due to complexity of submodule workflows for solo developer environment.

### Complete Project Directory Structure (pm-arbitrage-engine)

```
pm-arbitrage-engine/
├── .github/
│   └── workflows/
│       ├── ci.yml                          # Lint, test, build on PR
│       └── deploy.yml                      # Build image, push, deploy to Hetzner
├── .env.example                            # Template with all config keys (no secrets)
├── .env.development                        # Local dev config (Kalshi sandbox, testnet wallet)
├── .gitignore
├── .prettierrc
├── .eslintrc.js
├── docker-compose.yml                      # postgres + engine + dashboard (nginx)
├── docker-compose.dev.yml                  # postgres only for local dev
├── Dockerfile                              # Multi-stage build: build → production
├── nest-cli.json
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── tsconfig.build.json
├── vitest.config.ts                        # Vitest + unplugin-swc for decorator metadata
├── scripts/
│   ├── deploy.sh                           # Blue/green deployment script
│   ├── backup.sh                           # pg_dump + rclone to Hetzner Object Storage
│   └── restore-test.sh                     # Weekly automated restore validation
├── prisma/
│   ├── schema.prisma                       # All tables: positions, orders, contract_matches,
│   │                                       # audit_logs, risk_states, order_book_snapshots,
│   │                                       # platform_health_logs, compliance_reports
│   ├── migrations/
│   └── seed.ts                             # Dev seed data (test contract pairs, mock positions)
├── src/
│   ├── main.ts                             # Fastify adapter bootstrap, graceful shutdown
│   ├── app.module.ts                       # Root module importing all feature modules
│   ├── common/
│   │   ├── interfaces/
│   │   │   ├── platform-connector.interface.ts    # IPlatformConnector
│   │   │   ├── risk-manager.interface.ts          # IRiskManager
│   │   │   ├── execution-engine.interface.ts      # IExecutionEngine
│   │   │   └── detection-engine.interface.ts      # IDetectionEngine
│   │   ├── errors/
│   │   │   ├── system-error.ts                    # Base SystemError class
│   │   │   ├── platform-api-error.ts              # 1000-1999
│   │   │   ├── execution-error.ts                 # 2000-2999
│   │   │   ├── risk-limit-error.ts                # 3000-3999
│   │   │   └── system-health-error.ts             # 4000-4999
│   │   ├── events/
│   │   │   ├── execution.events.ts                # OrderFilledEvent, SingleLegExposureEvent, etc.
│   │   │   ├── risk.events.ts                     # LimitApproachedEvent, LimitBreachedEvent, etc.
│   │   │   ├── detection.events.ts                # OpportunityIdentifiedEvent, OpportunityFilteredEvent
│   │   │   ├── platform.events.ts                 # PlatformDegradedEvent, PlatformRecoveredEvent
│   │   │   └── monitoring.events.ts               # AlertCreatedEvent, etc.
│   │   ├── constants/
│   │   │   ├── error-codes.ts                     # Centralized 1000-4999 error code enum
│   │   │   ├── risk-limits.ts                     # Default limit values (referenced across modules)
│   │   │   └── platform.ts                        # PlatformId enum, fee constants
│   │   ├── types/
│   │   │   ├── normalized-order-book.type.ts      # Core data contract: ingestion → detection
│   │   │   ├── opportunity.type.ts                # Detected opportunity shape
│   │   │   └── position.type.ts                   # Open position shape
│   │   ├── config/
│   │   │   ├── configuration.ts                   # @nestjs/config factory (typed config)
│   │   │   ├── validation.schema.ts               # Joi/Zod config validation at startup
│   │   │   └── config.types.ts                    # Typed config interfaces
│   │   ├── filters/
│   │   │   └── system-error.filter.ts             # Global exception filter routing by severity
│   │   ├── interceptors/
│   │   │   ├── correlation-id.interceptor.ts      # Generates/propagates correlationId per cycle
│   │   │   └── response-wrapper.interceptor.ts    # Wraps responses in { data, timestamp } envelope
│   │   ├── decorators/
│   │   │   └── api-response.decorator.ts          # Swagger response decorators
│   │   ├── guards/
│   │   │   └── auth-token.guard.ts                # Bearer token validation for dashboard API
│   │   └── utils/
│   │       ├── with-retry.ts                      # Standardized retry with exponential backoff
│   │       ├── crypto.ts                          # Keystore decryption, audit log hash chaining
│   │       └── time.ts                            # NTP sync check, timestamp formatting
│   ├── core/
│   │   ├── core.module.ts
│   │   ├── trading-engine.service.ts              # Main loop orchestrator: poll → detect → evaluate → execute → monitor
│   │   ├── trading-engine.service.spec.ts
│   │   ├── engine-lifecycle.service.ts            # Startup, shutdown, graceful termination hooks
│   │   ├── engine-lifecycle.service.spec.ts
│   │   ├── scheduler.service.ts                   # Polling intervals, NTP checks (6hr), daily test alerts
│   │   └── scheduler.service.spec.ts
│   ├── modules/
│   │   ├── data-ingestion/
│   │   │   ├── data-ingestion.module.ts
│   │   │   ├── data-ingestion.service.ts          # Orchestrates connectors, publishes normalized books
│   │   │   ├── data-ingestion.service.spec.ts
│   │   │   ├── order-book-normalizer.service.ts   # Price normalization logic (Kalshi ¢ → decimal)
│   │   │   ├── order-book-normalizer.service.spec.ts
│   │   │   ├── platform-health.service.ts         # 30-second health status aggregation
│   │   │   └── platform-health.service.spec.ts
│   │   ├── arbitrage-detection/
│   │   │   ├── arbitrage-detection.module.ts
│   │   │   ├── detection.service.ts               # Cross-platform opportunity identification
│   │   │   ├── detection.service.spec.ts
│   │   │   ├── edge-calculator.service.ts         # Net edge calculation (fees, gas, slippage)
│   │   │   └── edge-calculator.service.spec.ts
│   │   ├── contract-matching/
│   │   │   ├── contract-matching.module.ts
│   │   │   ├── contract-matcher.service.ts        # MVP: manual pair lookup; Phase 1: NLP matching
│   │   │   ├── contract-matcher.service.spec.ts
│   │   │   ├── knowledge-base.service.ts          # CRUD for contract_matches table, feedback loop
│   │   │   ├── knowledge-base.service.spec.ts
│   │   │   ├── confidence-scorer.service.ts       # Phase 1: scoring logic, separate for testability
│   │   │   └── confidence-scorer.service.spec.ts
│   │   ├── execution/
│   │   │   ├── execution.module.ts
│   │   │   ├── execution.service.ts               # Coordinated cross-platform order submission
│   │   │   ├── execution.service.spec.ts
│   │   │   ├── leg-manager.service.ts             # Single-leg detection, retry/unwind logic
│   │   │   ├── leg-manager.service.spec.ts
│   │   │   ├── execution-lock.service.ts          # Sequential execution locking (atomic reservation)
│   │   │   └── execution-lock.service.spec.ts
│   │   ├── risk-management/
│   │   │   ├── risk-management.module.ts
│   │   │   ├── risk-manager.service.ts            # Position sizing, limit enforcement
│   │   │   ├── risk-manager.service.spec.ts
│   │   │   ├── correlation-tracker.service.ts     # Cluster exposure calculation
│   │   │   ├── correlation-tracker.service.spec.ts
│   │   │   ├── risk-budget.service.ts             # Daily loss tracking, drawdown monitoring
│   │   │   └── risk-budget.service.spec.ts
│   │   ├── monitoring/
│   │   │   ├── monitoring.module.ts
│   │   │   ├── event-consumer.service.ts          # EventEmitter2 subscriber, routes to outputs
│   │   │   ├── event-consumer.service.spec.ts
│   │   │   ├── telegram-alert.service.ts          # Telegram API integration
│   │   │   ├── telegram-alert.service.spec.ts
│   │   │   ├── audit-log.service.ts               # Append-only + SHA-256 hash chaining
│   │   │   ├── audit-log.service.spec.ts
│   │   │   ├── compliance-report.service.ts       # Quarterly report generation (Phase 1)
│   │   │   └── compliance-report.service.spec.ts
│   │   └── exit-management/
│   │       ├── exit-management.module.ts
│   │       ├── exit-monitor.service.ts            # Continuous position monitoring, exit triggers
│   │       ├── exit-monitor.service.spec.ts
│   │       ├── threshold-evaluator.service.ts     # MVP: fixed thresholds; Phase 1: model-driven
│   │       └── threshold-evaluator.service.spec.ts
│   ├── connectors/
│   │   ├── connector.module.ts                    # Registers all platform connectors
│   │   ├── kalshi/
│   │   │   ├── kalshi.connector.ts                # IPlatformConnector implementation
│   │   │   ├── kalshi.connector.spec.ts
│   │   │   ├── kalshi-api.client.ts               # Raw HTTP client for Kalshi REST API
│   │   │   ├── kalshi-websocket.client.ts         # WebSocket connection management
│   │   │   └── kalshi.types.ts                    # Kalshi-specific API response types
│   │   ├── polymarket/
│   │       ├── polymarket.connector.ts            # IPlatformConnector implementation
│   │       ├── polymarket.connector.spec.ts
│   │       ├── polymarket-websocket.client.ts      # WebSocket connection management
│   │       ├── polymarket-auth.service.ts         # SDK-based wallet auth (API key derivation)
│   │       └── polymarket.types.ts                # Polymarket-specific types
│   │   └── paper/
│   │       ├── paper-trading.connector.ts         # IPlatformConnector decorator (wraps real connector)
│   │       ├── fill-simulator.service.ts          # Simulated fill generation (per-platform params)
│   │       └── paper-trading.types.ts             # PaperTradingConfig, SimulatedFill
│   ├── dashboard/
│   │   ├── dashboard.module.ts
│   │   ├── dashboard.controller.ts                # REST endpoints (/api/health, /api/positions, etc.)
│   │   ├── dashboard.controller.spec.ts
│   │   ├── dashboard.gateway.ts                   # NestJS WebSocket gateway for real-time events
│   │   └── dashboard.gateway.spec.ts
│   ├── reconciliation/
│   │   ├── reconciliation.module.ts               # Dedicated reconciliation module
│   │   ├── startup-reconciliation.service.ts      # Post-crash state reconciliation vs platform APIs
│   │   ├── reconciliation.controller.ts           # REST endpoints for manual reconciliation actions
│   │   └── dto/
│   │       └── resolve-reconciliation.dto.ts      # Validation DTO for reconciliation resolution
│   └── persistence/
│       ├── persistence.module.ts                  # PrismaService, repositories
│       ├── prisma.service.ts                      # Prisma client lifecycle management
│       └── repositories/
│           ├── position.repository.ts
│           ├── order.repository.ts
│           ├── contract-match.repository.ts
│           ├── audit-log.repository.ts
│           ├── risk-state.repository.ts
│           └── order-book-snapshot.repository.ts
└── test/
    ├── e2e/
    │   ├── execution-flow.e2e-spec.ts             # Full detection → risk → execution pipeline
    │   ├── degradation.e2e-spec.ts                # Platform failure → graceful degradation
    │   └── startup-reconciliation.e2e-spec.ts     # Crash recovery scenarios
    └── fixtures/
        ├── order-books.fixture.ts                 # Mock normalized order book data
        ├── contract-pairs.fixture.ts              # Test contract match pairs
        └── platform-responses.fixture.ts          # Mock Kalshi/Polymarket API responses
```

> **ADR (Story 5.5):** Reconciliation was moved from `persistence/` to a dedicated `ReconciliationModule` at `src/reconciliation/` during Story 5.5 to avoid expanding `PersistenceModule`'s dependency surface and preventing circular DI.

### Architectural Boundaries

**Module Dependency Graph (allowed imports):**
```
core/ → modules/* (orchestrates all modules via interfaces)
modules/data-ingestion/ → connectors/ (consumes platform data)
modules/arbitrage-detection/ → modules/contract-matching/ (match validation)
modules/execution/ → connectors/ (submits orders), modules/risk-management/ (budget reservation)
modules/exit-management/ → connectors/ (exit orders), modules/risk-management/ (budget release)
modules/monitoring/ → persistence/ (audit logs, reports), common/events/ (subscribes to all)
modules/contract-matching/ → persistence/ (knowledge base CRUD)
All modules → common/ (interfaces, errors, events, types, constants)
dashboard/ → modules/monitoring/ (event subscription for WebSocket push)
persistence/ → prisma/ (database access)
```

**Forbidden Dependencies:**
- No module imports another module's service directly — only through interfaces in `common/interfaces/`
- `connectors/` never imports from `modules/` — connectors are consumed, not consumers
- `common/` never imports from `modules/`, `connectors/`, `core/`, or `dashboard/`
- `persistence/` never imports from `modules/` — modules depend on persistence, not the reverse

### Data Flow

```
Platform APIs (Kalshi WS, Polymarket REST/Chain)
    ↓
connectors/ (normalize to IPlatformConnector interface)
    ↓
core/trading-engine (orchestrates the polling cycle)
    ↓
modules/data-ingestion/ (aggregate, health check, publish NormalizedOrderBook)
    ↓
modules/arbitrage-detection/ (identify opportunities, calculate edge)
    ↓ uses modules/contract-matching/ (match validation, knowledge base lookup)
    ↓ (synchronous DI call)
modules/risk-management/ (validate position, check limits, reserve budget)
    ↓ (synchronous DI call)
modules/execution/ (submit orders, manage legs, lock execution)
    ↓
modules/exit-management/ (monitor positions, evaluate thresholds, trigger exits)
    ↓ (EventEmitter2 fan-out from all modules)
modules/monitoring/ (audit logs, Telegram alerts, dashboard events, compliance reports)
    ↓
dashboard/ (REST API + WebSocket gateway → React SPA)
    ↓
persistence/ (PostgreSQL via Prisma — positions, audit trail, knowledge base, snapshots)
```

### Requirements to Structure Mapping

| PRD Module | Directory | Key FRs |
|-----------|-----------|---------|
| Engine Lifecycle | `core/` | Graceful shutdown, polling orchestration |
| Reconciliation | `reconciliation/` | Startup reconciliation, crash recovery, orphan detection |
| Data Ingestion | `modules/data-ingestion/` + `connectors/` | FR-DI-01 through FR-DI-05 |
| Arbitrage Detection | `modules/arbitrage-detection/` | FR-AD-01 through FR-AD-04 |
| Contract Matching | `modules/contract-matching/` | FR-CM-01 through FR-CM-04, FR-AD-05 through FR-AD-07 |
| Execution | `modules/execution/` | FR-EX-01 through FR-EX-08 |
| Risk Management | `modules/risk-management/` | FR-RM-01 through FR-RM-09 |
| Monitoring & Alerting | `modules/monitoring/` | FR-MA-01 through FR-MA-09 |
| Exit Management | `modules/exit-management/` | FR-EM-01 through FR-EM-03 |
| Platform Integration | `connectors/kalshi/` + `connectors/polymarket/` | FR-PI-01 through FR-PI-07 |
| Data Export | `modules/monitoring/` + `persistence/repositories/` | FR-DE-01 through FR-DE-04 |
| Scheduling | `core/scheduler.service.ts` | NTP sync (NFR-R5), polling cycle (NFR-P1), daily test alerts |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All technology choices verified compatible — NestJS 11 + Fastify adapter + Prisma 6 + PostgreSQL 16+ + Vitest 4 + viem + EventEmitter2 + @nestjs/schedule + @nestjs/swagger. No version conflicts or incompatible pairings.

**Pattern Consistency:** Naming conventions flow consistently through the stack — `snake_case` in PostgreSQL → Prisma `@map` → `camelCase` in TypeScript → `camelCase` in API JSON responses → `kebab-case` in file names and URL paths. Event naming (dot-notation) aligns with module directory structure. Error hierarchy maps 1:1 to PRD error catalog ranges (1000-4999).

**Structure Alignment:** Module directories map directly to PRD module boundaries. Dependency graph enforces interface-based boundaries at compile time. `core/` orchestrator sits above modules, `common/` sits below — clean layering with no circular dependencies.

### Requirements Coverage ✅

**Functional Requirements:** 100% coverage — all 60+ FRs (FR-DI, FR-AD, FR-EX, FR-RM, FR-MA, FR-EM, FR-CM, FR-PI, FR-DE) mapped to specific directories with clear ownership.

**Non-Functional Requirements:** 100% coverage — all 14 NFRs (Performance P1-P4, Security S1-S4, Reliability R1-R5, Integration I1-I4) addressed by architectural decisions with specific implementation strategies.

### Implementation Readiness ✅

**Decision Completeness:** 15+ decisions across 5 categories, all with explicit rationale, versions specified, and deferred items clearly listed with Phase 1 timeline.

**Structure Completeness:** 70+ files/directories defined. Every service has co-located test file. E2E tests cover 3 critical paths. Module dependency graph with forbidden dependencies documented.

**Pattern Completeness:** Naming, structure, format, communication, and process patterns all defined with examples. Anti-patterns explicitly listed. Enforcement guidelines documented.

### Gap Analysis

**Critical Gaps:** 0

**Important Gaps (non-blocking, address during implementation):**
1. **WebSocket authentication:** `dashboard.gateway.ts` validates Bearer token during `handleConnection` handshake hook. Implementation detail, not architectural gap.
2. **Prisma schema detail:** Full field/relation/index definition deferred to first implementation story. PRD knowledge base schema provides reference.
3. **Dashboard repo structure:** Standard Vite + React + shadcn/ui — no separate architectural specification needed.

**Nice-to-Have (adopted):**
1. **OpenAPI spec committed to repo:** NestJS Swagger module auto-generates and exports spec as part of CI build. Dashboard type generation pulls from committed spec file rather than hitting running server.
2. **ADR format:** Formalize Architecture Decision Record format for future decisions during implementation. This architecture document serves as the initial ADR collection.

**Deferred to Phase 1:**
- Runbook templates (operational procedures stabilize first)
- WAL-based continuous archiving
- Caddy reverse proxy + HTTPS + JWT session management
- Secrets manager migration

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (60+ FRs, 14 NFRs, fintech/api_backend/high complexity)
- [x] Scale and complexity assessed (single operator, 5 core modules, real-time event pipeline)
- [x] Technical constraints identified (single process, heterogeneous platforms, 7-year compliance)
- [x] Cross-cutting concerns mapped (6 concerns: platform abstraction, state management, observability, error handling, configuration, progressive sophistication)

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions (NestJS 11, Prisma 6, PostgreSQL 16+, Vitest 4, viem)
- [x] Technology stack fully specified across all layers (language, framework, ORM, testing, blockchain, dashboard, deployment, CI/CD)
- [x] Integration patterns defined (hybrid sync/async, EventEmitter2, IPlatformConnector, Swagger-generated types)
- [x] Performance considerations addressed (in-memory caching, single event loop, no network hops on hot path)

**✅ Implementation Patterns**
- [x] Naming conventions established (DB, API, code, events — all with examples)
- [x] Structure patterns defined (feature-based modules, co-located tests, common/ for cross-cutting)
- [x] Communication patterns specified (sync DI hot path, async EventEmitter2 fan-out)
- [x] Process patterns documented (structured logging with correlationId, withRetry(), boundary-only validation, centralized error classes)

**✅ Project Structure**
- [x] Complete directory structure defined (70+ files across core/, modules/, connectors/, common/, dashboard/, persistence/)
- [x] Component boundaries established (dependency graph with forbidden dependencies)
- [x] Integration points mapped (data flow diagram from platform APIs through execution pipeline to dashboard)
- [x] Requirements to structure mapping complete (all FR groups mapped to specific directories)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — 100% FR/NFR coverage, zero critical gaps, coherent technology choices, clean module boundaries.

**Key Strengths:**
1. 1:1 mapping between PRD modules and code structure — traceability from requirement to file
2. Clean separation of synchronous hot path (detect → risk → execute) and async observability (EventEmitter2 fan-out to monitoring)
3. Platform connector abstraction (`IPlatformConnector`) satisfies extensibility requirement (FR-DI-05) from day one
4. Encrypted keystore for Polymarket private key — proportional security without over-engineering
5. Progressive sophistication path defined at every module (MVP manual → Phase 1 NLP/model-driven)
6. `core/` orchestrator prevents engine lifecycle logic from bleeding into domain modules

**Areas for Future Enhancement:**
- WAL-based continuous archiving for point-in-time recovery (Phase 1)
- Caddy reverse proxy + HTTPS + JWT session management (Phase 1)
- Secrets manager migration (Phase 1)
- Multi-platform connector additions (Phase 1+)
- ADR format formalization for future decisions
- Runbook templates for operational procedures (Phase 1)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented — technology versions, naming conventions, module boundaries
- Use implementation patterns consistently across all components — response wrappers, error classes, event naming, logging structure
- Respect project structure and forbidden dependencies — no module bypasses interfaces, no connector imports modules
- Emit domain events for all observable state changes — never skip the fan-out path
- Extend `SystemError` hierarchy for all error conditions — never throw raw `Error`
- Include `correlationId` in all log entries within an execution cycle

**First Implementation Priority:**
1. `nest new pm-arbitrage-system --strict --package-manager pnpm` + Fastify swap + core dependency installation
2. Docker Compose with PostgreSQL + Prisma schema initialization
3. Module scaffolding (core/, all 7 modules, connectors/, common/, dashboard/, persistence/)
4. Common infrastructure (error classes, event definitions, interfaces, config validation, guards, interceptors)
