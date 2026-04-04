---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
---

# pm-arbitrage-system - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for pm-arbitrage-system, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Data Ingestion Module:**
- FR-DI-01 [MVP]: Real-time connections to Polymarket and Kalshi with auto-reconnection (max 60s exponential backoff)
- FR-DI-02 [MVP]: Normalize heterogeneous platform data into unified order book within 500ms (95th percentile)
- FR-DI-03 [MVP]: Detect platform API degradation within 81s of websocket timeout, transition to polling
- FR-DI-04 [MVP]: Publish platform health status every 30s (healthy/degraded/offline)
- FR-DI-05 [Phase 1]: Support adding new platform connectors without modifying core modules

**Arbitrage Detection Module:**
- FR-AD-01 [MVP]: Identify cross-platform arbitrage opportunities, full detection cycle within 1 second
- FR-AD-02 [MVP]: Calculate expected edge accounting for fees, gas, liquidity depth
- FR-AD-03 [MVP]: Filter opportunities below minimum edge threshold (default 0.8% net)
- FR-AD-04 [MVP]: Operator can manually approve contract matches with confidence <85%
- FR-AD-05 [Phase 1]: Score contract matching confidence (0-100%) using semantic analysis
- FR-AD-06 [Phase 1]: Auto-approve matches ≥85%, queue <85% for operator review
- FR-AD-07 [Phase 1]: Accumulate contract matching knowledge base from resolved matches

**Execution Module:**
- FR-EX-01 [MVP]: Coordinate near-simultaneous order submission (<100ms between legs)
- FR-EX-02 [MVP]: Execute more liquid leg first, then immediately execute second leg
- FR-EX-03 [MVP]: Verify order book depth before placing any order
- FR-EX-04 [MVP]: Detect single-leg exposure within 5 seconds
- FR-EX-05 [MVP]: Alert operator immediately with full context on single-leg exposure
- FR-EX-06 [MVP]: Operator can retry failed leg or close filled leg via dashboard
- FR-EX-07 [Phase 1]: Auto-close/hedge first leg if second fails within timeout (5s default)
- FR-EX-08 [Phase 1]: Adapt leg sequencing based on venue-specific latency profiles

**Risk Management Module:**
- FR-RM-01 [MVP]: Enforce 3% bankroll per pair position sizing limit
- FR-RM-02 [MVP]: Enforce max 10 simultaneous open pairs (MVP), 25 (Phase 1)
- FR-RM-03 [MVP]: Halt trading at 5% daily loss limit with high-priority alert
- FR-RM-04 [MVP]: Operator can override position limits with explicit confirmation
- FR-RM-05 [Phase 1]: Calculate correlation exposure by event category
- FR-RM-06 [Phase 1]: Enforce 15% bankroll correlation cluster limit
- FR-RM-07 [Phase 1]: Auto-prevent new positions breaching correlation limits with triage recommendations
- FR-RM-08 [Phase 1]: Adjust position sizing by contract matching confidence score
- FR-RM-09 [Phase 1]: Monte Carlo stress testing against historical/synthetic scenarios

**Monitoring & Alerting Module:**
- FR-MA-01 [MVP]: Telegram alerts for all critical events within 2 seconds
- FR-MA-02 [MVP]: Log all trades to timestamped CSV with 7-year retention
- FR-MA-03 [MVP]: Daily summary of health, P&L, positions, alerts via CSV
- FR-MA-04 [Phase 1]: Web dashboard with 2-minute morning scan view
- FR-MA-05 [Phase 1]: Contract matching approval interface with side-by-side comparison
- FR-MA-06 [Phase 1]: Log all manual operator decisions with rationale for audit trail
- FR-MA-07 [Phase 1]: Automated quarterly compliance reports
- FR-MA-08 [Phase 1]: Export audit trails in CSV for legal review
- FR-MA-09 [Phase 1]: Weekly performance metrics (autonomy ratio, slippage, opportunity frequency)

**Exit Management:**
- FR-EM-01 [MVP]: Fixed threshold exits (80% edge take-profit, 2x edge stop-loss, 48h pre-resolution)
- FR-EM-02 [Phase 1]: Continuous edge recalculation for open positions
- FR-EM-03 [Phase 1]: Five-criteria model-driven exit logic

**Contract Matching & Knowledge Base:**
- FR-CM-01 [MVP]: Manual curation of 20-30 contract pairs in config file
- FR-CM-02 [Phase 1]: Semantic matching of contract descriptions and resolution criteria
- FR-CM-03 [Phase 1]: Store validated matches in knowledge base with confidence scores and outcomes
- FR-CM-04 [Phase 1]: Use resolution outcomes as feedback to improve confidence scoring

**Platform Integration & Compliance:**
- FR-PI-01 [MVP]: Kalshi API key-based authentication
- FR-PI-02 [MVP]: Polymarket wallet-based authentication (private key signing)
- FR-PI-03 [MVP]: Enforce platform rate limits with 20% safety buffer
- FR-PI-04 [MVP]: Track rate limit utilization, alert at 70%
- FR-PI-05 [MVP]: Validate trades against compliance matrix before execution
- FR-PI-06 [Phase 1]: Retrieve credentials from external secrets management at startup
- FR-PI-07 [Phase 1]: Zero-downtime API key rotation (<5s degraded)

**Data Export & Reporting:**
- FR-DE-01 [MVP]: Export trade logs in JSON with CSV capability
- FR-DE-02 [MVP]: Annual tax report CSV with P&L by platform/quarter
- FR-DE-03 [Phase 1]: Quarterly compliance reports in PDF
- FR-DE-04 [Phase 1]: On-demand audit trail export for any period within 7-year window

### NonFunctional Requirements

**Performance:**
- NFR-P1: Order book normalization within 500ms of platform event (95th percentile)
- NFR-P2: Full detection cycle within 1 second
- NFR-P3: Both legs submitted <100ms apart (same event loop cycle)
- NFR-P4: Dashboard updates within 2 seconds of data change

**Security:**
- NFR-S1: Credentials in env vars (MVP), secrets manager (Phase 1); zero exposure events
- NFR-S2: Zero-downtime API key rotation, <5s degraded operation
- NFR-S3: Complete audit trail for all trades, 7-year retention, tamper-evident
- NFR-S4: Authenticated access to dashboard/API; no unauthenticated access

**Reliability:**
- NFR-R1: 99% uptime during market hours (Mon-Fri 9am-5pm ET), 95% overall
- NFR-R2: Graceful degradation per-platform (cancel pending, continue healthy platforms, widen thresholds 1.5x)
- NFR-R3: 5s single-leg exposure timeout; <5 events/month target, <2/month compliance
- NFR-R4: Platform health updated every 30s; degradation alert within 60s
- NFR-R5: All snapshots/executions logged with microsecond timestamps, 7-year retention

**Integration:**
- NFR-I1: Defensive API parsing; handle unexpected responses without crashing
- NFR-I2: Rate limit enforcement with 20% buffer; alert at 70% utilization
- NFR-I3: Auto-reconnecting WebSockets (exponential backoff, max 60s)
- NFR-I4: On-chain transaction confirmation with 30s timeout, chain reorg handling, gas estimation +20% buffer

### Additional Requirements

**From Architecture:**
- Starter template: NestJS CLI (`nest new`) with Fastify adapter, Prisma 6, viem, Vitest — first implementation story
- PostgreSQL 16+ (replaces PRD's SQLite suggestion) for audit trail, correlation analytics, 7-year retention
- Docker Compose 3-service architecture (postgres, engine, dashboard/nginx)
- In-memory caching only (no Redis); ephemeral state rebuilt from APIs on restart
- Hybrid communication: synchronous DI for hot path, EventEmitter2 for observability fan-out
- IPlatformConnector unified interface for all platform connectors
- Centralized typed error hierarchy (SystemError → PlatformApiError, ExecutionError, RiskLimitError, SystemHealthError)
- Global exception filter routing by severity (Critical → Telegram+audit+halt, Warning → dashboard+log, Info → log)
- Structured JSON logging via Pino with correlationId per execution cycle
- Standardized retry utility (`withRetry`) with exponential backoff
- Blue/green deployment via manual bash script with 5-minute observation window
- External health monitoring (Healthchecks.io/UptimeRobot) hitting `/api/health` every 60s
- Hourly pg_dump backups to Hetzner Object Storage, weekly automated restore test
- Dashboard: separate React SPA repo, Vite build, React Query + WebSocket context, shadcn/ui
- API documentation via @nestjs/swagger as single source of truth
- Static Bearer token auth for MVP dashboard
- Localhost-only binding (127.0.0.1:8080) with SSH tunnel access

**From PRD (additional technical):**
- Sequential execution locking with atomic risk budget reservation for concurrent opportunities
- Startup reconciliation against platform APIs to detect orphan fills after crash
- NTP synchronization at startup and every 6 hours (<100ms drift tolerance)
- Clock drift monitoring every 30 minutes with escalating alerts
- Alerting fallback chain: Telegram → Email → SMS with daily test alerts
- Opportunity frequency baseline tracking (8-12/week) with edge degradation detection
- Correlation cluster management (Fed Policy, Elections, Economic Indicators, Geographic Events, Uncategorized)
- Contract matching knowledge base with feedback loop for confidence scoring
- Price normalization: all internal calculations in decimal probability (0.00-1.00)
- Error code catalog: 1000-1999 (Platform API), 2000-2999 (Execution), 3000-3999 (Risk), 4000-4999 (System Health)

### FR Coverage Map

FR-DI-01: Epic 1 (Kalshi), Epic 2 (Polymarket) - Real-time platform connections
FR-DI-02: Epic 1 (Kalshi), Epic 2 (Polymarket + cross-platform) - Order book normalization
FR-DI-03: Epic 2 - Platform API degradation detection and polling fallback
FR-DI-04: Epic 1 - Platform health status publishing
FR-DI-05: Epic 11 - New platform connector support
FR-AD-01: Epic 3 - Cross-platform arbitrage detection
FR-AD-02: Epic 3 - Edge calculation (fees, gas, liquidity)
FR-AD-03: Epic 3 - Minimum edge threshold filtering
FR-AD-04: Epic 3 - Manual contract match approval
FR-AD-05: Epic 8 - NLP confidence scoring
FR-AD-06: Epic 8 - Auto-approve/queue by confidence
FR-AD-07: Epic 8 - Knowledge base accumulation
FR-AD-08: Epic 9 - Resolution date gating & annualized return threshold
FR-EX-01: Epic 5 - Near-simultaneous leg submission
FR-EX-02: Epic 5 - Liquid leg first execution
FR-EX-03: Epic 5 - Order book depth verification
FR-EX-04: Epic 5 - Single-leg exposure detection
FR-EX-05: Epic 5 - Single-leg exposure alerting
FR-EX-06: Epic 5 - Operator retry/close for single-leg
FR-EX-07: Epic 10 - Auto-close/hedge on second leg failure
FR-EX-08: Epic 10 - Adaptive leg sequencing
FR-RM-01: Epic 4 - Position sizing limit (3% per pair)
FR-RM-02: Epic 4 - Portfolio limit (10 MVP / 25 Phase 1)
FR-RM-03: Epic 4 - Daily loss limit halt (5%)
FR-RM-04: Epic 4 - Operator override with confirmation
FR-RM-05: Epic 9 - Correlation exposure calculation
FR-RM-06: Epic 9 - Correlation cluster limit (15%)
FR-RM-07: Epic 9 - Auto-prevent correlation breaches
FR-RM-08: Epic 9 - Confidence-adjusted position sizing
FR-RM-09: Epic 9 - Monte Carlo stress testing
FR-MA-01: Epic 6 - Telegram alerts (<2s)
FR-MA-02: Epic 6 - CSV trade logging (7-year retention)
FR-MA-03: Epic 6 - Daily summary via CSV
FR-MA-04: Epic 7 - Web dashboard morning scan
FR-MA-05: Epic 7 - Contract matching approval interface
FR-MA-06: Epic 7 - Manual decision logging
FR-MA-07: Epic 12 - Quarterly compliance reports
FR-MA-08: Epic 12 - Audit trail CSV export
FR-MA-09: Epic 7 - Weekly performance metrics
FR-EM-01: Epic 5 - Fixed threshold exits
FR-EM-02: Epic 10 - Continuous edge recalculation
FR-EM-03: Epic 10 - Five-criteria model-driven exits
FR-CM-01: Epic 3 - Manual contract pair curation
FR-CM-02: Epic 8 - Semantic contract matching
FR-CM-03: Epic 8 - Knowledge base storage
FR-CM-04: Epic 8 - Resolution outcome feedback loop
FR-EX-09: Epic 10.7 - Per-pair position cooldown and concentration limits
FR-CM-05: Epic 8 - Automated cross-platform candidate discovery
FR-PI-01: Epic 1 - Kalshi API authentication
FR-PI-02: Epic 2 - Polymarket wallet authentication
FR-PI-03: Epic 1 - Rate limit enforcement (20% buffer)
FR-PI-04: Epic 1 - Rate limit utilization tracking
FR-PI-05: Epic 6 - Compliance matrix validation
FR-PI-06: Epic 11 - External secrets management
FR-PI-07: Epic 11 - Zero-downtime key rotation
FR-DE-01: Epic 6 - Trade log export (JSON/CSV)
FR-DE-02: Epic 6 - Annual tax report CSV
FR-DE-03: Epic 12 - Quarterly compliance reports (PDF)
FR-DE-04: Epic 12 - On-demand audit trail export

## Epic List

### Epic 1: Project Foundation, Core Infrastructure & Kalshi Connectivity
Operator can deploy the system, connect to Kalshi, and verify real-time normalized data flows. Includes project scaffold (NestJS + Fastify + Prisma + Docker + PostgreSQL), NTP synchronization, and the core engine lifecycle.
**FRs covered:** FR-DI-01 (Kalshi), FR-DI-02 (Kalshi normalization), FR-DI-04, FR-PI-01, FR-PI-03, FR-PI-04
**Additional:** Starter template, Prisma schema, Docker Compose, NTP sync, engine lifecycle, graceful shutdown

## Epic 1: Project Foundation, Core Infrastructure & Kalshi Connectivity

Operator can deploy the system, connect to Kalshi, and verify real-time normalized data flows.

### Story 1.1: Project Scaffold & Development Environment

As an operator,
I want a deployable NestJS project with Docker Compose (PostgreSQL + engine),
So that I have a working development and deployment foundation.

**Acceptance Criteria:**

**Given** the repository is cloned and dependencies installed
**When** I run `docker-compose up`
**Then** PostgreSQL starts and the NestJS engine connects to it
**And** `GET /api/health` returns 200 with `{ data: { status: "ok" }, timestamp: "<ISO8601>" }`

**Given** a pull request is opened
**When** CI pipeline runs
**Then** lint, test, and build all pass
**And** Vitest runs with unplugin-swc for decorator metadata support

**Given** the project is scaffolded
**When** I inspect the directory structure
**Then** it matches the architecture's module organization (`src/modules/`, `src/connectors/`, `src/common/`, `src/core/`)
**And** Prisma is initialized with an empty schema ready for migrations
**And** environment variables are loaded via `@nestjs/config` from `.env.development`

### Story 1.2: Core Engine Lifecycle & Graceful Shutdown

As an operator,
I want the trading engine to start up cleanly, run a continuous polling loop, and shut down gracefully,
So that I can deploy and restart the system safely without data loss.

**Acceptance Criteria:**

**Given** the engine process starts
**When** initialization completes
**Then** the trading engine service begins the main polling loop at configured intervals
**And** engine lifecycle service registers startup and shutdown hooks
**And** a startup log entry is written with timestamp and configuration summary

**Given** the engine receives SIGTERM/SIGINT
**When** graceful shutdown initiates
**Then** the polling loop stops accepting new cycles
**And** any in-flight operations complete before process exit
**And** all database connections are closed cleanly
**And** a shutdown log entry is written with timestamp

**Given** the scheduler service is running
**When** polling interval elapses
**Then** the next cycle triggers (detection → risk → execution pipeline placeholder)
**And** cycle timing is logged for performance monitoring

### Story 1.3: Kalshi Platform Connector & Authentication

As an operator,
I want to connect to Kalshi's API with authenticated access and see raw order book data,
So that I can verify platform connectivity works before building detection logic.

**Acceptance Criteria:**

**Given** Kalshi API credentials are configured in environment variables
**When** the engine starts
**Then** the Kalshi connector authenticates via API key (FR-PI-01)
**And** establishes a WebSocket connection for real-time data
**And** connection status is logged

**Given** the Kalshi WebSocket disconnects
**When** reconnection triggers
**Then** exponential backoff is applied (1s, 2s, 4s... max 60s)
**And** reconnection attempts are logged with attempt count

**Given** the connector is making API requests
**When** rate limit utilization reaches 70% of published limits
**Then** an alert-level log is emitted (FR-PI-04)
**And** request queueing activates to enforce 20% safety buffer (FR-PI-03)

**Given** a Kalshi API call fails
**When** the error matches a known error code (1001-1007)
**Then** the appropriate `PlatformApiError` is thrown with severity and retry strategy
**And** retryable errors use `withRetry()` with exponential backoff
**And** non-retryable errors (1001 Unauthorized, 1007 Schema Change) are escalated immediately

**Given** the `IPlatformConnector` interface is defined in `common/interfaces/`
**When** the Kalshi connector is implemented
**Then** it implements all interface methods (`submitOrder`, `cancelOrder`, `getOrderBook`, `getPositions`, `getHealth`, `getPlatformId`, `getFeeSchedule`, `connect`, `disconnect`, `onOrderBookUpdate`)
**And** the `SystemError` base class and `PlatformApiError` subclass exist in `common/errors/`
**And** the `withRetry()` utility exists in `common/utils/`

### Story 1.4: Order Book Normalization & Health Monitoring

As an operator,
I want Kalshi order book data normalized into the unified internal format with platform health status,
So that I can verify data quality and system health before adding more platforms.

**Acceptance Criteria:**

**Given** Kalshi sends an order book update
**When** the normalizer processes it
**Then** Kalshi cents are converted to decimal probability (62¢ → 0.62)
**And** the normalized output matches the PRD's `NormalizedOrderBook` schema (platform, contract_id, best_bid, best_ask, fees, timestamp, platform_health)
**And** normalization completes within 500ms (95th percentile) (FR-DI-02)

**Given** a normalized price is produced
**When** validation runs
**Then** prices outside 0.00-1.00 range are rejected, logged as error, and the opportunity is discarded

**Given** the platform health service is running
**When** 30 seconds elapse
**Then** health status is published (healthy/degraded/offline) based on API response time, update frequency, and connection state (FR-DI-04)

**Given** no order book update is received for >60 seconds
**When** data staleness is detected
**Then** platform status transitions to "degraded"
**And** a warning-level event is emitted

**Given** the engine needs to persist snapshots
**When** order book data arrives
**Then** snapshots are written to `order_book_snapshots` table (Prisma migration created in this story)
**And** health status is written to `platform_health_logs` table

### Story 1.5: Structured Logging, Correlation Tracking & Event Infrastructure

As an operator,
I want structured JSON logs with correlation IDs and a working event bus for domain events,
So that I can trace system behavior end-to-end and future modules can subscribe to events.

**Acceptance Criteria:**

**Given** any module emits a log entry
**When** the log is written
**Then** it includes `timestamp`, `level`, `module`, `correlationId`, `message`, and `data` fields
**And** format is structured JSON via Pino

**Given** a polling cycle begins
**When** a new correlation ID is generated
**Then** all log entries within that cycle share the same `correlationId`
**And** the correlation ID interceptor propagates it through the request context

**Given** the `@nestjs/event-emitter` package is installed and configured
**When** the EventEmitter2 module is registered in `app.module.ts`
**Then** any module can emit and subscribe to typed domain events

**Given** base event classes exist in `common/events/`
**When** a domain event is emitted (e.g., `platform.health.degraded`)
**Then** it follows dot-notation naming convention
**And** the event class uses PascalCase (e.g., `PlatformDegradedEvent`, `PlatformRecoveredEvent`)
**And** each event class includes `timestamp`, `correlationId`, and event-specific payload

### Story 1.6: NTP Synchronization & Time Management

As an operator,
I want the system clock synchronized with NTP servers and monitored for drift,
So that all timestamps are audit-quality and cross-platform timing is reliable.

**Acceptance Criteria:**

**Given** the engine starts
**When** NTP sync runs
**Then** system clock is validated against pool.ntp.org
**And** sync result is logged (drift amount, NTP server used)

**Given** the scheduler triggers NTP check (every 6 hours)
**When** clock drift is measured
**Then** drift <100ms: no action
**And** drift 100-500ms: warning alert to operator
**And** drift 500ms-1000ms: critical alert
**And** drift >1000ms: halt trading until resolved

### Epic 2: Polymarket Connectivity & Cross-Platform Data
Operator can see live normalized order books from both platforms side by side, with health monitoring, degradation detection, and automatic recovery. Cross-platform data foundation is complete.
**FRs covered:** FR-DI-01 (Polymarket), FR-DI-02 (Polymarket + cross-platform), FR-DI-03, FR-PI-02
**Additional:** Wallet-based auth via @polymarket/clob-client SDK, WebSocket management, price normalization
**Epic 2 Implementation Note:** Polymarket orders are off-chain (CLOB REST API via SDK), not on-chain Polygon transactions. On-chain interactions (deposits, withdrawals, settlement) deferred to Epic 5. SDK handles auth internally — IAuthProvider abstraction unnecessary.

## Epic 2: Polymarket Connectivity & Cross-Platform Data

Operator can see live normalized order books from both platforms side by side, with health monitoring, degradation detection, and automatic recovery.

### Story 2.1: Polymarket Connector & Wallet Authentication

As an operator,
I want to connect to Polymarket with wallet-based authentication,
So that I can access Polymarket's order book and trading API.

**Acceptance Criteria:**

**Given** `POLYMARKET_PRIVATE_KEY` is configured in environment variables
**When** the engine starts
**Then** the @polymarket/clob-client SDK derives API keys from the private key (FR-PI-02)
**And** the Polymarket connector authenticates via the SDK's built-in wallet signing

> **Implementation Note (Epic 2 Retro):** Original plan specified AES-256 encrypted keystore; actual implementation uses direct private key in env vars with SDK-managed auth. Encrypted keystore deferred to Epic 11 (security hardening).

**Given** the Polymarket connector is initialized
**When** it connects to Polymarket's APIs
**Then** CLOB REST API client retrieves order book data via @polymarket/clob-client SDK
**And** WebSocket connection is established for real-time updates
**And** connection status is logged with platform ID

**Given** the Polymarket WebSocket disconnects
**When** reconnection triggers
**Then** exponential backoff is applied (1s, 2s, 4s... max 60s) reusing the pattern from Epic 1
**And** reconnection attempts are logged

**Given** the Polymarket connector is implemented
**When** I inspect the code
**Then** it implements the `IPlatformConnector` interface from `common/interfaces/`
**And** order submission uses the off-chain CLOB API via @polymarket/clob-client (synchronous REST confirmation, same pattern as Kalshi)
**And** rate limit enforcement reuses `withRetry()` and `PlatformApiError` from Epic 1

> **Implementation Note (Epic 2 Retro):** Original plan specified on-chain transaction handling via viem with gas estimation and chain reorg detection (NFR-I4). Actual implementation: Polymarket orders are off-chain CLOB (REST API via SDK). On-chain concerns (gas estimation, transaction confirmation, chain reorg handling) apply only to deposits/withdrawals/settlement — deferred to Epic 5.

### Story 2.2: Polymarket Order Book Normalization

As an operator,
I want Polymarket data normalized into the same unified format as Kalshi,
So that cross-platform comparison is possible using a single data structure.

**Acceptance Criteria:**

**Given** Polymarket sends order book data
**When** the normalizer processes it
**Then** the output matches the `NormalizedOrderBook` schema (same type as Kalshi output)
**And** Polymarket's decimal probability format is preserved (already 0.00-1.00)
**And** fee structure is normalized: taker fee as decimal (gas estimate excluded from normalization — handled at edge calculation time)
**And** normalization completes within 500ms (95th percentile) (FR-DI-02)

> **Implementation Note (Epic 2 Retro):** Polymarket prices already decimal (0.00-1.00), ~50x faster normalization than Kalshi. Gas estimate not included in normalized fee structure — it's a static conservative estimate ($0.10-0.50) applied during edge calculation (Story 3.3). Dynamic gas estimation deferred to Epic 5.

**Given** a normalized Polymarket price is produced
**When** validation runs
**Then** prices outside 0.00-1.00 range are rejected, logged as error, and discarded
**And** NaN and null values are caught by defensive validation (NaN guard pattern established in Epic 2)

**Given** Polymarket snapshots are produced
**When** persistence runs
**Then** snapshots are written to the existing `order_book_snapshots` table (same table as Kalshi, differentiated by `platform` column)

### Story 2.3: Cross-Platform Data Aggregation & Health Dashboard

As an operator,
I want to see aggregated order books from both platforms with unified health status,
So that I can verify the complete data foundation before building detection logic.

**Acceptance Criteria:**

**Given** both Kalshi and Polymarket connectors are running
**When** the data ingestion service orchestrates a polling cycle
**Then** normalized order books from both platforms are available to downstream modules
**And** each contract pair's data includes both platforms' pricing for the same event

**Given** both platforms are publishing health status
**When** the health service aggregates
**Then** a unified health view is available showing per-platform status (healthy/degraded/offline)
**And** platform health events are emitted via EventEmitter2 (`platform.health.degraded`, `platform.health.recovered`)
**And** health status is persisted to `platform_health_logs` table with both platforms

**Given** one platform is degraded and the other is healthy
**When** health is queried
**Then** the system reports partial health (one green, one yellow/red)
**And** downstream modules can query per-platform health independently

### Story 2.4: Graceful Degradation & Automatic Recovery

As an operator,
I want the system to detect platform outages, manage degradation state, and recover automatically,
So that one platform failing doesn't compromise the system's ability to operate on healthy platforms.

**Acceptance Criteria:**

**Given** a platform's WebSocket has not sent data
**When** 81 seconds elapse (WebSocket timeout threshold)
**Then** the platform is marked as "degraded" (FR-DI-03)
**And** the system transitions to polling mode for that platform
**And** a high-priority `PlatformDegradedEvent` is emitted with platform ID, last data timestamp, and degradation reason

**Given** a platform is in degraded state
**When** the degradation protocol activates
**Then** the platform's health status is set to "degraded" and exposed to all downstream modules
**And** a `degradation.protocol.activated` event is emitted that downstream modules (execution, when it exists) will subscribe to for cancelling pending orders and halting new trades
**And** opportunity thresholds are widened by 1.5x on remaining healthy platforms (NFR-R2)

**Given** a degraded platform's WebSocket reconnects
**When** data flow resumes
**Then** the system validates data freshness (timestamp within 30 seconds)
**And** platform status transitions back to "healthy"
**And** a `PlatformRecoveredEvent` is emitted
**And** opportunity thresholds return to normal
**And** recovery is logged with outage duration and impact summary

**Given** a platform is degraded
**When** polling mode is active
**Then** the system continues fetching order book data via REST at 30-second intervals
**And** existing data from that platform is marked with `platform_health: "degraded"` in normalized output

### Epic 3: Arbitrage Detection & Contract Matching
Operator can see identified arbitrage opportunities with calculated edge using manually curated contract pairs, and verify the detection logic finds real dislocations.
**FRs covered:** FR-AD-01, FR-AD-02, FR-AD-03, FR-AD-04, FR-CM-01

## Epic 3: Arbitrage Detection & Contract Matching

Operator can see identified arbitrage opportunities with calculated edge using manually curated contract pairs, and verify the detection logic finds real dislocations.

### Story 3.1: Manual Contract Pair Configuration

As an operator,
I want to curate and manage a list of verified cross-platform contract pairs in a config file,
So that the system knows which Polymarket and Kalshi contracts represent the same event.

**Acceptance Criteria:**

**Given** a JSON/YAML config file exists with contract pair definitions
**When** the engine loads configuration at startup
**Then** each pair includes: Polymarket contract ID, Kalshi contract ID, event description, and operator verification timestamp (FR-CM-01)
**And** 20-30 pairs can be configured
**And** invalid pair definitions (missing fields, duplicate IDs) are rejected at startup with clear error messages

**Given** the config file is updated
**When** the engine is restarted
**Then** the updated pairs are loaded without code changes
**And** removed pairs are no longer tracked

### Story 3.2: Cross-Platform Arbitrage Detection

As an operator,
I want the system to automatically identify price dislocations across my curated contract pairs,
So that I can see which opportunities exist in real-time.

**Acceptance Criteria:**

**Given** normalized order books from both platforms are available (Epic 2)
**When** the detection service runs a cycle
**Then** all configured contract pairs are evaluated for price dislocations
**And** the full detection cycle completes within 1 second (FR-AD-01)
**And** raw dislocations are produced internally for edge calculation (no public event emitted at this stage — the public `OpportunityIdentifiedEvent` is emitted by Story 3.3 after enrichment)

**Given** either platform's health is "degraded" or "offline"
**When** the detection cycle runs
**Then** pairs involving that platform are skipped
**And** skipped pairs are logged at debug level

### Story 3.3: Edge Calculation & Opportunity Filtering

As an operator,
I want each opportunity's net edge calculated accounting for all real costs, and sub-threshold opportunities filtered out,
So that only genuinely profitable opportunities are surfaced.

**Acceptance Criteria:**

**Given** a raw price dislocation is passed from the detection service (Story 3.2)
**When** the edge calculator processes it
**Then** net edge is calculated as: `|Polymarket price - (1 - Kalshi price)| - Polymarket taker fee - Kalshi taker fee - gas estimate` (FR-AD-02)
**And** fees are sourced from each platform connector's `getFeeSchedule()`
**And** gas estimate uses a static conservative estimate ($0.10-0.50, configurable) converted to decimal of position size (dynamic viem estimation deferred to Epic 5)

**Given** the edge calculator produces a result
**When** net edge is below the minimum threshold (configurable, default 0.8%)
**Then** the opportunity is filtered out (FR-AD-03)
**And** filtered opportunities are logged with reason and edge value for opportunity frequency tracking
**And** an `OpportunityFilteredEvent` is emitted for monitoring

**Given** the edge calculator produces a result
**When** net edge meets or exceeds the threshold
**Then** the opportunity is enriched with: net edge %, gross edge %, fee breakdown, liquidity depth at execution prices, and recommended position size placeholder
**And** an `OpportunityIdentifiedEvent` is emitted via EventEmitter2 with full enriched context (this is the single public event that downstream modules — execution, monitoring — subscribe to)

**Given** a detection cycle completes
**When** results are summarized
**Then** total detected, total filtered (with filter reason breakdown), and total actionable counts are logged

### Story 3.4: Contract Match Approval Workflow (MVP)

As an operator,
I want to review and approve contract pair matches that need verification,
So that I maintain zero-tolerance accuracy on which contracts are paired.

**Acceptance Criteria:**

**Given** a contract pair exists in the config file
**When** it is loaded at startup
**Then** it is marked as "operator-approved" with the configured verification timestamp (FR-AD-04)
**And** no automated matching occurs — all pairs are manually curated for MVP

**Given** the operator wants to add a new contract pair
**When** they edit the config file and restart
**Then** the new pair is active immediately
**And** the system logs the new pair addition with operator rationale field

**Given** the Prisma schema needs contract match tracking
**When** this story is implemented
**Then** a `contract_matches` table is created via migration with fields: match_id, polymarket_contract_id, kalshi_contract_id, polymarket_description, kalshi_description, operator_approved, operator_approval_timestamp, operator_rationale, first_traded_timestamp (nullable), total_cycles_traded (default 0)
**And** config file pairs are seeded into the table at startup for tracking
**And** only the fields listed above are included — future fields (confidence_score, resolution tracking, divergence) are added by Epic 8's own migration

### Epic 4: Risk Management & Position Controls
Operator's capital is protected by enforced position sizing, portfolio limits, and daily loss limits. System halts trading automatically when limits are breached. Must be live before first trade.
**FRs covered:** FR-RM-01, FR-RM-02, FR-RM-03, FR-RM-04
**Additional:** Sequential execution locking with atomic risk budget reservation

### Epic 4.5: Pre-Execution Validation Sprint
Validation and hygiene sprint ensuring upstream pipeline correctness before Epic 5 connects to real platforms. Hard gate — Epic 5 does not start until 4.5 clears.
**FRs covered:** None (validation and infrastructure hygiene)
**Additional:** Property-based testing for FinancialMath, pipeline latency instrumentation, shared e2e test config, technical debt consolidation

## Epic 4: Risk Management & Position Controls

Operator's capital is protected by enforced position sizing, portfolio limits, and daily loss limits. Must be live before first trade.

### Story 4.1: Position Sizing & Portfolio Limits

As an operator,
I want the system to enforce maximum position size per pair and maximum simultaneous open pairs,
So that no single trade or accumulation of trades can over-expose my capital.

**Acceptance Criteria:**

**Given** an opportunity is being evaluated for execution
**When** the risk manager validates the position
**Then** position size is capped at 3% of bankroll per arbitrage pair (FR-RM-01)
**And** the trade is rejected if it would exceed the maximum of 10 simultaneous open pairs (FR-RM-02)
**And** rejection is logged with current position count and limit

**Given** the `IRiskManager` interface is defined in `common/interfaces/`
**When** the risk manager service is implemented
**Then** it exposes `validatePosition(opportunity): Promise<RiskDecision>` that returns approve/reject with reasoning
**And** the `RiskLimitError` subclass exists in `common/errors/` with codes 3001-3005

**Given** bankroll and risk parameters are configured
**When** the engine starts
**Then** bankroll amount, position size limit (%), and max open pairs are loaded from environment config
**And** invalid values (negative bankroll, >100% position size) are rejected at startup

**Given** the risk manager needs to track state
**When** this story is implemented
**Then** a `risk_states` table is created via Prisma migration with fields for daily P&L, current position count, and last reset timestamp

### Story 4.2: Daily Loss Limit & Trading Halt

As an operator,
I want trading to halt automatically when my daily loss limit is reached,
So that a bad day can't spiral into catastrophic losses.

**Acceptance Criteria:**

**Given** the risk budget service is tracking daily P&L
**When** cumulative daily losses reach 5% of bankroll
**Then** all trading is halted immediately (FR-RM-03)
**And** a `LimitBreachedEvent` (critical severity) is emitted via EventEmitter2
**And** the halt is logged with daily P&L, bankroll, and timestamp
**And** risk state is persisted to `risk_states` table

**Given** trading is halted due to daily loss limit
**When** the operator reviews the situation
**Then** the halt remains in effect until the next calendar day (UTC midnight)
**And** the daily loss counter resets at midnight UTC automatically

**Given** daily P&L approaches the limit
**When** losses reach 80% of the daily limit (4% of bankroll)
**Then** a `LimitApproachedEvent` (warning severity) is emitted
**And** the event includes current loss amount, remaining budget, and positions contributing to losses

### Story 4.3: Operator Risk Override

As an operator,
I want to manually approve trades that would exceed normal position limits when I have specific reasoning,
So that I can act on high-conviction opportunities while maintaining awareness of increased risk.

**Acceptance Criteria:**

**Given** an opportunity is rejected by position sizing or portfolio limit
**When** the operator sends `POST /api/risk/override` with opportunity ID and rationale (authenticated via Bearer token from Epic 1)
**Then** the trade is allowed to proceed with the override logged (FR-RM-04)
**And** the override log includes: operator confirmation timestamp, original limit, override amount, and operator rationale
**And** the override endpoint returns the risk decision with updated budget state

**Given** an override is requested
**When** the daily loss limit has been breached
**Then** the override is rejected — daily loss halt cannot be overridden
**And** the attempted override is logged as "denied: daily loss halt active"
**And** the endpoint returns 403 with clear explanation

**Given** no dashboard exists yet (MVP)
**When** the operator needs to override
**Then** they can call the REST endpoint directly (e.g., via curl or HTTP client)
**And** Epic 7's dashboard will wrap this endpoint in a UI later

### Story 4.4: Sequential Execution Locking & Risk Budget Reservation

As an operator,
I want concurrent opportunities to be evaluated and executed sequentially with atomic risk budget reservations,
So that two simultaneous opportunities can't both pass risk checks and then collectively breach limits.

**Acceptance Criteria:**

**Given** multiple opportunities are detected in the same cycle
**When** they are ranked by expected edge (highest first)
**Then** each is evaluated sequentially, not in parallel

**Given** an opportunity passes risk validation
**When** the execution lock is acquired
**Then** the risk budget is atomically reserved (correlation exposure, position count, daily capital)
**And** subsequent opportunities see the updated budget including the reservation

**Given** execution completes for a reserved opportunity
**When** both legs fill successfully
**Then** the reservation is committed (budget permanently allocated to new position)

**Given** execution fails for a reserved opportunity
**When** the opportunity is abandoned
**Then** the reservation is released (budget returned to available pool)
**And** the next opportunity in the queue can proceed

**Given** the execution lock service is implemented
**When** I inspect the code
**Then** it uses a global execution lock (MVP) ensuring only one opportunity is processed at a time
**And** reservation check + execution happens atomically within the lock

### Epic 4.5: Pre-Execution Validation Sprint
Validation and hygiene sprint ensuring upstream pipeline correctness before Epic 5 connects to real platforms. Hard gate — Epic 5 does not start until 4.5 clears. Emerged from Epic 4 retrospective after identifying that three consecutive epics failed to deliver retro commitments that existed outside the story system.
**FRs covered:** None (validation and infrastructure hygiene)
**Additional:** Property-based testing for FinancialMath, pipeline latency instrumentation, shared e2e test config, technical debt consolidation

## Epic 4.5: Pre-Execution Validation Sprint

Validation and hygiene sprint ensuring upstream pipeline correctness before Epic 5 connects to real platforms with real money. All items are converted retro commitments that were previously skipped because they existed outside the story system. Hard gate: Epic 5 does not start until Epic 4.5 clears.

### Story 4.5.0: Regression Baseline Verification

As an operator,
I want to confirm all existing tests pass clean on a fresh checkout before adding new tests,
So that I can distinguish pre-existing failures from new ones introduced during the validation sprint.

**Acceptance Criteria:**

**Given** the pm-arbitrage-engine codebase at the end of Epic 4
**When** `pnpm test` is run on a clean checkout
**Then** 484+ tests pass with zero failures
**And** `pnpm lint` passes with no errors
**And** this verified count becomes the regression baseline for Stories 4.5.1-4.5.4

### Story 4.5.1: Property-Based Testing for FinancialMath Composition Chain

As an operator,
I want the financial math composition chain tested with randomized inputs to surface edge cases,
So that I can trust position sizing and budget reservation calculations with real money.

**Acceptance Criteria:**

**Given** the `fast-check` library is installed
**When** property-based tests run against the composition chain
**Then** arbitraries cover: price (0-1), fees (0-5%), gas (0-1), position sizes (10-10000), bankroll (1000-1000000)
**And** the full chain is tested: `calculateGrossEdge` → `calculateNetEdge` → position sizing → `reserveBudget`
**And** 1000+ random inputs are generated per test property
**And** every output is a finite `Decimal` (no NaN, no Infinity, no negative position sizes)
**And** all existing 484+ tests continue to pass

### Story 4.5.2: Pipeline Latency Instrumentation

As an operator,
I want each stage of the trading pipeline to log its execution duration,
So that I can identify performance bottlenecks and measure the impact of the execution lock on cycle time.

**Acceptance Criteria:**

**Given** `TradingEngineService.executeCycle()` runs a full detection → risk → execution cycle
**When** each pipeline stage completes
**Then** duration in milliseconds is logged for: detection, edge calculation, risk validation, execution queue processing
**And** total cycle time is logged
**And** a documented baseline is established from running 100+ test cycles
**And** all existing tests continue to pass

### Story 4.5.3: Shared e2e Test Environment Config

As an operator,
I want all e2e test files to share a single environment configuration,
So that adding a new env var requires touching one file instead of three.

**Acceptance Criteria:**

**Given** environment variables are currently duplicated across `app.e2e-spec.ts`, `core-lifecycle.e2e-spec.ts`, and `logging.e2e-spec.ts`
**When** a shared test environment config is extracted
**Then** all three e2e test files import from a single shared source
**And** all existing e2e tests pass with the shared config
**And** adding a new environment variable requires modifying exactly one file
**And** `pnpm lint` passes with no errors

### Story 4.5.4: Technical Debt Consolidation

As an operator,
I want all known technical debt and framework gotchas centralized in dedicated files,
So that accumulated knowledge from Epics 2-4 is discoverable and actionable.

**Acceptance Criteria:**

**Given** technical debt and gotchas are currently scattered across individual story dev notes
**When** consolidation is complete
**Then** `technical-debt.md` exists with all known debt items from Epics 2-4, each with: description, priority, target epic, and source story
**And** `docs/gotchas.md` exists with framework-specific gotchas including: `plainToInstance` defaults, `OnModuleInit` ordering, `ConfigService.get` returning strings, circular import resolution pattern, fire-once event pattern
**And** each gotcha has a code example showing the problem and solution
**And** no existing tests or code are modified

### Story 4.5.5: Kalshi Order Book Normalization Deduplication

As an operator,
I want the Kalshi cents-to-decimal and NO-to-YES inversion logic extracted to a single shared utility,
So that Epic 5 execution code builds on a single source of truth instead of 3 duplicated implementations.

**Acceptance Criteria:**

**Given** Kalshi normalization logic is duplicated in `kalshi.connector.ts`, `kalshi-websocket.client.ts`, and `order-book-normalizer.service.ts`
**When** deduplication is complete
**Then** a shared utility exists in `common/utils/` containing the cents-to-decimal conversion and NO-to-YES price inversion
**And** all three consumers import from the shared utility instead of implementing their own
**And** all existing 498+ tests pass with zero failures
**And** `pnpm lint` reports zero errors
**And** new unit tests cover the shared utility (edge cases: zero price, boundary values 0/100 cents, YES/NO sides)

### Epic 5: Trade Execution, Leg Management & Exit Monitoring
Operator can execute arbitrage trades with near-simultaneous leg submission, single-leg exposure detection/alerting, and automated exit management (take profit, stop loss, time-based). Complete automated trade lifecycle.
**FRs covered:** FR-EX-01, FR-EX-02, FR-EX-03, FR-EX-04, FR-EX-05, FR-EX-06, FR-EM-01
**Additional:** Startup reconciliation (moved from Epic 1), open_positions and orders tables

## Epic 5: Trade Execution, Leg Management & Exit Monitoring

Operator can execute arbitrage trades with near-simultaneous leg submission, single-leg exposure detection/alerting, and automated exit management. Complete automated trade lifecycle.

### Story 5.1: Order Submission & Position Tracking

As an operator,
I want the system to submit orders to both platforms and track open positions in the database,
So that I have a reliable record of all trades and their current state.

**Acceptance Criteria:**

**Given** an opportunity has passed risk validation (Epic 4) and is locked for execution
**When** the execution service processes it
**Then** the primary leg (determined by `primaryLeg` field in the contract pair config, defaulting to "kalshi") is submitted first via `IPlatformConnector.submitOrder()` (FR-EX-02)
**And** the second leg is submitted immediately after the first (target: <100ms between submissions, same event loop cycle) (FR-EX-01)
**And** order book depth is verified before each order placement — minimum size sufficient for target position at expected price (FR-EX-03)

**Given** an order is submitted
**When** a fill is confirmed by the platform
**Then** an `OrderFilledEvent` is emitted via EventEmitter2
**And** the position is recorded in the `open_positions` table (Prisma migration: position_id, polymarket_order_id, kalshi_order_id, polymarket_side, kalshi_side, entry_prices, sizes, expected_edge, status, created_at, updated_at)
**And** orders are tracked in the `orders` table (Prisma migration: order_id, platform, contract_id, side, price, size, status, fill_price, fill_size, timestamps)

**Given** order book depth is insufficient for the target position size
**When** depth verification fails
**Then** the opportunity is abandoned, execution lock released, and logged as "filtered: insufficient liquidity" (code 2001)

**Given** the contract pair config from Epic 3 Story 3.1
**When** a new pair is defined
**Then** it includes an optional `primaryLeg` field ("kalshi" | "polymarket", default "kalshi") specifying which platform's leg to execute first

### Story 5.2: Single-Leg Exposure Detection & Alerting

As an operator,
I want the system to detect when only one leg fills and immediately alert me with full context,
So that I can make an informed decision about the exposed position.

**Acceptance Criteria:**

**Given** the first leg has filled
**When** the second leg fails to fill within 5 seconds (FR-EX-04)
**Then** a single-leg exposure is detected
**And** a `SingleLegExposureEvent` (critical severity) is emitted with: filled leg details (platform, side, price, size), failed leg details, current prices on both platforms, estimated P&L scenarios (close now, retry at current price, hold), and recommended actions (FR-EX-05)

**Given** single-leg exposure is detected
**When** the system creates the alert
**Then** the `ExecutionError` (code 2004) is logged with full context
**And** the position status is updated to "single_leg_exposed" in `open_positions`

**Given** single-leg exposure events accumulate
**When** the monthly count exceeds 5
**Then** a warning event is emitted indicating systematic investigation needed (NFR-R3)

### Story 5.3: Single-Leg Resolution (Operator Actions)

As an operator,
I want to retry the failed leg at a worse price or close the filled leg to cut losses,
So that I can resolve single-leg exposure within acceptable loss parameters.

**Acceptance Criteria:**

**Given** a position is in "single_leg_exposed" state
**When** the operator sends `POST /api/positions/:id/retry-leg` with updated price parameters
**Then** the system attempts to fill the failed leg at the specified price (FR-EX-06)
**And** if successful, the position transitions to "open" with updated fill details
**And** the retry is logged with original price, retry price, and resulting edge

**Given** a position is in "single_leg_exposed" state
**When** the operator sends `POST /api/positions/:id/close-leg`
**Then** the filled leg is closed via the platform connector (submitting an opposing trade on that platform)
**And** the position transitions to "closed" with realized P&L
**And** the close is logged with loss amount and operator rationale

**Given** no operator action is taken on a single-leg exposure
**When** the position remains exposed
**Then** the system continues emitting the exposure alert every 60 seconds until resolved
**And** current P&L scenarios are updated with each alert

### Story 5.4: Exit Monitoring & Fixed Threshold Exits

As an operator,
I want open positions continuously monitored and automatically closed when exit thresholds are hit,
So that profits are captured and losses are limited without manual intervention.

**Acceptance Criteria:**

**Given** a position is in "open" state
**When** the exit monitor evaluates it during each polling cycle
**Then** current edge is recalculated using live order book prices from both platforms

**Given** the current captured edge reaches 80% of initial edge
**When** the take-profit threshold is hit
**Then** exit orders are submitted to both platforms to reverse each leg on its respective platform (sell what was bought, buy what was sold) (FR-EM-01)
**And** an `ExitTriggeredEvent` is emitted with exit type "take_profit", realized P&L, and initial vs. final edge

**Given** the current loss reaches 2x the initial edge
**When** the stop-loss threshold is hit
**Then** exit orders are submitted immediately (reversing each leg on its platform)
**And** an `ExitTriggeredEvent` is emitted with exit type "stop_loss" and loss details

**Given** a position is within 48 hours of contract resolution
**When** the time-based threshold is hit
**Then** exit orders are submitted (reversing each leg on its platform)
**And** an `ExitTriggeredEvent` is emitted with exit type "time_based" and remaining edge

**Given** an exit order fills on both platforms
**When** the position is fully closed
**Then** the position transitions to "closed" with complete P&L record
**And** daily P&L in risk budget is updated
**And** the position count is decremented, freeing capacity for new trades

**Given** an exit order fails to fill on one platform
**When** a partial exit occurs
**Then** the position transitions to "exit_partial"
**And** a `SingleLegExposureEvent` is emitted, reusing the same detection and resolution workflow from Stories 5.2/5.3
**And** the operator can resolve via the same retry-leg or close-leg endpoints

### Story 5.5: Startup Reconciliation & Crash Recovery

As an operator,
I want the system to reconcile its state against both platforms on startup,
So that I can trust the system after a restart or crash — especially if positions were open.

**Acceptance Criteria:**

**Given** the engine starts and `open_positions` records exist in the database
**When** startup reconciliation runs
**Then** the system queries both Kalshi and Polymarket APIs for all fills/orders in the time window `[last_state_timestamp - 60s, current_time]`
**And** API-reported fills are compared against local position records

**Given** a fill is reported by the platform API but not in local state
**When** a discrepancy is detected
**Then** a `SystemHealthError` (code 4005, critical severity) is emitted
**And** the position is flagged as "RECONCILIATION_REQUIRED" in the database
**And** all new trading is halted until operator confirms corrective action via `POST /api/reconciliation/:id/resolve`

**Given** no discrepancies are found
**When** reconciliation completes
**Then** "reconciliation complete, no discrepancies" is logged
**And** existing open positions resume monitoring and exit evaluation
**And** the risk budget is recalculated from current position state

**Given** reconciliation results are produced
**When** they are persisted
**Then** results are written via structured JSON logging with reconciliation details (positions matched, discrepancies found, timestamps)
**And** note: once Epic 6 Story 6.5 deploys the `audit_logs` table with hash chaining, reconciliation results should be retroactively routed through the AuditLogService for tamper-evident persistence

### Epic 5.5: Paper Trading Infrastructure
Paper trading as a permanent, platform-agnostic system capability. Each platform independently configurable as live or paper. Decorator pattern wraps existing IPlatformConnector implementations — zero changes to live connector code.
**FRs covered:** FR-DI-05 (new platform connectors without modifying core modules)
**Additional:** Interface stabilization (cancelOrder, mock factories), per-platform fill simulation, `is_paper` state isolation, mixed mode validation

## Epic 5.5: Paper Trading Infrastructure

Paper trading as a permanent, platform-agnostic system capability. Each platform independently configurable as live or paper. Decorator pattern wraps existing IPlatformConnector implementations — zero changes to live connector code.

### Story 5.5.0: Interface Stabilization & Test Infrastructure

As a developer,
I want cancelOrder() implemented, mocks centralized, and documentation updated,
So that the interface is frozen and stable before building the decorator pattern on top.

**Acceptance Criteria:**

**Given** `cancelOrder()` is defined in `IPlatformConnector` but not implemented
**When** Story 5.5.0 is complete
**Then** `cancelOrder()` is functional on both Kalshi and Polymarket connectors
**And** cancellation errors are wrapped in `ExecutionError` with appropriate error codes

**Given** mock files are duplicated across 15+ test files
**When** Story 5.5.0 is complete
**Then** centralized mock factories exist: `createMockPlatformConnector()`, `createMockRiskManager()`, `createMockExecutionEngine()`
**And** each factory returns a complete mock with sensible defaults and per-call overrides
**And** all existing test files are migrated to use factories (zero duplicated mock definitions)

**Given** P&L source-of-truth confusion occurred in Stories 5.3, 5.4, 5.5
**When** Story 5.5.0 is complete
**Then** `gotchas.md` exists in project root with P&L source-of-truth rule: "Always compute P&L from order fill records, never from `position.entryPrices`"
**And** rule includes a code example showing correct vs incorrect approach

**Given** technical debt items accumulated across Epics 2-5
**When** Story 5.5.0 is complete
**Then** `technical-debt.md` is updated: Kalshi dedup marked resolved, Epic 5 items added, gas estimation references its Epic 6 story

**Given** reconciliation module lives in `src/reconciliation/` not `persistence/`
**When** Story 5.5.0 is complete
**Then** architecture doc reflects actual module location with rationale (ADR from Story 5.5)

**Given** persistence repository coverage is 52.17% statements / 0% branches
**When** Story 5.5.0 is complete
**Then** coverage audit documents which untested paths are business logic vs Prisma pass-through
**And** specific gaps are flagged for coverage in stories that touch those files

**Sequencing:** This story MUST complete before Story 5.5.1 begins. Dependency chain: cancelOrder() → mock factory (needs final interface) → decorator in 5.5.1 (wraps stable interface).

**Interface freeze takes effect after this story merges.** `IPlatformConnector` and `IRiskManager` — no new methods until Epic 6 unless team discusses and handles full ripple (mock factory + decorator) in same PR.

**DoD Gates (from Epic 4.5 retro):**
- Test isolation: no shared mutable state between tests
- Interface preservation: no breaking changes to existing interface methods
- Normalization ownership: connectors own all platform-specific normalization

- All existing tests pass (baseline: 731), `pnpm lint` reports zero errors
- New unit tests cover: cancelOrder on both connectors, mock factory completeness, factory override behavior

### Story 5.5.1: Paper Trading Connector & Mode Configuration

As an operator,
I want to configure any platform connector in paper mode via environment variables,
So that I can run execution logic against live order books without submitting real orders.

**Acceptance Criteria:**

**Given** `PLATFORM_MODE_KALSHI=paper` is set in environment
**When** the engine starts
**Then** the Kalshi connector is wrapped in a PaperTradingConnector decorator

**Given** PaperTradingConnector wraps a live connector
**When** `getOrderBook()`, `getHealth()`, `onOrderBookUpdate()` are called
**Then** they proxy transparently to the underlying live connector

**Given** PaperTradingConnector wraps a live connector
**When** `submitOrder()` is called
**Then** the order is intercepted locally (never reaches the platform API)
**And** a simulated fill is generated using configurable parameters

**Given** per-platform fill simulation config exists
**When** a paper order is submitted for Kalshi
**Then** fill latency uses `PAPER_FILL_LATENCY_MS_KALSHI` (default: 150ms)
**And** slippage uses `PAPER_SLIPPAGE_BPS_KALSHI` (default: 5 bps)

**Given** per-platform fill simulation config exists
**When** a paper order is submitted for Polymarket
**Then** fill latency uses `PAPER_FILL_LATENCY_MS_POLYMARKET` (default: 800ms)
**And** slippage uses `PAPER_SLIPPAGE_BPS_POLYMARKET` (default: 15 bps)

**Given** platform mode is set at startup
**When** the engine is running
**Then** the mode cannot be changed without a restart (immutable at runtime)

**Given** PaperTradingConnector is active
**When** any execution event is emitted
**Then** the event payload includes `isPaper: true` metadata

- `connectors/paper/paper-trading.connector.ts` implements IPlatformConnector via decorator pattern
- `connectors/paper/fill-simulator.service.ts` handles simulated fill generation
- `connectors/paper/paper-trading.types.ts` defines PaperTradingConfig, SimulatedFill types
- All existing tests pass, `pnpm lint` reports zero errors
- New unit tests cover: decorator proxying, fill simulation, config validation, event metadata

### Story 5.5.2: Paper Position State Isolation & Tracking

As an operator,
I want paper trading positions tracked separately from live positions,
So that paper results never contaminate live P&L or risk calculations.

**Acceptance Criteria:**

**Given** the Prisma schema
**When** migration runs
**Then** `open_positions` and `orders` tables have an `is_paper` Boolean column (default: false)
**And** a composite index exists on `(is_paper, status)` for both tables

**Given** paper mode is active for a platform
**When** a paper order fills
**Then** the resulting position is persisted with `is_paper = true`

**Given** risk budget queries (position limits, exposure calculations)
**When** querying positions
**Then** repository methods filter by `is_paper = false` by default (live-only)
**And** paper positions have an isolated risk budget that does not affect live limits

**Given** paper positions exist
**When** the operator views the dashboard
**Then** paper positions are visually distinct (amber border, `[PAPER]` tag)
**And** paper P&L is excluded from live summary totals by default (toggle to include)

- All existing tests pass, `pnpm lint` reports zero errors
- New unit tests cover: repository filtering, isolation verification, migration rollback

### Story 5.5.3: Mixed Mode Validation & Operational Safety

As an operator,
I want the system to validate mixed mode configurations at startup,
So that I am protected from invalid or dangerous platform mode combinations.

**Acceptance Criteria:**

**Given** platform mode configuration
**When** the engine starts
**Then** startup logs clearly display each platform's mode (`[Kalshi: LIVE] [Polymarket: PAPER]`)

**Given** an invalid mode value (not `live` or `paper`)
**When** the engine starts
**Then** startup fails with a clear error message

**Given** mixed mode is active (some platforms live, some paper)
**When** an arbitrage opportunity spans a live and paper platform
**Then** the execution proceeds (paper side simulated, live side real)
**And** the opportunity and resulting positions are tagged with `mixedMode: true`

**Given** all platforms are in paper mode
**When** the engine starts
**Then** a startup warning is logged: "All platforms in PAPER mode — no live trading active"

**Given** the engine is running in any mode
**When** the operator queries system status
**Then** the API response includes the mode for each platform

- All existing tests pass, `pnpm lint` reports zero errors
- New unit tests cover: startup validation, mixed mode tagging, mode display in status API
- E2E test: full cycle with one platform live + one paper, verifying isolation

### Epic 6: Monitoring, Alerting & Compliance Logging
Operator receives real-time Telegram alerts, has CSV trade logs for daily review, compliance validation before execution, and complete audit trail. MVP feature set complete.
**FRs covered:** FR-MA-01, FR-MA-02, FR-MA-03, FR-DE-01, FR-DE-02, FR-PI-05
**Additional:** Gas estimation implementation (tech debt from Epic 2), alerting health monitoring (daily test alerts), error code catalog implementation

### Epic 6.5: Paper Trading Validation
7-day structured validation of the complete system against live markets in paper mode. Hard gate — Epic 7 does not start until Epic 6.5 clears. Follows the precedent of Epic 4.5 and Epic 5.5 as a validation sprint inserted between main epics.
**FRs covered:** None (validation and operational readiness)
**Additional:** Codebase audit, event pair selection, VPS deployment, metrics framework, 5-day paper execution, validation report

## Epic 6: Monitoring, Alerting & Compliance Logging

Operator receives real-time Telegram alerts, has CSV trade logs for daily review, compliance validation before execution, and complete audit trail. MVP feature set complete.

### Story 6.0: Gas Estimation Implementation

As a developer,
I want gas costs accurately estimated and included in edge calculations,
So that Polymarket arbitrage opportunities account for real execution costs instead of using a placeholder.

**Acceptance Criteria:**

**Given** the TODO in `polymarket.connector.ts` for gas estimation
**When** Story 6.0 is complete
**Then** the TODO is removed and replaced with functional gas estimation logic
**And** gas cost is included in edge calculations via the existing fee/gas parameters

**Given** a Polymarket order is being evaluated
**When** gas estimation runs
**Then** the estimate includes a 20% safety buffer (per PRD NFR-I4 and architecture spec)
**And** the estimate uses recent on-chain data (not a hardcoded constant)

**Given** paper trading data from Epic 5.5
**When** gas estimation is calibrated
**Then** simulated gas costs are informed by observed patterns during paper trading validation

- All existing tests pass, `pnpm lint` reports zero errors
- New unit tests cover: gas estimation accuracy, buffer application, edge calculation integration
- TODO in `polymarket.connector.ts` removed

**Technical Debt:** Resolves carry-forward item from Epic 2 (carried through Epics 4.5, 5). Source: Epic 5 retrospective commitment.

### Story 6.1: Telegram Alert Integration

As an operator,
I want real-time Telegram alerts for all critical system events,
So that I'm immediately informed of opportunities, executions, risks, and errors wherever I am.

**Acceptance Criteria:**

**Given** a Telegram bot token and chat ID are configured
**When** a critical event is emitted via EventEmitter2 (OpportunityIdentified, OrderFilled, ExitTriggered, SingleLegExposure, LimitBreach, PlatformDegraded, SystemHealthError)
**Then** a Telegram message is sent within 2 seconds of the event (FR-MA-01)
**And** the message includes full context: event type, timestamp, affected contracts, P&L impact, and recommended actions where applicable

**Given** the Telegram API fails
**When** 3 consecutive send attempts fail
**Then** the failure is logged as a warning
**And** alerts are buffered locally and retried
**And** system operation continues — alerting failure never blocks trading

**Given** the scheduler triggers the daily test alert (configurable time, default 8am)
**When** the test fires
**Then** a test message is sent to Telegram
**And** success/failure is logged for alerting health monitoring

### Story 6.2: Event Consumer & Monitoring Hub

As an operator,
I want a centralized monitoring service that subscribes to all domain events and routes them to the right outputs,
So that I have a single, reliable system for observability across all modules.

**Acceptance Criteria:**

**Given** the event consumer service is initialized
**When** it registers with EventEmitter2
**Then** it subscribes to all domain event types: `execution.*`, `risk.*`, `detection.*`, `platform.*`, `monitoring.*`

**Given** an event is received
**When** the consumer routes it by severity
**Then** Critical events → Telegram alert + audit log (via AuditLogService from Story 6.5) + potential halt evaluation
**And** Warning events → Telegram alert + audit log
**And** Info events → audit log only

**Given** the global exception filter is in place (from architecture)
**When** an unhandled `SystemError` is caught
**Then** it is routed through the same severity-based pipeline
**And** the error code, severity, and retry strategy are included in the output

### Story 6.3: CSV Trade Logging & Daily Summaries

As an operator,
I want all trades logged to timestamped CSV files with a daily summary,
So that I can review each day's activity in a spreadsheet and track performance over time.

**Acceptance Criteria:**

**Given** a trade is executed (position opened or closed)
**When** the trade completes
**Then** it is appended to a timestamped CSV file (one file per day) with columns: timestamp, platform, contract_id, side, price, size, fill_price, fees, gas, edge, P&L, position_id, correlation_id (FR-MA-02)
**And** CSV files are retained for 7 years

**Given** a new calendar day begins (UTC midnight)
**When** the daily summary generates
**Then** it includes: total trades, total P&L, open position count, closed position count, opportunities detected vs. executed, single-leg events, risk limit events, system health summary (FR-MA-03)
**And** the summary is appended to a daily summary CSV

**Given** the operator wants to export trade logs
**When** they request `GET /api/exports/trades?startDate=X&endDate=Y&format=json|csv`
**Then** the system returns trade data in the requested format (FR-DE-01)

### Story 6.4: Compliance Validation & Trade Gating

As an operator,
I want every trade validated against a compliance matrix before execution,
So that I never accidentally trade non-compliant contracts that could create regulatory risk.

**Acceptance Criteria:**

**Given** a compliance matrix is configured (per-platform rules specifying which contract categories are tradeable)
**When** an opportunity enters the execution service (after risk validation, before `submitOrder()` is called)
**Then** the compliance validator checks the contract category against the matrix for both platforms (FR-PI-05)
**And** non-compliant trades are hard-blocked with operator notification
**And** the rejection is logged with: contract category, platform, rule violated, and timestamp
**And** the execution service returns early without submitting orders

**Given** the compliance matrix is in config
**When** the engine starts
**Then** rules are loaded and validated (no empty rules, no conflicting platform entries)
**And** MVP implementation uses hardcoded rules in configuration file

**Given** the compliance check placement in the pipeline
**When** I inspect the execution service code
**Then** compliance validation is the first operation inside the execution service, running after the execution lock is acquired but before any `submitOrder()` call
**And** this avoids modifying the `IRiskManager` interface — compliance is an execution concern, not a risk concern

### Story 6.5: Audit Trail & Tax Report Export

As an operator,
I want a tamper-evident audit trail and annual tax report export,
So that my legal counsel and tax advisor have exactly what they need without manual reconstruction.

**Acceptance Criteria:**

**Given** the `audit_logs` table needs to be created
**When** this story is implemented
**Then** a Prisma migration creates the `audit_logs` table with fields: id, timestamp, event_type, module, correlation_id, details (JSON), previous_hash, current_hash
**And** this story is the canonical owner of the `audit_logs` table — no other story creates it

**Given** the AuditLogService is implemented
**When** any auditable event occurs (trade, manual intervention, risk override, system error, reconciliation)
**Then** the entry includes SHA-256 hash of the previous entry's hash + current data, creating a verifiable chain (NFR-S3)
**And** the service is available for injection by all modules (monitoring hub from 6.2, reconciliation from 5.5, etc.)

**Given** Story 5.5's reconciliation logging used structured JSON as interim
**When** Story 6.5 is deployed
**Then** the reconciliation service is updated to route results through AuditLogService for tamper-evident persistence

**Given** the operator requests an annual tax report
**When** they call `GET /api/exports/tax-report?year=2026`
**Then** the system generates a CSV with: complete trade log, P&L summaries by platform and quarter, cost basis tracking, and transaction categorization (on-chain vs. regulated exchange) (FR-DE-02)

**Given** the audit trail is queried
**When** any entry's hash chain is verified
**Then** the chain is provably intact (each entry's hash matches recalculation from previous entry + current data)
**And** any tampering would break the chain and be detectable

### Epic 6.5: Paper Trading Validation
7-day structured validation of the complete system against live markets in paper mode. Hard gate — Epic 7 does not start until Epic 6.5 clears. Follows the precedent of Epic 4.5 and Epic 5.5 as a validation sprint inserted between main epics.
**FRs covered:** None (validation and operational readiness)
**Additional:** Codebase audit, event pair selection, VPS deployment, metrics framework, 5-day paper execution, validation report

## Epic 6.5: Paper Trading Validation

7-day structured validation of the complete system against live markets in paper mode. Phases: codebase readiness → infrastructure provisioning → measurement framework → paper execution (5 days) → validation report. Hard gate: Epic 7 does not start until Epic 6.5 clears.

**Sequencing:** 6.5.0 → 6.5.0a → [6.5.1 + 6.5.2 in parallel] → 6.5.2a → 6.5.3 → 6.5.4 → 6.5.5 → 6.5.6

### Story 6.5.0: Codebase Readiness & Tech Debt Clearance

As an operator,
I want to verify the codebase is clean, all known tech debt items from Epic 6 are resolved, and the system runs correctly on a fresh checkout,
So that paper trading validation starts from a known-good baseline with no pre-existing issues muddying the results.

**Acceptance Criteria:**

**Given** the pm-arbitrage-engine codebase at the end of Epic 6
**When** `pnpm test` is run on a clean checkout
**Then** 1,078+ tests pass with zero failures
**And** `pnpm lint` passes with zero errors
**And** this verified count becomes the regression baseline for Epic 6.5

**Given** the Epic 6 retro identified financial math violations in "display" code (Story 6.1 formatters)
**When** a decimal compliance audit is performed across the engine codebase
**Then** every arithmetic operation on monetary fields uses `decimal.js` — no native JS `+`, `-`, `*`, `/` on prices, fees, edges, P&L, or budget values
**And** violations found are fixed and covered by tests
**And** audit results are documented (files checked, violations found, fixes applied)
**And** scope boundary: this covers `src/` production code only — test assertions that compare Decimal outputs using `.toNumber()`, `.toFixed()`, or `toBeCloseTo()` for readability are not violations. The rule targets computation, not assertion formatting.

**Given** the retro established an absolute Decimal math rule with no context-based exceptions
**When** this story completes
**Then** `gotchas.md` includes the Decimal math rule with examples of non-obvious violation sites (formatters, test helpers, logging utilities)
**And** the rule explicitly states: any arithmetic on a field that touches money uses `decimal.js`, regardless of where the code lives

**Given** `financial-math.property.spec.ts` has a known flaky property test (carry-forward from Epic 5.5)
**When** a timeboxed 1-hour fix attempt is performed
**Then** either: the test is fixed and passes reliably on 10 consecutive runs, **or** the test is documented as non-deterministic with root cause analysis and a decision recorded (keep with `@retry`, remove, or rewrite)

**Given** Epic 6 added REST endpoints (trade export, tax report, reconciliation)
**When** Swagger spec validation is performed
**Then** all Epic 6 endpoints have proper `@ApiOperation`, `@ApiResponse`, and DTO decorators
**And** `pnpm build` produces no Swagger-related warnings

**Given** paper trading mode requires specific environment configuration
**When** `.env.example` and `.env.development` are reviewed
**Then** all `PLATFORM_MODE_*`, `PAPER_FILL_*`, and `PAPER_SLIPPAGE_*` variables are present with documented defaults
**And** `.env.development` is configured for dual paper mode (both platforms)

**Given** the system depends on PostgreSQL via Docker Compose
**When** `docker-compose -f docker-compose.dev.yml up -d` is run followed by `pnpm prisma migrate dev`
**Then** PostgreSQL starts cleanly, all migrations apply, and `pnpm prisma studio` connects successfully

**Given** the application should run stable in idle paper mode
**When** the engine is started locally in dual paper mode and left running for 30 minutes
**Then** application logs are captured for the full runtime window
**And** logs are analyzed for errors, unhandled exceptions, memory warnings, connection failures, or unexpected event patterns
**And** any issues found are documented and fixed (or triaged with rationale if deferring)
**And** a clean 30-minute run with no errors or anomalies is achieved before marking this story complete

**Sequencing:** This story MUST complete before Stories 6.5.1, 6.5.2, and 6.5.3 begin. It establishes the baseline for all subsequent validation work.

**DoD Gates (carried from Epic 4.5/5.5):**
- Test isolation: no shared mutable state between tests
- All existing 1,078+ tests pass, `pnpm lint` reports zero errors
- Any new tests added for decimal violations follow co-located pattern

### Story 6.5.0a: Code Review Tech Debt Fixes

As an operator,
I want the pre-existing tech debt items surfaced by the Story 6.5.0 code review to be resolved before paper trading validation begins,
So that the validation run produces trustworthy results on a codebase with no known observability gaps or architecture violations.

**Acceptance Criteria:**

**Given** the `verifyDepth()` method in `execution.service.ts` has a catch block that silently returns `false`
**When** an API failure, rate limit, or transient error occurs during depth verification
**Then** a structured warning log is emitted with the error context (platform, market, error type)
**And** a `execution.depth-check.failed` event is emitted for monitoring consumption
**And** the method still returns `false` (fail-closed behavior preserved)

**Given** the `handlePriceChange()` method in `polymarket-websocket.client.ts` may not update order book price levels
**When** the method's behavior is investigated against Polymarket's WebSocket message types
**Then** either: (a) confirmed dead code path — documented with rationale and no fix needed, **or** (b) confirmed bug — price levels are updated from `price_change` messages and covered by tests
**And** investigation findings are documented in `gotchas.md`

**Given** `kalshi.connector.ts` has `getPositions()` throwing raw `new Error('getPositions not implemented')`
**When** this placeholder is reviewed
**Then** it is replaced with `throw new PlatformApiError(...)` using the SystemError hierarchy with appropriate error code
**And** the method signature and JSDoc remain unchanged

**Given** the `polymarket-websocket.client.ts` staleness check detects data older than 30 seconds
**When** stale data is detected and the emit is skipped
**Then** a `platform.health.data-stale` event is emitted with platform identifier and staleness duration
**And** the event is consumable by the monitoring hub for Telegram alerting

**Sequencing:** After 6.5.0, before 6.5.1. Can run in parallel with 6.5.1/6.5.2/6.5.3 if preferred.

**DoD Gates:**
- All existing tests pass, `pnpm lint` reports zero errors
- New event emissions have co-located unit tests
- No new `decimal.js` violations introduced

**Origin:** Code review findings #4, #5, #8, #10 from `6-5-0-code-review-findings.md`

### Story 6.5.1: Event Pair Selection & Contract Configuration

As an operator,
I want a curated set of active cross-platform contract pairs configured and verified,
So that the detection engine has real market pairs to monitor during validation phases.

**Acceptance Criteria:**

**Given** the system requires cross-platform contract pairs to detect arbitrage opportunities
**When** live Kalshi and Polymarket markets are surveyed
**Then** 10-15 active cross-platform pairs are identified where both platforms offer contracts on the same underlying event
**And** each pair has matching resolution criteria (same question, compatible outcome structure, overlapping resolution window)
**And** pairs are diversified across at least 3 categories (e.g., politics, crypto, economics, sports, weather)

**Given** identified pairs need verified contract identifiers
**When** each pair is validated against live platform APIs
**Then** Kalshi event ticker and market IDs are confirmed accessible via the Kalshi API
**And** Polymarket condition IDs and token IDs are confirmed accessible via the Polymarket API
**And** each pair has been spot-checked for active order book depth on both platforms (not empty or delisted markets)

**Given** the system loads contract pairs from `contract-pairs.yaml`
**When** all verified pairs are configured
**Then** `contract-pairs.yaml` contains 10-15 entries in the format expected by `ContractMatchingService`
**And** each entry includes: pair name, Kalshi identifiers, Polymarket identifiers, category tag, expected resolution date, and confidence score (100 for manually verified)
**And** the engine starts successfully with the new configuration and `ContractMatchingService` loads all pairs without errors

**Given** contract pairs may become stale (resolved, delisted, or liquidity dried up)
**When** pair selection is complete
**Then** a selection log documents: rationale for each pair chosen, pairs considered but rejected (with reason), date of verification, and expected resolution dates
**And** pairs with resolution dates within 14 days of Phase 2 end are flagged as at-risk for early resolution during validation

**Given** the detection engine needs sufficient opportunity surface
**When** pairs are selected
**Then** at least 5 pairs have resolution dates >30 days out (ensuring they remain active through the full 7-day validation window)
**And** at least 3 pairs are in historically active categories with regular order book updates

**Sequencing:** Requires 6.5.0 complete. Can run in parallel with 6.5.2 and 6.5.3. Must complete before 6.5.5.

**Previous Story Intelligence:**
- `contract-pairs.yaml` format defined in Story 3.1 (Manual Contract Pair Configuration)
- `ContractMatchingService` loads pairs at startup — verify format compatibility before writing 10+ entries
- Kalshi API uses event tickers; Polymarket uses condition IDs — different identifier structures
- Compliance config from Story 6.4 has blocked categories — cross-reference pairs against compliance config to avoid `COMPLIANCE_BLOCKED` on first run

### Story 6.5.2: Deployment Runbook & VPS Provisioning

As an operator,
I want a documented deployment process and a provisioned VPS running the engine,
So that paper trading validation runs against live markets on persistent infrastructure rather than a local dev machine.

**Acceptance Criteria:**

**Given** the system needs persistent infrastructure for 7+ days of continuous operation
**When** a Hetzner VPS is provisioned
**Then** the VPS runs Ubuntu 24.04 LTS
**And** SSH key authentication is configured (password auth disabled)
**And** firewall is configured SSH-only (no public-facing ports)
**And** VPS sizing is documented with rationale (CPU, RAM, disk for PostgreSQL + Node.js engine)

**Given** the engine requires a runtime environment
**When** the VPS is configured
**Then** Node.js 20 LTS, pnpm, and Docker (for PostgreSQL) are installed
**And** PostgreSQL runs via Docker Compose with the production compose file
**And** Prisma migrations apply successfully against the production database
**And** the engine builds cleanly via `pnpm build`

**Given** the engine needs to run continuously and survive SSH disconnects
**When** process management is configured
**Then** pm2 manages the engine process with automatic restart on crash
**And** pm2 is configured for startup persistence (survives VPS reboot)
**And** `pm2 logs` captures stdout/stderr for post-hoc analysis

**Given** production credentials must be managed securely
**When** `.env.production` is configured
**Then** a `.env.production` template exists in the runbook with all required variables and placeholder values
**And** the deployed `.env.production` contains real API keys for Kalshi (sandbox) and Polymarket (testnet/read-only)
**And** both platforms are configured in paper mode (`PLATFORM_MODE_KALSHI=paper`, `PLATFORM_MODE_POLYMARKET=paper`)
**And** `.env.production` is never committed to version control

**Given** data loss during validation would require restarting the observation period
**When** backup is configured
**Then** hourly `pg_dump` runs via cron, compressed, with 7-day rolling retention
**And** at least one backup has been manually verified by restoring to a separate database and confirming row counts

**Given** the deployment process should be reproducible
**When** the runbook is complete
**Then** a deployment runbook document exists covering: VPS provisioning, runtime setup, clone/install/migrate/build steps, `.env.production` setup, pm2 configuration, backup cron setup, and verification checklist
**And** the runbook has been validated end-to-end by following it on the actual VPS (not just written theoretically)

**Given** the engine should confirm it's operational after deployment
**When** the engine starts on the VPS
**Then** the Telegram daily test alert fires successfully (confirming Telegram bot token, chat ID, and network egress)
**And** the engine runs stable for at least 10 minutes with no errors in `pm2 logs`
**And** the health endpoint responds correctly via SSH tunnel

**Sequencing:** Requires 6.5.0 complete. Can run in parallel with 6.5.1 and 6.5.3. Must complete before 6.5.5.

**Previous Story Intelligence:**
- Architecture doc specifies Hetzner VPS with SSH tunnel access (no public ports beyond SSH)
- Backup strategy from architecture: hourly pg_dump, 7-day rolling window
- Telegram daily test alert implemented in Story 6.1 via `@Cron` — confirms connectivity without manual testing
- Paper trading connector from Epic 5.5 decorates real connectors — platform API connections are real, only execution is simulated

### Story 6.5.2a: Polymarket Batch Order Book Migration & Health Log Optimization

As an operator,
I want Polymarket order books fetched via a single batch API call instead of sequential per-pair requests,
So that rate limit consumption drops from O(n) to O(1), ingestion latency improves ~6x, and all order books share a consistent timestamp for accurate arbitrage detection.

**Acceptance Criteria:**

**Given** the Polymarket connector has multiple configured token IDs
**When** `DataIngestionService.ingestCurrentOrderBooks()` runs a polling cycle
**Then** all Polymarket order books are fetched via a single `clobClient.getOrderBooks(params: BookParams[])` call
**And** only 1 rate limit read token is consumed per cycle (regardless of pair count)
**And** each returned `OrderBookSummary` is normalized via `normalizePolymarket()` into `NormalizedOrderBook`
**And** all normalized books are persisted and events emitted as before

**Given** the batch `getOrderBooks()` call returns results
**When** some token IDs return empty or missing order books
**Then** the missing tokens are logged at warning level with their token IDs
**And** successfully returned order books are still processed normally
**And** no error is thrown for partial results

**Given** the batch `getOrderBooks()` call fails entirely (network error, rate limit, 5xx)
**When** the error is caught
**Then** a `PlatformApiError` is thrown with appropriate error code and retry strategy
**And** the error is handled identically to the current single-call error path

**Given** `PlatformHealthService.publishHealth()` runs on its 30-second cron
**When** a platform's health status has NOT changed since the last tick
**Then** no `platform_health_logs` row is written to the database
**And** the in-memory status and event emission continue as before

**Given** `PlatformHealthService.publishHealth()` runs on its 30-second cron
**When** a platform's health status HAS changed (e.g., `healthy → degraded`)
**Then** a `platform_health_logs` row IS written with the new status
**And** the appropriate domain event is emitted as before

**Given** the Polymarket connector exposes `getOrderBooks(contractIds: string[])`
**When** inspecting the `IPlatformConnector` interface
**Then** the interface is unchanged — `getOrderBooks()` is a Polymarket-specific method, not on the shared interface
**And** `DataIngestionService` calls it via a typed reference to `PolymarketConnector`

**Technical Notes:**
- `@polymarket/clob-client` SDK method: `getOrderBooks(params: BookParams[]): Promise<OrderBookSummary[]>` — supports up to 500 tokens per request
- Rate limiter: `acquireRead()` once per batch, not per token
- Health log guard: reuse existing `previousStatus` map in `PlatformHealthService` for the persistence condition
- Existing single `getOrderBook()` method remains for any future single-fetch needs (e.g., retry of individual token)

**Sequencing:** Requires 6.5.0 and 6.5.2 complete. Must complete before 6.5.3. This ensures all subsequent validation stories run against the production-grade batch pipeline.

**Previous Story Intelligence:**
- Migration analysis doc: `docs/polymarket-batch-orderbook-migration.md` — contains full problem analysis, SDK confirmation, and performance comparison
- Sprint Change Proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-02-28.md`
- Source files: `src/connectors/polymarket/polymarket.connector.ts` (lines 211-274), `src/modules/data-ingestion/data-ingestion.service.ts` (lines 125-259), `src/modules/data-ingestion/platform-health.service.ts` (lines 41-144)
- Rate limiter: `src/common/utils/rate-limiter.ts` — no changes needed
- Current utilization: 91.8% with 8 pairs (8 tokens/cycle); target: ~12.5% (1 token/cycle)

### Story 6.5.3: Validation Framework & Go/No-Go Criteria

As an operator,
I want a defined measurement framework with explicit success thresholds before starting live observation,
So that validation phases produce structured, evaluable data rather than anecdotal impressions.

**Acceptance Criteria:**

**Given** Phase 1 (read-only detection) needs quantitative evaluation
**When** the metrics collection template for Phase 1 is designed
**Then** the template captures per-cycle: detection timestamp, opportunities found, edge values, detection latency (ms), platform health status, order book depth at detection time
**And** the template captures daily aggregates: total cycles, total opportunities, edge distribution (min/median/max/mean), latency percentiles (p50/p95/p99), platform uptime percentage
**And** the collection mechanism is defined (structured log parsing, database queries, or dedicated metrics endpoint)

**Given** Phase 2 (paper execution) adds execution and monitoring dimensions
**When** the metrics collection template for Phase 2 is designed
**Then** the template extends Phase 1 metrics with: paper orders submitted, fill simulation results, position lifecycle events (open → monitor → exit), exit trigger types, single-leg detections, risk budget consumption
**And** monitoring validation metrics are included: Telegram alerts sent (by severity), CSV log entries written, daily summary generation, audit trail hash chain length
**And** resilience metrics are included: memory usage trend, connection recovery events, graceful shutdown/restart count, reconciliation results

**Given** validation requires daily human observation alongside automated metrics
**When** the observation log format is established
**Then** the format includes: date, observer, key observations (narrative), anomalies noted, decisions made, environment changes, and open questions
**And** the format is lightweight enough to fill in 10 minutes per day (not a bureaucratic exercise)

**Given** the PRD defines quantitative success targets
**When** go/no-go criteria are formalized for Phase 1 → Phase 2 gate
**Then** criteria include:
- Opportunity detection frequency: ≥8 per week (PRD target) — or documented explanation if lower with threshold adjustment proposal
- Detection latency: <500ms per cycle (NFR-P3)
- Zero unhandled crashes during 48h run
- Both platform connections maintained >95% uptime
**And** each criterion has a clear pass/fail definition (no subjective judgment)
**And** a "conditional proceed" path is defined for criteria that partially fail (e.g., 5 opportunities instead of 8 — investigate thresholds, don't auto-abort)

**Given** the PRD defines end-of-validation success gates
**When** go/no-go criteria are formalized for Phase 2 → Epic 7 gate
**Then** criteria include:
- Zero unhandled crashes during 5-day run
- Telegram alerts verified functional (at least one of each severity level observed or manually triggered)
- CSV logs and daily summaries populated correctly with no missing fields beyond documented N/A gaps
- Audit trail hash chain verified intact via `verifyChain()`
- Reconciliation successful after at least one intentional restart
- Single-leg exposure events: <3 requiring manual intervention (PRD success gate)
**And** each criterion has a clear pass/fail definition

**Given** the validation framework needs stakeholder sign-off before the clock starts
**When** all templates and criteria are complete
**Then** the complete validation framework (metrics templates, observation log format, go/no-go criteria for both gates) is reviewed and approved by Arbi
**And** approval is recorded with date

**Sequencing:** Requires 6.5.0 complete. Can run in parallel with 6.5.1 and 6.5.2. Must complete before 6.5.5.

**Previous Story Intelligence:**
- PRD MVP Success Gate section defines quantitative targets — use as source of truth for thresholds
- NFR-P3 specifies <500ms detection latency at p95
- Story 6.2 implemented `EventConsumerService` with severity classification (27 events) — use as reference for "at least one of each severity level"
- Story 6.3 CSV trade log has 5 N/A columns due to event payload gaps — document these as known gaps, not validation failures
- Story 6.5 audit trail `verifyChain()` already exists — just needs to be run against real data

### Story 6.5.4: WebSocket Stability & Structured Log Payloads

As an operator,
I want the Polymarket WebSocket connection to stay alive during idle periods, health status to not flap on transient reconnects, and all event log entries to show real structured values instead of `[object]`,
So that paper trading validation runs against a stable, observable system where health reflects real connectivity problems and logs are usable for diagnosis.

**Acceptance Criteria:**

**Given** the Polymarket WebSocket client is connected
**When** no market data arrives for an extended idle period
**Then** the client sends periodic ping frames (every 30s) to keep the connection alive
**And** the server does not close the connection with code 1006 due to inactivity

**Given** the WebSocket connection drops and reconnects within one health check cycle (30s)
**When** the platform health service evaluates health on the next tick
**Then** the platform is NOT marked as degraded (transient reconnect is tolerated)
**And** the degradation protocol is NOT activated

**Given** the WebSocket connection has been down for 2+ consecutive health check ticks (~60s of confirmed timeout)
**When** the platform health service evaluates health
**Then** the degradation protocol IS activated with reason `websocket_timeout`
**And** degradation is only cleared after 2+ consecutive healthy observations

**Given** any domain event is emitted with Date, array, or nested object fields
**When** `EventConsumerService.summarizeEvent()` processes the event for logging
**Then** Date values appear as ISO 8601 strings (e.g. `2026-03-01T12:00:00.000Z`)
**And** arrays appear as actual arrays (e.g. `["polymarket"]`)
**And** nested plain objects appear as serialized objects (e.g. `{"pollingCycleCount": 3, "reason": "websocket_timeout"}`)
**And** no field in the log output contains the literal string `[object]`

**Sequencing:** Requires 6.5.3 complete. Must complete before 6.5.5.

**Previous Story Intelligence:**
- Story 2.4 implemented `DegradationProtocolService` with activate/deactivate lifecycle and `DegradationProtocolActivatedEvent`/`DegradationProtocolDeactivatedEvent` events — both event classes use Date instances and arrays that currently serialize as `[object]`
- Story 2.2 implemented `PolymarketWebSocketClient` with exponential backoff reconnect (`RETRY_STRATEGIES.WEBSOCKET_RECONNECT`: 1s initial, 60s max, 2x multiplier) — reconnect logic is sound, just missing keepalive ping
- Story 1.4 implemented `PlatformHealthService` with 30s cron tick, 60s staleness threshold, 81s WebSocket timeout threshold — single-observation triggers cause flapping
- Story 6.2 implemented `EventConsumerService.summarizeEvent()` with the `[object]` fallback at line 311 — the `str()` helper only handles primitives, not the summarize path
- `RETRY_STRATEGIES.WEBSOCKET_RECONNECT` in `common/errors/platform-api-error.ts` — `maxRetries: Infinity` confirms reconnect is meant to be permanent

### Story 6.5.5k: Exit Path Depth Verification & Partial Fill Handling

As an operator,
I want exit orders to be depth-verified and partial fills handled correctly,
So that the system never orphans untracked contracts, never corrupts risk state with incorrect P&L, and exits are sized to what the order book can actually fill.

**Acceptance Criteria:**

**Given** an exit order returns `status: 'partial'` (e.g., 300 of 400 contracts filled)
**When** realized P&L is calculated
**Then** P&L uses the actual exit fill sizes (`filledQuantity`) from both legs, not the entry fill sizes
**And** exit fees are calculated on the actual traded notional (exit fill size x exit fill price)
**And** capital returned to the risk manager reflects only the exited portion

**Given** an exit order returns `status: 'partial'` on either leg
**When** the exit completes with unfilled contracts remaining
**Then** the position transitions to `EXIT_PARTIAL` (not `CLOSED`)
**And** a `SingleLegExposureEvent` is emitted with remainder details and operator action recommendations
**And** capital remains reserved in the risk budget until the operator fully resolves the position
**And** the exit monitor's next polling cycle does NOT re-evaluate this position (confirmed: queries only `OPEN` status)

**Given** an exit threshold is triggered and `executeExit()` is called
**When** exit orders are about to be submitted
**Then** fresh order books are fetched for both legs (intentional second fetch — book may have changed since evaluation)
**And** available depth is calculated at the close price or better on each side
**And** if either side has zero depth, the exit is deferred to the next cycle (position stays `OPEN`)
**And** exit sizes are capped to available depth and equalized across both legs: `exitSize = min(primaryDepth, secondaryDepth, entryFillSize)`

**Given** the threshold evaluator is computing close prices for a position
**When** `getClosePrice()` is called with a position size
**Then** the returned price is a VWAP (volume-weighted average price) across order book levels needed to fill the position size
**And** if the book cannot fill the full position, the VWAP covers available depth (pessimistic signal)
**And** if `getClosePrice()` is called without a position size, it returns top-of-book price (backward compatible)

**Given** the architecture document describes the exit-management hot path
**When** this story is complete
**Then** the hot path diagram is updated to note depth-verified exit sizing and partial fill handling

**Implementation Order:**
1. Fix P&L to use exit fill sizes (P0 — prerequisite for everything else)
2. Partial fills transition to EXIT_PARTIAL (P0 — depends on correct P&L)
3. Pre-exit depth check + deferral (P1 — builds on partial fill handling)
4. VWAP-aware close pricing (P1 — independent but logically follows)
5. Architecture doc update (P2 — last)

**Design Decisions:**
- No partial capital release until operator fully resolves — conservative, prevents risk budget drift
- No auto-retry of unfilled remainder — operator decides via existing retry-leg/close-leg endpoints (Story 5.3)
- No minimum fill ratio for exits (unlike entry's 25%) — at exit time, any reduction in exposure is beneficial
- No edge re-validation at exit — exit decision already made; depth check is about execution feasibility
- Cross-leg equalization prevents creating directional exposure from asymmetric partial fills
- Double order book fetch in executeExit() is intentional freshness — must be commented in code

**Sequencing:** After 6-5-5j (take-profit negative threshold fix), before 6-5-5 (paper execution validation).

**Previous Story Intelligence:**
- Story 5.4 specified that partial exits transition to `exit_partial` with `SingleLegExposureEvent` — this story implements that specified-but-missing behavior
- Story 6.5.5b implemented depth-aware sizing for entry (`getAvailableDepth()`) — same pattern adapted for exit
- Story 6.5.5h implemented cross-leg equalization for entry — same principle applied to exit sizing
- `EXIT_PARTIAL` already exists in `PositionStatus` enum — no schema change needed
- Exit monitor queries only `OPEN` positions — `EXIT_PARTIAL` positions are not re-evaluated (no double-exit risk)
- Kalshi connector returns `status: 'partial'` when `order.remaining_count > 0` — this is a reachable production scenario
- FR-EX-03 mandates depth verification "before placing any order" — applies universally, not just entry
- FR-EM-03 (Phase 1) lists "liquidity deterioration" as exit criterion #5 — VWAP infrastructure is directly reusable for Epic 10 Story 10.2

**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md`

**DoD Gates:**
- All existing tests pass (`pnpm test`), `pnpm lint` reports zero errors
- New test cases cover: partial fill P&L, EXIT_PARTIAL transition, depth deferral, VWAP calculation, cross-leg equalization
- No `decimal.js` violations introduced
- Architecture doc updated

### Story 6.5.5: Paper Execution Validation (5 days)

As an operator,
I want to run the full trading pipeline in paper mode for 5 days against live markets,
So that I can validate the complete position lifecycle, monitoring stack, and system resilience before considering production deployment.

**Acceptance Criteria:**

**Given** Stories 6.5.0, 6.5.1, 6.5.2, 6.5.2a, 6.5.3, and 6.5.4 are complete
**When** paper execution is enabled on the VPS
**Then** the engine runs the full pipeline: detection → risk validation → paper execution → position monitoring → exit
**And** both platforms operate in paper mode (confirmed via startup logs showing `PaperTradingConnector` active for each platform)

**Given** position lifecycle is the core behavior under validation
**When** paper trades execute over the 5-day window
**Then** at least one complete position lifecycle is observed: opportunity detected → risk validated → orders submitted → fills simulated → position opened → exit threshold hit → exit orders submitted → position closed
**And** if no opportunities reach execution (edge below threshold on all pairs), this is documented with analysis — the detection-to-execution funnel drop-off is itself a finding
**And** position state transitions are verified against the expected state machine (PENDING → OPEN → MONITORING → CLOSING → CLOSED)

**Given** single-leg exposure detection is a critical safety mechanism
**When** paper execution runs for 5 days
**Then** any single-leg events are detected within 5 seconds (PRD requirement) and Telegram alerts fire
**And** single-leg exposure events total <3 requiring manual intervention (PRD success gate)
**And** if single-leg events occur, the resolution path (operator action or automatic timeout) is documented

**Given** risk management must constrain paper execution as it would live execution
**When** paper trades execute
**Then** position sizing respects 3% bankroll limit per pair
**And** daily loss limits are tracked (even for simulated P&L)
**And** compliance gate validates each opportunity before execution (Story 6.4)
**And** no `COMPLIANCE_BLOCKED` events on configured pairs (pairs were pre-verified in 6.5.1)

**Given** the full monitoring stack must be validated on live infrastructure
**When** the 5-day window completes
**Then** Telegram alerts have been received for at least: one execution event, one risk-related event, and one platform health event (or manually triggered if not organically observed)
**And** CSV trade logs contain entries for all paper trades with correct field population (known N/A gaps from event payload limitations documented, not treated as failures)
**And** daily summary generation has produced at least 4 daily summaries (one per completed day)
**And** audit trail hash chain is verified intact via `verifyChain()` at end of validation

**Given** the system must demonstrate resilience over sustained operation
**When** resilience scenarios are tested during the 5-day window
**Then** at least one intentional graceful shutdown + restart is performed with positions open, and reconciliation correctly recovers state
**And** memory usage is sampled daily (via `process.memoryUsage()` or pm2 metrics) — no upward trend indicating a leak
**And** any platform connection drops during the 5 days are recovered automatically with reconnection logged

**Given** the 5-day window produces extensive operational data
**When** each day completes
**Then** daily observation log entries are recorded per the format from Story 6.5.3
**And** metrics are collected per the Phase 2 template from Story 6.5.3
**And** anomalies or unexpected behaviors are documented immediately, not deferred to the report

**Given** Phase 2 completion gates the validation report
**When** the 5-day observation period completes
**Then** go/no-go criteria from Story 6.5.3 (Phase 2 → Epic 7 gate) are evaluated with pass/fail for each criterion
**And** all collected metrics, observation logs, and anomaly notes are organized for Story 6.5.6 (report compilation)

**Sequencing:** Requires 6.5.4 complete. Gates 6.5.6.

**Previous Story Intelligence:**
- Paper trading connectors from Epic 5.5 simulate fills with configurable latency and slippage — fill parameters in `.env.production`
- Exit monitoring from Story 5.4 uses fixed thresholds — exits trigger when edge erodes past configured percentage
- Single-leg detection from Story 5.2 fires within 5 seconds — validated in unit tests but never against live timing
- Reconciliation from Story 5.5 loads open positions from DB on startup — the restart-with-open-positions test is the real-world proof
- CSV trade log N/A columns (Story 6.3): `contractId`, `fees`, `gas` on `OrderFilledEvent` — known gap, deferred to Epic 8 enrichment
- Compliance gate (Story 6.4) runs in-memory before depth verification in `ExecutionService.execute()` — zero-latency check

### Story 6.5.6: Validation Report & Epic 7 Readiness

As an operator,
I want a structured validation report that synthesizes all observation data into a go/no-go recommendation,
So that the decision to proceed with Epic 7 and production deployment is evidence-based, not assumption-based.

**Acceptance Criteria:**

**Given** Phase 1 and Phase 2 observation data has been collected over 7 days
**When** the validation report is compiled
**Then** the report contains the following sections:

1. **Executive Summary** — one-paragraph verdict: proceed, proceed with conditions, or halt
2. **Metrics Summary vs PRD Targets** — table format, each metric with target value, observed value, and pass/fail/conditional
3. **Detection Analysis** — opportunity frequency, edge distribution, per-pair breakdown, detection-to-execution funnel (opportunities detected → risk-validated → executed → filled → position opened)
4. **Execution Analysis** — paper trade count, position lifecycle completions, fill simulation behavior, exit trigger distribution, single-leg events
5. **Monitoring Stack Validation** — Telegram alerts (count by severity, delivery reliability), CSV logs (completeness, known gaps), daily summaries (generation consistency), audit trail (hash chain integrity result)
6. **Resilience Observations** — restart/reconciliation results, memory trend, connection recovery events, uptime percentages
7. **Anomalies & Surprises** — anything that deviated from expectations, whether positive or negative
8. **Observation Narrative** — what we saw, what assumptions held, what assumptions broke, what surprised us
9. **Epic 7 Scope Recommendations** — specific adjustments to dashboard scope informed by real operational data
10. **Go/No-Go Recommendation** — explicit recommendation with conditions if applicable

**Given** the report must be actionable, not just descriptive
**When** the go/no-go recommendation is written
**Then** it explicitly addresses each Phase 2 gate criterion from Story 6.5.3 with evidence
**And** if recommending "proceed with conditions," each condition is specific and time-bounded (not open-ended)
**And** if recommending "halt," the report identifies what must change and proposes a re-validation plan

**Given** the detection-to-execution funnel is critical for production viability
**When** funnel analysis is performed
**Then** each stage of the funnel is quantified: opportunities detected → passed edge threshold → passed risk validation → execution attempted → fills simulated → position opened → position exited
**And** drop-off at each stage is documented with root cause analysis

**Given** Epic 7 scope should be informed by validation findings
**When** scope recommendations are written
**Then** at least 3 specific, evidence-backed recommendations are provided for Epic 7 prioritization
**And** recommendations distinguish between "must have based on validation findings" and "nice to have based on operational observations"

**Given** the report is the primary decision artifact for production readiness
**When** the report is complete
**Then** the report is saved to `{implementation_artifacts}/paper-trading-validation-report.md`
**And** Arbi reviews and records a decision: proceed to Epic 7, proceed with conditions, or halt with re-validation plan

**Sequencing:** Requires 6.5.5 complete. Final story in Epic 6.5. Approval of this report gates Epic 7 planning.

**Previous Story Intelligence:**
- Daily observation logs provide the narrative backbone
- Metrics templates from Story 6.5.3 define the exact data points to report on — no ad hoc metrics
- Event payload N/A gaps (Epic 6 retro carry-forward) — report should note which gaps impacted validation data quality, feeding into Epic 8 enrichment prioritization
- PRD MVP Success Gate section is the authoritative reference for target values

### Epic 7: Operator Dashboard & Advanced Monitoring (Phase 1)
Operator has a lightweight web dashboard for 2-minute morning scans, weekly performance metrics, contract matching approval interface, and manual intervention capabilities.
**FRs covered:** FR-MA-04, FR-MA-05, FR-MA-06, FR-MA-09

## Epic 7: Operator Dashboard & Advanced Monitoring (Phase 1)

Operator has a lightweight web dashboard for 2-minute morning scans, weekly performance metrics, contract matching approval interface, and manual intervention capabilities.

### Story 7.1: Dashboard Project Setup & System Health View

As an operator,
I want a web dashboard showing system health, P&L, and open positions at a glance,
So that my morning scan takes 2 minutes instead of digging through CSV files.

**Acceptance Criteria:**

**Given** the dashboard project is scaffolded (separate repo: pm-arbitrage-dashboard)
**When** I open the dashboard in a browser
**Then** it displays: system health status (green/yellow/red per platform), trailing 7-day P&L, execution quality ratio, open position count, and active alert count (FR-MA-04)

**Given** the dashboard connects to the backend
**When** the WebSocket connection is established
**Then** real-time updates push to the UI (position changes, alert updates, health status changes)
**And** the dashboard authenticates via Bearer token (same static token from MVP)

**Given** the dashboard project is set up
**When** I inspect the codebase
**Then** it uses Vite + React 19 + React Query (TanStack Query) + shadcn/ui
**And** REST data is fetched via a typed client generated from the backend's Swagger spec (`/api/docs-json`)
**And** WebSocket events are managed via a context provider that invalidates/patches React Query cache
**And** Docker Compose is updated to include the dashboard container (nginx serving static build)

**Given** the backend has accumulated endpoints across Epics 1-6 (health, positions, risk override, single-leg resolution, trade exports, tax reports, matches)
**When** the Swagger spec is generated
**Then** all existing endpoints have proper `@nestjs/swagger` decorators (ApiTags, ApiOperation, ApiResponse, ApiBody, ApiParam)
**And** any endpoints missing decorators are updated in this story since the dashboard is the first consumer requiring complete API documentation

### Story 7.2: Open Positions & P&L Detail View

As an operator,
I want to see all open positions with current edge, P&L, and exit proximity,
So that I can quickly assess portfolio state and identify positions needing attention.

**Acceptance Criteria:**

**Given** the operator navigates to the positions view
**When** positions load
**Then** each position shows: contract pair names, entry prices, current prices, initial edge, current edge, unrealized P&L, time to resolution, exit threshold proximity (% to take-profit, % to stop-loss)

**Given** a position's status changes (filled, exit triggered, single-leg exposed)
**When** the WebSocket pushes the update
**Then** the positions view updates in real-time without page refresh (NFR-P4: <2 seconds)

**Given** the operator wants to manually close a position
**When** they click a close button on a position
**Then** a confirmation dialog shows estimated P&L and asks for rationale
**And** on confirmation, `POST /api/positions/:id/close-leg` is called (reusing Epic 5 endpoint)

### Story 7.3: Contract Matching Approval Interface

As an operator,
I want to review pending contract matches with side-by-side resolution criteria comparison,
So that I can make informed approval decisions quickly.

**Acceptance Criteria:**

**Given** pending matches exist (confidence <85% in Phase 1, or new manual pairs)
**When** the operator opens the matches view
**Then** each pending match displays: both contract descriptions side-by-side, resolution criteria from both platforms, confidence score (if available), and similar historical matches from knowledge base (FR-MA-05)

**Given** the operator reviews a match
**When** they approve with rationale text
**Then** `POST /api/matches/:id/approve` is called with the rationale
**And** the match is logged with operator_rationale and approval_timestamp (FR-MA-06)
**And** the match disappears from the pending queue

**Given** the operator rejects a match
**When** they click reject with rationale
**Then** `POST /api/matches/:id/reject` is called
**And** the rejection is logged and the pair is excluded from detection

### Story 7.4: Weekly Performance Metrics & Trends

As an operator,
I want weekly performance summaries with key metrics and trend analysis,
So that I can track whether the system is improving or degrading over time.

**Acceptance Criteria:**

**Given** the operator navigates to the performance view
**When** the weekly summary loads
**Then** it displays: autonomy ratio (automated decisions ÷ manual interventions), average slippage vs. modeled, opportunity frequency (detected, filtered, executed), P&L by week, and hit rate (FR-MA-09)

**Given** multiple weeks of data exist
**When** trend analysis runs
**Then** 4-week rolling averages are shown for opportunity frequency, edge captured, and slippage
**And** alert indicators highlight if opportunity frequency drops below baseline (8-12/week)
**And** edge degradation leading indicators are surfaced (time-to-convergence trend, order book depth trend)

### Epic 7.5: Position Lifecycle Improvements & Dashboard Enrichment
Operator can manage the full position lifecycle — including partially exited positions — with comprehensive visibility into history, details, balance, and risk/reward projections. Discovered during paper trading validation (Story 6.5.5): EXIT_PARTIAL positions stall permanently, manual close fails for OPEN positions, and dashboard lacks operational depth.
**FRs reinforced:** FR-EM-01 (fixed threshold exits — extended to EXIT_PARTIAL remainder), FR-EX-06 (operator close via dashboard), FR-MA-04 (dashboard enrichment)
**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-08.md`

## Epic 7.5: Position Lifecycle Improvements & Dashboard Enrichment

Operator can manage the full position lifecycle — including partially exited positions — with comprehensive visibility into history, details, balance, and risk/reward projections.

### Story 7.5.1: EXIT_PARTIAL Re-evaluation & Dual-Platform Close Endpoint

As an operator,
I want partially exited positions to be automatically re-evaluated for exit by the exit monitor, and I want a new endpoint to manually close any open position across both platforms,
So that positions never stall permanently and I always have a manual override for the full position lifecycle.

**Acceptance Criteria:**

**EXIT_PARTIAL Re-evaluation:**

**Given** a position is in `EXIT_PARTIAL` status with unfilled remainder contracts
**When** the exit monitor's polling cycle runs
**Then** the position is included in the evaluation query alongside `OPEN` positions
**And** the residual contract size is computed as `entryFillSize - alreadyExitedFillSize` per leg
**And** `alreadyExitedFillSize` per leg is the sum of `filledQuantity` across all exit orders for that leg's platform (consistent with Story 6.5.5k's P&L source-of-truth: exit fills from Order records)
**And** a shared `getResidualSize(position)` utility computes this, aggregating across all exit orders per leg, reusable by both the exit monitor and the close endpoint
**And** all downstream logic (threshold evaluation, depth checks, VWAP close pricing, cross-leg equalization) operates on the residual sizes, not the original entry sizes

**Given** an EXIT_PARTIAL position's residual contracts meet an exit threshold (SL, TP, or time-based)
**When** exit orders are submitted for the remainder
**Then** exit sizes are `min(residualPrimaryDepth, residualSecondaryDepth, residualEntryFillSize)`
**And** if both legs fill for the full remainder, the position transitions to `CLOSED` with aggregate P&L (sum of partial exit P&L + remainder exit P&L)
**And** if the remainder only partially fills again, the position stays `EXIT_PARTIAL` with an updated residual

**Given** an EXIT_PARTIAL position has zero depth on either side
**When** the exit monitor evaluates it
**Then** the exit is deferred to the next cycle (same pattern as OPEN positions with no depth)

**Dual-Platform Close Endpoint:**

**Given** a position is in `OPEN` or `EXIT_PARTIAL` status
**When** the operator calls `POST /api/positions/:id/close` with optional `{ rationale: string }`
**Then** the system fetches fresh order books for both platforms
**And** submits opposing trades on both legs simultaneously (sell what was bought, buy what was sold) using best available prices
**And** for EXIT_PARTIAL positions, the close operates on the residual contract sizes (via `getResidualSize()`)
**And** on success, the position transitions to `CLOSED` with realized P&L
**And** risk budget is fully released (capital deployed decremented, position count decremented, pair removed from active tracking)

**Given** one leg of the manual close fills but the other fails
**When** a single-leg exposure occurs during manual close
**Then** the position transitions to `SINGLE_LEG_EXPOSED` (not EXIT_PARTIAL — this is a fresh execution attempt)
**And** a `SingleLegExposureEvent` is emitted with full context, recommended actions, and `origin: 'manual_close'` to distinguish from automated exit failures
**And** the operator can resolve via existing retry-leg/close-leg endpoints (Story 5.3)

**Given** the position is in any status other than `OPEN` or `EXIT_PARTIAL`
**When** the operator calls `POST /api/positions/:id/close`
**Then** the endpoint returns 422 with error "Position is not in a closeable state"

**Implementation Notes:**
- New `PositionManagementController` in `src/dashboard/` with `POST /api/positions/:id/close`
- New `IPositionCloseService` interface in `common/interfaces/` — injected into dashboard controller via token (same pattern as `IPriceFeedService` from Story 7.2)
- `PositionCloseService` implementation in `src/modules/execution/` coordinates dual-platform close via `IPlatformConnector`
- `getResidualSize(position)` utility in `common/utils/` or co-located with position repository — aggregates exit order `filledQuantity` per leg per platform
- Exit monitor query change: `findByStatusWithOrders(['OPEN', 'EXIT_PARTIAL'], isPaper)` — repository method accepts array of statuses
- All financial math uses `decimal.js` — residual size = `new Decimal(entryFillSize).minus(sumOfExitFillSizes)`
- Existing `close-leg` endpoint remains untouched — it serves a different purpose (single-platform resolution for SINGLE_LEG_EXPOSED)

**DoD Gates:**
- All existing tests pass (`pnpm test`), `pnpm lint` reports zero errors
- New test cases cover: EXIT_PARTIAL re-evaluation with residual sizes, depth deferral on residual, aggregate P&L across multiple partial exits, dual-platform close for OPEN, dual-platform close for EXIT_PARTIAL residual, single-leg failure during manual close (with origin context), status guard (reject non-closeable statuses)
- No `decimal.js` violations introduced

### Story 7.5.2: Position History, Details Page & Balance Overview

As an operator,
I want to see my full position history, drill into detailed breakdowns of any position, see my available vs. blocked capital at a glance, and assess risk/reward via projected SL/TP P&L,
So that I can understand how the system has been performing over time and make informed decisions about open positions.

**Dependency Note:** The bulk of this story (position history queries, detail page, balance overview, audit trail index) has no dependency on Story 7.5.1 and can be developed in parallel. Only the SL/TP projected P&L for EXIT_PARTIAL positions depends on `getResidualSize()` from 7.5.1.

**Acceptance Criteria:**

**Position History:**

**Given** the operator navigates to the positions view
**When** the page loads
**Then** a tab or toggle allows switching between "Open Positions" (current behavior) and "All Positions" (includes CLOSED, EXIT_PARTIAL, SINGLE_LEG_EXPOSED, RECONCILIATION_REQUIRED)
**And** closed positions show: pair name, entry/exit prices, realized P&L, exit type (stop_loss / take_profit / time_based / manual), open/close timestamps, mode (paper/live)
**And** the list is sorted by most recently updated, with pagination or virtual scrolling for large datasets

**Given** the backend needs to serve position history
**When** `GET /api/positions` is called
**Then** it accepts optional query params: `status` (filter by one or more statuses), `isPaper` (boolean), `limit`, `offset`
**And** closed positions include their associated orders (entry + exit) in the response DTO
**And** the enrichment service computes realized P&L for closed positions from order fill records (same source-of-truth as 6.5.5k: `filledQuantity` × `fillPrice` on orders, never from `position.entryPrices`)

**Position Details Page:**

**Given** the operator clicks on any position row (open or closed)
**When** the detail page loads
**Then** it displays a comprehensive breakdown:
- **Entry section:** Number of contracts per leg, entry prices (requested vs. fill), entry timestamps, entry slippage (fill price - requested price), capital invested (sum of both legs: fillSize × fillPrice + fees)
- **Current state section (for open positions):** Current prices on both platforms, current edge, unrealized P&L, time held
- **Exit section (for closed/partially exited):** Exit prices (requested vs. fill), exit timestamps, exit type and trigger reason, exit slippage, realized P&L breakdown (gross P&L - Kalshi fees - Polymarket fees)
- **Order history:** Chronological list of all orders associated with this position (entry, exit attempts, partial fills, retry attempts) with status, timestamps, and fill details
- **Audit trail:** Key events from audit_logs filtered by this position's pair_id (opportunity identified, risk reserved, orders filled, exit triggered, single-leg events)

**Given** the detail page needs backend data
**When** `GET /api/positions/:id/details` is called
**Then** the response includes: position record, all associated orders, entry reasoning (from the audit log's `risk.budget.reserved` event details), and capital breakdown
**And** the audit trail events are fetched from audit_logs filtered by pair_id with relevant event types only (not orderbook.updated or detection spam)

**Audit Trail Index (mandatory):**

**Given** the audit_logs table has 133K+ rows and growing
**When** Story 7.5.2 is implemented
**Then** a Prisma migration creates a functional btree index: `CREATE INDEX idx_audit_logs_pair_id ON audit_logs USING btree ((details->>'pairId'))`
**And** the detail page's audit trail query uses this index path for performant filtering

**Balance Overview:**

**Given** the operator views the main dashboard
**When** the system health / overview section loads
**Then** it displays: total bankroll, deployed capital (blocked), available capital (bankroll - deployed - reserved), reserved capital (pending reservations not yet committed), and open position count
**And** these values are sourced from the risk state endpoint — bankroll from engine environment config (single source of truth), deployed/reserved/count from the risk_states table

**Given** the backend needs to serve balance data
**When** `GET /api/risk/state` is called (extended existing endpoint)
**Then** the response additionally includes: `totalBankroll` (from engine config), `availableCapital` (computed: bankroll - deployed - reserved)
**And** bankroll is never hardcoded in the frontend — always fetched from the API to prevent drift if capital is topped up

**SL/TP Projected P&L:**

**Given** a position is in OPEN or EXIT_PARTIAL status
**When** the positions table renders
**Then** each position row displays projected P&L at the stop-loss threshold and projected P&L at the take-profit threshold
**And** these values are computed by the enrichment service using: current close prices at SL/TP edge levels, position sizes (residual for EXIT_PARTIAL via `getResidualSize()`), and estimated fees
**And** the display format shows both values inline (e.g., "SL: -$2.14 / TP: +$1.87") so the operator can assess risk/reward at a glance

**Given** the enrichment service computes SL/TP projections
**When** the backend returns position data via WebSocket or REST
**Then** the enriched DTO includes `projectedSlPnl` and `projectedTpPnl` as decimal values
**And** the computation lives in the enrichment service (not the threshold evaluator) to keep the trading hot path clean — same service that already computes exit proximity and current P&L

**Implementation Notes:**
- Position history and details leverage existing position repository with expanded query capabilities — no new tables
- The detail page's audit trail uses the new btree index on `(details->>'pairId')` for performant JSONB filtering
- Balance extends existing `GET /api/risk/state` response DTO — bankroll from `ConfigService`, everything else from risk_states table
- SL/TP projected P&L in `PriceFeedService` enrichment — natural extension of existing enrichment pass that already has access to close prices, position data, and fee rates
- Frontend: new route `/positions/:id` for detail page, tab component on positions list, balance card on dashboard home
- All financial math uses `decimal.js`

**DoD Gates:**
- All existing tests pass (`pnpm test`), `pnpm lint` reports zero errors
- New test cases cover: position history query with status filters, detail page DTO assembly with orders and audit events, audit trail index existence verification, balance computation (bankroll - deployed - reserved), SL/TP P&L projection with fee estimation, residual-size projections for EXIT_PARTIAL
- No `decimal.js` violations introduced
- Generated API client regenerated after new/modified endpoints

### Story 7.5.3: Close All Positions & Updated Close UX

As an operator,
I want a "Close All Positions" bulk action and the existing per-position close button updated to use the new dual-platform close endpoint,
So that I can quickly exit all positions in an emergency and the close button actually works for OPEN positions.

**Sequencing:** Depends on both 7.5.1 (close endpoint) and 7.5.2 (enrichment for projected close P&L in dialog). Must be implemented last.

**Acceptance Criteria:**

**Updated Per-Position Close Button:**

**Given** the operator clicks "Close" on a position in OPEN or EXIT_PARTIAL status
**When** the confirmation dialog appears
**Then** it shows: pair name, current P&L, projected close P&L at current market prices (from enrichment), and a rationale text field
**And** on confirmation, the frontend calls `POST /api/positions/:id/close` (the new dual-platform endpoint from Story 7.5.1) instead of `POST /api/positions/:id/close-leg`
**And** on success, the position row updates in real-time via WebSocket to reflect CLOSED status
**And** on failure (single-leg exposure), the position row updates to SINGLE_LEG_EXPOSED and the operator sees the error context in a toast notification with a link to the position detail page

**Given** a position is in CLOSED, SINGLE_LEG_EXPOSED, or RECONCILIATION_REQUIRED status
**When** the positions table renders
**Then** no "Close" button is shown for that position

**Close All Positions:**

**Given** the operator has one or more positions in OPEN or EXIT_PARTIAL status
**When** they click "Close All Positions"
**Then** a confirmation dialog shows: total number of positions to close, aggregate current P&L across all closeable positions, and a warning that this will attempt to close all positions at current market prices
**And** the dialog requires the operator to type "CLOSE ALL" to prevent accidental triggering (same safety pattern as risk override confirmation from Story 4.3)
**And** on confirmation, the frontend calls `POST /api/positions/close-all` with optional `{ rationale: string }`

**Given** the backend receives `POST /api/positions/close-all`
**When** the endpoint processes the request
**Then** it returns immediately with `202 Accepted` and a `{ batchId: string }`
**And** positions are closed sequentially in the background (not parallel — respect rate limits and sequential execution locking from Story 4.4)
**And** each individual close acquires/releases the execution lock per-position (delegating to `IPositionCloseService`), allowing the exit monitor to still process non-queued positions without deadlock
**And** as each position resolves, a `position.update` WebSocket event is pushed (existing event type) so the operator sees positions flipping to CLOSED one by one
**And** when the batch completes, a `batch.complete` WebSocket event is pushed with summary: `{ batchId, closed: number, failed: number, rateLimited: number, results: [{ positionId, status, pnl?, error? }] }`

**Given** rate limit headroom is insufficient for all remaining positions mid-batch
**When** the rate limit pre-check fails for a position
**Then** that position is skipped with `{ status: 'rate_limited' }` in the results
**And** the batch continues with remaining positions (close as many as possible — partial success is better than full abort in an emergency)
**And** the summary clearly reports how many were rate-limited so the operator knows to retry

**Given** no positions are in a closeable state
**When** the operator views the positions page
**Then** the "Close All Positions" button is disabled with a tooltip "No open positions to close"

**WebSocket Event Registration:**

**Given** a new `batch.complete` event type is introduced
**When** Story 7.5.3 is implemented
**Then** `DashboardEventMapperService` is updated with the new event mapping
**And** `DASHBOARD_EVENTS` constant includes the new event type
**And** `WsEventEnvelope` types are extended to include the batch complete payload
**And** this follows the same wiring pattern as Story 7.3's `match.pending` event

**Implementation Notes:**
- The per-position close dialog already exists from Story 7.2 — update API call target and add projected close P&L field
- `POST /api/positions/close-all` in `PositionManagementController` (from 7.5.1), delegating to `IPositionCloseService`
- Async batch processing: use NestJS event emitter or a simple in-memory queue — the batch runs in background, WebSocket pushes progress
- Per-position execution lock ensures no conflict with exit monitor's concurrent polling cycles
- Rate limit check per-position before each close attempt — skip and report if insufficient budget
- "Close All" button: red, visually distinct, separated from routine controls, visible only when closeable positions exist
- Frontend: progress indicator ("Closing 3/10...") driven by `position.update` WebSocket events already being listened to

**DoD Gates:**
- All existing tests pass (`pnpm test`), `pnpm lint` reports zero errors
- New test cases cover: close-all async batch execution, close-all with mixed success/failure/rate-limited results, close-all with no closeable positions (empty result), per-position execution lock during batch (no deadlock), updated close button calls correct endpoint, confirmation dialog shows projected P&L, "CLOSE ALL" typed confirmation validation, `batch.complete` event emission and mapping
- No `decimal.js` violations introduced
- Generated API client regenerated after new endpoint

### Epic 8: Intelligent Contract Matching & Knowledge Base (Phase 1)
System automatically discovers candidate contract pairs from platform catalogs, scores confidence via semantic analysis, auto-approves high-confidence matches, and learns from resolution outcomes.
**FRs covered:** FR-AD-05, FR-AD-06, FR-AD-07, FR-CM-02, FR-CM-03, FR-CM-04, FR-CM-05

## Epic 8: Intelligent Contract Matching & Knowledge Base (Phase 1)

System automatically discovers candidate contract pairs from platform catalogs, scores confidence via semantic analysis, auto-approves high-confidence matches, and learns from resolution outcomes.

### Story 8.1: Knowledge Base Schema & Resolution Tracking

As an operator,
I want the contract matching knowledge base to track resolution outcomes and divergence,
So that matching accuracy improves over time from real data.

**Acceptance Criteria:**

**Given** the `contract_matches` table exists from Epic 3
**When** this story is implemented
**Then** a Prisma migration adds: confidence_score (nullable float), resolution_criteria_hash (text), polymarket_resolution (text nullable), kalshi_resolution (text nullable), resolution_timestamp (timestamptz nullable), resolution_diverged (boolean nullable), divergence_notes (text nullable)
**And** the KnowledgeBaseService provides CRUD operations for the expanded schema (FR-CM-03)
**And** after contract resolution, outcomes are recorded and divergence is flagged automatically

### Story 8.2: Semantic Contract Matching & Confidence Scoring

As an operator,
I want the system to automatically identify potential cross-platform contract matches using semantic analysis,
So that I can scale beyond 20-30 manually curated pairs to 50+.

**Acceptance Criteria:**

**Given** contract descriptions are available from both platforms
**When** the confidence scorer analyzes a potential pair
**Then** it produces a confidence score (0-100%) based on: settlement date matching (weighted highest), normalized string similarity on descriptions (cosine similarity on TF-IDF or similar), and resolution criteria keyword overlap (FR-AD-05, FR-CM-02)
**And** the `ConfidenceScorerService` uses a pluggable scoring strategy interface (`IScoringStrategy`) so the algorithm can be swapped without changing consumers
**And** the initial `IScoringStrategy` implementation uses LLM-based semantic analysis (cost-efficient model with optional escalation to higher-quality model for ambiguous cases) for high-accuracy confidence scoring
**And** deterministic string-based analysis (TF-IDF, cosine similarity, keyword overlap) is implemented as a separate `PreFilterService` for use as the candidate narrowing stage in the discovery pipeline, not as the primary scoring strategy
**And** LLM provider, model selection, and escalation thresholds are configurable via environment variables

**Given** a confidence score is produced
**When** the score is ≥85%
**Then** the match is auto-approved and added to active pairs (FR-AD-06)
**And** a `MatchAutoApprovedEvent` is emitted

**Given** a confidence score is <85%
**When** the match is flagged
**Then** it enters the pending queue for operator review via dashboard (FR-AD-06)
**And** a `MatchPendingReviewEvent` is emitted

### Story 8.3: Resolution Feedback Loop

As an operator,
I want the system to learn from past resolution outcomes to improve future matching accuracy,
So that confidence scoring gets better over time with accumulated data.

**Acceptance Criteria:**

**Given** both platforms have resolved a matched contract pair
**When** outcomes are compared
**Then** matching resolutions (both YES or both NO) are logged as positive validation (FR-CM-04)
**And** divergent resolutions trigger: alert to operator, reduced confidence for similar semantic patterns, and mandatory root cause analysis in `divergence_notes`
**And** the knowledge base accumulates validated patterns (FR-AD-07)

**Given** sufficient resolved matches exist (quarterly batch)
**When** calibration analysis runs
**Then** confidence thresholds are evaluated against actual accuracy
**And** recommendations are surfaced to operator (e.g., "auto-approve threshold could be lowered to 80% based on 0% divergence rate")

### Story 8.4: Cross-Platform Candidate Discovery Pipeline

As an operator,
I want the system to automatically discover potential cross-platform contract matches from active platform listings,
So that the scoring pipeline has an automated input source and I don't need to manually search both platforms for new pairs.

**Acceptance Criteria:**

**Given** both platform connectors implement `IContractCatalogProvider`
**When** the scheduled discovery job runs (configurable, default: twice daily)
**Then** active contract catalogs are fetched from all connected platforms via `listActiveContracts()` returning `ContractSummary[]` (title, description, category, settlement date, contract ID, platform)
**And** catalogs are cached locally for the duration of the discovery run
**And** the discovery job runs off the trading hot path via `@nestjs/schedule` (same pattern as NTP sync, daily health digests)

**Given** contract catalogs are loaded from both platforms
**When** the pre-filter stage runs
**Then** for each contract on one platform, the opposite platform's catalog is narrowed to a shortlist using deterministic filters: category match, settlement date proximity (configurable window, default: ±7 days), and TF-IDF/cosine similarity on titles
**And** pairs already in the knowledge base (approved, rejected, or pending) are excluded
**And** the pre-filter produces candidate pairs with a shortlist of ~5-20 candidates per source contract

**Given** candidate pairs survive the pre-filter
**When** the scoring stage runs
**Then** each candidate pair is routed through `ConfidenceScorerService` via the `IScoringStrategy` interface (FR-CM-05)
**And** results flow into the existing auto-approve (≥85%) / operator review (<85%) workflow from Story 8.2
**And** new candidate pairs appear as pending matches in the dashboard (Story 7.3's approval interface)

**Given** a discovery run encounters LLM API errors
**When** scoring fails for a candidate pair
**Then** the candidate is queued for retry on the next scheduled discovery run
**And** an `LlmScoringError` (error code range 4100-4199) is logged with context
**And** discovery continues processing remaining candidates (partial failure is acceptable)
**And** the trading hot path is never affected by discovery failures

**Given** `IContractCatalogProvider` is defined in `common/interfaces/`
**When** a new platform connector is added (Epic 11)
**Then** implementing `IContractCatalogProvider` is optional (separate from `IPlatformConnector`)
**And** connectors that implement it automatically participate in discovery runs without core module changes

**Tech Note:** Recommended initial LLM configuration: Gemini 2.5 Flash as primary (cost-efficient, good quality), Claude Haiku 4.5 for escalation on ambiguous cases. At ~5,000 comparisons per discovery run, estimated LLM API cost is a few cents per run. Model selection is configurable via environment variables per Story 8.2's AC.

### Story 8.6: Candidate Discovery Filtering Fixes & Match Page Pagination

As an operator,
I want the candidate discovery pipeline to use correct settlement dates from Kalshi, filter out unrelated candidates effectively, and the match review page to support pagination,
So that LLM API calls are not wasted on garbage candidates, the match review queue is navigable at scale, and the data quality is correct for downstream features (Story 8.3, Story 9.3).

**Acceptance Criteria:**

**Given** the Kalshi API returns markets with `expected_expiration_time`, `expiration_time`, and `close_time` fields
**When** `mapToContractSummary` maps a Kalshi market to `ContractSummary`
**Then** `settlementDate` uses the fallback chain: `expected_expiration_time` → `expiration_time` → `close_time`
**And** given `expiration_time` is required per the Kalshi SDK, when a market response lacks both `expected_expiration_time` and `expiration_time`, then a structured warning is emitted with the market ticker so the anomaly is visible in operational logs

**Given** `isWithinSettlementWindow` receives a contract pair where either settlement date is undefined
**When** the date filter evaluates the pair
**Then** the pair is excluded (`return false`), not included

**Given** the pre-filter TF-IDF threshold is applied to candidate pairs
**When** the threshold value is calibrated
**Then** the value is determined by before/after analysis against the existing 693 matches in the database
**And** all 4 legitimate matches (scores 40–55) must survive the tighter filter
**And** the before/after candidate analysis is documented in the dev agent record with exact counts

**Given** the match review page displays contract matches
**When** there are more than 20 matches for the selected filter
**Then** prev/next pagination controls are displayed with a page indicator
**And** page resets to 1 when the status filter changes

**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-10b.md`

**Problem A (text length inconsistency) decision gate:** Only pursue description normalization if the post-fix analysis shows remaining garbage matches where description asymmetry is a contributing factor. If numbers are clean after B0+B1+B2, skip entirely.

### Epic 9: Advanced Risk & Portfolio Management (Phase 1)
System provides correlation-aware position sizing, dynamic cluster limits, confidence-adjusted sizing, capital efficiency gating, and Monte Carlo stress testing.
**FRs covered:** FR-AD-08, FR-RM-05, FR-RM-06, FR-RM-07, FR-RM-08, FR-RM-09

## Epic 9: Advanced Risk & Portfolio Management (Phase 1)

System provides correlation-aware position sizing, dynamic cluster limits, confidence-adjusted sizing, capital efficiency gating, and Monte Carlo stress testing.

### Story 9.1: Correlation Cluster Tracking & Exposure Calculation

As an operator,
I want the system to track which positions belong to correlated event clusters and calculate aggregate exposure,
So that I'm not unknowingly concentrated in a single risk factor.

**Acceptance Criteria:**

**Given** contract pairs are classified into correlation clusters (Fed Policy, Elections, Economic Indicators, Geographic Events, Uncategorized)
**When** a new position is opened
**Then** its cluster is identified and cluster exposure is recalculated: `Cluster Exposure = Sum(Position Size × Entry Price)` for all open pairs in cluster (FR-RM-05)
**And** cluster exposure as % of bankroll is tracked in real-time

**Given** the operator disagrees with a cluster assignment
**When** they override via `POST /api/risk/cluster-override`
**Then** the override is logged to audit trail with rationale
**And** exposure calculations use the overridden cluster

### Story 9.1a: Kalshi Fixed-Point API Migration (Course Correction 2026-03-12)

As an operator,
I want the Kalshi connector updated to use the new fixed-point API response format,
So that order book data flows and trade execution are restored after Kalshi's 2026-03-12 migration removed all legacy integer fields.

**Acceptance Criteria:**

**Given** Kalshi's REST API now returns `orderbook_fp` with `yes_dollars`/`no_dollars` string arrays instead of `orderbook` with `yes`/`no` integer arrays
**When** the system fetches order book data via `getOrderBook()`
**Then** the response is parsed correctly using the new field names and string types
**And** prices (already in dollars) are not double-divided by 100
**And** the `NormalizedOrderBook` output is identical in shape to pre-migration

**Given** Kalshi's WebSocket now sends `yes_dollars_fp`/`no_dollars_fp` in snapshots and `price_dollars`/`delta_fp` in deltas (all strings)
**When** the WebSocket client receives orderbook messages
**Then** snapshots and deltas are parsed and applied correctly
**And** local orderbook state is maintained with string-based price levels

**Given** the Zod validation schemas and TypeScript interfaces reference old field names
**When** a Kalshi API response or WebSocket message arrives
**Then** all schemas validate against the new fixed-point field names and string types

**Context:** Kalshi completed their Fixed-Point Migration on 2026-03-12, removing all legacy integer-based fields. 6 files affected: kalshi.connector.ts, kalshi-response.schema.ts, kalshi.types.ts, kalshi-websocket.client.ts, kalshi-price.util.ts, kalshi-price.util.spec.ts.

### Story 9.1b: Orderbook Staleness Detection & Alerting (Course Correction 2026-03-12)

As an operator,
I want the system to detect when a platform stops providing valid order book data and alert me immediately via Telegram,
So that I can take corrective action without delay when an API issue occurs.

**Acceptance Criteria:**

**Given** a platform's order book data has not been successfully refreshed within a configurable staleness threshold (default: 90 seconds)
**When** the staleness check runs
**Then** a `platform.orderbook.stale` event is emitted with platform ID, last successful update timestamp, and staleness duration
**And** a Telegram alert is sent with actionable context

**Given** a platform's order book was stale but fresh data resumes
**When** the next successful order book update is received
**Then** a `platform.orderbook.recovered` event is emitted
**And** a Telegram recovery notification is sent

**Given** a platform's order book is stale
**When** the arbitrage detection cycle runs
**Then** opportunities involving the stale platform are suppressed
**And** the suppression reason is logged

**Context:** The Kalshi FP migration breakage (Story 9-1a) was discovered manually via debugging — no automated alert fired. This story closes that observability gap. Builds on existing platform health infrastructure (FR-DI-03, FR-DI-04, NFR-R4).

### Story 9.2: Correlation Limit Enforcement & Triage Recommendations

As an operator,
I want the system to prevent trades that would breach correlation limits and recommend which positions to close to free budget,
So that portfolio concentration risk is managed automatically.

**Acceptance Criteria:**

**Given** cluster exposure is at 12-15% of bankroll (soft limit zone)
**When** a new opportunity in that cluster is detected
**Then** position size is adjusted: `Adjusted Size = Base Size × (1 - (Current Cluster % ÷ 15%))` (FR-RM-07)
**And** operator is alerted with current cluster state

**Given** a new position would push cluster exposure above 15% hard limit
**When** risk validation runs
**Then** the trade is rejected (FR-RM-06)
**And** triage recommendations are provided: positions in the cluster ranked by remaining edge, with lowest-edge position suggested for closure to free budget (FR-RM-07)

**Given** aggregate exposure across all clusters exceeds 50% of bankroll
**When** the aggregate limit is breached
**Then** no new positions are allowed in any cluster until aggregate drops below 50%

### Story 9.3: Confidence-Adjusted Position Sizing

As an operator,
I want position sizes automatically reduced for lower-confidence contract matches,
So that uncertain matches carry proportionally less capital risk.

**Acceptance Criteria:**

**Given** an opportunity has a contract match confidence score
**When** position sizing is calculated
**Then** adjusted size = `base_size × confidence_score` (FR-RM-08)
**And** a 90% confidence match gets 90% of base size, an 85% match gets 85%

**Given** a match was manually approved (MVP pairs with no NLP score)
**When** position sizing runs
**Then** manually approved matches use 100% base size (confidence = 1.0)

### Story 9.4: Monte Carlo Stress Testing

As an operator,
I want the system to run stress tests against historical and synthetic scenarios,
So that I can validate my risk parameters aren't calibrated too loosely.

**Acceptance Criteria:**

**Given** the current portfolio state and risk parameters
**When** Monte Carlo simulation runs (triggered manually via `POST /api/risk/stress-test` or on weekly schedule)
**Then** it simulates 1000+ scenarios using historical price movements and synthetic adverse scenarios (FR-RM-09)
**And** results include: probability of drawdown >15%, >20%, >25%; expected worst-case loss; portfolio VaR at 95% and 99% confidence

**Given** stress test results indicate risk parameters are too loose
**When** probability of >20% drawdown exceeds 5%
**Then** an alert is emitted recommending parameter tightening with specific suggestions

### Story 9.5: Capital Efficiency Gating & Resolution Date Filtering (Course Correction 2026-03-13)

As an operator,
I want the system to reject opportunities that lack a known resolution date or whose annualized return doesn't justify the capital lockup,
So that my capital is only deployed in trades with favorable time-value economics.

**Acceptance Criteria:**

**Given** an opportunity passes the net edge threshold (FR-AD-03, ≥0.8%)
**When** the contract match has no resolution date (null)
**Then** the opportunity is rejected before risk validation
**And** an `OpportunityFilteredEvent` is emitted with reason: "no resolution date"
**And** the rejection is logged with pair ID and contract descriptions

**Given** an opportunity has a known resolution date
**When** the annualized net return is calculated as: `(net_edge / capital_per_unit) × (365 / days_to_resolution)`
**And** the result is below the configurable minimum (default: 15%)
**Then** the opportunity is rejected before risk validation (FR-AD-08)
**And** an `OpportunityFilteredEvent` is emitted with reason: "annualized return {calculated}% below {threshold}% minimum"
**And** the rejection is logged with calculated annualized return, days to resolution, and threshold

**Given** an opportunity has a resolution date and meets the annualized return threshold
**When** the capital efficiency check passes
**Then** the opportunity proceeds to risk validation unchanged
**And** the annualized return is included in the enriched opportunity context for downstream logging and dashboard display

**Given** the capital efficiency gate configuration
**When** the engine starts
**Then** `MIN_ANNUALIZED_RETURN` is loaded from env config (default: 0.15)
**And** invalid values (negative, >10.0) are rejected at startup
**And** the threshold is logged at startup for operator awareness

**Context:** Discovered during Sprint 9 paper trading. A position on "Will OpenAI or Anthropic IPO first?" had no resolution date and locked ~$50 capital for TP: +$0.23 vs SL: -$8.15. The system's only quality gate (FR-AD-03, 0.8% net edge) passed the opportunity because it doesn't evaluate time-value of capital. See sprint-change-proposal-2026-03-13.md for full analysis.

### Story 9.7: Matches Page Redesign & Data Alignment (Course Correction 2026-03-13)

As an operator,
I want the dashboard matches page redesigned as a proper table with all contract match fields visible, separate status views, cluster filtering, and a match detail page,
So that I can efficiently review, filter, and inspect contract matches with full operational context including cluster assignments, resolution dates, and trading activity.

**Acceptance Criteria:**

**Given** the `contract_matches` table has 22 fields including cluster, resolution date, categories, primary leg, and trading activity
**When** the operator views the matches page
**Then** all fields are accessible — key columns in the table view, full record on the detail page
**And** the card-based layout is replaced with a structured table

**Given** the operator wants to view matches by approval status
**When** they navigate the matches page
**Then** Pending, Approved, and All are presented as separate tabbed views (not a single consolidated list)

**Given** the operator wants to filter by correlation cluster
**When** they select a cluster from the filter dropdown
**Then** the table shows only matches belonging to that cluster
**And** the filter works across all status tabs

**Given** the operator clicks on a match row in the table
**When** the detail page loads at `/matches/:id`
**Then** the full record is displayed with all fields organized in sections: contract pair details, resolution data, trading activity, operator review status

**Given** Epic 8 (semantic matching) is complete
**When** the matches page renders
**Then** no dead code references Epic 8 as future work (e.g., "Knowledge Base: Coming in Epic 8")
**And** the deleted `MatchCard` component is replaced by table rows

**Given** the backend DTO is updated
**When** the API returns match data
**Then** `MatchSummaryDto` includes all 8 previously missing fields: `polymarketRawCategory`, `kalshiRawCategory`, `firstTradedTimestamp`, `totalCyclesTraded`, `primaryLeg`, `resolutionDate`, `resolutionCriteriaHash`, and resolved `cluster` object
**And** the generated API client is regenerated to reflect the updated types

**Context:** The matches page was built in Epic 7 (Story 7-3) and hasn't been updated to reflect fields added in Epics 8 and 9. Eight database fields — including operationally critical cluster assignment, resolution date, and trading activity — are invisible to the operator. See sprint-change-proposal-2026-03-13b.md for full analysis.

### Epic 10: Model-Driven Exits & Advanced Execution (Phase 1)
System continuously recalculates edge and triggers exits on five criteria, plus adapts leg sequencing and auto-manages single-leg exposure.
**FRs covered:** FR-EM-02, FR-EM-03, FR-EX-07, FR-EX-08

## Epic 10: Model-Driven Exits & Advanced Execution (Phase 1)

System continuously recalculates edge and triggers exits on five criteria, plus adapts leg sequencing and auto-manages single-leg exposure.

**Capacity Budget (Team Agreement #22):** 4 planned feature stories + 3 pre-epic stories = 7 base. Budget 30-40% for internal corrections → expect 9-11 total stories.

**Architecture Decision (Epic 9 Retro):** Retrofit, don't rethink. Trading cycle stays poll-based (entry decisions). Exit monitor gets WebSocket real-time feed (exit decisions). Two data paths, one architecture. Divergence monitoring required (Team Agreement #23).

**Critical Prerequisites (must complete before feature stories):**
- WebSocket subscription establishment (10-0-1) — blocks 10.1
- Carry-forward debt resolution (10-0-2) — blocks 10.2 (resolutionDate, realizedPnl) and 10.3 (SingleLegContext)
- Exit monitor architecture review (10-0-3) — informs 10.1/10.2 implementation approach

### Story 10-0-1: WebSocket Subscription Establishment & Divergence Monitoring

As an operator,
I want WebSocket connections to actually subscribe to contract tickers and divergence between poll and WebSocket data paths to be monitored,
So that exit decisions can use real-time data and I'm alerted when data paths drift apart.

**Context:** Epic 9 story 9-20 discovered WebSocket connections exist but no tickers are subscribed. Data only flows during polling cycles. This story establishes the subscription mechanism and divergence detection required by the dual data path architecture.

**Acceptance Criteria:**

**Given** the `IPlatformConnector` interface
**When** this story is implemented
**Then** a new method `subscribeToContracts(contractIds: ContractId[])` is added to the interface
**And** both Kalshi and Polymarket connectors implement the method
**And** the exit monitor subscribes to tickers for all open positions

**Given** WebSocket subscriptions are active
**When** both poll and WebSocket data arrive for the same contract
**Then** divergence is measured (price delta, staleness delta)
**And** divergence exceeding configurable threshold emits `platform.data.divergence` event
**And** divergence metrics are available on the dashboard health view (Team Agreement #18: vertical slice)

**Given** the data path contract
**When** the system operates
**Then** polling is authoritative for entry decisions (detection pipeline)
**And** WebSocket is authoritative for exit decisions (exit monitor)
**And** this contract is documented and enforced at the architectural level

**Tech Debt Note (from Story 9-20):** Post-ingestion `publishHealth()` call was the immediate fix. This story builds the proper subscription mechanism on top of that foundation.

### Story 10-0-2: Carry-Forward Debt Triage & Critical Fixes

As an operator,
I want carry-forward tech debt items that directly impact Epic 10 stories resolved before feature development begins,
So that feature stories don't hit known blockers mid-implementation.

**Context:** Epic 9 retro identified 28 tech debt items (8 new + 20 carry-forward). Three directly block Epic 10 feature stories.

**Acceptance Criteria:**

**Given** the 28 tech debt items from the Epic 9 retro
**When** this story is implemented
**Then** every item has an explicit disposition: address now, address during Epic 10, carry forward, or close — with rationale

**Given** tech debt item #1 (`handleSingleLeg` 16-param → `SingleLegContext` interface, from Epic 5.5)
**When** this story is implemented
**Then** `handleSingleLeg` accepts a `SingleLegContext` object instead of 16 positional parameters
**And** all call sites are updated
**And** this unblocks Story 10.3 (Automatic Single-Leg Management)

**Given** tech debt item #3 (`realizedPnl` column on OpenPosition, from Epic 6)
**When** this story is implemented
**Then** a `realized_pnl` column exists on the `open_positions` table (Prisma migration)
**And** realized P&L is populated when positions are closed
**And** this unblocks Story 10.2 criterion tracking

**Given** tech debt item #5 (`resolutionDate` has no write path, from Epic 5)
**When** this story is implemented
**Then** `resolution_date` is populated from platform API data during contract match creation or update
**And** time-based exit logic (Story 10.2 criterion #3) has functional input data

**Given** the full triage is complete
**When** results are reviewed
**Then** a triage document exists with all 28 items categorized and rationale provided

### Story 10-0-3: Exit Monitor Architecture Review (Spike)

As an operator,
I want the ThresholdEvaluatorService refactor sketched out before implementing the five-criteria model,
So that the implementation approach is validated before code is written.

**Context:** The current ThresholdEvaluatorService handles fixed-threshold exits (take-profit, stop-loss, pre-resolution). Story 10.2 expands this to five criteria with shadow mode. This spike produces a design sketch, not implementation.

**Acceptance Criteria:**

**Given** the current ThresholdEvaluatorService architecture
**When** this spike is completed
**Then** a design document exists covering:
- How the five criteria compose (independent evaluation, priority ordering, or weighted)
- How shadow mode comparison works (both modes evaluate, one executes, diff logged)
- How the WebSocket data path (from 10-0-1) feeds into continuous recalculation
- Which criteria need new data sources (model confidence changes, liquidity snapshots)
- Interface changes needed for ExitMonitorService

**Given** this is a spike
**When** scope is evaluated
**Then** no production code is written — output is a design document reviewed by the team
**And** the spike follows the investigation-first pattern (Team Agreement from retro)

### Story 10.1: Continuous Edge Recalculation

As an operator,
I want open positions' expected edge continuously recalculated using live market data,
So that exit decisions are based on current reality, not stale entry-time assumptions.

**Acceptance Criteria:**

**Given** a position is open
**When** the exit monitor evaluates it each cycle
**Then** expected edge is recalculated based on: current fee schedules, live liquidity depth at exit prices, updated gas estimates, and time to resolution (FR-EM-02)
**And** recalculation uses WebSocket price feed (authoritative for exit decisions, per 10-0-1 data path contract) with polling fallback
**And** recalculated edge is persisted and available to the dashboard

**Given** continuous recalculation is active
**When** the dashboard displays open positions
**Then** each position shows: current recalculated edge, edge delta since entry, last recalculation timestamp, and data source indicator (WebSocket/polling fallback) (Team Agreement #18: vertical slice minimum)

**Given** WebSocket data is unavailable for a position
**When** the exit monitor recalculates
**Then** polling data is used as fallback
**And** the position is flagged with a data staleness indicator on the dashboard
**And** a `platform.data.fallback` event is emitted

**Dependencies:** Story 10-0-1 (WebSocket subscriptions), Story 10-0-3 (architecture review output)
**Vertical Slice:** Dashboard position view shows recalculated edge, delta, data source

### Story 10.2: Five-Criteria Model-Driven Exit Logic

As an operator,
I want the system to trigger exits based on five intelligent criteria instead of fixed thresholds,
So that more edge is captured and losses are cut more precisely.

**Acceptance Criteria:**

**Given** a position's edge is recalculated
**When** any of five exit criteria are met
**Then** an exit is triggered (FR-EM-03):
1. **Edge evaporation:** Recalculated edge drops below breakeven after costs
2. **Model update:** Confidence score for the contract match has decreased below threshold
3. **Time decay:** Expected value diminishes as resolution approaches (configurable decay curve) — requires `resolutionDate` write path (resolved in 10-0-2)
4. **Risk budget breach:** Portfolio-level risk limit is approached and this position has lowest remaining edge
5. **Liquidity deterioration:** Order book depth at exit prices drops below minimum executable threshold
**And** realized P&L is tracked per position using `realized_pnl` column (resolved in 10-0-2)

**Given** model-driven exits are active
**When** the system is configured
**Then** the operator can toggle between fixed thresholds (MVP) and model-driven exits via config
**And** both modes can run in shadow mode (model-driven calculates but fixed thresholds execute) for validation

**Given** shadow mode is active
**When** an exit occurs (by either mode)
**Then** a daily comparison summary is logged showing: "fixed would have exited at X with P&L Y, model would have exited at Z with P&L W, actual edge captured"
**And** this comparison data is available in the dashboard performance view for building confidence in the switch

**Given** the dashboard displays positions
**When** model-driven exits are active (or shadow mode)
**Then** each position shows: which criterion is closest to triggering, proximity percentage per criterion, and exit mode indicator (fixed/model/shadow) (Team Agreement #18: vertical slice minimum)

**Given** shadow mode generates comparison data
**When** the operator views the performance page
**Then** a shadow mode comparison table shows per-exit: trigger criterion, fixed vs model timing, P&L delta, and cumulative advantage/disadvantage

**Given** paper trading mode is active
**When** model-driven exits evaluate
**Then** paper mode uses simulated fill prices (no platform API verification of fills)
**And** live mode uses real platform API verification
**And** both paths have explicit test coverage (Team Agreement #20: paper/live boundary)

**Given** tests are written for this story
**When** internal subsystems are validated
**Then** tests verify that recalculated edge data actually arrives from the WebSocket/polling path — not just that the criterion evaluation logic handles it correctly (Team Agreement #19: internal subsystem verification)

**Dependencies:** Story 10-0-1 (WebSocket data feed), Story 10-0-2 (resolutionDate write path, realizedPnl column), Story 10-0-3 (architecture review — five-criteria composition design)
**Vertical Slice:** Exit criteria proximity display, shadow mode comparison table, exit mode indicator

### Story 10.3: Automatic Single-Leg Management

As an operator,
I want the system to automatically manage single-leg exposure by closing or hedging the filled leg,
So that I don't need to be available for every single-leg event.

**Acceptance Criteria:**

**Given** a second leg fails to fill within the configurable timeout (default 5 seconds)
**When** automatic single-leg management is enabled
**Then** the system attempts to unwind the filled leg within acceptable loss parameters (FR-EX-07)
**And** if unwind succeeds, the position is closed with loss logged
**And** if unwind fails, the position remains in "single_leg_exposed" for operator resolution (fallback to MVP workflow from Story 5.2/5.3)
**And** an `AutoUnwindEvent` is emitted with action taken and result

**Given** the `handleSingleLeg` function
**When** this story is implemented
**Then** it accepts a `SingleLegContext` interface (resolved in 10-0-2) instead of positional parameters
**And** the `AutoUnwindEvent` payload includes full `SingleLegContext` for audit trail completeness

**Given** paper trading mode is active
**When** a single-leg event occurs
**Then** the auto-unwind uses simulated fills (paper mode cannot verify against real platform APIs — simulated fills don't exist on platforms)
**And** the unwind result is marked as `simulated: true` in the event payload and audit log
**And** live mode uses real platform API order submission for unwind
**And** both paths have explicit test coverage with dedicated `paper-live-boundary` tests (Team Agreement #20)

**Given** auto-unwind is attempted (paper or live)
**When** the dashboard displays single-leg events
**Then** each event shows: auto-unwind attempted (yes/no), action taken (close/hedge/fallback), result (success/fail/simulated), loss amount, and time elapsed (Team Agreement #18: vertical slice minimum)

**Given** tests validate auto-unwind behavior
**When** internal subsystems interact
**Then** tests verify the unwind order actually reaches the connector (not just that the management logic makes the right decision) (Team Agreement #19: internal subsystem verification)

**Dependencies:** Story 10-0-2 (SingleLegContext refactor)
**Vertical Slice:** Single-leg event detail view with auto-unwind status, action, result, and loss
**Tech Debt Note (from Epic 5.5):** `handleSingleLeg` 16-param signature is resolved in 10-0-2. This story builds on the clean interface.

### Story 10.4: Adaptive Leg Sequencing & Matched-Count Execution

As an operator,
I want the system to dynamically choose which platform's leg to execute first based on real-time latency and to execute matched contract counts on both legs,
So that leg risk is minimized and positions are truly hedged (equal contract counts on both sides of the arbitrage).

**Acceptance Criteria:**

**Given** both platform connectors track execution latency
**When** the latency difference exceeds 200ms
**Then** the faster platform's leg is executed first, overriding the static `primaryLeg` config (FR-EX-08)
**And** the sequencing decision is logged with latency measurements

**Given** latency profiles are stable (difference <200ms)
**When** sequencing is determined
**Then** the static `primaryLeg` config is used (preserving MVP behavior)

**Given** an arbitrage opportunity is ready for execution
**When** position sizing is calculated
**Then** the system performs pre-flight depth verification on BOTH legs before submitting either order
**And** ideal count is computed as `idealCount = reservedCapitalUsd / (buyPrice + sellPrice)` (unified formula producing matched contract counts)
**And** each leg is depth-capped independently: `cappedCount = min(idealCount, availableDepth)`
**And** the final `matchedCount = min(primaryCapped, secondaryCapped)` is used for BOTH legs
**And** edge re-validation (FR-EX-03a) runs with `matchedCount` before any order is submitted
_(Added: Story 6.5.5b identified that the MVP model computes leg sizes independently from `reservedCapitalUsd / legPrice`, producing mismatched contract counts with asymmetric payoff profiles.)_

**Given** pre-flight depth check rejects one or both legs
**When** neither order has been submitted yet
**Then** the full reservation is released cleanly (no single-leg exposure possible)
**And** this eliminates the MVP constraint where primary is submitted before secondary depth is known

**Given** adaptive sequencing makes a decision
**When** the dashboard displays recent executions
**Then** each execution shows: which platform went first, latency measurements for both platforms, sequencing reason (latency override / static config), and matched contract count vs ideal count (Team Agreement #18: vertical slice minimum)

**Given** both poll and WebSocket data paths are active
**When** execution uses depth data for pre-flight verification
**Then** depth data source is logged (poll vs WebSocket) per execution
**And** if poll and WebSocket depth diverge beyond threshold, the more conservative (lower) depth is used
**And** divergence is emitted as `platform.data.divergence` event (Team Agreement #23: two-data-path divergence monitoring)

**Given** tests validate execution flow
**When** depth verification and order submission are tested
**Then** tests verify orders actually reach the connector (not just that sizing logic produces correct values) (Team Agreement #19: internal subsystem verification)

**Dependencies:** Story 10-0-1 (WebSocket subscriptions for depth data path)
**Vertical Slice:** Execution detail view with sequencing decision, latency, matched vs ideal count, data source

**Tech Debt Note (from Story 6.5.0 code review, Finding #7):** `polymarket.connector.ts` has hardcoded `ORDER_POLL_TIMEOUT_MS` and `ORDER_POLL_INTERVAL_MS` with no exponential backoff or jitter. When implementing Story 10.4, make these timeouts configurable via `@nestjs/config` and add jitter to the polling loop.

**Tech Debt Note (from Story 6.5.5b):** The MVP depth-aware sizing model computes primary and secondary ideal sizes independently (`reservedCapitalUsd / legPrice`), producing different contract counts. With asymmetric depth capping this divergence can widen, creating directional exposure rather than hedged arbitrage. This story's matched-count execution eliminates that limitation.

### Epic 10.5: Settings Infrastructure, Structural Guards & Process Hardening
Move operational env vars to DB-backed settings with dashboard UI. Establish structural enforcement for the three recurring defect classes identified in Epic 10 retro (event wiring, collection lifecycle, paper/live mode contamination). Codify new conventions and process gates before Epic 11 begins.

## Epic 10.5: Settings Infrastructure, Structural Guards & Process Hardening

Move operational env vars to DB-backed settings with dashboard UI. Establish structural enforcement for the three recurring defect classes identified in Epic 10 retro (event wiring, collection lifecycle, paper/live mode contamination). Codify new conventions and process gates before Epic 11 begins.

**Capacity Budget (Agreement #22):** 8 base stories. With 30-40% correction buffer → expect 10-12 total.

**Story Sequencing:**
- Track A (sequential): 10-5-1 → 10-5-2 → 10-5-3 (settings)
- Track B (parallel): 10-5-4, 10-5-5, 10-5-6 (structural guards — independent of Track A)
- Track C (parallel): 10-5-7 (research spike — independent)
- Track D (last): 10-5-8 (documentation — depends on 10-5-4, 10-5-5)

### Story 10-5-1: EngineConfig Schema Expansion & Seed Migration

_(Defined in sprint-change-proposal-2026-03-22.md — settings infrastructure)_

### Story 10-5-2: Settings CRUD Endpoints & Hot-Reload Mechanics

_(Defined in sprint-change-proposal-2026-03-22.md — settings infrastructure)_

### Story 10-5-3: Dashboard Settings Page UI

_(Defined in sprint-change-proposal-2026-03-22.md — settings infrastructure)_

### Story 10-5-4: Event Wiring Verification & Collection Lifecycle Guards

As an operator,
I want automated verification that event emitters are connected to their subscribers and that in-memory collections have cleanup paths,
So that the two most common silent correctness failures (44% and 33% recurrence in Epic 10) are caught by tests instead of review.

**Context:** Epic 10 retro identified event wiring gaps in 4/9 stories and unbounded collection leaks in 3/9 stories. Both share the "silent correctness failure" shape — no error thrown, unit tests pass, handler logic correct in isolation. Agreement #26 mandates structural guards over review vigilance.

**Acceptance Criteria:**

**Given** the EventEmitter2 wiring pattern used across modules
**When** a new `@OnEvent` handler is added
**Then** an `expectEventHandled()` integration test helper exists that verifies: (1) the event is emitted by the expected service, (2) a handler with matching decorator exists, (3) the handler is actually invoked when the event fires through the real EventEmitter2

**Given** the test helper is available
**When** existing event wiring is audited
**Then** all existing `@OnEvent` handlers have corresponding `expectEventHandled()` tests
**And** any dead handlers (decorated but never triggered) are identified and removed

**Given** a story introduces a new `@OnEvent` handler
**When** the developer writes tests
**Then** a test template exists (co-located in `common/testing/`) demonstrating the `expectEventHandled()` pattern
**And** the story creation checklist requires event wiring tests for any story with event-driven behavior

**Given** in-memory collections (Map, Set, arrays used as caches)
**When** the codebase is audited
**Then** every Map/Set/cache has a documented cleanup path (TTL, max-size eviction, or lifecycle-bound disposal)
**And** CLAUDE.md documents the collection lifecycle convention: "Every new Map/Set must specify its cleanup strategy in a code comment and have a test for the cleanup path"

**Given** the MEDIUM prevention analysis (retro action item #3 deliverable)
**When** completed
**Then** the top 3 recurring MEDIUM categories from Epic 10 code reviews are documented with structural prevention measures (not "be more careful" agreements)

**Dependencies:** None (can run in parallel with settings stories)
**Blocks:** Epic 11.1 (plugin architecture)

### Story 10-5-5: Paper/Live Mode Boundary Inventory & Test Suite

As an operator,
I want every `isPaper`/`is_paper` branch in the codebase inventoried and covered by dual-mode tests,
So that the mode contamination defect class (22% recurrence in Epic 10, including a post-deploy bug in 10.1) is structurally prevented.

**Context:** Epic 10 retro identified paper/live mode contamination in 2/9 stories. Story 10.1 had a post-deploy bug where raw SQL `SELECT COUNT(*) FROM open_positions WHERE status IN (...)` did NOT filter by `is_paper`, causing 3 paper positions to trigger a LIVE halt. Story 10-0-2a fixed `validatePosition` mode-awareness but a dedicated boundary test suite was never completed (Epic 9 action item #5 — partial).

**Acceptance Criteria:**

**Given** the full codebase
**When** an `isPaper`/`is_paper` branch inventory is performed
**Then** a document lists every location where behavior diverges based on mode: service methods, repository queries, raw SQL, Prisma queries, event handlers, connectors
**And** each location is categorized: (a) has dual-mode test coverage, (b) needs test coverage, (c) structurally cannot contaminate

**Given** the inventory identifies gaps (category b)
**When** tests are written
**Then** a `paper-live-boundary.spec.ts` integration test file exists covering all category (b) locations
**And** each test verifies that paper-mode operations do not affect live-mode state and vice versa
**And** the test file is organized by module (risk, execution, exit, reconciliation, detection)

**Given** Prisma repository queries that filter by mode
**When** the inventory is complete
**Then** all repository methods that query `open_positions`, `orders`, or `risk_states` with status filters also include `is_paper` filtering
**And** a shared repository pattern or helper enforces mode-scoping (e.g., `withModeFilter(isPaper)` Prisma middleware or shared `where` clause builder)

**Given** raw SQL queries exist in the codebase
**When** they reference mode-sensitive tables
**Then** every raw SQL query includes `is_paper` filtering
**And** a code comment convention is established: `-- MODE-FILTERED` marker on compliant queries

**Given** a new story introduces mode-dependent behavior
**When** the developer writes tests
**Then** the story creation checklist requires dual-mode test coverage for any `isPaper` branch
**And** CLAUDE.md documents the paper/live boundary convention

**Dependencies:** None (can run in parallel with settings stories and 10-5-4)
**Blocks:** Epic 11.1 (plugin architecture — new connectors must handle mode correctly)

### Story 10-5-6: Exit-Monitor Spec File Split

As an operator,
I want the 69KB exit-monitor spec file decomposed into focused test files,
So that test maintenance burden is reduced and individual exit criteria can be tested, debugged, and modified independently.

**Context:** Epic 10 retro flagged `exit-monitor.service.spec.ts` at 69KB as a maintenance burden (Medium debt). The file covers six exit criteria (C1-C6), shadow mode comparison, threshold evaluation, WebSocket data integration, and position lifecycle — all in a single file. Story 10.2 expanded it significantly. The file is too large for efficient navigation, and failures in one criterion's tests obscure failures in others.

**Acceptance Criteria:**

**Given** the current `exit-monitor.service.spec.ts` (69KB)
**When** the split is complete
**Then** the spec file is decomposed into focused files, each under 15KB
**And** file naming follows the pattern: `exit-monitor-{concern}.spec.ts` (e.g., `exit-monitor-edge-evaporation.spec.ts`, `exit-monitor-shadow-mode.spec.ts`)

**Given** the decomposed spec files
**When** tests are run
**Then** zero test coverage regression — all existing tests pass in their new locations
**And** `pnpm test` reports the same number of passing exit-monitor tests before and after the split

**Given** shared test setup (mocks, fixtures, helpers)
**When** multiple spec files need the same setup
**Then** shared setup is extracted to a `exit-monitor.test-helpers.ts` file co-located in the same directory
**And** each spec file imports only the helpers it needs (no monolithic `beforeEach`)

**Given** the six-criteria model (C1-C6)
**When** a suggested split structure is defined
**Then** at minimum these files exist:
- `exit-monitor-core.spec.ts` — position lifecycle, evaluation loop, mode switching
- `exit-monitor-edge-evaporation.spec.ts` — C1
- `exit-monitor-confidence-drop.spec.ts` — C2
- `exit-monitor-time-decay.spec.ts` — C3
- `exit-monitor-risk-budget.spec.ts` — C4
- `exit-monitor-liquidity.spec.ts` — C5
- `exit-monitor-profit-capture.spec.ts` — C6
- `exit-monitor-shadow-mode.spec.ts` — shadow vs fixed comparison

**Given** this is a refactoring story
**When** scope is evaluated
**Then** no production code changes — only spec file reorganization
**And** no new tests added (that's for feature stories)

**Dependencies:** None (can run in parallel with all other 10.5 stories)
**Blocks:** Epic 11.1 (clean test structure needed before connector changes touch exit paths)

### Story 10-5-7: External Secrets Management Research Spike

As an operator,
I want a design document mapping the system's credential surface to a secrets manager integration,
So that Story 11.2 (External Secrets Management Integration) starts with zero open architectural questions.

**Context:** Epic 11 includes Story 11.2 (External Secrets Management) and Story 11.3 (Zero-Downtime Key Rotation). Both require decisions about provider selection, credential lifecycle, fallback strategy, and integration pattern. This spike produces a design document, not implementation — following the investigation-first pattern validated in Epic 10 (Story 10-0-3).

**Acceptance Criteria:**

**Given** the system's current credential surface
**When** the spike is completed
**Then** a design document exists covering:
- Complete inventory of all credentials/secrets in the system (Kalshi API key/secret, Polymarket private key, operator Bearer token, PostgreSQL password, Telegram bot token, LLM API keys)
- Which credentials are used at startup-only vs. runtime-refreshable
- Current storage mechanism for each (env var, file path, in-memory)

**Given** the secrets manager landscape
**When** providers are evaluated
**Then** the design document includes a provider comparison with recommendation:
- AWS Secrets Manager, HashiCorp Vault, and at least one lightweight alternative (e.g., SOPS, age-encrypted files for solo operator use case)
- Evaluation criteria: cost at solo-operator scale, complexity, SDK maturity for Node.js/NestJS, rotation support, audit logging
- Clear recommendation with rationale

**Given** the recommended provider
**When** the integration pattern is designed
**Then** the design document covers:
- Credential lifecycle model: fetch → cache → use → refresh → invalidate
- NestJS integration pattern (custom ConfigFactory, provider, or module)
- Fallback strategy when secrets manager is unavailable (env var fallback with degraded-security alert)
- How this interacts with Story 10-5-2's `getEffectiveConfig()` pattern (secrets are NOT in EngineConfig DB — clear boundary)
- Key rotation mechanics: how `POST /api/admin/rotate-credentials/:platform` (Story 11.3) triggers re-fetch

**Given** this is a spike
**When** scope is evaluated
**Then** no production code is written — output is a design document
**And** the document is reviewed by Winston (architecture) before the spike is marked complete
**And** the spike follows the investigation-first pattern (Team Agreement from Epic 9 retro)

**Dependencies:** None (research, can run in parallel with everything)
**Blocks:** Epic 11.2 (External Secrets Management Integration)

### Story 10-5-8: CLAUDE.md, Story Template & Process Convention Updates

As an operator,
I want all Epic 10 retro conventions, structural guard patterns, and process improvements documented in CLAUDE.md and the story creation checklist,
So that the dev agent follows these conventions automatically and Epic 11 stories are created with the new sizing and verification gates.

**Context:** Epic 10 retro produced 3 new team agreements (#24 disciplines as deliverables, #25 story sizing gate, #26 structural guards over vigilance), identified 3 recurring defect classes needing conventions, and generated structural enforcement stories (10-5-4, 10-5-5) whose patterns need to be codified. This story is the documentation counterpart — encoding the new norms so they persist beyond the retro document.

**Acceptance Criteria:**

**Given** Story 10-5-4 delivers event wiring verification patterns
**When** CLAUDE.md is updated
**Then** the following conventions are documented:
- Event wiring convention: every `@OnEvent` handler requires an `expectEventHandled()` integration test
- Collection lifecycle convention: every new Map/Set must specify cleanup strategy in a code comment and have a test for the cleanup path
- Top 3 MEDIUM prevention measures from the MEDIUM analysis (10-5-4 deliverable)

**Given** Story 10-5-5 delivers paper/live boundary patterns
**When** CLAUDE.md is updated
**Then** the following conventions are documented:
- Paper/live boundary convention: every `isPaper` branch requires dual-mode test coverage
- Repository mode-scoping pattern (shared `withModeFilter` or equivalent from 10-5-5)
- Raw SQL `-- MODE-FILTERED` marker convention

**Given** Agreement #25 (story sizing gate)
**When** the story creation checklist is updated
**Then** a sizing gate is added: "Stories exceeding 10 tasks or 3+ integration boundaries are flagged for splitting"
**And** the gate is a checklist item during story preparation, not a post-implementation observation

**Given** Agreement #24 (retro commitments as deliverables)
**When** CLAUDE.md is updated
**Then** the retrospective section documents: "Every retro action item must be expressible as a story with ACs or a task within a story. Open-ended discipline commitments without enforcement are rejected at retro time."

**Given** Agreement #26 (structural guards over review vigilance)
**When** CLAUDE.md is updated
**Then** the code review section documents: "If review catches the same defect category three times across an epic, it becomes a pre-epic story with structural prevention — not a 'be more careful' agreement."

**Given** this story depends on patterns established by 10-5-4 and 10-5-5
**When** sequencing is evaluated
**Then** this story is implemented after 10-5-4 and 10-5-5 are complete (so documented patterns match actual implementation)

**Dependencies:** 10-5-4 (event wiring patterns), 10-5-5 (paper/live patterns)
**Blocks:** Epic 11 story creation (SM needs updated checklist before writing Epic 11 stories)

### Epic 10.7: Paper Trading Profitability & Execution Quality Sprint
System enters positions only when both platforms can support the trade, calculates edge using realistic VWAP fill prices, monitors exits with accurate depth metrics, and tracks P&L for every closed position.
**FRs covered:** FR-EX-03 (strengthened), FR-EX-03a (expanded), FR-EX-09 (new), FR-EM-03 (C5 fix)
**Additional:** realized_pnl bug fix, shadow comparison fix, dynamic edge threshold, trading windows

**Context (Course Correction 2026-03-23):** Analysis of all 202 paper trading positions revealed 0% profitability. Root causes: phantom edges from thin Polymarket books, C5 depth metric VWAP circularity, missing P&L tracking, excessive pair concentration. See `sprint-change-proposal-2026-03-23-paper-profitability.md` for full evidence and analysis.

**Capacity Budget (Agreement #22):** 9 base stories, expect 12-13 total with 30-40% correction buffer.

## Epic 10.7: Paper Trading Profitability & Execution Quality Sprint

System enters positions only when both platforms can support the trade, calculates edge using realistic VWAP fill prices, monitors exits with accurate depth metrics, and tracks P&L for every closed position.

### Story 10-7-1: Pre-Trade Dual-Leg Liquidity Gate [P0]

As an operator,
I want the system to verify sufficient order book depth on both platforms before entering any position,
So that positions are only opened when both legs can realistically execute at target size.

**Context:** Current FR-EX-03 / Story 6-5-5b checks depth per-leg sequentially — primary leg is submitted before secondary depth is verified. 99.7% of 605 order failures were Polymarket insufficient liquidity. Position sizes of ~47 contracts entered against 1-6 contract deep books.

**Acceptance Criteria:**

**Given** an opportunity passes risk validation and is locked for execution
**When** the execution service prepares to submit orders
**Then** order book depth is fetched for BOTH platforms before EITHER leg is submitted
**And** the minimum total book depth across both legs is compared against the target position size
**And** if either leg has total depth < `DUAL_LEG_MIN_DEPTH_RATIO` × target size (configurable, default: 1.0), the opportunity is rejected
**And** rejection emits `execution.opportunity.filtered` with reason `"insufficient dual-leg depth"` and depth details per platform

**Given** both legs pass the dual-leg depth check
**When** depth is sufficient but asymmetric
**Then** position size is capped to the minimum of both legs' available depth
**And** if the capped size falls below the minimum fill threshold, the opportunity is rejected

**Given** the dual-leg gate is in place
**When** a depth check API call fails on either platform
**Then** the opportunity is rejected (fail-closed)
**And** a `execution.depth-check.failed` event is emitted with error context

**Given** the pre-trade depth gate configuration
**When** the engine starts
**Then** `DUAL_LEG_MIN_DEPTH_RATIO` is loaded from EngineConfig DB (default: 1.0)
**And** the setting appears in the dashboard Settings page under "Execution" group

**PRD Impact:** FR-EX-03 amended — dual-leg verification before either leg is submitted.

### Story 10-7-2: VWAP Slippage-Aware Opportunity Edge Calculation [P0]

As an operator,
I want the system to calculate expected edge using VWAP fill prices at target position size,
So that the displayed edge accurately reflects what execution would actually achieve.

**Context:** Expected edge at entry averaged +3.4% but collapsed to -17.5% on recalculation. Detection uses best-level prices; execution fills across multiple levels at worse prices. `calculateVwapClosePrice()` in `financial-math.ts` already walks the book — reuse at detection stage.

**Acceptance Criteria:**

**Given** an opportunity is detected with a cross-platform price gap
**When** the edge calculator computes net edge
**Then** it uses `calculateVwapClosePrice()` to estimate fill prices for BOTH legs at the target position size
**And** the VWAP-estimated prices replace best-bid/ask in the edge formula
**And** the edge includes estimated fees and gas at the VWAP-estimated prices

**Given** order book depth is insufficient to VWAP-price the full target size
**When** the VWAP calculation returns a partial fill
**Then** the edge is calculated at the partial fill VWAP
**And** if the partial fill is below minimum fill threshold, the opportunity is filtered before risk validation

**Given** a computed VWAP-based edge
**When** it falls below the minimum edge threshold (FR-AD-03)
**Then** the opportunity is filtered with reason `"VWAP-adjusted edge below threshold"`
**And** both the best-level edge and VWAP-adjusted edge are logged for comparison

**Depends on:** 10-7-1 (shares depth-fetching pattern)

### Story 10-7-3: C5 Exit Depth Slippage Band Correction [P0]

As an operator,
I want the C5 liquidity_deterioration criterion to count depth within a configurable slippage band around VWAP,
So that the depth metric doesn't systematically understate executable liquidity.

**Context:** Confirmed VWAP circularity: `calculateVwapClosePrice()` walks the full book, blending worse prices. `getAvailableExitDepth()` uses that VWAP as a hard cutoff, excluding the liquidity that produced it. C5 fired on 93.4% of exits with detail `"Min depth 1 vs required 5"`.

**Acceptance Criteria:**

**Given** a position is being evaluated for exit by the C5 criterion
**When** `getAvailableExitDepth()` computes available depth
**Then** the price cutoff is `closePrice × (1 + EXIT_DEPTH_SLIPPAGE_TOLERANCE)` for buy-close
**And** the price cutoff is `closePrice × (1 - EXIT_DEPTH_SLIPPAGE_TOLERANCE)` for sell-close
**And** `EXIT_DEPTH_SLIPPAGE_TOLERANCE` defaults to 0.02 (2%) and is configurable via EngineConfig DB

**Given** the slippage band is applied
**When** depth is computed
**Then** levels at prices within the tolerance band of VWAP are included in the depth count
**And** levels beyond the tolerance band are excluded

**Given** the configuration
**When** the engine starts
**Then** `EXIT_DEPTH_SLIPPAGE_TOLERANCE` appears in Settings under "Exit Strategy" group
**And** a value of 0.0 restores the original strict-VWAP behavior (backward-compatible)

### Story 10-7-4: Realized P&L Computation Investigation & Fix [P0]

As an operator,
I want `realized_pnl` accurately computed and persisted for every closed position,
So that I can evaluate the system's actual profitability.

**Context:** Story 10-0-2 (2026-03-16) claims `realizedPnl DB persistence (3 close paths)`. Database analysis (2026-03-23) shows `realized_pnl = NULL` for ALL 198 closed positions. Investigation-first pattern (Epic 9 retro convention).

**Acceptance Criteria:**

**Given** the existing `realized_pnl` computation code
**When** this story is investigated
**Then** the root cause of all-NULL values is documented before any code changes

**Given** the root cause is identified
**When** the fix is applied
**Then** `realized_pnl` is populated for every position closed via: model-driven exit, shadow exit, manual close, auto-unwind, and close-all
**And** the formula is: `Σ (exit_proceeds - entry_cost - fees)` across both legs using `decimal.js`

**Given** positions are closed in paper mode
**When** paper fills are simulated
**Then** `realized_pnl` is still computed using the simulated fill prices

**Given** the fix is deployed
**When** new positions are closed
**Then** `realized_pnl` is non-null for every closed position

### Story 10-7-5: Exit Execution Chunking & Polymarket Liquidity Handling [P1]

As an operator,
I want exit orders split into smaller chunks matching available liquidity,
So that single-leg exposure on exit is reduced.

**Context:** 235 single-leg exposure events. Kalshi exits fill, Polymarket fails with "Partial exit — remainder contracts unexited" (code 2008).

**Acceptance Criteria:**

**Given** an exit is triggered for a position
**When** the exit execution prepares orders
**Then** available depth on both platforms is checked before submitting exit orders
**And** if available depth on either platform is less than position size, the exit is chunked into smaller orders
**And** each chunk attempts both legs before proceeding to the next

**Given** a partial exit completes
**When** the next exit evaluation cycle runs
**Then** the position size reflects the remaining (unexited) contracts
**And** the exit monitor continues evaluating the residual position

**Given** a chunked exit where one leg fills but the other fails
**When** single-leg exposure occurs at the chunk level
**Then** the exposure is limited to the chunk size (not the full position)
**And** existing auto-unwind logic (Story 10-3) handles chunk-level exposure

**Given** configurable chunking
**When** the operator sets `EXIT_MAX_CHUNK_SIZE`
**Then** exit orders never exceed this size; default is unlimited (backward-compatible)

**Depends on:** 10-7-3 (uses corrected depth metric)

### Story 10-7-6: Per-Pair Position Cooldown & Concentration Limits [P1]

As an operator,
I want per-pair position frequency limits and concentration caps,
So that the system doesn't repeatedly hammer the same thin order books.

**Context:** 2 pairs = 92% of 202 positions. xAI/Text Arena: 116 positions (57%), 162 single-leg events.

**Acceptance Criteria:**

**Given** a position was recently opened for a specific pair
**When** a new opportunity is detected within `PAIR_COOLDOWN_MINUTES` (default: 30)
**Then** the opportunity is filtered with reason `"pair cooldown active"`

**Given** a pair has `PAIR_MAX_CONCURRENT_POSITIONS` open positions (default: 2)
**When** a new opportunity is detected for the same pair
**Then** the opportunity is filtered before risk validation

**Given** position diversity requirements
**When** total open positions exceeds `PAIR_DIVERSITY_THRESHOLD` (default: 5)
**Then** new positions only allowed for pairs below the average positions-per-pair

**Given** settings
**When** the engine starts
**Then** all three settings in EngineConfig DB under "Risk Management" group

### Story 10-7-7: Shadow Exit Comparison Event Payload Fix [P1]

As an operator,
I want shadow exit comparison audit logs to contain actual decision data,
So that I can evaluate shadow vs. model exit performance.

**Context:** Story 10-2 shadow mode. 979 `execution.exit.shadow_comparison` entries, all fields NULL.

**Acceptance Criteria:**

**Given** the shadow comparison service evaluates a position
**When** it emits the comparison event
**Then** the payload includes: `shadowDecision`, `modelDecision`, `agreement`, `positionId`, `pairId`, `currentEdge`
**And** no fields are null when the comparison completes

**Given** shadow and model disagree
**When** the comparison is logged
**Then** divergence detail includes triggered criteria and proximity values

### Story 10-7-8: Dynamic Minimum Edge Threshold Based on Book Depth [P2]

As an operator,
I want the minimum edge threshold to scale dynamically with order book depth,
So that higher edges are demanded for illiquid markets.

**Context:** Positions entering at 1.5-2% edge are underwater after slippage on thin books.

**Acceptance Criteria:**

**Given** an opportunity passes the base minimum edge threshold (0.8%)
**When** the effective threshold is calculated
**Then** `effectiveMinEdge = baseMinEdge × (1 + DEPTH_EDGE_SCALING_FACTOR / min(kalshiDepth, polymarketDepth))`
**And** capped at `MAX_DYNAMIC_EDGE_THRESHOLD` (default: 5%)

**Given** deeply liquid markets
**When** the threshold is calculated
**Then** it converges to the base minimum (no penalty)

**Given** configuration
**Then** setting factor to 0 disables dynamic scaling (backward-compatible)

**Depends on:** 10-7-2 (builds on VWAP edge)

### Story 10-7-9: Trading Window Analysis & Time-of-Day Filtering [P2]

As an operator,
I want the system to optionally restrict trading to hours with adequate liquidity,
So that trades are placed when books can support them.

**Context:** 90% of positions opened 15:00-21:00 UTC. Investigation-first pattern.

**Acceptance Criteria:**

**Given** existing position data
**When** analysis is performed
**Then** findings document: avg depth per hour, fill success rate per hour, single-leg rate per hour

**Given** suboptimal hours identified
**When** trading windows implemented
**Then** `TRADING_WINDOW_START_UTC` and `TRADING_WINDOW_END_UTC` configurable (default: 0-24, no restriction)
**And** opportunities outside window filtered
**And** open positions still monitored regardless of window

### Epic 10.8: God Object Decomposition & Structural Refactoring
Decompose all identified God Objects into focused, single-responsibility services. Every refactored source file should be under ~600 lines. Zero functional changes — pure internal refactoring with 100% test pass rate maintained throughout.
**FRs covered:** None (internal quality improvement)
**Course correction:** 2026-03-23 — codebase audit identified 6 God Objects/Files accumulated over Epics 4–10.5 (RiskManagerService 1,651 lines, ExitMonitorService 1,438 lines, ExecutionService 1,395 lines, DashboardService 1,205 lines, TelegramMessageFormatter 789 lines, TelegramAlertService 734 lines).

**Prerequisites:** Epic 10.7 must be complete before refactoring begins (don't interrupt active feature work).

### Epic 10.95: TimescaleDB Migration, Time-Series Storage & Backtesting Quality
Migrate time-series tables to TimescaleDB hypertables with compression, reducing storage by ~90% (337 GB → <50 GB) and improving time-range query performance 10-50x, while maintaining full Prisma compatibility. Additionally, address backtesting engine quality: performance optimization for monthly+ ranges, fix force-close statistics distortion, and add position detail view.
**FRs covered:** None (infrastructure optimization + backtesting quality)
**Course correction:** 2026-04-03 — database grew to 337 GB in ~3 months from 3 time-series tables (historical_prices 180 GB, historical_depths 151 GB, historical_trades 5.9 GB). 76 GB index bloat, cache hit rates below threshold. Projected 1.3 TB/year without intervention.
**Course correction:** 2026-04-06 — post-TimescaleDB backtesting quality issues: monthly ranges still slow (per-chunk depth reloading, LRU cache undersized), force-close at simulation end distorts P&L statistics, no position detail view in dashboard.

**Prerequisites:** Epic 10.9 complete. Full pg_dump backup before migration.

## Epic 10.95: TimescaleDB Migration & Time-Series Storage Optimization

Migrate time-series tables to TimescaleDB hypertables with compression, reducing storage by ~90% and improving query performance 10-50x, while maintaining full Prisma and SQL compatibility. TimescaleDB is a PostgreSQL extension — not a database replacement.

### Story 10-95-1: TimescaleDB Extension Installation & Proof of Concept

As an operator,
I want TimescaleDB installed and verified on the smallest time-series table,
So that I can validate the migration approach before converting larger tables.

**Acceptance Criteria:**

**Given** Docker Compose files use `postgres:16` image
**When** the migration is applied
**Then** both `docker-compose.yml` and `docker-compose.dev.yml` use `timescale/timescaledb-ha:pg16`
**And** existing data volumes are compatible (drop-in replacement)

**Given** TimescaleDB is not installed
**When** the Prisma migration runs
**Then** `CREATE EXTENSION IF NOT EXISTS timescaledb` succeeds
**And** the Prisma schema declares `extensions = [timescaledb]` in the datasource block

**Given** `historical_trades` (5.9 GB, smallest table) exists as a regular table
**When** the hypertable conversion runs
**Then** `SELECT create_hypertable('historical_trades', 'timestamp', migrate_data => true, chunk_time_interval => INTERVAL '1 day')` succeeds
**And** the Prisma schema uses `@@id([id, timestamp])` composite PK
**And** the unique constraint includes `timestamp`: `@@unique([platform, contractId, source, externalTradeId, timestamp])`

**Given** `historical_trades` is now a hypertable
**When** existing Prisma queries execute (findMany, create, createMany)
**Then** all operations succeed identically to before conversion

**Given** unused indexes exist on `historical_trades`
**When** the migration runs
**Then** `historical_trades_platform_contract_id_timestamp_idx` (0 scans, 676 MB) is dropped
**And** `historical_trades_timestamp_idx` (0 scans, 132 MB) is dropped

### Story 10-95-2: Hypertable Conversion — historical_prices & historical_depths

As an operator,
I want the two largest tables converted to hypertables with optimized indexes,
So that the database can handle long-term data growth efficiently.

**Acceptance Criteria:**

**Given** `historical_prices` (180 GB, 248M rows) exists as a regular table
**When** the migration runs
**Then** `create_hypertable('historical_prices', 'timestamp', migrate_data => true, chunk_time_interval => INTERVAL '1 day')` succeeds
**And** Prisma schema uses `@@id([id, timestamp])` composite PK

**Given** `historical_depths` (151 GB, 106M rows) exists as a regular table
**When** the migration runs
**Then** `create_hypertable('historical_depths', 'timestamp', migrate_data => true, chunk_time_interval => INTERVAL '1 day')` succeeds
**And** Prisma schema uses `@@id([id, timestamp])` composite PK

**Given** bloated/rarely-used indexes exist (76 GB total bloat)
**When** hypertable conversion completes
**Then** the following indexes are dropped:
- `historical_prices_contract_id_source_timestamp_idx` (27 GB, 23 scans)
- `historical_prices_timestamp_idx` (2.1 GB, 32 scans)
- `historical_depths_timestamp_idx` (2.9 GB, 28 scans)

**Given** both tables are converted to hypertables
**When** backtesting queries run (price lookups, depth snapshots, OHLCV aggregation)
**Then** all results match pre-migration output

**Given** the migration involves large data movement (~330 GB)
**When** the migration is planned
**Then** a full `pg_dump` backup is taken before execution
**And** a maintenance window is scheduled (estimated: 2-4 hours)

### Story 10-95-3: Compression Policies, Retention & Observability

As an operator,
I want old data automatically compressed and retention policies enforced,
So that storage stays bounded and I can monitor compression effectiveness.

**Acceptance Criteria:**

**Given** all three hypertables exist
**When** compression is enabled
**Then** each table has compression configured with `segmentby = 'platform, contract_id, source'` and `orderby = 'timestamp DESC'`

**Given** compression policies are set (7-day interval)
**When** chunks older than 7 days exist
**Then** they are automatically compressed
**And** compressed chunks remain fully queryable via Prisma

**Given** existing data spans ~3 months
**When** manual compression of old chunks is triggered
**Then** all chunks older than 7 days are compressed
**And** total database size drops from ~337 GB to target <50 GB

**Given** retention policies are configured via EngineConfig with differentiated defaults
**When** the retention interval elapses
**Then** raw data older than the configured period is automatically dropped (chunk-level DROP, no vacuum overhead):
- `historical_prices`: 2 years (walk-forward validation across multiple market regimes)
- `historical_trades`: 1 year (seasonal pattern coverage)
- `historical_depths`: 6 months (heaviest table — compression target)
**And** operator is notified via Telegram when retention runs
**And** retention periods are configurable but defaults are non-negotiable (per Epic 10.9 retro)

**Given** compressed data exists
**When** the operator views the dashboard System Health page
**Then** a new "Storage" section shows total database size, per-table compressed vs uncompressed size, compression ratio, and chunk count

### Story 10-95-4: BacktestEngineService Decomposition (Added by Epic 10.9 Retro)

As a developer,
I want BacktestEngineService decomposed into focused sub-services,
So that the codebase doesn't carry a 917-line God Object with 9 constructor dependencies into Epic 11.

**Context:** Added during Epic 10.9 retrospective. BacktestEngineService grew from ~380 lines (10-9-3) to 917 lines (10-9-3a) with 9 constructor dependencies (exceeding facade ≤8 threshold). Decomposition seams are already visible. Uses the facade decomposition playbook proven in Epic 10.8. Slotted as final 10.95 story — can slip to Epic 11 if correction buffer consumed, but default plan is completion before Epic 11.

**Acceptance Criteria:**

**Given** BacktestEngineService is 917 formatted lines with 9 constructor dependencies
**When** decomposition is complete
**Then** `WalkForwardRoutingService` is extracted (walk-forward train/test splitting, headless run management, out-of-sample validation orchestration)
**And** `ChunkedDataLoadingService` is extracted (chunked time-window processing, cursor-based pagination, batch depth pre-loading, chunk progress events)
**And** BacktestEngineService remains as a facade delegating to the new services
**And** BacktestEngineService constructor has ≤8 dependencies
**And** BacktestEngineService is under 600 formatted lines
**And** all existing tests pass with zero behavioral changes
**And** extracted services have co-located spec files with tests migrated from the original

**Dependencies:** Stories 10-95-1 through 10-95-3 complete (migration stable)
**Blocks:** Clean entry into Epic 11

### Story 10-95-5: Backtest Engine Performance Optimization for Extended Date Ranges (Added by Course Correction 2026-04-06)

As an operator,
I want monthly+ backtests to complete in reasonable time (minutes, not tens of minutes),
So that I can run calibration sweeps over meaningful historical periods without waiting excessively.

**Context:** Post-TimescaleDB migration, short-range backtests improved but monthly ranges remain slow. Three compounding bottlenecks: per-chunk depth re-loading (30 cycles for 30-day backtest), LRU cache undersized (2K entries vs ~4.4M unique keys), sequential per-position depth lookups falling back to N+1 `findFirst()`.

**Acceptance Criteria:**

1. **Given** a 30-day backtest with 50+ active pairs
   **When** the backtest runs end-to-end
   **Then** total wall-clock time is at least 3x faster than current baseline

2. **Given** the depth data loader
   **When** loading depths for a chunk
   **Then** a single batch query fetches depths for all contracts (no per-contract `findFirst()` fallback)
   **And** the batch query leverages TimescaleDB chunk exclusion via time-range predicates

3. **Given** the depth caching strategy
   **When** a backtest spans multiple chunks
   **Then** depth cache is shared across chunk boundaries using a sliding window or range-based pre-load
   **And** the cache size is dynamically bounded by available memory (configurable max, default 512MB RSS budget)

4. **Given** a time step with N open positions
   **When** `evaluateExits()` needs depth data
   **Then** all N depth lookups are resolved from pre-loaded cache (zero individual DB queries during simulation loop)
   **And** cache misses are logged at WARN level

5. **Given** existing backtest tests
   **When** the optimization is applied
   **Then** all existing tests pass without modification and results are identical to pre-optimization output

6. **Given** the backtest engine emits progress events
   **When** a chunk completes
   **Then** the event includes `depthCacheHitRate` and `depthQueriesExecuted`

**Dependencies:** Benefits from 10-95-4 (engine decomposition creates `ChunkedDataLoadingService`)

### Story 10-95-6: Replace Simulation-End Force-Close with Open Position Reporting (Added by Course Correction 2026-04-06)

As an operator,
I want backtests to leave open positions unclosed at simulation end and instead report blocked capital separately,
So that backtest statistics accurately reflect realized trading performance without artificial losses from force-closed positions.

**Context:** `closeRemainingPositions()` force-closes all open positions at simulation end with `exitReason: 'SIMULATION_END'` and `exitEdge: 0`, inflating loss count and depressing total P&L, profit factor, win rate, and Sharpe ratio. In live trading these positions would remain open.

**Acceptance Criteria:**

1. **Given** a backtest completes with N open positions remaining
   **When** the simulation ends
   **Then** those positions are **not** closed

2. **Given** open positions exist at simulation end
   **When** results are persisted
   **Then** each open position is stored with null exit fields + calculated `unrealizedPnl`
   **And** `BacktestRun` stores `openPositionCount`, `blockedCapitalUsd`, `unrealizedPnlUsd`

3. **Given** aggregate metrics are calculated
   **When** open positions exist
   **Then** all metrics reflect **only naturally closed positions**

4. **Given** the backtest detail page
   **When** the run has open positions
   **Then** a "Blocked Capital" section shows: open position count, total capital blocked, estimated unrealized P&L, percentage of initial capital blocked
   **And** the Positions tab distinguishes open vs closed positions

**Dependencies:** Independent of 10-95-5. Prisma migration required (new fields + nullable exitReason).

### Story 10-95-7: Backtest Position Detail View (Added by Course Correction 2026-04-06)

As an operator,
I want to click on a backtest position row and see a detailed view of that position,
So that I can understand the rationale, P&L breakdown, and conditions for each individual backtest trade.

**Context:** Live trading has `PositionDetailPage` (613 lines, 8 sections) at `/positions/:id`. Backtest positions table shows 13 columns inline with no click-through. Operators need the same drill-down capability.

**Acceptance Criteria:**

1. **Given** the backtest Positions tab
   **When** the operator clicks a position row
   **Then** a detail view opens for that position

2. **Given** a closed backtest position detail view
   **When** the view renders
   **Then** it displays: Entry section (prices, size, edge, timestamp, contract IDs), Exit section (reason, prices, edge, duration), P&L Breakdown (per-leg P&L, fees, net realized), Sides & Strategy description

3. **Given** an open backtest position detail view (from 10-95-6)
   **When** the view renders
   **Then** Exit section shows "Position still open at simulation end" with unrealized P&L and blocked capital

4. **Given** the backend API
   **When** `GET /backtesting/runs/:runId/positions/:positionId` is called
   **Then** it returns the full position record, 404 if position doesn't belong to run

5. **Given** the detail view component
   **When** implemented
   **Then** it reuses existing UI primitives from live `PositionDetailPage` where applicable
   **And** sections not applicable to backtesting are omitted (Auto-Unwind, Exit Criteria, Execution Info, Order History, Audit Trail)

**Dependencies:** Depends on 10-95-6 (open position fields and UI patterns)

### Story 10-95-8: Backtest Zero-Price Filtering & Exit Fee Accounting (Added by Course Correction 2026-04-08)

As an operator,
I want the backtest engine to reject zero-price historical candles and deduct realistic exit fees from realized P&L,
So that backtest results reflect actual tradeable opportunities and accurate profit/loss accounting.

**Context:** Backtest run `fd98b78e` (Mar 1-5, $10K bankroll) lost $2,929.70 due to: (1) 95.2% of Kalshi historical price rows being zero-volume candles treated as real prices, creating phantom edges averaging 67.3%, and (2) missing exit fee deduction in `backtest-portfolio.service.ts:closePosition()`.

**Acceptance Criteria:**

1. Data loader SQL (`loadAlignedPricesForChunk`) excludes rows where Kalshi or Polymarket `close = 0`
2. TypeScript defense-in-depth guard rejects zero-price rows after Decimal conversion; excluded rows counted in chunk progress events
3. Backtest report `dataQuality` section includes `zeroRowsExcluded`, `zeroRowsExcludedPct`, `perPlatformExclusion`
4. `closePosition()` computes exit fees using `FinancialMath.calculateTakerFeeRate()` with platform fee schedules; `realizedPnl = legPnl - fees`; `fees` field populated (not null)
5. Capital tracking accounts for fee-deducted PnL
6. Configurable maximum edge threshold (default 15%) rejects phantom signals
7. Dashboard Summary tab shows "Data Quality" card with exclusion stats and >20% warning banner
8. All existing tests pass; new tests cover zero-price filtering, fee calculation, edge cap, data quality metrics

**Dependencies:** None (10-95-1 through 10-95-7 all complete).

### Story 10-95-9: Backtest Exit Logic Fix & Full-Cost PnL Accounting (Added by Course Correction 2026-04-10)

As an operator,
I want the backtest PROFIT_CAPTURE exit to verify actual position profitability before triggering, and realized P&L to include all trading costs (entry fees + gas),
So that backtest exit classifications are accurate and P&L reflects true economics.

**Context:** Backtest run `e90b5698` (Mar 1-5, $10K bankroll) lost $937.90 after Story 10-95-8 fixed zero-price contamination and added exit fees. Two remaining defects: (1) PROFIT_CAPTURE exit condition (`exit-evaluator.service.ts:104`) fires on edge convergence regardless of PnL direction — ALL 39 PROFIT_CAPTURE exits were losers (avg -$9.23, 84.6% had adverse Kalshi price movement). (2) Entry fees (~$4.5-5.5/position) and gas ($0.50/position) omitted from `realizedPnl` in `backtest-portfolio.service.ts:240`.

**Acceptance Criteria:**

1. PROFIT_CAPTURE exit requires `capturedRatio >= exitProfitCapturePct` AND mark-to-market PnL > 0 (using `calculateLegPnl()` for both legs). If `mtmPnl <= 0`, condition returns false (falls through to other triggers).
2. `ExitEvaluationParams` includes position entry prices, current prices, sides, and size for PnL calculation. Uses existing `calculateLegPnl` from `common/utils/financial-math.ts`.
3. `openPosition()` computes and stores entry fees (`entryFees: Decimal`) and gas cost (`gasCost: Decimal`) on `SimulatedPosition` using `FinancialMath.calculateTakerFeeRate()` with platform fee schedules.
4. `closePosition()` computes `realizedPnl = kalshiPnl + polyPnl - exitFees - entryFees - gasCost`. `fees` field = `entryFees + exitFees`. Capital tracking uses fully-net PnL.
5. `edgeThresholdPct` default raised from 0.008 to 0.03. Config validation rejects values below 0.02. Existing `maxEdgeThresholdPct` (15%) remains.
6. New `STOP_LOSS` exit condition: triggers when mark-to-market PnL drops below `-exitStopLossPct * positionSizeUsd` (default 15%). Priority between INSUFFICIENT_DEPTH (2) and PROFIT_CAPTURE (3). New `BacktestExitReason` enum value added via Prisma migration.
7. `calculateUnrealizedPnl()` includes entry fees + gas: `unrealizedPnl = mtmPnl - estimatedExitFees - entryFees - gasCost`.
8. All existing tests pass. New tests: PROFIT_CAPTURE positive/negative PnL paths, entry fee storage, full-cost PnL, STOP_LOSS trigger/non-trigger, edge threshold validation, unrealized PnL cost components.

**Dependencies:** None (10-95-1 through 10-95-8 all complete).

### Story 10-95-10: Backtest Side Selection Fix & Depth Exit Improvement (Added by Course Correction 2026-04-11)

As an operator,
I want the backtest engine to correctly determine arbitrage direction per opportunity and not force-close positions on depth cache misses,
So that backtest results reflect actual arbitrage profitability rather than systematic wrong-direction trading and spurious exits.

**Context:** Backtest run `09b344c7` (Mar 1-5, $10K bankroll, post-10-95-9) lost $1,078.97 with 8.1% win rate. Root cause investigation revealed:

1. **Side selection is a no-op:** `calculateBestEdge()` in `edge-calculation.utils.ts:9-27` computes `edgeA = grossEdge(kalshi, 1-poly)` and `edgeB = grossEdge(poly, 1-kalshi)`. Since `grossEdge(a,b) = b - a`, both resolve to `1 - kalshi - poly` (addition is commutative). `edgeA.gt(edgeB)` is never true, so `buySide` always defaults to `'polymarket'`. Result: ALL 141 positions are SELL Kalshi / BUY Polymarket regardless of which platform has the higher price. 52 positions where Poly > Kalshi entered anti-arbitrage (0% win rate, -$587.54).

2. **INSUFFICIENT_DEPTH exits on cache misses:** `hasDepth = kalshiDepth !== null && polyDepth !== null` at `backtest-engine.service.ts:525` force-closes positions whenever depth data is missing from the cache for either platform — regardless of whether liquidity actually exists. 87/111 closed positions (78%) exit this way, at -$757.75 total.

The prior course correction (2026-04-10) incorrectly dismissed the unidirectional bias: "Not a bug. If Kalshi consistently prices higher for the same events, SELL K / BUY P is the correct arb direction." DB evidence proves otherwise: 47% of positions have Poly > Kalshi, and 100% of those are losers.

**Acceptance Criteria:**

1. **Given** `calculateBestEdge()` in `edge-calculation.utils.ts`
   **When** `kalshiClose > polymarketClose`
   **Then** `buySide = 'polymarket'` (buy the cheaper Poly, sell the expensive Kalshi)
   **And** `bestEdge` reflects the net edge for this direction

2. **Given** `calculateBestEdge()` in `edge-calculation.utils.ts`
   **When** `polymarketClose > kalshiClose`
   **Then** `buySide = 'kalshi'` (buy the cheaper Kalshi, sell the expensive Poly)
   **And** `bestEdge` reflects the net edge for this direction

3. **Given** `calculateBestEdge()` in `edge-calculation.utils.ts`
   **When** `kalshiClose == polymarketClose`
   **Then** `bestEdge` is zero or negative (no arbitrage exists when prices are equal after fees)

4. **Given** the position creation in `backtest-engine.service.ts:647-661`
   **When** a position is opened
   **Then** `kalshiSide` and `polymarketSide` correctly reflect the `buySide` determination
   **And** positions where Kalshi is cheaper have `kalshiSide = 'BUY'`
   **And** positions where Poly is cheaper have `polymarketSide = 'BUY'`

5. **Given** the exit evaluation loop in `backtest-engine.service.ts:490-564`
   **When** depth data is missing from the cache for one or both platforms (`findNearestDepthFromCache` returns null)
   **Then** the position is NOT force-closed due to cache miss
   **And** exit evaluation proceeds using available price data (kalshiClose/polymarketClose from the time step)
   **And** `hasDepth` is set to `false` only when depth data IS present but shows insufficient liquidity for the position size

6. **Given** the `calculateCurrentEdge()` utility in `edge-calculation.utils.ts`
   **When** computing the current edge for an open position
   **Then** it uses the position's recorded `buySide` (not a re-computed buySide) to ensure edge direction consistency between entry and exit evaluation

7. **Given** the edge calculation regression test suite
   **When** `calculateBestEdge()` is called with kalshi=0.60, poly=0.40
   **Then** `buySide = 'polymarket'` and `bestEdge > 0`
   **When** called with kalshi=0.35, poly=0.55
   **Then** `buySide = 'kalshi'` and `bestEdge > 0`
   **When** called with kalshi=0.50, poly=0.50
   **Then** `bestEdge <= 0` (no arb after fees)

8. **Given** a re-run of the Mar 1-5 backtest with the same config as run `09b344c7`
   **When** the backtest completes
   **Then** positions show BOTH directions (SELL K / BUY P and BUY K / SELL P) in the results
   **And** INSUFFICIENT_DEPTH exits represent < 30% of closed positions (down from 78%)
   **And** win rate improves significantly from the 8.1% baseline

**Tasks:**

1. **Fix `calculateBestEdge()` side determination** — Replace the symmetric edge comparison with a direct price comparison: if `kalshiClose > polymarketClose`, `buySide = 'polymarket'`; otherwise `buySide = 'kalshi'`. Compute `bestEdge` using the gross edge for the selected direction. Ensure the gross edge is positive for valid arb opportunities.

2. **Fix depth exit logic** — In `backtest-engine.service.ts`, change `hasDepth` semantics: `null` depth (cache miss) should NOT trigger INSUFFICIENT_DEPTH. Only trigger when depth data exists but shows insufficient liquidity. When depth is null, proceed with exit evaluation using mid-price (kalshiClose/polymarketClose already available).

3. **Add `buySide` to `SimulatedPosition`** — Store the entry-time `buySide` on the position so that `calculateCurrentEdge()` for exit evaluation uses the same direction as entry. Add field to simulation types.

4. **Update `calculateCurrentEdge()` for open positions** — Accept an optional `buySide` parameter. When evaluating exits for open positions, pass the stored `buySide` to ensure directional consistency. Current implementation re-computes buySide each tick, which with the fix could flip direction mid-position.

5. **Regression tests for side selection** — Add tests for `calculateBestEdge()` covering: kalshi > poly → buySide 'polymarket'; poly > kalshi → buySide 'kalshi'; equal prices → non-positive edge; extreme prices (0.02/0.95); symmetric prices around 0.50.

6. **Regression tests for depth exit** — Add tests verifying: null depth (cache miss) does NOT trigger INSUFFICIENT_DEPTH; present-but-insufficient depth DOES trigger; exit evaluation proceeds normally on cache miss.

7. **Update existing tests** — Fix any existing tests that implicitly depend on buySide always being 'polymarket' or hasDepth always being false on null.

8. **Validation backtest** — Re-run Mar 1-5 with same config. Verify bidirectional positions, reduced INSUFFICIENT_DEPTH rate, improved win rate.

**Technical Notes:**
- The fix in `calculateBestEdge()` is surgical: replace the edge comparison with a price comparison. The gross edge calculation and net edge calculation are both correct — only the side determination is broken.
- For depth exit: the current `findNearestDepthFromCache()` returns `null` for cache misses AND for genuinely empty order books. Consider distinguishing these cases (cache miss = no data point near the timestamp vs empty book = data point exists but no levels). Simplest approach: treat null as "no data available, proceed with price-only evaluation."
- No Prisma migration needed. No new DB fields (buySide is stored on the in-memory `SimulatedPosition`, not persisted — the DB already has `kalshi_side`/`polymarket_side` columns which will now correctly vary).
- This story addresses the prior course correction's incorrect dismissal of the direction bias. The evidence is unambiguous: 52 positions with Poly > Kalshi have 0% win rate.

**Dependencies:** 10-95-9 complete (STOP_LOSS, PROFIT_CAPTURE PnL guard, full-cost accounting all in place).

### Story 10-95-11: Backtest Edge Metric Realignment (Added by Course Correction 2026-04-12)

As an operator,
I want the backtest engine to use the same edge formula as the PRD and live detection engine (`|K-P|` price discrepancy instead of `1-K-P` overround gap),
So that backtest entry/exit decisions predict actual profitability and results can be compared to live performance.

**Context:** Backtest run `9bab5cf5` (Mar 1-5, $10K bankroll, post-10-95-10) lost -$3,406 on 436 positions (7.1% win rate). Root cause investigation revealed the backtest engine's `calculateBestEdge()` uses `1-K-P` (overround gap) while both the PRD (FR-AD-02 Edge Calculation Formula) and the live detection engine (`detection.service.ts:190-217`, fixed in March 3 SCP) use `|K-P|` (price discrepancy). These metrics differ by `|1-2*sellSidePrice|`, averaging 6-22 cents. 70% of positions (304/436) have the coded net edge exceeding the raw `|K-P|` gap, meaning the engine enters trades where maximum possible profit cannot cover predicted edge. Additionally, `calculateNetEdge()` uses complement prices (`1-P`) instead of actual trade prices for fee deductions, diverging from the PRD example formulas.

**Acceptance Criteria:**

1. **Given** `calculateBestEdge()` **when** computing gross edge **then** returns `max(K,P) - min(K,P)` (= `|K-P|`), matching `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` as used by the live detection engine.

2. **Given** `calculateNetEdge()` **when** computing fee deductions **then** uses actual trade prices (`kalshiClose`, `polymarketClose`) instead of complement prices (`1-polymarketClose`, `1-kalshiClose`). Matches the PRD example: "Buy fee cost (Polymarket at 0.58): 0.58 x 0.02 = 0.0116; Sell fee cost (Kalshi at 0.62): 0.62 x 0.0266 = 0.01649."

3. **Given** `calculateCurrentEdge()` **when** evaluating open position edge **then** uses the same `|K-P|` metric with actual prices, preserving the `entryBuySide` parameter (from 10-95-10).

4. **Given** `edgeThresholdPct` configuration **then** default raised from 0.03 to 0.05 and minimum floor recalibrated to ensure threshold exceeds roundtrip fees per unit (~5% for $200 positions with ~$10 roundtrip fees).

5. **Given** `maxEdgeThresholdPct` configuration **then** recalibrated for the `|K-P|` metric: raised from 0.15 to 0.40 (price gaps can legitimately exceed 15% when platforms genuinely disagree).

6. **Given** existing tests **when** all run **then** all pass with updated assertions for new formula. Regression tests added comparing backtest edge output to PRD examples.

**Tasks:**

1. **Fix `calculateBestEdge()` gross edge** — Change from `1-K-P` to `max(K,P) - min(K,P)`. Use `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` directly (buyPrice = min, sellPrice = max). Side determination (price comparison from 10-95-10) is already correct — do not change it.

2. **Fix `calculateNetEdge()` sell price** — Change `sellPrice` from `1-polymarketClose` / `1-kalshiClose` to actual `polymarketClose` / `kalshiClose`. Both fee schedules should compute fees at the actual trade price.

3. **Fix `calculateCurrentEdge()` gross edge** — Change from `1-K-P` to `max(K,P) - min(K,P)`, maintaining the `entryBuySide` parameter for directional consistency.

4. **Recalibrate thresholds** — Update `edgeThresholdPct` default (0.03 → 0.05), min (0.02 → 0.04). Update `maxEdgeThresholdPct` default (0.15 → 0.40).

5. **Update edge-calculation.utils.spec.ts** — All edge value assertions must change. Add PRD example as explicit regression test: K=0.62, P=0.58 → grossEdge=0.04, buySide='polymarket'.

6. **Update fixture files** — Any with `edgeThresholdPct` below 0.04 must be raised.

7. **Validation backtest** — Re-run Mar 1-5 after fix. Verify edge values align with `|K-P|` metric.

**Technical Notes:**
- `FinancialMath.calculateGrossEdge()` and `FinancialMath.calculateNetEdge()` in `common/utils/financial-math.ts` are already correct — they use actual prices. Only the backtest wrapper functions in `edge-calculation.utils.ts` are wrong.
- PnL accounting in `backtest-portfolio.service.ts` is independent of the edge metric and already correct (from 10-95-9).
- Entry fee computation in `detectOpportunities()` already uses actual prices (correct from 10-95-9). Only the edge threshold check uses the wrong metric.

**Dependencies:** 10-95-10 complete (side selection + buySide on position).

### Story 10-95-12: Backtest Pair Re-Entry Cooldown (Added by Course Correction 2026-04-12)

As an operator,
I want the backtest engine to enforce a cooldown period before re-entering the same pair after a TIME_DECAY exit,
So that the simulation doesn't churn through persistent non-converging edges, accumulating fees without new information.

**Context:** In backtest run `9bab5cf5`, the top pair was entered 76 times at 1.24-hour intervals, losing $761. Top 3 pairs account for 42% of total loss ($1,421) from fee churning alone. After TIME_DECAY exit, the engine immediately re-enters because the persistent edge still exceeds the threshold. No cooldown or condition-change requirement exists.

**Acceptance Criteria:**

1. **Given** a position exits via TIME_DECAY **when** the same pair appears as a candidate in subsequent timesteps **then** the pair is skipped until `cooldownHours` have elapsed since the exit timestamp.

2. **Given** a position exits via EDGE_EVAPORATION, PROFIT_CAPTURE, STOP_LOSS, or RESOLUTION_FORCE_CLOSE **when** the same pair reappears **then** no cooldown is enforced (these exits indicate changed market conditions).

3. **Given** `cooldownHours` configuration **then** defaults to `exitTimeLimitHours` value. Configurable via `IBacktestConfig` with `@IsNumber() @Min(0) @IsOptional()` validation.

4. **Given** cooldown tracking **then** tracked per-pair in simulation loop via `Map<pairId, lastTimeDecayExit>`. Cleanup: entries expire after cooldownHours, map cleared at simulation end. `/** Cleanup: entries expire after cooldownHours, .clear() on simulation end */`

5. **Given** headless simulations (walk-forward, sensitivity) **then** cooldown state is independent per run (scoped by `tempRunId`).

6. **Given** existing tests **when** all run **then** all pass. New tests: cooldown blocks re-entry within period, allows after expiry, does not apply to non-TIME_DECAY exits, map cleanup works.

**Tasks:**

1. **Add `cooldownHours` to config** — `IBacktestConfig`, `BacktestConfigDto` with `@IsNumber() @Min(0) @IsOptional()` default = `exitTimeLimitHours`.

2. **Add cooldown map to simulation loop** — In `runSimulationLoop()`, initialize `Map<string, Date>` for cooldown tracking. On TIME_DECAY close, record exit timestamp per pair. In `detectOpportunities()`, skip pairs within cooldown window.

3. **Non-TIME_DECAY exits bypass cooldown** — Only record cooldown on TIME_DECAY. Other exit reasons indicate condition change.

4. **Cooldown tests** — Verify: blocks re-entry within period; allows after expiry; does not apply to EDGE_EVAPORATION/PROFIT_CAPTURE/STOP_LOSS exits; map cleanup at simulation end; headless isolation.

5. **Update config validation tests** — Add `cooldownHours` validation tests.

**Technical Notes:**
- The cooldown map is per-simulation-run, not per-pair-globally. Each `runSimulationLoop()` invocation gets its own map.
- Collection lifecycle: `/** Cleanup: .delete() on cooldown expiry check, .clear() at end of runSimulationLoop */`
- No Prisma changes. No new exit reasons. This is purely an entry filter.

**Dependencies:** 10-95-11 complete (correct edge metric ensures cooldown operates on meaningful entry decisions).

### Story 10-95-13: Backtest Entry Liquidity Filter & Stop-Loss Recalibration (Added by Course Correction 2026-04-12)

As an operator,
I want the backtest engine to reject entry into positions where one platform shows stale or illiquid pricing, and I want a tighter stop-loss default,
So that the simulation avoids illusory edges from liquidity asymmetry and cuts losses faster on diverging positions.

**Context:** In backtest run `2d2f84ac`, 8 STOP_LOSS exits (-$736) and 106 diverged TIME_DECAY exits (-$1,338) share the same root cause: one platform's price is stale/flat while the other moves dramatically. All 8 stop-loss pairs verified against `contract_matches` — descriptions and CLOB token IDs match correctly. These are NOT contract matching errors. The apparent "edge" is illusory because one platform has no real market activity (e.g., Polymarket at $0.002 with zero price movement). 62 of 106 diverged TIME_DECAY positions show identical one-sided flat-price movement (51 Polymarket flat, 11 Kalshi flat).

**Acceptance Criteria:**

1. **Given** a candidate entry opportunity **when** either platform's price is below `minEntryPricePct` (default 0.05) **then** the entry is skipped and a counter is incremented in the calibration report.

2. **Given** a candidate entry opportunity **when** the absolute price gap between platforms (`|kalshiPrice - polymarketPrice|`) exceeds `maxEntryPriceGapPct` (default 0.25) **then** the entry is skipped and a counter is incremented.

3. **Given** `exitStopLossPct` configuration **when** no explicit value is provided **then** the default is `0.15` (was `0.30`). `@Min(0.05) @Max(0.50)` validation range.

4. **Given** filtered entries **when** the calibration report is generated **then** a new "Liquidity Filters" section shows: total candidates evaluated, entries rejected by min-price filter (with per-platform breakdown), entries rejected by price-gap filter, and the configured thresholds.

5. **Given** existing tests **when** all run **then** all pass. New tests: min-price filter rejects below threshold, allows above; price-gap filter rejects above threshold, allows below; stop-loss triggers at 15% default; filter counters accumulate correctly in report; all three filters are configurable and independently disablable (min 0 disables).

**Tasks:**

1. **Add config parameters** — `minEntryPricePct` and `maxEntryPriceGapPct` to `IBacktestConfig` and `BacktestConfigDto` with `@IsNumber() @Min(0) @IsOptional()` validation. Update `exitStopLossPct` default from 0.30 to 0.15.

2. **Add entry filtering in opportunity detection** — In `detectOpportunities()` (or equivalent entry evaluation), add pre-entry checks for min price and price gap. Skip and count filtered entries.

3. **Accumulate filter metrics** — Track per-run counts of filtered entries by reason. Include in calibration report generation.

4. **Tests** — Verify: min-price blocks entry below threshold; price-gap blocks entry above threshold; stop-loss triggers at new default; filters configurable; counters accumulate; existing tests pass.

**Technical Notes:**
- Entry filters are evaluated before edge calculation to avoid wasted compute.
- Filter counters use the same `RunningAccumulators` pattern as existing metrics.
- Collection lifecycle: counters are primitives (no Map/Set cleanup needed).

**Dependencies:** 10-95-12 complete (all prior fixes in place).

### Story 10-95-14: PROFIT_CAPTURE Fee-Aware P&L Guard (Added by Course Correction 2026-04-12)

As an operator,
I want the backtest PROFIT_CAPTURE exit to verify post-fee profitability before triggering,
So that positions with small edge but large fees are not exited as "profit captures" when they would actually realize a loss.

**Context:** In backtest run `2d2f84ac`, 81 of 413 PROFIT_CAPTURE exits (20%) realized a net loss despite the P&L guard at `exit-evaluator.service.ts:120-133` checking `mtmPnl > 0`. The guard uses raw `calculateLegPnl()` (price movement only), but `closePosition()` at `backtest-portfolio.service.ts:262-266` deducts entry fees, exit fees, and gas. When raw P&L is positive but smaller than total fees, the guard approves exit but the actual result is negative.

Evidence:
- Losing PROFIT_CAPTURE avg: entry_edge 4.1%, raw P&L ~$8.40, fees ~$9.80, realized -$1.99
- Winning PROFIT_CAPTURE avg: entry_edge 8.8%, raw P&L ~$19.50, fees ~$7.46, realized +$12.06
- Win rate by entry edge: <5% = 61%, 5-6% = 84%, 6-8% = 95%, 8%+ = 100%

**Note:** Story 10-95-11 already raised the default `edgeThresholdPct` from 0.03 to 0.05, which prevents many low-edge entries. The fee-aware guard is still needed as defense-in-depth for positions that enter near the threshold.

**Acceptance Criteria:**

1. **Given** PROFIT_CAPTURE exit evaluation **when** `capturedRatio >= exitProfitCapturePct` **then** the P&L guard estimates total fees (entry fees from position + estimated exit fees using `FinancialMath.calculateTakerFeeRate()`) and checks `rawMtmPnl - estimatedTotalFees > 0`. If post-fee P&L <= 0, condition returns false (falls through to other exit triggers).

2. **Given** estimated exit fees in the P&L guard **then** uses the same fee estimation pattern as `calculateUnrealizedPnl()` in `backtest-portfolio.service.ts:46-55` (existing implementation that already includes exit fee calculation).

3. **Given** a position where raw mark-to-market P&L is positive but smaller than estimated total fees **when** PROFIT_CAPTURE is evaluated **then** it returns false and the position falls through to EDGE_EVAPORATION, TIME_DECAY, or STOP_LOSS as appropriate.

4. **Given** `ExitEvaluationParams` **then** includes `entryFees` and `gasCost` from the position record (already available on `SimulatedPosition`).

5. **Given** existing tests **when** all run **then** all pass. New tests: fee-aware guard rejects exit when raw P&L < total fees; fee-aware guard approves when raw P&L > total fees; guard correctly estimates exit fees using platform fee schedules; edge cases: zero fees, very small positions.

**Tasks:**

1. **Extend `ExitEvaluationParams`** — Add `entryFees: Decimal` and `gasCost: Decimal` (sourced from `SimulatedPosition`).

2. **Make P&L guard fee-aware** — In `isProfitCaptureTriggered()`, after computing raw `mtmPnl`, estimate exit fees using `FinancialMath.calculateTakerFeeRate()` for both platforms (same pattern as `calculateUnrealizedPnl`). Check `mtmPnl - exitFees - entryFees - gasCost > 0`.

3. **Pass position cost data to exit evaluator** — Ensure `evaluateExits()` call site passes entry fees and gas cost from the position.

4. **Tests** — Verify: guard rejects when raw P&L positive but < fees; guard accepts when raw P&L > fees; fee estimation matches `calculateUnrealizedPnl` pattern; parametric tests across fee schedule ranges.

**Technical Notes:**
- `SimulatedPosition` already carries `entryFees` and `gasCost` (added in Story 10-95-9).
- Exit fee estimation reuses `FinancialMath.calculateTakerFeeRate()` + `DEFAULT_KALSHI_FEE_SCHEDULE` / `DEFAULT_POLYMARKET_FEE_SCHEDULE` already imported in `backtest-portfolio.service.ts`.
- No new dependencies. No Prisma changes.

**Dependencies:** 10-95-12 complete. Independent of 10-95-13 (can be implemented in parallel).

### Epic 10.96: Live Trading Engine Alignment & Configuration Calibration
Port 5 backtest quality fixes (from stories 10-95-8 through 10-95-14) to the live trading engine and calibrate configuration defaults to backtest-validated settings. Live engine is disabled (early `return;` on line 65 of `trading-engine.service.ts`) — must not re-enable until 10.96 is complete.
**FRs covered:** FR-AD-03 (edge threshold), FR-RM-01 (position sizing), FR-EM-01 (exit thresholds) — strengthens existing requirements
**Course correction:** 2026-04-13 — backtest profitability analysis revealed 6 critical fixes exist only in backtest engine. Recalibrations: side selection bug (10-95-10) NOT in live (removed), edge formula (10-95-11) functionally correct in live (removed). 5 fixes to port across 4 stories.
**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-13-live-engine-alignment.md`

**Prerequisites:** Epic 10.95 complete. Hard sequencing gate before Epic 11.

## Epic 10.96: Live Trading Engine Alignment & Configuration Calibration

Port backtest-validated fixes to the live trading engine. First porting story (10-96-1) establishes the backtest-to-live pattern; stories 10-96-2 and 10-96-3 follow the template. Winston's design sketches gate all feature stories.

### Story 10-96-0: Structural Guards — configService Type Safety & Route Prefix Validation (Slot Zero)

As an operator,
I want configService.get() type-safety enforcement and route prefix validation as structural guards,
So that two recurring defect classes (string-typed config values, missing route prefixes) are prevented at compile/startup time rather than caught in review.

**Acceptance Criteria:**

**Given** `configService.get<boolean>()` returns strings (NestJS behavior)
**When** the structural guard is applied
**Then** a typed config accessor pattern replaces raw `configService.get()` calls with explicit parsing
**And** boolean/number env vars are parsed at the boundary, not trusted as generic types

**Given** route prefixes can be omitted on new controllers
**When** the structural guard is applied
**Then** a startup validation check verifies all controllers have route prefixes
**And** missing prefixes cause a startup error (fail-fast)

**Given** the dashboard API client was generated before recent endpoint changes
**When** this story completes
**Then** the API client is regenerated via `swagger-typescript-api`

**Context:** Agreement #26 items. Slipped Epics 10.9 and 10.95. Non-negotiable per Arbi directive (Agreement #34 slot-zero enforcement). Resolves debt ledger items #1, #2, #3.

### Story 10-96-1: Entry-Fee-Aware Exit PnL & Percentage Stop-Loss

As an operator,
I want the live exit evaluation to account for entry fees and gas in PnL calculations, and to enforce a percentage-based stop-loss,
So that PROFIT_CAPTURE exits are profitable after all costs and catastrophic positions are exited early.

**Acceptance Criteria:**

**Given** an open position with entry fee data (`entryKalshiFeeRate`, `entryPolymarketFeeRate`, `entryClosePriceKalshi`, `entryClosePricePolymarket`)
**When** the threshold evaluator computes `currentPnl`
**Then** `currentPnl = kalshiPnl + polymarketPnl - exitFees - entryFees - gasCost`

**Given** `exitStopLossPct` config setting (default 0.20)
**When** `currentPnl <= -exitStopLossPct × positionSizeUsd`
**Then** a STOP_LOSS exit is triggered

**Impacted files:** `threshold-evaluator.service.ts`, `exit-monitor.service.ts`, `config-defaults.ts`
**Ports from:** 10-95-9 + 10-95-14
**Backtest evidence:** Entry fees + gas = ~$800 invisible costs. Fee-unaware PROFIT_CAPTURE produced 81 losers. Two STOP_LOSS triggers prevented -$168 in catastrophic losses.
**Design sketch required:** Winston provides implementation site and service boundary before ready-for-dev.

### Story 10-96-2: Max Edge Cap & Entry Liquidity Filters

As an operator,
I want phantom edge signals and illiquid entries rejected before execution,
So that the live engine doesn't trade on data anomalies or stale pricing.

**Acceptance Criteria:**

**Given** `maxEdgeThresholdPct` config setting (default 0.35)
**When** `netEdge > maxEdgeThresholdPct`
**Then** the opportunity is rejected as a phantom signal

**Given** `minEntryPricePct` config setting (default 0.08)
**When** either platform's price < threshold
**Then** the opportunity is rejected

**Given** `maxEntryPriceGapPct` config setting (default 0.20)
**When** `|kalshiPrice - polymarketPrice| > threshold`
**Then** the opportunity is rejected

**Impacted files:** `edge-calculator.service.ts`, `trading-engine.service.ts`, `config-defaults.ts`
**Ports from:** 10-95-8 + 10-95-13
**Backtest evidence:** Phantom signals at 40%+ edge. Liquidity filters eliminated -$736 STOP_LOSS and -$1,338 diverged TIME_DECAY losses.
**Design sketch required:** Winston provides entry filter pipeline service boundary.

### Story 10-96-3: Post-TIME_DECAY Re-Entry Cooldown

As an operator,
I want the live engine to enforce a cooldown period after TIME_DECAY exits,
So that toxic pairs aren't immediately re-entered.

**Acceptance Criteria:**

**Given** `timeDecayCooldownHours` config setting (default 24)
**When** a position exits with reason TIME_DECAY
**Then** the pair is blocked from re-entry for `timeDecayCooldownHours`

**Given** a position exits with reason other than TIME_DECAY (PROFIT_CAPTURE, EDGE_EVAPORATION)
**When** cooldown is checked
**Then** the existing `pairCooldownMinutes` applies (shorter)

**Impacted files:** `pair-concentration-filter.interface.ts`, `pair-concentration-filter.service.ts`, `exit-monitor.service.ts`, `config-defaults.ts`
**Ports from:** 10-95-12
**Backtest evidence:** TIME_DECAY exits average -$9.10 P&L and 93h hold. Without cooldown, engine re-enters same toxic pair immediately.
**Design sketch required:** Winston provides cooldown-into-concentration-filter boundary.

### Story 10-96-4: Configuration Defaults Calibration

As an operator,
I want configuration defaults updated to backtest-validated values,
So that the live engine starts with settings proven to be profitable.

**Acceptance Criteria:**

**Given** the following config defaults exist in `config-defaults.ts`
**When** this story is applied
**Then** the values are updated:

| Setting | Current | New | Rationale |
|---------|---------|-----|-----------|
| `detectionMinEdgeThreshold` | `'0.008'` | `'0.05'` | Below 5%, fee drag makes entries negative EV |
| `detectionGasEstimateUsd` | `'0.30'` | `'0.50'` | Conservative estimate validated by backtest |
| `riskMaxOpenPairs` | `10` | `25` | Phase 1 PRD spec (FR-RM-02) |
| `exitProfitCaptureRatio` | `0.5` | `0.8` | 80% threshold validated — 100% win rate |
| `pairCooldownMinutes` | `30` | `60` | Modest increase for generic cooldown |

**Impacted files:** `config-defaults.ts`, DTO validation decorators if bounds need adjustment
**Depends on:** 10-96-0, 10-96-1, 10-96-2, 10-96-3 (settings must exist before calibrating)
**Backtest evidence:** Current defaults set during MVP before any backtest validation. Backtest profitable only after parameter tuning.

### Epic 11: Platform Extensibility & Security Hardening (Phase 1)
System supports new platform connectors without core changes, external secrets management, and zero-downtime key rotation.
**FRs covered:** FR-DI-05, FR-PI-06, FR-PI-07

**Prerequisites (from Epic 10.5, 10.7, 10.8, and 10.96):** Epic 10.5 stories 10-5-4 through 10-5-8, Epic 10.7, Epic 10.8, and Epic 10.96 must be complete before feature stories begin. Epic 10.96 is a hard sequencing gate — live engine must be aligned before extensibility work begins.
**Note:** Epic 10.9 (backtesting calibration) has no architectural dependency on Epic 11. Current sequencing (10.9 → 11) is a focus preference, not a hard gate.
**Tech debt to address in Epic 11 pre-epic:** ConfigModule extraction (Medium — DashboardModule 13 providers, ExecutionModule 15 providers), ConfigAccessor inconsistency (Low — 7+ services still using configService.get()).

## Epic 10.8: God Object Decomposition & Structural Refactoring

Decompose all identified God Objects into focused, single-responsibility services. Every refactored source file should be under ~600 lines. Zero functional changes — pure internal refactoring with 100% test pass rate maintained throughout.

**Hard Constraint:** Zero functional changes. Every story must pass the existing test suite with no behavioral modifications.

**Prerequisite:** Reviewer context template (reusable template with changes summary, codebase conventions snippet, out-of-scope declaration) must be prepared and applied to all 10.8 story files in Lad MCP `context` parameter. Goal: improve 19% actionable review rate from Epic 10.7.

### Story 10-8-0: God Object Decomposition Design Spike (P0 — GATE)

As the architect,
I want a single design document with method-to-service allocation tables for all 6 God Objects,
So that all code stories (10-8-1 through 10-8-6) have an unambiguous decomposition plan reviewed and accepted before implementation begins.

**Acceptance Criteria:**

**Given** the 6 identified God Objects (RiskManagerService ~1,651 lines, ExitMonitorService ~1,547 lines, ExecutionService ~1,430 lines, DashboardService ~1,205 lines, TelegramMessageFormatter ~789 lines, TelegramAlertService ~734 lines)
**When** the design spike is complete
**Then** a single document exists with:
- Method-to-service allocation table for each God Object (which methods move where)
- Test file mapping plan (which spec files split and where tests migrate)
- Constructor dependency splits (which deps go to which new service)
- Cross-service touchpoint analysis (`closePosition()`, `releasePartialCapital()`, PnL accumulation path through chunking loop)
- ConfigAccessor circular DI resolution paths
**And** the document is reviewed and accepted by Arbi
**And** no code story (10-8-1 through 10-8-6) starts until the design spike is accepted

**Owner:** Winston (Architect)

**Rationale:** Agreement #27 upgraded — design sketch as a story with verifiable artifact, not a soft pre-step. Failed as honor-system pre-step across two consecutive retros (10.5, 10.7).

### Story 10-8-1: RiskManagerService Decomposition (P0)

As a developer,
I want `RiskManagerService` (1,651 lines, 34 methods, 6 responsibilities) decomposed into 4 focused services,
So that each service has a single responsibility and is consumable by an AI agent in one context read.

**Acceptance Criteria:**

**Given** the existing `RiskManagerService` has 6 distinct responsibilities
**When** I extract `BudgetReservationService` (reserve/commit/release/adjust/clear), `TradingHaltService` (halt/resume lifecycle), and `RiskStateManager` (state init/persistence/recalculation)
**Then** `RiskManagerService` retains only validation, PnL, and config orchestration
**And** each new service file is under 500 lines
**And** `RiskManagerService` is under 600 lines
**And** all existing tests pass with zero behavioral changes
**And** `risk-manager.service.spec.ts` (2,747 lines) is decomposed into co-located files (<800 lines each)
**And** no module dependency rule violations are introduced
**And** all consumers inject the most specific service they need

### Story 10-8-2: ExitMonitorService Decomposition (P0)

As a developer,
I want `ExitMonitorService` (~1,547 lines, 10 methods, 9 constructor deps, 23 config properties) decomposed into 3 focused services,
So that exit execution, data source management, and evaluation logic are independently testable.

**Acceptance Criteria:**

**Given** the existing `ExitMonitorService` mixes evaluation, execution, and data source concerns
**When** I extract `ExitExecutionService` (executeExit, handlePartialExit) and `ExitDataSourceService` (classifyDataSource, combineDataSources, getClosePrice, getAvailableExitDepth)
**Then** `ExitMonitorService` retains only the evaluation loop and config management
**And** each new service file is under 500 lines
**And** `ExitMonitorService` is under 600 lines
**And** config properties are distributed to the service that uses them
**And** all existing tests pass with zero behavioral changes

### Story 10-8-3: ExecutionService Decomposition (P1)

As a developer,
I want `ExecutionService` (~1,430 lines, 7 methods, ~200 lines/method) decomposed into 3 focused services,
So that sequencing strategy, depth analysis, and core execution are independently maintainable.

**Acceptance Criteria:**

**Given** the existing `ExecutionService` bundles sequencing, depth analysis, and execution orchestration
**When** I extract `LegSequencingService` (determineSequencing, resolveConnectors, classifyDataSource) and `DepthAnalysisService` (getAvailableDepth + depth helpers)
**Then** `ExecutionService` retains only core `execute`, `handleSingleLeg`, and `reloadConfig`
**And** each new service file is under 500 lines
**And** `ExecutionService` is under 600 lines
**And** `execute()` method is under 200 lines (extract orchestration helpers if needed)
**And** `execution.service.spec.ts` (3,714 lines) is decomposed into co-located files (<800 lines each)
**And** all existing tests pass with zero behavioral changes

### Story 10-8-4: DashboardService Decomposition (P1)

As a developer,
I want `DashboardService` (1,205 lines, 20 methods, 14 deps) decomposed into 4 focused services,
So that the "gateway God object" pattern is eliminated and each dashboard concern is independently maintainable.

**Acceptance Criteria:**

**Given** the existing `DashboardService` aggregates overview, positions, capital, PnL, alerts, audit, shadow, and bankroll concerns
**When** I extract `DashboardOverviewService` (overview + health), `DashboardCapitalService` (capital + PnL + bankroll), and `DashboardAuditService` (alerts + audit parsing)
**Then** `DashboardService` retains only position queries (delegating to `enrichmentService`)
**And** each new service file is under 400 lines
**And** `DashboardController` injects specific services (not a single God service)
**And** `dashboard.service.spec.ts` (1,444 lines) is decomposed into co-located files
**And** all existing tests pass with zero behavioral changes

### Story 10-8-5: TelegramMessageFormatter Domain Split (P2)

As a developer,
I want the `TelegramMessageFormatter` God File (789 lines, 31 functions) split into domain-specific formatter files,
So that each formatter file is focused and under 200 lines.

**Acceptance Criteria:**

**Given** the existing file has 31 standalone formatter functions in one file
**When** I split into 7 domain files (execution, risk, platform, system, exit, detection, matching formatters) plus `formatter-utils.ts`
**Then** each formatter file is under 200 lines
**And** a barrel `index.ts` in `formatters/` re-exports all functions for backward compatibility
**And** `telegram-message.formatter.ts` is deleted (replaced by domain files)
**And** all existing tests pass with zero behavioral changes

### Story 10-8-6: TelegramAlertService Circuit Breaker Extraction (P2)

As a developer,
I want the circuit breaker logic extracted from `TelegramAlertService` (734 lines) into a dedicated `TelegramCircuitBreaker` service,
So that message delivery and failure resilience are independently testable.

**Acceptance Criteria:**

**Given** the existing `TelegramAlertService` mixes message delivery with circuit breaking state machine
**When** I extract `TelegramCircuitBreaker` (circuit state tracking, consecutive failure counting, recovery logic)
**Then** `TelegramCircuitBreaker` is under 200 lines
**And** `TelegramAlertService` is under 550 lines
**And** the circuit breaker is independently testable
**And** all existing tests pass with zero behavioral changes

## Epic 10.9: Backtesting & System Calibration (Phase 1)

Ingest historical prediction market data from multiple sources (platform APIs, PMXT Archive, OddsPipe, Predexon), replay detection and cost models against historical price/depth data, and produce parameter calibration reports with recommended values, confidence intervals, and sensitivity analysis. Dashboard page for running backtests and reviewing results.

**Prerequisite:** Epic 10.8 (God Object Decomposition) complete — clean module boundaries required for backtesting to consume detection/cost calculation logic without pulling in God Objects.

**Data Source Strategy:**
- **Cross-platform matched pairs:** OddsPipe (primary, free tier) + Predexon (active cross-reference, $49/mo)
- **Historical prices:** Kalshi `/candlesticks` (OHLCV, 1-min) + Polymarket `/prices-history` (1-min)
- **Historical orderbook depth:** PMXT Archive (hourly Polymarket L2 snapshots, Parquet) + own OrderBookSnapshot collection (30s, going forward)
- **Historical trades:** Polymarket Goldsky subgraph + Kalshi `/historical/trades`
- **Bootstrap dataset:** poly_data pre-built snapshot for Polymarket trade data

**Data Quality Risks (must be addressed in stories):**
- Survivorship bias in historical data (delisted/resolved contracts)
- Timezone misalignment between platforms
- Gaps in PMXT Archive coverage
- OddsPipe/Predexon matching errors polluting cross-platform pair data
- Kalshi live/historical API partition (cutoff ~3 months rolling)

**Scope boundary:** Calibration-focused analysis module. NOT a full replay engine through the live pipeline (ReplayConnector — deferred to Phase 2).

**Capacity Budget (Agreement #22):** 7 base stories, expect 9-10 total with 30-40% correction buffer.

### Story 10-9-0: Backtesting & Calibration Design Spike (P0 — GATE)

As the architect,
I want a design document covering data source integration, persistence strategy, and backtest engine architecture,
So that all code stories (10-9-1a through 10-9-6) have validated assumptions and no open architectural questions.

**Context:** Epic 10.8 retro defined this story as critical path. Follows the investigation-first pattern validated across three epics (10-0-3, 10-8-0). New external dependencies (OddsPipe, Predexon, PMXT Archive, Goldsky subgraph) each carry API integration risk.

**Acceptance Criteria:**

**Given** the data source strategy in the epic description
**When** the design spike is complete
**Then** a design document exists covering:
1. Data source API verification (actual endpoint testing: Kalshi `/candlesticks`, `/historical/trades`, `/historical/cutoff`; Polymarket `/prices-history`; Goldsky subgraph schema; PMXT Archive Parquet format; OddsPipe API; Predexon API)
2. Data persistence strategy (Postgres vs. flat files vs. hybrid; Prisma model fit for time-series data)
3. Common schema design for normalized historical data (prices, trades, depth snapshots)
4. Backtest engine state machine architecture
5. Test fixture strategy with deterministic datasets and known expected outcomes
6. Story sizing review with explicit split assessment on 10-9-3 (Backtest Simulation Engine)
7. Minimum viable calibration section — the cut line if scope pressure hits
8. Spec file naming map for all new modules
9. Reviewer context template for 10.9 stories

**Given** CLAUDE.md convention updates pending from Epic 10.8 retro
**When** the design spike document is finalized
**Then** CLAUDE.md is updated with:
- Constructor dependency dual threshold: leaf services ≤5, facades ≤8 (with mandatory rationale comment for exceptions)
- Line count dual metric: 600 formatted = review trigger, 400 logical = hard gate (documented exceptions require Prettier rationale AND logical count under 400)

**Given** this is a gate story
**When** the document is complete
**Then** it is reviewed and accepted by Arbi before any code story (10-9-1a through 10-9-6) starts

**Owner:** Winston (Architect)
**Dependencies:** None
**Blocks:** All 10.9 code stories (10-9-1a through 10-9-6)

### Story 10-9-1a: Platform API Price & Trade Ingestion (P0)

As an operator,
I want the system to ingest historical price and trade data from Polymarket and Kalshi,
So that backtesting has a local dataset of cross-platform pricing to analyze.

**Acceptance Criteria:**

**Given** the system has API access to Polymarket and Kalshi
**When** a data ingestion job is triggered (CLI command or dashboard action)
**Then** historical price data is fetched from Kalshi `/candlesticks` (1-min OHLCV) and Polymarket `/prices-history` (1-min)
**And** historical trades are fetched from Kalshi `/historical/trades` (cursor-paginated) and Polymarket Goldsky subgraph (GraphQL)
**And** poly_data pre-built snapshot is supported as a bootstrap import for Polymarket trade data (saves days of initial subgraph collection)
**And** all data is normalized to a common schema and persisted in PostgreSQL
**And** ingestion handles Kalshi's live/historical API partition (cutoff detection via `GET /historical/cutoff`)
**And** ingestion is idempotent (re-running does not create duplicates)
**And** data quality checks flag: timezone misalignment, coverage gaps, suspicious price jumps, survivorship bias indicators (resolved/delisted contracts)
**And** progress is observable via structured logs and dashboard status indicator
**And** rate limits are respected (Polymarket 1,000 req/10s for price history, Kalshi 20 req/s basic tier)

### Story 10-9-1b: Depth Data & Third-Party Ingestion (P0)

As an operator,
I want the system to ingest historical orderbook depth from PMXT Archive and supplementary OHLCV from OddsPipe,
So that backtesting can model VWAP-based fill pricing and slippage.

**Acceptance Criteria:**

**Given** PMXT Archive provides hourly Polymarket L2 orderbook snapshots in Parquet format
**And** OddsPipe provides OHLCV candlesticks at 1m/5m/1h/1d intervals
**When** a depth data ingestion job is triggered
**Then** PMXT Archive Parquet files are downloaded and parsed into the common schema (bids/asks arrays matching `OrderBookSnapshot` format)
**And** OddsPipe OHLCV data is fetched for matched pairs as supplementary price data
**And** coverage gap detection identifies time ranges with missing depth data (gaps between hourly PMXT snapshots)
**And** freshness tracking records last available snapshot timestamp per contract per source
**And** ingestion is idempotent
**And** data quality checks flag: PMXT coverage gaps >2 hours, OddsPipe matching discrepancies vs our own matches
**And** progress is observable via structured logs and dashboard status indicator

### Story 10-9-2: Cross-Platform Pair Matching Validation (P0)

As an operator,
I want to cross-reference our contract matching against OddsPipe and Predexon matched pairs,
So that I can validate matching accuracy and identify pairs we may have missed.

**Acceptance Criteria:**

**Given** OddsPipe provides 2,500+ auto-matched Polymarket↔Kalshi pairs
**And** Predexon provides cross-platform matching with 99%+ claimed accuracy
**When** a matching validation job runs
**Then** our `ContractMatch` records are compared against OddsPipe matched pairs
**And** our `ContractMatch` records are compared against Predexon matched pairs
**And** a validation report shows: confirmed matches (all 3 agree), our-only matches (we matched, they didn't), external-only matches (they matched, we didn't), conflicts (disagreements between sources)
**And** external-only matches are flagged as candidates for our knowledge base
**And** conflicts are flagged with match details for operator review
**And** the report is persisted and viewable on the dashboard

### Story 10-9-3: Backtest Simulation Engine — Core (P0)

As an operator,
I want to run a backtest that replays historical data through parameterized detection and cost models,
So that I can evaluate whether a given parameter set would have been profitable.

**Acceptance Criteria:**

**Given** historical data has been ingested (Stories 10-9-1a, 10-9-1b)
**And** cross-platform pairs are identified (own matches + validated external matches)
**When** a backtest is configured with: date range, parameter set (minimum edge threshold, position sizing %, max concurrent pairs, trading window hours), and fee model
**Then** the engine iterates through historical data chronologically
**And** at each timestamp, the detection model identifies opportunities using the parameterized edge threshold
**And** position sizing is computed using VWAP from available depth data (PMXT Archive hourly L2 or interpolated)
**And** execution costs are modeled using historical fee schedules (Kalshi dynamic fees, Polymarket fixed fees + gas estimates)
**And** exit logic applies the parameterized exit criteria against subsequent price data
**And** the engine tracks simulated portfolio state: open positions, P&L per position, aggregate P&L, drawdown, capital utilization
**And** fill modeling uses conservative assumptions: taker fills at ask/bid (no queue position), partial fills proportional to available depth, no market impact modeling
**And** single-leg scenarios are not simulated (assume both legs fill — documented as known limitation in calibration report, Story 10-9-4)

**Scope Boundary — Data Loading:**
This story implements the simulation engine with direct data loading (single-query `loadPrices`/`loadPairs`). This is sufficient for development and small-to-medium test datasets (<10K price records). Production-scale data loading (200GB+) is handled by Story 10-9-3a (Backtest Pipeline Scalable Data Loading), which refactors the data retrieval layer while preserving all simulation logic from this story.

**Note:** Story 10-9-3a depends on this story being complete first. Do not attempt production-scale backtests until 10-9-3a and 10-9-3b are merged.

### Story 10-9-3a: Backtest Pipeline Scalable Data Loading (P0)

As an operator,
I want the backtest engine to process large historical datasets (200GB+) without memory exhaustion or excessive query load,
So that I can run calibration backtests over the full available date range (months to years of data) reliably.

**Problem Context:**
The current `executePipeline` method loads ALL prices and pairs for the selected date range in a single Prisma query, materializing everything in Node.js memory. This is unsustainable at production scale (~200GB of historical price/depth data). Additionally, depth lookups use an N+1 query pattern (~10K individual queries per simulation run).

**Acceptance Criteria:**

**Given** a backtest configuration with a date range spanning months or years of historical data
**When** the pipeline executes
**Then:**
1. `loadPrices()` is replaced with chunked loading — data processed in configurable time-windows (default: 1 day) using cursor-based Prisma pagination
2. `alignPrices()` operates per-chunk rather than on the full dataset — only the current chunk's time steps are held in memory at any time
3. Depth data for each chunk is pre-loaded in a single batched query before the simulation loop processes that chunk (eliminates N+1 pattern)
4. Walk-forward analysis shares pre-loaded chunk data with headless sub-simulations — no redundant re-loading
5. Chunk-level progress events emitted via EventEmitter2 (e.g., `backtest.pipeline.chunk.completed`) for dashboard progress tracking
6. Memory usage stays bounded — peak RSS does not exceed 512MB for a 90-day backtest with 500+ pairs at 5-minute resolution
7. All existing backtest simulation tests continue to pass without modification (simulation logic unchanged)
8. Pipeline timeout (`timeoutSeconds`) still enforced correctly across chunks
9. Dashboard displays chunk-level progress (e.g., "Processing day 15 of 90") via WebSocket gateway, with graceful fallback to state machine status for pre-deployment runs

**Technical Notes:**
- Follow patterns proven in data-ingestion module: 7-day chunked windows, p-limit concurrency, batch operations
- Chunk size should be configurable via `IBacktestConfig` (new field: `chunkWindowDays`, default 1)
- Pre-load depths: single `findMany` with `IN` clause on contract IDs + timestamp range per chunk, keyed into a `Map` for O(1) lookup during simulation
- Portfolio state (openPositions, closedPositions, equity curve) persists across chunks — only price data is discarded
- **Follow-up candidate:** Chunk-level resume on failure (persist last successful chunk index to `BacktestRun`, allow restart from checkpoint). Defer unless chunk failures observed during integration testing.
- **Known limitation:** Depth data density was underestimated at design time. Per-chunk depth loading for all 5,640 contract IDs produces ~573K records (~5.7 GB of `Decimal` objects), exceeding V8 heap limits. Fix: Story 10-9-3b (contract filtering, native numbers, bounded cache, re-enable timeouts).

**Dependencies:** Story 10-9-3 (simulation engine must exist first)
**Blocked by:** None beyond 10-9-3
**Blocks:** Production-scale calibration runs (10-9-4 at scale), dashboard progress indicator. **Note:** 10-9-3b required before production-scale runs are viable.

**Tasks:**
1. Add `chunkWindowDays` field to `IBacktestConfig` interface with default value
2. Implement `loadPricesChunked()` generator/iterator yielding day-sized price batches via cursor pagination
3. Implement `preloadDepthsForChunk()` — batch depth query for all active contract IDs within chunk timestamp range
4. Refactor `executePipeline()` to iterate over chunks: load → align → simulate → discard per window
5. Ensure portfolio state carries across chunk boundaries (open positions survive chunk transitions)
6. Add chunk progress event emission + dashboard WebSocket consumption + fallback for pre-deployment runs
7. Refactor walk-forward to split by chunks rather than re-loading entire dataset 3x
8. Add integration test: 90-day simulated backtest with chunked loading (mock Prisma, verify bounded memory)
9. Add unit test: chunk boundary — position opened in chunk N is correctly evaluated for exit in chunk N+1
10. Add unit test: depth pre-loading returns correct nearest depth within chunk window

### Story 10-9-3b: Backtest Depth Loading Memory Fix (P0 HOTFIX)

As an operator,
I want the backtest engine depth loading to operate within bounded memory,
So that production-scale backtests complete without V8 heap exhaustion.

**Problem Context:**
Story 10-9-3a introduced chunked pipeline loading but `preloadDepthsForChunk` still loads ALL depth snapshots for ALL 5,640 contract IDs per 1-day chunk (~573K records → ~37.8M `Decimal` objects → ~5.7 GB). Additionally, timeout checks were commented out during development and never re-enabled, removing the circuit breaker for runaway memory consumption.

**Acceptance Criteria:**

**Given** a backtest configuration with a date range spanning days to months of historical data
**When** the pipeline executes
**Then:**
1. Depth data is loaded only for contracts that have aligned price data in the current chunk (not all approved pairs)
2. Depth cache memory is bounded — peak depth cache size does not exceed configurable limit (default: 100K records per chunk)
3. If a chunk's depth data exceeds the bound, depths are loaded lazily per-contract via LRU cache (bounded size, e.g., 500 entries) instead of eager full pre-load
4. Depth level parsing uses native `number` for price/size instead of `decimal.js` `Decimal` (depth levels are used for VWAP fill estimation, not financial settlement)
5. Timeout checks are re-enabled at chunk boundaries and within the simulation loop
6. `closedPositions` array is bounded — positions are flushed to a chunked buffer or aggregate metrics accumulated to prevent unbounded growth
7. `capitalSnapshots` are downsampled to fixed intervals (e.g., 1 per hour) rather than 1 per open/close event
8. All existing backtest simulation tests continue to pass
9. A 7-day backtest with 2,933 approved pairs at 1-day chunk size completes without OOM (peak RSS < 1 GB)

**Technical Notes:**
- **Contract filtering (AC#1):** After `loadAlignedPricesForChunk`, extract distinct `kalshiContractId` and `polymarketContractId` from `chunkTimeSteps`. Pass only those IDs to `preloadDepthsForChunk`. Expected reduction: 5,640 → <500 per chunk.
- **Bounded depth cache (AC#2-3):** Add `maxDepthRecordsPerChunk` constant. If query count exceeds threshold, fall back to lazy per-contract loading with LRU cache.
- **Native numbers for depth (AC#4):** Replace `Decimal` in `NormalizedHistoricalDepth.bids[].price`/`.size` and `.asks[].price`/`.size` with `number`. Update `parseJsonDepthLevels`, `adaptDepthToOrderBook`, `findNearestDepthFromCache`. Memory reduction: ~60% per depth record (~120 bytes/Decimal → 8 bytes/number).
- **Re-enable timeouts (AC#5):** Uncomment 3 timeout blocks in `backtest-engine.service.ts`. Use `timeoutSeconds` from config.
- **closedPositions bounding (AC#6):** Accumulate aggregate metrics in-memory. Write individual positions to DB in batches at chunk boundaries. `persistResults` reads from DB.
- **capitalSnapshots downsampling (AC#7):** Fixed-interval sample (1 per hour) instead of every open/close event.

**Dependencies:** Story 10-9-3a (already done)
**Blocked by:** None
**Blocks:** Production-scale calibration runs, Epic 10.9 closure

**Tasks:**
1. Filter `contractIds` in `executePipeline` to only contracts present in `chunkTimeSteps` after loading aligned prices
2. Add depth record count check and implement fallback lazy loading with LRU cache in `BacktestDataLoaderService`
3. Convert `NormalizedHistoricalDepth` bid/ask levels from `Decimal` to native `number`; update `parseJsonDepthLevels`, `adaptDepthToOrderBook`, `findNearestDepthFromCache`
4. Uncomment and verify all 3 timeout check blocks in `backtest-engine.service.ts`
5. Bound `closedPositions` — flush to DB at chunk boundaries or switch to streaming aggregate metrics
6. Downsample `capitalSnapshots` to fixed intervals
7. Unit test: contract filtering reduces depth loading to chunk-active contracts only
8. Unit test: depth cache fallback to lazy LRU when record count exceeds threshold
9. Integration test: 7-day backtest with full pair set completes within memory bounds (peak RSS < 1 GB)
10. Unit test: timeout correctly halts pipeline when exceeded

### Story 10-9-4: Calibration Report Generation with Sensitivity Analysis (P0)

As an operator,
I want backtest results presented as a calibration report with recommended parameter values, confidence intervals, sensitivity analysis, and out-of-sample validation,
So that I can make informed parameter decisions with clear risk boundaries and confidence against overfitting.

**Acceptance Criteria:**

**Given** a completed backtest run (Story 10-9-3)
**When** the calibration report is generated
**Then** the report includes:
- **Summary metrics:** Total trades, profit factor, net P&L, max drawdown, Sharpe ratio, win rate, average edge captured vs expected
- **Recommended parameter values:** The parameter set that maximizes profit factor (primary) or Sharpe (secondary)
- **Confidence intervals:** Bootstrap resampling (1000+ iterations) producing 95% CI for profit factor and Sharpe
- **Sensitivity analysis:** Parameter sweep across defined ranges with profit factor, max drawdown, and Sharpe ratio computed at each point:
  - Minimum edge threshold: sweep 0.5% to 5.0% in 0.1% steps
  - Position sizing: sweep 1% to 5% of bankroll in 0.5% steps
  - Max concurrent pairs: sweep 5 to 30 in steps of 5
  - Trading window: compare full-day vs top-performing UTC hour ranges
- **Degradation boundaries:** Identify parameter values where profit factor drops below 1.0 (breakeven) — "below 2.8% minimum edge, the system is unprofitable"
- **Out-of-sample validation:** Walk-forward analysis — train on the first N% of the date range, test on the remaining (100-N)%, with configurable split ratio (default 70/30). Report separates in-sample vs out-of-sample metrics. Parameters showing >30% degradation between in-sample and out-of-sample are flagged as potential overfits.
- **Known limitations:** Single-leg risk not modeled (both legs assumed to fill), market impact not modeled, queue position not modeled (taker-only fills), depth interpolation between hourly PMXT snapshots
- **Data quality summary:** Coverage gaps, excluded periods, pair count, total data points analyzed
**And** the report is persisted as a `BacktestRun` record (analogous to `CalibrationRun` / `StressTestRun`)
**And** sensitivity charts are renderable by the dashboard

### Story 10-9-5: Backtest Dashboard Page (P1)

As an operator,
I want a dashboard page to configure, trigger, and review backtests,
So that I can run calibration analysis without CLI access.

**Acceptance Criteria:**

**Given** the backtesting module is operational
**When** I navigate to the Backtest page
**Then** I can configure a backtest: select date range, adjust parameter values, choose fee model, select validation mode (full-range or walk-forward with configurable split)
**And** I can trigger a backtest run and see progress indication
**And** I can view completed backtest results with summary metrics
**And** sensitivity analysis is displayed as interactive charts (parameter on x-axis, metric on y-axis, with degradation boundary highlighted)
**And** out-of-sample vs in-sample metrics are visually distinguished (separate panels or overlaid with clear labeling)
**And** overfitting warnings are prominently displayed when >30% in-sample/out-of-sample degradation detected
**And** known limitations are visible in a collapsible section on every report view
**And** I can compare two backtest runs side-by-side (before/after parameter change)
**And** the page follows existing dashboard patterns (DataTable, URL state, sidebar navigation)
**And** backtest history is listed with status, date range, key metrics

### Story 10-9-6: Historical Data Freshness & Incremental Updates (P1)

As an operator,
I want the historical data to stay current with incremental updates,
So that backtests always reflect the latest available market data.

**Acceptance Criteria:**

**Given** an initial data ingestion has been completed
**When** a refresh job runs (configurable cron schedule, default daily)
**Then** only new data since last ingestion is fetched (incremental, not full re-download)
**And** PMXT Archive is checked for new hourly snapshots
**And** OddsPipe/Predexon are checked for new matched pairs
**And** Kalshi historical cutoff advancement is handled (data migrating from live to historical tier)
**And** data quality checks re-run on new data
**And** stale data warnings are emitted if any source hasn't updated within expected window
**And** dashboard shows data freshness indicators (last update timestamp per source)

## Epic 11: Platform Extensibility & Security Hardening (Phase 1)

System supports new platform connectors without core changes, external secrets management, and zero-downtime key rotation.

### Story 11.1: Platform Connector Plugin Architecture

As an operator,
I want to add new trading platforms by implementing a connector without touching core modules,
So that expanding to a third venue is a contained implementation effort.

**Acceptance Criteria:**

**Given** the `IPlatformConnector` interface and two connectors already exist from Epics 1-2
**When** this story is implemented
**Then** the connector module uses dynamic discovery (scanning for `IPlatformConnector` implementations) rather than hardcoded imports (FR-DI-05)
**And** a new connector can be registered by implementing the interface and adding it to the connectors directory — no changes to detection, execution, risk, or monitoring modules required
**And** documentation exists for the connector implementation contract: required methods, error handling patterns, event emission, rate limit integration, health reporting

**Given** this is primarily a refactoring and verification story (not build-from-scratch)
**When** I inspect the scope
**Then** the work focuses on: ensuring dynamic connector registration, verifying no core module has hardcoded Kalshi/Polymarket references outside of `connectors/`, and documenting the extension pattern

**Tech Debt Note (from Story 6.5.0 code review, Finding #11):** `polymarket.connector.ts` `postOrder` response uses blind `as Record<string, unknown>` casting without runtime validation. When implementing Story 11.1's connector plugin architecture, add runtime validation (e.g., Zod schemas) for all external API response types to prevent undefined order IDs and orphaned orders.

**Interface Note (from Epic 10):** By the time this story is implemented, `IPlatformConnector` will include `subscribeToContracts()` and `unsubscribeFromContracts()` (added in Story 10-0-1). The connector plugin documentation must cover WebSocket subscription implementation requirements in addition to the original REST/polling methods.

### Story 11.2: External Secrets Management Integration

As an operator,
I want credentials retrieved from an external secrets manager at startup,
So that sensitive keys are never stored on disk unencrypted or in process memory long-term.

**Acceptance Criteria:**

**Given** a secrets manager is configured (AWS Secrets Manager, HashiCorp Vault, or similar)
**When** the engine starts
**Then** all platform credentials (Kalshi API key/secret, Polymarket keystore password, dashboard Bearer token, PostgreSQL password) are fetched from the secrets manager (FR-PI-06)
**And** credentials are held in memory only during active use
**And** all secrets access is logged to audit trail

**Given** the secrets manager is unavailable at startup
**When** credential fetch fails
**Then** the engine falls back to environment variables with a warning alert
**And** the fallback is logged as a security concern

### Story 11.3: Zero-Downtime API Key Rotation

As an operator,
I want to rotate platform API keys without stopping the trading engine,
So that security incidents or routine rotation don't cause trading downtime.

**Acceptance Criteria:**

**Given** a new API key is available in the secrets manager
**When** the operator triggers rotation via `POST /api/admin/rotate-credentials/:platform`
**Then** the new key is fetched and validated (test API call)
**And** the connector switches to the new key with <5 seconds of degraded operation (FR-PI-07)
**And** the old key is invalidated after successful switchover
**And** the rotation event is logged to audit trail

### Epic 12: Advanced Compliance & Reporting (Phase 1)
System generates automated quarterly compliance reports, on-demand audit trail exports, and comprehensive regulatory monitoring.
**FRs covered:** FR-MA-07, FR-MA-08, FR-DE-03, FR-DE-04

## Epic 12: Advanced Compliance & Reporting (Phase 1)

System generates automated quarterly compliance reports, on-demand audit trail exports, and comprehensive regulatory monitoring.

### Story 12.1: Quarterly Compliance Report Generation

As an operator,
I want automated quarterly compliance reports covering all regulatory requirements,
So that my legal counsel can complete a 22-minute review instead of manual investigation.

**Acceptance Criteria:**

**Given** a quarter has ended (or operator triggers manually via `POST /api/reports/compliance?quarter=Q1&year=2026`)
**When** the compliance report generates
**Then** it produces a PDF with standardized sections: trading activity summary (volume, platforms, categories), wash trading analysis with cross-platform rationale, anti-spoofing compliance (order cancellation patterns), platform relationship health (API usage, terms compliance), and regulatory horizon scan (FR-MA-07, FR-DE-03)

**Given** the report is generated
**When** the operator downloads it
**Then** it is accessible via `GET /api/reports/compliance/:id/download`
**And** the report generation event is logged to audit trail

### Story 12.2: On-Demand Audit Trail Export

As an operator,
I want to export audit trails for any time period within the 7-year retention window,
So that legal counsel can review specific periods on demand.

**Acceptance Criteria:**

**Given** the operator requests an audit trail export
**When** they call `GET /api/exports/audit-trail?startDate=X&endDate=Y&format=csv`
**Then** the system exports all audit log entries for the period with: timestamp, event_type, module, correlation_id, details, hash chain verification status (FR-MA-08, FR-DE-04)
**And** exports include timestamp correlation between opposite legs for arbitrage pair verification
**And** cancellation rationale is included for all non-filled orders

**Given** the export covers a large time range
**When** the result would exceed 100MB
**Then** the export is generated asynchronously and the operator is notified when ready via Telegram

### Story 12.3: Regulatory Keyword Monitoring Service

As an operator,
I want automated monitoring of regulatory feeds for prediction market keywords,
So that I'm notified of regulatory developments before they impact my trading.

**Acceptance Criteria:**

**Given** the regulatory monitoring service is configured with RSS feed URLs and keyword lists
**When** CFTC RSS feeds are polled (hourly)
**Then** filings containing configured keywords ("prediction market", "event contract", "Kalshi", "Polymarket") trigger immediate alerts to operator with filing link and matched keywords

**Given** platform status page URLs are configured
**When** they are polled hourly
**Then** platform disruptions exceeding 2 hours trigger a high-priority alert (potential regulatory action indicator)

**Given** the operator has set up external news monitoring (e.g., Google Alerts forwarding to an RSS feed or email-to-RSS bridge)
**When** those feeds are added to the service's configurable feed list
**Then** matches are included in the daily regulatory digest sent to operator

**Given** the monitoring implementation
**When** I inspect the code
**Then** it uses standard RSS parsing, HTTP polling, and string matching only — no AI/NLP, no Google Alerts API (which doesn't exist)
**And** the service accepts any number of configurable RSS/Atom feed URLs, making it feed-source-agnostic
