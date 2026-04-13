# Sprint Change Proposal: Paper Trading Profitability Fix

**Date:** 2026-04-16
**Triggered by:** 2-day paper trading analysis (Apr 14-15, 2026)
**Current Epic:** 10.96 — Live Trading Engine Alignment & Configuration Calibration
**Scope Classification:** Minor — Direct implementation by dev team
**Mode:** Batch

---

## Section 1: Issue Summary

### Problem Statement

The system ran in paper mode for ~38 hours (Apr 14 09:39 UTC to Apr 15 23:21 UTC), producing 19 positions (16 closed, 3 open). Results were catastrophic: **6.25% win rate, -$346.60 realized PnL, -$452.72 combined PnL**. Only 1 of 16 closed positions was profitable (+$16.14).

### Discovery Context

A deep analytical review of all paper positions, orders, exit criteria, and engine configuration was conducted via direct database queries on 2026-04-16. The analysis revealed the system was entering trades where fees exceeded the modeled edge, creating a systematic fee-donation pattern.

### Root Cause Chain

**PRIMARY — DB config divergence (10-96-4 ineffective):**
Story 10-96-4 ("Configuration Defaults Calibration") updated code defaults in `config-defaults.ts` but the seed script (`prisma/seed-config.ts`) is idempotent — it only populates NULL columns, never overwrites existing values. The `engine_config` DB row retains pre-calibration values:

| Setting | Code Default (10-96-4) | DB Actual | Impact |
|---------|----------------------|-----------|--------|
| `detectionMinEdgeThreshold` | `0.05` (5%) | `0.008` (0.8%) | 69% of entries had sub-5% edge |
| `exitProfitCaptureRatio` | `0.8` | `0.5` | Profit capture threshold too loose |

This single divergence is the **dominant cause** of the paper trading losses. 11 of 16 closed positions entered with expected_edge below 5% — all structurally unprofitable at entry because round-trip spread + fees exceeded the edge.

**SECONDARY — No edge_evaporation re-entry cooldown:**
Story 10-96-3 added a 24h cooldown for TIME_DECAY exits, but EDGE_EVAPORATION exits (62.5% of all exits) only fall through to the generic `pairCooldownMinutes` (60 min). The system re-entered KC/DET 4 times at ~80-90 minute intervals, losing ~$15 each time ($61 total), because the 60-min cooldown had expired between entries.

**TERTIARY — Loose edge evaporation exit when edge is negative:**
Position `0afa4945` (Valorant TH/KC, still OPEN) has a recalculated edge of **-24.9%** with unrealized PnL of -$52.75. The edge evaporation dollar-PnL threshold (-$67) hasn't triggered. When the arbitrage has fully reversed (negative edge), the system should exit immediately regardless of the PnL dollar threshold.

### Evidence Summary

| Metric | Value |
|--------|-------|
| Total positions | 19 (16 closed, 3 open) |
| Win/Loss | 1W / 15L (6.25%) |
| Realized PnL | -$346.60 |
| Unrealized PnL | -$106.12 |
| Combined PnL | -$452.72 |
| Sub-5% edge entries | 11/16 (69%) |
| Positions held <30s | 13/16 (81%) |
| Repeat entries on same pair | KC/DET 4x, SJ/CHI 2x, TOR/MIL 2x |
| Exit by edge_evaporation | 10/16 (62.5%), avg hold 21.4s |
| Exit by time_decay | 5/16 (31.25%) |
| Exit by liquidity_deterioration | 1/16 (6.25%) |
| DB `detection_min_edge_threshold` | 0.008 (should be 0.05) |
| DB `exit_profit_capture_ratio` | 0.5 (should be 0.8) |

---

## Section 2: Impact Analysis

### Epic Impact

**Epic 10.96 (current, in-progress):** All 7 existing stories are done. The new stories extend the epic's scope ("Configuration Calibration") — they are a natural continuation of 10-96-4's intent, fixing the DB-side gap. No conflict with completed stories.

**Epic 11, 12 (backlog):** Unaffected. The sequencing gate (10.96 complete before 11 begins) remains — these new stories must finish first.

### Artifact Conflicts

**PRD:** No conflict. FR-AD-03 ("Filter opportunities below minimum edge threshold") is already specified. The 5% threshold is documented in CLAUDE.md domain rules. The fix enforces what's already required.

**Architecture:** No structural change. The config-accessor pattern, the seed script's idempotent design, and the detection pipeline remain architecturally sound. The issue is an operational gap (DB values not migrated), not an architectural flaw.

**CLAUDE.md:** Already updated by 10-96-4 to reference 5% minimum edge. No change needed.

### Technical Impact

**Impacted files (10-96-7):**
- New: `prisma/migrations/<timestamp>_calibrate_engine_config_defaults/migration.sql`
- Modified: `prisma/seed-config.ts` (add config migration pattern)

**Impacted files (10-96-8):**
- Modified: `src/modules/arbitrage-detection/pair-concentration-filter.service.ts` (add edge_evaporation cooldown)
- Modified: `src/modules/arbitrage-detection/pair-concentration-filter.interface.ts` (new config field)
- Modified: `src/modules/exit-management/threshold-evaluator.service.ts` (negative-edge immediate exit)
- Modified: `src/common/config/config-defaults.ts` (new config key)
- Modified: `src/common/config/settings-metadata.ts` (new setting)
- Modified: `src/dashboard/dto/update-settings.dto.ts` (new field)
- Modified: `prisma/schema.prisma` (new column)

---

## Section 3: Recommended Approach

**Selected Path:** Direct Adjustment — add 3 new stories to Epic 10.96.

**Rationale:**
- The root cause (DB config divergence) is a gap in 10-96-4's implementation, not a new feature
- Epic 10.96's charter ("Configuration Calibration") directly covers this work
- All required infrastructure (config-accessor pattern, pair-concentration-filter, threshold-evaluator) already exists from completed stories
- No rollback needed — no previously correct behavior was broken
- No PRD/MVP scope change — we're enforcing rules that were already specified

**Effort estimate:** Low (2-3 stories, each <1 day)
**Risk level:** Low (well-understood code paths, existing test patterns)
**Timeline impact:** +2-3 days before Epic 10.96 retro and Epic 11

---

## Section 4: Detailed Change Proposals

### Story 10-96-7: DB Config Migration — Activate Calibrated Defaults

**As an** operator,
**I want** the engine_config DB row updated to match the backtest-validated defaults from 10-96-4,
**So that** the 5% minimum edge threshold and 0.8 profit capture ratio are actually active in paper and live trading.

**Acceptance Criteria:**

**Given** the engine_config row has `detection_min_edge_threshold = 0.008`
**When** the Prisma migration runs
**Then** `detection_min_edge_threshold` is updated to `0.05`
**And** `exit_profit_capture_ratio` is updated to `0.8`

**Given** the seed script's idempotent design (only sets NULLs)
**When** future config calibrations are needed
**Then** a documented pattern exists for applying config value changes via Prisma migration SQL
**And** the seed-config.ts header comment warns that changing defaults does NOT update existing DB rows

**Given** the migration is applied
**When** the engine starts
**Then** `configAccessor.detectionMinEdgeThreshold` returns `0.05`
**And** `configAccessor.exitProfitCaptureRatio` returns `0.8`
**And** the dashboard Settings page reflects the new values

**Impacted files:**
- New: `prisma/migrations/<timestamp>_calibrate_config_defaults/migration.sql`
- Modified: `prisma/seed-config.ts` (documentation only — header warning)

**Backtest/paper evidence:** 11/16 positions entered below 5% edge = $207 of $347 total losses. Single most impactful fix.

**Context:** This is a gap-fill for 10-96-4, not a new feature. The code defaults are correct; the DB was never updated because the seed script is idempotent by design.

---

### Story 10-96-8: Edge-Evaporation Re-Entry Cooldown & Negative-Edge Immediate Exit

**As an** operator,
**I want** a specific re-entry cooldown after edge_evaporation exits and an immediate exit gate when the arbitrage edge has flipped negative,
**So that** the engine stops repeatedly entering proven-losing pairs and doesn't hold positions where the arb has reversed.

**Acceptance Criteria:**

**AC1 — Edge-evaporation cooldown:**

**Given** `edgeEvaporationCooldownHours` config setting (default 4)
**When** a position exits with criterion `EDGE_EVAPORATION`
**Then** the pair is blocked from re-entry for `edgeEvaporationCooldownHours`

**Given** a position exits with a criterion other than EDGE_EVAPORATION or TIME_DECAY
**When** cooldown is checked
**Then** only the generic `pairCooldownMinutes` applies

**Given** the pair-concentration-filter already queries `getLatestTimeDecayExitByPairIds`
**When** this story is implemented
**Then** a parallel `getLatestEdgeEvaporationExitByPairIds` repository method is added
**And** the filter checks both cooldowns (TIME_DECAY and EDGE_EVAPORATION) for each pair

**AC2 — Negative-edge immediate exit:**

**Given** an open position being evaluated by the threshold evaluator
**When** `recalculatedEdge < 0` (arbitrage has reversed)
**Then** an EDGE_EVAPORATION exit is triggered immediately, regardless of the dollar PnL threshold
**And** the exit detail includes `"Edge reversed: recalculated edge negative"`

**Given** `recalculatedEdge >= 0`
**When** the evaluator runs
**Then** the existing dollar-PnL-based edge evaporation logic applies (no change)

**Impacted files:**
- `pair-concentration-filter.service.ts` (new cooldown branch)
- `pair-concentration-filter.interface.ts` (new config field type)
- `threshold-evaluator.service.ts` (negative-edge gate before existing evap check)
- `config-defaults.ts`, `settings-metadata.ts`, `update-settings.dto.ts` (new setting)
- `prisma/schema.prisma` + migration (new `edge_evaporation_cooldown_hours` column)
- `open-position.repository.ts` (new `getLatestEdgeEvaporationExitByPairIds` method)

**Paper evidence:**
- KC/DET entered 4 times, all edge_evaporation exits, -$61 total (60-min generic cooldown insufficient)
- Position `0afa4945` has -24.9% recalculated edge, -$52.75 PnL, still open because dollar threshold not reached

---

### Story 10-96-9: Paper Trading Re-Verification (48h Run)

**As an** operator,
**I want** a 48-hour paper trading verification run after 10-96-7 and 10-96-8 are deployed,
**So that** I can confirm the fixes produce structurally profitable behavior before enabling live trading.

**Acceptance Criteria:**

**Given** stories 10-96-7 and 10-96-8 are deployed
**When** the engine runs in paper mode for 48 hours
**Then** the following are verified via database queries:

| Metric | Target | Method |
|--------|--------|--------|
| Zero sub-5% edge entries | 0 positions with `expected_edge < 0.05` | `SELECT ... WHERE expected_edge < 0.05` |
| No immediate exits | 0 positions with `hold_time < 60s` AND `exit_criterion = 'EDGE_EVAPORATION'` | Time delta check |
| No repeat same-pair losses | Max 1 entry per pair within 4h after edge_evap exit | Pair grouping query |
| Win rate improvement | > 30% (up from 6.25%) | Win/loss count |
| No negative-edge open positions | 0 open positions with `recalculated_edge < 0` | Status + edge check |

**Given** the verification pass
**When** all targets are met
**Then** Epic 10.96 retro can proceed and the live trading gate (Epic 10.96 → Epic 11 sequencing) is satisfied

**Given** the verification fails on any target
**When** results are analyzed
**Then** a follow-up course correction is triggered before proceeding

**Depends on:** 10-96-7, 10-96-8

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

All changes are within the existing Epic 10.96 scope and can be implemented directly by the dev team.

### Story Sequencing

```
10-96-7 (P0, DB migration)  ─┐
                               ├──► 10-96-9 (P2, verification run)
10-96-8 (P1, cooldown + gate) ┘
```

- **10-96-7** and **10-96-8** are independent and can be implemented in parallel
- **10-96-9** depends on both and runs after deployment

### Handoff Recipients

| Role | Responsibility |
|------|---------------|
| Dev agent (bmad-dev) | Implement 10-96-7 and 10-96-8 via TDD |
| Operator (Arbi) | Run 10-96-9 verification, review results |
| SM (bmad-correct-course) | Close Epic 10.96, trigger retro |

### Success Criteria

1. `engine_config.detection_min_edge_threshold = 0.05` after migration
2. `engine_config.exit_profit_capture_ratio = 0.8` after migration
3. Edge_evaporation exits trigger 4h cooldown on the pair
4. Positions with negative recalculated edge exit immediately
5. 48h paper run meets all verification targets
6. All existing tests pass (4021+ baseline)

### Sprint Status Updates Required

```yaml
# Add to Epic 10.96 section:
# Course correction 2026-04-16: Paper trading analysis (19 positions, 6.25% win rate, -$347 PnL)
# revealed DB config divergence — 10-96-4 calibrated code defaults but seed script is idempotent,
# so engine_config retained stale values (detection_min_edge_threshold=0.008 instead of 0.05,
# exit_profit_capture_ratio=0.5 instead of 0.8). Secondary: no edge_evaporation re-entry cooldown,
# no negative-edge immediate exit gate.
# Sprint Change Proposal: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16-paper-trading-profitability-fix.md
10-96-7-db-config-migration-calibrated-defaults: ready-for-dev
10-96-8-edge-evaporation-cooldown-negative-edge-exit: ready-for-dev
10-96-9-paper-trading-re-verification-run: backlog
```

### Deferred Debt Ledger Updates

Add new item:
```
# | 14 | Config seed idempotency gap — code default changes don't propagate to existing DB rows | Medium | Small | Mitigated by migration pattern in 10-96-7, documented in seed-config.ts |
```

---

## Checklist Summary

| ID | Item | Status |
|----|------|--------|
| 1.1 | Trigger: Paper trading analysis (Apr 14-15) | [x] Done |
| 1.2 | Core problem: DB config divergence + missing cooldown + loose exit gate | [x] Done |
| 1.3 | Evidence: 19 positions queried, engine_config verified, code defaults confirmed | [x] Done |
| 2.1 | Epic 10.96 can continue with added stories | [x] Done |
| 2.2 | No epic-level scope change needed | [x] Done |
| 2.3 | Future epics (11, 12) unaffected | [x] Done |
| 2.4 | No new epics needed | [x] Done |
| 2.5 | Epic priority unchanged | [x] Done |
| 3.1 | PRD: No conflict (enforcing existing FR-AD-03) | [x] Done |
| 3.2 | Architecture: No structural change | [x] Done |
| 3.3 | UI/UX: Dashboard Settings page auto-reflects config changes | [N/A] Skip |
| 3.4 | Testing, CI/CD: No impact | [N/A] Skip |
| 4.1 | Direct Adjustment: Viable, Low effort, Low risk | [x] Viable |
| 4.2 | Rollback: Not applicable | [N/A] Not viable |
| 4.3 | MVP Review: Not needed (MVP complete, enforcing existing rules) | [N/A] Not viable |
| 4.4 | Selected: Direct Adjustment — 3 stories in Epic 10.96 | [x] Done |
| 5.1-5.5 | Proposal components complete | [x] Done |
