# Story 9.3: Confidence-Adjusted Position Sizing

Status: done

## Story

As an operator,
I want position sizes automatically reduced for lower-confidence contract matches,
So that uncertain matches carry proportionally less capital risk.

## Acceptance Criteria

1. **Given** an opportunity has a contract match confidence score, **When** position sizing is calculated, **Then** adjusted size = `base_size × (confidence_score / 100)` and a 90% confidence match gets 90% of base size, an 85% match gets 85%. [Source: epics.md#Story-9.3, prd.md#FR-RM-08]

2. **Given** a match was manually approved (MVP pairs with no NLP score, `confidenceScore` is `null`), **When** position sizing runs, **Then** manually approved matches use 100% base size (confidence treated as 1.0). [Source: epics.md#Story-9.3]

## Tasks / Subtasks

- [x] **Task 1: Add `confidenceScore` to `ContractPairConfig` and propagate from DB** (AC: #1, #2)
  - [x]Add `confidenceScore?: number | null` to `ContractPairConfig` interface in `modules/contract-matching/types/contract-pair-config.type.ts`
  - [x]Map in `ContractPairLoaderService.dbMatchToConfig()`: `confidenceScore: match.confidenceScore ?? null`
  - [x]Add test in `contract-pair-loader.service.spec.ts` verifying `confidenceScore` propagation from DB match

- [x] **Task 2: Extend `extractClusterInfo()` to also extract `confidenceScore`** (AC: #1, #2)
  - [x]Extend the return type of `extractClusterInfo()` in `risk-manager.service.ts` to include `confidenceScore?: number`
  - [x]Extract from `pairConfig.confidenceScore`: `confidenceScore: typeof pairConfig.confidenceScore === 'number' ? pairConfig.confidenceScore : undefined`
  - [x]Rename method to `extractPairContext()` for clarity (it now extracts more than cluster info) — update all call sites within `validatePosition()`

- [x] **Task 3: Apply confidence adjustment in `validatePosition()`** (AC: #1, #2)
  - [x]Insert confidence adjustment AFTER base size calculation (`bankroll × maxPositionPct`) and BEFORE the max open pairs check — this ensures all downstream checks (capital, cluster projection) use the confidence-adjusted size
  - [x]Implementation:

    ```typescript
    // [Story 9.3] Confidence-adjusted position sizing
    const pairContext = this.extractPairContext(opportunity);
    let rawConfidence = pairContext?.confidenceScore ?? null;

    // Validate range — treat out-of-bounds as null (fail-open)
    if (rawConfidence != null && (rawConfidence < 0 || rawConfidence > 100)) {
      this.logger.warn({
        message: 'Invalid confidence score out of [0,100] range, treating as null',
        data: { rawConfidence },
      });
      rawConfidence = null;
    }

    const confidenceMultiplier =
      rawConfidence != null ? new FinancialDecimal(rawConfidence).div(100) : new FinancialDecimal(1);
    maxPositionSizeUsd = maxPositionSizeUsd.mul(confidenceMultiplier);
    ```

  - [x]Hoist `extractPairContext` call to just after the base size calculation (currently `extractClusterInfo` is called inside the cluster enforcement block — move it earlier so both confidence and cluster logic share one extraction)
  - [x]Pass `pairContext` to the cluster enforcement block instead of calling extraction again
  - [x]Log the confidence adjustment when applied (confidence < 100):
    ```typescript
    if (rawConfidence != null && rawConfidence < 100) {
      this.logger.log({
        message: 'Confidence-adjusted position sizing applied',
        data: {
          confidenceScore: rawConfidence,
          multiplier: confidenceMultiplier.toFixed(4),
          adjustedSizeUsd: maxPositionSizeUsd.toFixed(2),
        },
      });
    }
    ```

- [x] **Task 4: Add observability fields to `RiskDecision`** (AC: #1)
  - [x]Add to `RiskDecision` in `common/types/risk.type.ts`:
    - `confidenceScore?: number` (raw 0-100 value from the match, for logging/dashboard)
    - `confidenceAdjustedSizeUsd?: Decimal` (position size after confidence adjustment, before cluster tapering)
  - [x]Population logic in `validatePosition()` return paths:
    - `confidenceScore`: always populate when the raw value is present (not null) — even when 100%, so the operator can see the score for every scored match
    - `confidenceAdjustedSizeUsd`: only populate when adjustment was actually applied (`rawConfidence != null && rawConfidence < 100`)

- [x] **Task 5: Tests** (AC: #1, #2)
  - [x]`risk-manager.service.spec.ts` — add confidence adjustment test scenarios:
    - 90% confidence → `maxPositionSizeUsd` = 90% of base (AC #1 example)
    - 85% confidence → 85% of base (AC #1 example)
    - 87.5% confidence (non-integer) → 87.5% of base (decimal precision)
    - 0% confidence → `maxPositionSizeUsd` = 0 (zero position, effectively blocks trade)
    - `null` confidence → 100% of base, no adjustment (AC #2)
    - 100% confidence → 100% of base, no adjustment
    - Out-of-range confidence (-10) → treated as null, full base size, warning logged
    - Out-of-range confidence (150) → treated as null, full base size, warning logged
    - Confidence + cluster soft-limit tapering compose: e.g., 80% confidence + cluster at 13% → `base × 0.80 × (1 - 13%/15%)`
    - Extraction returns `null` (no pairConfig) → skip confidence adjustment, use full base size (fail-open, consistent with cluster extraction failure pattern)
    - Verify `confidenceScore` populated in `RiskDecision` when raw value is present (even at 100%)
    - Verify `confidenceAdjustedSizeUsd` populated only when confidence < 100
    - Verify both fields NOT populated when confidence is null
  - [x]`contract-pair-loader.service.spec.ts` — verify `confidenceScore` propagation:
    - DB match with `confidenceScore: 90` → config has `confidenceScore: 90`
    - DB match with `confidenceScore: null` → config has `confidenceScore: null`

## Dev Notes

### Architecture Context

This story adds the final position-sizing modifier in the risk validation hot path. Story 4.1 established base sizing (`bankroll × maxPositionPct`). Story 9.2 added cluster-based soft-limit tapering. This story adds confidence-based scaling, completing FR-RM-08. [Source: epics.md#Epic-9, prd.md#FR-RM-08]

**Data flow for confidence score (currently broken, this story fixes it):**

```
ContractMatch.confidenceScore (Prisma, Float?, 0-100 scale)
  → [NOT MAPPED] ContractPairConfig lacks confidenceScore
  → RawDislocation.pairConfig → EnrichedOpportunity.dislocation
  → validatePosition(opportunity: unknown) — cannot access confidence
```

After this story:

```
ContractMatch.confidenceScore (Prisma, Float?, 0-100)
  → ContractPairConfig.confidenceScore (number | null)  [Task 1]
  → RawDislocation.pairConfig → EnrichedOpportunity.dislocation
  → extractPairContext() extracts it                     [Task 2]
  → validatePosition() applies adjustment                [Task 3]
```

[Source: codebase `contract-pair-loader.service.ts#dbMatchToConfig`, `risk-manager.service.ts#extractClusterInfo`]

### Position in `validatePosition()` Pipeline

Current execution order in `validatePosition()`:

1. Trading halt check (existing)
2. Base `maxPositionSizeUsd = bankroll × maxPositionPct` (existing)
3. **NEW: Extract pair context + confidence adjustment** — `maxPositionSizeUsd *= confidenceScore / 100`
4. Max open pairs check (existing)
5. Available capital check (existing) — now uses confidence-adjusted size
6. Cluster limit enforcement: aggregate check, soft-limit tapering, hard-limit projection (Story 9.2) — reuse `pairContext` from step 3
7. Approaching-limit event emission (existing)
8. Return approved

**Why placement between steps 2 and 4:** Confidence is a match-quality property. All downstream checks (capital availability, cluster limit projection) should use the actual position size that will be deployed. Placing it early ensures the cluster hard-limit projection uses the confidence-adjusted size — if a 70% confidence match reduces position size to 70% of base, the cluster projection should reflect that smaller capital addition. [Source: codebase `risk-manager.service.ts`, `validatePosition()` method]

**Composition with cluster tapering:** The two adjustments multiply. Example at 80% confidence with cluster at 13% (soft-limit zone, hard limit 15%):

```
base = bankroll × 0.03
after confidence = base × 0.80
after cluster taper = (base × 0.80) × (1 - 13%/15%) = base × 0.80 × 0.133 = base × 0.107
```

This is correct — both quality uncertainty and portfolio concentration reduce the position size. [Source: epics.md#Story-9.2 AC#1, epics.md#Story-9.3 AC#1]

### Key Implementation Details

**Confidence score scale:** The DB stores 0-100 (`Float?` in Prisma). The AC formula says `base_size × confidence_score` where "90% confidence → 90% of base size". Therefore normalize to 0-1: `confidenceMultiplier = confidenceScore / 100`. All math via `decimal.js`. [Source: prisma/schema.prisma line 111, epics.md#Story-9.3 AC#1, CLAUDE.md domain rules]

**Null handling (AC #2):** `confidenceScore` is `null` for:

- MVP pairs loaded from YAML config (no NLP scoring)
- Manually operator-approved matches created before Epic 8 (semantic matching)
- Any match where the scoring pipeline hasn't run yet

All null cases → multiplier = 1.0 (full base size). [Source: epics.md#Story-9.3 AC#2]

**Range validation:** Confidence scores should be in [0, 100]. Out-of-range values (negative or >100) are treated as null (fail-open) with a warning log. This guards against corrupted DB data. The NLP scoring pipeline produces valid 0-100 values; this is a defensive measure only.

**Extraction pattern:** Extend the existing `extractClusterInfo()` to also return `confidenceScore`. The method already traverses `opportunity.dislocation.pairConfig` — just add one more field extraction. Rename to `extractPairContext()` since it now extracts confidence in addition to cluster info. If extraction returns `null` (no pairConfig), skip confidence adjustment entirely (fail-open) — consistent with the established cluster extraction failure pattern. The existing method already logs warnings on extraction failure. [Source: codebase `risk-manager.service.ts`, `extractClusterInfo()` method]

**Hoisting the extraction call:** Currently `extractClusterInfo()` is called inside the cluster enforcement `if` block. After this story, the extraction must happen earlier (before confidence adjustment at pipeline step 3) and the result passed to both the confidence logic and the cluster logic. This deduplicates the traversal.

**No new config values needed.** The confidence score comes from the match data, not environment config. No new env vars.

**No new events needed.** Confidence adjustment is a sizing modifier, not a limit check. It doesn't warrant its own event — the existing log entry and `RiskDecision` observability fields are sufficient. If the operator wants to see confidence-adjusted positions, the `confidenceScore` and `confidenceAdjustedSizeUsd` fields on `RiskDecision` propagate through the approved opportunity log.

**No module boundary violations.** `ContractPairConfig` is in `contract-matching/types/` (allowed import for `risk-management` via `common/` types path). The confidence score data flows through the existing `EnrichedOpportunity` → `validatePosition(unknown)` pipeline. [Source: CLAUDE.md module dependency rules]

### Existing Infrastructure to Reuse

| Component              | Location                                               | What to Reuse                                                         |
| ---------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| `extractClusterInfo()` | `risk-manager.service.ts`                              | Extend to extract `confidenceScore`, rename to `extractPairContext()` |
| `ContractPairConfig`   | `contract-matching/types/contract-pair-config.type.ts` | Add field                                                             |
| `dbMatchToConfig()`    | `contract-pair-loader.service.ts`                      | Add mapping                                                           |
| `RiskDecision`         | `common/types/risk.type.ts`                            | Add observability fields                                              |
| `FinancialDecimal`     | `common/utils/financial-math.ts`                       | For all arithmetic                                                    |
| Existing spec patterns | `risk-manager.service.spec.ts`                         | Mock patterns for ConfigService, CorrelationTracker, EventEmitter2    |

### Testing Strategy

Co-located specs using Vitest 4 + `unplugin-swc`. Mock `PrismaService`, `ConfigService`, `EventEmitter2`, `CorrelationTrackerService` (same mocking pattern as Story 9.2 tests).

**Baseline:** 1942 tests, 112 files, all green (1 pre-existing e2e timeout in `logging.e2e-spec.ts` — unrelated).

**Key test scenarios:**

- Below 100% confidence (90%, 85%, 87.5%) → verify `maxPositionSizeUsd` is scaled correctly
- 0% confidence → position size = 0
- Null confidence → full base size (no adjustment)
- 100% confidence → full base size (no adjustment)
- Out-of-range (-10, 150) → treated as null, warning logged
- Confidence + cluster tapering composition → verify multiplicative reduction
- Extraction failure (null pairContext) → fail-open, full base size
- Observability: `confidenceScore` populated when present (even at 100%); `confidenceAdjustedSizeUsd` only when < 100

### Previous Story Intelligence (Story 9.2)

- **Extraction pattern works well.** `extractClusterInfo()` with typed narrowing of `unknown` is clean and testable. Extend, don't rewrite.
- **`validatePosition()` is now `async`** (changed from sync in Story 9.2 for `getTriageRecommendations()`). New logic can also be async if needed, but confidence adjustment is synchronous (no DB queries) — just arithmetic.
- **`FinancialDecimal` wrapper** used throughout `validatePosition()` — use consistently for confidence math.
- **Config pattern:** Cluster limits read from `ConfigService` as strings, wrapped in `new FinancialDecimal(...)`. Confidence score comes from match data (number), not config — wrap in `new FinancialDecimal(rawConfidence)`.
- **Test fix lesson from 9.2:** Soft-limit tapering at certain percentages can reduce size enough to pass hard-limit projection. Design test values carefully to avoid false passes.

### Project Structure Notes

All files align with established module structure. No new modules, directories, or dependencies needed. Changes are contained to:

- `modules/contract-matching/` — type + loader (data propagation)
- `modules/risk-management/` — validation logic (business rule)
- `common/types/` — `RiskDecision` extension (observability)

[Source: CLAUDE.md architecture, codebase exploration]

### References

- [Source: epics.md#Story-9.3] — Acceptance criteria and business rules
- [Source: prd.md#FR-RM-08] — "adjust position sizing based on contract matching confidence score (lower confidence = smaller position size, formula: base_size × confidence_score)"
- [Source: CLAUDE.md#Domain-Rules] — All financial math uses decimal.js
- [Source: CLAUDE.md#Module-Dependency-Rules] — Allowed imports, forbidden cross-module references
- [Source: prisma/schema.prisma line 111] — `confidenceScore Float? @map("confidence_score")` on ContractMatch
- [Source: codebase `risk-manager.service.ts#validatePosition`] — Current `validatePosition()` implementation
- [Source: codebase `risk-manager.service.ts#extractClusterInfo`] — Extraction pattern to extend
- [Source: codebase `contract-pair-loader.service.ts#dbMatchToConfig`] — DB → config mapping
- [Source: codebase `contract-matching/types/contract-pair-config.type.ts#ContractPairConfig`] — Current interface (lacks confidenceScore)
- [Source: codebase `common/types/risk.type.ts#RiskDecision`] — Current `RiskDecision` interface
- [Source: codebase `core/trading-engine.service.ts#executeCycle`] — `maxPositionSizeUsd` → `recommendedPositionSizeUsd` flow
- [Source: Story 9.2 dev notes] — Extraction pattern, async validatePosition, FinancialDecimal usage, test value design lesson

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Existing test asserting "cluster info extraction" log message updated to "pair context extraction" after rename

### Completion Notes List

- All 5 tasks implemented per story spec with TDD approach
- 14 new tests added to `risk-manager.service.spec.ts` (confidence adjustment scenarios)
- 2 new tests added to `contract-pair-loader.service.spec.ts` (confidenceScore propagation)
- `extractClusterInfo()` renamed to `extractPairContext()` — 1 existing test assertion updated for new log message
- Extraction hoisted before confidence adjustment; `pairContext` shared with cluster enforcement block (no duplicate extraction)
- `toPairConfig()` for YAML pairs explicitly sets `confidenceScore: null` (review fix — data model consistency)
- Confidence observability fields added to all post-extraction rejection paths, not just approved path (review fix)
- Lad MCP code review completed — 2 genuine findings fixed, 3 out-of-scope items noted below
- Adversarial code review completed — 3 MEDIUM issues fixed:
  - M1: 0% confidence test now verifies `approved` status and `confidenceScore: 0` propagation
  - M2: Added test verifying confidence observability fields on rejection paths (max open pairs)
  - M3: Added test verifying YAML pairs set `confidenceScore: null`
- Final test count: 1965 unit tests passing (112 files), 0 regressions

### Follow-up Items (out of scope)

- `processOverride()` uses unadjusted base size — if overrides should preserve confidence adjustment, this needs a separate story
- `reserveBudget()` cap uses unadjusted base — callers pass confidence-adjusted `recommendedPositionSizeUsd` from `validatePosition()`, so actual reservation is correct, but the safety cap could be tightened in a future story

### File List

- `src/modules/contract-matching/types/contract-pair-config.type.ts` — added `confidenceScore?: number | null`
- `src/modules/contract-matching/contract-pair-loader.service.ts` — added `confidenceScore` mapping in `dbMatchToConfig()` and `toPairConfig()`
- `src/modules/risk-management/risk-manager.service.ts` — renamed `extractClusterInfo` → `extractPairContext`, hoisted extraction, added confidence adjustment + observability fields
- `src/common/types/risk.type.ts` — added `confidenceScore` and `confidenceAdjustedSizeUsd` to `RiskDecision`
- `src/modules/risk-management/risk-manager.service.spec.ts` — 15 new confidence tests + 1 assertion update (review: +1 rejection-path observability test, strengthened 0% test)
- `src/modules/contract-matching/contract-pair-loader.service.spec.ts` — 3 new confidenceScore tests (review: +1 YAML null test)
