# Story 4.5.4: Technical Debt Consolidation

Status: done

## Story

As an operator,
I want all known technical debt and framework gotchas centralized in dedicated files,
so that accumulated knowledge from Epics 2-4 is discoverable and actionable.

## Acceptance Criteria

### AC1: Technical Debt Registry
**Given** technical debt and gotchas are currently scattered across individual story dev notes
**When** consolidation is complete
**Then** `technical-debt.md` exists in the engine repo root with all known debt items from Epics 2-4, each with: description, priority, target epic, and source story

### AC2: Gotchas Document
**Given** framework-specific gotchas have been discovered across Epics 1-4
**When** consolidation is complete
**Then** `docs/gotchas.md` exists with framework-specific gotchas including: `plainToInstance` defaults, `OnModuleInit` ordering, `ConfigService.get` returning strings, circular import resolution pattern, fire-once event pattern, and `FinancialDecimal` / `Decimal` precision handling
**And** each gotcha has a code example showing the problem and solution

### AC3: No Code Modifications
**Given** this is a documentation-only story
**When** all changes are complete
**Then** no existing tests or source code are modified
**And** `pnpm test` passes with the same test count as before (498 tests — inherited from Story 4.5.3 completion; verify with `pnpm test` before creating any files)
**And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Create `technical-debt.md` in engine repo root (AC: #1)
  - [x] 1.1 Scan all story files from Epics 1-4 Dev Notes sections for debt items
  - [x] 1.2 Scan codebase for TODO/FIXME markers
  - [x] 1.3 Write `technical-debt.md` with table: description, priority, target epic, source story
- [x] Task 2: Create `docs/gotchas.md` (AC: #2)
  - [x] 2.1 Create `docs/` directory if it doesn't exist
  - [x] 2.2 Write each gotcha with problem description and code example (problem + solution)
- [x] Task 3: Verify no regressions (AC: #3)
  - [x] 3.1 Run `pnpm test` — 498 tests pass
  - [x] 3.2 Run `pnpm lint` — zero errors

## Dev Notes

### This is a documentation-only story

No TypeScript files, no test files, no config files are created or modified. Only two markdown files are produced:
1. `pm-arbitrage-engine/technical-debt.md`
2. `pm-arbitrage-engine/docs/gotchas.md`

### Technical Debt Items to Include

These are the known debt items gathered from all story dev notes, retros, and codebase analysis:

| # | Description | Priority | Target | Source |
|---|-------------|----------|--------|--------|
| 1 | **Kalshi order book normalization duplicated in 3 locations** — `order-book-normalizer.service.ts`, `kalshi.connector.ts`, `kalshi-websocket.client.ts` all repeat the cents-to-decimal + NO-to-YES transformation. Extract to a shared utility in `common/utils/`. Verify duplication still present before including. | High | Epic 5 | Codebase scan (Stories 1-4, 2-2) |
| 2 | **TODO: Story 5.1 — replace with IExecutionEngine.execute() call** in `execution-queue.service.ts` line 53 | Medium | Epic 5 (Story 5.1) | `execution-queue.service.ts` |
| 3 | **TODO(Epic 5): Add gas estimation for on-chain settlement** in `polymarket.connector.ts` line 312 | Medium | Epic 5 | `polymarket.connector.ts` |
| 4 | **Error code numbering deviates from PRD** — PRD says `3001 = Daily Loss Limit Exceeded`, implementation uses `3001 = Position Size Exceeded`, `3003 = Daily Loss Limit Breached`. Shipped with 397+ tests, so follow implementation numbering going forward. Document deviation. | Low | Post-Epic 5 reconciliation | Story 4-2 Dev Notes |
| 5 | **Polymarket order book transformation** has minor duplication between `polymarket-websocket.client.ts` and `polymarket.connector.ts`. Less critical than Kalshi (no inversion logic). | Low | Monitor | Codebase scan |
| 6 | **`forwardRef()` used for ConnectorModule ↔ DataIngestionModule circular dependency** — works but is a code smell. Consider restructuring module boundaries if it grows. | Low | Monitor | Story 2-2 Dev Notes |

### Gotchas to Document (with code examples)

Each gotcha below must include a "Problem" code block and a "Solution" code block.

#### 1. `plainToInstance()` Does Not Apply TypeScript Defaults

**Source:** Story 3-1 Dev Notes

**Problem:**
```typescript
class ContractPairDto {
  primaryLeg?: PrimaryLeg = PrimaryLeg.KALSHI; // TS default — IGNORED by plainToInstance
}
const dto = plainToInstance(ContractPairDto, parsed);
console.log(dto.primaryLeg); // undefined, NOT PrimaryLeg.KALSHI
```

**Solution:**
```typescript
// Explicitly default in the transform step, not the DTO
const dto = plainToInstance(ContractPairDto, parsed);
dto.primaryLeg = dto.primaryLeg ?? PrimaryLeg.KALSHI;
// Do NOT use exposeDefaultValues: true — it masks missing-field bugs in future DTOs
```

#### 2. `OnModuleInit` Execution Order Not Guaranteed

**Source:** Story 3-4 Dev Notes, Epic 3 Retro

**Problem:**
```typescript
// ContractMatchSyncService depends on ContractPairLoaderService having loaded pairs
// But NestJS does NOT guarantee OnModuleInit order between providers in the same module
@Injectable()
export class ContractMatchSyncService implements OnModuleInit {
  async onModuleInit() {
    const pairs = this.pairLoader.getActivePairs(); // May be empty!
  }
}
```

**Solution:**
```typescript
async onModuleInit() {
  const pairs = this.pairLoader.getActivePairs();
  if (pairs.length === 0) {
    this.logger.warn('No active pairs loaded yet — skipping initial seed');
    return; // Defensive check — don't crash, just skip
  }
  await this.seedMatches(pairs);
}
```

#### 3. `ConfigService.get()` Returns Strings for Env Vars

**Source:** Story 4-1, 4-2 Dev Notes

**Problem:**
```typescript
// process.env values are ALWAYS strings, even with <number> generic
const maxPct = this.configService.get<number>('RISK_MAX_POSITION_PCT', 0.03);
// maxPct is actually string "0.03", not number 0.03
// Arithmetic silently produces wrong results: "0.03" * 100 = 3, but "0.03" + 1 = "0.031"
```

**Solution:**
```typescript
const maxPctRaw = this.configService.get<string | number>('RISK_MAX_POSITION_PCT', 0.03);
const maxPct = Number(maxPctRaw);
// Always wrap in Number() when expecting numeric values from env
```

#### 4. Circular Import Resolution via Constants Extraction

**Source:** Story 4-3 Debug Log, Story 2-2 Dev Notes

**Problem:**
```typescript
// risk-management.module.ts imports RiskController which imports RISK_MANAGER_TOKEN
// from risk-management.module.ts → circular!
// Also: ConnectorModule ↔ DataIngestionModule circular dependency
```

**Solution:**
```typescript
// Extract DI tokens to a separate constants file
// risk-management.constants.ts
export const RISK_MANAGER_TOKEN = 'RISK_MANAGER_TOKEN';

// For module-level circular deps, use forwardRef():
@Module({
  imports: [forwardRef(() => DataIngestionModule)],
})
export class ConnectorModule {}
```

#### 5. Fire-Once Event Pattern for Warning Emissions

**Source:** Story 4-2 AC2

**Problem:**
```typescript
// updateDailyPnl() called on every trade — emits LimitApproachedEvent every time
// losses are in the 80-100% range, flooding logs and Telegram
updateDailyPnl(pnl: Decimal) {
  if (this.dailyLossRatio >= 0.8) {
    this.eventEmitter.emit('risk.limit.approached', event); // fires repeatedly!
  }
}
```

**Solution:**
```typescript
private dailyLossApproachEmitted = false;

updateDailyPnl(pnl: Decimal) {
  if (this.dailyLossRatio >= 0.8 && !this.dailyLossApproachEmitted) {
    this.eventEmitter.emit('risk.limit.approached', event);
    this.dailyLossApproachEmitted = true; // fire once per day
  }
}

resetDaily() {
  this.dailyPnl = new Decimal(0);
  this.dailyLossApproachEmitted = false; // reset flag at midnight UTC
}
```

#### 6. FinancialDecimal / Decimal Precision — Never Use Native `number` for Financial Math

**Source:** Story 4.5.1 (property-based testing), Epic 4 Retro

**Problem:**
```typescript
// Native JS number arithmetic introduces floating-point errors
const edge = priceA - priceB - fees; // 0.1 + 0.2 = 0.30000000000000004
const positionSize = bankroll * 0.03; // Accumulated rounding in position sizing
```

**Solution:**
```typescript
import { FinancialMath } from '../common/utils/financial-math';

// All financial calculations use Decimal (via decimal.js) through FinancialMath
const edge = FinancialMath.calculateEdge(priceA, priceB, fees);
const positionSize = FinancialMath.calculatePositionSize(bankroll, maxPct);
// Never convert to number until final display/serialization
// Property-based tests (Story 4.5.1) verify composition chain correctness
```

### Key Constraints

- **Do NOT create any `.ts` files** — this is markdown only
- **Do NOT modify any existing files** — no source, test, or config changes
- **Do NOT reorganize code** — only document the debt, don't fix it
- **Use the exact gotcha names from the acceptance criteria** — all 5 must be present
- **Code examples must reflect actual codebase patterns** — use real service names and patterns from the project

### File Locations

- `pm-arbitrage-engine/technical-debt.md` — new file, engine repo root
- `pm-arbitrage-engine/docs/gotchas.md` — new file, may need to create `docs/` directory

Check if `docs/` exists first:
```bash
ls pm-arbitrage-engine/docs/ 2>/dev/null || echo "Directory does not exist — create it"
```
If `docs/` already contains files, do not modify or overwrite them — only add `gotchas.md`.

### Project Structure Notes

- Both files live in the engine repo (`pm-arbitrage-engine/`), not the main repo
- `docs/` directory is the standard location for project documentation per CLAUDE.md's `project_knowledge` config
- No alignment conflicts — these are new documentation files

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5.4] — Original requirements
- [Source: _bmad-output/implementation-artifacts/3-1-manual-contract-pair-configuration.md#Dev Notes] — plainToInstance gotcha
- [Source: _bmad-output/implementation-artifacts/3-4-contract-match-approval-workflow-mvp.md#Dev Notes] — OnModuleInit gotcha
- [Source: _bmad-output/implementation-artifacts/4-1-position-sizing-portfolio-limits.md#Dev Notes] — ConfigService.get gotcha
- [Source: _bmad-output/implementation-artifacts/4-2-daily-loss-limit-trading-halt.md#Dev Notes] — Fire-once pattern, error code deviation
- [Source: _bmad-output/implementation-artifacts/4-3-operator-risk-override.md#Debug Log] — Circular import resolution
- [Source: _bmad-output/implementation-artifacts/2-2-polymarket-order-book-normalization.md#Dev Notes] — forwardRef pattern
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-02-17.md] — Epic 4 retro learnings
- [Source: _bmad-output/implementation-artifacts/4-5-3-shared-e2e-test-environment-config.md] — Previous story, 498 test baseline
- [Source: pm-arbitrage-engine/src/modules/execution/execution-queue.service.ts:53] — TODO marker
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts:312] — TODO marker

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — documentation-only story, no debugging required.

### Completion Notes List

- Verified all 6 debt items against actual codebase before documenting (confirmed TODO markers at expected lines, confirmed Kalshi normalization duplication in 3 locations)
- `docs/` directory already existed with `migration-rollback.md` — no directory creation needed
- All 6 gotchas documented with problem/solution code examples using real project service names
- 498 tests pass, zero lint errors — no regressions

### File List

- `pm-arbitrage-engine/technical-debt.md` — NEW (AC1)
- `pm-arbitrage-engine/docs/gotchas.md` — NEW (AC2)
