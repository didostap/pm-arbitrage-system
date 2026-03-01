# Codebase Structure

## Root Directory

```
/
├── pm-arbitrage-engine/    # Main application code (WORKING DIRECTORY, independent git repo)
├── docs/                   # Project documentation (currently empty)
├── _bmad-output/          # BMAD artifacts
├── _bmad/                 # BMAD config
├── CLAUDE.md              # Claude Code instructions
└── .claude/               # Claude memory + project config
```

## pm-arbitrage-engine/src/ Full Structure

```
src/
├── main.ts
├── app.module.ts / app.controller.ts / app.service.ts
│
├── core/
│   ├── core.module.ts
│   ├── trading-engine.service.ts         # Main orchestrator: ingest → detect → edge calc → risk → execute
│   ├── engine-lifecycle.service.ts       # Bootstrap/shutdown: config validation, reconciliation, risk init
│   └── scheduler.service.ts             # @Interval polling cycles, NTP checks
│
├── modules/
│   ├── data-ingestion/
│   │   ├── data-ingestion.module.ts
│   │   ├── data-ingestion.service.ts     # WebSocket subscription, order book polling, snapshot persistence
│   │   ├── order-book-normalizer.service.ts  # Platform-specific → NormalizedOrderBook
│   │   ├── platform-health.service.ts    # Health calculation, p95 latency, staleness detection
│   │   └── degradation-protocol.service.ts   # Platform degradation state, edge threshold multiplier
│   │
│   ├── arbitrage-detection/
│   │   ├── arbitrage-detection.module.ts
│   │   ├── detection.service.ts          # Cross-platform dislocation detection
│   │   ├── edge-calculator.service.ts    # Net edge with fees/gas, liquidity depth, position sizing
│   │   ├── types/                        # RawDislocation, EnrichedOpportunity, EdgeCalculationResult, DetectionCycleResult
│   │   └── __tests__/edge-calculation-scenarios.csv
│   │
│   ├── contract-matching/
│   │   ├── contract-matching.module.ts
│   │   ├── contract-pair-loader.service.ts   # YAML config reader → PairConfig[]
│   │   ├── contract-match-sync.service.ts    # Sync YAML pairs → ContractMatch DB table
│   │   ├── dto/contract-pair.dto.ts
│   │   └── types/contract-pair-config.type.ts
│   │
│   ├── execution/
│   │   ├── execution.module.ts
│   │   ├── execution.service.ts          # Two-leg execution: verify depth → submit → persist → events
│   │   ├── execution-queue.service.ts    # Budget reservation → execute → commit/release
│   │   ├── execution-lock.service.ts     # Concurrency guard
│   │   ├── single-leg-resolution.service.ts  # Retry/close exposed legs
│   │   ├── single-leg-resolution.controller.ts  # REST API for operator actions
│   │   ├── exposure-tracker.service.ts   # Weekly/monthly single-leg exposure tracking
│   │   ├── exposure-alert-scheduler.service.ts  # Periodic re-emit of exposure alerts
│   │   ├── single-leg-pnl.util.ts        # P&L scenarios, recommended actions
│   │   ├── execution.constants.ts
│   │   ├── retry-leg.dto.ts / close-leg.dto.ts
│   │
│   ├── risk-management/
│   │   ├── risk-management.module.ts
│   │   ├── risk-manager.service.ts       # Budget, position limits, daily loss, halt/resume, overrides
│   │   ├── risk-management.constants.ts
│   │   ├── risk-override.controller.ts   # POST /api/risk/override (auth-guarded)
│   │   └── dto/risk-override.dto.ts
│   │
│   ├── exit-management/
│   │   ├── exit-management.module.ts
│   │   ├── exit-monitor.service.ts       # @Interval(30s) position evaluation
│   │   └── threshold-evaluator.service.ts  # P&L targets, time-based exit triggers
│   │
│   └── monitoring/
│       └── .gitkeep                      # NOT YET IMPLEMENTED
│
├── connectors/
│   ├── connector.module.ts / connector.constants.ts / connector.module.spec.ts
│   ├── paper/
│   │   ├── paper-trading.types.ts            # PaperTradingConfig, SimulatedOrder, PAPER_MAX_ORDERS
│   │   ├── fill-simulator.service.ts         # Simulated fill generation (Decimal math, LRU eviction)
│   │   ├── fill-simulator.service.spec.ts    # 11 tests
│   │   ├── paper-trading.connector.ts        # IPlatformConnector wrapper (real data + simulated execution)
│   │   └── paper-trading.connector.spec.ts   # 13 tests
│   ├── kalshi/
│   │   ├── kalshi.connector.ts           # IPlatformConnector implementation (REST + WebSocket)
│   │   ├── kalshi-websocket.client.ts    # Snapshot/delta WS order book management
│   │   ├── kalshi.types.ts
│   │   └── kalshi-sdk.d.ts               # Type declarations for kalshi-typescript SDK
│   └── polymarket/
│       ├── polymarket.connector.ts       # IPlatformConnector implementation (CLOB + viem)
│       ├── polymarket-websocket.client.ts  # WS order book management
│       ├── polymarket.types.ts
│       └── polymarket-error-codes.ts
│
├── reconciliation/
│   ├── reconciliation.module.ts
│   ├── startup-reconciliation.service.ts # Verify positions/orders vs platform state on boot
│   ├── reconciliation.controller.ts      # GET /status, POST /run, POST /resolve
│   └── dto/resolve-reconciliation.dto.ts
│
├── persistence/
│   └── repositories/
│       ├── position.repository.ts        # CRUD + specialized queries (with orders, with pair)
│       └── order.repository.ts           # CRUD + pair-based queries
│
├── common/
│   ├── prisma.service.ts / persistence.module.ts
│   ├── interfaces/
│   │   ├── platform-connector.interface.ts  # IPlatformConnector (11 methods)
│   │   ├── risk-manager.interface.ts        # IRiskManager (12 methods)
│   │   ├── execution-engine.interface.ts    # IExecutionEngine, ExecutionResult
│   │   └── execution-queue.interface.ts     # IExecutionQueue
│   ├── types/
│   │   ├── normalized-order-book.type.ts    # NormalizedOrderBook, PriceLevel
│   │   ├── platform.type.ts                 # PlatformId enum, OrderParams, OrderResult, FeeSchedule, etc.
│   │   ├── risk.type.ts                     # RiskConfig, RiskDecision, BudgetReservation, RankedOpportunity, etc.
│   │   ├── reconciliation.types.ts          # ReconciliationResult, ReconciliationDiscrepancy, etc.
│   │   └── ntp.type.ts
│   ├── errors/
│   │   ├── system-error.ts              # Base error class
│   │   ├── platform-api-error.ts        # Codes 1000-1999
│   │   ├── execution-error.ts           # Codes 2000-2999
│   │   ├── risk-limit-error.ts          # Codes 3000-3999
│   │   ├── system-health-error.ts       # Codes 4000-4999
│   │   └── config-validation-error.ts
│   ├── events/
│   │   ├── event-catalog.ts             # EVENT_NAMES constant (30 event types)
│   │   ├── base.event.ts                # BaseEvent class
│   │   ├── execution.events.ts          # OrderFilled, SingleLegExposure, SingleLegResolved, ExitTriggered, etc.
│   │   ├── detection.events.ts
│   │   ├── risk.events.ts
│   │   ├── platform.events.ts
│   │   ├── orderbook.events.ts
│   │   ├── system.events.ts
│   │   └── time.events.ts
│   ├── utils/
│   │   ├── financial-math.ts            # FinancialMath class (Decimal-based edge calculations)
│   │   ├── rate-limiter.ts              # Token bucket with read/write channels + tier presets
│   │   ├── with-retry.ts               # Retry utility with backoff
│   │   ├── ntp-sync.util.ts            # NTP time synchronization
│   │   ├── kalshi-price.util.ts        # Kalshi cents ↔ decimal conversion
│   │   └── platform.ts                 # Platform utility functions
│   ├── services/
│   │   └── correlation-context.ts       # AsyncLocalStorage-based correlationId
│   ├── guards/
│   │   └── auth-token.guard.ts          # Bearer token auth for API endpoints
│   └── config/
│       └── logger.config.ts             # Pino logger configuration
│
├── prisma/
│   ├── schema.prisma                    # 8 models, 3 enums
│   └── migrations/                      # Prisma migration files
│
└── test/                                # E2E tests
    ├── setup.ts
    ├── app.e2e-spec.ts
    ├── core-lifecycle.e2e-spec.ts
    ├── data-ingestion.e2e-spec.ts
    └── logging.e2e-spec.ts
```

## Dashboard Module (added in Story 7.1)

```
src/dashboard/
├── dashboard.module.ts
├── dashboard.controller.ts / dashboard.controller.spec.ts
├── dashboard.service.ts / dashboard.service.spec.ts
├── dashboard.gateway.ts / dashboard.gateway.spec.ts      # WebSocket gateway (@nestjs/platform-ws)
├── dashboard-event-mapper.service.ts / .spec.ts           # Internal events → WS events
└── dto/
    ├── index.ts
    ├── dashboard-overview.dto.ts / platform-health.dto.ts
    ├── position-summary.dto.ts / alert-summary.dto.ts
    ├── ws-events.dto.ts                                    # WS event payload interfaces
    └── response-wrappers.dto.ts                            # { data, timestamp } Swagger wrappers
```

## Monitoring Module (added in Story 6.x)

```
src/modules/monitoring/
├── monitoring.module.ts
├── event-consumer.service.ts           # Central event subscription hub
├── telegram-alert.service.ts           # Telegram Bot API integration
├── csv-trade-log.service.ts            # Daily CSV logs
├── compliance-checker.service.ts       # Pre-trade compliance
├── trade-export.controller.ts          # GET /exports/trades, /tax-report
└── dto/
    ├── trade-export-query.dto.ts
    └── tax-report-query.dto.ts
```

## Response DTOs for existing controllers (added in Story 7.1)

- `src/common/dto/health-check-response.dto.ts` — AppController
- `src/modules/execution/dto/single-leg-response.dto.ts` — SingleLegResolutionController
- `src/modules/risk-management/dto/risk-override-response.dto.ts` — RiskOverrideController
- `src/reconciliation/dto/reconciliation-response.dto.ts` — ReconciliationController

## Dashboard SPA (pm-arbitrage-dashboard/ — separate repo)

```
pm-arbitrage-dashboard/
├── Dockerfile / nginx.conf / entrypoint.sh
├── src/
│   ├── api/client.ts + generated/ (swagger-typescript-api)
│   ├── components/ (HealthComposite, MetricDisplay, DashboardPanel, ConnectionStatus)
│   ├── components/ui/ (shadcn: badge, card, alert, tooltip)
│   ├── hooks/useDashboard.ts
│   ├── providers/WebSocketProvider.tsx
│   ├── pages/DashboardPage.tsx
│   ├── types/ws-events.ts
│   └── lib/env.ts, utils.ts
└── public/env.js (runtime env injection)
```

## NOT YET IMPLEMENTED (from CLAUDE.md architecture)

- `common/filters/` — Global exception filter
- `common/interceptors/` — correlationId, response wrapper