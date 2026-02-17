# Story 3.0: Epic 3 Sprint 0 — Targeted Preparation

Status: done

## Story

As an operator,
I want financial math foundations, decimal precision utilities, config validation schemas, and migration rollback strategies in place,
so that Epic 3's detection and edge calculation stories build on verified, production-grade infrastructure.

## Acceptance Criteria

### AC1: Financial Math Test Scenarios (Hand-Verified)

**Given** a CSV file exists at `src/modules/arbitrage-detection/__tests__/edge-calculation-scenarios.csv`
**When** the developer inspects it
**Then** it contains 15+ hand-verified edge calculation scenarios with columns:
- `scenario_name`, `buy_price`, `sell_price`, `buy_fee_pct`, `sell_fee_pct`, `gas_estimate_usd`, `position_size_usd`, `expected_gross_edge`, `expected_net_edge`, `expected_filtered` (boolean), `notes`

**Note:** Column names are platform-agnostic (buy/sell, not polymarket/kalshi) to support Epic 11 extensibility. Each scenario row documents which platform is buy vs sell in the `notes` column.

Scenarios MUST include:
1. **Exact threshold boundary:** net edge = 0.80% (passes filter)
2. **Just below threshold:** net edge = 0.79% (filtered out)
3. **Just above threshold:** net edge = 0.81% (passes filter)
4. **Zero edge:** identical prices after fees
5. **Negative edge:** fees exceed gross edge
6. **High fee platform:** one platform with 2%+ taker fee
7. **Low fee platform:** one platform with 0.1% taker fee
8. **Asymmetric fees:** vastly different fee structures
9. **Max gas impact:** gas estimate = $0.50 on small position ($50)
10. **Negligible gas:** gas estimate = $0.01
11. **Large spread:** >5% gross edge
12. **Complementary pricing:** Polymarket YES + Kalshi NO arbitrage
13. **Inverse complementary:** Polymarket NO + Kalshi YES arbitrage
14. **Edge at boundary prices:** prices near 0.00 or 1.00
15. **Realistic scenario:** actual Polymarket/Kalshi price pair from manual research

### AC2: Decimal.js Installation and FinancialMath Utility

**Given** the `decimal.js` package is installed
**When** the developer inspects `src/common/utils/financial-math.ts`
**Then** it exports a `FinancialMath` class with static methods:
- `calculateGrossEdge(buyPrice: Decimal, sellPrice: Decimal): Decimal`
- `calculateNetEdge(grossEdge: Decimal, buyPrice: Decimal, sellPrice: Decimal, buyFeeSchedule: FeeSchedule, sellFeeSchedule: FeeSchedule, gasEstimateUsd: Decimal, positionSizeUsd: Decimal): Decimal`
- `isAboveThreshold(netEdge: Decimal, threshold: Decimal): boolean`

**And** all methods use `Decimal` type from `decimal.js` (never native `number` for financial calculations)
**And** a companion spec file `financial-math.spec.ts` exists that validates all 15+ CSV scenarios pass with exact expected output
**And** `Decimal` precision is configured to 20 significant digits

**Given** the edge formula
**When** gross edge is calculated
**Then** it uses: `|buyPrice - (1 - sellPrice)|`

**Given** the net edge formula
**When** net edge is calculated
**Then** it uses:
```
buyFeeCost = buyPrice × (buyFeeSchedule.takerFeePercent / 100)
sellFeeCost = sellPrice × (sellFeeSchedule.takerFeePercent / 100)
gasFraction = gasEstimateUsd / positionSizeUsd
netEdge = grossEdge - buyFeeCost - sellFeeCost - gasFraction
```

**CRITICAL:** Fees are percentage-based, applied to the trade price — NOT flat subtraction from edge.
**CRITICAL:** `FeeSchedule.takerFeePercent` uses 0-100 scale (2.0 = 2%). Must divide by 100 before multiplication. FinancialMath handles this conversion internally — callers pass `FeeSchedule` objects unchanged.

### AC3: No New Fee Type — Reuse Existing FeeSchedule

**Given** the existing `FeeSchedule` interface in `src/common/types/`
**When** FinancialMath methods need fee information
**Then** they accept `FeeSchedule` objects directly (one per platform leg)
**And** NO new `FeeBreakdown` type is created — `FeeSchedule` already contains `takerFeePercent` which is all that's needed
**And** gas estimate is passed separately as a `Decimal` parameter (it's not a platform fee, it's a transaction cost)

### AC4: Contract Pair Config Schema with Validation

**Given** a contract pairs YAML config schema is defined
**When** the engine loads `config/contract-pairs.yaml` at startup
**Then** each pair is validated with `class-validator` decorators:
- `polymarketContractId` (required, string, non-empty)
- `kalshiContractId` (required, string, non-empty)
- `eventDescription` (required, string, non-empty)
- `operatorVerificationTimestamp` (required, ISO 8601 datetime)
- `primaryLeg` (optional, enum: "kalshi" | "polymarket", default "kalshi")

**And** startup fails with clear error messages if:
- Any required field is missing
- Duplicate `polymarketContractId` or `kalshiContractId` values exist
- More than 30 pairs are configured (soft warning, not hard block)
- `operatorVerificationTimestamp` is not valid ISO 8601

**And** `class-validator` and `class-transformer` packages are installed

**Note:** YAML chosen over JSON (architecture default) because operators hand-edit this file and YAML is more readable for manual curation. This is a deliberate deviation from the architecture's "JSON files for configuration" statement. Also install `js-yaml` for parsing.

### AC5: Migration Rollback Strategy

**Given** the developer creates down-migrations for data-bearing tables
**When** rollback is tested locally
**Then** companion `down.sql` files exist for:
- `20260212222514_add_order_book_and_health_tables` (drops `order_book_snapshots` and `platform_health_logs`)
- `20260215035740_add_platform_enum` (reverts enum migration)

**And** the `20260211094744_init` migration is excluded — it creates the foundational `system_metadata` table and Prisma baseline; rolling back init means dropping the entire database, which is already handled by `prisma migrate reset`

**And** rollback of `add_platform_enum` → `add_order_book_and_health_tables` succeeds cleanly in local Docker (apply, rollback, re-apply cycle)
**And** a `docs/migration-rollback.md` or section in existing docs describes the rollback procedure

### AC6: Existing Test Suite Regression

**Given** all Sprint 0 changes are complete
**When** `pnpm test` runs
**Then** all 249 existing tests continue to pass
**And** new tests for `FinancialMath` utility add 15+ test cases
**And** new tests for config validation add 5+ test cases

## Tasks / Subtasks

- [x] Task 1: Financial Math Test Design (AC: #1)
  - [x] 1.1 Research 3-5 real Polymarket/Kalshi price pairs for realistic scenarios
  - [x] 1.2 Hand-calculate each scenario using the CORRECT formula (fees applied to prices, not flat subtraction)
  - [x] 1.3 Create CSV file with 15+ scenarios, platform-agnostic column names
  - [x] 1.4 Document formula derivation in CSV header comments
  - [x] 1.5 Cross-verify threshold boundary scenarios (0.79%, 0.80%, 0.81%) with extra precision

- [x] Task 2: Decimal.js + FinancialMath Setup (AC: #2, #3)
  - [x] 2.1 Install `decimal.js` (`pnpm add decimal.js`)
  - [x] 2.2 Create `FinancialMath` utility class in `src/common/utils/financial-math.ts`
  - [x] 2.3 Implement `calculateGrossEdge` — accepts buy/sell prices (platform-agnostic)
  - [x] 2.4 Implement `calculateNetEdge` — accepts two `FeeSchedule` objects, handles 0-100 → 0-1 conversion internally
  - [x] 2.5 Implement `isAboveThreshold`
  - [x] 2.6 Add NaN/Infinity input guards (reject with descriptive error, following Epic 2's NaN guard pattern)
  - [x] 2.7 Write comprehensive spec file loading CSV scenarios
  - [x] 2.8 Export from `src/common/utils/index.ts`

- [x] Task 3: Config Schema + Validation (AC: #4)
  - [x] 3.1 Install `class-validator`, `class-transformer`, and `js-yaml`
  - [x] 3.2 Create `ContractPairDto` with validation decorators in `src/modules/contract-matching/dto/`
  - [x] 3.3 Create `ContractPairsConfigDto` (array wrapper with duplicate check, max-length warning)
  - [x] 3.4 Create sample `config/contract-pairs.example.yaml` with 2-3 example pairs
  - [x] 3.5 Write validation tests (valid config, missing fields, duplicates, bad timestamps)

- [x] Task 4: Migration Rollback Strategy (AC: #5)
  - [x] 4.1 Create `down.sql` for `20260215035740_add_platform_enum` migration
  - [x] 4.2 Create `down.sql` for `20260212222514_add_order_book_and_health_tables` migration
  - [x] 4.3 Test rollback in local Docker (apply, rollback, re-apply)
  - [x] 4.4 Document rollback procedure (include why `init` migration is excluded)

- [x] Task 5: Regression Gate (AC: #6)
  - [x] 5.1 Run full test suite, confirm 249 existing tests pass
  - [x] 5.2 Run `pnpm lint` and fix any issues
  - [x] 5.3 Verify no import boundary violations (common/ must not import from modules/)

## Dev Notes

### Architecture Constraints

- `FinancialMath` goes in `src/common/utils/` — it's a pure utility, no module dependencies
- Reuse existing `FeeSchedule` from `src/common/types/` — do NOT create a new FeeBreakdown type
- Contract pair DTOs go in `src/modules/contract-matching/dto/` — domain validation belongs with the contract-matching module, not in common/config/
- **DO NOT** create the `contract_matches` Prisma migration here — that belongs to Story 3.4
- **DO NOT** create detection service or arbitrage module — that's Story 3.2

### Fee Calculation — CRITICAL CORRECTNESS NOTE

**The PRD's prose formula is WRONG. The PRD's worked example is CORRECT. Follow the example.**

PRD prose says: `Net Edge = |Polymarket Price - Kalshi Price| - Total Fees - Gas Estimate`
This implies flat fee subtraction — **INCORRECT**.

PRD example says: `Polymarket taker fee: 0.02 × 0.58 = 0.0116` — fees applied to prices.

**Correct formula:**
```
grossEdge = |buyPrice - (1 - sellPrice)|
buyFeeCost = buyPrice × (takerFeePercent / 100)     // e.g., 0.58 × (2.0/100) = 0.0116
sellFeeCost = sellPrice × (takerFeePercent / 100)    // e.g., 0.62 × (1.5/100) = 0.0093
gasFraction = gasEstimateUsd / positionSizeUsd        // e.g., 0.10 / 100.00 = 0.001
netEdge = grossEdge - buyFeeCost - sellFeeCost - gasFraction
```

**FeeSchedule uses 0-100 scale** (e.g., `takerFeePercent: 2.0` means 2%). FinancialMath MUST divide by 100 before multiplying by price. This conversion is encapsulated inside FinancialMath — callers pass raw `FeeSchedule` objects.

### Decimal.js Configuration

```typescript
import Decimal from 'decimal.js';

// Configure for financial precision
Decimal.set({
  precision: 20,       // 20 significant digits
  rounding: Decimal.ROUND_HALF_UP,
  toExpNeg: -18,       // Don't use exponential notation for small numbers
  toExpPos: 20,
});
```

### Existing Codebase Patterns to Follow

- **File naming:** kebab-case (`financial-math.ts`, `financial-math.spec.ts`)
- **Test co-location:** spec files next to source files
- **Utility exports:** re-export from `src/common/utils/index.ts`
- **Type exports:** check existing `src/common/types/` files for pattern — `FeeSchedule` is already there
- **NaN guards:** follow Epic 2 pattern — validate inputs, reject NaN/Infinity/null/undefined with descriptive errors
- **Testing framework:** Vitest with `describe`/`it`/`expect`, use `unplugin-swc` for decorator support

### Dependencies to Install

```bash
pnpm add decimal.js class-validator class-transformer js-yaml
pnpm add -D @types/js-yaml
```

Note: `decimal.js` has built-in TypeScript types — no separate `@types/` package needed.

### What NOT to Do (Scope Guard)

- Do NOT create a new `FeeBreakdown` type — reuse existing `FeeSchedule`
- Do NOT create the arbitrage detection module structure (creating the `__tests__/` directory for CSV data is acceptable — it's test data, not module scaffolding)
- Do NOT create Prisma migrations for `contract_matches` (Story 3.4)
- Do NOT implement detection cycle or opportunity filtering logic
- Do NOT touch connectors/ directory
- Do NOT modify existing services or modules
- Do NOT add EventEmitter2 events (no domain events in Sprint 0)
- Keep changes additive — new files only, no modifications to existing code except `index.ts` re-exports

### Config Format Decision

YAML chosen over architecture's default JSON because:
- Operators hand-edit contract pairs (FR-CM-01: manual curation of 20-30 pairs)
- YAML is more readable for manual curation workflow
- JSON requires precise comma/bracket syntax — error-prone for manual editing
- This is a deliberate, documented deviation from architecture's "JSON files for configuration" statement

### Project Structure Notes

New files to create:
```
src/common/utils/financial-math.ts
src/common/utils/financial-math.spec.ts
src/modules/contract-matching/dto/contract-pair.dto.ts
src/modules/contract-matching/dto/contract-pair.dto.spec.ts
config/contract-pairs.example.yaml
src/modules/arbitrage-detection/__tests__/edge-calculation-scenarios.csv
prisma/migrations/20260212222514_add_order_book_and_health_tables/down.sql
prisma/migrations/20260215035740_add_platform_enum/down.sql
docs/migration-rollback.md
```

### Out of Scope: Planning Doc Alignment

The Epic 2 retro identified stale architecture doc content (e.g., Polymarket auth still says "AES-256 encrypted keystore" but actual implementation uses direct private key with SDK-managed auth). This is a housekeeping task tracked separately — NOT part of Sprint 0. Sprint 0 is pure implementation prep.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3 Sprint 0]
- [Source: _bmad-output/implementation-artifacts/epic-2-retro-2026-02-15.md#Epic 3 Preparation Plan]
- [Source: _bmad-output/planning-artifacts/architecture.md#Technology Stack]
- [Source: CLAUDE.md#Domain Rules — edge calculation, price normalization]
- [Source: CLAUDE.md#Module Dependency Rules — common/ constraints]
- [Source: Epic 2 Retro Q4 — correct fee application formula: fee × price, not flat subtraction]

### Previous Story Intelligence (Epic 2)

- **249 tests passing** — regression gate baseline
- **NaN guard pattern** established in Story 2.2 — apply to FinancialMath (reject NaN inputs)
- **Platform enum** (KALSHI/POLYMARKET) already in Prisma schema — use consistently
- **`toPlatformEnum()` utility** exists in `src/common/utils/platform.ts` — follow same pattern for new utils
- **`FeeSchedule` type** exists in `src/common/types/` with `takerFeePercent` on 0-100 scale — reuse directly
- **SDK-level mocking** pattern — mock at library level, not HTTP level

### Git Intelligence

Recent commits follow pattern: `feat: <description>` for new functionality. Sprint 0 should use:
- `feat: add decimal.js financial math utility with edge calculation`
- `feat: add contract pair config schema with class-validator`
- `chore: add migration rollback scripts`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

N/A — no debug issues encountered.

### Completion Notes List

- **Task 1:** Created 16 hand-verified CSV scenarios covering all 15 required categories. Each scenario verified with decimal.js precision=20. Threshold boundary scenarios engineered to produce exact 0.79%, 0.80%, 0.81% net edges by adjusting gas parameters.
- **Task 2:** Installed decimal.js. Created FinancialMath class with calculateGrossEdge, calculateNetEdge, isAboveThreshold. All methods use Decimal types. NaN/Infinity/zero-division guards implemented. Spec file loads CSV scenarios dynamically — 55 tests (16 gross + 16 net + 16 threshold + 6 guard + 1 CSV count).
- **Task 3:** Installed class-validator, class-transformer, js-yaml. Created ContractPairDto with all required decorators (IsString, IsNotEmpty, IsISO8601, IsEnum). Created ContractPairsConfigDto with static validateDuplicatesAndLimits method for duplicate detection and >30 pair warning. Added reflect-metadata via test/setup.ts for decorator support. 10 validation tests.
- **Task 4:** Created down.sql for both data-bearing migrations. add_platform_enum rollback reverts enum columns to TEXT and drops Platform type. add_order_book_and_health_tables rollback drops both tables. init migration excluded per AC. docs/migration-rollback.md documents procedure.
- **Task 5:** Full regression: 314 tests pass (249 existing + 65 new). Lint clean. No import boundary violations in common/.

### Code Review Fixes Applied

- **M1 (MEDIUM):** Replaced global `Decimal.set()` with `Decimal.clone()` → exported `FinancialDecimal` class in `financial-math.ts`. Prevents global config pollution if other modules import `decimal.js`.
- **M2 (MEDIUM):** Added comment documenting CSV parser limitations in `financial-math.spec.ts` (no escaped quotes/newline support — acceptable for controlled test data).
- **M3 (MEDIUM):** Added comment in `contract-pair.dto.ts` documenting that startup validation wiring belongs to Story 3.1, clarifying AC4 scope boundary.

### File List

New files:
- `src/modules/arbitrage-detection/__tests__/edge-calculation-scenarios.csv`
- `src/common/utils/financial-math.ts`
- `src/common/utils/financial-math.spec.ts`
- `src/modules/contract-matching/dto/contract-pair.dto.ts`
- `src/modules/contract-matching/dto/contract-pair.dto.spec.ts`
- `config/contract-pairs.example.yaml`
- `prisma/migrations/20260215035740_add_platform_enum/down.sql`
- `prisma/migrations/20260212222514_add_order_book_and_health_tables/down.sql`
- `docs/migration-rollback.md`
- `test/setup.ts`

Modified files:
- `src/common/utils/index.ts` (added FinancialMath export)
- `vitest.config.ts` (added setupFiles for reflect-metadata)
- `package.json` / `pnpm-lock.yaml` (new dependencies)
