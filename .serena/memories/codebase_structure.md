# Codebase Structure

## Root Directory
```
/
├── pm-arbitrage-engine/    # Main application code (WORKING DIRECTORY)
├── docs/                   # Project documentation
├── _bmad-output/          # BMAD artifacts
├── CLAUDE.md              # Claude Code instructions
└── README.md              # Project overview
```

## pm-arbitrage-engine/ Structure
```
pm-arbitrage-engine/
├── src/                   # Source code
│   ├── main.ts            # Application entry point
│   ├── app.module.ts      # Root NestJS module
│   ├── app.controller.ts  # Root controller
│   ├── app.service.ts     # Root service
│   ├── modules/           # Feature modules
│   │   ├── arbitrage-detection/
│   │   ├── data-ingestion/
│   │   ├── execution/
│   │   ├── monitoring/
│   │   └── risk-management/
│   ├── connectors/        # External platform integrations
│   │   ├── kalshi/
│   │   └── polymarket/
│   ├── core/              # Core engine services
│   │   ├── trading-engine.service.ts
│   │   ├── engine-lifecycle.service.ts
│   │   └── scheduler.service.ts
│   └── common/            # Shared utilities
│       ├── types/         # Type definitions
│       ├── config/        # Configuration
│       ├── utils/         # Utilities (retry, rate-limiter)
│       ├── errors/        # Error classes
│       ├── events/        # Event definitions
│       ├── interfaces/    # Interfaces
│       └── prisma.service.ts
├── prisma/
│   └── schema.prisma      # Database schema
├── test/                  # E2E and integration tests
├── dist/                  # Build output
├── docker-compose.yml     # Production Docker setup
├── docker-compose.dev.yml # Development Docker setup
├── Dockerfile             # Container definition
├── vitest.config.ts       # Test configuration
├── tsconfig.json          # TypeScript config
├── eslint.config.mjs      # ESLint config
├── .prettierrc            # Prettier config
├── .env.development       # Dev environment vars
├── .env.example           # Environment template
└── package.json           # Dependencies and scripts
```

## Key Module Responsibilities
- **arbitrage-detection:** Identifies arbitrage opportunities
- **data-ingestion:** Fetches and normalizes market data
- **execution:** Executes trades
- **monitoring:** System health and metrics
- **risk-management:** Position limits and risk controls
- **connectors:** API clients for Kalshi and Polymarket
- **core:** Main trading engine orchestration
