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

### Epic 6: Monitoring, Alerting & Compliance Logging
Operator receives real-time Telegram alerts, has CSV trade logs for daily review, compliance validation before execution, and complete audit trail. MVP feature set complete.
**FRs covered:** FR-MA-01, FR-MA-02, FR-MA-03, FR-DE-01, FR-DE-02, FR-PI-05
**Additional:** Alerting health monitoring (daily test alerts), error code catalog implementation

## Epic 6: Monitoring, Alerting & Compliance Logging

Operator receives real-time Telegram alerts, has CSV trade logs for daily review, compliance validation before execution, and complete audit trail. MVP feature set complete.

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

### Epic 8: Intelligent Contract Matching & Knowledge Base (Phase 1)
System automatically identifies potential contract matches via semantic analysis, scores confidence, auto-approves high-confidence matches, and learns from resolution outcomes.
**FRs covered:** FR-AD-05, FR-AD-06, FR-AD-07, FR-CM-02, FR-CM-03, FR-CM-04

## Epic 8: Intelligent Contract Matching & Knowledge Base (Phase 1)

System automatically identifies potential contract matches via semantic analysis, scores confidence, auto-approves high-confidence matches, and learns from resolution outcomes.

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
**And** the initial implementation uses deterministic string-based analysis (no LLM dependency) — settlement dates, normalized description similarity, and keyword overlap
**And** the door is open for an LLM-based strategy implementation later via the same interface

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

### Epic 9: Advanced Risk & Portfolio Management (Phase 1)
System provides correlation-aware position sizing, dynamic cluster limits, confidence-adjusted sizing, and Monte Carlo stress testing.
**FRs covered:** FR-RM-05, FR-RM-06, FR-RM-07, FR-RM-08, FR-RM-09

## Epic 9: Advanced Risk & Portfolio Management (Phase 1)

System provides correlation-aware position sizing, dynamic cluster limits, confidence-adjusted sizing, and Monte Carlo stress testing.

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

### Story 10.4: Adaptive Leg Sequencing

As an operator,
I want the system to dynamically choose which platform's leg to execute first based on real-time latency,
So that leg risk is minimized by executing the faster platform first.

**Acceptance Criteria:**

**Given** both platform connectors track execution latency
**When** the latency difference exceeds 200ms
**Then** the faster platform's leg is executed first, overriding the static `primaryLeg` config (FR-EX-08)
**And** the sequencing decision is logged with latency measurements

**Given** latency profiles are stable (difference <200ms)
**When** sequencing is determined
**Then** the static `primaryLeg` config is used (preserving MVP behavior)

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
