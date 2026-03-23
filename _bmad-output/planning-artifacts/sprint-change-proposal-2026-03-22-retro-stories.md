# Sprint Change Proposal — Epic 10 Retro Action Items into Epic 10.5

**Date:** 2026-03-22
**Triggered by:** Epic 10 retrospective findings (2026-03-22)
**Scope Classification:** Moderate
**Approved:** Yes — 2026-03-22

---

## Section 1: Issue Summary

**Problem Statement:** Epic 10 retrospective identified 3 recurring defect classes (event wiring gaps 44%, collection leaks 33%, paper/live mode contamination 22%) that are structural risks requiring enforcement before Epic 11 opens the connector interface to plugin architecture. Additionally, 3 new team agreements (#24, #25, #26) and process improvements need to be codified as deliverables, and an external secrets management spike is needed to unblock Epic 11.2.

**Discovery Context:** Epic 10 retrospective (2026-03-22), completed after 9/9 stories delivered. The retro produced 7 action items, originally planned as pre-Epic 11 stories (11-0-1 through 11-0-4) plus parallel prep tasks. This proposal moves all retro action items into Epic 10.5, consolidating all pre-Epic 11 work into a single epic.

**Evidence:**
- 4/9 Epic 10 stories had event wiring gaps caught in code review (44% recurrence)
- 3/9 stories had unbounded collection leaks (33%)
- 2/9 stories had paper/live mode contamination (22%)
- Story 10.1 post-deploy bug: missing `is_paper` SQL filter caused paper positions to trigger LIVE halt
- Story 10-0-1 oversized: 7 phases, 17 tasks, 5 CRITICAL findings — drives story sizing gate
- Epic 9 action item #3 (MEDIUM prevention analysis) not addressed — 1 full epic as orphan
- 69KB exit-monitor spec file maintenance burden
- Epic 10 retro key insight: "Disciplines drift, deliverables ship" → Agreement #24

---

## Section 2: Impact Analysis

### Epic Impact
- **Epic 10:** Complete (9/9). No modifications.
- **Epic 10.5:** Expanded from 3 stories (settings only) to 8 stories (settings + structural guards + process + research).
- **Epic 11:** Pre-epic stories 11-0-1 through 11-0-4 removed. Epic 11 starts clean with feature stories only (11.1, 11.2, 11.3). No dependency conflicts — structural guard prerequisites now satisfied by Epic 10.5.
- **Epic 12:** No impact.

### Story Impact
- No existing stories modified.
- 5 new stories added to Epic 10.5 (10-5-4 through 10-5-8).
- 4 planned pre-Epic 11 stories (11-0-1 through 11-0-4) absorbed — will not be created.

### Artifact Conflicts
- **PRD:** No conflict. Structural guards and process hardening fulfill quality requirements more completely.
- **Architecture:** No conflict. Event wiring verification, collection lifecycle guards, and mode boundary enforcement are refinements, not changes.
- **CLAUDE.md:** Updated by Story 10-5-8 with new conventions from 10-5-4 and 10-5-5.
- **Story creation checklist:** Updated by Story 10-5-8 with story sizing gate (Agreement #25).
- **sprint-status.yaml:** New story entries for 10-5-4 through 10-5-8. No 11-0-x entries needed.
- **epics.md:** Expanded Epic 10.5 definition. Epic 11 pre-epic references cleaned up.

### Technical Impact
- `expectEventHandled()` integration test helper added to `common/testing/`
- Paper/live mode boundary test suite (`paper-live-boundary.spec.ts`) added
- Exit-monitor spec file decomposed from 1 × 69KB to ~8 × <15KB files
- CLAUDE.md gains 5 new conventions (event wiring, collection lifecycle, mode boundary, story sizing, retro-as-deliverables)
- No architectural changes. No new dependencies.

---

## Section 3: Recommended Approach

**Selected Path:** Option 1 — Direct Adjustment

**Rationale:**
- The retro already defined clear deliverables with owners and success criteria — these translate directly to stories with ACs.
- Moving retro items into Epic 10.5 (vs. keeping as 11-0-x) consolidates all pre-Epic 11 work into one epic, simplifying tracking and sequencing.
- Settings stories (10-5-1 through 10-5-3) and structural guard stories (10-5-4 through 10-5-6) are fully parallelizable — no timeline extension for the settings track.
- Follows Agreement #24: disciplines encoded as deliverables, not aspirational commitments.
- Agreement #22 correction budget: 8 base stories with 30-40% buffer → expect 10-12 total.

**Effort Estimate:** Medium (5 new stories, each low-to-medium complexity — no new production features, primarily testing infrastructure, audits, research, and documentation)
**Risk Level:** Low — proven patterns, no architectural novelty, clear deliverables
**Timeline Impact:** Minimal on settings track (parallel). Epic 10.5 duration extends to accommodate 8 stories, but two independent tracks run concurrently.

---

## Section 4: Detailed Change Proposals

### Epic 10.5 Redefinition

**OLD title:** Settings Infrastructure — DB-Backed Configuration & Dashboard Settings Page

**NEW title:** Settings Infrastructure, Structural Guards & Process Hardening

**NEW description:** Move operational env vars to DB-backed settings with dashboard UI. Establish structural enforcement for the three recurring defect classes identified in Epic 10 retro (event wiring, collection lifecycle, paper/live mode contamination). Codify new conventions and process gates before Epic 11 begins.

**Capacity Budget (Agreement #22):** 8 base stories. With 30-40% correction buffer → expect 10-12 total.

---

### Story Sequencing

| Track | Stories | Dependencies |
|---|---|---|
| Settings (sequential) | 10-5-1 → 10-5-2 → 10-5-3 | Internal chain |
| Structural Guards (parallel) | 10-5-4, 10-5-5, 10-5-6 | Independent of each other and settings |
| Research (parallel) | 10-5-7 | Independent |
| Documentation (last) | 10-5-8 | After 10-5-4 and 10-5-5 |

---

### Story 10-5-4: Event Wiring Verification & Collection Lifecycle Guards

As an operator,
I want automated verification that event emitters are connected to their subscribers and that in-memory collections have cleanup paths,
So that the two most common silent correctness failures (44% and 33% recurrence in Epic 10) are caught by tests instead of review.

**Context:** Epic 10 retro identified event wiring gaps in 4/9 stories and unbounded collection leaks in 3/9 stories. Both share the "silent correctness failure" shape — no error thrown, unit tests pass, handler logic correct in isolation. Agreement #26 mandates structural guards over review vigilance.

**Acceptance Criteria:**

**Given** the EventEmitter2 wiring pattern used across modules
**When** a new `@OnEvent` handler is added
**Then** an `expectEventHandled()` integration test helper exists that verifies: (1) the event is emitted by the expected service, (2) a handler with matching decorator exists, (3) the handler is actually invoked when the event fires through the real EventEmitter2

**Given** the test helper is available
**When** existing event wiring is audited
**Then** all existing `@OnEvent` handlers have corresponding `expectEventHandled()` tests
**And** any dead handlers (decorated but never triggered) are identified and removed

**Given** a story introduces a new `@OnEvent` handler
**When** the developer writes tests
**Then** a test template exists (co-located in `common/testing/`) demonstrating the `expectEventHandled()` pattern
**And** the story creation checklist requires event wiring tests for any story with event-driven behavior

**Given** in-memory collections (Map, Set, arrays used as caches)
**When** the codebase is audited
**Then** every Map/Set/cache has a documented cleanup path (TTL, max-size eviction, or lifecycle-bound disposal)
**And** CLAUDE.md documents the collection lifecycle convention: "Every new Map/Set must specify its cleanup strategy in a code comment and have a test for the cleanup path"

**Given** the MEDIUM prevention analysis (retro action item #3 deliverable)
**When** completed
**Then** the top 3 recurring MEDIUM categories from Epic 10 code reviews are documented with structural prevention measures (not "be more careful" agreements)

**Dependencies:** None (can run in parallel with settings stories)
**Blocks:** Epic 11.1 (plugin architecture)

---

### Story 10-5-5: Paper/Live Mode Boundary Inventory & Test Suite

As an operator,
I want every `isPaper`/`is_paper` branch in the codebase inventoried and covered by dual-mode tests,
So that the mode contamination defect class (22% recurrence in Epic 10, including a post-deploy bug in 10.1) is structurally prevented.

**Context:** Epic 10 retro identified paper/live mode contamination in 2/9 stories. Story 10.1 had a post-deploy bug where raw SQL `SELECT COUNT(*) FROM open_positions WHERE status IN (...)` did NOT filter by `is_paper`, causing 3 paper positions to trigger a LIVE halt. Story 10-0-2a fixed `validatePosition` mode-awareness but a dedicated boundary test suite was never completed (Epic 9 action item #5 — partial).

**Acceptance Criteria:**

**Given** the full codebase
**When** an `isPaper`/`is_paper` branch inventory is performed
**Then** a document lists every location where behavior diverges based on mode: service methods, repository queries, raw SQL, Prisma queries, event handlers, connectors
**And** each location is categorized: (a) has dual-mode test coverage, (b) needs test coverage, (c) structurally cannot contaminate

**Given** the inventory identifies gaps (category b)
**When** tests are written
**Then** a `paper-live-boundary.spec.ts` integration test file exists covering all category (b) locations
**And** each test verifies that paper-mode operations do not affect live-mode state and vice versa
**And** the test file is organized by module (risk, execution, exit, reconciliation, detection)

**Given** Prisma repository queries that filter by mode
**When** the inventory is complete
**Then** all repository methods that query `open_positions`, `orders`, or `risk_states` with status filters also include `is_paper` filtering
**And** a shared repository pattern or helper enforces mode-scoping (e.g., `withModeFilter(isPaper)` Prisma middleware or shared `where` clause builder)

**Given** raw SQL queries exist in the codebase
**When** they reference mode-sensitive tables
**Then** every raw SQL query includes `is_paper` filtering
**And** a code comment convention is established: `-- MODE-FILTERED` marker on compliant queries

**Given** a new story introduces mode-dependent behavior
**When** the developer writes tests
**Then** the story creation checklist requires dual-mode test coverage for any `isPaper` branch
**And** CLAUDE.md documents the paper/live boundary convention

**Dependencies:** None (can run in parallel with settings stories and 10-5-4)
**Blocks:** Epic 11.1 (plugin architecture — new connectors must handle mode correctly)

---

### Story 10-5-6: Exit-Monitor Spec File Split

As an operator,
I want the 69KB exit-monitor spec file decomposed into focused test files,
So that test maintenance burden is reduced and individual exit criteria can be tested, debugged, and modified independently.

**Context:** Epic 10 retro flagged `exit-monitor.service.spec.ts` at 69KB as a maintenance burden (Medium debt). The file covers six exit criteria (C1-C6), shadow mode comparison, threshold evaluation, WebSocket data integration, and position lifecycle — all in a single file. Story 10.2 expanded it significantly. The file is too large for efficient navigation, and failures in one criterion's tests obscure failures in others.

**Acceptance Criteria:**

**Given** the current `exit-monitor.service.spec.ts` (69KB)
**When** the split is complete
**Then** the spec file is decomposed into focused files, each under 15KB
**And** file naming follows the pattern: `exit-monitor-{concern}.spec.ts` (e.g., `exit-monitor-edge-evaporation.spec.ts`, `exit-monitor-shadow-mode.spec.ts`)

**Given** the decomposed spec files
**When** tests are run
**Then** zero test coverage regression — all existing tests pass in their new locations
**And** `pnpm test` reports the same number of passing exit-monitor tests before and after the split

**Given** shared test setup (mocks, fixtures, helpers)
**When** multiple spec files need the same setup
**Then** shared setup is extracted to a `exit-monitor.test-helpers.ts` file co-located in the same directory
**And** each spec file imports only the helpers it needs (no monolithic `beforeEach`)

**Given** the six-criteria model (C1-C6)
**When** a suggested split structure is defined
**Then** at minimum these files exist:
- `exit-monitor-core.spec.ts` — position lifecycle, evaluation loop, mode switching
- `exit-monitor-edge-evaporation.spec.ts` — C1
- `exit-monitor-confidence-drop.spec.ts` — C2
- `exit-monitor-time-decay.spec.ts` — C3
- `exit-monitor-risk-budget.spec.ts` — C4
- `exit-monitor-liquidity.spec.ts` — C5
- `exit-monitor-profit-capture.spec.ts` — C6
- `exit-monitor-shadow-mode.spec.ts` — shadow vs fixed comparison

**Given** this is a refactoring story
**When** scope is evaluated
**Then** no production code changes — only spec file reorganization
**And** no new tests added (that's for feature stories)

**Dependencies:** None (can run in parallel with all other 10.5 stories)
**Blocks:** Epic 11.1 (clean test structure needed before connector changes touch exit paths)

---

### Story 10-5-7: External Secrets Management Research Spike

As an operator,
I want a design document mapping the system's credential surface to a secrets manager integration,
So that Story 11.2 (External Secrets Management Integration) starts with zero open architectural questions.

**Context:** Epic 11 includes Story 11.2 (External Secrets Management) and Story 11.3 (Zero-Downtime Key Rotation). Both require decisions about provider selection, credential lifecycle, fallback strategy, and integration pattern. This spike produces a design document, not implementation — following the investigation-first pattern validated in Epic 10 (Story 10-0-3).

**Acceptance Criteria:**

**Given** the system's current credential surface
**When** the spike is completed
**Then** a design document exists covering:
- Complete inventory of all credentials/secrets in the system (Kalshi API key/secret, Polymarket private key, operator Bearer token, PostgreSQL password, Telegram bot token, LLM API keys)
- Which credentials are used at startup-only vs. runtime-refreshable
- Current storage mechanism for each (env var, file path, in-memory)

**Given** the secrets manager landscape
**When** providers are evaluated
**Then** the design document includes a provider comparison with recommendation:
- AWS Secrets Manager, HashiCorp Vault, and at least one lightweight alternative (e.g., SOPS, age-encrypted files for solo operator use case)
- Evaluation criteria: cost at solo-operator scale, complexity, SDK maturity for Node.js/NestJS, rotation support, audit logging
- Clear recommendation with rationale

**Given** the recommended provider
**When** the integration pattern is designed
**Then** the design document covers:
- Credential lifecycle model: fetch → cache → use → refresh → invalidate
- NestJS integration pattern (custom ConfigFactory, provider, or module)
- Fallback strategy when secrets manager is unavailable (env var fallback with degraded-security alert)
- How this interacts with Story 10-5-2's `getEffectiveConfig()` pattern (secrets are NOT in EngineConfig DB — clear boundary)
- Key rotation mechanics: how `POST /api/admin/rotate-credentials/:platform` (Story 11.3) triggers re-fetch

**Given** this is a spike
**When** scope is evaluated
**Then** no production code is written — output is a design document
**And** the document is reviewed by Winston (architecture) before the spike is marked complete
**And** the spike follows the investigation-first pattern (Team Agreement from Epic 9 retro)

**Dependencies:** None (research, can run in parallel with everything)
**Blocks:** Epic 11.2 (External Secrets Management Integration)

---

### Story 10-5-8: CLAUDE.md, Story Template & Process Convention Updates

As an operator,
I want all Epic 10 retro conventions, structural guard patterns, and process improvements documented in CLAUDE.md and the story creation checklist,
So that the dev agent follows these conventions automatically and Epic 11 stories are created with the new sizing and verification gates.

**Context:** Epic 10 retro produced 3 new team agreements (#24 disciplines as deliverables, #25 story sizing gate, #26 structural guards over vigilance), identified 3 recurring defect classes needing conventions, and generated structural enforcement stories (10-5-4, 10-5-5) whose patterns need to be codified. This story is the documentation counterpart — encoding the new norms so they persist beyond the retro document.

**Acceptance Criteria:**

**Given** Story 10-5-4 delivers event wiring verification patterns
**When** CLAUDE.md is updated
**Then** the following conventions are documented:
- Event wiring convention: every `@OnEvent` handler requires an `expectEventHandled()` integration test
- Collection lifecycle convention: every new Map/Set must specify cleanup strategy in a code comment and have a test for the cleanup path
- Top 3 MEDIUM prevention measures from the MEDIUM analysis (10-5-4 deliverable)

**Given** Story 10-5-5 delivers paper/live boundary patterns
**When** CLAUDE.md is updated
**Then** the following conventions are documented:
- Paper/live boundary convention: every `isPaper` branch requires dual-mode test coverage
- Repository mode-scoping pattern (shared `withModeFilter` or equivalent from 10-5-5)
- Raw SQL `-- MODE-FILTERED` marker convention

**Given** Agreement #25 (story sizing gate)
**When** the story creation checklist is updated
**Then** a sizing gate is added: "Stories exceeding 10 tasks or 3+ integration boundaries are flagged for splitting"
**And** the gate is a checklist item during story preparation, not a post-implementation observation

**Given** Agreement #24 (retro commitments as deliverables)
**When** CLAUDE.md is updated
**Then** the retrospective section documents: "Every retro action item must be expressible as a story with ACs or a task within a story. Open-ended discipline commitments without enforcement are rejected at retro time."

**Given** Agreement #26 (structural guards over review vigilance)
**When** CLAUDE.md is updated
**Then** the code review section documents: "If review catches the same defect category three times across an epic, it becomes a pre-epic story with structural prevention — not a 'be more careful' agreement."

**Given** this story depends on patterns established by 10-5-4 and 10-5-5
**When** sequencing is evaluated
**Then** this story is implemented after 10-5-4 and 10-5-5 are complete (so documented patterns match actual implementation)

**Dependencies:** 10-5-4 (event wiring patterns), 10-5-5 (paper/live patterns)
**Blocks:** Epic 11 story creation (SM needs updated checklist before writing Epic 11 stories)

---

## Section 5: Implementation Handoff

**Change Scope:** Moderate — 5 new stories added to existing epic, proven patterns, no architectural changes.

**Handoff:** Dev agent implements stories across two parallel tracks:

**Track A — Settings (sequential, unchanged):**
1. **10-5-1** (schema + seed) → **10-5-2** (API + hot-reload) → **10-5-3** (dashboard UI)

**Track B — Structural Guards & Research (parallel):**
4. **10-5-4** (event wiring + collection lifecycle) — parallel with Track A
5. **10-5-5** (paper/live boundary inventory) — parallel with Track A
6. **10-5-6** (exit-monitor spec split) — parallel with everything
7. **10-5-7** (secrets management spike) — parallel with everything

**Track C — Documentation (depends on Track B):**
8. **10-5-8** (CLAUDE.md + checklist updates) — after 10-5-4 and 10-5-5

**Epic 11 Cleanup:**
- Remove pre-epic stories 11-0-1 through 11-0-4 from planning. Epic 11 starts with 11.1, 11.2, 11.3 only.

**Success Criteria:**
- `expectEventHandled()` helper exists and covers all existing `@OnEvent` handlers
- Every Map/Set has documented cleanup path
- Zero `isPaper` branches without dual-mode test coverage
- Exit-monitor spec decomposed into files each <15KB, zero coverage regression
- Secrets management design document reviewed and approved by Winston
- CLAUDE.md updated with 5 new conventions
- Story creation checklist includes sizing gate
- All 79 tunables editable via Settings page without restart (unchanged from original 10.5)

**Sprint Status Updates Required:**
- Add stories `10-5-4` through `10-5-8` as backlog in Epic 10.5
- Update Epic 10.5 title and summary statistics
- Do NOT add 11-0-x stories — they are absorbed by 10-5-4 through 10-5-8
