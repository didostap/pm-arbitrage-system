# Sprint Change Proposal — Settings Infrastructure (DB-Backed Configuration)

**Date:** 2026-03-22
**Triggered by:** Operational requirement post-Epic 10 completion
**Scope Classification:** Moderate
**Approved:** Yes — 2026-03-22

---

## Section 1: Issue Summary

**Problem Statement:** The system has ~80 environment variables controlling operational behavior (exit strategy, risk thresholds, auto-unwind, discovery pipeline, LLM scoring, paper trading, etc.). Only bankroll is currently DB-backed and editable via the dashboard (Story 9-14). All other tunables require SSH → `.env` edit → process restart. This conflicts with the PRD's operational autonomy goal (30-45 min/day at steady state) and the architecture's EngineConfig DB pattern.

**Discovery Context:** Identified after Epic 10 completion as the system matures toward live trading. Frequent tuning of exit parameters, risk limits, and discovery settings during paper trading validation highlighted the friction.

**Evidence:**
- `.env.example` contains ~80 variables across 20+ logical groups
- Story 9-14 proved the DB → hot-reload → event → WS broadcast pattern for bankroll
- Architecture doc specifies EngineConfig as "singleton model with typed columns — not a generic key-value store"
- PRD Cross-Cutting Concern #5: "Configuration Management — all must be configurable without code changes"

---

## Section 2: Impact Analysis

### Epic Impact
- **No existing epics affected.** Epic 10 is complete. Epics 11-12 remain in backlog, unmodified.
- **New Epic 10.5** created: "Settings Infrastructure — DB-Backed Configuration & Dashboard Settings Page"
- Slots between completed Epic 10 and backlog Epic 11 with zero dependency conflicts.

### Story Impact
- No existing stories modified. Three new stories defined (see Section 4).

### Artifact Conflicts
- **PRD:** No conflict. Fulfills Cross-Cutting Concern #5 more completely.
- **Architecture:** Compliant. Typed columns on EngineConfig singleton (not key-value store).
- **UX Design:** New Settings page section needed. Follows existing sidebar navigation pattern (Story 9-13), reuses InfoTooltip (Story 9-21), shadcn/ui primitives.
- **Prisma Schema:** Migration to extend EngineConfig model with ~79 typed columns.
- **Dashboard SPA:** New route, page component, API hooks. Generated API client regeneration.

### Technical Impact
- Env vars remain as seed defaults (first run when DB is empty) and fallback values.
- Services refactored to read from DB via shared `getEffectiveConfig()` helper.
- Cron-based settings (discovery, resolution, calibration, telegram) require dynamic `SchedulerRegistry` updates.
- Hot-reload is per-module scoped — only affected services reload on change.

---

## Section 3: Recommended Approach

**Selected Path:** Option 1 — Direct Adjustment

**Rationale:**
- The bankroll pattern (Story 9-14) is battle-tested: DB singleton → typed columns → repository → service hot-reload → event emission → WS broadcast → dashboard UI
- Extending this to all tunables is a natural evolution, not architectural novelty
- Three stories provide clean vertical slices: data layer → API/wiring → UI
- No rollback needed, no MVP scope change, no architectural redesign

**Effort Estimate:** Medium (3 stories, each medium complexity)
**Risk Level:** Low — proven pattern, no new dependencies
**Timeline Impact:** None on Epic 11/12. Epic 10.5 completes before Epic 11 begins.

---

## Section 4: Detailed Change Proposals

### Epic Definition

**Epic 10.5: Settings Infrastructure — DB-Backed Configuration & Dashboard Settings Page**

Move all operational environment variables (~79 tunables) from .env files to the EngineConfig DB singleton with typed columns, expose via grouped Settings page with hot-reload, appropriate input types, tooltip hints, and enum enforcement. Excludes infrastructure vars (NODE_ENV, PORT, DATABASE_URL), platform URLs, credentials/secrets, and startup-only flags (DISCOVERY_RUN_ON_STARTUP).

---

### Variable Classification

**Excluded from Settings page (stay in .env only):**

| Category | Variables |
|----------|-----------|
| Infrastructure | `NODE_ENV`, `PORT`, `DATABASE_URL` |
| Platform URLs | `KALSHI_API_BASE_URL`, `POLYMARKET_CLOB_API_URL`, `POLYMARKET_WS_URL`, `POLYMARKET_CHAIN_ID`, `POLYMARKET_GAMMA_API_URL` |
| Credentials/Secrets | `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PATH`, `POLYMARKET_PRIVATE_KEY`, `OPERATOR_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `LLM_PRIMARY_API_KEY`, `LLM_ESCALATION_API_KEY` |
| Startup-only | `DISCOVERY_RUN_ON_STARTUP` |
| Platform config | `KALSHI_API_TIER` |

**Settings page groups (79 tunables, display order):**

| Order | Section | Variables | Count |
|-------|---------|-----------|-------|
| 1 | Exit Strategy | `EXIT_MODE`, `EXIT_EDGE_EVAP_MULTIPLIER`, `EXIT_CONFIDENCE_DROP_PCT`, `EXIT_TIME_DECAY_HORIZON_H`, `EXIT_TIME_DECAY_STEEPNESS`, `EXIT_TIME_DECAY_TRIGGER`, `EXIT_RISK_BUDGET_PCT`, `EXIT_RISK_RANK_CUTOFF`, `EXIT_MIN_DEPTH`, `EXIT_PROFIT_CAPTURE_RATIO` | 10 |
| 2 | Risk Management | `RISK_MAX_POSITION_PCT`, `RISK_MAX_OPEN_PAIRS`, `RISK_DAILY_LOSS_PCT` | 3 |
| 3 | Execution | `EXECUTION_MIN_FILL_RATIO`, `ADAPTIVE_SEQUENCING_ENABLED`, `ADAPTIVE_SEQUENCING_LATENCY_THRESHOLD_MS`, `POLYMARKET_ORDER_POLL_TIMEOUT_MS`, `POLYMARKET_ORDER_POLL_INTERVAL_MS` | 5 |
| 4 | Auto-Unwind | `AUTO_UNWIND_ENABLED`, `AUTO_UNWIND_DELAY_MS`, `AUTO_UNWIND_MAX_LOSS_PCT` | 3 |
| 5 | Detection & Edge Calculation | `DETECTION_MIN_EDGE_THRESHOLD`, `DETECTION_GAS_ESTIMATE_USD`, `DETECTION_POSITION_SIZE_USD`, `MIN_ANNUALIZED_RETURN` | 4 |
| 6 | Discovery Pipeline | `DISCOVERY_ENABLED`, `DISCOVERY_CRON_EXPRESSION`, `DISCOVERY_PREFILTER_THRESHOLD`, `DISCOVERY_SETTLEMENT_WINDOW_DAYS`, `DISCOVERY_MAX_CANDIDATES_PER_CONTRACT`, `DISCOVERY_LLM_CONCURRENCY` | 6 |
| 7 | LLM Confidence Scoring | `LLM_PRIMARY_PROVIDER`, `LLM_PRIMARY_MODEL`, `LLM_ESCALATION_PROVIDER`, `LLM_ESCALATION_MODEL`, `LLM_ESCALATION_MIN`, `LLM_ESCALATION_MAX`, `LLM_AUTO_APPROVE_THRESHOLD`, `LLM_MIN_REVIEW_THRESHOLD`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_MS` | 10 |
| 8 | Resolution & Calibration | `RESOLUTION_POLLER_ENABLED`, `RESOLUTION_POLLER_CRON_EXPRESSION`, `RESOLUTION_POLLER_BATCH_SIZE`, `CALIBRATION_ENABLED`, `CALIBRATION_CRON_EXPRESSION` | 5 |
| 9 | Data Quality & Staleness | `ORDERBOOK_STALENESS_THRESHOLD_MS`, `WS_STALENESS_THRESHOLD_MS`, `DIVERGENCE_PRICE_THRESHOLD`, `DIVERGENCE_STALENESS_THRESHOLD_MS`, `KALSHI_POLLING_CONCURRENCY`, `POLYMARKET_POLLING_CONCURRENCY` | 6 |
| 10 | Paper Trading | `PLATFORM_MODE_KALSHI`, `PLATFORM_MODE_POLYMARKET`, `PAPER_FILL_LATENCY_MS_KALSHI`, `PAPER_SLIPPAGE_BPS_KALSHI`, `PAPER_FILL_LATENCY_MS_POLYMARKET`, `PAPER_SLIPPAGE_BPS_POLYMARKET`, `ALLOW_MIXED_MODE` | 7 |
| 11 | Trading Engine | `POLLING_INTERVAL_MS` | 1 |
| 12 | Gas Estimation (Polymarket) | `GAS_BUFFER_PERCENT`, `GAS_POLL_INTERVAL_MS`, `GAS_POL_PRICE_FALLBACK_USD`, `POLYMARKET_SETTLEMENT_GAS_UNITS`, `POLYMARKET_RPC_URL` | 5 |
| 13 | Telegram Alerts | `TELEGRAM_TEST_ALERT_CRON`, `TELEGRAM_TEST_ALERT_TIMEZONE`, `TELEGRAM_SEND_TIMEOUT_MS`, `TELEGRAM_MAX_RETRIES`, `TELEGRAM_BUFFER_MAX_SIZE`, `TELEGRAM_CIRCUIT_BREAK_MS` | 6 |
| 14 | Logging & Compliance | `CSV_TRADE_LOG_DIR`, `CSV_ENABLED`, `COMPLIANCE_MATRIX_CONFIG_PATH`, `AUDIT_LOG_RETENTION_DAYS`, `DASHBOARD_ORIGIN` | 5 |
| 15 | Stress Testing | `STRESS_TEST_SCENARIOS`, `STRESS_TEST_DEFAULT_DAILY_VOL`, `STRESS_TEST_MIN_SNAPSHOTS` | 3 |

**Total: 79 tunables across 15 groups**

---

### Story 10-5-1: EngineConfig Schema Expansion & Seed Migration

**Goal:** Extend the EngineConfig Prisma singleton with typed columns for all 79 tunable variables (15 groups). Seed from env vars on first run (no DB row). Existing bankroll columns untouched.

**Acceptance Criteria:**

- **AC1:** Prisma migration adds typed columns to EngineConfig for all 79 tunables, grouped by logical domain. Column types match variable semantics:
  - Boolean for toggles (DISCOVERY_ENABLED, CSV_ENABLED, etc.)
  - Decimal(20,8) for financial values (thresholds, percentages)
  - Integer for counts/ms values (POLLING_INTERVAL_MS, RISK_MAX_OPEN_PAIRS)
  - String for enums/free-text (EXIT_MODE, LLM_PRIMARY_PROVIDER, cron expressions)
  - All columns nullable — null means "use env var default."
- **AC2:** Enum types in DB where applicable:
  - EXIT_MODE: 'fixed' | 'model' | 'shadow'
  - PLATFORM_MODE: 'live' | 'paper'
  - LLM_PROVIDER: 'gemini' | 'anthropic'
  - Store as String with Zod validation (not Prisma enum — avoids migration churn when adding values).
- **AC3:** EngineConfigRepository extended with:
  - `get()` returns full config (existing, no change)
  - `upsertSettings(partial: Partial<EngineConfigSettings>)` — merge-update
  - `getEffectiveConfig()` — DB values merged over env defaults (DB wins)
- **AC4:** Seed logic: on first startup (no DB row), upsert creates row with all values from env vars. Subsequent startups read from DB. Env vars remain as fallback defaults only.
- **AC5:** Existing bankroll columns (bankrollUsd, paperBankrollUsd) untouched. Existing bankroll endpoints and hot-reload flow unchanged.
- **AC6:** Column naming follows snake_case convention (@map). Example: exitMode → exit_mode, detectionMinEdgeThreshold → detection_min_edge_threshold.
- **AC7:** All new columns have JSDoc comments documenting purpose, unit, and valid range (matches .env.example comments).
- **AC8:** Tests: repository unit tests for upsert partial merge, getEffectiveConfig fallback logic, seed-on-first-run behavior.

**Technical Notes:**
- Architecture mandates typed columns, not key-value store
- Nullable columns enable incremental adoption — services can check DB first, fall back to ConfigService.get() if null
- This story does NOT change how services read config — that's Story 10-5-2

---

### Story 10-5-2: Settings CRUD Endpoints & Hot-Reload Mechanics

**Goal:** Expose all 79 DB-backed tunables via REST endpoints with validation, wire services to read from DB (falling back to env), and implement hot-reload so changes take effect without restart.

**Acceptance Criteria:**

- **AC1:** `GET /api/dashboard/settings` — returns all settings grouped by section (15 groups), each variable with: current value, env default, data type, description (tooltip text), valid range/options, group name. Response follows standard `{ data, timestamp }` wrapper.
- **AC2:** `PATCH /api/dashboard/settings` — accepts partial update of any subset of settings. Validates each field:
  - Type checking (boolean, number, string, decimal)
  - Range validation where applicable (e.g., RISK_MAX_POSITION_PCT 0-1, AUTO_UNWIND_DELAY_MS 0-30000)
  - Enum validation (EXIT_MODE, PLATFORM_MODE, LLM_PROVIDER)
  - Returns updated settings + timestamp.
- **AC3:** `POST /api/dashboard/settings/reset` — resets specified fields (or all) back to env var defaults. Sets DB columns to null (triggering fallback).
- **AC4:** Settings metadata registry: a typed constant mapping each setting key to `{ group, label, description, type, default, min?, max?, options?, unit? }`. Single source of truth for API responses, validation, and frontend rendering.
- **AC5:** Hot-reload mechanism: after PATCH, affected services reload their config from DB. Pattern follows bankroll precedent: DB persist → service.reloadConfig() → event emission → WS broadcast. Event: `ConfigSettingsUpdatedEvent` with changed fields + previous values.
- **AC6:** Services refactored to read tunables via a shared `getEffectiveConfig()` helper (DB value ?? env default). Each module reads its relevant group on init and on reload. Services that cache config in memory (RiskManager, ExitMonitor, DetectionService, etc.) implement `reloadConfig()`.
- **AC7:** WS event `config.settings.updated` broadcast on every change, carrying changed field names and new values. Dashboard can react in real-time.
- **AC8:** Audit log entry for every settings change: who changed what, old → new values, timestamp. Uses existing AuditLog infrastructure.
- **AC9:** Validation DTOs with class-validator decorators for all 79 fields (all optional — PATCH semantics). Zod schema from Story 10-5-1 used for runtime validation of enum/range constraints.
- **AC10:** Tests:
  - Controller: PATCH with valid/invalid payloads, reset endpoint
  - Service: hot-reload triggers, event emission, fallback logic
  - Integration: settings change → service picks up new value

**Technical Notes:**
- PATCH (not PUT) — partial updates are the common case
- Settings metadata registry avoids duplicating descriptions/ranges across backend validation, API responses, and frontend rendering
- Hot-reload is per-module: only affected services reload. E.g., changing EXIT_MODE reloads ExitMonitor but not DiscoveryService.
- Cron-expression changes (DISCOVERY_CRON_EXPRESSION, etc.) require special handling — NestJS @Cron is decorator-based. Use SchedulerRegistry to dynamically update cron jobs at runtime.

---

### Story 10-5-3: Dashboard Settings Page UI

**Goal:** New Settings page in the dashboard SPA with grouped sections, appropriate input controls, tooltip hints, and real-time sync via WebSocket.

**Acceptance Criteria:**

- **AC1:** New "Settings" route (`/settings`) added to sidebar navigation (AppSidebar). Icon: gear/cog. Positioned after Stress Testing, before any future items.
- **AC2:** Page layout: vertical scrollable list of 15 collapsible sections, ordered per approved specification:
  1. Exit Strategy
  2. Risk Management
  3. Execution
  4. Auto-Unwind
  5. Detection & Edge Calculation
  6. Discovery Pipeline
  7. LLM Confidence Scoring
  8. Resolution & Calibration
  9. Data Quality & Staleness
  10. Paper Trading
  11. Trading Engine
  12. Gas Estimation (Polymarket)
  13. Telegram Alerts
  14. Logging & Compliance
  15. Stress Testing
- **AC3:** Each setting rendered with the appropriate input type:
  - Boolean → Toggle switch (shadcn Switch)
  - Enum (EXIT_MODE, PLATFORM_MODE, LLM_PROVIDER) → Select dropdown
  - Number/Integer → Number input with min/max constraints
  - Decimal → Text input with decimal validation
  - String (cron, paths) → Text input
  - Milliseconds → Number input with "ms" unit label
- **AC4:** Every setting has an InfoTooltip (existing component) showing: description text, unit, valid range, and env var name. Tooltip text sourced from the settings metadata returned by `GET /api/dashboard/settings`.
- **AC5:** Inline save per field: changing a value triggers debounced PATCH (300ms debounce). Success → green flash confirmation. Failure → red flash + toast with validation error. No page-level "Save All" button.
- **AC6:** "Reset to default" action per field (icon button) and per section ("Reset section" link). Triggers `POST /api/dashboard/settings/reset` for the relevant fields. Confirmation dialog before reset.
- **AC7:** Each field shows its env default value as placeholder/hint text when the DB value matches the default (subtle "(default)" label). When user has overridden a value, show a visual indicator (dot or different background) distinguishing it from defaults.
- **AC8:** Real-time sync: listen for WS `config.settings.updated` events. If another session changes a setting, update the displayed value in real-time with a brief highlight animation.
- **AC9:** Section collapse state persisted in localStorage. All sections default to expanded on first visit.
- **AC10:** TanStack Query integration:
  - `useSettings()` query hook (GET /api/dashboard/settings)
  - `useUpdateSettings()` mutation hook (PATCH)
  - `useResetSettings()` mutation hook (POST reset)
  - Optimistic updates on PATCH for responsive feel
  - Invalidate on WS event for cross-session sync
- **AC11:** Responsive layout: single-column on mobile, two-column grid on desktop (label+tooltip left, input right). Touch-friendly targets.
- **AC12:** Generated API client regenerated to include new endpoints.
- **AC13:** Tests: component tests for input type rendering per data type, debounced save behavior, reset confirmation flow, WS update handling.

**Technical Notes:**
- Leverage existing shadcn/ui primitives (Switch, Select, Input, Collapsible, Tooltip). No new UI library dependencies.
- InfoTooltip component already exists (Story 9-21). Reuse directly.
- Settings metadata from API drives rendering — frontend has zero hardcoded field definitions. Adding a new setting in the backend auto-appears on UI.
- Debounced inline save provides responsive feel without save button ceremony. The bankroll precedent uses a dialog — Settings page is higher density, so inline edit is more appropriate.

---

## Section 5: Implementation Handoff

**Change Scope:** Moderate — new epic with 3 stories, proven pattern, no architectural changes.

**Handoff:** Dev agent implements stories sequentially:
1. **10-5-1** (schema + seed) — blocks 10-5-2
2. **10-5-2** (API + hot-reload) — blocks 10-5-3
3. **10-5-3** (dashboard UI) — depends on 10-5-2

**Success Criteria:**
- All 79 tunables editable via Settings page without restart
- Env vars continue to work as seed defaults on fresh deployment
- Existing bankroll flow untouched
- Hot-reload verified: change EXIT_MODE on Settings page → ExitMonitor uses new mode within seconds
- Audit trail captures all settings changes

**Sprint Status Updates Required:**
- Add `epic-10-5: backlog` with stories `10-5-1`, `10-5-2`, `10-5-3` as backlog
