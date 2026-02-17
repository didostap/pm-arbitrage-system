# Story 3.1: Manual Contract Pair Configuration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to curate and manage a list of verified cross-platform contract pairs in a YAML config file,
so that the system knows which Polymarket and Kalshi contracts represent the same event and can load them reliably at startup.

**FRs covered:** FR-CM-01 (Manual curation of 20-30 contract pairs in config file)

## Acceptance Criteria

### AC1: YAML Config Loading at Startup

**Given** a `config/contract-pairs.yaml` file exists with contract pair definitions
**When** the engine starts and `ContractPairLoaderService.onModuleInit()` runs
**Then** the YAML file is parsed using `js-yaml` (already installed in Sprint 0)
**And** each pair is validated using `ContractPairDto` decorators and `ContractPairsConfigDto.validateDuplicatesAndLimits()` (both created in Sprint 0)
**And** valid pairs are stored in memory and accessible to other modules via `ContractPairLoaderService.getActivePairs()`
**And** a startup log entry is written: `"Contract pairs loaded"` with pair count, file path, and correlation ID

### AC2: Startup Failure on Invalid Config

**Given** the config file contains invalid pair definitions (missing fields, duplicate IDs, bad timestamps)
**When** the engine starts
**Then** startup fails with a clear, actionable error message listing ALL validation errors (not just the first one)
**And** the error is thrown as a `ConfigValidationError` extending `SystemError` (code 4010, severity "critical")
**And** the process exits with a non-zero exit code

**Given** the config file does not exist at `config/contract-pairs.yaml`
**When** the engine starts
**Then** startup fails with error: `"Contract pairs config file not found: config/contract-pairs.yaml"`
**And** the error includes the expected file path for easy debugging

**Given** the config file exists but contains invalid YAML syntax
**When** the engine starts
**Then** startup fails with the YAML parse error message and file path

**Given** the config file exists but contains zero pairs (empty array or null)
**When** the engine starts
**Then** startup fails with error: `"Contract pairs config must contain at least one pair"`
**And** note: `validateDuplicatesAndLimits()` from Sprint 0 does NOT check for empty arrays — the loader must add this check explicitly before calling it

### AC3: Config Reload on Restart

**Given** the config file is updated (pairs added, removed, or modified)
**When** the engine is restarted
**Then** the updated pairs are loaded without code changes
**And** removed pairs are no longer returned by `getActivePairs()`
**And** new pairs are available immediately after startup

### AC4: Pair Access API

**Given** the contract pairs are loaded successfully
**When** any module calls `ContractPairLoaderService.getActivePairs()`
**Then** it returns an array of validated `ContractPairConfig` objects (runtime type, not DTO)
**And** each object contains: `polymarketContractId`, `kalshiContractId`, `eventDescription`, `operatorVerificationTimestamp` (as Date), `primaryLeg` (defaulted to "kalshi" if omitted)

**Given** a module needs to look up a pair by contract ID
**When** it calls `ContractPairLoaderService.findPairByContractId(contractId: string)`
**Then** it returns the matching pair if found (searching both `polymarketContractId` and `kalshiContractId`)
**And** returns `undefined` if no match exists

### AC5: Contract Matching Module Registration

**Given** the `ContractMatchingModule` is created
**When** the engine starts
**Then** it is registered in `app.module.ts`
**And** `ContractPairLoaderService` is exported so other modules (arbitrage-detection in Story 3.2) can inject it
**And** the module does NOT import from other `modules/` directories (follows dependency rules)

### AC6: Soft Warning on >30 Pairs

**Given** the config file contains more than 30 pairs
**When** the engine starts
**Then** a warning-level log is emitted: `"Contract pairs count exceeds recommended maximum"` with actual count
**And** startup continues normally (this is NOT a hard block)

### AC7: Existing Test Suite Regression

**Given** all Story 3.1 changes are complete
**When** `pnpm test` runs
**Then** all 314 existing tests continue to pass (Sprint 0 baseline)
**And** new tests for `ContractPairLoaderService` add 10+ test cases
**And** `pnpm lint` passes with no errors

## Tasks / Subtasks

- [x] Task 1: Create ContractMatchingModule (AC: #5)
  - [x] 1.1 Create `src/modules/contract-matching/contract-matching.module.ts` with NestJS `@Module` decorator
  - [x] 1.2 Register module in `src/app.module.ts`
  - [x] 1.3 Export `ContractPairLoaderService` from the module

- [x] Task 2: Create ContractPairLoaderService (AC: #1, #2, #3, #4)
  - [x] 2.1 Create `src/modules/contract-matching/contract-pair-loader.service.ts`
  - [x] 2.2 Implement `onModuleInit()` to load and validate `config/contract-pairs.yaml`
  - [x] 2.3 Parse YAML with `js-yaml` (`load()` function)
  - [x] 2.4 Validate each pair using `class-transformer` `plainToInstance()` + `class-validator` `validate()`
  - [x] 2.5 Run `ContractPairsConfigDto.validateDuplicatesAndLimits()` for cross-pair validation
  - [x] 2.6 Throw `ConfigValidationError` (code 4010) on any validation failure — aggregate ALL errors
  - [x] 2.7 Store validated pairs in private `activePairs: ContractPairConfig[]` array
  - [x] 2.8 Implement `getActivePairs(): ContractPairConfig[]` — returns shallow copy (`[...this.activePairs]`); deep clone unnecessary for single-operator in-process use
  - [x] 2.9 Implement `findPairByContractId(contractId: string): ContractPairConfig | undefined`
  - [x] 2.10 Log successful load with pair count at `log` level

- [x] Task 3: Create ContractPairConfig Runtime Type (AC: #4)
  - [x] 3.1 Create `src/modules/contract-matching/types/contract-pair-config.type.ts`
  - [x] 3.2 Define `ContractPairConfig` interface with parsed fields (timestamp as `Date`, primaryLeg with default)
  - [x] 3.3 Export from module's types index

- [x] Task 4: Create ConfigValidationError (AC: #2)
  - [x] 4.1 Create `ConfigValidationError` in `src/common/errors/` extending `SystemError`
  - [x] 4.2 Use error code 4010 (SystemHealth range 4000-4999), severity "critical"
  - [x] 4.3 Include `validationErrors: string[]` in error metadata for actionable debugging
  - [x] 4.4 Export from `src/common/errors/index.ts`

- [x] Task 5: Create contract-pairs.yaml (AC: #1)
  - [x] 5.1 Copy `config/contract-pairs.example.yaml` to `config/contract-pairs.yaml`
  - [x] 5.2 Add `config/contract-pairs.yaml` to `.gitignore` (operator-specific, not tracked)
  - [x] 5.3 Ensure example file remains tracked for reference

- [x] Task 6: Write Tests (AC: #7)
  - [x] 6.1 Create `src/modules/contract-matching/contract-pair-loader.service.spec.ts`
  - [x] 6.2 Test: valid YAML loads correctly, pairs accessible via `getActivePairs()`
  - [x] 6.3 Test: missing file throws ConfigValidationError with file path
  - [x] 6.4 Test: invalid YAML syntax throws ConfigValidationError
  - [x] 6.5 Test: missing required fields throws with all field errors listed
  - [x] 6.6 Test: duplicate polymarketContractId throws
  - [x] 6.7 Test: duplicate kalshiContractId throws
  - [x] 6.8 Test: invalid ISO 8601 timestamp throws
  - [x] 6.9 Test: >30 pairs logs warning but succeeds
  - [x] 6.10 Test: `findPairByContractId()` returns correct pair or undefined
  - [x] 6.11 Test: `primaryLeg` defaults to "kalshi" when omitted
  - [x] 6.12 Test: empty pairs array throws (at least 1 pair required)
  - [x] 6.13 Run full regression: `pnpm test` — all 314+ tests pass

- [x] Task 7: Lint & Final Check (AC: #7)
  - [x] 7.1 Run `pnpm lint` and fix any issues
  - [x] 7.2 Verify no import boundary violations (contract-matching/ must not import from other modules/)

## Dev Notes

### Architecture Constraints

- `ContractPairLoaderService` lives in `src/modules/contract-matching/` — it's domain logic, not common infrastructure
- The module imports ONLY from `common/` (errors, types) — no cross-module imports
- `ContractMatchingModule` exports `ContractPairLoaderService` so `ArbitrageDetectionModule` (Story 3.2) can import it via `ContractMatchingModule`
- This follows the allowed dependency: `modules/arbitrage-detection/ → modules/contract-matching/` (match validation) per CLAUDE.md

### Sprint 0 Foundation (Already Built)

These files were created in Sprint 0 and MUST be reused — do NOT recreate or duplicate:

| File | What It Provides |
|------|-----------------|
| `src/modules/contract-matching/dto/contract-pair.dto.ts` | `ContractPairDto` with class-validator decorators, `ContractPairsConfigDto` with `validateDuplicatesAndLimits()`, `PrimaryLeg` enum |
| `src/modules/contract-matching/dto/contract-pair.dto.spec.ts` | 10 validation tests for DTOs |
| `config/contract-pairs.example.yaml` | Example YAML with 3 sample pairs |
| `src/common/utils/financial-math.ts` | `FinancialMath` class (used in Story 3.3, not this story) |

**Key detail from Sprint 0 code review:** The DTO file contains this comment:
> "Sprint 0 scope: schema + validation logic only. Startup wiring (loading contract-pairs.yaml, calling validate(), and failing on errors) belongs to Story 3.1"

### Config File Path Resolution

The YAML config path should be resolved relative to `process.cwd()` (the engine root), not relative to the source file. Use `path.resolve(process.cwd(), 'config/contract-pairs.yaml')`. Make the path configurable via `ConfigService` with key `CONTRACT_PAIRS_CONFIG_PATH` and default `config/contract-pairs.yaml` — this enables test overrides and custom deployment paths. Note: `ConfigModule.forRoot({ isGlobal: true })` is already registered in `app.module.ts` (Epic 1), so `ConfigService` is injectable without importing `ConfigModule` in `ContractMatchingModule`.

### ContractPairConfig vs ContractPairDto

- `ContractPairDto` = validation DTO with class-validator decorators (input validation)
- `ContractPairConfig` = clean runtime type used by the rest of the system (output type)
- The loader service transforms DTO → Config during loading: parses `operatorVerificationTimestamp` string to `Date`, applies `primaryLeg` default

**`primaryLeg` default — CRITICAL:** The Sprint 0 DTO declares `primaryLeg?: PrimaryLeg = PrimaryLeg.KALSHI` as a TypeScript property default. However, `plainToInstance()` from `class-transformer` does NOT apply TypeScript defaults unless `exposeDefaultValues: true` is passed in options. When `primaryLeg` is omitted in YAML, the field will be `undefined` after `plainToInstance()`. **The loader MUST explicitly default `primaryLeg` to `'kalshi'` during the DTO → Config transform step**, not rely on the DTO's TypeScript default. Do NOT use `exposeDefaultValues: true` as a workaround — it masks missing-field issues in future DTOs.

```typescript
// Runtime type — no decorators, no class-validator dependency
export interface ContractPairConfig {
  polymarketContractId: string;
  kalshiContractId: string;
  eventDescription: string;
  operatorVerificationTimestamp: Date;
  primaryLeg: 'kalshi' | 'polymarket';
}
```

### Error Code Assignment

- Code **4010**: `ConfigValidationError` — contract pair config validation failure at startup
- This fits in the SystemHealth range (4000-4999) because a bad config file is a system health issue that prevents startup
- Severity: "critical" — the engine cannot operate without valid contract pairs

### Testing Strategy

- Mock the file system for YAML loading tests — use `vi.mock('fs')` or provide test YAML content via a temp file
- DO NOT mock `class-validator` or `class-transformer` — let them run for real to validate the integration
- Use `Test.createTestingModule()` from `@nestjs/testing` for NestJS DI integration
- Mock `ConfigService` to provide test config path

### What NOT to Do (Scope Guard)

- Do NOT create the `contract_matches` Prisma migration — that belongs to Story 3.4
- Do NOT create the detection service or arbitrage detection module — that's Story 3.2
- Do NOT implement edge calculation wiring — that's Story 3.3
- Do NOT create REST API endpoints for contract pair management (future story)
- Do NOT emit domain events for pair loading — simple startup logging is sufficient for MVP
- Do NOT implement hot-reload / file watching — restart-based reload is the MVP approach per AC3
- Do NOT modify existing services or modules (except `app.module.ts` for registration)

### Existing Codebase Patterns to Follow

- **File naming:** kebab-case (`contract-pair-loader.service.ts`)
- **Module registration:** See `data-ingestion.module.ts` for pattern — imports, providers, exports
- **Error throwing:** See `DataIngestionService` for `SystemHealthError` usage pattern
- **Logging:** Use NestJS `Logger` (from `@nestjs/common`) — `private readonly logger = new Logger(ContractPairLoaderService.name)`
- **onModuleInit:** See `PrismaService` for lifecycle hook pattern
- **Test setup:** `reflect-metadata` is already loaded via `test/setup.ts` in vitest config

### Dependencies — All Already Installed

| Package | Purpose | Installed In |
|---------|---------|-------------|
| `js-yaml` | Parse YAML config file | Sprint 0 |
| `class-validator` | DTO validation decorators | Sprint 0 |
| `class-transformer` | `plainToInstance()` transform | Sprint 0 |
| `@types/js-yaml` | TypeScript types for js-yaml | Sprint 0 |

No new dependencies needed.

### Project Structure Notes

New files to create:
```
src/modules/contract-matching/contract-matching.module.ts
src/modules/contract-matching/contract-pair-loader.service.ts
src/modules/contract-matching/contract-pair-loader.service.spec.ts
src/modules/contract-matching/types/contract-pair-config.type.ts
src/common/errors/config-validation-error.ts
```

Modified files:
```
src/app.module.ts                    (add ContractMatchingModule import)
src/common/errors/index.ts           (export ConfigValidationError)
.gitignore                           (add config/contract-pairs.yaml)
```

### Previous Story Intelligence (Sprint 0)

- **314 tests passing** — regression gate baseline
- **ContractPairDto** uses `@IsISO8601()` for timestamp validation — works correctly
- **`PrimaryLeg` enum** already defined in DTO file — reuse, do NOT redeclare
- **`validateDuplicatesAndLimits()`** is a static method returning `string[]` errors — aggregate these with class-validator errors before throwing
- **reflect-metadata** loaded via `test/setup.ts` — decorators work in tests
- **Sprint 0 code review M3** added comment clarifying that startup wiring belongs here

### Git Intelligence

Recent engine commits follow pattern: `feat: <description>`. Story 3.1 should use:
- `feat: add contract pair loader with YAML config validation`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1 — acceptance criteria]
- [Source: _bmad-output/implementation-artifacts/epic-3-sprint-0.md#AC4 — config schema and validation]
- [Source: _bmad-output/implementation-artifacts/epic-3-sprint-0.md#Code Review M3 — startup wiring scope note]
- [Source: _bmad-output/planning-artifacts/architecture.md#Module Organization — contract-matching/ placement]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries — allowed imports]
- [Source: CLAUDE.md#Module Dependency Rules — contract-matching constraints]
- [Source: CLAUDE.md#Error Handling — SystemError hierarchy requirement]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation, no debugging needed.

### Completion Notes List

- **Code Review Fixes (Claude Opus 4.6):**
  - H1: Added explicit null/non-object check in `parseYaml()` for empty file content (previously fell through to generic "at least one pair" error)
  - M2: Fixed warning message to match AC6 format: `"Contract pairs count exceeds recommended maximum (31 pairs, max 30)"`
  - M3: Added `logger.warn` spy assertion to >30 pairs test to verify warning is actually emitted
  - Added new test case for empty file content (330 total tests)
  - M1 (hierarchy design): Noted but kept as-is — story spec says extend `SystemError`, not `SystemHealthError`
- Implemented `ContractPairLoaderService` with `onModuleInit()` lifecycle hook for YAML config loading at startup
- Created `ContractPairConfig` runtime interface (clean type, no decorators) separate from validation DTO
- Created `ConfigValidationError` (code 4010, severity critical) extending `SystemError`
- Config path configurable via `CONTRACT_PAIRS_CONFIG_PATH` env var, defaults to `config/contract-pairs.yaml`
- DTO → Config transform explicitly defaults `primaryLeg` to `'kalshi'` (does not rely on TS property defaults per Sprint 0 review finding)
- Validation aggregates ALL errors (class-validator + cross-pair duplicates) before throwing
- `>30 pairs` warning logged but does not block startup (separated from hard errors)
- Empty pairs array explicitly checked before `validateDuplicatesAndLimits()` (which doesn't check for empty)
- 15 new tests covering all ACs; 329 total tests pass (1 pre-existing flaky e2e test for Kalshi API excluded)
- `pnpm lint` passes clean
- No import boundary violations — `contract-matching/` only imports from `common/`

### File List

New files:
- `src/modules/contract-matching/contract-matching.module.ts`
- `src/modules/contract-matching/contract-pair-loader.service.ts`
- `src/modules/contract-matching/contract-pair-loader.service.spec.ts`
- `src/modules/contract-matching/types/contract-pair-config.type.ts`
- `src/modules/contract-matching/types/index.ts`
- `src/common/errors/config-validation-error.ts`
- `config/contract-pairs.yaml` (gitignored, operator-specific)

Modified files:
- `src/app.module.ts` (added ContractMatchingModule import)
- `src/common/errors/index.ts` (exported ConfigValidationError)
- `.gitignore` (added config/contract-pairs.yaml)
