# Story 6.5.5: Paper Execution Validation (5 days)

Status: ready-for-dev

## Story

As an operator,
I want to run the full trading pipeline in paper mode for 5 days against live markets,
so that I can validate the complete position lifecycle, monitoring stack, and system resilience before considering production deployment.

## Acceptance Criteria

1. **Given** Stories 6.5.0–6.5.4 are complete
   **When** paper execution is enabled on the VPS
   **Then** the engine runs the full pipeline: detection → risk validation → paper execution → position monitoring → exit
   **And** both platforms operate in paper mode (confirmed via startup logs showing `PaperTradingConnector` active for each platform)

2. **Given** position lifecycle is the core behavior under validation
   **When** paper trades execute over the 5-day window
   **Then** at least one complete position lifecycle is observed: opportunity detected → risk validated → orders submitted → fills simulated → position opened → exit threshold hit → exit orders submitted → position closed
   **And** if no opportunities reach execution (edge below threshold on all pairs), this is documented with analysis — the detection-to-execution funnel drop-off is itself a finding
   **And** position state transitions are verified against the expected state machine (PENDING → OPEN → MONITORING → CLOSING → CLOSED)

3. **Given** single-leg exposure detection is a critical safety mechanism
   **When** paper execution runs for 5 days
   **Then** any single-leg events are detected within 5 seconds (PRD requirement) and Telegram alerts fire
   **And** single-leg exposure events total <3 requiring manual intervention (PRD success gate)
   **And** if single-leg events occur, the resolution path (operator action or automatic timeout) is documented

4. **Given** risk management must constrain paper execution as it would live execution
   **When** paper trades execute
   **Then** position sizing respects 3% bankroll limit per pair
   **And** daily loss limits are tracked (even for simulated P&L)
   **And** compliance gate validates each opportunity before execution (Story 6.4)
   **And** no `COMPLIANCE_BLOCKED` events on configured pairs (pairs were pre-verified in 6.5.1)

5. **Given** the full monitoring stack must be validated on live infrastructure
   **When** the 5-day window completes
   **Then** Telegram alerts have been received for at least: one execution event, one risk-related event, and one platform health event (or manually triggered if not organically observed)
   **And** CSV trade logs contain entries for all paper trades with correct field population (known N/A gaps from event payload limitations documented, not treated as failures)
   **And** daily summary generation has produced at least 4 daily summaries (one per completed day)
   **And** audit trail hash chain is verified intact via `verifyChain()` at end of validation

6. **Given** the system must demonstrate resilience over sustained operation
   **When** resilience scenarios are tested during the 5-day window
   **Then** at least one intentional graceful shutdown + restart is performed with positions open, and reconciliation correctly recovers state
   **And** memory usage is sampled daily (via `process.memoryUsage()` or pm2 metrics) — no upward trend indicating a leak
   **And** any platform connection drops during the 5 days are recovered automatically with reconnection logged

7. **Given** the 5-day window produces extensive operational data
   **When** each day completes
   **Then** daily observation log entries are recorded per the format from Story 6.5.3
   **And** metrics are collected per the Phase 2 template from Story 6.5.3
   **And** anomalies or unexpected behaviors are documented immediately, not deferred to the report

8. **Given** Phase 2 completion gates the validation report
   **When** the 5-day observation period completes
   **Then** go/no-go criteria from Story 6.5.3 (Phase 2 → Epic 7 gate) are evaluated with pass/fail for each criterion
   **And** all collected metrics, observation logs, and anomaly notes are organized for Story 6.5.6 (report compilation)

## Tasks / Subtasks

### Pre-Flight (Day 0)

**All timestamps and day boundaries are UTC.** "Morning check" means the first SSH session of the UTC day.

- [ ] Task 1: VPS pre-flight verification (AC: #1)
  - [x] 1.1 SSH into VPS. Verify engine is deployed at latest commit from Story 6.5.4 (`git log --oneline -1` should show `45551cd`)
  - [x] 1.2 Verify required CLI tools are available on VPS: `which jq psql docker pm2 node pnpm` — all must resolve. If `jq` missing: `sudo apt install -y jq`. If `psql` missing: `sudo apt install -y postgresql-client`.
  - [x] 1.3 Verify `pm2 status` shows engine process online
  - [x] 1.4 Verify PostgreSQL Docker container is running: `docker ps | grep postgres`
  - [x] 1.5 Verify disk space is sufficient for 5 days of operation: `df -h /` — require at least 10GB free (logs + DB growth + backups)
  - [x] 1.6 Verify `.env.production` has `PLATFORM_MODE_KALSHI=paper` and `PLATFORM_MODE_POLYMARKET=paper`
  - [x] 1.7 Pull latest code if needed: `git pull && pnpm install --frozen-lockfile && pnpm prisma generate && pnpm build && pm2 restart pm-arbitrage-engine`
  - [x] 1.8 Confirm `contract-pairs.yaml` has all 8 verified pairs from Story 6.5.1
  - [x] 1.9 Verify startup logs show `PaperTradingConnector` active for both platforms: `pm2 logs pm-arbitrage-engine --lines 50 | grep -i paper`
  - [x] 1.10 Verify Telegram test alert works: temporarily set `TELEGRAM_TEST_ALERT_CRON=*/2 * * * *`, restart, wait for alert, revert to `0 8 * * *` and restart
  - [x] 1.11 Verify both platform API connections are healthy: check logs for successful order book ingestion from both Kalshi and Polymarket
  - [x] 1.12 Run audit trail baseline verification via NestJS REPL on VPS:
    ```bash
    cd ~/pm-arbitrage-engine && node -e "
      const { NestFactory } = require('@nestjs/core');
      const { AppModule } = require('./dist/app.module');
      NestFactory.createApplicationContext(AppModule).then(async (app) => {
        const svc = app.get('AuditLogService');
        const result = await svc.verifyChain();
        console.log(JSON.stringify(result, null, 2));
        await app.close();
      });
    "
    ```
    Record baseline `entriesChecked` count. If no entries yet, note "chain empty — baseline established".
  - [x] 1.13 Record baseline metrics: test count (1,139 from 6.5.4), memory baseline from `pm2 show pm-arbitrage-engine | grep memory`
  - [x] 1.14 Verify pm2-logrotate is installed and configured: `pm2 show pm2-logrotate` — should show `max_size: 100M`, `retain: 7`. If missing: `pm2 install pm2-logrotate && pm2 set pm2-logrotate:max_size 100M && pm2 set pm2-logrotate:retain 7`
  - [ ] 1.15 Prepare observation log file: `pm-arbitrage-engine/docs/validation/observation-log.md` using template from 6.5.3

### Phase 2: Paper Execution (Days 1-5)

- [ ] Task 2: Day 1 — Initial observation and stability (AC: #1, #2, #4, #7)
  - [ ] 2.1 Morning check: `pm2 status`, `pm2 logs --lines 100`, verify no overnight crashes. Check disk space: `df -h /`.
  - [ ] 2.2 Check detection cycle logs: `pm2 logs --json | jq 'select(.msg == "Detection cycle complete") | {ts: .time, duration: .data.durationMs, found: .data.dislocationsFound}'` — verify cycles running
  - [ ] 2.3 Check opportunity detection: look for `detection.opportunity.identified` events in logs
  - [ ] 2.4 Verify risk budget state: `psql -h localhost -p 5433 -U postgres -d pmarbitrage -c "SELECT * FROM risk_states"`
  - [ ] 2.5 Record memory usage: `pm2 show pm-arbitrage-engine | grep memory`
  - [ ] 2.6 Check platform health: query `platform_health_logs` for any degradation events — verify hysteresis (Story 6.5.4) prevents flapping
  - [ ] 2.7 Fill in Day 1 observation log entry
  - [ ] 2.8 Collect Phase 2 metrics per template

- [ ] Task 3: Day 2 — Intentional restart and reconciliation test (AC: #6, #7)
  - [ ] 3.1 Morning check: same as Day 1 (2.1–2.5)
  - [ ] 3.2 **Intentional restart test:** Check if any positions are open (`SELECT * FROM open_positions WHERE status = 'OPEN'`). If yes, proceed to 3.3. If no, skip to 3.5.
  - [ ] 3.3 Graceful shutdown: `pm2 stop pm-arbitrage-engine`. Wait 10 seconds. Verify shutdown logs show graceful exit (pending operations completed).
  - [ ] 3.4 Restart: `pm2 start pm-arbitrage-engine`. Verify startup logs show `StartupReconciliationService.reconcile()` running. Check `system.reconciliation.complete` event in logs — verify `discrepanciesFound: 0` (or document any discrepancies).
  - [ ] 3.5 If no positions were open for restart test, note this — will retry on Day 3 or 4 if positions open later
  - [ ] 3.6 Record memory usage, check for upward trend vs Day 1
  - [ ] 3.7 Fill in Day 2 observation log entry
  - [ ] 3.8 Collect Phase 2 metrics per template

- [ ] Task 4: Day 3 — Monitoring stack validation (AC: #5, #7)
  - [ ] 4.1 Morning check: same routine
  - [ ] 4.2 **Telegram alert audit:** Count alerts received so far by severity: critical / warning / info. Target: at least 1 of each by end of Day 5.
  - [ ] 4.3 If any severity level has zero alerts, plan manual trigger scenarios for Day 4:
    - **Critical:** If no single-leg events, will need to document as not organically observed
    - **Warning:** Kill one platform's WebSocket connection via firewall rule (`sudo ufw deny out to <platform_ip>`) for ~90s, then re-allow — should trigger degradation warning
    - **Info:** Should have `execution.order.filled` or `detection.opportunity.identified` if any trades executed
  - [ ] 4.4 **CSV trade log check:** `ls -la ~/pm-arbitrage-engine/data/trade-logs/trades-*.csv` on VPS (or `$CSV_TRADE_LOG_DIR/trades-*.csv` if overridden in `.env.production`). Verify files exist for each day. Spot-check columns — 5 N/A columns (contractId, fees, gas from OrderFilledEvent) are known gaps, not failures.
  - [ ] 4.5 **Daily summary check:** Verify `DailySummaryService` produced summaries: check for Telegram messages with daily summary content, or `pm2 logs --json | jq 'select(.msg | contains("Daily summary"))'`
  - [ ] 4.6 If restart test was skipped on Day 2 (no positions), retry today if positions exist
  - [ ] 4.7 Record memory usage
  - [ ] 4.8 Fill in Day 3 observation log entry
  - [ ] 4.9 Collect Phase 2 metrics per template

- [ ] Task 5: Day 4 — Deep metrics review and gap filling (AC: #2, #3, #5, #7)
  - [ ] 5.1 Morning check: same routine
  - [ ] 5.2 **Position lifecycle analysis:** Document the detection-to-execution funnel using these commands:
    ```bash
    # Opportunities detected
    pm2 logs --json | jq 'select(.msg | contains("opportunity.identified"))' | wc -l
    # Positions by status
    psql -h localhost -p 5433 -U postgres -d pmarbitrage -c "SELECT status, COUNT(*) FROM open_positions GROUP BY status"
    # Orders by status
    psql -h localhost -p 5433 -U postgres -d pmarbitrage -c "SELECT status, COUNT(*) FROM orders GROUP BY status"
    # Risk rejections
    pm2 logs --json | jq 'select(.msg | contains("risk.limit"))' | wc -l
    # Compliance blocks
    pm2 logs --json | jq 'select(.msg | contains("compliance.blocked"))' | wc -l
    ```
    Fill in funnel:
    - Opportunities detected: \_\_\_
    - Passed edge threshold: \_\_\_
    - Passed risk validation: \_\_\_
    - Execution attempted: \_\_\_
    - Fills simulated: \_\_\_
    - Positions opened: \_\_\_
    - Positions exited: \_\_\_
  - [ ] 5.3 If zero complete lifecycles so far, analyze why:
    - Are edges too thin? Check `edge_values` in detection logs
    - Are risk limits too tight? Check `risk.limit.approached` events
    - Are pairs inactive? Check order book depth per pair
    - Document findings — this is itself valuable validation data
  - [ ] 5.4 **Single-leg exposure review:** Check for `execution.single_leg.exposure` events in logs. Count manual-intervention-required events. Target: <3 over full 5 days.
  - [ ] 5.5 **Manually trigger missing Telegram alert severities** if not organically observed (scenarios from Task 4, step 4.3)
  - [ ] 5.6 Record memory usage — compare trend over Days 1-4
  - [ ] 5.7 Fill in Day 4 observation log entry
  - [ ] 5.8 Collect Phase 2 metrics per template

- [ ] Task 6: Day 5 — Final observation and data compilation (AC: #5, #6, #7, #8)
  - [ ] 6.1 Morning check: same routine — FINAL DAY
  - [ ] 6.2 **Memory trend analysis:** Plot/compare daily memory readings. Pass: no consistent upward trend. Document readings.
  - [ ] 6.3 **Audit trail verification:** Run `verifyChain()` using same NestJS REPL method as Task 1.12. Must return `valid: true`. Document `entriesChecked` count and compare against pre-flight baseline.
  - [ ] 6.4 **Connection recovery audit:** Search logs for `degradation.protocol.activated` / `degradation.protocol.deactivated` events. Verify all degradations recovered automatically.
  - [ ] 6.5 **Final CSV trade log check:** `ls -la ~/pm-arbitrage-engine/data/trade-logs/trades-*.csv && wc -l ~/pm-arbitrage-engine/data/trade-logs/trades-*.csv`. Verify daily files for all 5 days. Count total entries.
  - [ ] 6.6 **Final daily summary check:** Verify at least 4 summaries generated (Days 1-4 completed, Day 5 still in progress).
  - [ ] 6.7 **Final Telegram alert tally:** Confirm at least 1 of each severity level received over 5 days.
  - [ ] 6.8 Fill in Day 5 observation log entry
  - [ ] 6.9 Collect final Phase 2 metrics

### Post-Observation

- [ ] Task 7: Go/No-Go evaluation (AC: #8)
  - [ ] 7.1 Evaluate each Phase 2 → Epic 7 gate criterion from `docs/validation/go-no-go-criteria.md`:

    | #    | Criterion                                     | Result | Evidence |
    | ---- | --------------------------------------------- | ------ | -------- |
    | P2-1 | Zero unhandled crashes in 5 days              |        |          |
    | P2-2 | Telegram alerts functional (1+ each severity) |        |          |
    | P2-3 | CSV trade logs populated correctly            |        |          |
    | P2-4 | Daily summaries produced                      |        |          |
    | P2-5 | Audit trail hash chain intact                 |        |          |
    | P2-6 | Reconciliation successful after restart       |        |          |
    | P2-7 | Single-leg events <3 manual intervention      |        |          |
    | P2-8 | ≥3 complete position lifecycles               |        |          |

  - [ ] 7.2 For any criterion rated "conditional proceed" — document root cause and proposed mitigation
  - [ ] 7.3 Compile all daily observation logs, metrics snapshots, and anomaly notes into organized format for Story 6.5.6
  - [ ] 7.4 Write executive summary: 1-paragraph verdict on system readiness

## Dev Notes

### Nature of This Story

**This is an OPERATIONAL EXECUTION story, not a code story.** No code changes. No tests to write. No lint to run.

The deliverables are:

1. A completed 5-day observation period with the engine running on VPS in paper mode
2. Daily observation log entries in `docs/validation/observation-log.md`
3. Metrics collected per Phase 2 template in `docs/validation/phase2-metrics-template.md`
4. Go/No-Go evaluation against criteria defined in `docs/validation/go-no-go-criteria.md`
5. Compiled data package for Story 6.5.6 (Validation Report)

### System Architecture During Validation

**Pipeline flow (all synchronous on hot path):**

```
DataIngestionService (30s polling + WebSocket)
  → DetectionService.detectDislocations()
    → RiskManagementService.validatePosition()
      → ComplianceGateService.validate()
        → ExecutionService.execute() [via PaperTradingConnector]
          → ExitManagementService.monitor()
```

**Paper Trading Connector behavior:**

- Wraps real connectors via decorator pattern
- `getOrderBook()` → calls real platform API (live market data)
- `submitOrder()` → simulates fill locally with configurable latency (`PAPER_FILL_DELAY_MS`) and slippage (`PAPER_SLIPPAGE_BPS`)
- Orders/positions persisted to real DB — identical to live execution
- Events emitted identically to live execution — monitoring stack cannot distinguish paper from live

**Position state machine:**

```
OPEN → SINGLE_LEG_EXPOSED (if secondary leg fails)
SINGLE_LEG_EXPOSED → OPEN (retry success) or CLOSED (close filled leg)
OPEN → MONITORING (exit monitoring active)
MONITORING → CLOSING (exit threshold hit)
CLOSING → CLOSED (exit orders filled)
Any → RECONCILIATION_REQUIRED (startup discrepancy)
```

### Infrastructure Setup (from Story 6.5.2)

- **VPS:** Hetzner CX22 (2 vCPU, 4GB RAM, 40GB SSD), Ubuntu 24.04 LTS
- **Process manager:** pm2 with `ecosystem.config.js` (restart_delay: 5000, max_restarts: 10)
- **Database:** PostgreSQL 16 via Docker (`docker-compose.dev.yml`), port 5433
- **Backup:** Hourly `pg_dump` via cron, 7-day rolling retention
- **Access:** SSH tunnel only (`ssh -L 8080:localhost:8080 user@vps`)
- **Environment:** `.env.production` with `PLATFORM_MODE_KALSHI=paper`, `PLATFORM_MODE_POLYMARKET=paper`

### Contract Pairs (from Story 6.5.1)

8 manually verified cross-platform pairs in `contract-pairs.yaml`, diversified across 5 categories. All pairs pre-verified against compliance matrix (zero blocked-category matches).

### Validation Framework (from Story 6.5.3)

Validation documents in `pm-arbitrage-engine/docs/validation/`:

- **`phase2-metrics-template.md`** — Defines all Phase 2 metrics to collect daily:
  - Execution: paper orders submitted/filled, fill latency, positions opened/exited, exit triggers, single-leg events
  - Risk: budget reservations/commits/releases, limit approaches/breaches, utilization %
  - Monitoring: Telegram alerts by severity, CSV entries, daily summaries, audit chain length
  - Resilience: memory trend, connection recoveries, restarts, reconciliation results
- **`observation-log-template.md`** — Daily log format: system status, observations, anomalies, decisions, environment changes, quick metrics snapshot. Target: <10 min/day.
- **`go-no-go-criteria.md`** — Phase 2 → Epic 7 gate: 8 criteria (P2-1 through P2-8) with explicit pass/fail/conditional-proceed definitions and evaluation commands.

### Data Collection Commands (Key Reference)

```bash
# Detection cycle performance
pm2 logs --json | jq 'select(.msg == "Detection cycle complete") | {ts: .time, durationMs: .data.durationMs, found: .data.dislocationsFound}'

# Opportunities detected
pm2 logs --json | jq 'select(.msg | contains("opportunity.identified"))'

# Platform health transitions
psql -h localhost -p 5433 -U postgres -d pmarbitrage -c "SELECT * FROM platform_health_logs WHERE created_at >= NOW() - INTERVAL '1 day' ORDER BY created_at"

# Open positions
psql -h localhost -p 5433 -U postgres -d pmarbitrage -c "SELECT id, pair_id, status, created_at FROM open_positions ORDER BY created_at DESC"

# Orders
psql -h localhost -p 5433 -U postgres -d pmarbitrage -c "SELECT id, platform, status, fill_price, created_at FROM orders ORDER BY created_at DESC LIMIT 20"

# Risk state
psql -h localhost -p 5433 -U postgres -d pmarbitrage -c "SELECT * FROM risk_states"

# Memory usage
pm2 show pm-arbitrage-engine | grep memory

# CSV trade logs (default path; override via CSV_TRADE_LOG_DIR env var)
ls -la ~/pm-arbitrage-engine/data/trade-logs/trades-*.csv
wc -l ~/pm-arbitrage-engine/data/trade-logs/trades-*.csv

# Audit chain verification (via NestJS REPL)
cd ~/pm-arbitrage-engine && node -e "
  const { NestFactory } = require('@nestjs/core');
  const { AppModule } = require('./dist/app.module');
  NestFactory.createApplicationContext(AppModule).then(async (app) => {
    const svc = app.get('AuditLogService');
    const result = await svc.verifyChain();
    console.log(JSON.stringify(result, null, 2));
    await app.close();
  });
"

# Disk space check
df -h /

# Degradation events
pm2 logs --json | jq 'select(.msg | contains("degradation.protocol"))'

# Single-leg events
pm2 logs --json | jq 'select(.msg | contains("single_leg"))'
```

### Monitoring Stack Components Under Validation

| Component                  | Source Story | What to Validate                                                       |
| -------------------------- | ------------ | ---------------------------------------------------------------------- |
| Telegram alerts            | 6.1          | Delivery for critical/warning/info events                              |
| Event consumer (36 events) | 6.2          | Severity classification, event routing, serialization (fixed in 6.5.4) |
| CSV trade logging          | 6.3          | Daily files, correct columns, 5 N/A gaps documented                    |
| Daily summary service      | 6.3          | Daily Telegram + structured log with P&L, trade counts                 |
| Compliance gate            | 6.4          | Pre-execution validation, zero blocked events on verified pairs        |
| Audit trail                | 6.5          | Hash chain integrity via `verifyChain()`                               |
| WebSocket keepalive        | 6.5.4        | Ping/pong (30s/10s), no 1006 closures from idle timeout                |
| Health hysteresis          | 6.5.4        | 2-tick degradation (no flapping), 2-tick recovery                      |
| Structured log payloads    | 6.5.4        | No `[object]` in any event log — dates as ISO, arrays as arrays        |
| Batch order book fetch     | 6.5.2a       | Single API call per Polymarket cycle, ~150ms latency                   |

### Failure Recovery Procedures

**If engine crashed overnight:**

1. Run `pm2 logs --lines 200` to identify root cause
2. If OOM kill (check `dmesg | grep -i oom`) → note memory at crash, restart and monitor more closely. If repeated, consider VPS RAM upgrade.
3. If DB connection lost → verify PostgreSQL container: `docker ps | grep postgres`. If down: `docker-compose -f docker-compose.dev.yml up -d`. Engine will auto-reconnect via pm2 restart.
4. If transient/network crash → `pm2 restart pm-arbitrage-engine` and continue validation. Document crash in observation log with timestamp and cause.
5. If reproducible crash on same trigger → abort validation, file bug, fix, and restart from Day 0 after fix deployed.

**If VPS rebooted unexpectedly:**

- pm2 auto-starts engine (configured via `pm2 startup`). PostgreSQL Docker container has `restart: unless-stopped`.
- Engine may restart-loop briefly until PostgreSQL is ready — pm2's `restart_delay: 5000` handles this.
- Validation **continues** from where it left off — do NOT restart from Day 0. Document reboot in observation log.
- Verify reconciliation ran on startup: `pm2 logs --json | jq 'select(.msg | contains("reconciliation"))'`

**If disk space runs low (<5GB free):**

1. Check backup accumulation: `du -sh /var/backups/pm-arbitrage/`
2. Check pm2 logs: `du -sh ~/.pm2/logs/`
3. If logs are large, verify pm2-logrotate is working: `pm2 show pm2-logrotate`
4. Emergency: remove oldest backups beyond 3 days: `find /var/backups/pm-arbitrage/ -mtime +3 -delete`

### Known Gaps and Acceptable Limitations

- **CSV N/A columns:** `contractId`, `fees`, `gas` in `OrderFilledEvent` are null — documented in Story 6.3, deferred to Epic 8 enrichment. NOT a validation failure.
- **Paper fill simulation:** Fills are instant (configurable delay) with configurable slippage. Real fill behavior differs — this is expected and acceptable for paper validation.
- **Edge thresholds:** If all edges are below 0.8% net threshold, zero executions may occur. This is a valid outcome — document as market-conditions finding, not system failure.
- **Event severity gaps:** `monitoring.audit.chain_broken` defaults to Info (could be Critical), `platform.health.disconnected` defaults to Info (could be Warning). Documented in 6.5.3, flagged for post-validation improvement.
- **Pre-existing flaky test:** `logging.e2e-spec.ts:86` — timing-dependent, pre-existing. Ignore if it appears.
- **Test baseline:** 1,139 tests (1,133 passing, 2 failing, 4 skipped) — the 2 failures are pre-existing from Story 6.5.4 completion.

### Previous Story Intelligence (Story 6.5.4)

**Completion notes from 6.5.4:**

- Test count: 1,139 tests (70 files), +38 new tests from 6.5.4
- WebSocket keepalive added to both clients (30s ping, 10s pong timeout)
- Hysteresis: 2 unhealthy ticks to degrade, 2 healthy ticks to recover (removed 81s bypass)
- `summarizeEvent()` fixed: recursive `serializeValue()` handles Date→ISO, Decimal→string, arrays, nested objects, circular refs, max depth
- Code review fixes applied (CR-1): reverted maxRetries to Infinity, fixed hash test flake, etc.

**Key files modified in 6.5.4 (now under live validation):**

- `polymarket-websocket.client.ts` — keepalive ping
- `kalshi-websocket.client.ts` — keepalive ping
- `platform-health.service.ts` — consecutive-tick hysteresis
- `event-consumer.service.ts` — recursive serialization

### Git Intelligence

Latest engine commits:

```
45551cd feat: implement WebSocket keepalive mechanism for Kalshi and Polymarket
8804bef feat: add comprehensive validation documentation
c470f15 feat: implement batch fetching of order books for Polymarket
88c6aad feat: add production environment configuration, PostgreSQL backup and restore scripts
c2fa2a9 feat: update Kalshi API integration with new base URL, enhance orderbook structure
```

### Project Structure Notes

- No code changes — this is an operational execution story
- Output files (observation logs, metrics) go in `pm-arbitrage-engine/docs/validation/`
- All work happens on the VPS via SSH — no local development needed
- Engine repo commit should be at `45551cd` or later

### Testing Requirements

**None.** This story validates the system as deployed. No code changes, no new tests, no lint.

Post-edit workflow: N/A — the "post-edit" is the 5-day observation window and go/no-go evaluation.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.5.5, lines 1688-1753] — Epic definition, ACs, sequencing, previous story intelligence
- [Source: _bmad-output/implementation-artifacts/6-5-4-websocket-stability-structured-log-payloads.md] — Previous story (baseline: 1,139 tests, all 4 tasks complete)
- [Source: _bmad-output/implementation-artifacts/6-5-3-validation-framework-go-no-go-criteria.md] — Validation framework with Phase 2 metrics and go/no-go criteria
- [Source: _bmad-output/implementation-artifacts/6-5-2-deployment-runbook-vps-provisioning.md] — VPS setup, pm2 config, backup, SSH tunnel access
- [Source: _bmad-output/implementation-artifacts/6-5-1-event-pair-selection-contract-configuration.md] — 8 verified contract pairs, compliance check
- [Source: pm-arbitrage-engine/docs/validation/phase2-metrics-template.md] — Phase 2 metrics collection template
- [Source: pm-arbitrage-engine/docs/validation/observation-log-template.md] — Daily observation log format
- [Source: pm-arbitrage-engine/docs/validation/go-no-go-criteria.md] — Phase 2 → Epic 7 gate criteria (P2-1 through P2-8)
- [Source: pm-arbitrage-engine/docs/deployment-runbook.md] — Deployment runbook for VPS operations
- [Source: pm-arbitrage-engine/src/connectors/paper/paper-trading.connector.ts] — PaperTradingConnector decorator pattern
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts] — EventConsumerService with 36 events, severity classification
- [Source: pm-arbitrage-engine/src/reconciliation/startup-reconciliation.service.ts] — Startup reconciliation for crash recovery test

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
