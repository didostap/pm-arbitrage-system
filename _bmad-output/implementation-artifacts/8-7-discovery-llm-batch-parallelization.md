# Story 8.7: Discovery LLM Batch Parallelization

Status: done

## Story

As an operator,
I want the candidate discovery pipeline to process LLM scoring calls in parallel batches instead of sequentially,
So that discovery run duration scales as O(n/concurrency) instead of O(n) and full runs complete in minutes rather than tens of minutes.

## Acceptance Criteria

1. **Given** the candidate discovery pipeline runs with multiple candidates per Polymarket contract
   **When** candidates are scored via `IScoringStrategy.scoreMatch()`
   **Then** candidates are processed in parallel batches of configurable size (default: 10) using `Promise.allSettled`
   **And** the outer `polyContracts` loop remains sequential (unchanged)
   [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Section-3; _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Edit-1b]

2. **Given** the `DISCOVERY_LLM_CONCURRENCY` environment variable is set
   **When** the `CandidateDiscoveryService` is constructed
   **Then** the concurrency cap is read from config with a default of 10, floored at 1 (values ≤0 or NaN resolve to 1)
   **And** batch sizes respect this cap (e.g., concurrency=3 with 8 candidates yields 3 batches: 3+3+2)
   [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Edit-1a]

3. **Given** a candidate within a batch fails (promise rejects)
   **When** `Promise.allSettled` completes the batch
   **Then** all other candidates in the batch still complete successfully
   **And** the failed candidate increments `stats.scoringFailures` and is logged with polyContractId, kalshiContractId, and error message
   **And** the discovery run continues to the next batch and subsequent Polymarket contracts
   [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Edit-1b error handling; epics.md#Story-8.4 AC "partial failure is acceptable"]

4. **Given** all batches for a Polymarket contract's candidates have completed
   **When** results are collected
   **Then** a debug log `"Candidate batch completed"` is emitted once per Polymarket contract with: `polyContractId`, `candidateCount` (total for that contract), `concurrency`, and `durationMs` (wall time for all batches)
   [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Edit-1b timing log]

5. **Given** the `DISCOVERY_LLM_CONCURRENCY` env var is added
   **When** configuration files are checked
   **Then** `.env.example` and `.env.development` both include `DISCOVERY_LLM_CONCURRENCY=10` with a comment referencing Gemini Tier 1 flash rate limit sizing
   [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Env-var-addition]

## Tasks / Subtasks

- [x] **Task 1: Add `llmConcurrency` config property** (AC: #2)
  - [x] Add `private readonly llmConcurrency: number;` property to `CandidateDiscoveryService`
  - [x] Add to constructor after `maxCandidatesPerContract` assignment: `this.llmConcurrency = Math.max(1, Number(this.configService.get<number>('DISCOVERY_LLM_CONCURRENCY', 10)) || 1);`
  - [x] The `Math.max(1, ...)` floor prevents infinite loop if set to 0/negative; `|| 1` handles NaN from non-numeric input
  - [x] Pattern: identical to existing config reads (e.g., `maxCandidatesPerContract`, `preFilterThreshold`) plus defensive floor

- [x] **Task 2: Replace sequential inner loop with batch-parallel processing** (AC: #1, #3, #4)
  - [x] Pre-resolve `ranked.slice(0, maxCandidatesPerContract)` into `candidatePairs` array with type-narrowed `kalshiContract` (filter out undefined finds)
  - [x] Replace the sequential `for...of` + try/catch with a batched `for` loop using `Promise.allSettled` with `llmConcurrency` chunk size
  - [x] Handle rejected results: increment `stats.scoringFailures++`, log with polyContractId/kalshiContractId/error
  - [x] Add safety comment documenting stats mutation concurrency assumption
  - [x] Add timing log after all batches for a polyContract: `"Candidate batch completed"` with `polyContractId`, `candidateCount`, `concurrency`, `durationMs`

- [x] **Task 3: Add env vars to config files** (AC: #5)
  - [x] Add `DISCOVERY_LLM_CONCURRENCY=10` to `.env.example` after `DISCOVERY_MAX_CANDIDATES_PER_CONTRACT` with comment
  - [x] Add `DISCOVERY_LLM_CONCURRENCY=10` to `.env.development` after `DISCOVERY_MAX_CANDIDATES_PER_CONTRACT`

- [x] **Task 4: Add tests for batch parallelization** (AC: #1, #2, #3, #4)
  - [x] Add `DISCOVERY_LLM_CONCURRENCY: 10` to the `configValues` object alongside other `DISCOVERY_*` vars
  - [x] Test: rejected promise in batch doesn't block other candidates — set up 3 candidates, middle one's `prisma.contractMatch.create` throws a non-P2002 error (making `processCandidate` throw), verify other 2 complete with matches created and stats show `scoringFailures: 1` plus correct `pairsScored`/`autoApproved` counts for the 2 successful candidates
  - [x] Test: concurrency config is respected — set `DISCOVERY_LLM_CONCURRENCY=2` in configValues, provide 5 candidates, verify all 5 are scored (`scoreMatch` called 5 times) and the timing log shows `concurrency: 2` and `candidateCount: 5`
  - [x] Test: timing log emitted per polyContract — set up 1 polyContract with 2 candidates, verify `logger.debug` called with `message: 'Candidate batch completed'` and `data` containing `durationMs` (typeof number), `candidateCount: 2`, `concurrency: 10`
  - [x] Test: empty candidatePairs (all filtered out) — pre-filter returns candidates whose IDs don't match any Kalshi contract, verify batch loop is skipped, timing log still emits with `candidateCount: 0` and `durationMs` close to 0, no `scoreMatch` calls
  - [x] Test: concurrency floor at 1 — set `DISCOVERY_LLM_CONCURRENCY=0`, verify processing still completes and timing log shows `concurrency: 1`
  - [x] Verify all 25 existing tests pass unchanged

- [x] **Task 5: Run lint and full test suite** (AC: #1-#5)
  - [x] `cd pm-arbitrage-engine && pnpm lint` — clean
  - [x] `pnpm test` — 1745 passed (1740 existing + 5 new), 2 todo

## Dev Notes

### Implementation Sequence — FOLLOW THIS ORDER

1. **Task 1** (config property) — 1 property + 1 line in constructor. Zero risk.
2. **Task 2** (inner loop refactor) — The core change. See detailed code below.
3. **Task 3** (env files) — 2 lines across 2 files.
4. **Task 4** (tests) — Run existing tests first to confirm green, then add new tests.
5. **Task 5** (lint + full suite) — Final validation.

### Core Refactor: Sequential → Batch-Parallel

**File:** `src/modules/contract-matching/candidate-discovery.service.ts`

**Current code** (inner loop in `runDiscovery()`, approximately lines 179-201):
```typescript
for (const candidate of ranked.slice(0, this.maxCandidatesPerContract)) {
  const kalshiContract = kalshiContracts.find(k => k.contractId === candidate.id);
  if (!kalshiContract) continue;

  try {
    await this.processCandidate(polyContract, kalshiContract, stats);
  } catch (error) {
    stats.scoringFailures++;
    this.logger.error({ ... });
  }
}
```

**Replace with:**
```typescript
const candidatePairs = ranked
  .slice(0, this.maxCandidatesPerContract)
  .map(candidate => ({
    candidate,
    kalshiContract: kalshiContracts.find(k => k.contractId === candidate.id),
  }))
  .filter(
    (
      pair,
    ): pair is typeof pair & {
      kalshiContract: ContractSummary;
    } => pair.kalshiContract !== undefined,
  );

// Process candidates in parallel batches.
// Stats mutations inside processCandidate (e.g. stats.pairsScored++)
// are synchronous increments that execute between await points in
// Node.js's single-threaded event loop — no two increments can
// interleave mid-operation. Do not refactor those increments to
// span an await without revisiting concurrency safety.
const batchStart = Date.now();

for (let i = 0; i < candidatePairs.length; i += this.llmConcurrency) {
  const batch = candidatePairs.slice(i, i + this.llmConcurrency);
  const results = await Promise.allSettled(
    batch.map(({ kalshiContract }) => this.processCandidate(polyContract, kalshiContract, stats)),
  );

  for (const [idx, result] of results.entries()) {
    if (result.status === 'rejected') {
      stats.scoringFailures++;
      const { kalshiContract } = batch[idx];
      this.logger.error({
        message: 'Candidate processing failed',
        data: {
          polyContractId: polyContract.contractId,
          kalshiContractId: kalshiContract.contractId,
          error: result.reason instanceof Error ? result.reason.message : String(result.reason),
        },
      });
    }
  }
}

this.logger.debug({
  message: 'Candidate batch completed',
  data: {
    polyContractId: polyContract.contractId,
    candidateCount: candidatePairs.length,
    concurrency: this.llmConcurrency,
    durationMs: Date.now() - batchStart,
  },
});
```

[Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Edit-1b — exact code provided]

### Why Existing Tests Pass Unchanged

The refactor preserves identical observable behavior:

1. **LlmScoringError**: Caught inside `processCandidate` → increments `scoringFailures` → returns → promise **fulfills**. The `results.entries()` loop never sees it.
2. **P2002 race condition**: Caught inside `processCandidate` → returns → promise **fulfills**. No stats increment (unchanged).
3. **Other errors**: `processCandidate` throws → promise **rejects** → `results.entries()` loop catches it → increments `scoringFailures` + logs. Equivalent to the current outer try/catch.
4. **Mock call order**: `batch.map()` creates promises in array order. `mockRejectedValueOnce`/`mockResolvedValueOnce` are consumed in call order, which is preserved.
5. **Stats totals**: Identical — same increments, just interleaved rather than sequential.

[Source: Codebase verification of processCandidate error handling at lines 228-355]

### `processCandidate` Is Already Parallel-Safe

- **DB reads**: `prisma.contractMatch.findFirst` with different contract ID pairs — independent queries
- **DB writes**: `prisma.contractMatch.create` — unique constraint on (polymarketContractId, kalshiContractId) with P2002 handler for race conditions
- **LLM calls**: `scoringStrategy.scoreMatch` is stateless
- **Stats mutations**: `stats.field++` — synchronous increments that execute between await points. In Node.js single-threaded event loop, no two increments interleave mid-operation even with concurrent promises.

[Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Section-2 evidence; processCandidate lines 340-353 P2002 handler]

### Rate Limit Sizing

Default concurrency = 10. Rationale:
- Gemini Tier 1 Flash: 300 RPM
- 70% safety buffer (NFR-I2): ~210 RPM effective
- At ~2-3s per LLM call, 10 concurrent calls ≈ 200-300 RPM (within budget)
- Batch-then-wait pattern provides natural breathing room between batches
- Operator tunes via `DISCOVERY_LLM_CONCURRENCY` env var and timing logs

[Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Edit-1a rationale]

### What This Story Does NOT Change

- `processCandidate()` method — zero modifications
- `IScoringStrategy` interface — zero modifications
- Event emissions — unchanged
- Outer `polyContracts` loop — stays sequential
- All error handling in `processCandidate` (LlmScoringError, P2002)
- Three-tier scoring logic (auto-approve/pending/auto-reject thresholds)
- `PreFilterService`, `CatalogSyncService`, `ConfidenceScorerService`

[Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Unchanged]

### Deferred (Future Optimization)

Outer `polyContracts` loop parallelization — introduces shared stats across contract batches, higher complexity, separate proposal needed.

[Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md#Section-5 deferred]

### Project Structure Notes

**Files to modify:**
- `src/modules/contract-matching/candidate-discovery.service.ts` — 1 property + constructor line + inner loop replacement
- `src/modules/contract-matching/candidate-discovery.service.spec.ts` — add ~3 new test cases
- `.env.example` — add `DISCOVERY_LLM_CONCURRENCY=10`
- `.env.development` — add `DISCOVERY_LLM_CONCURRENCY=10`

**No files to create. No files to delete. No Prisma schema changes. No new dependencies.**

### Testing Strategy

- **Framework:** Vitest 4, co-located specs
- **Mock setup:** Manual DI mocks matching existing pattern in spec file (not `@golevelup/ts-vitest`)
- **Baseline:** 101 test files, 1739 passed, 2 todo, 1 pre-existing flaky e2e (logging.e2e-spec.ts)
- **Existing tests:** All 24 tests in `candidate-discovery.service.spec.ts` must pass unchanged
- **New test cases:**
  - Rejected promise in batch: 3 candidates, 1 throws non-LLM error → other 2 complete, stats show `scoringFailures: 1` + correct counts
  - Concurrency config: `DISCOVERY_LLM_CONCURRENCY=2`, 5 candidates → all 5 scored, timing log confirms `concurrency: 2` and `candidateCount: 5`
  - Timing log: verify `logger.debug` called with `"Candidate batch completed"` including `durationMs` (number), `candidateCount`, `concurrency`
  - Empty candidatePairs: all pre-filter results have no Kalshi match → batch loop skipped, timing log emits with `candidateCount: 0`, no `scoreMatch` calls
  - Concurrency floor: `DISCOVERY_LLM_CONCURRENCY=0` → processing completes (floors to 1 via `Math.max`)
- **Add `DISCOVERY_LLM_CONCURRENCY: 10` to `configValues` object** alongside other `DISCOVERY_*` vars

### Previous Story Intelligence

**From Story 8.6 (Filtering Fixes):**
- `isWithinSettlementWindow` now returns `false` for null dates (line 38)
- Threshold calibrated to 0.25 (was 0.15)
- Test baseline post-8.6: 1651 tests (96 files)
- Kalshi date fallback chain uses `||` not `??` (empty string lesson from 8.4)
[Source: 8-6-candidate-discovery-filtering-fixes-match-page-pagination.md — Completion Notes]

**From Story 8.3 (Resolution Feedback Loop):**
- Test baseline post-8.3: 1739 passed, 2 todo (101 files) — verified by test run 2026-03-11
- `ResolutionPollerService` and `CalibrationService` added to contract-matching module
- `SchedulerRegistry` pattern used for dynamic cron (same as `CandidateDiscoveryService`)
[Source: 8-3-resolution-feedback-loop.md; epic-8-retro-2026-03-11.md]

**From Epic 8 Retrospective:**
- Module boundary violations: 0 across all Epic 8 stories
- `forwardRef(() => ConnectorModule)` in `ContractMatchingModule` for circular dependency
- Post-implementation bug fixes concentrated in 8.4 (12 fixes from live testing)
- All stories had Lad MCP + adversarial code reviews
[Source: epic-8-retro-2026-03-11.md]

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-11.md] — Full change proposal: problem statement, impact analysis, code edits, env var spec, success criteria
- [Source: epics.md#Story-8.4] — Discovery pipeline AC: partial failure acceptable, LlmScoringError handling, IScoringStrategy interface
- [Source: pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts lines 127-213] — Current `runDiscovery()` with sequential inner loop
- [Source: pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts lines 228-355] — `processCandidate()` with P2002 handler and LlmScoringError handling
- [Source: pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts lines 54-82] — Constructor config pattern
- [Source: pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.spec.ts] — 24 existing tests (mock patterns, assertion style)
- [Source: pm-arbitrage-engine/.env.example lines 95-100] — Existing DISCOVERY_* env vars
- [Source: 8-6-candidate-discovery-filtering-fixes-match-page-pagination.md] — Previous story context
- [Source: 8-3-resolution-feedback-loop.md] — Most recent story context
- [Source: epic-8-retro-2026-03-11.md] — Epic 8 retrospective learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

### Completion Notes List

- Changed `|| 10` to `|| 1` in constructor NaN fallback after Lad MCP code review caught that `0 || 10` evaluates to 10, violating the "floor at 1" AC. With `|| 1`, values of 0 correctly floor to 1 via `Math.max(1, ...)`.
- Strengthened concurrency floor test to verify timing log shows `concurrency: 1` (not just that processing completes), preventing false positive.
- All 25 existing tests pass unchanged. 5 new tests added (30 total in file). Full suite: 1745 passed, 2 todo.
- `processCandidate()` unchanged — batch refactor is confined to the inner loop in `runDiscovery()`.
- Secondary Lad reviewer timed out; primary reviewer findings addressed.
- **Code review fix (2026-03-11):** Hardened test cleanup in `describe('batch parallelization')` — added `afterEach` block to restore `Logger.prototype.debug` spy and reset `configValues['DISCOVERY_LLM_CONCURRENCY']` instead of manual cleanup at end of each test body. Prevents spy leaks and stale config on test failure. Added missing eslint-disable directives for pre-existing `no-unsafe-member-access`/`no-unsafe-call` from spy access patterns.

### File List

- `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts` — added `llmConcurrency` property + constructor config read; replaced sequential inner loop with batch-parallel `Promise.allSettled` processing + timing log
- `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.spec.ts` — added `Logger` import, `DISCOVERY_LLM_CONCURRENCY` to configValues, 5 new tests in `describe('batch parallelization')`
- `pm-arbitrage-engine/.env.example` — added `DISCOVERY_LLM_CONCURRENCY=10` with comment
- `pm-arbitrage-engine/.env.development` — added `DISCOVERY_LLM_CONCURRENCY=10`
