# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

PM Arbitrage System — institutional-grade automated trading engine exploiting cross-platform arbitrage in prediction markets (Polymarket ↔ Kalshi). NestJS 11 + Fastify + Prisma 6 + PostgreSQL 16+ + TypeScript strict mode.

**Working Directory:** All development work happens in `/pm-arbitrage-engine/`. Root contains project docs and BMAD config.

## Repository Structure (CRITICAL)

**This project uses a DUAL-REPOSITORY structure:**

1. **Main Repo** (current directory): Planning artifacts, story files, BMAD config, documentation
2. **Engine Repo** (`pm-arbitrage-engine/`): **Nested independent git repository** with implementation code

**IMPORTANT:** `pm-arbitrage-engine/` has its own `.git` directory and is **NOT tracked** by the main repo. Changes in the engine repo require **separate commits**.

## Commands

```bash
cd pm-arbitrage-engine

# Dev
pnpm install
pnpm start:dev              # Hot-reload
pnpm build                  # Production build

# Test
pnpm test                   # Vitest (run before committing)
pnpm test:watch             # Watch mode
pnpm test:cov               # Coverage

# Quality
pnpm lint                   # ESLint (auto-fix). ALWAYS run after edits.
pnpm format                 # Prettier

# Database
pnpm prisma migrate dev --name <name>   # Create migration
pnpm prisma generate                     # Regenerate client
pnpm prisma studio                       # DB GUI

# Docker
docker-compose -f docker-compose.dev.yml up -d   # PostgreSQL only
docker-compose up                                  # Full stack
```

## Architecture

Full architecture decisions: see `docs/architecture.md`
Full requirements: see `docs/prd.md`

### Module Structure

```
src/
├── core/                           # Engine lifecycle, trading loop orchestrator, scheduler
├── modules/
│   ├── data-ingestion/             # Platform API connections, order book normalization
│   ├── arbitrage-detection/        # Cross-platform opportunity identification
│   ├── contract-matching/          # Manual pair lookup (MVP) → NLP matching (Phase 1)
│   ├── execution/                  # Cross-platform order submission, leg management
│   ├── risk-management/            # Position sizing, correlation limits, loss limits
│   ├── monitoring/                 # Audit logs, Telegram alerts, compliance reports
│   └── exit-management/            # Position monitoring, exit triggers
├── connectors/
│   ├── kalshi/                     # IPlatformConnector implementation (REST/WebSocket)
│   └── polymarket/                 # IPlatformConnector implementation (on-chain via viem)
├── common/
│   ├── interfaces/                 # IPlatformConnector, IRiskManager, IExecutionEngine, IDetectionEngine
│   ├── errors/                     # SystemError hierarchy (codes 1000-4999)
│   ├── events/                     # Domain event classes (EventEmitter2)
│   ├── types/                      # NormalizedOrderBook, Opportunity, Position
│   ├── constants/                  # Error codes, risk limits, platform enums
│   ├── config/                     # @nestjs/config typed configuration
│   ├── filters/                    # Global exception filter (routes by severity)
│   ├── interceptors/               # correlationId, response wrapper
│   ├── guards/                     # Bearer token auth
│   └── utils/                      # withRetry(), crypto, time/NTP
├── dashboard/                      # REST + WebSocket gateway for operator UI
└── persistence/                    # PrismaService, repositories, startup reconciliation
```

### Communication Patterns

**Hot path (synchronous DI injection) — BLOCKING IS CORRECT HERE:**
```
Detection → Risk validation → Execution
```
Never execute without risk validation completing. This is a direct synchronous call chain.

**Fan-out (async EventEmitter2) — NEVER BLOCK EXECUTION:**
```
All modules emit events → Monitoring subscribes → Dashboard, Telegram, audit logs
```
Telegram API timeouts must never delay the next execution cycle.

### Module Dependency Rules

**IMPORTANT — These are hard constraints. Violations break the architecture.**

Allowed imports:
- `core/` → `modules/*` (orchestrates via interfaces)
- `modules/data-ingestion/` → `connectors/` (consumes platform data)
- `modules/execution/` → `connectors/` (submits orders) + `modules/risk-management/` (budget reservation)
- `modules/exit-management/` → `connectors/` (exit orders) + `modules/risk-management/` (budget release)
- `modules/arbitrage-detection/` → `modules/contract-matching/` (match validation)
- `modules/monitoring/` → `persistence/` (audit logs) + `common/events/`
- All modules → `common/` (interfaces, errors, events, types, constants)

**FORBIDDEN — never create these imports:**
- No module imports another module's service directly — only through interfaces in `common/interfaces/`
- `connectors/` NEVER imports from `modules/`
- `common/` NEVER imports from `modules/`, `connectors/`, `core/`, or `dashboard/`
- `persistence/` NEVER imports from `modules/`

### Error Handling

**YOU MUST extend the SystemError hierarchy. NEVER throw raw `Error` or generic NestJS exceptions.**

```
SystemError (base)
├── PlatformApiError      (codes 1000-1999) — API failures, auth, rate limits
├── ExecutionError        (codes 2000-2999) — Order failures, single-leg exposure
├── RiskLimitError        (codes 3000-3999) — Limit breaches, position sizing
└── SystemHealthError     (codes 4000-4999) — State corruption, staleness, disk/memory
```

Each error carries: `severity`, `retryStrategy`, contextual data. The global exception filter routes by severity:
- Critical → high-priority event (Telegram + audit + potential halt)
- Warning → dashboard update + log
- Info → log only

### Event Emission

**Every observable state change MUST emit a domain event via EventEmitter2.**

Event naming: dot-notation matching module structure.
```
execution.order.filled
execution.single-leg.detected
risk.limit.approached
risk.limit.breached
detection.opportunity.identified
detection.opportunity.filtered
platform.health.degraded
platform.health.recovered
```

Event classes in `common/events/` — use PascalCase (e.g., `OrderFilledEvent`).

### API Response Format

All REST endpoints use standardized wrappers:
```typescript
// Success
{ data: T, timestamp: string }

// Error
{ error: { code: number, message: string, severity: string }, timestamp: string }

// List
{ data: T[], count: number, timestamp: string }
```

JSON fields: `camelCase`. Null for absent optionals (never `undefined`, never omitted).

### Logging

Structured JSON. Every log entry includes: `timestamp`, `level`, `module`, `correlationId`, `message`, `data`.

The `correlationId` links related events across an execution cycle. Use the `correlation-id.interceptor.ts`.

## Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Files | kebab-case | `risk-manager.service.ts` |
| Classes/Interfaces | PascalCase | `IRiskManager`, `KalshiConnector` |
| Functions/variables | camelCase | `validatePosition`, `currentExposure` |
| Constants | UPPER_SNAKE_CASE | `MAX_POSITION_SIZE` |
| DB tables | snake_case (Prisma @map) | `contract_matches`, `audit_logs` |
| DB columns | snake_case (Prisma @map) | `confidence_score`, `created_at` |
| API URLs | kebab-case | `/api/contract-matches` |
| API JSON fields | camelCase | `confidenceScore` |
| Events | dot-notation | `execution.order.filled` |

## Testing

- **Co-located:** `risk-manager.service.ts` → `risk-manager.service.spec.ts` (same directory)
- **E2E:** in `test/e2e/`
- **Framework:** Vitest + unplugin-swc for decorator metadata
- **Run before committing.** Do not commit if tests fail.

## Post-Edit Workflow

1. Complete all code changes
2. Run `cd pm-arbitrage-engine && pnpm lint`
3. Fix any remaining errors
4. Run `pnpm test`
5. Only then mark task as complete

## Domain Rules

- **Price normalization:** Internal = decimal probability (0.00-1.00). Kalshi uses cents (÷100). Polymarket already decimal.
- **Edge calculation:** `|Price_A - Price_B| - fees - gas`. Minimum threshold: 0.8% net.
- **Single-leg exposure:** Detection within 5 seconds. Alert operator immediately with full context.
- **Contract matching errors:** ZERO tolerance. Any matching error halts trading.
- **Rate limits:** Stay under 70% of platform limits. 20% safety buffer on enforcement.
- **Position sizing:** Max 3% of bankroll per pair. Correlation cluster max 15%.

## Environment

- `.env.development` — Local dev (PostgreSQL on port 5433)
- `.env.production` — Production (localhost-only binding via SSH tunnel)
- `.env.example` — Template with all required variables

## Troubleshooting

- **"Prisma Client not found"** → `pnpm prisma generate`
- **Port conflict** → `docker ps`, stop conflicting containers
- **Module not found** → `pnpm install` and restart
- **TS errors after schema change** → `pnpm prisma generate`