# Sprint Change Proposal: Startup Performance — Excessive Resource Consumption

**Date:** 2026-04-13
**Epic:** 10.96 (Live Trading Engine Alignment & Configuration Calibration)
**Scope:** Minor — Direct implementation by dev team
**Status:** Approved

---

## 1. Issue Summary

Launching the PM Arbitrage Engine on a MacBook Pro M1 (16 GB RAM) causes immediate and sustained high CPU/thermal load. Investigation identified two root causes in the infrastructure layer — both active regardless of whether the trading pipeline is enabled.

**Root Cause 1 — WebSocket infinite reconnection loops:**
`RETRY_STRATEGIES.WEBSOCKET_RECONNECT.maxRetries` is set to `Infinity` (`src/common/errors/platform-api-error.ts:57-62`). When connectors fail to authenticate (placeholder credentials in dev, or expired credentials in production), both Kalshi and Polymarket WebSocket clients retry forever with exponential backoff capped at 60s. Each attempt involves RSA-PSS signature computation (Kalshi), DNS/TLS negotiation, and 10s connection timeout timers.

**Root Cause 2 — Gas estimation blocking module init:**
`GasEstimationService.onModuleInit()` (`src/connectors/polymarket/gas-estimation.service.ts:102-107`) synchronously awaits `this.poll()`, which makes two external network calls (Polygon RPC + CoinGecko API). This blocks module initialization on external service availability. The service already has a static fallback ($0.30 USD) that handles the case when cached values are absent.

**Eliminated from scope:** Startup reconciliation was initially suspected but investigation confirmed it completes in 1-5ms in dev (zero live positions = zero API calls, already guards on connector health).

---

## 2. Impact Analysis

### Epic Impact
- **Epic 10.96 (in-progress):** No impact on existing stories. Fix improves developer experience for remaining 10.96 work (10-96-2, 10-96-3, 10-96-4).
- **No other epics affected.**

### Artifact Conflicts
- **Architecture doc:** Amendment needed — WebSocket reconnection policy currently implies infinite retries. Must document configurable `maxRetries`.
- **PRD:** No conflict. NFR-I3 specifies exponential backoff strategy but is silent on retry count.
- **UI/UX:** No impact.
- **Environment config:** New env vars needed in `.env.example`, `.env.development`, `env.schema.ts`.

### Technical Impact
- 3 source files modified (retry config, gas estimation service, Kalshi connector credential guard)
- 1 planning artifact amended (architecture.md)
- 2-3 env config files updated
- Existing tests need minor adjustments (gas estimation init test, WebSocket reconnection tests)

---

## 3. Recommended Approach

**Path:** Direct Adjustment — course correction story within Epic 10.96.

**Rationale:**
- Low effort (3 service files + config + architecture doc)
- Low risk (non-functional changes to startup behavior, no business logic)
- High developer impact (eliminates thermal throttling during local development)
- Production benefit (finite retries prevent zombie reconnection loops if credentials expire at runtime; non-blocking gas init reduces startup latency)

**Effort:** Low (estimated 1 story, ~10-15 tasks)
**Risk:** Low
**Timeline impact:** None — parallelizable with remaining 10.96 stories

---

## 4. Detailed Change Proposals

### CP-1: Cap WebSocket reconnection retries (Approved)

**File:** `src/common/errors/platform-api-error.ts` (lines 57-62)

```
OLD:
WEBSOCKET_RECONNECT: {
    maxRetries: Infinity,
    initialDelayMs: 1000,
    maxDelayMs: 60000,
    backoffMultiplier: 2,
},

NEW:
WEBSOCKET_RECONNECT: {
    maxRetries: 10,
    initialDelayMs: 1000,
    maxDelayMs: 60000,
    backoffMultiplier: 2,
},
```

**Additional:** Improve Kalshi connector credential guard (`kalshi.connector.ts:168`) to reject placeholder values like `your-key-id-here`, not just empty strings.

**Rationale:** 10 retries with exponential backoff covers ~17 minutes of transient network issues. Persistent failures surface as degraded health via the degradation protocol (Story 2.4). Infinite retries with bad credentials create silent sustained CPU burn.

### CP-2: Make gas estimation non-blocking at startup (Approved)

**File:** `src/connectors/polymarket/gas-estimation.service.ts` (lines 102-107)

```
OLD:
async onModuleInit(): Promise<void> {
    await this.poll();
    ...
}

NEW:
async onModuleInit(): Promise<void> {
    void this.poll();
    ...
}
```

**Rationale:** The service's fallback chain (`getGasEstimateUsd()` returns `staticFallbackUsd` when no cached values exist) already handles the case when external APIs are unreachable. Blocking module init on two external calls adds unnecessary startup latency. First interval tick (30s) populates the cache.

**Test impact:** `'starts polling on onModuleInit'` test needs `flushPromises` or `runAllTimersAsync` to let the fire-and-forget poll complete before assertion.

### CP-3: Architecture doc amendment (Approved)

**File:** `_bmad-output/planning-artifacts/architecture.md`

**Section:** WebSocket Reconnection Policy

**Amendment:** Document configurable `maxRetries` (default 10) replacing implicit infinite retry assumption. Include rationale about CPU impact of infinite retries with invalid credentials.

---

## 5. Implementation Handoff

**Scope classification:** Minor — direct implementation by dev team.

**Story:** Add as course correction story `10-96-1a-startup-performance-websocket-gas-fixes` in Epic 10.96.

**Handoff:** Dev agent implements via `bmad-dev-skill` with TDD cycle.

**Success criteria:**
1. App starts without causing sustained CPU spike on M1 MacBook
2. WebSocket clients stop retrying after 10 failed attempts and report `disconnected` health
3. Gas estimation uses static fallback during startup, populates dynamic estimate on first successful poll
4. Kalshi connector rejects placeholder API key values
5. All existing tests pass (with minor adjustments to gas estimation and WS reconnection tests)
6. Architecture doc reflects configurable maxRetries policy
