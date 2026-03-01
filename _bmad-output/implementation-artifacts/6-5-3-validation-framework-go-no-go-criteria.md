# Story 6.5.3: Validation Framework & Go/No-Go Criteria

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want a defined measurement framework with explicit success thresholds before starting live observation,
so that validation phases produce structured, evaluable data rather than anecdotal impressions.

## Acceptance Criteria

1. **Given** Phase 1 (read-only detection) needs quantitative evaluation
   **When** the metrics collection template for Phase 1 is designed
   **Then** the template captures per-cycle: detection timestamp, opportunities found, edge values, detection latency (ms), platform health status, order book depth at detection time
   **And** the template captures daily aggregates: total cycles, total opportunities, edge distribution (min/median/max/mean), latency percentiles (p50/p95/p99), platform uptime percentage
   **And** the collection mechanism is defined (structured log parsing, database queries, or dedicated metrics endpoint)

2. **Given** Phase 2 (paper execution) adds execution and monitoring dimensions
   **When** the metrics collection template for Phase 2 is designed
   **Then** the template extends Phase 1 metrics with: paper orders submitted, fill simulation results, position lifecycle events (open → monitor → exit), exit trigger types, single-leg detections, risk budget consumption
   **And** monitoring validation metrics are included: Telegram alerts sent (by severity), CSV log entries written, daily summary generation, audit trail hash chain length
   **And** resilience metrics are included: memory usage trend, connection recovery events, graceful shutdown/restart count, reconciliation results

3. **Given** validation requires daily human observation alongside automated metrics
   **When** the observation log format is established
   **Then** the format includes: date, observer, key observations (narrative), anomalies noted, decisions made, environment changes, and open questions
   **And** the format is lightweight enough to fill in 10 minutes per day (not a bureaucratic exercise)

4. **Given** the PRD defines quantitative success targets
   **When** go/no-go criteria are formalized for Phase 1 → Phase 2 gate
   **Then** criteria include:
   - Opportunity detection frequency: ≥8 per week (PRD target) — or documented explanation if lower with threshold adjustment proposal
   - Detection cycle time: <1s per cycle (NFR-P2)
   - Zero unhandled crashes during 48h run
   - Both platform connections maintained >95% uptime
   **And** each criterion has a clear pass/fail definition (no subjective judgment)
   **And** a "conditional proceed" path is defined for criteria that partially fail (e.g., 5 opportunities instead of 8 — investigate thresholds, don't auto-abort)

5. **Given** the PRD defines end-of-validation success gates
   **When** go/no-go criteria are formalized for Phase 2 → Epic 7 gate
   **Then** criteria include:
   - Zero unhandled crashes during 5-day run
   - Telegram alerts verified functional (at least one of each severity level observed or manually triggered)
   - CSV logs and daily summaries populated correctly with no missing fields beyond documented N/A gaps
   - Audit trail hash chain verified intact via `verifyChain()`
   - Reconciliation successful after at least one intentional restart
   - Single-leg exposure events: <3 requiring manual intervention (PRD success gate)
   **And** each criterion has a clear pass/fail definition

6. **Given** the validation framework needs stakeholder sign-off before the clock starts
   **When** all templates and criteria are complete
   **Then** the complete validation framework (metrics templates, observation log format, go/no-go criteria for both gates) is reviewed and approved by Arbi
   **And** approval is recorded with date

## Tasks / Subtasks

- [x] Task 1: Create Phase 1 Metrics Collection Template (AC: #1)
  - [x] 1.1 Create `pm-arbitrage-engine/docs/validation/phase1-metrics-template.md` with the per-cycle metrics table
  - [x] 1.2 Define per-cycle metrics columns: `timestamp`, `cycle_number`, `opportunities_found`, `edge_values` (comma-separated list of detected edges), `max_edge`, `detection_latency_ms`, `kalshi_health` (healthy/degraded/disconnected), `polymarket_health`, `kalshi_book_depth` (total bid+ask levels across configured pairs), `polymarket_book_depth`
  - [x] 1.3 Define daily aggregate metrics section: `date`, `total_cycles`, `total_opportunities`, `edge_min`, `edge_median`, `edge_max`, `edge_mean`, `latency_p50_ms`, `latency_p95_ms`, `latency_p99_ms`, `kalshi_uptime_pct`, `polymarket_uptime_pct`, `unhandled_errors_count`, `degradation_events_count`
  - [x] 1.4 Document collection mechanism for each metric:
    - **Detection latency**: Already logged per-cycle by `DetectionService.detectDislocations()` — extract from structured JSON logs via `jq` filter: `jq 'select(.msg == "Detection cycle complete") | .data.durationMs'` (Pino uses `msg` field in production JSON output, not `message`)
    - **Opportunities found**: Already emitted as `detection.opportunity.identified` events — count via `EventConsumerService.getMetrics().eventCounts['detection.opportunity.identified']`, OR query `pm2 logs` with `jq` for events matching this pattern
    - **Edge values**: Logged in `detection.opportunity.identified` event payload — extract `edge` field from structured logs
    - **Platform health**: Query `platform_health_logs` table via Prisma Studio or direct SQL: `SELECT * FROM platform_health_logs WHERE created_at >= NOW() - INTERVAL '1 day' ORDER BY created_at`
    - **Order book depth**: Logged per-ingestion in `DataIngestionService` — extract `bidLevels` and `askLevels` from structured logs
    - **Daily aggregates**: Computed from per-cycle data using shell scripts (provided in template) or manual SQL queries
  - [x] 1.5 Include sample `jq` one-liners and SQL queries for each collection method. **CRITICAL**: In production JSON output, Pino uses `msg` as the log message field (not `message`). All `jq` filters must use `.msg` for message matching. The `data` sub-object retains its field names as-is (e.g., `.data.durationMs`, `.data.dislocationsFound`).

- [x] Task 2: Create Phase 2 Metrics Collection Template (AC: #2)
  - [x] 2.1 Create `pm-arbitrage-engine/docs/validation/phase2-metrics-template.md` extending Phase 1
  - [x] 2.2 Define execution metrics: `paper_orders_submitted`, `paper_orders_filled`, `fill_latency_ms`, `positions_opened`, `positions_exited`, `exit_trigger_types` (take_profit/stop_loss/time_based counts), `single_leg_detections`, `single_leg_resolutions`
  - [x] 2.3 Define risk metrics: `budget_reservations`, `budget_commits`, `budget_releases`, `risk_limit_approaches`, `risk_limit_breaches`, `risk_budget_utilization_pct` (note: `daily_loss_pct` is not meaningful in paper mode — track risk limit enforcement logic instead)
  - [x] 2.4 Define monitoring validation metrics:
    - **Telegram alerts**: Count by severity — query `EventConsumerService.getMetrics().severityCounts` for {critical, warning, info} breakdown. Severity classification is implemented for 36 domain events across 3 levels in `EventConsumerService.classifyEventSeverity()` — see Task 6.2 for exact breakdown
    - **CSV trade log entries**: Count rows in daily CSV file via `wc -l /path/to/trades-YYYY-MM-DD.csv`. Known gap: 5 columns show N/A due to event payload gaps from Story 6.3 (doc these as known, not failures)
    - **Daily summary generation**: Verify `DailySummaryService.handleDailySummary()` fired via log check or Telegram message receipt
    - **Audit trail integrity**: Run `AuditLogService.verifyChain()` — returns `ChainVerificationResult` with `valid` boolean, `entriesChecked` count
  - [x] 2.5 Define resilience metrics:
    - **Memory usage**: `pm2 monit` or `pm2 show pm-arbitrage-engine | grep memory` — capture hourly snapshots via cron
    - **Connection recovery events**: Count `degradation.protocol.activated` / `degradation.protocol.deactivated` event pairs in logs
    - **Graceful shutdown/restart**: Count pm2 restart events: `pm2 logs | grep "PM2 Process restarted"` + count reconciliation events
    - **Reconciliation**: Query `system.reconciliation.complete` events — check `discrepanciesFound` count in payload

- [x] Task 3: Create Observation Log Format (AC: #3)
  - [x] 3.1 Create `pm-arbitrage-engine/docs/validation/observation-log-template.md`
  - [x] 3.2 Define daily entry format (lightweight, 10-minute fill time):
    ```markdown
    ## Day N — YYYY-MM-DD
    **Observer:** Arbi
    **Time spent reviewing:** X min

    ### System Status
    - Engine uptime: Xh Xm (since last restart)
    - Platform connections: Kalshi [OK/ISSUE], Polymarket [OK/ISSUE]
    - pm2 restarts today: N

    ### Key Observations
    - [Narrative: what happened today, notable patterns, anything unexpected]

    ### Anomalies
    - [List any anomalies, errors, or unexpected behavior — or "None"]

    ### Decisions Made
    - [Any configuration changes, pair adjustments, or manual interventions — or "None"]

    ### Environment Changes
    - [Software updates, VPS changes, pair additions/removals — or "None"]

    ### Open Questions
    - [Questions to investigate tomorrow — or "None"]

    ### Quick Metrics Snapshot
    | Metric | Value |
    |--------|-------|
    | Opportunities detected | |
    | Best edge seen | |
    | Avg detection latency | |
    | Telegram alerts fired | |
    | Unhandled errors | |
    ```
  - [x] 3.3 Include instructions: "Copy this template for each day. Fill in during morning review. Takes <10 minutes."

- [x] Task 4: Define Phase 1 → Phase 2 Go/No-Go Criteria (AC: #4)
  - [x] 4.1 Create `pm-arbitrage-engine/docs/validation/go-no-go-criteria.md`
  - [x] 4.2 Define Phase 1 → Phase 2 gate criteria with pass/fail definitions:

    | # | Criterion | Pass | Fail | Conditional Proceed |
    |---|-----------|------|------|---------------------|
    | P1-1 | Opportunity detection frequency | ≥2 opportunities detected over 48h (validates ≥8/week PRD pace) | 0 opportunities in 48h (detection fundamentally broken) | 1 opportunity: investigate edge thresholds, market activity, pair coverage. Document findings. If root cause is market conditions (not code), adjust thresholds and proceed. Note: 48h is a limited sample — low count may reflect market inactivity, not system failure. |
    | P1-2 | Detection latency | p95 < 1s (per NFR-P2: detection cycle < 1 second) | p95 > 5s (unusable for execution) | 1s < p95 < 5s: document bottleneck, assess whether it impacts Phase 2 execution timing. Proceed if execution latency budget is not consumed. |
    | P1-3 | System stability | Zero unhandled crashes/exceptions in 48h | >3 unhandled crashes OR any crash requiring manual data repair | 1-3 crashes: root cause each, determine if intermittent (network) or systematic (code bug). Fix and extend Phase 1 by 24h for re-validation. |
    | P1-4 | Platform connectivity | Both platforms >95% uptime over 48h | Either platform <80% uptime | 80-95% uptime: investigate root cause (rate limits? API changes? VPS network?). If external to our system and recoverable, proceed with documented risk. |
    | P1-5 | Data integrity | <0.1% of order book snapshots have integrity issues (NaN/null in financial fields) — allows for rare transient API errors | >5% of snapshots have data integrity issues | 0.1-5%: investigate pattern, determine if platform-side or our normalization. Fix if ours, document if theirs. |
    | P1-6 | Contract matching accuracy | Zero contract matching errors across all detected opportunities (PRD absolute threshold) | Any systematic mismatch between configured pairs and platform contracts | N/A — contract matching accuracy is binary pass/fail per PRD. Any error halts trading. |

  - [x] 4.3 Include "how to evaluate" section with specific commands/queries for each criterion

- [x] Task 5: Define Phase 2 → Epic 7 Go/No-Go Criteria (AC: #5)
  - [x] 5.1 Add Phase 2 → Epic 7 gate criteria to `go-no-go-criteria.md`:

    | # | Criterion | Pass | Fail | Conditional Proceed |
    |---|-----------|------|------|---------------------|
    | P2-1 | System stability | Zero unhandled crashes in 5-day run | >3 crashes OR any data corruption | 1-3 crashes: same protocol as P1-3, extend Phase 2 by 48h after fixes |
    | P2-2 | Telegram alerts functional | At least one alert of each severity level (critical, warning, info) observed or manually triggered during 5 days | Telegram integration completely non-functional (zero alerts sent) | Some severity levels never triggered: manually trigger remaining levels via test scenarios (e.g., kill platform connection for critical alert). Document results. |
    | P2-3 | CSV trade logging | Daily CSV files populated with correct columns. Missing fields limited to 5 documented N/A columns from Story 6.3 | CSV files empty, missing, or with >5 additional broken columns | Minor formatting issues: fix and document. N/A columns from Story 6.3 are known gaps, NOT failures. |
    | P2-4 | Daily summaries | `DailySummaryService` produces summary for each day of Phase 2 | Zero summaries generated | Partial summaries: investigate cron timing, fix and extend. |
    | P2-5 | Audit trail integrity | `verifyChain()` returns `valid: true` at end of Phase 2 | `valid: false` — hash chain broken | N/A — chain integrity is binary pass/fail. If broken, investigate `brokenAtId` and `brokenAtTimestamp` in `ChainVerificationResult`. |
    | P2-6 | Reconciliation | At least one intentional restart with successful reconciliation (zero unresolved discrepancies) | Reconciliation fails OR leaves unresolved discrepancies after restart | Minor discrepancies resolved by reconciliation engine: pass (that's its job). Only fail if discrepancies remain unresolved. |
    | P2-7 | Single-leg exposure | <3 events requiring manual operator intervention over 5 days (PRD success gate). **Definition of "manual intervention"**: events where the single-leg resolution service cannot auto-resolve and the operator must manually retry or close via API. Auto-resolved single-leg events do NOT count toward this threshold. | ≥5 events requiring manual intervention | 3-4 events: evaluate root cause distribution. If all from same pair/platform, may be pair-specific — remove pair and document. If systemic, fail. |
    | P2-8 | Paper execution coverage | At least 3 complete position lifecycles (open → monitor → exit) observed | Zero complete lifecycles | 1-2 lifecycles: extend Phase 2 by 48h. If still insufficient, evaluate whether market conditions or system config are limiting factor. |

  - [x] 5.2 Include evaluation procedure with specific commands for each criterion

- [x] Task 6: Document Collection Infrastructure Reference (AC: #1, #2)
  - [x] 6.1 Add appendix to metrics templates: "Existing System Infrastructure" that maps each metric to its data source:
    - **Structured logs**: pm2 logs → `jq` filters (all per-cycle metrics)
    - **Database queries**: Prisma Studio or `psql` via SSH tunnel (health logs, order/position tables)
    - **EventConsumerService.getMetrics()**: In-memory counters for event totals and severity breakdown (accessible via future dashboard or log dump at end of phase)
    - **AuditLogService.verifyChain()**: Programmatic call or future REST endpoint
    - **CSV files**: Direct file inspection on VPS (path: configurable via `TRADE_LOG_DIR` env var)
    - **pm2 monit**: Real-time process metrics (CPU, memory, restarts)
  - [x] 6.2 Document the 36 domain events in `EventConsumerService` with their actual severity levels (reference for "at least one of each severity" criterion):
    - **Critical** (6 events): `CRITICAL_EVENTS` constant — `execution.single_leg.exposure`, `risk.limit.breached`, `system.trading.halted`, `system.health.critical`, `system.reconciliation.discrepancy`, `time.drift.halt`
    - **Warning** (6 events): `WARNING_EVENTS` constant — `execution.order.failed`, `risk.limit.approached`, `platform.health.degraded`, `time.drift.critical`, `time.drift.warning`, `degradation.protocol.activated`
    - **Telegram-eligible Info** (6 events): `TELEGRAM_ELIGIBLE_INFO_EVENTS` constant — `execution.order.filled`, `execution.exit.triggered`, `execution.single_leg.resolved`, `detection.opportunity.identified`, `platform.health.recovered`, `system.trading.resumed`
    - **Info** (remaining 18 events): All other events default to info severity (includes `platform.health.disconnected`, `execution.depth-check.failed`, `execution.compliance.blocked`, `monitoring.audit.chain_broken`, `monitoring.audit.write_failed`, etc.)
    - **NOTE**: `monitoring.audit.chain_broken` and `platform.health.disconnected` default to Info in current code — consider whether these should be escalated to Critical/Warning respectively. Document as-is for validation, flag as potential improvement for post-validation.

- [x] Task 7: Operator review and approval (AC: #6)
  - [x] 7.1 Arbi reviews complete validation framework
  - [x] 7.2 Approval recorded with date at top of `go-no-go-criteria.md`
  - [x] 7.3 Any feedback incorporated before Phase 1 begins

## Dev Notes

### Nature of This Story

**This is a DOCUMENTATION-ONLY story.** No code changes. No tests. No lint required. The deliverables are three markdown documents:

1. `pm-arbitrage-engine/docs/validation/phase1-metrics-template.md` — Phase 1 metrics collection template
2. `pm-arbitrage-engine/docs/validation/phase2-metrics-template.md` — Phase 2 metrics collection template (extends Phase 1)
3. `pm-arbitrage-engine/docs/validation/observation-log-template.md` — Daily observation log format
4. `pm-arbitrage-engine/docs/validation/go-no-go-criteria.md` — Pass/fail criteria for both gates

**Tasks 1-6** can be done by the dev agent (creating docs). **Task 7** is an operator approval step — must be handed back to Arbi.

### Architecture Compliance

No architecture constraints apply — this story creates documentation, not code. However, the metrics and collection methods must accurately reference the existing system:

- **Event catalog**: 36 domain events defined in `src/common/events/event-catalog.ts` with `EVENT_NAMES` constant
- **Severity classification**: `EventConsumerService.classifyEventSeverity()` classifies events into Critical/Warning/Info using `CRITICAL_EVENTS`, `WARNING_EVENTS`, and `TELEGRAM_ELIGIBLE_INFO_EVENTS` constants
- **Metrics endpoint**: `EventConsumerService.getMetrics()` returns `EventConsumerMetrics` with `totalEventsProcessed`, `eventCounts` (per-event), `severityCounts`, `errorsCount`, `lastEventTimestamp`
- **Daily summary**: `DailySummaryService.buildSummary()` produces `DailySummaryData` with: `totalTrades`, `totalPnl`, `opportunitiesDetected`, `opportunitiesExecuted`, `openPositions`, `closedPositions`, `singleLegEvents`, `riskLimitEvents`, `systemHealthSummary`
- **Audit trail**: `AuditLogService.verifyChain()` returns `ChainVerificationResult` with `valid`, `entriesChecked`, `brokenAtId`, `brokenAtTimestamp`, `expectedHash`, `actualHash`
- **Reconciliation**: `StartupReconciliationService.reconcile()` checks pending orders and active positions against platform state; emits `system.reconciliation.complete` event
- **CSV trade log**: `CsvTradeLogService` writes per-trade rows; 5 columns documented as N/A from Story 6.3 event payload gaps
- **Detection**: `DetectionService.detectDislocations()` logs cycle duration — use for latency metrics
- **Platform health**: `PlatformHealthService` tracks per-platform status (healthy/degraded/disconnected); transition-only DB persistence (Story 6.5.2a)

### PRD-Sourced Thresholds

From `prd.md` lines 332-345 (MVP Success Gate):
- **50+ completed arbitrage cycles** — not directly applicable to paper trading, but the opportunity detection frequency (≥8/week) derives from this
- **Profit factor >1.2** — cannot evaluate in paper mode (no real fills), deferred to live trading
- **Zero contract matching errors** — absolute threshold, applies in paper mode
- **<3 single-leg events requiring manual intervention** — applicable in Phase 2

From `prd.md` NFR section:
- **NFR-P1**: Order book normalization within 500ms of platform event
- **NFR-P2**: Detection cycle < 1 second
- **NFR-P3**: Execution submission < 100ms between legs — applicable to Phase 2
- **NFR-P4**: Dashboard < 2s — not applicable (dashboard not built yet, Epic 7)

### CSV Trade Log Known Gaps

Story 6.3 documented 5 N/A columns in CSV trade log due to event payload gaps. These are **known gaps**, NOT validation failures. The go/no-go criteria must explicitly call this out to avoid false negatives.

### Existing Monitoring Infrastructure for Data Collection

| Data Source | What It Provides | Access Method |
|-------------|-----------------|---------------|
| Structured JSON logs (pm2) | Per-cycle detection latency, opportunities, edges, platform status | `pm2 logs --json \| jq '...'` |
| `platform_health_logs` table | Platform health transitions with timestamps | SQL via Prisma Studio / psql |
| `orders` table | Paper orders submitted, fill statuses | SQL query |
| `open_positions` table | Position lifecycle, exit triggers | SQL query |
| `EventConsumerService.getMetrics()` | In-memory event counters, severity breakdown | Log dump or future API endpoint |
| `AuditLogService.verifyChain()` | Hash chain integrity verification | Programmatic call |
| CSV trade log files | Per-trade records with timestamps | `wc -l`, `cat`, `head` on VPS |
| `DailySummaryService` | Daily P&L, trade counts, system health | Telegram message + structured log |
| pm2 process metrics | Memory usage, CPU, restart count | `pm2 monit`, `pm2 show` |
| `StartupReconciliationService` | Post-restart consistency check | `system.reconciliation.complete` event |

### Previous Story Intelligence (Story 6.5.2a)

**Metrics after 6.5.2a:**
- Tests passing: 1,101 (70 test files)
- Lint errors: 0
- Build: Clean

**Key changes from 6.5.2a:**
- Polymarket batch order book fetching — single API call per cycle instead of sequential
- Health log persistence now transition-only (no more 5,760 writes/day)
- Ingestion latency ~150ms (was ~960ms) — significantly below NFR-P1 threshold
- Rate limit consumption: 1 token/cycle (was 8) — headroom for 500 tokens/request

**Flaky test note:** `logging.e2e-spec.ts:86` is pre-existing timing-dependent flaky test. Not related to this story.

### Git Intelligence

Recent engine commits:
```
c470f15 feat: implement batch fetching of order books for Polymarket
88c6aad feat: add production environment configuration, PostgreSQL backup and restore scripts
c2fa2a9 feat: update Kalshi API integration with new base URL, enhance orderbook structure
48caebd feat: update Polymarket WebSocket handling to support nested price_change messages
6d0c1d5 feat: enhance codebase with TypeScript linting rules, add new dependencies
```

### Web Research Required

**None.** This is a documentation story referencing existing system infrastructure. All thresholds come from the PRD and architecture documents. No external libraries or APIs to verify.

### Project Structure Notes

Files to create (all new, documentation only):
- `pm-arbitrage-engine/docs/validation/phase1-metrics-template.md`
- `pm-arbitrage-engine/docs/validation/phase2-metrics-template.md`
- `pm-arbitrage-engine/docs/validation/observation-log-template.md`
- `pm-arbitrage-engine/docs/validation/go-no-go-criteria.md`

Parent directory `pm-arbitrage-engine/docs/validation/` does not exist yet — create it.

No existing files modified. No schema changes. No dependency changes. No env var changes.

### Testing Requirements

**None.** This story produces documentation only. No code to test. No lint to run.

Post-edit workflow for this story: just verify the docs are well-structured and all criteria reference real system capabilities.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.5.3, lines 1589-1648] — Epic definition, ACs, sequencing, previous story intelligence
- [Source: _bmad-output/planning-artifacts/prd.md#MVP-Success-Gate, lines 332-345] — Quantitative success targets
- [Source: _bmad-output/planning-artifacts/prd.md#NFR-P1-through-P4, lines 1629-1648] — Performance NFRs
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts, lines 13-141] — Complete event catalog (36 events)
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts] — `EventConsumerService` with severity classification, metrics, event routing
- [Source: pm-arbitrage-engine/src/modules/monitoring/daily-summary.service.ts] — `DailySummaryService` with `DailySummaryData` interface
- [Source: pm-arbitrage-engine/src/modules/monitoring/audit-log.service.ts] — `AuditLogService.verifyChain()` with `ChainVerificationResult`
- [Source: pm-arbitrage-engine/src/modules/monitoring/csv-trade-log.service.ts] — CSV trade logging with 5 known N/A columns
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.ts] — `DetectionService.detectDislocations()` with cycle duration logging
- [Source: pm-arbitrage-engine/src/reconciliation/startup-reconciliation.service.ts] — Startup reconciliation with discrepancy handling
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts] — Platform health with transition-only DB persistence
- [Source: _bmad-output/implementation-artifacts/6-5-2a-polymarket-batch-orderbook-migration.md] — Previous story context and metrics

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — documentation-only story, no code changes or test runs.

### Completion Notes List

- Tasks 1-6 complete. Task 7 (operator approval) requires Arbi review.
- All 36 domain events verified against `event-catalog.ts` and `EventConsumerService` severity classification constants.
- Lad MCP design review and code review incorporated: added event-to-metric mapping tables, cross-references between docs, "How to Use" sections, and fixed duplicate `time.drift.warning` in Appendix B.
- Severity escalation candidates documented (post-validation improvement): `monitoring.audit.chain_broken` → Critical, `platform.health.disconnected` → Warning.
- No code changes, no tests, no lint required.

### File List

- `pm-arbitrage-engine/docs/validation/phase1-metrics-template.md` (NEW)
- `pm-arbitrage-engine/docs/validation/phase2-metrics-template.md` (NEW)
- `pm-arbitrage-engine/docs/validation/observation-log-template.md` (NEW)
- `pm-arbitrage-engine/docs/validation/go-no-go-criteria.md` (NEW)
