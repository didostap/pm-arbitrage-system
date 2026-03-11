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

### Story 10.1: Continuous Edge Recalculation

As an operator,
I want open positions' expected edge continuously recalculated using live market data,
So that exit decisions are based on current reality, not stale entry-time assumptions.

**Acceptance Criteria:**

**Given** a position is open
**When** the exit monitor evaluates it each cycle
**Then** expected edge is recalculated based on: current fee schedules, live liquidity depth at exit prices, updated gas estimates, and time to resolution (FR-EM-02)
**And** recalculated edge is persisted and available to the dashboard

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
3. **Time decay:** Expected value diminishes as resolution approaches (configurable decay curve)
4. **Risk budget breach:** Portfolio-level risk limit is approached and this position has lowest remaining edge
5. **Liquidity deterioration:** Order book depth at exit prices drops below minimum executable threshold

**Given** model-driven exits are active
**When** the system is configured
**Then** the operator can toggle between fixed thresholds (MVP) and model-driven exits via config
**And** both modes can run in shadow mode (model-driven calculates but fixed thresholds execute) for validation

**Given** shadow mode is active
**When** an exit occurs (by either mode)
**Then** a daily comparison summary is logged showing: "fixed would have exited at X with P&L Y, model would have exited at Z with P&L W, actual edge captured"
**And** this comparison data is available in the dashboard performance view for building confidence in the switch

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

**Tech Debt Note (from Story 6.5.0 code review, Finding #7):** `polymarket.connector.ts` has hardcoded `ORDER_POLL_TIMEOUT_MS` and `ORDER_POLL_INTERVAL_MS` with no exponential backoff or jitter. When implementing Story 10.4, make these timeouts configurable via `@nestjs/config` and add jitter to the polling loop.

**Tech Debt Note (from Story 6.5.5b):** The MVP depth-aware sizing model computes primary and secondary ideal sizes independently (`reservedCapitalUsd / legPrice`), producing different contract counts. With asymmetric depth capping this divergence can widen, creating directional exposure rather than hedged arbitrage. This story's matched-count execution eliminates that limitation.

### Epic 11: Platform Extensibility & Security Hardening (Phase 1)
System supports new platform connectors without core changes, external secrets management, and zero-downtime key rotation.
**FRs covered:** FR-DI-05, FR-PI-06, FR-PI-07

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
