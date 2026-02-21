# Sprint Change Proposal: Paper Trading Infrastructure

**Date:** 2026-02-19
**Trigger:** Polymarket testnet unavailable; paper trading needed as permanent, platform-agnostic capability
**Scope Classification:** Moderate
**Status:** Approved

---

## Section 1: Issue Summary

Polymarket does not offer a testnet environment, making live-environment testing the only option for validating execution logic. This creates unacceptable risk for real-capital operations during development and ongoing validation.

Paper trading must be implemented as a **permanent, platform-agnostic capability** — not a transient development phase. It serves three ongoing purposes:

1. **Pre-deployment validation** — verify execution logic against live order books without capital risk
2. **New platform onboarding** — safely test any future platform connector before committing capital
3. **Strategy experimentation** — test parameter changes (thresholds, sizing) in parallel with live trading

The system must support **mixed mode operation** where each platform is independently configurable as live or paper (e.g., Kalshi live + Polymarket paper).

## Section 2: Impact Analysis

**Epic Impact:**
- **Epic 5 (in-progress):** No changes. Stories 5.3–5.5 remain as-is. Epic 5.5 is sequenced after Epic 5 completion.
- **New Epic 5.5:** Paper Trading Infrastructure — 3 stories added (5.5.1, 5.5.2, 5.5.3).
- **Epic 6 (backlog):** Benefits from paper trading events (monitoring can subscribe to paper execution events). No story changes.
- **Epic 7 (backlog):** Benefits from UX spec additions (mode indicator, paper position badge). No story changes.
- No other epics affected.

**Artifact Conflicts:** None.
- **PRD:** Section rewrite ("Pre-MVP: Backtesting & Paper Trading Scope") — elevates paper trading from transient phase to permanent capability.
- **Architecture:** New `connectors/paper/` directory + per-platform environment config. Follows existing `IPlatformConnector` pattern (FR-DI-05).
- **UX Design Specification:** Mode indicator badges + paper position distinction. Minimal, additive changes.
- **Prisma Schema:** `is_paper` flag on `open_positions` and `orders` tables. Migration within Story 5.5.2.

**Technical Impact:**
- Decorator pattern wrapping existing `IPlatformConnector` implementations
- 3 new files in `connectors/paper/` directory
- 2 table migrations (add `is_paper` column + composite index)
- Per-platform environment variables for mode and fill simulation
- Repository-level filtering for risk budget isolation (no RiskManagerService changes)
- All existing tests must continue to pass

## Section 3: Recommended Approach

**Selected:** Direct Adjustment — add Epic 5.5 after Epic 5.

**Rationale:**
- Paper trading is a permanent infrastructure capability, not a pre-execution hygiene task (rules out Epic 4.75)
- Sequencing after Epic 5 ensures execution primitives (order submission, position tracking, single-leg handling) exist before paper trading wraps them
- Decorator pattern means zero changes to existing connector implementations
- Mode is immutable at runtime (config-only, requires restart) — eliminates state machine complexity

**Alternatives considered:**
- **Epic 4.75 (pre-execution sprint):** Rejected — paper trading is permanent capability, not a gate. Epic 4.5-style sprints are for hygiene/debt.
- **Fold into Epic 5 stories:** Rejected — Epic 5 stories (5.3–5.5) are already scoped for live execution concerns. Adding paper trading increases scope and conflates concerns.
- **Defer to post-Epic 6:** Rejected — delays safe testing capability, increases risk of live-capital errors during Epic 5 validation.

## Section 4: Detailed Change Proposals

### 4a. Add Epic 5.5 to `epics.md`

Insert after Epic 5, before Epic 6:

---

**Epic 5.5: Paper Trading Infrastructure**

Paper trading as a permanent, platform-agnostic system capability. Each platform independently configurable as live or paper. Decorator pattern wraps existing IPlatformConnector implementations — zero changes to live connector code.

**Story 5.5.1: Paper Trading Connector & Mode Configuration**

As an operator,
I want to configure any platform connector in paper mode via environment variables,
So that I can run execution logic against live order books without submitting real orders.

Acceptance Criteria:

- **Given** `PLATFORM_MODE_KALSHI=paper` is set in environment
  **When** the engine starts
  **Then** the Kalshi connector is wrapped in a PaperTradingConnector decorator

- **Given** PaperTradingConnector wraps a live connector
  **When** `getOrderBook()`, `getHealth()`, `onOrderBookUpdate()` are called
  **Then** they proxy transparently to the underlying live connector

- **Given** PaperTradingConnector wraps a live connector
  **When** `submitOrder()` is called
  **Then** the order is intercepted locally (never reaches the platform API)
  **And** a simulated fill is generated using configurable parameters

- **Given** per-platform fill simulation config exists
  **When** a paper order is submitted for Kalshi
  **Then** fill latency uses `PAPER_FILL_LATENCY_MS_KALSHI` (default: 150ms)
  **And** slippage uses `PAPER_SLIPPAGE_BPS_KALSHI` (default: 5 bps)

- **Given** per-platform fill simulation config exists
  **When** a paper order is submitted for Polymarket
  **Then** fill latency uses `PAPER_FILL_LATENCY_MS_POLYMARKET` (default: 800ms)
  **And** slippage uses `PAPER_SLIPPAGE_BPS_POLYMARKET` (default: 15 bps)

- **Given** platform mode is set at startup
  **When** the engine is running
  **Then** the mode cannot be changed without a restart (immutable at runtime)

- **Given** PaperTradingConnector is active
  **When** any execution event is emitted
  **Then** the event payload includes `isPaper: true` metadata

- `connectors/paper/paper-trading.connector.ts` implements IPlatformConnector via decorator pattern
- `connectors/paper/fill-simulator.service.ts` handles simulated fill generation
- `connectors/paper/paper-trading.types.ts` defines PaperTradingConfig, SimulatedFill types
- All existing tests pass, `pnpm lint` reports zero errors
- New unit tests cover: decorator proxying, fill simulation, config validation, event metadata

**Story 5.5.2: Paper Position State Isolation & Tracking**

As an operator,
I want paper trading positions tracked separately from live positions,
So that paper results never contaminate live P&L or risk calculations.

Acceptance Criteria:

- **Given** the Prisma schema
  **When** migration runs
  **Then** `open_positions` and `orders` tables have an `is_paper` Boolean column (default: false)
  **And** a composite index exists on `(is_paper, status)` for both tables

- **Given** paper mode is active for a platform
  **When** a paper order fills
  **Then** the resulting position is persisted with `is_paper = true`

- **Given** risk budget queries (position limits, exposure calculations)
  **When** querying positions
  **Then** repository methods filter by `is_paper = false` by default (live-only)
  **And** paper positions have an isolated risk budget that does not affect live limits

- **Given** paper positions exist
  **When** the operator views the dashboard
  **Then** paper positions are visually distinct (amber border, `[PAPER]` tag)
  **And** paper P&L is excluded from live summary totals by default (toggle to include)

- All existing tests pass, `pnpm lint` reports zero errors
- New unit tests cover: repository filtering, isolation verification, migration rollback

**Story 5.5.3: Mixed Mode Validation & Operational Safety**

As an operator,
I want the system to validate mixed mode configurations at startup,
So that I am protected from invalid or dangerous platform mode combinations.

Acceptance Criteria:

- **Given** platform mode configuration
  **When** the engine starts
  **Then** startup logs clearly display each platform's mode (`[Kalshi: LIVE] [Polymarket: PAPER]`)

- **Given** an invalid mode value (not `live` or `paper`)
  **When** the engine starts
  **Then** startup fails with a clear error message

- **Given** mixed mode is active (some platforms live, some paper)
  **When** an arbitrage opportunity spans a live and paper platform
  **Then** the execution proceeds (paper side simulated, live side real)
  **And** the opportunity and resulting positions are tagged with `mixedMode: true`

- **Given** all platforms are in paper mode
  **When** the engine starts
  **Then** a startup warning is logged: "All platforms in PAPER mode — no live trading active"

- **Given** the engine is running in any mode
  **When** the operator queries system status
  **Then** the API response includes the mode for each platform

- All existing tests pass, `pnpm lint` reports zero errors
- New unit tests cover: startup validation, mixed mode tagging, mode display in status API
- E2E test: full cycle with one platform live + one paper, verifying isolation

---

### 4b. Update PRD — "Pre-MVP: Backtesting & Paper Trading Scope"

Replace the existing "Pre-MVP: Backtesting & Paper Trading Scope" section with:

> **Paper Trading — Permanent System Capability**
>
> Paper trading is a permanent, platform-agnostic capability — not a transient development phase. It enables safe validation of execution logic against live market data without capital risk.
>
> **Core design:**
> - Decorator pattern wrapping `IPlatformConnector` — any platform can run in paper mode without connector code changes
> - Per-platform configuration via environment variables (mode, fill latency, slippage)
> - Mixed mode operation: each platform independently set to `live` or `paper`
> - Mode is immutable at runtime (requires restart to change)
>
> **State isolation:**
> - `is_paper` flag on positions and orders — repository-level filtering
> - Paper positions have isolated risk budgets (do not consume live limits)
> - Paper P&L excluded from live summaries by default
>
> **Ongoing use cases:**
> 1. Pre-deployment validation of execution logic changes
> 2. New platform connector onboarding (safe testing before capital commitment)
> 3. Strategy parameter experimentation in parallel with live trading
>
> **Out of scope (future consideration):**
> - Historical replay / backtesting engine (replay recorded order books through paper trading)
> - Paper trading analytics dashboard (dedicated views beyond position tagging)

### 4c. Update Architecture — Connector Directory & Environment Config

**Add to connector directory structure:**

```
connectors/
├── kalshi/
├── polymarket/
└── paper/
    ├── paper-trading.connector.ts    # IPlatformConnector decorator
    ├── fill-simulator.service.ts     # Simulated fill generation
    └── paper-trading.types.ts        # PaperTradingConfig, SimulatedFill
```

**Add to environment configuration section:**

```
# Platform Mode (per-platform, values: live | paper)
PLATFORM_MODE_KALSHI=live
PLATFORM_MODE_POLYMARKET=paper

# Paper Trading Fill Simulation (per-platform)
PAPER_FILL_LATENCY_MS_KALSHI=150
PAPER_SLIPPAGE_BPS_KALSHI=5
PAPER_FILL_LATENCY_MS_POLYMARKET=800
PAPER_SLIPPAGE_BPS_POLYMARKET=15
```

**Architecture note:** PaperTradingConnector implements `IPlatformConnector` using the decorator pattern. It receives a real connector instance at construction, proxies all data-read methods (`getOrderBook`, `getHealth`, `onOrderBookUpdate`, `getFeeSchedule`, `getPlatformId`) to the underlying connector, and intercepts all execution methods (`submitOrder`, `cancelOrder`) with local simulation. This satisfies FR-DI-05 ("Support adding new platform connectors without modifying core modules").

**Canonical fill simulation defaults (reconciliation note):** Earlier incremental proposals used preliminary values (Kalshi: 50ms/10bps, Polymarket: 200ms/15bps). The values in this document are canonical: Kalshi 150ms/5bps, Polymarket 800ms/15bps. The 800ms Polymarket latency better reflects on-chain confirmation times. SM must apply these canonical values when updating architecture.md. All values are operator-configurable via environment variables.

### 4d. Update UX Design Specification

**Dashboard header — Mode indicator:**
Each platform tile in the header health bar displays a mode badge:
- **LIVE** — green badge, normal operation
- **PAPER** — amber badge with dotted border, paper trading active

Badge placement: inline after platform name (e.g., `Kalshi [LIVE]` · `Polymarket [PAPER]`). Badges are static — reflect startup configuration.

**Open Positions view — Paper position distinction:**
- Amber left-border accent (vs. default neutral border for live positions)
- `[PAPER]` tag after the pair name
- Paper positions excluded from P&L summary totals by default (toggle to include)
- Filter toggle: All / Live Only / Paper Only

### 4e. Update Sprint Status (`sprint-status.yaml`)

Insert after `epic-5-retrospective: optional`:

```yaml
  # EPIC 5.5: Paper Trading Infrastructure
  epic-5-5: backlog
  5-5-1-paper-trading-connector-mode-configuration: backlog
  5-5-2-paper-position-state-isolation-tracking: backlog
  5-5-3-mixed-mode-validation-operational-safety: backlog
  epic-5-5-retrospective: optional
```

Update summary statistics:
- Total Epics: 13 → 14
- Total Stories: 52 → 55
- Total Items: 67 → 72

### 4f. Prisma Schema Migration (within Story 5.5.2)

Add to `open_positions` and `orders` tables:

```prisma
isPaper    Boolean  @default(false) @map("is_paper")

@@index([isPaper, status])
```

Migration created during Story 5.5.2 implementation. Default `false` ensures backward compatibility — all existing records are treated as live.

## Section 5: Implementation Handoff

**Scope:** Moderate — new epic with 3 stories, 4 artifact updates.

**Sequencing:** Epic 5.5 begins after Epic 5 completes (Stories 5.3–5.5 done). Epic 5 execution primitives (order submission, position tracking, single-leg handling) must exist before paper trading can wrap them.

**Parallelization note:** Story 5.5.1 (connector decorator + fill simulation) depends only on `IPlatformConnector`, which exists since Epic 1. It has no dependency on Stories 5.3–5.5. If schedule pressure arises, 5.5.1 can be parallelized with Epic 5's remaining stories. Stories 5.5.2 and 5.5.3 depend on execution tables and mixed-mode scenarios from Epic 5, so they must wait. Default recommendation: sequential after Epic 5 (safer).

**Handoff:**
1. Scrum Master (SM) applies artifact changes to: `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, `sprint-status.yaml`
2. Dev agent implements Stories 5.5.1 → 5.5.2 → 5.5.3 sequentially via standard create-story flow
3. Each story follows the post-edit workflow: lint → test → verify all existing tests pass

**Success Criteria:**
- PaperTradingConnector decorator wraps any IPlatformConnector implementation
- Per-platform mode and fill simulation configurable via environment variables
- `is_paper` flag isolates paper positions at repository level
- Mixed mode operation validated (live + paper platforms in same engine instance)
- All pre-existing tests pass, zero lint errors
- New unit tests + E2E test for mixed mode cycle

**Dependencies:**
- Epic 5 Stories 5.3–5.5 must be complete for Stories 5.5.2–5.5.3 (execution primitives exist)
- Story 5.5.1 depends only on IPlatformConnector (available since Epic 1) — parallelizable if needed
- No external dependencies (uses existing order book data, no new API integrations)
