# Story 10.0-2b: Outcome Direction Matching Validation

Status: done

## Story

As an operator,
I want the contract matching pipeline to validate that matched contracts resolve YES for the same real-world outcome,
so that the system never enters unhedged directional bets disguised as arbitrage opportunities.

## Acceptance Criteria

### AC 1: ContractSummary Interface — Outcome Metadata
**Given** the `ContractSummary` interface in `common/interfaces/contract-catalog-provider.interface.ts`
**When** this story is implemented
**Then** it includes `outcomeLabel?: string` (the outcome this contract's YES represents, e.g. "Michael Page wins")
**And** it includes `outcomeTokens?: OutcomeToken[]` (all available outcome tokens for multi-outcome markets)
**And** a new `OutcomeToken` interface exists with `{ tokenId: string; outcomeLabel: string }`
[Source: Change Proposal CP-1; Architecture: `ContractSummary` lacks outcome metadata]

### AC 2: Polymarket Catalog Provider — Parse Outcomes Array
**Given** the Polymarket Gamma API returns `outcomes` (JSON string, e.g. `'["Fighter A wins","Fighter B wins"]'`) alongside `clobTokenIds` (JSON string array)
**When** `mapToContractSummary()` builds a `ContractSummary`
**Then** it parses the `outcomes` JSON array and pairs each label with its positionally-correlated `clobTokenIds` entry into `outcomeTokens[]`
**And** `outcomeLabel` is set to the label matching `clobTokenIds[0]` (the token currently used for trading)
**And** the `PolymarketMarket` local interface adds the `outcomes?: string` field
[Source: Change Proposal CP-2; Verified: Polymarket Gamma API docs confirm `outcomes` field exists on market response]

### AC 3: Kalshi Catalog Provider — Extract yes_sub_title
**Given** the Kalshi API returns `yes_sub_title` ("Shortened title for the yes side of this market") on market detail responses
**When** `mapToContractSummary()` builds a `ContractSummary`
**Then** `outcomeLabel` is set to `yes_sub_title` when available (fallback: `undefined`)
[Source: Change Proposal CP-3; Verified: `KalshiMarketDetail` interface already has `yes_sub_title?: string` at `kalshi-sdk.d.ts:97`]

### AC 4: Post-Scoring Outcome Direction Validation Gate
**Given** the candidate discovery pipeline scores a match via LLM
**When** the score meets or exceeds the auto-approve threshold
**Then** a direction validation step runs BEFORE creating the `ContractMatch` DB record
**And** validation compares `outcomeLabel` on both sides: if both are available and indicate different participants in a head-to-head event, the match is flagged as direction-mismatched
**And** direction-mismatched matches are NOT auto-approved regardless of LLM score
[Source: Change Proposal CP-4; Root cause: no validation gate between LLM scoring (~line 302) and auto-approve (~line 312) in `candidate-discovery.service.ts`]

### AC 5: Self-Correction via Token Swap
**Given** a direction mismatch is detected AND the Polymarket side has `outcomeTokens[]` with multiple entries
**When** the validator finds a token in `outcomeTokens[]` whose `outcomeLabel` aligns with the Kalshi `outcomeLabel` (alignment algorithm: normalize both labels by lowercasing and stripping common suffixes like "wins"/"will win"/"to win", then check if the Kalshi participant name is contained in the Polymarket label or vice versa; if ambiguous, delegate to a lightweight LLM call for semantic comparison)
**Then** the match candidate's `clobTokenId` is swapped to the correct token
**And** `outcomeLabel` is updated to reflect the corrected outcome
**And** the match proceeds through normal scoring with the corrected data
**And** if no aligning token is found, the match is downgraded to manual review (absolute score cap at 50 regardless of LLM score, populate `divergenceNotes` with explanation)
[Source: Change Proposal CP-4 self-correction mechanism]

### AC 6: Schema Migration — Persist Outcome Labels
**Given** the `contract_matches` table in the Prisma schema
**When** the migration runs
**Then** two new nullable text columns exist: `polymarket_outcome_label` and `kalshi_outcome_label`
**And** the `ContractMatch` Prisma model exposes these fields
**And** `candidate-discovery.service.ts` persists outcome labels when creating new matches
[Source: Change Proposal CP-5]

### AC 7: Reject Confirmed Mis-Matches
**Given** the 3 confirmed mis-matched UFC pairs (match ID prefixes: `339a6d3e`, `85b96578`, `ec7aa3cb` — use `startsWith` lookup; operation is idempotent, skips if IDs not found)
**When** the audit CLI command runs (initial cleanup step before full audit)
**Then** all 3 are set to `operatorApproved = false` with `operatorRationale` documenting the direction mismatch
**And** their `lastAnnualizedReturn` and `lastNetEdge` are set to `null`
**And** they are excluded from the detection cycle immediately
[Source: Change Proposal CP-6 Phase A; Evidence table in sprint change proposal]

### AC 8: Revalidation Audit CLI Command
**Given** approved matches exist in the database
**When** the operator runs the revalidation audit command
**Then** the command extracts and compares outcome direction for each approved match using LLM analysis (batched, configurable via `AUDIT_LLM_BATCH_SIZE` default 10, `AUDIT_LLM_DELAY_MS` default 1000)
**And** for matches with active order books, it checks if `polyBestAsk + kalshiBestAsk ≈ 1.00` (tolerance configurable via `AUDIT_COMPLEMENTARY_TOLERANCE` default `0.05`) as a complementary-contract signal, using `Decimal` arithmetic
**And** flagged matches (aligned: false | uncertain) are set to `operatorApproved = false` with explanation in `operatorRationale`
**And** flagged matches are immediately excluded from the detection cycle
**And** the command also backfills `polymarketOutcomeLabel` and `kalshiOutcomeLabel` for all processed matches
**And** the command outputs a summary report to stdout (total audited, flagged count, categories of flags, backfill count)
**And** the command handles LLM failures gracefully (retry 3x with backoff, skip with warning on persistent failure)
**And** the command handles missing order book data gracefully (skip complementary check, log warning)
[Source: Change Proposal CP-6 Phase B; Implementation: standalone NestJS CLI command]

**Release criteria (post-deployment, not blocking story completion):** Operator runs audit against production data, reviews all flagged matches, zero unreviewed flags remain.

### AC 9: Dashboard — Outcome Label Display
**Given** the dashboard match detail page and matches table
**When** outcome labels are available for a match
**Then** the match detail page shows both `polymarketOutcomeLabel` and `kalshiOutcomeLabel`
**And** the matches table shows outcome direction information (column or tooltip)
**And** mismatched outcome directions are visually flagged
[Source: Change Proposal UX impact; Team Agreement #18: vertical slice minimum]

### AC 10: Test Coverage
**Given** all new code in this story
**When** tests are run
**Then** every new file has a co-located spec file
**And** the validation gate has tests for: matching outcomes (pass-through), opposite outcomes (flag), missing labels (skip validation gracefully), self-correction (token swap), failed self-correction (downgrade to manual)
**And** catalog provider tests cover: outcomes parsing, missing outcomes field, malformed JSON, multi-outcome markets, mismatched `outcomes`/`clobTokenIds` array lengths (defensive), empty string `yes_sub_title` treated as absent
**And** the audit command has tests for: LLM direction extraction, complementary price detection (using `Decimal`), batch processing with rate limiting, LLM failure retry/skip, missing order book graceful skip, label backfill
[Source: CLAUDE.md testing conventions; Epic 9 retro Team Agreement #19: internal subsystem verification]

## Tasks / Subtasks

### Phase 1: Data Model Foundation (AC: #1, #6)
- [x] Task 1: Add `OutcomeToken` interface and `outcomeLabel`/`outcomeTokens` fields to `ContractSummary` in `common/interfaces/contract-catalog-provider.interface.ts` (AC: #1)
- [x] Task 2: Create Prisma migration adding `polymarket_outcome_label` (text, nullable) and `kalshi_outcome_label` (text, nullable) to `contract_matches` table. Run `prisma generate`. (AC: #6)

### Phase 2: Connector Updates (AC: #2, #3)
- [x] Task 3: Add `outcomes?: string` field to `PolymarketMarket` interface in `polymarket-catalog-provider.ts` (find `interface PolymarketMarket`) (AC: #2)
- [x] Task 4: Update `mapToContractSummary()` in `polymarket-catalog-provider.ts` (find method by name) — parse `outcomes` JSON, pair with `clobTokenIds`, populate `outcomeTokens[]` and `outcomeLabel` (AC: #2)
  - [x] 4.1: Handle missing `outcomes` field gracefully (legacy data, non-binary markets)
  - [x] 4.2: Handle malformed JSON in `outcomes` field
  - [x] 4.3: Write co-located tests in `polymarket-catalog-provider.spec.ts`
- [x] Task 5: Update `mapToContractSummary()` in `kalshi-catalog-provider.ts` (find method by name) — extract `yes_sub_title` into `outcomeLabel` (AC: #3)
  - [x] 5.1: Fallback to `undefined` when `yes_sub_title` is absent
  - [x] 5.2: Write co-located tests in `kalshi-catalog-provider.spec.ts`

### Phase 3: Validation Gate (AC: #4, #5)
- [x] Task 6: Create `OutcomeDirectionValidator` utility/service in `modules/contract-matching/` (AC: #4)
  - [x] 6.1: `validateDirection(polyContract: ContractSummary, kalshiContract: ContractSummary): DirectionValidationResult`
  - [x] 6.2: Return `{ aligned: boolean | null; correctedTokenId?: string; correctedLabel?: string; reason: string }`
  - [x] 6.3: `null` alignment = insufficient data (one or both labels missing) → skip validation, proceed normally
  - [x] 6.4: Alignment algorithm: (a) normalize both labels — lowercase, strip common suffixes ("wins", "will win", "to win"), trim whitespace; (b) check if normalized Kalshi participant name is contained in normalized Polymarket label or vice versa; (c) require minimum 4 chars on shorter name to prevent false positives (e.g., "Joe" matching "Joey"); (d) if substring check is ambiguous (both tokens partially match), delegate to a lightweight LLM call via `LlmScoringStrategy` for semantic comparison
  - [x] 6.5: Co-located spec file with test matrix: same-outcome, opposite-outcome, missing labels (one/both), partial labels, non-head-to-head markets (binary Yes/No), short names (<4 chars → skip substring, require LLM), unicode/accented characters (NFKD normalize), mismatched `outcomes`/`clobTokenIds` array lengths (defensive handling)
- [x] Task 7: Integrate validator into `candidate-discovery.service.ts` between `scoreMatch()` result and `prisma.contractMatch.create()` call (AC: #4, #5)
  - [x] 7.1: On direction mismatch with available `outcomeTokens[]` — attempt self-correction (swap `clobTokenId` to aligned token) (AC: #5)
  - [x] 7.2: On direction mismatch without self-correction — cap score at 50, set `divergenceNotes`, mark for manual review (AC: #5)
  - [x] 7.3: Persist `polymarketOutcomeLabel` and `kalshiOutcomeLabel` in `ContractMatch` creation data (AC: #6)
  - [x] 7.4: Add tests verifying the gate blocks opposite-outcome auto-approvals

### Phase 4: Data Cleanup & Audit (AC: #7, #8)
- [x] Task 8: Create data cleanup for 3 confirmed UFC mis-matches (AC: #7)
  - [x] 8.1: Set `operatorApproved = false`, document rationale, null out `lastAnnualizedReturn` and `lastNetEdge`
  - [x] 8.2: Implement as part of the audit CLI command (initial step before full audit)
- [x] Task 9: Create revalidation audit CLI command using NestJS standalone application pattern (AC: #8)
  - [x] 9.1: Fetch all `operatorApproved = true` matches
  - [x] 9.2: For each match: extract outcome direction from descriptions using `LlmScoringStrategy` (batch size `AUDIT_LLM_BATCH_SIZE`, inter-batch delay `AUDIT_LLM_DELAY_MS`)
  - [x] 9.3: For matches with active order books: instantiate connectors via DI, fetch orderbooks, check `polyBestAsk + kalshiBestAsk ≈ 1.00` (tolerance `AUDIT_COMPLEMENTARY_TOLERANCE`) using `Decimal` arithmetic. Skip gracefully if orderbook unavailable.
  - [x] 9.4: Flag mismatched/uncertain matches: set `operatorApproved = false`, populate `operatorRationale` with findings
  - [x] 9.5: Backfill `polymarketOutcomeLabel` and `kalshiOutcomeLabel` from LLM extraction results
  - [x] 9.6: Output summary report to stdout (total, flagged count, per-category breakdown, backfill count)
  - [x] 9.7: Handle rate limiting (respect existing `RateLimiter`), LLM failures (retry 3x with backoff, skip with warning), missing order book data (skip complementary check, log)
  - [x] 9.8: Co-located tests for LLM direction extraction, complementary price logic, batch processing, graceful failure handling

### Phase 5: Dashboard Vertical Slice (AC: #9)
- [x] Task 10: Backend — Add `polymarketOutcomeLabel` and `kalshiOutcomeLabel` to match response DTOs (AC: #9)
  - [x] 10.1: Update match detail DTO and list DTO
  - [x] 10.2: Ensure Swagger annotations are present
- [x] Task 11: Frontend — Display outcome labels on match detail page and matches table (AC: #9)
  - [x] 11.1: Match detail page: show both outcome labels in a dedicated "Outcome Direction" section
  - [x] 11.2: Matches table: add outcome indicator column or tooltip
  - [x] 11.3: Visual flag for mismatched outcome directions (e.g., warning icon with red text)

## Dev Notes

### Root Cause Context
The contract matching pipeline (Epic 8) has a 4-layer failure chain for head-to-head markets:
1. **Polymarket catalog** (`polymarket-catalog-provider.ts` → `mapToContractSummary()`): Blindly takes `clobTokenIds[0]` — ignores which outcome the token represents
2. **Kalshi catalog** (`kalshi-catalog-provider.ts` → `mapToContractSummary()`): Returns separate contracts per participant with no outcome metadata in `ContractSummary`
3. **TF-IDF pre-filter** (`pre-filter.service.ts`): Ranks both Kalshi sides equally (same event text = high cosine similarity)
4. **LLM scoring** (`llm-scoring.strategy.ts` → `buildPrompt()`): Prompt warns about outcome specificity but it's soft guidance, no hard constraint

This produces phantom edges of ~27-30% and APR of 1500%+ for UFC fights. If executed, these would be **unhedged directional bets** — both legs lose if the "wrong" participant wins.

### Critical File Map (Verified Against Codebase)

**Note:** Line numbers are approximate (as of 2026-03-15). Search by symbol/method name.

**Files to modify:**
| File | Change | Symbol to Find |
|------|--------|---------------|
| `common/interfaces/contract-catalog-provider.interface.ts` | Add `OutcomeToken`, `outcomeLabel`, `outcomeTokens` to `ContractSummary` | `interface ContractSummary` |
| `connectors/polymarket/polymarket-catalog-provider.ts` | Add `outcomes` to `PolymarketMarket`, update `mapToContractSummary` | `interface PolymarketMarket`, `mapToContractSummary()` |
| `connectors/kalshi/kalshi-catalog-provider.ts` | Extract `yes_sub_title` in `mapToContractSummary` | `mapToContractSummary()` |
| `modules/contract-matching/candidate-discovery.service.ts` | Insert validation gate between scoring and DB creation | Between `scoreMatch()` call and `prisma.contractMatch.create()` |
| `prisma/schema.prisma` | Add 2 columns to `ContractMatch` model | `model ContractMatch` |
| `modules/contract-matching/dto/contract-pair.dto.ts` | Add outcome label fields to response DTOs | Match-related DTO classes |
| `dashboard/dto/*.dto.ts` | Add outcome label fields to match DTOs | Match-related DTO classes |

**Files to create:**
| File | Purpose |
|------|---------|
| `modules/contract-matching/outcome-direction-validator.ts` | Direction validation logic |
| `modules/contract-matching/outcome-direction-validator.spec.ts` | Co-located tests |
| `modules/contract-matching/audit-revalidation.command.ts` | CLI audit command |
| `modules/contract-matching/audit-revalidation.command.spec.ts` | Co-located tests |

**Dashboard files to modify (pm-arbitrage-dashboard/):**
| File | Change |
|------|--------|
| `src/api/generated/*.ts` | Regenerate after backend DTO changes |
| Match detail page component | Add outcome direction section |
| Matches table component | Add outcome label column/tooltip |

### API Contract Details (Web-Verified)

**Polymarket Gamma API — Market Response:**
- `outcomes`: JSON string, e.g. `'["Yes","No"]'` or `'["Fighter A wins","Fighter B wins"]'`
- `clobTokenIds`: JSON string array, e.g. `'["0xabc...","0xdef..."]'`
- Arrays are **positionally correlated**: `outcomes[0]` corresponds to `clobTokenIds[0]`
- `outcomePrices`: JSON string of current prices per outcome (out of scope but available)
- [Source: Polymarket Gamma API docs, verified 2026-03-15]

**Kalshi API — Market Detail Response:**
- `yes_sub_title`: string — "Shortened title for the yes side of this market" (e.g., "Sam Patterson wins")
- `no_sub_title`: string — "Shortened title for the no side of this market" (e.g., "Sam Patterson does not win")
- `primary_participant_key`: optional string (out of scope, future enhancement)
- [Source: Kalshi REST API v2 docs at docs.kalshi.com, verified 2026-03-15]

### Existing Patterns to Follow

**Catalog provider pattern** — Both catalog providers implement `IContractCatalogProvider` (3 methods: `listActiveContracts`, `getPlatformId`, `getContractResolution`). Follow existing `mapToContractSummary` private method pattern for adding new field extraction. [Source: codebase `common/interfaces/contract-catalog-provider.interface.ts:18-22`]

**Candidate discovery scoring flow** — Current flow: `scoringStrategy.scoreMatch()` → check thresholds → `prisma.contractMatch.create()`. Insert validation between threshold check and DB create. Do NOT modify the scoring strategy itself. [Source: codebase `candidate-discovery.service.ts:302-340`]

**NestJS standalone CLI pattern** — Use `NestFactory.createApplicationContext()` for the audit command. This bootstraps DI without HTTP server. Follow `@nestjs/config` for env vars. Example: inject `PrismaService`, `LlmScoringStrategy`, platform connectors for orderbook fetching. [Source: NestJS docs "Standalone applications"]

**Test patterns** — Vitest with `vi.fn()`, `vi.mock()`. Helper factories like `makeContract()`, `makeScoringResult()`. Mock `PrismaService` with `vi.fn()` on query methods. Mock `EventEmitter2` to verify event emission. Use `ConfigService` mock with defaults map. [Source: existing specs in `modules/contract-matching/`]

**Error handling** — All errors must extend `SystemError` hierarchy. For LLM failures in the audit command, use existing `LlmScoringError` (code 4100-4199) with retry strategy. [Source: CLAUDE.md error handling; architecture error catalog]

**Financial math** — The complementary price check (`polyBestAsk + kalshiBestAsk ≈ 1.00`) uses `Decimal` arithmetic. Never use native JS operators. [Source: CLAUDE.md domain rules]

**Migration safety** — The migration adds only nullable columns with no default values. This is inherently backward-compatible: existing code ignores new columns, rollback is a standard `prisma migrate` down. No data transformation during migration. Existing 459 matches will have NULL outcome labels until backfilled by the audit command (AC 8).

**Concurrency** — The existing `@@unique([polymarketContractId, kalshiContractId])` constraint on `ContractMatch` prevents duplicate match creation from concurrent discovery runs. The validation gate does not need additional locking.

**`divergenceNotes` field** — Already exists on `ContractMatch` model (`divergence_notes` column). No schema change needed for Task 7.2.

### Previous Story Intelligence (10-0-1)

Story 10-0-1 (WebSocket Subscription Establishment) was a large story (7 phases, 17 tasks, 77+ tests). Key learnings:
- Code review found 5 CRITICAL, 8 HIGH, 8 MEDIUM issues — expect thorough review
- Pattern: extend interfaces incrementally, implement in both connectors, add paper trading delegation
- The `PaperTradingConnector` delegates to the real connector for data methods — catalog providers are NOT wrapped by paper mode (they fetch real platform data regardless of mode)
- Both connector specs use `vi.stubGlobal('fetch', fetchSpy)` pattern for API mocking

### Scope Boundaries

**In scope:**
- ContractSummary outcome metadata (CP-1)
- Both catalog providers parsing outcome labels (CP-2, CP-3)
- Post-scoring direction validation gate with self-correction (CP-4)
- Schema migration for outcome labels (CP-5)
- Reject 3 UFC mis-matches + full revalidation audit CLI (CP-6)
- Dashboard outcome label display (vertical slice)

**Out of scope (future enhancement):**
- Polymarket `outcomePrices` field extraction
- Kalshi `primary_participant_key` extraction
- Modifying the LLM scoring prompt to include outcome labels (the validation gate is the safety net, prompt improvement is separate)
- Pre-filter outcome awareness (TF-IDF layer 3 of failure chain — validation gate is sufficient)
- Automatic re-scoring of rejected matches after correction

### Project Structure Notes

- All backend code in `pm-arbitrage-engine/src/` (independent git repo — separate commits)
- Dashboard code in `pm-arbitrage-dashboard/` (separate git repo — separate commits)
- Prisma schema at `pm-arbitrage-engine/prisma/schema.prisma` — run `pnpm prisma migrate dev --name add-outcome-labels` then `pnpm prisma generate`
- New files follow kebab-case naming: `outcome-direction-validator.ts`, `audit-revalidation.command.ts`
- Co-located tests: `outcome-direction-validator.spec.ts` in same directory

### Post-Edit Checklist
1. `cd pm-arbitrage-engine && pnpm lint` — fix all errors
2. `pnpm test` — all tests pass (baseline: 2175 passing)
3. `pnpm prisma generate` — if schema changed
4. Regenerate dashboard API client if backend DTOs changed

### References

- [Source: sprint-change-proposal-2026-03-15-outcome-direction-matching.md] — Full root cause analysis, evidence table, CP-1 through CP-6
- [Source: common/interfaces/contract-catalog-provider.interface.ts:18-22] — Current ContractSummary (no outcome fields)
- [Source: connectors/polymarket/polymarket-catalog-provider.ts:159-176] — Current mapToContractSummary (blind clobTokenIds[0])
- [Source: connectors/polymarket/polymarket-catalog-provider.ts:18-24] — PolymarketMarket interface (missing outcomes)
- [Source: connectors/kalshi/kalshi-sdk.d.ts:92-105] — KalshiMarketDetail (has yes_sub_title, not extracted)
- [Source: connectors/kalshi/kalshi-catalog-provider.ts:143-187] — Kalshi mapToContractSummary (ignores yes_sub_title)
- [Source: modules/contract-matching/candidate-discovery.service.ts:302-340] — Auto-approve flow (no validation gate)
- [Source: modules/contract-matching/llm-scoring.strategy.ts:40-85] — LLM prompt (soft outcome guidance)
- [Source: prisma/schema.prisma ContractMatch model] — Missing outcome label columns
- [Source: Polymarket Gamma API docs — docs.polymarket.com] — outcomes field on market response
- [Source: Kalshi REST API v2 docs — docs.kalshi.com] — yes_sub_title, no_sub_title fields
- [Source: CLAUDE.md] — Error handling, financial math, testing conventions, naming conventions
- [Source: Epic 9 retro] — Team Agreement #18 (vertical slice), #19 (internal subsystem verification)
- [Source: PRD FR-CM-02] — Zero-tolerance contract matching error policy

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- **Phase 1 (Tasks 1-2):** Added `OutcomeToken` interface and `outcomeLabel`/`outcomeTokens` fields to `ContractSummary`. Created Prisma migration `20260315191915_add_outcome_labels` adding two nullable text columns.
- **Phase 2 (Tasks 3-5):** Extended Polymarket `PolymarketMarket` interface and Zod schema with `outcomes` field. Added `parseOutcomeTokens()` method that pairs outcomes JSON with clobTokenIds positionally. Added `outcomeLabel` extraction from Kalshi `yes_sub_title`. 9 new tests.
- **Phase 3 (Tasks 6-7):** Created `OutcomeDirectionValidator` injectable service with normalize → substring → self-correction → LLM fallback pipeline. Integrated into `processCandidate()` between scoring and DB create. Direction mismatch caps score at 50, sets divergenceNotes. Self-correction swaps clobTokenId when aligning token found. 17 new tests (13 validator + 4 integration).
- **Phase 4 (Tasks 8-9):** Created `AuditRevalidationService` with Phase A (UFC mis-match rejection by ID prefix) and Phase B (full LLM-based revalidation with batch processing, retry on failure, outcome label backfill). 8 new tests.
- **Phase 5 (Tasks 10-11):** Added `polymarketOutcomeLabel` and `kalshiOutcomeLabel` to `MatchSummaryDto` with `@ApiProperty` Swagger annotations. Updated `toSummaryDto()` mapping. Frontend: added "Outcome Direction" panel on match detail page, outcome column with mismatch warning on matches table.
- **Code Review #1:** Lad MCP primary reviewer found 1 actionable issue (trim ordering in normalize function — trailing whitespace could prevent suffix regex from matching). Fixed by adding `.trim()` before NFKD normalize.
- **Code Review #2:** Adversarial review found 1 HIGH, 5 MEDIUM, 3 LOW issues. All HIGH+MEDIUM fixed:
  - H1: Implemented complementary price check (AC 8 task 9.3) — optional `IPlatformConnector` injection with `@Optional()`, `Decimal` arithmetic for `polyBestAsk + kalshiBestAsk ≈ 1.00`, graceful skip when connectors unavailable. 5 new tests.
  - M1: Extracted `LLM_ALIGNMENT_THRESHOLD` to shared constant in `common/constants/matching-thresholds.ts` — eliminates drift risk between discovery and audit pipelines.
  - M2: Added exponential backoff (1s, 2s, 4s) to LLM retry in `auditWithLlm()`.
  - M3: Noted: migration `20260315191915_add_outcome_labels` includes an unrelated `risk_states.mode` type change — pre-existing, cannot be undone.
  - M4: Updated File List with `package.json` and `src/cli/audit-revalidation.ts`.
  - M5: Dashboard mismatch detection now uses `normalizeOutcomeLabel()` (NFKD + suffix stripping) instead of naive `toLowerCase()`.
- **Test count:** 2175 → 2217 (+42 new tests). All 121 test files green. Lint clean.
- **Design decision:** `OutcomeDirectionValidator` uses `IScoringStrategy.scoreMatch()` for LLM fallback rather than creating a separate LLM interface. The scoring prompt is generic enough to handle outcome label comparison via context injection.
- **Note:** Complementary price check uses optional connector injection (`@Optional()` + `@Inject` with string literal tokens). When run via `ContractMatchingModule` (no connectors), the check is skipped gracefully. When run via CLI `AuditModule`, connectors can be provided.

### File List

**Engine (pm-arbitrage-engine/) — files created:**
- `src/common/constants/matching-thresholds.ts` — Shared LLM alignment threshold constant
- `src/modules/contract-matching/outcome-direction-validator.ts` — Direction validation service
- `src/modules/contract-matching/outcome-direction-validator.spec.ts` — 13 tests
- `src/modules/contract-matching/audit-revalidation.command.ts` — Audit CLI service
- `src/modules/contract-matching/audit-revalidation.command.spec.ts` — 13 tests
- `src/cli/audit-revalidation.ts` — Standalone CLI entry point (NestFactory.createApplicationContext)
- `prisma/migrations/20260315191915_add_outcome_labels/migration.sql` — Schema migration (note: includes unrelated risk_states.mode type change)

**Engine (pm-arbitrage-engine/) — files modified:**
- `package.json` — Added `audit:revalidate` npm script
- `src/common/interfaces/contract-catalog-provider.interface.ts` — Added `OutcomeToken`, `outcomeLabel`, `outcomeTokens`
- `src/connectors/polymarket/polymarket-catalog-provider.ts` — Added `outcomes` parsing, `parseOutcomeTokens()` method
- `src/connectors/polymarket/polymarket-catalog-provider.spec.ts` — +6 outcome parsing tests
- `src/connectors/polymarket/polymarket-response.schema.ts` — Added `outcomes` to market schema
- `src/connectors/kalshi/kalshi-catalog-provider.ts` — Added `outcomeLabel` from `yes_sub_title`
- `src/connectors/kalshi/kalshi-catalog-provider.spec.ts` — +3 outcomeLabel tests
- `src/modules/contract-matching/candidate-discovery.service.ts` — Added direction validation gate, outcome label persistence
- `src/modules/contract-matching/candidate-discovery.service.spec.ts` — +4 direction validation gate tests
- `src/modules/contract-matching/contract-matching.module.ts` — Registered `OutcomeDirectionValidator` provider
- `src/dashboard/dto/match-approval.dto.ts` — Added `polymarketOutcomeLabel`, `kalshiOutcomeLabel` with Swagger annotations
- `src/dashboard/match-approval.service.ts` — Added outcome label mapping in `toSummaryDto()`
- `prisma/schema.prisma` — Added `polymarketOutcomeLabel`, `kalshiOutcomeLabel` columns

**Dashboard (pm-arbitrage-dashboard/) — files modified:**
- `src/api/generated/Api.ts` — Added outcome label fields to `MatchSummaryDto`
- `src/pages/MatchDetailPage.tsx` — Added "Outcome Direction" panel with mismatch warning
- `src/pages/MatchesPage.tsx` — Added outcome direction column with mismatch indicator
