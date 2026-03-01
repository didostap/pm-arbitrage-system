# Project Overview

**Project Name:** PM Arbitrage System
**Purpose:** Institutional-grade automated trading engine exploiting cross-platform arbitrage in prediction markets (Polymarket ↔ Kalshi).

**Stack:** NestJS 11 + Fastify + Prisma 6 + PostgreSQL 16+ + TypeScript strict mode

**Working Directory:** All development work happens in `pm-arbitrage-engine/` subdirectory, which is an **independent nested git repository** (NOT tracked by the main repo). Changes require separate commits.

**Root Directory:** Contains CLAUDE.md instructions, `_bmad-output/` artifacts, `_bmad/` config. `docs/` directory exists but is currently empty.

**Primary Entry Point:** `pm-arbitrage-engine/src/main.ts`

**Key Capabilities (implemented as of Epic 7.1):**
- Real-time WebSocket order book ingestion from Kalshi + Polymarket
- Platform health monitoring with degradation protocol
- Cross-platform arbitrage dislocation detection
- Net edge calculation with fee/gas awareness
- Risk management with position sizing, budget reservation, and daily loss limits
- Two-leg execution with single-leg exposure handling
- Position exit monitoring with threshold evaluation
- Startup reconciliation with platform state verification
- Operator risk override API with audit trail
- Contract pair management via YAML config + DB sync
- Monitoring: Telegram alerts, CSV trade logs, compliance checks, trade/tax exports
- Paper trading infrastructure (simulated execution, mode isolation)
- **Operator Dashboard** (React 19 + Vite + TanStack Query + shadcn/ui):
  - System health view (composite health, per-platform status, P&L, execution quality)
  - WebSocket gateway for real-time push updates
  - Typed API client generated from OpenAPI spec (swagger-typescript-api)
  - Docker Compose integration (nginx serving SPA with API/WS proxy)

**Codebase Size:** ~120+ source files, ~55+ test spec files (1170 tests), plus pm-arbitrage-dashboard SPA
