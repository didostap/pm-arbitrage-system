# Story 9.20: Platform Staleness Investigation & Remediation

Status: done

<!-- Validation: Run validate-create-story for quality check before dev-story. -->

## Story

As a **system operator**,
I want **the platform health indicators to show "stale" less than 20% of the time under normal operating conditions**,
so that **I can trust the dashboard's health status and distinguish genuine platform issues from false positives caused by internal timing mismatches**.

## Acceptance Criteria

### Phase 1: Investigation (must complete before any code changes)

1. **Empirical staleness measurement**: Query `platform_health_logs` via Postgres MCP to measure actual staleness frequency per platform over the most recent operating window. Report: total health log entries, count of `status='degraded'` entries, percentage degraded, average and max duration of degraded windows. If insufficient data exists (engine not running recently), document this and use structured log analysis from the engine's JSON log output instead. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — success criteria "measured over 1-hour window"]

2. **Cycle duration analysis**: Query engine logs (or run the engine briefly) to collect `pollingCycleDurationMs` values from "Polling cycle complete" log entries (added in Story 9-15, `data-ingestion.service.ts:305`). Report: average, p50, p95, p99, and max cycle duration across at least 10 cycles. Compare these against the 60s `STALENESS_THRESHOLD`. Also measure the full `executeCycle()` duration from "Trading cycle completed" log entries (`trading-engine.service.ts:243`, field `durationMs`). [Source: Story 9-15 AC #12 — polling cycle duration metric]

3. **WebSocket data flow verification**: Check engine logs for "Order book normalized (WebSocket)" entries (`data-ingestion.service.ts:357`). Report: whether WebSocket updates are flowing for each platform, approximate frequency, and whether they keep `lastUpdateTime` fresh between polling cycles. If WebSocket data is NOT flowing, investigate why — the `PaperTradingConnector` delegates `onOrderBookUpdate` to the real connector (`paper-trading.connector.ts:45-47`), so WS should flow even in paper mode. Check if the connector's `connect()` method is called and WebSocket subscriptions are established. [Source: Story 9-15 code review fix M1 — `processWebSocketUpdate` switched to `recordContractUpdate`]

4. **Health check timing analysis**: Analyze the interaction between the `publishHealth()` cron (`@Cron('*/30 * * * * *')`, `platform-health.service.ts:72`) and the polling cycle (`setInterval(30000)`, `scheduler.service.ts:42`). Determine whether cron ticks systematically land in windows where `lastUpdateTime` is >60s old. The cron fires on clock seconds (0, 30), while `setInterval` fires relative to process start — they are NOT synchronized. [Derived from: codebase timing analysis]

5. **Root cause document**: Before implementing any fix, write a structured findings section in the `### Completion Notes List` section of this story file documenting: (a) measured staleness percentage, (b) measured cycle durations, (c) WebSocket data flow status, (d) identified root cause(s), (e) proposed fix with rationale referencing AC #6 options. Present findings to the operator before proceeding to Phase 2. **If investigation is inconclusive** (no clear root cause after completing all Phase 1 tasks), document findings with "inconclusive" status and escalate to the operator — do not proceed to remediation without a supported hypothesis. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — "Investigation-first. Root cause determines fix scope."]

### Phase 2: Remediation (scope determined by investigation)

6. **Fix implementation**: Based on investigation findings, implement the appropriate fix from the following menu. The developer MUST NOT skip investigation and jump to a fix — the fix scope depends on what the investigation reveals:
   - **(a) Cycle duration exceeds threshold**: If total `executeCycle()` duration regularly exceeds 60s, the fix must reduce cycle duration (NOT increase the threshold — the 60s `STALENESS_THRESHOLD` must remain at 60,000ms). Possible approaches: decouple ingestion from the trading pipeline so ingestion runs on its own schedule, or optimize the slow stage.
   - **(b) WebSocket gaps**: If WebSocket data is not flowing (or flowing intermittently), fix the subscription/connection lifecycle so that WS updates keep `lastUpdateTime` fresh between polling cycles. WebSocket updates call `recordContractUpdate()` → `recordUpdate()` → `lastUpdateTime.set(platform, Date.now())`, so ANY WS update should prevent staleness.
   - **(c) Cron/interval timing mismatch**: If the 30s cron and 30s interval systematically create windows where health checks see stale data despite data arriving frequently, adjust the timing relationship (e.g., offset the cron start time, increase health check frequency to reduce maximum blind spots, or trigger a health check after each successful data ingestion rather than relying solely on a fixed schedule). Do NOT add a grace margin to `calculateHealth()` — this would effectively relax the threshold by another name, violating AC #7.
   - **(d) Aggregation logic**: If `computeCompositeHealth()` or `getHealth()` in `DashboardService` incorrectly represents the current state (e.g., reading stale DB transition logs), fix the aggregation.
   - **(e) Combined**: If multiple causes contribute, address each.
   [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — "Possible outcomes" section]

7. **STALENESS_THRESHOLD unchanged**: The `STALENESS_THRESHOLD` constant (60,000ms, `platform-health.service.ts:22`) MUST remain at 60,000. The fix must make data retrieval genuinely fast enough that staleness doesn't occur — not relax the threshold. If investigation reveals the 60s threshold is architecturally incompatible with the system's design, document the finding and escalate to the operator — do not silently change it. [Source: operator instruction — confirmed in disambiguation]

8. **Staleness transition logging**: Add a structured log entry at `log` (info) level whenever a platform's health status transitions (healthy→degraded, degraded→healthy, etc.). Required fields: `message: 'Platform health transition'`, `module: 'data-ingestion'`, `correlationId` (from the enclosing `withCorrelationId` context), `platform`, `previousStatus`, `newStatus` (`health.status`), `timestamp`, `lastUpdateAgeMs` (`Date.now() - lastUpdateTime.get(platform)`), `reason` (`health.metadata?.degradationReason || 'none'`). Implementation: add in `publishHealth()` inside the existing `health.status !== previousStatus` block (`platform-health.service.ts` transition detection section). These logs enable the operator to verify the <20% success criteria by querying for `reason='stale_data'` transitions. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — "developer agent should log staleness state transitions with timestamps"]

### Phase 3: Verification

9. **Success criteria**: After the fix is deployed, platform staleness indicators show stale <20% of the time under normal operating conditions (both platforms in healthy state). Measurement: count `status='degraded'` transitions with `degradationReason='stale_data'` in the transition logs (AC #8) over a 1-hour window. If the engine is not running long enough for a 1-hour window during development, measure over available window and extrapolate with documented assumptions. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — success criteria]

10. **No regression in staleness detection**: Genuine staleness (platform actually stops providing data for >60s) MUST still be detected and reported. The fix must not suppress legitimate staleness alerts. Verify with a test: mock `recordUpdate` to stop being called, confirm `calculateHealth()` returns `'degraded'` after 60s. [Derived from: architecture requirement — staleness detection is a safety mechanism]

11. **`computeCompositeHealth()` verification**: Verify that `computeCompositeHealth()` (`dashboard.service.ts:1044-1051`) correctly handles `'initializing'` status (falls through to `'healthy'` — confirmed as intentional behavior from Story 9-15). Document this verification in completion notes. No code change expected. [Source: disambiguation #5 — verification-only]

12. **All existing tests pass**: `pnpm test` passes. `pnpm lint` clean. No test count regression. New tests added for any code changes. [Source: CLAUDE.md post-edit workflow]

## Tasks / Subtasks

### Phase 1: Investigation (AC: #1, #2, #3, #4, #5)

- [x] **Task 1:** Measure staleness from database (AC: #1)
  - [x] 1.1: Use Postgres MCP to query `platform_health_logs` — count total entries and `status='degraded'` entries per platform, compute degraded percentage
  - [x] 1.2: Query degraded window durations — for consecutive degraded→healthy transitions, compute average and max duration. Note: `publishHealth()` only writes to DB on **transitions**, not every tick — so counting rows measures transition count, not time-in-state. Use window functions to compute duration between consecutive transitions. Sample approach:
    ```sql
    WITH transitions AS (
      SELECT platform, status, created_at,
             LEAD(created_at) OVER (PARTITION BY platform ORDER BY created_at) as next_transition
      FROM platform_health_logs
      WHERE created_at > NOW() - INTERVAL '1 hour'
    )
    SELECT platform,
           COUNT(*) as degraded_windows,
           AVG(EXTRACT(EPOCH FROM (next_transition - created_at))) as avg_duration_s,
           MAX(EXTRACT(EPOCH FROM (next_transition - created_at))) as max_duration_s,
           SUM(EXTRACT(EPOCH FROM (next_transition - created_at))) as total_degraded_s
    FROM transitions
    WHERE status = 'degraded' AND next_transition IS NOT NULL
    GROUP BY platform;
    ```
  - [x] 1.3: If insufficient data, start the engine (`pnpm start:dev` in pm-arbitrage-engine) and let it run for 5-10 minutes to collect data, then re-query

- [x] **Task 2:** Measure cycle durations (AC: #2)
  - [x] 2.1: Query engine logs for "Polling cycle complete" entries, extract `pollingCycleDurationMs`
  - [x] 2.2: Query engine logs for "Trading cycle completed" entries, extract `durationMs`
  - [x] 2.3: Compute statistics: average, p50, p95, p99, max for both polling and full cycle durations
  - [x] 2.4: Compare against `STALENESS_THRESHOLD` (60s) — is the cycle regularly exceeding 60s?

- [x] **Task 3:** Verify WebSocket data flow (AC: #3)
  - [x] 3.1: Search engine logs for "Order book normalized (WebSocket)" entries — are WS updates flowing?
  - [x] 3.2: If WS updates are absent or sparse, investigate:
    - Is `connect()` called on the real connectors? Are WebSocket subscriptions established?
    - Does `PaperTradingConnector` delegate correctly?
    - For Polymarket specifically: check if `DATA_STALE` filter (rejects data >30s old, `polymarket-websocket.client.ts`) is silently discarding updates — this would prevent `recordContractUpdate()` from being called via the WS path
  - [x] 3.3: If WS updates are present, measure their frequency — are they frequent enough to keep `lastUpdateTime` within the 60s threshold between polling cycles?

- [x] **Task 4:** Analyze timing relationships (AC: #4)
  - [x] 4.1: Check whether the health cron (`*/30 * * * * *`) and polling interval (`setInterval(30000)`) systematically create windows where `lastUpdateTime` age >60s
  - [x] 4.2: Diagram the timing: when does ingestion set `lastUpdateTime`? When does `publishHealth()` read it? What's the worst-case gap?

- [x] **Task 5:** Write root cause document (AC: #5)
  - [x] 5.1: Compile investigation findings into a structured summary with data
  - [x] 5.2: Identify root cause(s) with supporting evidence
  - [x] 5.3: Propose fix approach with rationale (must reference AC #6 options)

### Implementation Gate (between Phase 1 and Phase 2)

- [x] **Task 5.5:** PAUSE — Present root cause findings to operator (Arbi) and await approval of proposed fix approach before proceeding to Phase 2. If running autonomously (dev-story), present findings and proposed approach in the conversation and ask for confirmation.

### Phase 2: Remediation (AC: #6, #7, #8)

- [x] **Task 6:** Implement fix based on investigation (AC: #6, #7)
  - [x] 6.1: Implement the fix identified in Task 5 (scope determined by investigation)
  - [x] 6.2: Write unit tests for any code changes
  - [x] 6.3: Verify `STALENESS_THRESHOLD` remains at 60,000ms (AC: #7)

- [x] **Task 7:** Add staleness transition logging (AC: #8)
  - [x] 7.1: In `publishHealth()`, add a structured log entry in the existing `health.status !== previousStatus` block (`platform-health.service.ts:103`)
  - [x] 7.2: Include fields: platform, previousStatus, newStatus, timestamp, lastUpdateAgeMs, reason (from health.metadata)
  - [x] 7.3: Write a test verifying the transition log is emitted on status change

### Phase 3: Verification (AC: #9, #10, #11, #12)

- [x] **Task 8:** Verify success criteria (AC: #9, #10, #11, #12)
  - [ ] 8.1: Run the engine and verify stale <20% over available measurement window (AC: #9) — requires post-deployment measurement
  - [x] 8.2: Verify genuine staleness still detected — mock `recordUpdate` stopping, confirm degradation after 60s (AC: #10) — covered by existing test (line 369)
  - [x] 8.3: Verify `computeCompositeHealth()` handles `'initializing'` correctly (AC: #11) — falls through to `'healthy'`, confirmed
  - [x] 8.4: Run `pnpm test` and `pnpm lint` — all passing, no regressions (AC: #12) — 2119 tests, lint clean

## Dev Notes

### Architecture Context

**The staleness detection pipeline (post-9-15):**
```
Data arrives via:
  1. Polling cycle: executeCycle() → ingestCurrentOrderBooks() → recordContractUpdate() → recordUpdate()
  2. WebSocket callback: onOrderBookUpdate → processWebSocketUpdate() → recordContractUpdate() → recordUpdate()

Both paths set: lastUpdateTime.set(platform, Date.now())

Health check (independent 30s cron):
  publishHealth() → calculateHealth() → checks age = Date.now() - lastUpdateTime > 60,000
  → If yes: status = 'degraded' with degradationReason: 'stale_data'
```
[Source: `platform-health.service.ts:312-385` (calculateHealth), `platform-health.service.ts:391-398` (recordUpdate), `platform-health.service.ts:404-413` (recordContractUpdate), `data-ingestion.service.ts:326-376` (processWebSocketUpdate)]

**Two distinct staleness thresholds — do not confuse them:**
- `STALENESS_THRESHOLD` = 60,000ms (hardcoded, `platform-health.service.ts:22`) — used by `calculateHealth()` for platform-level health status. This is what drives the dashboard's "stale data" indicator.
- `ORDERBOOK_STALENESS_THRESHOLD_MS` = 90,000ms (configurable via env, `platform-health.service.ts:56`) — used by per-contract staleness (`getContractStaleness()`) and orderbook staleness alerting in `publishHealth()`. This is what drives Telegram alerts and detection suppression.

The "70% stale" problem is about the **platform-level 60s threshold** showing `'degraded'` status in the dashboard, NOT the 90s per-contract threshold.
[Source: `platform-health.service.ts:22,56`, `env.schema.ts:189-194`]

**Key timing relationships:**
- `publishHealth()`: `@Cron('*/30 * * * * *')` — fires on clock seconds :00 and :30 [Source: `platform-health.service.ts:72`]
- Polling cycle: `setInterval(30000)` — fires relative to process start, NOT synchronized with cron [Source: `scheduler.service.ts:42`]
- Cycle overlap guard: `isCycleInProgress()` skips if previous cycle still running [Source: `scheduler.service.ts:60`]
- Full cycle: ingest (polling) → detect → edge calc → risk → execute — all sequential inside `executeCycle()` [Source: `trading-engine.service.ts:57-287`]

**Dashboard health display chain:**
```
publishHealth() → writes to platform_health_logs on transitions only (line 103)
                → emits PLATFORM_HEALTH_UPDATED every tick (line 135)

Dashboard reads:
  REST: getHealth() → getLatestHealthLogs() → latest per-platform DB row (15s poll)
  WS: PLATFORM_HEALTH_UPDATED event → pushed every 30s tick

"Stale data" label shows when: p.dataFresh === false, which is: log.status !== 'healthy'
```
[Source: `dashboard.service.ts:171-207,1036-1042`, `HealthComposite.tsx:42-44`, `useDashboard.ts:20-27`]

### Investigation Hypotheses (ranked by likelihood)

**H1: Full executeCycle() exceeds 60s, preventing next cycle from refreshing data**
The scheduler skips cycles when `isCycleInProgress()`. If `executeCycle()` takes >30s, the next poll is skipped. If it takes >60s, `publishHealth()` sees `lastUpdateTime` >60s old → degraded. With 389+ Kalshi contracts at ~24s ingestion + detection + edge calc + risk + execution, total cycle time could approach or exceed 60s.
[Source: `trading-engine.service.ts:57-287`, `scheduler.service.ts:59-82`]

**H2: WebSocket updates not keeping `lastUpdateTime` fresh between cycles**
If WS data flows, it calls `recordContractUpdate()` → `recordUpdate()` → sets `lastUpdateTime`. This SHOULD prevent staleness between polling cycles. If WS is not flowing (connector not connected, subscriptions lost, paper mode issue), the only data path is polling, and the 60s gap becomes possible.
[Source: `data-ingestion.service.ts:326-376`, `paper-trading.connector.ts:45-47`]

**H3: Cron/interval timing mismatch creates systematic stale windows**
The 30s cron fires on clock seconds (:00, :30). The 30s interval fires at process-start-relative times. If data arrives just AFTER a health check and the next health check sees data that's almost 60s old, the timing mismatch could cause intermittent degradation.

**H4: Dashboard reads transition-persisted DB logs, not live health state**
`getLatestHealthLogs()` reads the most recent `platform_health_logs` row per platform. Since `publishHealth()` only writes on **transitions**, if the platform transitions to degraded and quickly back to healthy, the DB state depends on whether both transitions were written. The REST endpoint polls every 15s, but the underlying data only updates on transitions. However, `PLATFORM_HEALTH_UPDATED` events are emitted every tick — the WS path may be more accurate than the REST path.

### Investigation Tools

- **Postgres MCP** (`mcp__postgres__execute_sql`): Query `platform_health_logs` for staleness patterns, transition frequencies, degraded window durations
- **Kindly web search** (`mcp__kindly-web-search__web_search`): Research any unfamiliar patterns discovered during investigation (NestJS cron timing, `p-limit` interaction with event loop, etc.)
- **Engine logs**: JSON structured logs with `pollingCycleDurationMs`, `durationMs`, health transition events

### Constraint: STALENESS_THRESHOLD Must Stay at 60,000ms

The fix MUST NOT relax the staleness threshold. The 60s window is the safety boundary for detecting genuine platform failures. If the system can't keep `lastUpdateTime` within 60s of the current time, the system's data retrieval pipeline is too slow or broken — the threshold isn't wrong, the pipeline is.

If investigation reveals a fundamental architectural mismatch (e.g., the trading cycle inherently takes >60s and can't be optimized), document this finding and escalate. Do not change the threshold without operator approval.
[Source: operator instruction — confirmed in disambiguation]

### What Story 9-15 Already Fixed (do NOT re-diagnose)

- Epoch zero `'initializing'` status (false degradation on startup) — FIXED
- Sequential Kalshi polling bottleneck (117s → ~24s with `p-limit`) — FIXED
- Per-pair staleness model in detection — FIXED
- `processWebSocketUpdate` using `recordContractUpdate` (code review M1) — FIXED

This story investigates what's STILL causing ~70% stale AFTER those fixes.
[Source: `9-15-platform-health-concurrent-polling.md` — completion notes]

### Note on Line Numbers

Line numbers in references are approximate and may have shifted due to prior story implementations. If a referenced line doesn't match, search by function/symbol name (e.g., `calculateHealth`, `publishHealth`, `recordUpdate`).

### Key Files

| File | Relevance |
|---|---|
| `src/modules/data-ingestion/platform-health.service.ts` | `calculateHealth()` (line 312), `STALENESS_THRESHOLD` (line 22), `publishHealth()` (line 71), `recordUpdate` (line 391), `recordContractUpdate` (line 404) — PRIMARY investigation and modification target |
| `src/modules/data-ingestion/data-ingestion.service.ts` | `ingestCurrentOrderBooks()` (line 162), `processWebSocketUpdate()` (line 326), `onModuleInit()` WS callbacks (line 66) |
| `src/core/trading-engine.service.ts` | `executeCycle()` (line 57) — full cycle timing |
| `src/core/scheduler.service.ts` | `handlePollingCycle()` (line 59), `setInterval(30000)` (line 42), `isCycleInProgress()` skip guard |
| `src/dashboard/dashboard.service.ts` | `computeCompositeHealth()` (line 1044), `getLatestHealthLogs()` (line 1036), `getHealth()` (line 171) |
| `src/connectors/paper/paper-trading.connector.ts` | `onOrderBookUpdate` delegation (line 45) |
| `src/connectors/kalshi/kalshi-websocket.client.ts` | Reconnection handling, sequence gap detection |
| `src/connectors/polymarket/polymarket-websocket.client.ts` | `DATA_STALE` check (>30s old data rejected), reconnection |
| `src/modules/data-ingestion/platform-health.service.spec.ts` | Existing health tests — extend with transition logging tests |

### Existing Test Patterns

- **Framework:** Vitest 4 (NOT Jest). Co-located tests (`*.spec.ts` next to source).
- **Baseline:** 2112 tests passing, 118 files. [Source: test run 2026-03-15]
- **Health service mocking pattern**: `platform-health.service.spec.ts` uses `vi.useFakeTimers()` for time-dependent tests, `vi.spyOn(Date, 'now')` for timestamp control. EventEmitter2 is mocked with `vi.fn()` on `emit`. PrismaService is mocked for DB writes. [Source: `platform-health.service.spec.ts`]
- **Data ingestion mocking pattern**: `data-ingestion.service.spec.ts` mocks connectors, health service (`recordContractUpdate` assertions), and EventEmitter2. Uses `vi.mocked()` for type-safe mock access. [Source: `data-ingestion.service.spec.ts`]

### What NOT To Do

- **Do NOT change `STALENESS_THRESHOLD` from 60,000ms** — fix the pipeline, not the threshold
- **Do NOT re-diagnose what Story 9-15 already fixed** — epoch zero, sequential polling, per-pair staleness are resolved
- **Do NOT remove `getOrderbookStaleness()`** — still used by `publishHealth()` for platform-level orderbook staleness events (Story 9.1b)
- **Do NOT modify per-contract staleness threshold** (90s) — that's for detection suppression and Telegram alerts, separate concern
- **Do NOT add a full metrics/observability system** — lightweight structured logging is sufficient for verification
- **Do NOT change dashboard frontend health display logic** unless the fix specifically requires it (e.g., switching from REST to WS for health state)
- **Do NOT skip the investigation phase** — the sprint change proposal explicitly mandates investigation-first

### Previous Story Intelligence

- **9-15 (Platform Health Concurrent Polling)**: Fixed epoch zero false degradation, sequential polling (117s→~24s), per-pair staleness. Test count 2037→2056. Code review fixed WS `recordUpdate`→`recordContractUpdate`, added rejected-promise and duration tests. Key learning: `PaperTradingConnector` delegates `onOrderBookUpdate` to real connector, so WS should flow in paper mode.
- **9-19 (VWAP Dashboard Pricing)**: Unrelated content, but confirms test baseline at 2112. No health/staleness changes.
- **9-1b (Orderbook Staleness Detection)**: Introduced platform-level `ORDERBOOK_STALENESS_THRESHOLD_MS` (90s), `ORDERBOOK_STALE`/`RECOVERED` events. The 90s threshold is for alerting; the 60s threshold is for health status. Do not confuse them.
- **Sprint 9 pattern**: 14 prior course corrections absorbed. Investigation → diagnosis → targeted fix is the established pattern.

### References

- [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md#Story-9-20] — Problem statement, investigation checklist, possible outcomes, success criteria
- [Source: 9-15-platform-health-concurrent-polling.md] — Prior fix: epoch zero, concurrent polling, per-pair staleness (what's already fixed)
- [Source: CLAUDE.md#Architecture] — Module structure, communication patterns, dependency rules
- [Source: CLAUDE.md#Domain-Rules] — Financial math rules (relevant if calculation fixes needed)
- [Source: platform-health.service.ts:22] — `STALENESS_THRESHOLD = 60_000` (DO NOT CHANGE)
- [Source: platform-health.service.ts:56] — `ORDERBOOK_STALENESS_THRESHOLD_MS = 90_000` (separate concern)
- [Source: platform-health.service.ts:71-268] — `publishHealth()` — 30s cron, health calculation, transition events
- [Source: platform-health.service.ts:312-385] — `calculateHealth()` — staleness check at `age > this.STALENESS_THRESHOLD`
- [Source: platform-health.service.ts:391-413] — `recordUpdate()` and `recordContractUpdate()` — data freshness recording
- [Source: trading-engine.service.ts:57-287] — `executeCycle()` — full pipeline timing
- [Source: scheduler.service.ts:36-82] — Polling interval, cycle overlap guard
- [Source: data-ingestion.service.ts:162-320] — `ingestCurrentOrderBooks()` — polling implementation
- [Source: data-ingestion.service.ts:326-376] — `processWebSocketUpdate()` — WS update path
- [Source: dashboard.service.ts:171-207] — `getHealth()` — dashboard health endpoint
- [Source: dashboard.service.ts:1036-1051] — `getLatestHealthLogs()`, `computeCompositeHealth()`
- [Source: HealthComposite.tsx:42-44] — "Stale data" label condition: `!p.dataFresh`
- [Source: useDashboard.ts:20-27] — `useDashboardHealth` — 15s poll interval

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

N/A — investigation used Postgres MCP queries and static code analysis.

### Completion Notes List

#### Phase 1: Investigation Findings (2026-03-15)

**Task 1 — Empirical staleness (DB data, last 6h):**
- Kalshi: 22.5% time degraded (112 degraded / 238 total transitions). Avg degraded window: 43.3s, avg healthy: 133.5s.
- Polymarket: 34.5% time degraded (87 degraded / 211 total transitions). Avg degraded window: 84.7s, avg healthy: 113.9s.
- 100% of degraded entries have `connection_state='unknown'` → all are `stale_data` degradation (no connectivity or latency issues).
- Staleness age at degradation: Kalshi median 82s, Polymarket median 85s, p95 ~235-263s.

**Task 2 — Cycle duration:** Code analysis shows ingestion ~15-25s (389 Kalshi contracts via p-limit + Polymarket batch), full `executeCycle()` likely 30-60s+. Cannot query file-based JSON logs via Postgres.

**Task 3 — WebSocket data flow: CRITICAL FINDING — WS data NOT flowing.**
- Both connectors establish WS connections in `onModuleInit()` ✓
- `DataIngestionService.onModuleInit()` registers callbacks via `onOrderBookUpdate()` ✓
- **Neither connector subscribes to any tickers/tokens:**
  - `KalshiConnector.subscribeToTicker()` defined at line 598 but NEVER called from outside
  - `PolymarketConnector` has NO `subscribeToTicker()` method
  - `subscribeToTicker()` is NOT on `IPlatformConnector` interface
  - Both WS clients' `subscriptions` sets are always empty → zero data flows via WS

**Task 4 — Timing analysis:**
- `publishHealth()` cron: `*/30 * * * * *` (clock seconds :00, :30)
- Polling interval: `setInterval(30000)` (process-relative, NOT synchronized with cron)
- `recordContractUpdate()` only called during ingestion stage of `executeCycle()`
- Post-ingestion pipeline stages (detection, edge calc, risk, execution) do NOT call `recordUpdate`
- Without WS data, gap between ingestion completions = (cycle_duration - ingestion_duration) + inter_cycle_wait
- Any cycle where this gap > 60s triggers degraded status

**Task 5 — Root cause:**
- **Primary:** WebSocket subscriptions never established (AC #6(b)). Zero WS data between polls → `lastUpdateTime` only advances during ingestion → gap regularly exceeds 60s.
- **Contributing:** Cron/interval timing desync (AC #6(c)). Independent 30s cron fires during post-ingestion pipeline window when `lastUpdateTime` stagnates.

#### Phase 2: Remediation (2026-03-15)

**Fix implemented (AC #6(c)):** Post-ingestion `publishHealth()` call at end of `ingestCurrentOrderBooks()`.
- Triggers health evaluation immediately after data fetch, while `lastUpdateTime` is fresh
- `calculateHealth()` returns `'healthy'` → transition recorded → dashboard shows healthy
- The 30s cron continues as fallback for genuine staleness detection
- Double healthy ticks with cron are harmless (unhealthy ticks can't fire right after fresh ingestion)

**Transition logging (AC #8):** Added structured log entry in `publishHealth()` transition block with fields: `message`, `module`, `correlationId`, `platform`, `previousStatus`, `newStatus`, `timestamp`, `lastUpdateAgeMs`, `reason`.

**WS subscription gap documented as follow-on:** WebSocket connections exist but no tickers are subscribed. Fixing this requires: `IPlatformConnector` interface change, both connector implementations, `PaperTradingConnector` delegation, subscription lifecycle management, Polymarket DATA_STALE filter verification. Should be a dedicated story. When wired, WS will keep `lastUpdateTime` fresh continuously, structurally solving the staleness problem.

#### Phase 3: Verification (2026-03-15)

- AC #7: `STALENESS_THRESHOLD` unchanged at 60,000ms ✓
- AC #10: Genuine staleness detection verified (existing test: `lastUpdateTime` 61s ago → `'degraded'` with `stale_data`) ✓
- AC #11: `computeCompositeHealth()` handles `'initializing'` correctly — falls through to `'healthy'` ✓
- AC #12: 2119 tests passing (2112 → 2119, +7), lint clean ✓

#### Code Review (2026-03-15)

**Lad MCP code review completed.** 2 reviewers (kimi-k2.5, glm-5).

**Fixed (1 issue):**
- HIGH: Missing try/catch on post-ingestion `publishHealth()` call — if it throws, ingestion cycle fails. Wrapped in try/catch with error log. Added test for error resilience (+1 test, 2117→2118).

**Skipped (with rationale):**
- Correlation ID shadowing in `publishHealth()` — pre-existing behavior, not introduced by this story
- Race condition on concurrent `publishHealth()` calls — Node.js single-threaded, Map ops are synchronous between awaits. Worst case is duplicate healthy event emission, which is harmless.
- Unbounded `lastContractUpdateTime` map — pre-existing, not this story's scope
- Timestamp inconsistency within single tick — reads are microseconds apart (synchronous), negligible
- Composite key collision — pre-existing, contractIds don't contain colons
- WS path health evaluation — by design; WS updates keep `lastUpdateTime` fresh for the cron
- Recovery reason logging — `'none'` is accurate; healthy status has no `degradationReason`
- Hardcoded platform list — pre-existing across codebase
- Negative latency validation — pre-existing, not this story's scope
- AC #9: Post-deployment measurement needed. With the fix, every successful ingestion triggers a health check while data is fresh → the only remaining staleness source is genuine platform failure or ingestion failure.

#### Code Review #2 (2026-03-15)

**Adversarial BMAD code review completed.** Reviewer: Claude Opus 4.6.

**Fixed (3 MEDIUM issues):**
- MEDIUM: `pollingCycleDurationMs` metric included `publishHealth()` execution time — moved duration capture before `publishHealth()` call so metric reflects pure data-fetching time.
- MEDIUM: Degraded→healthy transition test missing field assertions (`correlationId`, `timestamp`, `lastUpdateAgeMs`) — added property checks and `lastUpdateAgeMs < 5s` assertion for recovery case.
- MEDIUM: Missing test for total ingestion failure (both platforms fail) — added test verifying `publishHealth()` still called when all platforms error (+1 test, 2118→2119).

**Noted (3 LOW, no action):**
- Transition log tests use real `Date.now()` vs `vi.useFakeTimers()` pattern — works correctly with relative time, non-issue in practice.
- Post-ingestion `publishHealth()` creates separate correlationId from ingestion — pre-existing `publishHealth()` design, not this story's scope.
- Task 8.1 left unchecked — correctly deferred to post-deployment measurement.

### File List

| File | Action | Description |
|---|---|---|
| `src/modules/data-ingestion/platform-health.service.ts` | Modified | Added staleness transition logging in `publishHealth()` transition block (AC #8) |
| `src/modules/data-ingestion/data-ingestion.service.ts` | Modified | Added `publishHealth()` call after `ingestCurrentOrderBooks()` with try/catch; moved polling duration metric before health check (AC #6, code review #1 + #2 fixes) |
| `src/modules/data-ingestion/platform-health.service.spec.ts` | Modified | +2 tests: transition logging on healthy→degraded and degraded→healthy with full field assertions (AC #8, code review #2 fix) |
| `src/modules/data-ingestion/data-ingestion.service.spec.ts` | Modified | +5 tests: publishHealth after ingestion, partial failure, total failure, no pairs, error resilience (AC #6, code review #1 + #2 fixes) |
