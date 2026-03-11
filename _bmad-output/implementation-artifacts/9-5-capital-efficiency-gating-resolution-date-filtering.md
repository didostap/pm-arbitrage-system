# Story 9.5: Capital Efficiency Gating & Resolution Date Filtering

Status: done

## Story

As an operator,
I want the system to reject opportunities that lack a known resolution date or whose annualized return doesn't justify the capital lockup,
So that my capital is only deployed in trades with favorable time-value economics.

[Source: epics.md#Story-9.5; sprint-change-proposal-2026-03-13.md]

## Acceptance Criteria

1. **Given** an opportunity passes the net edge threshold (FR-AD-03, ≥0.8%)
   **When** the contract match has no resolution date (null)
   **Then** the opportunity is rejected before risk validation
   **And** an `OpportunityFilteredEvent` is emitted with reason: `"no_resolution_date"`
   **And** the rejection is logged with pair event description and contract details
   [Source: epics.md#Story-9.5 AC1; FR-AD-08]

2. **Given** an opportunity has a known resolution date but the date is in the past (already resolved)
   **When** the capital efficiency check runs
   **Then** the opportunity is rejected before risk validation
   **And** an `OpportunityFilteredEvent` is emitted with reason: `"resolution_date_passed"`
   **And** the rejection is logged with pair event description and resolution date
   [Derived from: epics.md#Story-9.5 AC1/AC2 — edge case; prevents division-by-zero and stale match trading]

3. **Given** an opportunity has a known future resolution date
   **When** the annualized net return is calculated as: `netEdge × (365 / daysToResolution)`
   **And** the result is below the configurable minimum (default: 15%)
   **Then** the opportunity is rejected before risk validation
   **And** an `OpportunityFilteredEvent` is emitted with reason: `"annualized_return_{calculated}%_below_{threshold}%_minimum"`
   **And** the rejection is logged with calculated annualized return, days to resolution, and threshold
   [Source: epics.md#Story-9.5 AC2; FR-AD-08]

4. **Given** an opportunity has a resolution date and meets the annualized return threshold
   **When** the capital efficiency check passes
   **Then** the opportunity proceeds to risk validation unchanged
   **And** the annualized return is included in the `EnrichedOpportunity` for downstream logging and dashboard display
   [Source: epics.md#Story-9.5 AC3]

5. **Given** the capital efficiency gate configuration
   **When** the engine starts
   **Then** `MIN_ANNUALIZED_RETURN` is loaded from env config (default: 0.15)
   **And** invalid values (negative, >10.0) are rejected at startup
   **And** the threshold is logged at startup for operator awareness
   [Source: epics.md#Story-9.5 AC4]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3 → 4 → 5 → 6 → 7**

- [x] **Task 1: Add `resolutionDate` to `ContractPairConfig` and populate it** (AC: #1, #2, #3, #4)
  - [x]1.1 Add `resolutionDate?: Date | null` field to `ContractPairConfig` interface at `src/modules/contract-matching/types/contract-pair-config.type.ts:5-13`
  - [x]1.2 In `ContractPairLoaderService.dbMatchToConfig()` at `src/modules/contract-matching/contract-pair-loader.service.ts:119-133`, add `resolutionDate: match.resolutionDate ?? null` to the returned object. The `ContractMatch` Prisma model already has `resolutionDate: DateTime?` at `prisma/schema.prisma:110`. The field is already fetched by `getActivePairs()` since it uses `findMany()` without a `select` clause (returns all columns).
  - [x]1.3 In `ContractPairLoaderService.toPairConfig()` at `src/modules/contract-matching/contract-pair-loader.service.ts:246-257` (YAML-loaded pairs), add `resolutionDate: null`. YAML pairs don't have resolution dates — they'll be correctly filtered by the "no resolution date" gate.
  - [x]1.4 Update `contract-pair-loader.service.spec.ts` — verify `resolutionDate` is populated for DB-loaded pairs and `null` for YAML-loaded pairs

- [x] **Task 2: Add `MIN_ANNUALIZED_RETURN` env config** (AC: #5)
  - [x]2.1 Add to `src/common/config/env.schema.ts`:
    ```typescript
    /** Minimum annualized return threshold for capital efficiency gating (FR-AD-08). Default 15%. */
    MIN_ANNUALIZED_RETURN: decimalString('0.15'),
    ```
    Follow existing `decimalString()` pattern used by `RISK_CLUSTER_HARD_LIMIT_PCT`, `DETECTION_MIN_EDGE_THRESHOLD`, and other financial thresholds. The `decimalString` helper validates the value is a parseable decimal string and returns it as-is (string type in env).
  - [x]2.2 Add to `.env.example` and `.env.development`:
    ```
    # Capital efficiency: minimum annualized return to accept an opportunity (FR-AD-08)
    # Formula: netEdge × (365 / daysToResolution). Default 15%.
    MIN_ANNUALIZED_RETURN=0.15
    ```

- [x] **Task 3: Add `annualizedReturn` field to `EnrichedOpportunity`** (AC: #4)
  - [x]3.1 Add `annualizedReturn: Decimal | null` to `EnrichedOpportunity` interface at `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts:20-28`. Null when resolution date is unknown (should not happen after this gate, but keeps the type safe for any future bypass).
  - [x]3.2 Import `Decimal` from `decimal.js` if not already imported in the types file

- [x] **Task 4: Implement capital efficiency gate in `EdgeCalculatorService`** (AC: #1, #2, #3, #4, #5)
  - [x]4.1 Add config loading in `EdgeCalculatorService`. Follow the existing `minEdgeThreshold` getter pattern at `edge-calculator.service.ts:59-63`:
    ```typescript
    private get minAnnualizedReturn(): Decimal {
      return new FinancialDecimal(
        this.configService.get<string>('MIN_ANNUALIZED_RETURN', '0.15'),
      );
    }
    ```
    Uses `FinancialDecimal` (defined in `common/utils/financial-math.ts:6-11` — `Decimal.clone()` with precision: 20, ROUND_HALF_UP) for consistency with `minEdgeThreshold`. Config type is `string` because `decimalString()` returns a string.
    Add startup log in `onModuleInit()` similar to existing threshold logging.
  - [x]4.2 Add a private method `checkCapitalEfficiency()`:
    ```typescript
    private checkCapitalEfficiency(
      dislocation: RawDislocation,
      netEdge: Decimal,
      pairEventDescription: string,
      filtered: FilteredDislocation[],
    ): { passed: boolean; annualizedReturn: Decimal | null } {
      const resolutionDate = dislocation.pairConfig.resolutionDate;

      // Gate 1: Resolution date required
      if (!resolutionDate) {
        const reason = 'no_resolution_date';
        filtered.push({
          pairEventDescription,
          netEdge: netEdge.toString(),
          threshold: this.minAnnualizedReturn.toString(),
          reason,
        });
        this.logger.debug({
          message: `Opportunity filtered: ${pairEventDescription} — no resolution date`,
          correlationId: getCorrelationId(),
          data: { pairEventDescription, reason },
        });
        this.eventEmitter.emit(
          EVENT_NAMES.OPPORTUNITY_FILTERED,
          new OpportunityFilteredEvent(
            pairEventDescription, netEdge, this.minAnnualizedReturn, reason,
          ),
        );
        return { passed: false, annualizedReturn: null };
      }

      // Gate 2: Annualized return threshold
      const now = new Date();
      const daysToResolution = new Decimal(
        resolutionDate.getTime() - now.getTime(),
      ).div(86_400_000); // ms → days

      // If resolution is in the past or today, treat as 0 days → filter
      if (daysToResolution.lte(0)) {
        const reason = 'resolution_date_passed';
        filtered.push({
          pairEventDescription,
          netEdge: netEdge.toString(),
          threshold: this.minAnnualizedReturn.toString(),
          reason,
        });
        this.logger.debug({
          message: `Opportunity filtered: ${pairEventDescription} — resolution date in the past`,
          correlationId: getCorrelationId(),
          data: { pairEventDescription, resolutionDate: resolutionDate.toISOString(), reason },
        });
        this.eventEmitter.emit(
          EVENT_NAMES.OPPORTUNITY_FILTERED,
          new OpportunityFilteredEvent(
            pairEventDescription, netEdge, this.minAnnualizedReturn, reason,
          ),
        );
        return { passed: false, annualizedReturn: null };
      }

      const annualizedReturn = netEdge.mul(new FinancialDecimal(365).div(daysToResolution));

      if (annualizedReturn.lt(this.minAnnualizedReturn)) {
        const reason = `annualized_return_${annualizedReturn.mul(100).toFixed(1)}%_below_${this.minAnnualizedReturn.mul(100).toFixed(0)}%_minimum`;
        filtered.push({
          pairEventDescription,
          netEdge: netEdge.toString(),
          threshold: this.minAnnualizedReturn.toString(),
          reason,
        });
        this.logger.debug({
          message: `Opportunity filtered: ${pairEventDescription} — annualized return below threshold`,
          correlationId: getCorrelationId(),
          data: {
            pairEventDescription,
            annualizedReturn: annualizedReturn.toString(),
            threshold: this.minAnnualizedReturn.toString(),
            daysToResolution: daysToResolution.toFixed(1),
            resolutionDate: resolutionDate.toISOString(),
            reason,
          },
        });
        this.eventEmitter.emit(
          EVENT_NAMES.OPPORTUNITY_FILTERED,
          new OpportunityFilteredEvent(
            pairEventDescription, netEdge, this.minAnnualizedReturn, reason,
          ),
        );
        return { passed: false, annualizedReturn };
      }

      return { passed: true, annualizedReturn };
    }
    ```
    All financial math uses `Decimal` — no native JS operators on monetary values.
    [Source: CLAUDE.md Domain Rules — "ALL financial calculations MUST use decimal.js"]
  - [x]4.3 Integrate into `processSingleDislocation()` at `src/modules/arbitrage-detection/edge-calculator.service.ts:135-240`. Insert the capital efficiency check AFTER the net edge threshold check passes (after line 200, before the `EnrichedOpportunity` construction at ~line 208):
    ```typescript
    // --- After net edge threshold check passes ---

    // Capital efficiency gate (FR-AD-08): resolution date + annualized return
    const { passed, annualizedReturn } = this.checkCapitalEfficiency(
      dislocation, netEdge, pairEventDescription, filtered,
    );
    if (!passed) return;

    // --- Continue with existing enrichment ---
    ```
  - [x]4.4 Set `annualizedReturn` on the `EnrichedOpportunity` object (in the enriched construction block):
    ```typescript
    const enriched: EnrichedOpportunity = {
      // ... existing fields ...
      annualizedReturn,  // Decimal | null — always populated here since gate passed
    };
    ```
  - [x]4.5 Add `annualizedReturn` to `OpportunityIdentifiedEvent` payload for downstream monitoring. Add `annualizedReturn: annualizedReturn?.toNumber() ?? null` alongside existing fields in the event emission at ~line 225.
  - [x]4.6 Validate config at startup — add `MIN_ANNUALIZED_RETURN` validation in `validateConfig()` method (lines 45-57). Follow existing pattern: read value, validate range (must be ≥ 0 and ≤ 10.0), log. The existing `validateConfig()` checks for NaN, undefined, and negative values. Extend for the upper bound (10.0 = 1000% annualized maximum).

- [x] **Task 5: Update `EdgeCalculatorService` tests** (AC: #1, #2, #3, #4, #5)
  - [x]5.1 In `edge-calculator.service.spec.ts`, add test: **filters opportunity when `resolutionDate` is null** — create a dislocation with `pairConfig.resolutionDate = null`, net edge above threshold. Assert it lands in `filtered[]` with reason `no_resolution_date`, `OpportunityFilteredEvent` emitted, NOT in `opportunities[]`.
  - [x]5.2 Add test: **filters opportunity when annualized return below threshold** — `resolutionDate` 180 days out, net edge 0.01 (1%). Annualized = 0.01 × (365/180) ≈ 2.03% < 15%. Assert filtered with reason containing `annualized_return`.
  - [x]5.3 Add test: **passes opportunity when annualized return meets threshold** — `resolutionDate` 7 days out, net edge 0.03 (3%). Annualized = 0.03 × (365/7) ≈ 156%. Assert in `opportunities[]` with `annualizedReturn` populated.
  - [x]5.4 Add test: **filters when resolution date is in the past** — `resolutionDate` yesterday. Assert filtered with reason `resolution_date_passed`.
  - [x]5.5 Add test: **startup logs annualized return threshold** — verify config read and log.
  - [x]5.6 Add test: **rejects invalid `MIN_ANNUALIZED_RETURN` at startup** — verify that negative values and values >10.0 cause startup validation failure with appropriate error message.
  - [x]5.7 Update existing tests that create `pairConfig` mocks — add `resolutionDate` field (set to a future date, e.g. 30 days out) to prevent false filtering. Check all existing `pairConfig` mock factories in the spec file. Key files to update:
    - `edge-calculator.service.spec.ts` — all dislocation mock factories
    - `detection.service.spec.ts` — if it creates `ContractPairConfig` mocks
    - `trading-engine.service.spec.ts` — if it creates pair config mocks for opportunities

- [x] **Task 6: Update `OpportunityIdentifiedEvent` to include `annualizedReturn`** (AC: #4)
  - [x]6.1 Check `OpportunityIdentifiedEvent` class in `src/common/events/detection.events.ts`. The event takes a single `opportunity: Record<string, unknown>` payload. Add `annualizedReturn: number | null` to the payload object passed in the event emission (Task 4.5). No constructor signature change needed — just include the new field in the object literal.
  - [x]6.2 Update any tests that construct `OpportunityIdentifiedEvent` to include the new field in the payload object.
  - [x]6.3 Verify `event-consumer.service.ts` — uses `onAny` with `summarizeEvent()` which serializes the event payload. New fields on the payload object flow to audit logs automatically without changes.

- [x] **Task 7: Lint, test, verify** (AC: all)
  - [x]7.1 Run `pnpm lint` — fix any issues
  - [x]7.2 Run `pnpm test` — all existing tests must pass. Pre-existing e2e timeout failures (2) are acceptable.
  - [x]7.3 Verify: a dislocation with `resolutionDate: null` and net edge above threshold is filtered (not executed)
  - [x]7.4 Verify: a dislocation with poor annualized return is filtered
  - [x]7.5 Verify: a dislocation with good annualized return proceeds to risk validation with `annualizedReturn` populated

## Dev Notes

### Pipeline Insertion Point

The capital efficiency gate is inserted in `EdgeCalculatorService.processSingleDislocation()` at `src/modules/arbitrage-detection/edge-calculator.service.ts:135-240`. This is **after** the net edge threshold check (line 167) and **before** opportunity enrichment (line 208). The pipeline flow:

```
Detection → Edge Calculation [net edge filter → CAPITAL EFFICIENCY GATE → enrich] → Risk Validation → Execution
```

This placement:
- Reuses existing `FilteredDislocation` and `OpportunityFilteredEvent` infrastructure
- Ensures filtered opportunities never reach risk validation or execution
- Is "before risk validation" as the sprint change proposal specifies
[Source: trading-engine.service.ts:57-287 — executeCycle pipeline; edge-calculator.service.ts:135-240 — processSingleDislocation]

### Formula

**Annualized return = `netEdge × (365 / daysToResolution)`**

- `netEdge` from `FinancialMath.calculateNetEdge()` is already a decimal ratio (e.g., 0.031 for 3.1%). It equals `gross_edge - buy_fee_cost - sell_fee_cost - gas_fraction`.
- The sprint change proposal's formula `(net_edge / capital_per_unit) × (365 / days_to_resolution)` assumed dollar-denominated net_edge. Since the codebase's `netEdge` is already `dollars / capital`, the simplified form is mathematically equivalent and avoids unnecessary operations.
[Source: financial-math.ts:52-94 — calculateNetEdge returns ratio; sprint-change-proposal-2026-03-13.md Section 4.1]

### `ContractPairConfig` Gap

`ContractPairConfig` at `contract-pair-config.type.ts:5-13` currently lacks `resolutionDate`. The field exists on the `ContractMatch` Prisma model (`schema.prisma:110`) but `dbMatchToConfig()` strips it. Task 1 adds it back.

- **DB-loaded pairs** (via candidate discovery pipeline): `resolutionDate` populated from `ContractMatch.resolutionDate`
- **YAML-loaded pairs** (via `toPairConfig()`): `resolutionDate = null` → filtered by "no resolution date" gate. This is correct — all active pairs use DB-sourced matches since Epic 8.
- `matchId` is already on `ContractPairConfig` — same pattern of carrying DB fields into the pair config
[Source: contract-pair-loader.service.ts:119-133 — dbMatchToConfig; contract-pair-loader.service.ts:246-257 — toPairConfig; contract-pair-loader.service.ts:43-67 — getActivePairs]

### Edge Cases

1. **Resolution date in the past**: Filter with `resolution_date_passed`. Protects against stale contract matches where the event already resolved.
2. **Resolution date today (0 days)**: `daysToResolution ≤ 0` → filter. Division by zero is prevented.
3. **Very near resolution (< 1 day)**: Annualized return will be extremely high. This is correct — a 1% edge resolving in 6 hours is ≈1460% annualized and should be traded.
4. **Resolution date very far out**: e.g., 365+ days. A 3% edge resolving in 400 days = 2.7% annualized → filtered. This is the primary target case.

### Monitoring & Visibility

- **Audit logs**: `OpportunityFilteredEvent` is audit-logged for ALL events via `EventConsumerService.handleEvent()` (`onAny` listener). New filter reasons (`no_resolution_date`, `annualized_return_*`, `resolution_date_passed`) appear automatically in `audit_logs` table with no additional code.
- **Telegram**: `OPPORTUNITY_FILTERED` is classified as `info` severity and is NOT in `TELEGRAM_ELIGIBLE_INFO_EVENTS` (intentional — filtered opportunities are high-frequency). The rejection is visible in structured logs and audit trail. If future operator demand warrants Telegram for specific filter reasons, a targeted formatter can be added without changing the gate logic.
- **Dashboard**: The `annualizedReturn` field on `EnrichedOpportunity` flows through `OpportunityIdentifiedEvent` to the performance service and audit trail. Dashboard display of annualized return on active opportunities is a separate enhancement (no dashboard changes in this story).
[Source: event-consumer.service.ts:37-62 — severity classification; event-consumer.service.ts:145-276 — handleEvent audit trail]

### Existing Test Mocks

Existing tests in `edge-calculator.service.spec.ts` create `pairConfig` mocks without `resolutionDate`. After this story, they'll need `resolutionDate` set to a future date to prevent false filtering. Scan ALL mock factories and update them (Task 5.6).

Similar updates may be needed in:
- `detection.service.spec.ts` (if it creates `ContractPairConfig` mocks)
- `trading-engine.service.spec.ts` (if it creates pair config mocks)
- Any file importing `ContractPairConfig` type for test mocks

### No DB Migration Needed

`resolutionDate` already exists on `ContractMatch` (`schema.prisma:110`). This story only changes TypeScript types and runtime logic — no Prisma migration.

### No Module Boundary Violations

- `EdgeCalculatorService` is in `modules/arbitrage-detection/` — it reads config and emits events (both in `common/`)
- `ContractPairConfig` is in `modules/contract-matching/types/` — imported by `modules/arbitrage-detection/` (allowed: detection → contract-matching per architecture)
- No new cross-module dependencies introduced
[Source: CLAUDE.md Architecture — Module Dependency Rules]

### Project Structure Notes

- All changes are within `pm-arbitrage-engine/` (independent git repo — separate commit required)
- Alignment with kebab-case file naming, PascalCase types, camelCase variables — no new files needed, only modifications
- Config uses `decimalString()` pattern — matches `DETECTION_MIN_EDGE_THRESHOLD`, `RISK_CLUSTER_HARD_LIMIT_PCT`, etc.
- Decimal construction uses `FinancialDecimal` (precision: 20, ROUND_HALF_UP) — matches `minEdgeThreshold` getter pattern
[Source: env.schema.ts:8 — decimalString helper; financial-math.ts:6-11 — FinancialDecimal config]

### References

- [Source: epics.md#Story-9.5] — Story definition and acceptance criteria
- [Source: sprint-change-proposal-2026-03-13.md] — Full problem analysis, formula, scope
- [Source: prd.md#FR-AD-08] — Resolution date + annualized return gate requirement
- [Source: edge-calculator.service.ts:135-240] — `processSingleDislocation()` — insertion point
- [Source: financial-math.ts:52-94] — `calculateNetEdge()` returns decimal ratio
- [Source: contract-pair-config.type.ts:5-13] — `ContractPairConfig` interface to extend
- [Source: contract-pair-loader.service.ts:119-133] — `dbMatchToConfig()` to update
- [Source: schema.prisma:95-134] — `ContractMatch` model with existing `resolutionDate` field
- [Source: common/events/detection.events.ts:20-30] — `OpportunityFilteredEvent` class
- [Source: common/config/env.schema.ts] — Environment schema (Zod validation)
- [Source: event-consumer.service.ts:37-62] — Severity classification and Telegram routing

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References
N/A — no runtime debugging needed; all tests passed on first run after fixing default `resolutionDate` in test mock.

### Completion Notes List
- All 7 tasks implemented in order per story specification
- 11 new tests added (3 loader + 8 edge calculator), total test count: 1909 (up from 1898 baseline)
- Used `ConfigValidationError` (code 4010) for startup validation instead of raw `Error` — per Lad MCP code review finding and CLAUDE.md architecture rule
- Existing `validateConfig()` method still uses raw `Error` (pre-existing tech debt, not in scope)
- Default `resolutionDate` in edge-calculator test `makePair()` set to 3 days out (not 30) to ensure existing tests with small net edges pass the 15% annualized gate
- `minAnnualizedReturn` getter follows existing `minEdgeThreshold` pattern (creates new `FinancialDecimal` per call). Caching noted as future optimization but matches established codebase pattern
- Dynamic reason string for annualized return filter follows AC #3 specification exactly
- `OpportunityFilteredEvent` threshold parameter for date gates passes `minAnnualizedReturn` — consistent with story's prescribed code
- No DB migration needed — `resolutionDate` already exists on `ContractMatch` Prisma model

### Lad MCP Code Review
- Primary reviewer (kimi-k2.5): 4 critical, 4 medium, 3 low findings
- Secondary reviewer (glm-5): 0 critical, 3 medium, 3 low findings
- **Fixed**: Raw Error → ConfigValidationError (critical, architecture violation)
- **Not fixed (by design)**: minimum holding period (story Dev Notes explicitly allow short resolution), dynamic reason strings (matches AC)

### Senior Developer Review (AI)
- **Reviewer:** Claude Opus 4.6 (Dev Agent CR workflow), 2026-03-13
- **Findings:** 0 HIGH, 3 MEDIUM, 3 LOW — all fixed
- **M1 (fixed):** `makePair()` mock in `edge-calculator.service.spec.ts` was missing required `polymarketClobTokenId` field — added
- **M2 (fixed):** Inconsistent `Decimal` construction across test mocks (`Decimal` vs `FinancialDecimal`) — standardized to `Decimal` (matches `EnrichedOpportunity` type)
- **M3 (fixed):** `FilteredDislocation.threshold` was semantically overloaded — binary gates (no_resolution_date, resolution_date_passed) now use `'N/A'` instead of annualized return threshold; annualized return gate keeps the actual threshold
- **L1 (fixed):** `minAnnualizedReturn` getter was called up to 5 times per dislocation — cached in local variable
- **L2 (fixed):** No test for `resolutionDate: undefined` — added explicit test case
- **L3 (fixed):** `MIN_ANNUALIZED_RETURN` was placed under "Cluster Classification" section in `env.schema.ts` — moved to "Edge Calculation" section
- **Test count after review fixes:** 1910 (up from 1909, +1 for undefined resolutionDate test)

### File List
**Modified:**
- `src/modules/contract-matching/types/contract-pair-config.type.ts` — added `resolutionDate?: Date | null`
- `src/modules/contract-matching/contract-pair-loader.service.ts` — `dbMatchToConfig()` and `toPairConfig()` populate `resolutionDate`
- `src/modules/contract-matching/contract-pair-loader.service.spec.ts` — 3 new tests for resolutionDate
- `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts` — added `annualizedReturn: Decimal | null`
- `src/modules/arbitrage-detection/edge-calculator.service.ts` — capital efficiency gate, config validation, startup logging; review: cached getter, threshold semantics fix
- `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` — 9 new tests (8 original + 1 review), updated `makePair()` default, added `polymarketClobTokenId`; threshold assertions for binary gates
- `src/common/config/env.schema.ts` — added `MIN_ANNUALIZED_RETURN` decimalString (Edge Calculation section)
- `src/modules/execution/execution.service.spec.ts` — added `annualizedReturn` to mock
- `src/modules/risk-management/risk-manager.service.spec.ts` — added `annualizedReturn` to mock (standardized to `Decimal`)
- `.env.example` — added `MIN_ANNUALIZED_RETURN=0.15`
- `.env.development` — added `MIN_ANNUALIZED_RETURN=0.15`
