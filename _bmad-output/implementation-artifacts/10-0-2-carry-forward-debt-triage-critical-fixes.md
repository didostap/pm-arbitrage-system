# Story 10-0-2: Carry-Forward Debt Triage & Critical Fixes

Status: done

## Story

As an **operator**,
I want **carry-forward tech debt items that directly impact Epic 10 stories resolved before feature development begins**,
so that **feature stories don't hit known blockers mid-implementation**.

## Acceptance Criteria

### AC 1: Full Triage of All 28 Tech Debt Items
**Given** the 28 tech debt items from the Epic 9 retro (8 new + 20 carry-forward)
**When** this story is implemented
**Then** every item has an explicit disposition: address now, address during Epic 10, carry forward, or close — with rationale
**And** the triage is saved as `_bmad-output/implementation-artifacts/10-0-2-tech-debt-triage.md`
[Source: epics.md#Epic-10 Story 10-0-2 AC 1; epic-9-retro-2026-03-15.md Technical Debt Inventory]

### AC 2: handleSingleLeg → SingleLegContext Interface
**Given** tech debt item CF-1 (`handleSingleLeg` 17-param method in `execution.service.ts`, from Epic 5.5)
**When** this story is implemented
**Then** a `SingleLegContext` interface exists in the execution module capturing 16 named fields (17 original params minus unused `_reservation`)
**And** `handleSingleLeg` accepts a single `context: SingleLegContext` parameter instead of 17 positional parameters
**And** both call sites in `execution.service.ts` (search: `this.handleSingleLeg(`) construct `SingleLegContext` objects
**And** the unused `_reservation: BudgetReservation` parameter (param 13) is omitted from the interface (confirmed dead: prefixed with `_`, not referenced in method body)
**And** this unblocks Story 10.3 (Automatic Single-Leg Management)
[Source: epics.md#Epic-10 Story 10-0-2 AC 2; epic-9-retro-2026-03-15.md CF-1; execution.service.ts — search `handleSingleLeg(`]

### AC 3: realizedPnl Column on OpenPosition
**Given** tech debt item CF-3 (`realizedPnl` column missing, from Epic 6)
**When** this story is implemented
**Then** a `realized_pnl` column exists on the `open_positions` table (Prisma migration, `Decimal? @db.Decimal(20, 8)`)
**And** realized P&L is persisted when positions are fully closed via `position-close.service.ts` `closePosition()` (search: `isFullExit` → `updateStatus` in the full-exit branch)
**And** realized P&L is persisted when positions are closed via `single-leg-resolution.service.ts` `closeLeg()` (search: `updateStatus(positionId, 'CLOSED')`)
**And** zero-residual EXIT_PARTIAL → CLOSED transitions persist `realizedPnl` as `new Prisma.Decimal(0)` (search: `kalshiEffectiveSize.isZero() && polymarketEffectiveSize.isZero()` in `closePosition`)
**And** the dashboard position detail page and positions table show `realizedPnl` when available (non-null)
**And** this unblocks Story 10.2 criterion tracking (realized P&L per position)
[Source: epics.md#Epic-10 Story 10-0-2 AC 3; epic-9-retro-2026-03-15.md CF-3; position-close.service.ts — `closePosition()` method; single-leg-resolution.service.ts — `closeLeg()` method]

### AC 4: resolutionDate Remaining Write Path Gap
**Given** tech debt item CF-5 (`resolutionDate` has no write path, from Epic 5)
**When** this story is implemented
**Then** YAML-configured contract pairs can specify an optional `resolutionDate` field (ISO 8601 string)
**And** `contract-match-sync.service.ts` upsert persists the YAML `resolutionDate` to the DB
**And** auto-discovered matches continue populating `resolutionDate` from platform API `settlementDate` (already works — no change)
**And** the match-approval update endpoint accepts an optional `resolutionDate` field (operator can set/update via dashboard)
**And** time-based exit logic (Story 10.2 criterion #3) has functional input data for all match types
[Source: epics.md#Epic-10 Story 10-0-2 AC 4; epic-9-retro-2026-03-15.md CF-5; candidate-discovery.service.ts:371-374 (auto-discovery, already works); contract-pair-loader.service.ts:260 (YAML, always null)]

**Investigation finding:** Auto-discovered matches already populate `resolutionDate` from platform APIs — Kalshi `expected_expiration_time`/`expiration_time`/`close_time` chain (`kalshi-catalog-provider.ts:154-184`) and Polymarket `endDate` (`polymarket-catalog-provider.ts:178`). The gap is only YAML-loaded pairs and existing matches created before Epic 8.

### AC 5: Tests
**Given** all changes in this story
**When** tests are run
**Then** new tests cover: `SingleLegContext` construction at both call sites, `realizedPnl` persistence in full close + single-leg close + zero-residual, YAML `resolutionDate` parsing + sync, match-approval `resolutionDate` update
**And** all existing tests pass at baseline (2241 passed, 121 files)
**And** `pnpm lint` clean, `pnpm build` clean
[Source: CLAUDE.md post-edit workflow; baseline from Story 10-0-2a completion]

### AC 6: Triage Document Deliverable
**Given** the full triage is complete
**When** results are reviewed
**Then** a triage document exists at `_bmad-output/implementation-artifacts/10-0-2-tech-debt-triage.md` with all 28 items categorized and rationale provided
[Source: epics.md#Epic-10 Story 10-0-2 AC 6]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3 → 4 → 5 → 6 → 7**

### Phase 1: Triage Document (AC: #1, #6)

- [x] **Task 1: Save triage document** (AC: #1, #6)
  - [x] 1.1 Create `_bmad-output/implementation-artifacts/10-0-2-tech-debt-triage.md` with the full triage from the **Triage Reference** section below
  - [x] 1.2 Verify all 28 items have dispositions matching the reference

### Phase 2: SingleLegContext Refactor (AC: #2)

- [x] **Task 2: Create SingleLegContext interface** (AC: #2)
  - [x] 2.1 Create `src/modules/execution/single-leg-context.type.ts` with `SingleLegContext` interface.
    The 16 fields map 1:1 to `handleSingleLeg`'s current params (minus `_reservation`):
    ```typescript
    // Imports: resolve from handleSingleLeg's existing imports in execution.service.ts
    // - Decimal from 'decimal.js'
    // - OrderResult from '../../common/types/platform.type' (search: 'OrderResult' in execution.service.ts imports)
    // - EnrichedOpportunity from '../arbitrage-detection/types' (search: 'EnrichedOpportunity' in execution.service.ts imports)
    // - RankedOpportunity from '../../common/types/risk.type' (search: 'RankedOpportunity' in execution.service.ts imports)

    export interface SingleLegContext {
      pairId: string;
      primaryLeg: string;            // "kalshi" | "polymarket"
      primaryOrderId: string;
      primaryOrder: OrderResult;
      primarySide: string;            // "buy" | "sell"
      secondarySide: string;
      primaryPrice: Decimal;
      secondaryPrice: Decimal;
      primarySize: number;
      secondarySize: number;
      enriched: EnrichedOpportunity;
      opportunity: RankedOpportunity;
      errorCode: number;
      errorMessage: string;
      isPaper: boolean;
      mixedMode: boolean;
    }
    ```
    **IMPORTANT:** Before creating, verify the 16 fields match the actual `handleSingleLeg` signature by reading it (search: `private async handleSingleLeg(`). The `_reservation: BudgetReservation` param is the one to omit — it's underscore-prefixed and unused in the method body.

- [x] **Task 3: Refactor handleSingleLeg method** (AC: #2)
  - [x] 3.1 In `execution.service.ts`, change `handleSingleLeg` signature from 17 positional params to `(context: SingleLegContext)`
  - [x] 3.2 Update method body: destructure `context` at top, replace all parameter references
  - [x] 3.3 Update **call site 1** (~line 555, secondary leg submission error): construct `SingleLegContext` object from local variables
  - [x] 3.4 Update **call site 2** (~line 604, secondary leg non-filled status): construct `SingleLegContext` object from local variables
  - [x] 3.5 Run `pnpm build` to verify no type errors
  - [x] 3.6 Update `execution.service.spec.ts`: update any tests that mock or call `handleSingleLeg` with the new interface

### Phase 3: realizedPnl Persistence (AC: #3)

- [x] **Task 4: Prisma migration for realizedPnl** (AC: #3)
  - [x] 4.1 Add to `OpenPosition` model in `prisma/schema.prisma`:
    ```prisma
    realizedPnl       Decimal?       @map("realized_pnl") @db.Decimal(20, 8)
    ```
    Place after `expectedEdge` line (~220), alongside other financial fields.
  - [x] 4.2 Run `pnpm prisma migrate dev --name add-realized-pnl`
  - [x] 4.3 Run `pnpm prisma generate`

- [x] **Task 5: Persist realizedPnl on position close** (AC: #3)
  - [x] 5.1 In `position-close.service.ts` `closePosition()`, **full exit path** (search: `isFullExit` → the `updateStatus(position.positionId, 'CLOSED')` call in that branch): replace with a direct Prisma update that sets both status and realizedPnl:
    ```typescript
    await this.prisma.openPosition.update({
      where: { positionId: position.positionId },
      data: { status: 'CLOSED', realizedPnl: realizedPnl.toDecimalPlaces(8) },
    });
    ```
    Use direct Prisma call — `updateStatus()` is a thin wrapper and adding optional params to it would force auditing all callers. Direct Prisma is cleaner for this composite update.
  - [x] 5.2 In `position-close.service.ts`, **partial exit path** (search: `EXIT_PARTIAL` in the else branch after `isFullExit`): do NOT persist `realizedPnl`. Partial exits release capital proportionally via `releasePartialCapital()` but the position remains open — its lifetime `realizedPnl` is not yet determined. The partial P&L is already logged in the event.
  - [x] 5.3 In `position-close.service.ts`, **zero-residual path** (search: `kalshiEffectiveSize.isZero() && polymarketEffectiveSize.isZero()`): update the `updateStatus(position.positionId, 'CLOSED')` call to also persist `realizedPnl`. This path runs when an EXIT_PARTIAL position's residual legs are fully consumed by prior partial exits — P&L was already captured in prior `releasePartialCapital` calls, so persist `realizedPnl` as 0 (the cumulative P&L is tracked via risk manager, not this field).
    ```typescript
    await this.prisma.openPosition.update({
      where: { positionId: position.positionId },
      data: { status: 'CLOSED', realizedPnl: 0 },
    });
    ```
  - [x] 5.4 In `single-leg-resolution.service.ts` `closeLeg()` (search: `this.positionRepository.updateStatus(positionId, 'CLOSED')` near end of method): replace with direct Prisma update including `realizedPnl`:
    ```typescript
    await this.prisma.openPosition.update({
      where: { positionId },
      data: { status: 'CLOSED', realizedPnl: realizedPnl.toDecimalPlaces(8) },
    });
    ```
    Ensure `this.prisma` is injected (check existing constructor — `PrismaService` should already be available or add injection).
  - [x] 5.5 Add tests: verify `realizedPnl` is written to DB in full close, single-leg close, and zero-residual paths. Mock or spy on `prisma.openPosition.update` and assert `data.realizedPnl` is present and correct.

- [x] **Task 6: Dashboard realizedPnl display** (AC: #3)
  - [x] 6.1 Add `realizedPnl: string | null` to `PositionSummaryDto` in `src/dashboard/dto/position-summary.dto.ts` (with `@ApiProperty`)
  - [x] 6.2 Update `position-enrichment.service.ts` to include `realizedPnl` from the position record (convert via `new Decimal(value.toString()).toFixed(8)` when non-null)
  - [x] 6.3 Regenerate dashboard API client: `cd ../pm-arbitrage-dashboard && pnpm generate-api`
  - [x] 6.4 Show `realizedPnl` on position detail page (for CLOSED positions) and in the positions table as a column (only populated for closed positions, show "—" for open)
  - [x] 6.5 Use `PnlCell` shared cell renderer for consistent red/green formatting (search dashboard codebase: `PnlCell` in `src/components/` — created in Story 9-10; verify it exists and check its props interface before use)

### Phase 4: resolutionDate Gap Closure (AC: #4)

- [x] **Task 7: YAML config resolutionDate support** (AC: #4)
  - [x] 7.1 Add to `ContractPairDto` in `src/modules/contract-matching/dto/contract-pair.dto.ts`:
    ```typescript
    @IsOptional()
    @IsISO8601()
    resolutionDate?: string;
    ```
  - [x] 7.2 Update `ContractPairConfig` type in `src/modules/contract-matching/types/contract-pair-config.type.ts` (already has `resolutionDate?: Date | null` — no change needed, verify)
  - [x] 7.3 Update `contract-pair-loader.service.ts` to parse `resolutionDate` from YAML (convert ISO string → Date in `toPairConfig()` or equivalent mapping function). Currently line 260 hardcodes `resolutionDate: null` for YAML pairs — conditionally set from config.
  - [x] 7.4 Update `contract-match-sync.service.ts` upsert to persist `resolutionDate` from the pair config:
    - **create** branch: `resolutionDate: pair.resolutionDate ?? null` — new records get the value or null
    - **update** branch: `resolutionDate: pair.resolutionDate !== undefined ? pair.resolutionDate : undefined` — use `undefined` to skip Prisma field when config omits it (preserves existing DB value). Use `null` to explicitly clear if config sets `resolutionDate: null`.
    - YAML parsers treat omitted keys as `undefined` and explicit `null` as `null`. The config type `resolutionDate?: Date | null` distinguishes both: `undefined` = not specified (preserve DB), `null` = explicitly cleared.
  - [x] 7.5 Add tests: YAML pair with resolutionDate → parsed and synced; YAML pair without resolutionDate field → DB value preserved (not overwritten); YAML pair with explicit `resolutionDate: null` → DB value cleared; DB pair on create → null when absent.

- [x] **Task 8: Match-approval resolutionDate update** (AC: #4)
  - [x] 8.1 Add optional `resolutionDate?: string` (ISO 8601) to the match approval/update DTO (find the DTO used by the match-approval controller's approve endpoint)
  - [x] 8.2 In the match-approval service, when `resolutionDate` is provided, update the `ContractMatch` record
  - [x] 8.3 Add test: approve match with resolutionDate → persisted; approve without → unchanged

### Phase 5: Final Validation (AC: #5)

- [x] **Task 9: Test suite + lint + build** (AC: #5)
  - [x] 9.1 Run `pnpm test` — all existing + new tests pass
  - [x] 9.2 Run `pnpm lint` — clean
  - [x] 9.3 Run `pnpm build` — no type errors

## Dev Notes

### Architecture Patterns & Constraints

- **Module dependency rules**: All changes stay within existing module boundaries. `SingleLegContext` in `modules/execution/` (not `common/interfaces/` — it's execution-internal). [Source: CLAUDE.md Module Dependency Rules]
- **Financial math**: `realizedPnl` calculations already use `decimal.js`. Persistence uses `Prisma.Decimal`. Convert via `.toDecimalPlaces(8)` or `.toFixed(8)` for string representation. [Source: CLAUDE.md Domain Rules]
- **Error hierarchy**: No new error types needed. [Source: CLAUDE.md Error Handling]
- **Event emission**: No new events. Existing `EXIT_TRIGGERED` and `SINGLE_LEG_RESOLVED` events already carry `realizedPnl` as a string parameter. [Source: execution.events.ts]
- **Prisma Decimal convention**: All financial columns use `@db.Decimal(20, 8)`. [Source: schema.prisma lines 23-24, 149-155, 189-193, 220-231]

### Critical Implementation Details

1. **handleSingleLeg has 17 params, not 16**: The epic description says "16-param" but actual count is 17 (including `mixedMode` added in Story 5-5-3). The `_reservation: BudgetReservation` (param 13) is confirmed unused — omit from `SingleLegContext`. Current signature (verified, search: `private async handleSingleLeg(`):
    ```
    handleSingleLeg(
      pairId: string,                    // 1
      primaryLeg: string,                // 2  "kalshi" | "polymarket"
      primaryOrderId: string,            // 3
      primaryOrder: OrderResult,         // 4
      primarySide: string,               // 5  "buy" | "sell"
      secondarySide: string,             // 6
      primaryPrice: Decimal,             // 7
      secondaryPrice: Decimal,           // 8
      primarySize: number,               // 9
      secondarySize: number,             // 10
      enriched: EnrichedOpportunity,     // 11
      opportunity: RankedOpportunity,    // 12
      _reservation: BudgetReservation,   // 13  ← UNUSED, omit from interface
      errorCode: number,                 // 14
      errorMessage: string,              // 15
      isPaper: boolean,                  // 16
      mixedMode: boolean                 // 17
    )
    ```

2. **handleSingleLegFailure in position-close.service.ts is OUT OF SCOPE**: It has 6 params and a different semantic context (exit-time failure vs entry-time failure). The epic AC specifically mentions `handleSingleLeg` in execution.service.ts. [Source: epics.md#10-0-2 AC 2; position-close.service.ts:576]

3. **realizedPnl is already computed but not persisted**: `position-close.service.ts:447` computes `realizedPnl` (Decimal). `single-leg-resolution.service.ts:449` computes `realizedPnl` (Decimal). Both return the value in their result objects but don't write to DB. The fix is to include `realizedPnl` in the position status update. [Verified: position-close.service.ts:476-516; single-leg-resolution.service.ts:449-466]

4. **Position repository update pattern**: `updateStatus(id, status)` only updates status. Use either `this.prisma.openPosition.update({ where: { positionId }, data: { status, realizedPnl } })` directly OR add an optional `realizedPnl` param to `updateStatus`. Prefer direct Prisma call for clarity — the repository method is a thin wrapper. [Verified: position.repository.ts `updateStatus`]

5. **Partial exit does NOT persist realizedPnl**: When `closePosition()` results in a partial fill → `EXIT_PARTIAL`, the position stays open. The `realizedPnl` for the partial exit is used for capital release (`releasePartialCapital`) but the position's lifetime realized P&L is not yet determined. Only persist when transitioning to `CLOSED`. [Verified: position-close.service.ts:520-544]

6. **resolutionDate for auto-discovered matches already works**: `candidate-discovery.service.ts:371-374` writes `resolutionDate: polyContract.settlementDate ?? kalshiContract.settlementDate ?? null`. Both Kalshi and Polymarket catalog providers populate `settlementDate`. No changes needed for auto-discovery path. [Verified: candidate-discovery.service.ts, kalshi-catalog-provider.ts:154-184, polymarket-catalog-provider.ts:178]

7. **YAML resolutionDate → contract-match-sync upsert**: The upsert in `contract-match-sync.service.ts` must NOT overwrite an existing DB `resolutionDate` with `null` when the YAML pair omits the field. Use `resolutionDate: pair.resolutionDate ?? undefined` — Prisma skips `undefined` fields in `update`. [Source: Prisma docs on undefined vs null]

8. **ContractPairConfig type already has resolutionDate**: `types/contract-pair-config.type.ts:14` has `resolutionDate?: Date | null`. The type is ready. The gap is in the DTO (no validation decorator) and the loader (hardcoded null for YAML). [Verified: contract-pair-config.type.ts:14; contract-pair-loader.service.ts:260]

### Scope Boundaries

**In scope:**
- Triage document (28 items, dispositions, rationale)
- `SingleLegContext` interface + `handleSingleLeg` refactor
- `realizedPnl` Prisma column + persistence in close paths + dashboard display
- YAML `resolutionDate` DTO field + sync persistence + match-approval update

**Out of scope:**
- `handleSingleLegFailure` in position-close.service.ts (6 params, different context)
- Reconciliation `force_close` P&L capture (separate carry-forward item CF-7)
- resolutionDate backfill script for historical null records (operator can update via dashboard per AC 4)
- Event constructor parameter sprawl (carry-forward, not blocking)
- Any items triaged as "carry forward" or "during Epic 10"

### Previous Story Intelligence

**From Story 10-0-2a** (validatePosition mode-awareness):
- `getState(isPaper)` / `getBankrollForMode(isPaper)` pattern established — relevant context for understanding risk manager but no direct impact on this story's changes
- Baseline: 2241 tests, 121 files
- Known debt: `determineRejectionReason` not mode-aware, `CorrelationTrackerService` getters not mode-parameterized

**From Story 10-0-2b** (outcome direction matching validation):
- `ContractSummary` already has `settlementDate` and `outcomeLabel`/`outcomeTokens` fields
- Candidate discovery already writes `resolutionDate` from `settlementDate` — confirms auto-discovery path works
- Prisma schema recently migrated — ensure clean migration chain

**From Story 10-0-1** (WebSocket subscriptions):
- Large story pattern: 7 phases, 77+ tests, 5 CRITICAL code review findings
- Current story is smaller scope — 4 phases, expect ~15-25 new tests

### Project Structure Notes

- All backend code in `pm-arbitrage-engine/src/` (independent git repo — separate commits)
- Dashboard code in `pm-arbitrage-dashboard/` (separate git repo — separate commits)
- Triage document in `_bmad-output/implementation-artifacts/` (main repo)
- Prisma schema at `pm-arbitrage-engine/prisma/schema.prisma`
- New file: `src/modules/execution/single-leg-context.type.ts`
- No new modules, no new module registrations

### Post-Edit Checklist
1. `cd pm-arbitrage-engine && pnpm lint` — fix all errors
2. `pnpm test` — all tests pass (baseline: 2241 passed, 121 files)
3. `pnpm prisma generate` — after schema change
4. `pnpm build` — no type errors
5. Regenerate dashboard API client if backend DTOs changed

### References

- [Source: epics.md#Epic-10 Story 10-0-2] — Full AC definitions
- [Source: epic-9-retro-2026-03-15.md Technical Debt Inventory] — All 28 items with priorities and origins
- [Source: execution.service.ts:920-938] — `handleSingleLeg` 17-param signature
- [Source: execution.service.ts:555, 604] — Two call sites
- [Source: position-close.service.ts:386-516] — `realizedPnl` computation (not persisted)
- [Source: single-leg-resolution.service.ts:430-466] — `closeLeg` P&L computation (not persisted)
- [Source: prisma/schema.prisma:220] — `expectedEdge` field (adjacent placement for `realizedPnl`)
- [Source: candidate-discovery.service.ts:371-374] — Auto-discovery resolutionDate write (already works)
- [Source: contract-pair-loader.service.ts:260] — YAML pairs hardcoded `resolutionDate: null`
- [Source: contract-match-sync.service.ts:58-81] — Upsert (missing resolutionDate)
- [Source: kalshi-catalog-provider.ts:154-184] — Kalshi `settlementDate` extraction
- [Source: polymarket-catalog-provider.ts:178] — Polymarket `endDate` → `settlementDate`
- [Source: CLAUDE.md] — Post-edit workflow, module dependency rules, financial math, naming conventions
- [Source: Epic 9 retro Team Agreement #18] — Vertical slice minimum (dashboard display for realizedPnl)

---

## Triage Reference

The dev agent must save this triage as `_bmad-output/implementation-artifacts/10-0-2-tech-debt-triage.md`.

### Epic 9 New Items (8)

| # | Item | Disposition | Rationale |
|---|------|------------|-----------|
| E9-1 | WebSocket subscriptions never established | **CLOSED** | Resolved in Story 10-0-1. `subscribeToContracts()` added to `IPlatformConnector`, both connectors implement, divergence monitoring active. |
| E9-2 | Correlation tracker cache not mode-separated (paper/live) | **Carry forward** | Not blocking Epic 10. Mode separation only matters when paper mode exercises the risk validation pipeline's cluster exposure path, which it doesn't currently. Becomes relevant if Story 10.3 auto-management runs in paper mode. |
| E9-3 | Dashboard per-mode capital display (paper vs live) | **Carry forward** | Not blocking. Paper-only operation doesn't need visual separation. Revisit when live trading begins. |
| E9-4 | 4 P2 UX items from audit (sparklines, dynamic thresholds, drill-down) | **Carry forward** | Low-priority UX polish from Story 9-21 audit. Not blocking any feature. |
| E9-5 | `processOverride()` uses unadjusted base size | **Carry forward** | Overrides are operator-initiated safety valve with low frequency. Confidence adjustment on overrides is an enhancement, not a correctness fix. |
| E9-6 | Kalshi WS client staleness check parity with Polymarket | **Carry forward** | Low priority now that WS subscriptions work (10-0-1). Both connectors have staleness detection; parity is a completeness issue. |
| E9-7 | Per-pair staleness Telegram alerts | **Carry forward** | Platform-level alerts exist. Per-pair granularity is nice-to-have for debugging. |
| E9-8 | `correlation-tracker.service.spec.ts` not updated for `updateBankroll()` | **During Epic 10** | Low-effort test gap. Include in whichever story next touches the correlation tracker (likely 10.2 or 10.3). |

### Carry-Forward from Prior Epics (20)

| # | Item | Disposition | Rationale |
|---|------|------------|-----------|
| CF-1 | `handleSingleLeg` 17-param → `SingleLegContext` interface | **ADDRESS NOW** | Directly blocks Story 10.3 (Automatic Single-Leg Management). Epic AC explicitly requires this. |
| CF-2 | Event constructor parameter sprawl → options objects | **Carry forward** | No Epic 10 story depends on this. Events work correctly, just verbose constructors. Pattern change would touch 30+ event emission sites. |
| CF-3 | `realizedPnl` column on OpenPosition | **ADDRESS NOW** | Directly blocks Story 10.2 (Five-Criteria Model-Driven Exit Logic) criterion tracking. |
| CF-4 | Event payload enrichment (contractId, fees, gas on OrderFilledEvent) | **During Epic 10** | Relevant to Story 10.1 (continuous edge recalculation needs fee/gas data from events). Include in 10.1 story scope. |
| CF-5 | `resolutionDate` has no write path | **ADDRESS NOW (partial)** | Auto-discovered matches already populate from platform APIs (Epic 8 + 10-0-2b). Remaining gap: YAML pairs + dashboard update path. Blocks 10.2 time-decay criterion for YAML-configured pairs. |
| CF-6 | `entryPrices` stale after single-leg resolution | **Carry forward** | Edge case: entry prices could mismatch after retry resolves single-leg exposure. Low frequency, not blocking. |
| CF-7 | `force_close` in reconciliation doesn't capture real P&L | **Carry forward** | Emergency path. Normal close paths get `realizedPnl` in this story. Reconciliation force_close is a separate concern. |
| CF-8 | Error code catalog reconciliation — PRD vs codebase | **Carry forward** | Documentation debt. Error codes work correctly in practice. |
| CF-9 | Polymarket order book minor duplication | **Carry forward** | Performance not an issue at current scale. |
| CF-10 | `forwardRef` for ConnectorModule ↔ DataIngestionModule | **Carry forward** | Works correctly. `forwardRef` is the NestJS-recommended solution for circular deps. |
| CF-11 | PrismaService direct import in DashboardModule | **Carry forward** | Convention debt. Module works correctly via `PersistenceModule` exports. |
| CF-12 | Error severity defaults on error classes (code range mapping) | **During Epic 10** | Relevant to Story 10.3/10.4 autonomous actions where error severity drives automated decisions. Include in 10.3. |
| CF-13 | CI-generated Swagger client as tested contract | **Carry forward** | Process improvement. Manual regeneration works. |
| CF-14 | Fire-and-forget correlation ID propagation | **Carry forward** | Logging quality improvement. AsyncLocalStorage context works for synchronous chains. |
| CF-15 | `LLM_TIMEOUT_MS` not wired to SDK calls (AbortController) | **Carry forward** | LLM calls work with HTTP-layer timeout. AbortController is an enhancement. |
| CF-16 | Category alignment across platforms | **Carry forward** | Cluster classification handles mismatches via LLM fallback (Story 9-1). |
| CF-17 | No circuit breaker for persistent LLM API failures | **Carry forward** | Rate limiter + retry exist. Circuit breaker is an enhancement for when LLM call volume increases. |
| CF-18 | Polymarket `getContractResolution()` null conflated with API errors | **Carry forward** | Resolution poller works in practice. Null = unresolved is the common case. |
| CF-19 | Snapshot historical confidence at resolution time | **Carry forward** | Analytics enhancement. Current confidence scoring is live-only. |
| CF-20 | Wrap `getResolutionContext()` queries in transaction | **Carry forward** | Read-only queries. Consistency risk minimal. |

### Triage Summary

| Disposition | Count | Items |
|------------|-------|-------|
| **Address Now** | 3 | CF-1, CF-3, CF-5 (partial) |
| **During Epic 10** | 3 | CF-4 (in 10.1), CF-12 (in 10.3), E9-8 (next touch) |
| **Carry Forward** | 21 | E9-2 through E9-7, CF-2, CF-6 through CF-11, CF-13 through CF-20 |
| **Closed** | 1 | E9-1 (done in 10-0-1) |
| **Total** | 28 | |

### Newly Identified Debt (from 10-0-1, 10-0-2a, 10-0-2b — not part of original 28)
- `determineRejectionReason` not mode-aware (from 10-0-2a)
- `CorrelationTrackerService` getters not mode-parameterized (from 10-0-2a)
- Frontend `WsAlertNewPayload.type` missing 2 backend alert types (from 10-0-2a)

These are tracked for awareness but not triaged as part of this story's 28-item mandate.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- **Triage document**: Created `10-0-2-tech-debt-triage.md` with all 28 items triaged: 3 Address Now, 3 During Epic 10, 21 Carry Forward, 1 Closed.
- **SingleLegContext refactor**: Created `SingleLegContext` interface with 16 fields (omitting unused `_reservation: BudgetReservation`). Refactored `handleSingleLeg` from 17 positional params to single context object. Both call sites updated. No test changes needed — `handleSingleLeg` is private, tests exercise it indirectly via `execute()`.
- **realizedPnl persistence**: Added `realized_pnl` Decimal column to `open_positions`. Three close paths updated: full exit persists computed `realizedPnl`, zero-residual persists `0`, partial exit does NOT persist (position stays open). `PrismaService` injected into `PositionCloseService` and `SingleLegResolutionService` for direct Prisma updates (bypassing `updateStatus()` thin wrapper).
- **Dashboard realizedPnl**: `PositionSummaryDto` already had the field. Updated `dashboard.service.ts` to prefer DB-persisted value over on-the-fly computation for closed positions. Added `realizedPnl` to `PositionFullDetailDto` and both position endpoints. Added display to `PositionDetailPage.tsx` using `PnlCell`. Regenerated API client.
- **resolutionDate YAML support**: Added `@IsISO8601()` validated `resolutionDate` to `ContractPairDto`. Updated `toPairConfig()` to parse ISO → Date (was hardcoded null). Updated sync upsert: create always sets value (null if absent), update only includes when defined (preserves DB value when YAML omits field).
- **resolutionDate approval**: Added optional `resolutionDate` to `ApproveMatchDto` with ISO 8601 validation. Updated `approveMatch` service and controller to pass through and persist.
- **Lad code review**: Primary reviewer found no genuine issues (critical finding was false positive from stale dist/ files). Secondary reviewer timed out.
- **Test results**: 2252 passed (baseline 2241 + 11 new), 121 files, lint clean, build clean.
- **Code review #2** (2026-03-16): fixed 3 MEDIUM (realizedPnl dead code in CurrentStateSection → moved to ExitSection, missing computeRealizedPnl fallback in getPositionDetails, unchanged pair check missing resolutionDate comparison), 1 LOW (missing null-clearing test for sync resolutionDate). +1 test (2252→2253). Also flagged pre-existing `candidate-discovery.service.ts` debug artifact (`polyContracts.slice(32000)`) — reverted.

### Key Design Decisions

1. **Direct Prisma calls over repository wrapper**: Used `this.prisma.openPosition.update()` instead of extending `updateStatus()` — cleaner for composite status+realizedPnl updates without forcing audit of all `updateStatus` callers.
2. **DB value fallback**: Dashboard prefers DB `realizedPnl` when available, falls back to on-the-fly computation for pre-migration closed positions.
3. **Sync upsert spread pattern**: `...(pair.resolutionDate !== undefined ? { resolutionDate: pair.resolutionDate } : {})` — Prisma skips undefined fields, preserving existing DB values when YAML omits the field.

### File List

**Engine (pm-arbitrage-engine/):**
- `prisma/schema.prisma` — added `realizedPnl` column
- `prisma/migrations/20260316132415_add_realized_pnl/migration.sql` — migration
- `src/modules/execution/single-leg-context.type.ts` — **NEW** SingleLegContext interface
- `src/modules/execution/execution.service.ts` — handleSingleLeg refactored, import added
- `src/modules/execution/position-close.service.ts` — PrismaService injection, realizedPnl persistence (full + zero-residual)
- `src/modules/execution/single-leg-resolution.service.ts` — PrismaService injection, realizedPnl persistence (closeLeg)
- `src/modules/execution/position-close.service.spec.ts` — PrismaService mock, assertion updates, +3 new tests
- `src/modules/execution/single-leg-resolution.service.spec.ts` — PrismaService mock, assertion updates, +1 new test
- `src/modules/contract-matching/dto/contract-pair.dto.ts` — added resolutionDate field
- `src/modules/contract-matching/contract-pair-loader.service.ts` — parse resolutionDate from YAML
- `src/modules/contract-matching/contract-match-sync.service.ts` — resolutionDate in upsert
- `src/modules/contract-matching/contract-pair-loader.service.spec.ts` — +2 new tests
- `src/modules/contract-matching/contract-match-sync.service.spec.ts` — +4 new tests
- `src/dashboard/dto/match-approval.dto.ts` — resolutionDate on ApproveMatchDto
- `src/dashboard/match-approval.service.ts` — resolutionDate param + Prisma update
- `src/dashboard/match-approval.controller.ts` — pass resolutionDate through
- `src/dashboard/match-approval.controller.spec.ts` — updated assertion, +1 new test
- `src/dashboard/dashboard.service.ts` — DB-first realizedPnl in 3 response builders
- `src/dashboard/dto/position-detail.dto.ts` — added realizedPnl field

**Dashboard (pm-arbitrage-dashboard/):**
- `src/api/generated/Api.ts` — regenerated
- `src/pages/PositionDetailPage.tsx` — realizedPnl display for closed positions

**Main repo:**
- `_bmad-output/implementation-artifacts/10-0-2-tech-debt-triage.md` — **NEW** triage document
