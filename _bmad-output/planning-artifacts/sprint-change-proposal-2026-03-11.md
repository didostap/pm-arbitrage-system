# Sprint Change Proposal — LLM Batch Parallelization in Candidate Discovery

**Date:** 2026-03-11
**Triggered by:** Performance observation during Epic 8 operation
**Scope Classification:** Minor — direct implementation by dev team
**Mode:** Incremental review (all proposals approved)

---

## Section 1: Issue Summary

**Problem Statement:**
The candidate discovery pipeline (`candidate-discovery.service.ts`) processes LLM scoring requests sequentially. Each `processCandidate()` call awaits completion before starting the next, creating O(n) latency where n = number of candidates per contract. With LLM API calls taking 1-5 seconds each and `maxCandidatesPerContract` = 20, a single Polymarket contract's candidates can take 20-100 seconds to score. Full discovery runs across all contracts scale linearly from there.

**Discovery Context:**
Identified during post-Epic 8 operational review of the `8-4-cross-platform-candidate-discovery-pipeline` implementation. The sequential pattern was appropriate for initial correctness but is now a throughput bottleneck as the system matures.

**Evidence:**

- Code inspection: sequential `await` in loop at lines 179-201 of `candidate-discovery.service.ts`
- Each `processCandidate` makes 1-2 LLM API calls (primary + optional escalation) via `IScoringStrategy.scoreMatch()`
- The P2002 race condition handler (lines 340-353) demonstrates the code was designed to tolerate concurrent writes
- Stats mutations are single-expression synchronous increments, safe under concurrent `Promise.allSettled`

---

## Section 2: Impact Analysis

### Epic Impact

- **Epic 8 (Intelligent Contract Matching):** Done. This is a post-delivery optimization.
- **Epics 9-12:** Backlog. No dependencies on discovery throughput.
- **No epic additions, removals, or resequencing required.**

### Artifact Conflicts

- **PRD:** No conflicts. PRD specifies zero tolerance for matching errors and confidence scoring requirements but does not prescribe sequential vs. parallel processing.
- **Architecture:** No conflicts. Change is internal to `candidate-discovery.service.ts`. The `IScoringStrategy` interface contract and all module boundaries remain unchanged.
- **UI/UX:** No impact.
- **Monitoring:** Minor positive impact — `DISCOVERY_RUN_COMPLETED` events will report shorter `durationMs`.

### Technical Impact

- **Single file modified:** `candidate-discovery.service.ts`
- **One new env var:** `DISCOVERY_LLM_CONCURRENCY` (default: 10)
- **No new dependencies**
- **No interface changes**
- **Key risk:** LLM API rate limits. Mitigated by configurable concurrency cap defaulting to 10. Sized for Gemini Tier 1 flash (300 RPM) at 70% safety buffer. Batch-then-wait has natural breathing room between batches (result processing, DB writes). Operator tunes via timing logs.

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment**

Modify the inner candidate loop to batch-process candidates with bounded concurrency using `Promise.allSettled`. The outer `polyContracts` loop remains sequential (deferred secondary optimization to reduce complexity).

**Rationale:**

- Surgical, localized change — one method in one file
- Existing P2002 handler makes `processCandidate` already parallel-safe
- Stats mutation safety confirmed (single-expression increments in single-threaded Node.js)
- No new dependencies — pure `Promise.allSettled` batch approach
- Configurable concurrency respects NFR-I2 (20% safety buffer on API rate limits)

**Effort:** Low (single service method refactor + tests)
**Risk:** Low (existing race condition handling, no interface changes)
**Timeline Impact:** None — independent of current sprint work (Epics 9-12 backlog)

---

## Section 4: Detailed Change Proposals

### File: `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts`

#### Edit 1a — New config property

**Section:** Class properties + constructor

Add property:

```typescript
private readonly llmConcurrency: number;
```

Add to constructor (after `maxCandidatesPerContract` assignment):

```typescript
this.llmConcurrency = Number(this.configService.get<number>('DISCOVERY_LLM_CONCURRENCY', 10));
```

**Rationale:** Default of 10 concurrent LLM calls. Sized for Gemini Tier 1 flash (300 RPM) at 70% safety buffer (~210 RPM). With batch-then-wait at ~2-3s/call, effective RPM stays within budget. Operator-tunable via env var; timing logs enable empirical tuning.

#### Edit 1b — Replace sequential inner loop with batch-parallel processing

**Section:** Lines 179-201 (inner candidate loop in `runDiscovery()`)

Replace sequential `for...of` with:

1. **Pre-resolve candidates** into filtered array with type-narrowed `kalshiContract`
2. **Batch loop** using `Promise.allSettled` with `llmConcurrency` chunk size
3. **Error handling** on rejected results matching original behavior
4. **Safety comment** documenting the stats mutation concurrency assumption
5. **Timing log** per-contract for operator observability

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
// are single-expression increments that complete in one microtask tick,
// safe under concurrent Promise.allSettled. Do not refactor those
// increments to follow an await without revisiting concurrency safety.
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

### Unchanged

- `processCandidate()` method — zero modifications
- `IScoringStrategy` interface — zero modifications
- Event emissions — unchanged
- Outer `polyContracts` loop — stays sequential (deferred)
- All error handling in `processCandidate` (LlmScoringError, P2002)

### Env var addition

| Variable                    | Default | Description                                                                                       |
| --------------------------- | ------- | ------------------------------------------------------------------------------------------------- |
| `DISCOVERY_LLM_CONCURRENCY` | `10`    | Max concurrent LLM scoring calls per batch. Sized for Gemini Tier 1 flash (300 RPM @ 70% safety). |

Add after `DISCOVERY_MAX_CANDIDATES_PER_CONTRACT` in both files:

`.env.example`:

```
DISCOVERY_LLM_CONCURRENCY=10                              # Max concurrent LLM scoring calls per batch (Gemini Tier 1 flash @ 70% safety)
```

`.env.development`:

```
DISCOVERY_LLM_CONCURRENCY=10
```

---

## Section 5: Implementation Handoff

**Change Scope: Minor** — Direct implementation by development team.

**Handoff: Dev agent**

**Responsibilities:**

1. Implement edits 1a + 1b in `candidate-discovery.service.ts`
2. Update existing tests in `candidate-discovery.service.spec.ts` to cover:
   - Batch parallelization behavior (multiple candidates processed concurrently)
   - Concurrency config respected (verify batch sizes)
   - Error handling in parallel context (rejected promises → stats + logging)
   - Timing log emission
3. Add `DISCOVERY_LLM_CONCURRENCY` to `.env.example` and `.env.development`
4. Run `pnpm lint` and `pnpm test`

**Success Criteria:**

- Discovery run duration scales as O(n/concurrency) instead of O(n) for candidate scoring
- All existing tests pass without modification (processCandidate behavior unchanged)
- New tests cover batch parallelization edge cases
- `Candidate batch completed` debug log emitted with timing data

**Deferred (future optimization):**

- Outer `polyContracts` loop parallelization — introduces shared stats across contract batches, higher complexity, separate proposal needed
