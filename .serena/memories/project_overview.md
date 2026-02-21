# Project Overview

**Project Name:** PM Arbitrage System
**Purpose:** Institutional-grade automated trading engine exploiting cross-platform arbitrage in prediction markets (Polymarket ↔ Kalshi).

**Stack:** NestJS 11 + Fastify + Prisma 6 + PostgreSQL 16+ + TypeScript strict mode

**Working Directory:** All development work happens in `pm-arbitrage-engine/` subdirectory, which is an **independent nested git repository** (NOT tracked by the main repo). Changes require separate commits.

**Root Directory:** Contains CLAUDE.md instructions, `_bmad-output/` artifacts, `_bmad/` config. `docs/` directory exists but is currently empty.

**Primary Entry Point:** `pm-arbitrage-engine/src/main.ts`

**Key Capabilities (implemented as of Sprint 5):**
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

**Codebase Size:** ~102 source files, ~49 test spec files
