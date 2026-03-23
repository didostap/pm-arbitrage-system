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

### Testing Conventions (Epic 9 Retro)

- **Internal subsystem verification:** Tests must verify data actually arrives through claimed channels, not just that receiving code handles it correctly. If a module claims to receive data from WebSocket, test that the subscription exists and data flows — don't just test that the handler processes mock data.
- **Paper/live boundary testing:** Paper mode has fundamentally different execution semantics (simulated fills, no platform API verification). Every `isPaper` branch needs explicit dual-path test coverage. Create dedicated tests for paper/live divergent behavior.
- **Investigation-first pattern:** If a problem statement includes "intermittent," "unclear why," or "sometimes," the first task is investigation with documented findings before code changes. Do not assume the root cause.

### Testing Conventions (Epic 10 Retro)

- **Event wiring verification:** Every new `@OnEvent` handler MUST have a corresponding `expectEventHandled()` integration test verifying the decorator actually connects the emitter to the handler via real EventEmitter2. Use the helper in `src/common/testing/expect-event-handled.ts`. Do NOT rely on mocked EventEmitter2 for wiring verification.
- **Collection lifecycle requirement:** Every new `Map`/`Set` in a service MUST specify its cleanup strategy in a code comment (e.g., `/** Cleanup: .delete() on X, .clear() on Y */`) AND have a test verifying the cleanup path works. Unbounded collections must have a documented bound or TTL mechanism.

### Testing Conventions (Epic 10.5 — Paper/Live Mode Boundary)

- **Dual-mode test coverage for `isPaper` branches:** Any story introducing mode-dependent behavior MUST include dedicated tests verifying paper operations do not affect live state and vice versa. Use `describe.each([[true, 'paper'], [false, 'live']])` for dual-mode test matrix. Tests go in `src/common/testing/paper-live-boundary/` organized by module.
- **Repository mode-scoping:** All repository methods querying `open_positions` or `orders` with status filters MUST accept a required `isPaper: boolean` parameter (no defaults). Use the `withModeFilter(isPaper)` helper from `src/persistence/repositories/mode-filter.helper.ts` internally for where clauses. The `= false` default was the exact pattern that caused the 10.1 post-deploy bug.
- **Raw SQL `-- MODE-FILTERED` marker:** Every raw SQL query (`$queryRaw`, `$executeRaw`) referencing mode-sensitive tables (`open_positions`, `orders`, `risk_states`) MUST include `is_paper` filtering AND the `-- MODE-FILTERED` comment marker at the end of the query. Health check queries (`SELECT 1`) are exempt.

## Story Design Conventions (Epic 9 Retro)

- **Vertical slice minimum:** Every story that adds a backend capability MUST include at least minimal dashboard observability. An unobservable feature is an unvalidated feature. Story ACs should specify what the operator can see.
- **Compiler-driven migration:** When introducing a new type (e.g., branded types), intentionally break compilation and use the error list as the task list. This ensures complete coverage across the codebase.
- **Dual data path divergence:** Any architecture with parallel data paths (e.g., polling + WebSocket) MUST include observable divergence detection with alerting. Use the more conservative data for safety-critical decisions.

## Story Design Conventions (Epic 10 Retro)

- **Story sizing gate (Agreement #25):** Stories exceeding 10 tasks or 3+ integration boundaries MUST be flagged for splitting during story preparation. Story 10-0-1 (7 phases, 17 tasks, 5 CRITICAL review findings) demonstrated that oversized stories fragment the developer's mental model and make integration seam verification impractical. Pre-split review during preparation, not after implementation reveals the problem.

## Story Design Conventions (Epic 10.5 Retro)

- **Design sketch gate for hot-path stories (Agreement #27):** Any story touching execution, edge calculation, or risk management gets a lightweight design sketch reviewed by the architect before implementation begins. Scope: TOCTOU race analysis, fail-closed semantics, `isPaper` mode handling, module boundary interactions. The sketch is not a full design doc — it's a 15-minute review that catches architecture-class flaws before they become code review findings. Validated by 10-5-2 where a design review would have prevented a full hot-reload architecture rewrite.
- **Pre-implementation naming walkthrough (Agreement #29):** Story author and implementer do a 5-minute walkthrough of string literals, enum values, DTO field names, and API path conventions before coding starts. Prevents spec-to-implementation naming divergence that caused cascading E2E test failures in 10-5-3.

## Code Review Conventions (Epic 10.5 Retro)

- **Reviewer redundancy (Agreement #28):** Identify a fallback reviewer before each epic starts. If the primary Lad MCP reviewer fails after 3 retries, escalate to the fallback — different model, second instance, or structured self-review protocol with documented checklist. Addresses single point of failure where secondary reviewer (glm-5-turbo) consistently failed in Epic 10.5.

## Code Review Conventions (Epic 10 Retro)

- **Assertion depth:** Test assertions MUST verify payloads with `expect.objectContaining({...})` or equivalent. Bare `toHaveBeenCalled()` without argument verification is insufficient for event emission and service call tests. This was the most common MEDIUM finding (30%) in Epic 10 code reviews.
- **Dead code removal:** Remove unused imports, dead DTO fields, and stale comments immediately. Use `expectNoDeadHandlers()` from `src/common/testing/expect-event-handled.ts` for dead event handler detection. TypeScript strict mode (`noUnusedLocals`, `noUnusedParameters`) catches dead imports at compile time.
- **Boundary type safety:** Always convert Prisma Decimal fields via `new Decimal(value.toString())`. Validate external API responses at the boundary with explicit checks. Use branded entity ID types. Never trust `configService.get<boolean>()` for env vars — NestJS returns strings; parse explicitly.

## Process Conventions (Epic 10 Retro)

- **Retro commitments as deliverables (Agreement #24):** Every retro action item MUST be expressible as a story with acceptance criteria or a task within a story. Open-ended discipline commitments without enforcement mechanisms are rejected at retro time. If it can't be a story, rephrase until it can.
- **Structural guards over review vigilance (Agreement #26):** If code review catches the same defect category three times across an epic, it becomes a pre-epic story with structural prevention (test templates, linter rules, startup checks) — not a "be more careful" agreement. Recurring defect classes need constraints, not vigilance.

## Session Initialization

- **Serena activation:** Activate Serena at the start of every session (if Serena tools are present in the environment). If activation fails for reasons outside your control, continue without it and explain why.
- **Baseline verification:** Before making changes, run the project's existing test suite to confirm the baseline is green. If tests are already failing, surface this to the user — a known-good starting point is required before proceeding unless the user explicitly acknowledges the failures and instructs to continue.
- **Serena memory maintenance:** When Serena is available, record notable design decisions, useful patterns, and non-obvious implementation details to the appropriate Serena memory files as you work (e.g., `project_overview`, `suggested_commands`, `code_style`).

## Post-Edit Workflow

1. Complete all code changes
2. Run `cd pm-arbitrage-engine && pnpm lint`
3. Fix any remaining errors
4. Run `pnpm test`
5. Only then mark task as complete

## Post-Implementation Review

- **Lad MCP code review:** Once implementation is complete and all tests pass, submit the work for review using Lad MCP's `code_review` tool. This catches coherence-driven mistakes — errors difficult to self-detect because each generated token reinforces earlier choices.
- **Scope precisely:** Use the `paths` parameter pointed at files created or modified during this task. Include relevant acceptance criteria and architectural constraints in the `context` parameter for project-aware review.
- **Retry on failure:** The Lad MCP `code_review` tool returns two independent reviewer responses. The connection may fail due to network instability or cold starts. Retry up to 3 attempts with a brief pause between each. If only one reviewer responds after all retries, use that single response. If the tool is not available in the environment or all retries fail, report the failure to the user and proceed without external review.
- **Evaluate critically:** Address genuine bugs, security vulnerabilities, AC violations, or architectural mismatches. For stylistic suggestions or debatable trade-offs, apply judgment — if you disagree, note your reasoning and move on. When reviewers contradict each other, favor the finding that better aligns with the task's acceptance criteria.
- **Re-test after fixes:** If changes are made based on review feedback, re-run affected tests to confirm no regressions.

## Domain Rules

- **Price normalization:** Internal = decimal probability (0.00-1.00). Kalshi uses cents (÷100). Polymarket already decimal.
- **Edge calculation:** `|Price_A - Price_B| - fees - gas`. Minimum threshold: 0.8% net.
- **Single-leg exposure:** Detection within 5 seconds. Alert operator immediately with full context.
- **Contract matching errors:** ZERO tolerance. Any matching error halts trading.
- **Rate limits:** Stay under 70% of platform limits. 20% safety buffer on enforcement.
- **Position sizing:** Max 3% of bankroll per pair. Correlation cluster max 15%.
- **Financial math:** ALL financial calculations MUST use `decimal.js` (`Decimal`). NEVER use native JS `*`, `+`, `-`, `/` operators on monetary values — floating-point precision loss is unacceptable (e.g., `0.1 + 0.2 === 0.30000000000000004`). Use `.mul()`, `.plus()`, `.minus()`, `.div()`. When reading Prisma `Decimal` fields, convert via `new Decimal(value.toString())` — `Prisma.Decimal` and `decimal.js Decimal` are different types and cannot be used interchangeably.

## Environment

- `.env.development` — Local dev (PostgreSQL on port 5433)
- `.env.production` — Production (localhost-only binding via SSH tunnel)
- `.env.example` — Template with all required variables

## Tool Preferences

- **Web research:** Use `kindly-web-search` MCP tools (`web_search`, `get_content`) for all external lookups — API signatures, version behavior, breaking changes, deprecations, library docs, error diagnostics, unfamiliar patterns. Skip verification only for stable, well-known APIs where confidence is high. If `kindly-web-search` fails or is unavailable, notify the user immediately and describe what was being looked up — do not silently proceed without required research. Never use default `WebSearch`/`WebFetch`.

## Troubleshooting

- **"Prisma Client not found"** → `pnpm prisma generate`
- **Port conflict** → `docker ps`, stop conflicting containers
- **Module not found** → `pnpm install` and restart
- **TS errors after schema change** → `pnpm prisma generate`