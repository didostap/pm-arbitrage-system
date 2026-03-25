# Story 10-9.0: Backtesting & Calibration Design Spike

Status: done

## Story

As the architect,
I want a design document covering data source integration, persistence strategy, and backtest engine architecture,
So that all code stories (10-9-1a through 10-9-6) have validated assumptions and no open architectural questions.

## Context

Epic 10.8 retro defined this story as critical path. Follows the investigation-first pattern validated across three epics (10-0-3, 10-8-0). New external dependencies (OddsPipe, Predexon, PMXT Archive, Goldsky subgraph) each carry API integration risk.

**Motivation:** 0% paper trading profitability across 202 positions (Epic 10.7) revealed unvalidated system parameters. Backtesting was moved from PRD "Outside System Scope" to Phase 1 to provide the empirical foundation the PRD's success criteria demand.

**Scope boundary:** Calibration-focused analysis module. NOT a full replay engine through the live pipeline (ReplayConnector deferred to Phase 2). The module answers parameter calibration questions by analyzing historical price/depth data against parameterized detection + execution cost models.

**Gate:** This document must be reviewed and accepted by Arbi before any code story (10-9-1a through 10-9-6) starts.

## Acceptance Criteria

### AC1: Data Source API Verification

**Given** the data source strategy in the epic description
**When** the design spike is complete
**Then** a design document exists with actual endpoint verification for each source:

1. **Kalshi** — `/candlesticks` (1-min OHLCV), `/historical/trades` (cursor-paginated), `/historical/cutoff` (live/historical partition boundary)
2. **Polymarket** — `/prices-history` (1-min fidelity), Goldsky subgraph (on-chain trade history via GraphQL)
3. **PMXT Archive** — Parquet format L2 orderbook snapshots (hourly)
4. **OddsPipe** — OHLCV candlesticks, cross-platform matched pairs, spread detection
5. **Predexon** — Cross-platform matching pairs, candlesticks, trade history, orderbook history

Each source entry must include: endpoint URL, auth mechanism, rate limits, response schema, data granularity, historical depth, and integration risks/gotchas.

### AC2: Data Persistence Strategy

**Given** the need to store time-series historical data (prices, trades, depth snapshots)
**When** the design spike is complete
**Then** the document specifies:
- Storage approach (PostgreSQL with monthly partitioning, same as architecture doc specifies for OrderBookSnapshot)
- Prisma model definitions for all new tables
- Index strategy for querying by contract, platform, time range
- Batch insert strategy for high-volume ingestion
- Retention/cleanup policy
- Hybrid approach assessment (PostgreSQL vs flat Parquet files for PMXT Archive data)

### AC3: Common Schema Design

**Given** data arrives from 5+ heterogeneous sources with different formats
**When** the design spike is complete
**Then** a normalized common schema exists covering:
- Historical price data (OHLCV candles from Kalshi, Polymarket, OddsPipe, Predexon)
- Historical trade data (individual fills from Kalshi, Polymarket/Goldsky)
- Historical depth data (L2 orderbook snapshots from PMXT Archive, Predexon)
- Source provenance metadata (which source, ingestion timestamp, data quality flags)
- Schema aligns with existing `NormalizedOrderBook` type where applicable

### AC4: Backtest Engine State Machine Architecture

**Given** the backtest engine must iterate chronologically through historical data
**When** the design spike is complete
**Then** the document defines:
- State machine states and transitions (idle, configuring, loading-data, simulating, generating-report, complete, failed, cancelled)
- Parameterized inputs (date range, edge threshold, position sizing %, max concurrent pairs, trading window hours, fee model)
- Detection model integration (how edge calculation reuses `FinancialMath` from `common/utils/financial-math.ts`)
- VWAP fill modeling (conservative taker-only assumptions, partial fills proportional to depth)
- Exit logic evaluation (parameterized exit criteria against subsequent price data)
- Simulated portfolio state tracking (open positions, P&L per position, aggregate P&L, drawdown, capital utilization)
- Resolution-date force-close as distinct exit path
- Known limitations section (single-leg risk not modeled, no market impact, no queue position, depth interpolation between hourly PMXT snapshots)

### AC5: Test Fixture Strategy

**Given** backtesting requires deterministic, reproducible test scenarios
**When** the design spike is complete
**Then** the document specifies:
- Deterministic datasets with known expected outcomes (hand-crafted scenarios where the correct P&L is calculable)
- Fixture format and location (`src/modules/backtesting/__fixtures__/` or similar)
- Edge cases to cover: profitable scenario, unprofitable scenario, breakeven, resolution-date force-close, insufficient depth, coverage gaps
- How to generate fixtures from real data (anonymization/subsetting strategy)

### AC6: Story Sizing Review

**Given** Agreement #25 (sizing gate: >10 tasks or 3+ integration boundaries triggers split)
**When** the design spike is complete
**Then** explicit split assessment exists for:
- Story 10-9-3 (Backtest Simulation Engine Core) — largest P0 story, potentially complex
- Any other stories exceeding sizing thresholds
- Task count estimates per story
- Integration boundary counts per story

### AC7: Minimum Viable Calibration Cut Line

**Given** scope pressure may require descoping
**When** the design spike is complete
**Then** the document identifies which capabilities form the minimum viable calibration:
- Must-have: what subset produces a useful calibration report
- Nice-to-have: what can be deferred without invalidating the calibration analysis
- Dependencies between deferred and retained items

### AC8: Spec File Naming Map

**Given** multiple new modules and services will be created across 10.9 stories
**When** the design spike is complete
**Then** a complete naming map exists:
- Module directory: `src/modules/backtesting/`
- All planned service files with `.service.ts` / `.service.spec.ts` pairs
- DTO directory and files
- New Prisma model names
- New interface names in `common/interfaces/`
- New event class names in `common/events/`
- New error codes in SystemError hierarchy
- API endpoint paths

### AC9: Reviewer Context Template

**Given** Epic 10.9 introduces a new module with external integrations
**When** the design spike is complete
**Then** a reusable reviewer context template exists for Lad MCP `code_review` `context` parameter covering:
- Backtesting module architecture summary
- Key constraints (decimal.js, interface-only imports, error hierarchy, event emission)
- External API integration patterns
- Testing requirements specific to backtesting

### AC10: CLAUDE.md Convention Updates

**Given** CLAUDE.md convention updates pending from Epic 10.8 retro
**When** the design spike document is finalized
**Then** CLAUDE.md is updated with:
- Constructor dependency dual threshold: leaf services <=5, facades <=8 (with mandatory rationale comment for exceptions)
- Line count dual metric: 600 formatted = review trigger, 400 logical = hard gate (documented exceptions require Prettier rationale AND logical count under 400)

### AC11: Gate Review

**Given** this is a gate story
**When** the design document is complete
**Then** it is reviewed and accepted by Arbi before any code story (10-9-1a through 10-9-6) starts

## Tasks / Subtasks

- [x] Task 1: Data Source API Verification (AC: #1)
  - [x] 1.1 Verify Kalshi `/historical/cutoff`, `/candlesticks`, `/historical/trades` — document endpoints, RSA-PSS auth, rate limits (Basic: 20 read/sec), response schemas (dollar strings for prices), cursor pagination
  - [x] 1.2 Verify Polymarket `/prices-history` — document `market` param (token ID, not condition_id), `startTs`/`endTs` vs `interval` mutual exclusivity, rate limit (1,000 req/10s), response format `{history: [{t, p}]}`
  - [x] 1.3 Verify Goldsky subgraph — document GraphQL endpoint, `orderFilledEvent` schema, rate limit (100 req/s per IP), no auth
  - [x] 1.4 Verify PMXT Archive — document file naming (`polymarket_orderbook_YYYY-MM-DDTHH.parquet`), file sizes (150-600MB/hour), `update_type` field (`price_change` vs `book_snapshot`), no auth, intermittent downtime risk
  - [x] 1.5 Verify OddsPipe — document `GET /v1/markets/{id}/candlesticks`, `GET /v1/spreads`, API key via `X-API-Key`, free tier 100 req/min + 30-day history limit, Pro tier not yet available
  - [x] 1.6 Verify Predexon — document `GET /v2/matching-markets/pairs` (Dev+ only, $49/mo), free endpoints (candlesticks, trades, orderbooks), rate limits (free: 1 req/sec, 1,000/month), timestamp inconsistency (seconds vs milliseconds for orderbooks)
  - [x] 1.7 Verify poly_data — document bootstrap snapshot availability, UV package manager requirement, Python-only, 2+ day initial collection without snapshot
  - [x] 1.8 Cost-benefit assessment for paid tiers: Predexon Dev ($49/mo) for matching pairs, OddsPipe Pro ($99/mo, not yet available) for full history — recommend subscribe/defer/skip for each
  - [x] 1.9 Compile integration risk matrix: reliability assessment per source, fallback strategy for unavailable sources

- [x] Task 2: Data Persistence Strategy (AC: #2)
  - [x] 2.1 Define Prisma models: `HistoricalPrice`, `HistoricalTrade`, `HistoricalDepth`, `BacktestRun`, `BacktestPosition`
  - [x] 2.2 Design monthly partition strategy for time-series tables (aligned with existing `OrderBookSnapshot` architecture)
  - [x] 2.3 Define index strategy: composite indexes on (contract_id, platform, timestamp) for range queries
  - [x] 2.4 Define batch insert approach (cursor-based transactions, `createMany` vs raw SQL for volume)
  - [x] 2.5 Assess hybrid storage: Parquet files for PMXT Archive raw data vs PostgreSQL-only
  - [x] 2.6 Define retention policy and cleanup strategy for backtest run records

- [x] Task 3: Common Schema Design (AC: #3)
  - [x] 3.1 Design normalized price schema (OHLCV: open, high, low, close, volume, platform, contractId, interval, timestamp — all Decimal fields)
  - [x] 3.2 Design normalized trade schema (tradeId, platform, contractId, price, size, side, timestamp)
  - [x] 3.3 Design normalized depth schema (aligns with `NormalizedOrderBook` — bids/asks arrays with price/size Decimal pairs)
  - [x] 3.4 Design provenance metadata (sourceId enum, ingestionTimestamp, dataQualityFlags JSON, coverageStart/End)
  - [x] 3.5 Document normalization rules per source (Kalshi dollar strings -> Decimal, Polymarket decimal probability passthrough, PMXT Parquet column mapping)

- [x] Task 4: Backtest Engine State Machine (AC: #4)
  - [x] 4.1 Define state machine: states (idle, configuring, loading-data, simulating, generating-report, complete, failed, cancelled), transitions, guards
  - [x] 4.2 Define parameterized input schema (BacktestConfig DTO): dateRange, edgeThreshold, positionSizePct, maxConcurrentPairs, tradingWindowHours, feeModel, walkForwardSplit
  - [x] 4.3 Document detection model integration — reuses `FinancialMath.calculateGrossEdge`, `calculateNetEdge`, `isAboveThreshold` from `src/common/utils/financial-math.ts`
  - [x] 4.4 Document VWAP fill modeling — reuses `calculateVwapWithFillInfo` from same file; conservative taker-only fills, partial fills proportional to available depth
  - [x] 4.5 Document exit logic — parameterized exit criteria evaluation against subsequent price data, resolution-date force-close as distinct exit path
  - [x] 4.6 Document simulated portfolio tracking: position lifecycle, P&L per position (reuses `calculateLegPnl`), aggregate metrics, drawdown calculation, capital utilization
  - [x] 4.7 Document known limitations section text for inclusion in every calibration report

- [x] Task 5: Test Fixture Strategy (AC: #5)
  - [x] 5.1 Design fixture directory structure (`src/modules/backtesting/__fixtures__/`)
  - [x] 5.2 Define hand-crafted scenarios: profitable 2-leg arb, unprofitable (fees exceed edge), breakeven, resolution force-close, insufficient depth (partial fill), coverage gap handling
  - [x] 5.3 Define fixture format (JSON files with price series, depth snapshots, expected outcomes)
  - [x] 5.4 Document strategy for generating fixtures from real data (date range selection, pair selection, expected outcome calculation)

- [x] Task 6: Story Sizing Review (AC: #6)
  - [x] 6.1 Task count estimate per story (10-9-1a through 10-9-6)
  - [x] 6.2 Integration boundary count per story
  - [x] 6.3 Explicit split assessment for 10-9-3 (Backtest Simulation Engine Core)
  - [x] 6.4 Flag any stories exceeding Agreement #25 thresholds

- [x] Task 7: Minimum Viable Calibration Cut Line (AC: #7)
  - [x] 7.1 Identify must-have capabilities for useful calibration output
  - [x] 7.2 Identify nice-to-have capabilities that can be deferred
  - [x] 7.3 Document dependencies between retained and deferred items

- [x] Task 8: Spec File Naming Map (AC: #8)
  - [x] 8.1 Module directory tree: `src/modules/backtesting/` with all planned files
  - [x] 8.2 New Prisma model names and table mappings
  - [x] 8.3 New interfaces in `common/interfaces/` (e.g., `IHistoricalDataProvider`, `IBacktestEngine`, `ICalibrationReporter`)
  - [x] 8.4 New event classes in `common/events/` (dot-notation: `backtesting.data.ingested`, `backtesting.run.started`, `backtesting.run.completed`, etc.)
  - [x] 8.5 New error codes in SystemError hierarchy (4200-4299 range — 4100-4199 collision with LLM scoring codes avoided)
  - [x] 8.6 API endpoint paths (`/api/backtesting/*`)

- [x] Task 9: Reviewer Context Template (AC: #9)
  - [x] 9.1 Create reusable template for Lad MCP `code_review` `context` parameter
  - [x] 9.2 Include: module architecture summary, key constraints, external API patterns, testing requirements

- [x] Task 10: CLAUDE.md Convention Updates (AC: #10)
  - [x] 10.1 Add constructor dependency dual threshold: leaf services <=5, facades <=8 (mandatory rationale comment for exceptions)
  - [x] 10.2 Add line count dual metric: 600 formatted = review trigger, 400 logical = hard gate (Prettier rationale + logical count under 400 for exceptions)

## Dev Notes

### Output: Design Document

The primary deliverable is a design document file at `_bmad-output/implementation-artifacts/10-9-0-design-doc.md`. Follow the proven template from the 10-8-0 design doc:

**Required sections (mapped from 10-8-0 template):**
1. Data Source API Verification (with response schema tables, rate limit tables, auth details)
2. Data Persistence Strategy (Prisma models, partitioning, indexes, batch strategy)
3. Common Schema Design (normalized types with field tables)
4. Backtest Engine State Machine (state diagram, transition table, parameterized inputs)
5. Test Fixture Strategy (fixture format, scenarios, expected outcomes)
6. Story Sizing Review (task counts, integration boundaries, split assessment)
7. Minimum Viable Calibration (must-have vs nice-to-have table)
8. Spec File Naming Map (complete directory tree)
9. Reviewer Context Template (reusable for all 10.9 code reviews)

Plus: CLAUDE.md edits (Task 10).

**Document conventions (from 10-8-0):**
- Heavy use of Markdown tables for structured data
- Line number references to actual source code where relevant
- Explicit size estimates with compliance status indicators
- ASCII diagrams for state machines and data flows
- Risk assessment tables with likelihood/impact/mitigation columns

### Architecture Constraints

**Module structure:** `src/modules/backtesting/` — new NestJS module following existing patterns.

**Dependency rules (HARD CONSTRAINTS):**
- `modules/backtesting/` -> `common/utils/financial-math.ts` (shared edge, VWAP, fee, P&L calculations)
- `modules/backtesting/` -> `persistence/` (historical data storage, backtest run persistence)
- `modules/backtesting/` -> `common/types/` (`NormalizedOrderBook`, `Opportunity`, branded IDs)
- `modules/backtesting/` -> `common/interfaces/` (consume via interface tokens only)
- `modules/backtesting/` -> `common/errors/`, `common/events/`, `common/constants/`
- FORBIDDEN: Direct imports of other module services, connector imports from backtesting

**Financial math:** ALL calculations use `decimal.js` via `FinancialMath` class and VWAP functions in `src/common/utils/financial-math.ts`. NEVER native JS operators on monetary values. Kalshi prices arrive as dollar strings (e.g., `"0.5600"`), Polymarket as decimal probability (0-1). Both normalize to Decimal internally.

**Existing reusable code (DO NOT REIMPLEMENT):**
- `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` — edge calculation
- `FinancialMath.calculateNetEdge(...)` — fee-adjusted edge with gas
- `FinancialMath.calculateTakerFeeRate(price, feeSchedule)` — platform fee calc
- `calculateVwapWithFillInfo(orderBook, closeSide, positionSize)` — VWAP with fill details
- `calculateVwapClosePrice(orderBook, closeSide, positionSize)` — simpler VWAP
- `calculateLegPnl(side, entryPrice, closePrice, size)` — per-leg P&L
- `FinancialDecimal` — isolated Decimal clone (precision: 20, ROUND_HALF_UP)

All above are in `src/common/utils/financial-math.ts` (well-tested, production-ready, pure functions).

**Error handling:** Extend `SystemError` hierarchy. Allocate codes in 4200-4299 range (`SystemHealthError` subclass) for: ingestion failures, Parquet parse errors, backtest timeout, insufficient data. Note: existing codes 4001-4013 (system health), 4100-4103 (LLM scoring), and 4500 (monitoring) are already taken — avoid collision.

**Event emission:** Every observable state change emits via EventEmitter2. Naming: `backtesting.<noun>.<verb>` (e.g., `backtesting.run.started`, `backtesting.data.ingested`). PascalCase event classes in `common/events/`.

**No God Objects:** Services max ~300 lines, files max ~400 lines, constructor max 5 deps (leaf) / 8 deps (facade). Module providers max ~8.

### Data Source Intelligence (from API verification research)

**Kalshi API** (`https://api.elections.kalshi.com/trade-api/v2`):
- Auth: RSA-PSS signature (3 headers: `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-TIMESTAMP`, `KALSHI-ACCESS-SIGNATURE`)
- `/historical/cutoff` — returns `market_settled_ts`, `trades_created_ts` timestamps. No auth. Routes queries: data before cutoff -> `/historical/*`, after -> live endpoints
- `/historical/markets/{ticker}/candlesticks` — params: `ticker`, `start_ts`, `end_ts` (Unix), `period_interval` (1/60/1440 min). Response: OHLC with bid/ask/volume/OI. **Prices are dollar strings** (e.g., `"0.5600"`)
- `/historical/trades` — cursor-paginated, params: `ticker`, `min_ts`/`max_ts`, `limit` (max 1000). Response: `yes_price_dollars`, `no_price_dollars` as dollar strings
- Rate limits: Basic 20 read/sec, Advanced 30/sec, Premier 100/sec
- **GOTCHA:** Historical data removed from live endpoints as of March 6, 2026. Must route dynamically via cutoff

**Polymarket CLOB API** (`https://clob.polymarket.com`):
- `/prices-history` — no auth. Params: `market` (token ID, NOT condition_id or slug), `startTs`/`endTs` OR `interval` (mutually exclusive), `fidelity` (minutes, default 1). Response: `{history: [{t: unix_seconds, p: decimal_probability}]}`
- Rate limit: 1,000 req/10s for `/prices-history`
- **GOTCHA:** `market` param requires the asset/token ID, not the human-readable slug

**Goldsky Subgraph** (`https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn`):
- GraphQL. No auth. Key entity: `orderFilledEvent` (id, market_id, side, price, size, timestamp)
- Rate limit: 100 req/s per IP
- Open source: https://github.com/Polymarket/polymarket-subgraph

**PMXT Archive** (`https://archive.pmxt.dev/data/`):
- No auth. Direct HTTP download. Parquet files: `polymarket_orderbook_YYYY-MM-DDTHH.parquet`
- File sizes: 150-600MB per hourly snapshot. Contains `update_type`: `price_change` (level updates) and `book_snapshot` (full snapshots)
- **GOTCHA:** Intermittent downtime. Schema undocumented — must inspect Parquet files directly. Only L2 orderbook data (no trades). `book_snapshot` periodicity is irregular
- Node.js SDK: `pmxtjs` (npm)

**OddsPipe** (`https://oddspipe.com/v1`):
- Auth: `X-API-Key` header. Free signup
- `GET /v1/markets/{id}/candlesticks?interval=1m|5m|1h|1d` — OHLCV
- `GET /v1/spreads?min_spread=0.03` — cross-platform divergences
- Free tier: 100 req/min, **30-day history only**. Pro ($99/mo): not yet available
- **FLAG:** 30-day history severely limits backtesting utility. Pro tier "coming soon" — may not be available at implementation time

**Predexon** (`https://api.predexon.com`):
- Auth: `x-api-key` header. Free key at `dashboard.predexon.com`
- Free endpoints (all plans): `GET /v2/polymarket/candlesticks/{condition_id}`, `/trades`, `/orderbooks`, `GET /v2/kalshi/markets`, `/trades`, `/orderbooks`
- Matching endpoints (Dev+ $49/mo): `GET /v2/matching-markets`, `GET /v2/matching-markets/pairs`
- Free: 1 req/sec, 1,000 req/month. Dev: 20 req/sec, 1M req/month
- **GOTCHA:** Matching uses LLM-based technology — small % may be incorrect. Orderbook endpoints use millisecond timestamps while others use seconds. `similarity` field may be `null` for older matches

**poly_data** (github.com/warproxxx/poly_data):
- 646 stars, actively maintained (last commit Feb 2026). Python/UV package manager
- Pre-built snapshot saves 2+ days of initial Goldsky subgraph collection
- Produces structured trade data. Includes example backtesting notebook (backtrader-based)
- **Usage:** Bootstrap Polymarket trade data only. Not a runtime dependency

### Previous Story Intelligence

**10-8-0 Design Doc Template (proven pattern):**
The previous design spike at `_bmad-output/implementation-artifacts/10-8-0-design-doc.md` used this proven structure: numbered sections with heavy Markdown tables, line-number references to source code, explicit size estimates with compliance indicators, pre/post comparison tables, ASCII dependency graphs, and risk assessment matrices (likelihood/impact/mitigation). Follow this template.

**10-8 Epic Learnings:**
- Verbatim extraction pattern (no "while we're here" changes) — applicable to shared math extraction
- 3-layer adversarial code review (Blind Hunter + Edge Case Hunter + Acceptance Auditor) with triage buckets — continue using this for 10.9 reviews
- Test file splits needed explicit describe block mapping — plan spec file structure upfront in naming map
- Module provider count monitoring (some modules already over ~8 limit) — design backtesting module to stay under limit from the start

**Recent Git Commits (pm-arbitrage-engine):**
- All 10.8 stories completed: RiskManager, ExitMonitor, Execution, Dashboard, TelegramFormatter, TelegramCB decompositions
- Consistent pattern: new service + co-located spec, module update, original service slimmed, paper-live boundary spec updated
- Test suite at ~2964 tests, all passing

### Codebase State

**Financial math location:** `src/common/utils/financial-math.ts` — NOT yet extracted to `common/financial-math/` directory. The course correction proposal mentions extraction to `common/financial-math/` as part of the shared math pattern. Design spike should assess whether to extract during 10.9 or use the existing location.

**Existing relevant models:**
- `CalibrationRun` — LLM scoring threshold calibration (precedent for `BacktestRun`)
- `StressTestRun` — Monte Carlo stress test results (precedent for sensitivity analysis persistence)
- `OrderBookSnapshot` — full L2 depth with bids/asks JSON arrays (basis for historical depth schema)
- `ContractMatch` — Polymarket<->Kalshi pair mappings (basis for matching validation)

**Paper connector pattern:** `src/connectors/paper/` shows simulated fills without platform API calls — backtesting can reference this pattern for offline simulation.

**Config system:** 71+ tunable parameters in `EngineConfig` model, accessed via `ConfigAccessor` service. Backtesting can read these for scenario parametrization.

**Dashboard patterns:** 6 controllers with ~10+ endpoints. Standard patterns: DTO wrappers, response envelope (`{data, timestamp}`), WebSocket gateway for real-time events, URL state management. Performance reporting (weekly/daily aggregation) is the closest analogue to backtest reporting.

### Process Conventions

**Active agreements:**
- #24: Retro commitments as deliverables (100% follow-through when items are stories with ACs)
- #25: Story sizing gate (>10 tasks or 3+ integration boundaries -> split)
- #26: Structural guards over review vigilance
- #27: Design spike gate — this story implements it
- #28: Reviewer redundancy (fallback reviewer chain)
- #29: Pre-implementation naming walkthrough — untested, should be embedded as task or dropped per #30
- #30: No standalone soft commitments

**Profitability validation gate:** Arbi must provide profitability data before 10.9 kickoff. Decision fork: positive edge subset -> proceed with calibration; still 0% -> diagnose detection model vs parameters.

**Tech debt monitoring (do NOT address in 10.9 unless touched):**
- ExecutionService 1,024 formatted lines
- ExitMonitorService 914 formatted lines
- ConfigModule extraction (DashboardModule 13 providers, ExecutionModule 15 providers)
- ConfigAccessor inconsistency (7+ services)

### Project Structure Notes

- Design doc output: `_bmad-output/implementation-artifacts/10-9-0-design-doc.md`
- New module: `pm-arbitrage-engine/src/modules/backtesting/`
- Shared math: currently at `src/common/utils/financial-math.ts` — assess extraction to `common/financial-math/` in design doc
- New Prisma models: add to `pm-arbitrage-engine/prisma/schema.prisma`
- CLAUDE.md edits: `pm-arbitrage-engine/../../CLAUDE.md` (root repo) — convention updates

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 10.9, lines 3452-3654] — Epic definition and all story ACs
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-25-backtesting-calibration.md] — Course correction with full rationale, data source research, scope decisions
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-25-retro-chain-analysis.md] — Post-retro chain analysis, outstanding items, agreements status
- [Source: _bmad-output/planning-artifacts/architecture.md#Calibration Path, lines 665-682] — Architecture data flow for backtesting
- [Source: _bmad-output/planning-artifacts/architecture.md#Module Dependencies, lines 607-621] — Allowed/forbidden imports
- [Source: _bmad-output/implementation-artifacts/10-8-0-design-doc.md] — Previous design spike template (proven structure)
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts] — Shared financial math functions (DO NOT reimplement)
- [Source: pm-arbitrage-engine/prisma/schema.prisma] — Existing Prisma models (CalibrationRun, StressTestRun, OrderBookSnapshot, ContractMatch)
- [Source: CLAUDE.md#Architecture, #Testing, #Error Handling, #Event Emission] — All architectural constraints

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- API verification performed via kindly-web-search (Kalshi, Polymarket, Goldsky, PMXT, OddsPipe, Predexon, poly_data)
- Codebase exploration via Serena + parallel search agents for financial-math.ts, Prisma schema, error codes, event catalog, interfaces, types
- Error code collision discovered: story proposed 4100-4199 but 4100-4103 allocated to LLM scoring → resolved to 4200-4299
- Polymarket API correction: startTs/endTs and interval are NOT mutually exclusive (story notes assumed they were)
- Kalshi historical cutoff has 3 fields (not 2): added orders_updated_ts
- Goldsky OrderFilledEvent does NOT have side/price/blockNumber fields — must derive from amounts and asset IDs
- PMXT file sizes wider range than expected: 150-605 MB/hour (not 150-600)

### Completion Notes List

- Task 1: All 7 data sources verified via web research. Endpoints, auth, rate limits, response schemas, gotchas documented. Cost-benefit: subscribe Predexon Dev ($49/mo), skip OddsPipe Pro (not available). Risk matrix compiled with reliability ratings and fallback strategies.
- Task 2: 5 Prisma models defined (HistoricalPrice, HistoricalTrade, HistoricalDepth, BacktestRun, BacktestPosition) + 3 enums. Monthly partitioning for time-series. Hybrid storage (PostgreSQL + raw Parquet). Batch insert via createMany + raw SQL fallback. Retention policy defined.
- Task 3: Normalized schemas for price (OHLCV), trade, and depth. Provenance metadata with DataQualityFlags. Normalization rules per source (Kalshi dollar strings, Polymarket passthrough, Goldsky derivation, Predexon dual timestamps).
- Task 4: 8-state machine with transition table and guards. BacktestConfigDto with 16 parameters. Detection reuses FinancialMath.*. VWAP via calculateVwapWithFillInfo (taker-only). 5 exit criteria. Portfolio state tracking with drawdown. 8 known limitations documented verbatim.
- Task 5: Fixture directory with scenarios/, price-series/, depth-snapshots/, trades/ subdirs. 6 hand-crafted scenarios with expected outcomes. JSON fixture format defined. Real data generation strategy documented.
- Task 6: Story 10-9-3 exceeds Agreement #25 (12 tasks, 3+ boundaries). Split recommended: 10-9-3a (state machine + data loading, ~7 tasks) and 10-9-3b (simulation + portfolio, ~7 tasks). All other stories within limits.
- Task 7: Must-have: platform API ingestion + one depth source + engine + basic report. Nice-to-have: walk-forward, sensitivity, matching validation, dashboard, incremental updates. No cross-dependencies between deferred items.
- Task 8: Full module tree with sub-modules (ingestion/, engine/, reporting/). 5 Prisma models, 3 interfaces, 9 events, 8 error codes (4200-4299), 7 API endpoints. Provider counts within limits (4 + 6 across modules).
- Task 9: Reusable reviewer context template covering architecture, hard constraints, external API patterns, testing requirements.
- Task 10: CLAUDE.md updated — constructor dep dual threshold (leaf <=5, facade <=8 with mandatory rationale) and line count dual metric (600 formatted trigger, 400 logical gate).

### Change Log

- 2026-03-26: Story 10-9-0 implemented. Design document created at `_bmad-output/implementation-artifacts/10-9-0-design-doc.md`. CLAUDE.md updated with constructor dep dual threshold and line count dual metric conventions.

### File List

- `_bmad-output/implementation-artifacts/10-9-0-design-doc.md` (NEW — primary design document)
- `CLAUDE.md` (MODIFIED — Task 10 convention updates: constructor dep dual threshold, line count dual metric)
- `_bmad-output/implementation-artifacts/10-9-0-backtesting-design-spike.md` (MODIFIED — task checkboxes, dev agent record)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (MODIFIED — story status ready-for-dev → in-progress)
