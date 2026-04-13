# Story 10-96.8: Edge-Evaporation Re-Entry Cooldown & Negative-Edge Immediate Exit

Status: done

## Story

As an operator,
I want a specific re-entry cooldown after edge_evaporation exits and an immediate exit gate when the arbitrage edge has flipped negative,
so that the engine stops repeatedly entering proven-losing pairs and doesn't hold positions where the arb has reversed.

## Context

Paper trading analysis (Apr 14-15, 38h run, 19 positions) revealed two behavioral defects:

1. **Repeat-entry losses:** KC/DET entered 4 times at ~80-90 min intervals, all exiting via `edge_evaporation`, losing $61 total. The generic `pairCooldownMinutes` (60 min) expired between entries, allowing re-entry into a pair that consistently evaporates. Story 10-96-3 added a 24h cooldown for TIME_DECAY exits, but EDGE_EVAPORATION exits (62.5% of all exits) only fall through to the generic cooldown.

2. **Negative-edge position stuck open:** Position `0afa4945` (Valorant TH/KC) has a recalculated edge of -24.9% with unrealized PnL of -$52.75. The dollar-PnL edge evaporation threshold (-$67) hasn't triggered because the position size is small. When the arbitrage has fully reversed (negative edge), the system should exit immediately regardless of the PnL dollar threshold.

**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16-paper-trading-profitability-fix.md`

## Acceptance Criteria

1. **AC1 — Edge-evaporation cooldown:** **Given** `edgeEvaporationCooldownHours` config setting (default 4), **When** a position exits with criterion `EDGE_EVAPORATION`, **Then** the pair is blocked from re-entry for `edgeEvaporationCooldownHours`. **Given** a position exits with a criterion other than EDGE_EVAPORATION or TIME_DECAY, **When** cooldown is checked, **Then** only the generic `pairCooldownMinutes` applies. **Given** the pair-concentration-filter already queries `getLatestTimeDecayExitByPairIds`, **When** this story is implemented, **Then** a parallel `getLatestEdgeEvaporationExitByPairIds` repository method is added **And** the filter checks both cooldowns (TIME_DECAY and EDGE_EVAPORATION) for each pair.

2. **AC2 — Negative-edge immediate exit:** **Given** an open position being evaluated by the threshold evaluator, **When** `recalculatedEdge < 0` (arbitrage has reversed), **Then** an EDGE_EVAPORATION exit is triggered immediately, regardless of the dollar PnL threshold **And** the exit detail includes `"Edge reversed: recalculated edge negative"`. **Given** `recalculatedEdge >= 0`, **When** the evaluator runs, **Then** the existing dollar-PnL-based edge evaporation logic applies (no change).

## Tasks / Subtasks

- [x] Task 1: Config layer — add `edgeEvaporationCooldownHours` end-to-end (AC: #1)
  - [x] 1.1 Add column to `prisma/schema.prisma` and create migration
  - [x] 1.2 Add to `config-defaults.ts`, `env.schema.ts`, `effective-config.types.ts`
  - [x] 1.3 Add to `engine-config.repository.ts` `buildEffectiveConfig()` resolver
  - [x] 1.4 Add to `settings-metadata.ts` and `update-settings.dto.ts`
  - [x] 1.5 TDD: Add `env.schema.spec.ts` tests (default, accepts 0, rejects negative)
- [x] Task 2: Repository method — `getLatestEdgeEvaporationExitByPairIds` (AC: #1)
  - [x] 2.1 TDD: Write failing tests in `position.repository.spec.ts` (returns correct map, excludes non-edge-evap exits, empty map for no exits, empty pairIds guard, isPaper passthrough)
  - [x] 2.2 Implement `getLatestEdgeEvaporationExitByPairIds` in `position.repository.ts`
  - [x] 2.3 Verify tests pass
- [x] Task 3: Pair concentration filter — edge evaporation cooldown (AC: #1)
  - [x] 3.1 TDD: Write failing tests in `pair-concentration-filter.service.spec.ts` (block within cooldown, allow after expiry, disabled when config=0, independent from generic + TIME_DECAY cooldowns, TIME_DECAY+EDGE_EVAP overlap priority, correct event emission with reason and threshold)
  - [x] 3.2 Add `getLatestEdgeEvaporationExitByPairIds` to mock interface and `beforeEach` mock setup
  - [x] 3.3 Integrate into `pair-concentration-filter.service.ts`: read config, fetch repository, add filter check, update `emitFilteredEvent` signature and configValue ternary
  - [x] 3.4 Verify tests pass
- [x] Task 4: Negative-edge gate in threshold evaluator (AC: #2)
  - [x] 4.1 TDD: Write failing tests in `threshold-evaluator.service.spec.ts` for model mode (negative edge → triggers `edge_evaporation` with detail `'Edge reversed: recalculated edge negative'` and proximity 1)
  - [x] 4.2 Implement in `evaluateEdgeEvaporation()`: add negative-edge check before existing PnL threshold logic
  - [x] 4.3 TDD: Write failing tests for fixed mode (negative edge → triggers `edge_evaporation`, percentage SL still has priority when both fire, edge=0 does NOT trigger, positive edge does NOT trigger)
  - [x] 4.4 Implement in `evaluateFixed()`: add negative-edge gate after percentage stop-loss check
  - [x] 4.5 TDD: Write shadow mode test (negative edge → both fixed primary and shadowModelResult trigger `edge_evaporation`)
  - [x] 4.6 Verify all threshold evaluator tests pass
- [x] Task 5: Env files + lint + test (AC: all)
  - [x] 5.1 Add `EDGE_EVAPORATION_COOLDOWN_HOURS=4` to `.env.development` and `.env.example`
  - [x] 5.2 Run `pnpm lint && pnpm test` — 4044 tests pass (+22 from baseline), zero regressions

## Dev Notes

### Architecture Overview

This story has two independent parts that share the config layer:

**Part A (AC1) — Re-entry cooldown:** Replicates the TIME_DECAY cooldown pattern from story 10-96-3. The pair-concentration-filter already checks `getLatestTimeDecayExitByPairIds`; we add a parallel check for `getLatestEdgeEvaporationExitByPairIds` with its own configurable cooldown period.

**Part B (AC2) — Negative-edge exit gate:** Adds a short-circuit in the threshold evaluator that fires when `currentEdge < 0` (the arbitrage has reversed), producing an EDGE_EVAPORATION exit immediately. This must work in all three exit modes (fixed, model, shadow).

### Config Layer — End-to-End Pattern (Replicating `timeDecayCooldownHours`)

Follow the exact pattern established by `timeDecayCooldownHours` in story 10-96-3. Every step has a 1:1 precedent:

**1. Prisma Schema** — `prisma/schema.prisma:159`

Add after `timeDecayCooldownHours` (line 159):
```prisma
edgeEvaporationCooldownHours Int? @map("edge_evaporation_cooldown_hours")
```

Create migration: `cd pm-arbitrage-engine && npx prisma migrate dev --name add_edge_evaporation_cooldown_hours --create-only`, then `npx prisma migrate dev` to apply. Run `npx prisma generate` afterward.

**2. Config Defaults** — `src/common/config/config-defaults.ts:336`

Add after `timeDecayCooldownHours` block (after line 336):
```typescript
edgeEvaporationCooldownHours: {
  envKey: 'EDGE_EVAPORATION_COOLDOWN_HOURS',
  defaultValue: 4,
},
```

**3. Env Schema** — `src/common/config/env.schema.ts:292`

Add after `TIME_DECAY_COOLDOWN_HOURS` (after line 292):
```typescript
EDGE_EVAPORATION_COOLDOWN_HOURS: z.coerce.number().int().min(0).default(4),
```

**4. Effective Config Types** — `src/common/config/effective-config.types.ts:128`

Add after `timeDecayCooldownHours: number;` (after line 128):
```typescript
edgeEvaporationCooldownHours: number;
```

**5. Engine Config Repository** — `src/persistence/repositories/engine-config.repository.ts:181`

Add after `timeDecayCooldownHours` resolver (after line 181):
```typescript
edgeEvaporationCooldownHours: resolve('edgeEvaporationCooldownHours') as number,
```

**6. Settings Metadata** — `src/common/config/settings-metadata.ts:375`

Add after `timeDecayCooldownHours` block (after line 375):
```typescript
edgeEvaporationCooldownHours: {
  group: SettingsGroup.RiskManagement,
  label: 'EDGE_EVAPORATION Cooldown',
  description:
    'Hours to block re-entry after an EDGE_EVAPORATION exit. 0 = disabled (generic cooldown only).',
  type: 'integer',
  envDefault: CONFIG_DEFAULTS.edgeEvaporationCooldownHours.defaultValue,
  min: 0,
  unit: 'h',
},
```

**7. Update Settings DTO** — `src/dashboard/dto/update-settings.dto.ts:178`

Add after `timeDecayCooldownHours?` field (after line 178):
```typescript
@IsOptional()
@IsInt()
@Min(0)
edgeEvaporationCooldownHours?: number;
```

### Repository Method — `getLatestEdgeEvaporationExitByPairIds`

**File:** `src/persistence/repositories/position.repository.ts` — add after `getLatestTimeDecayExitByPairIds` (after line 345)

Mirror the TIME_DECAY method exactly but with `exit_criterion = 'edge_evaporation'`:

```typescript
/**
 * Batch-fetch latest EDGE_EVAPORATION exit timestamp per pair, mode-scoped.
 * Returns Map<pairId, Date> where Date is updatedAt (close time) of the most recent
 * closed position with exit_criterion = 'edge_evaporation'.
 * Pairs with no such exits are absent from the map.
 */
async getLatestEdgeEvaporationExitByPairIds(
  pairIds: string[],
  isPaper: boolean,
): Promise<Map<string, Date>> {
  if (pairIds.length === 0) return new Map();
  const rows = await this.prisma.$queryRaw<
    { pair_id: string; latest_exit: Date }[]
  >`
    SELECT pair_id, MAX(updated_at) AS latest_exit
    FROM open_positions
    WHERE pair_id IN (${Prisma.join(pairIds)})
      AND status = 'CLOSED'
      AND exit_criterion = 'edge_evaporation'
      AND is_paper = ${isPaper}
    GROUP BY pair_id -- MODE-FILTERED
  `;
  const map = new Map<string, Date>();
  for (const row of rows) {
    map.set(row.pair_id, row.latest_exit);
  }
  return map;
}
```

Key difference from TIME_DECAY method: only `'edge_evaporation'` (not dual-criterion like `('time_decay', 'time_based')`), because `edge_evaporation` is the same criterion name in both fixed and model modes. The `-- MODE-FILTERED` comment is required per CLAUDE.md raw SQL rules.

### Pair Concentration Filter Integration

**File:** `src/modules/arbitrage-detection/pair-concentration-filter.service.ts`

The pattern is identical to the TIME_DECAY integration. Three touch points:

**1. Read config** (after line 37):
```typescript
const edgeEvapCooldownHours = config.edgeEvaporationCooldownHours;
```

**2. Fetch repository data** (add to Promise.all, lines 56-68):
Add a fourth item to the Promise.all array:
```typescript
edgeEvapCooldownHours > 0
  ? this.positionRepository.getLatestEdgeEvaporationExitByPairIds(pairIds, isPaper)
  : Promise.resolve(new Map<string, Date>()),
```
Update the destructuring to capture it as `edgeEvapExits`.

**3. Add filter check** (after the TIME_DECAY check, line 130):
```typescript
// 1c. EDGE_EVAPORATION-specific cooldown check
if (!reason && edgeEvapCooldownHours > 0) {
  const lastEdgeEvapExit = edgeEvapExits.get(pairId);
  if (
    lastEdgeEvapExit &&
    now - lastEdgeEvapExit.getTime() < edgeEvapCooldownHours * 3_600_000
  ) {
    reason = 'edge_evap_cooldown_active';
  }
}
```

**4. Update `emitFilteredEvent` method** (lines 175-211):

Update signature to accept `edgeEvapCooldownHours: number` as a new parameter (7th param):
```typescript
private emitFilteredEvent(
  opportunity: EnrichedOpportunity,
  reason: string,
  cooldownMinutes: number,
  timeDecayCooldownHours: number,
  maxConcurrent: number,
  diversityThreshold: number,
  edgeEvapCooldownHours: number,  // NEW
): void {
```

Update the `configValue` ternary chain (lines 187-194) to include the new reason:
```typescript
const configValue =
  reason === 'pair_cooldown_active'
    ? cooldownMinutes
    : reason === 'time_decay_cooldown_active'
      ? timeDecayCooldownHours
      : reason === 'edge_evap_cooldown_active'
        ? edgeEvapCooldownHours
        : reason === 'pair_max_concurrent_reached'
          ? maxConcurrent
          : diversityThreshold;
```

**5. Update the call site** in the for-loop (lines 157-164):
Pass the new `edgeEvapCooldownHours` arg to `emitFilteredEvent`:
```typescript
this.emitFilteredEvent(
  opportunity,
  reason,
  cooldownMinutes,
  timeDecayCooldownHours,
  maxConcurrent,
  diversityThreshold,
  edgeEvapCooldownHours,  // NEW
);
```

### Negative-Edge Gate in Threshold Evaluator

**File:** `src/modules/exit-management/threshold-evaluator.service.ts`

Two insertion points — one for model/shadow mode, one for fixed mode:

**Model/Shadow mode — `evaluateEdgeEvaporation()` (line 305-332):**

Add at the top of the method, before the existing PnL threshold logic:
```typescript
// Negative-edge gate (10-96-8): if arb has reversed, exit immediately
if (common.currentEdge.isNeg()) {
  return {
    criterion: 'edge_evaporation',
    proximity: DECIMAL_ONE,
    triggered: true,
    detail: 'Edge reversed: recalculated edge negative',
  };
}
```

When `currentEdge < 0`, the arbitrage has fully reversed. The existing dollar-PnL threshold may not trigger if the position is small, but the position is guaranteed to be losing with no path to recovery. Trigger immediately with proximity 1.0.

**Fixed mode — `evaluateFixed()` (lines 203-286):**

Add after the percentage stop-loss check (after line 229) and before the edge-relative stop-loss (line 231):
```typescript
// Negative-edge gate (10-96-8): edge has reversed — exit immediately
if (currentEdge.isNeg()) {
  return {
    triggered: true,
    type: 'edge_evaporation',
    currentEdge,
    currentPnl,
    capturedEdgePercent: common.capturedEdgePercent,
    dataSource: params.dataSource,
  };
}
```

**Priority in fixed mode:** Percentage stop-loss (circuit breaker, -20% of position) still takes priority — if a position is at -25% PnL AND has negative edge, the percentage SL fires first. The negative-edge gate fires second, ahead of the dollar-based edge-relative SL, TP, and time-based exits.

**Why `isNeg()` not `isNegative()`:** `decimal.js` uses `isNeg()` — verify via IDE or docs. `isNeg()` returns true when the value is strictly less than zero (not for zero).

### Test Pattern Reference

**Env Schema Tests** — `src/common/config/env.schema.spec.ts` (after line 253)

Follow the TIME_DECAY_COOLDOWN_HOURS pattern (lines 242-260):
```typescript
// Story 10-96-8: EDGE_EVAPORATION_COOLDOWN_HOURS env var
it('[P1] EDGE_EVAPORATION_COOLDOWN_HOURS defaults to 4', () => {
  const result = envSchema.parse(validEnv);
  expect(result.EDGE_EVAPORATION_COOLDOWN_HOURS).toBe(4);
});

it('[P1] EDGE_EVAPORATION_COOLDOWN_HOURS accepts 0 (disabled)', () => {
  const result = envSchema.parse({
    ...validEnv,
    EDGE_EVAPORATION_COOLDOWN_HOURS: '0',
  });
  expect(result.EDGE_EVAPORATION_COOLDOWN_HOURS).toBe(0);
});

it('[P1] EDGE_EVAPORATION_COOLDOWN_HOURS rejects negative value', () => {
  expect(() =>
    envSchema.parse({ ...validEnv, EDGE_EVAPORATION_COOLDOWN_HOURS: '-1' }),
  ).toThrow();
});
```

**Repository Tests** — `src/persistence/repositories/position.repository.spec.ts` (after line 640)

Mirror the `getLatestTimeDecayExitByPairIds` test block (lines 596-640):
- Correct pair→date map for edge_evaporation exits
- Excludes non-edge_evaporation exits
- Empty map for no matching exits
- Empty pairIds guard (early return, no query)
- isPaper passthrough (verify `$queryRaw` called with correct params)

**Pair Concentration Filter Tests** — `src/modules/arbitrage-detection/pair-concentration-filter.service.spec.ts`

**Mock setup changes** (in `beforeEach`):
1. Add to the `positionRepo` mock type interface (line ~77): `getLatestEdgeEvaporationExitByPairIds: ReturnType<typeof vi.fn>;`
2. Add to `positionRepo` mock initialization (after line 88): `getLatestEdgeEvaporationExitByPairIds: vi.fn().mockResolvedValue(new Map()),`
3. Add to `mockEffectiveConfig` (after line 94): `edgeEvaporationCooldownHours: 4,`

Add a new `describe('EDGE_EVAPORATION cooldown')` block after the TIME_DECAY block (after line 373). Mirror the TIME_DECAY tests but with:
- `edgeEvaporationCooldownHours: 4` in mockEffectiveConfig
- `getLatestEdgeEvaporationExitByPairIds` mock on positionRepo
- `reason: 'edge_evap_cooldown_active'` in assertions
- Test independence from both generic cooldown AND TIME_DECAY cooldown
- Test disabling via `edgeEvaporationCooldownHours = 0`
- Event emission with correct threshold value (4)
- **Cooldown overlap test:** When both TIME_DECAY (12h ago, within 24h) and EDGE_EVAPORATION (2h ago, within 4h) cooldowns are active, TIME_DECAY check runs first (sequential order: generic → TIME_DECAY → EDGE_EVAPORATION) and its reason wins
- **Cross-cooldown test:** When TIME_DECAY cooldown has expired but EDGE_EVAPORATION is still active, `edge_evap_cooldown_active` is the reported reason

**Threshold Evaluator Tests** — `src/modules/exit-management/threshold-evaluator.service.spec.ts`

Add a new `describe('negative-edge immediate exit (Story 10-96-8)')` block. Test cases:

*Model mode:*
- `currentEdge < 0` → triggers `edge_evaporation` with `detail: 'Edge reversed: recalculated edge negative'` and `proximity: 1`
- `currentEdge = 0` → does NOT trigger the negative-edge gate (existing logic applies)
- `currentEdge > 0` → does NOT trigger the negative-edge gate

*Fixed mode:*
- `currentEdge < 0` → triggers `edge_evaporation` with type `'edge_evaporation'`
- Percentage stop-loss priority: when both `-20% PnL AND negative edge`, percentage SL fires (type = `'stop_loss'`)
- `currentEdge = 0` → does NOT trigger (existing fixed-mode logic applies)

*Shadow mode:*
- `currentEdge < 0` → both the primary result (fixed) AND `shadowModelResult` trigger `edge_evaporation`. Shadow mode runs `evaluateFixed()` as primary and `evaluateModelDriven()` as shadow, so both code paths are exercised:
```typescript
it('should trigger edge_evaporation in both fixed and shadow model results', () => {
  const input = makeInput({ exitMode: 'shadow', /* prices that produce negative edge */ });
  const result = service.evaluate(input);
  expect(result.triggered).toBe(true);
  expect(result.type).toBe('edge_evaporation');
  expect(result.shadowModelResult?.triggered).toBe(true);
  expect(result.shadowModelResult?.type).toBe('edge_evaporation');
});
```

To create a test with negative edge: set prices so that `currentPnl / legSize < 0`. Example: entry prices that diverge from current prices in the wrong direction (buy price goes up, sell price goes down). Use `makeInput()` helper with appropriate price overrides.

**Note on `detail` field:** `ThresholdEvalResult` (fixed mode) has no `detail` field — only `CriterionResult` (model mode) does. The detail `'Edge reversed: recalculated edge negative'` appears in model/shadow mode via `CriterionResult.detail`. In fixed mode, the exit type `'edge_evaporation'` conveys the semantic meaning; the exit monitor constructs audit event details from the type.

**Note on `DECIMAL_ONE` / `DECIMAL_ZERO`:** These are file-level constants in `threshold-evaluator.service.ts` (lines 119-120). No import needed — they're already in scope.

### Files Modified Summary

- Modified: `prisma/schema.prisma` — new `edgeEvaporationCooldownHours` column on EngineConfig
- New: `prisma/migrations/<timestamp>_add_edge_evaporation_cooldown_hours/migration.sql`
- Modified: `src/common/config/config-defaults.ts` — new default entry
- Modified: `src/common/config/env.schema.ts` — new env var
- Modified: `src/common/config/env.schema.spec.ts` — 3 new tests
- Modified: `src/common/config/effective-config.types.ts` — new field on interface
- Modified: `src/common/config/settings-metadata.ts` — new metadata entry
- Modified: `src/persistence/repositories/engine-config.repository.ts` — new resolver line
- Modified: `src/persistence/repositories/position.repository.ts` — new method
- Modified: `src/persistence/repositories/position.repository.spec.ts` — new test block
- Modified: `src/modules/arbitrage-detection/pair-concentration-filter.service.ts` — new cooldown branch
- Modified: `src/modules/arbitrage-detection/pair-concentration-filter.service.spec.ts` — new test block
- Modified: `src/modules/exit-management/threshold-evaluator.service.ts` — negative-edge gate (2 locations)
- Modified: `src/modules/exit-management/threshold-evaluator.service.spec.ts` — new test block
- Modified: `src/dashboard/dto/update-settings.dto.ts` — new DTO field
- Modified: `.env.development` — new env var
- Modified: `.env.example` — new env var

### What NOT To Do

- Do NOT modify `config-accessor.service.ts` — it uses `EffectiveConfig` type, which auto-resolves new fields
- Do NOT modify `exit-criteria.types.ts` — `edge_evaporation` is already a valid `ExitCriterion`
- Do NOT add a new ExitCriterion type — the negative-edge gate reuses `'edge_evaporation'` as its exit type
- Do NOT modify the exit-monitor service — it already passes `currentEdge` through from ThresholdEvalResult
- Do NOT modify `seed-config.ts` — the config layer handles new nullable fields automatically (NULL → env fallback → code default)
- Do NOT change `EXIT_CRITERION_PRIORITY` — `edge_evaporation` already has priority 2
- Do NOT use `configService.get<>()` — use ConfigAccessor
- Do NOT use native JS arithmetic on monetary values — use `decimal.js`

### Previous Story Intelligence (10-96-7)

- **Test baseline:** 4022 tests pass, 1 pre-existing e2e failure (unchanged)
- **Pattern:** TDD red-green cycle per unit of behavior
- **Code review:** 3-layer adversarial (Blind Hunter + Edge Case Hunter + Acceptance Auditor)
- **Key learning from 10-96-7:** Seed script is idempotent (only sets NULLs). New nullable column + code default means no migration SQL UPDATE needed for the config value — NULL falls through to env fallback → code default of 4
- **Key learning from 10-96-4:** After adding a new config field, verify that stale test fixtures in `seed-config.spec.ts` don't need updating (they will if there's a `defaultEnvValues` mock that enumerates all CONFIG_DEFAULTS keys)
- **Key learning from 10-96-3:** The TIME_DECAY cooldown was added with this exact pattern. Replicate it 1:1 for EDGE_EVAPORATION. The `pair-concentration-filter.service.ts` is 212 lines — well within the 300-line service limit after adding ~15 lines

### Git Intelligence

Recent commits follow `feat:` prefix for features. This story should use:
```
feat: add edge-evaporation cooldown and negative-edge immediate exit (10-96-8)
```

### Project Structure Notes

- All changes within `pm-arbitrage-engine/` — separate git repo from root
- Cooldown filter lives in `src/modules/arbitrage-detection/` (detection pipeline)
- Threshold evaluator lives in `src/modules/exit-management/` (exit pipeline)
- Config files live in `src/common/config/` (shared config layer)
- Repository lives in `src/persistence/repositories/` (data access layer)
- Module dependency rules: `arbitrage-detection/` → `persistence/` (via repository DI) is allowed
- The `pair-concentration-filter.interface.ts` in `common/interfaces/` does NOT need changes — the interface contract (`filterOpportunities(opportunities, isPaper)`) is unchanged

### Verification After Implementation

AC2 manual verification: with the engine running in paper mode, any position whose recalculated edge goes negative should be immediately exited with `exit_criterion = 'edge_evaporation'` and detail containing "Edge reversed". The stuck position `0afa4945` (if still open) should exit on the first evaluation cycle after deploy.

AC1 manual verification: after a position exits via `edge_evaporation`, query:
```sql
SELECT pair_id, updated_at FROM open_positions
WHERE exit_criterion = 'edge_evaporation' AND status = 'CLOSED'
ORDER BY updated_at DESC LIMIT 5;
```
Then verify no new entry for that pair_id appears within 4 hours.

### References

- [Source: sprint-change-proposal-2026-04-16-paper-trading-profitability-fix.md#Section-4-Story-10-96-8] — Full story spec, root cause, evidence
- [Source: epics.md#Story-10-96-8] — Epic-level AC (lines 4008-4039)
- [Source: 10-96-7-db-config-migration-calibrated-defaults.md] — Previous story intelligence
- [Source: sprint-status.yaml#line-310-311] — 10-96-3 TIME_DECAY cooldown pattern reference
- [Source: CLAUDE.md#Domain-Rules] — "Minimum threshold: 5% net"
- [Source: CLAUDE.md#Testing] — Co-located specs, assertion depth, event wiring verification
- [Source: CLAUDE.md#Paper-Live-Mode-Boundary] — isPaper required on all repository queries
- [Source: CLAUDE.md#Financial-Math] — decimal.js for all monetary calculations

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1: Config layer added end-to-end. Prisma migration `20260416102035_add_edge_evaporation_cooldown_hours` created and applied. All 7 config touch points updated. 3 env.schema tests added (default=4, accepts 0, rejects negative). Seed-config tests confirmed green (12/12).
- Task 2: `getLatestEdgeEvaporationExitByPairIds` repository method implemented mirroring TIME_DECAY pattern with `exit_criterion = 'edge_evaporation'`. 5 tests added (52/52 pass).
- Task 3: Pair concentration filter integrated with edge evaporation cooldown. Added to Promise.all, filter chain (1c check), emitFilteredEvent signature, configValue ternary. 7 tests added (34/34 pass).
- Task 4: Negative-edge gate added in both `evaluateEdgeEvaporation()` (model/shadow) and `evaluateFixed()` (after pct SL, before edge-relative SL). In fixed mode, the negative-edge gate effectively supersedes edge-relative SL for all negative-edge positions — pct SL still fires first for deep losses. Existing tests updated: default `makeInput` prices adjusted to produce positive edge, tests that used negative-edge prices updated to use pct SL prices or expect `edge_evaporation`. 8 new tests (model/fixed/shadow modes). Also updated `five-criteria-evaluator.spec.ts` (3 tests adjusted).
- Task 5: Env vars added to `.env.development` and `.env.example`. `settings.service.spec.ts` count updated (101→102). Lint clean for all modified files. 4044 tests pass (+22 from 4022 baseline), 1 pre-existing e2e failure unchanged.

### File List

- Modified: `prisma/schema.prisma` — new `edgeEvaporationCooldownHours` column on EngineConfig
- New: `prisma/migrations/20260416102035_add_edge_evaporation_cooldown_hours/migration.sql`
- Modified: `src/common/config/config-defaults.ts` — new default entry (envKey, defaultValue: 4)
- Modified: `src/common/config/env.schema.ts` — new EDGE_EVAPORATION_COOLDOWN_HOURS env var
- Modified: `src/common/config/env.schema.spec.ts` — 3 new tests
- Modified: `src/common/config/effective-config.types.ts` — new field on EffectiveConfig interface
- Modified: `src/common/config/settings-metadata.ts` — new metadata entry (RiskManagement group)
- Modified: `src/persistence/repositories/engine-config.repository.ts` — new resolver line
- Modified: `src/persistence/repositories/position.repository.ts` — new `getLatestEdgeEvaporationExitByPairIds` method
- Modified: `src/persistence/repositories/position.repository.spec.ts` — 5 new tests
- Modified: `src/modules/arbitrage-detection/pair-concentration-filter.service.ts` — new cooldown branch, updated emitFilteredEvent
- Modified: `src/modules/arbitrage-detection/pair-concentration-filter.service.spec.ts` — 7 new tests, mock updates
- Modified: `src/modules/exit-management/threshold-evaluator.service.ts` — negative-edge gate (2 locations: evaluateEdgeEvaporation, evaluateFixed)
- Modified: `src/modules/exit-management/threshold-evaluator.service.spec.ts` — 8 new tests, existing test adjustments for negative-edge gate
- Modified: `src/modules/exit-management/five-criteria-evaluator.spec.ts` — 3 test adjustments for negative-edge gate
- Modified: `src/dashboard/dto/update-settings.dto.ts` — new DTO field
- Modified: `src/dashboard/settings.service.spec.ts` — settings count 101→102
- Modified: `.env.development` — new EDGE_EVAPORATION_COOLDOWN_HOURS=4
- Modified: `.env.example` — new EDGE_EVAPORATION_COOLDOWN_HOURS=4
