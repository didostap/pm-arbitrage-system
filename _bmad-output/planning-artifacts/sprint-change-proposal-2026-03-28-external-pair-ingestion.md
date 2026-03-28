# Sprint Change Proposal — External Pair Ingestion into Live Discovery Pipeline

**Date:** 2026-03-28
**Author:** Bob (Scrum Master)
**Approved by:** Arbi
**Mode:** Incremental review
**Scope Classification:** Minor — direct implementation by dev team

---

## Section 1: Issue Summary

### Problem Statement

The system has two independent match-sourcing paths that don't feed each other:

- **Path A (live discovery):** `CandidateDiscoveryService` → catalog sync (Polymarket + Kalshi) → TF-IDF pre-filter → LLM scoring → `ContractMatch` creation. Expensive (LLM call per candidate pair), bounded by our own pre-filter quality and catalog completeness.
- **Path B (backtesting validation):** `MatchValidationService` → OddsPipe/Predexon fetch → cross-reference against our `ContractMatch` records → report. High-quality pre-matched data, but results are trapped in JSON report blobs as `external-only` entries.

OddsPipe provides 2,500+ auto-matched Polymarket-Kalshi pairs (free tier). Predexon provides cross-platform matching with 99%+ claimed accuracy ($49/mo). These services have already done the hard work of identifying cross-platform pairs. Our system fetches their data, compares it against our matches, and then **discards the novel pairs** — never ingesting them into the live discovery pipeline.

### Context

Discovered after Story 10-9-2 (Cross-Platform Pair Matching Validation) was completed. That story built the full validation infrastructure — `OddsPipeService.fetchMatchedPairs()`, `PredexonMatchingService.fetchMatchedPairs()`, cross-referencing logic, report persistence — but scoped it as read-only verification per Epic 10.9's backtesting focus. The gap became apparent once validation reports showed large numbers of `external-only` matches that our discovery pipeline never found.

### Evidence

- `OddsPipeService.fetchMatchedPairs()` — production-ready, tested (Story 10-9-1b, 64 tests)
- `PredexonMatchingService.fetchMatchedPairs()` — production-ready, tested (Story 10-9-2, 66 tests)
- `ConfidenceScorerService` + `OutcomeDirectionValidator` — existing LLM validation pipeline (Epic 8)
- `ExternalMatchedPair` type — already defined in `modules/backtesting/types/match-validation.types.ts`
- Validation reports categorize `external-only` pairs and flag them as `isKnowledgeBaseCandidate: true` — but nothing acts on that flag

---

## Section 2: Impact Analysis

### Epic Impact

- **Epic 10.9 (in-progress):** No modifications needed. Backtesting infrastructure remains as-is. Story 10-9-6 (historical data freshness) is independent.
- **Epic 8 (done):** Not reopened. This builds on Epic 8's scoring infrastructure but lives as a standalone story.
- **Epic 11, 12 (backlog):** No impact.

### Story Impact

**New standalone story added to sprint backlog:**
- External Pair Ingestion — feeds OddsPipe/Predexon matched pairs into the live discovery pipeline via LLM validation
- Prioritized above 10-9-6 and Epic 11 (directly expands arbitrage opportunity surface)
- Independent of 10-9-6 (can run in parallel)

### Artifact Conflicts

**PRD:** No conflict. Enhancement falls within existing FR scope:
- FR-AD-07: Accumulate contract matching knowledge base from resolved matches
- FR-CM-02: Semantic matching of contract descriptions and resolution criteria
- FR-CM-03: Store validated matches in knowledge base with confidence scores and outcomes

**Architecture:** Update required (approved during incremental review):
- New interface `IExternalPairProvider` in `common/interfaces/`
- Module dependency addition: `modules/contract-matching/` → `common/interfaces/` (IExternalPairProvider)
- Data flow update: OddsPipe/Predexon serve dual roles (backtesting validation + live discovery sourcing)
- No forbidden dependency violations — contract-matching imports interface, not backtesting services directly

**UI/UX:** No specification conflict. Source/origin field on `ContractMatch` (or metadata) is a required task to indicate candidate provenance (discovery pipeline vs. Predexon vs. OddsPipe) for operator review context.

### Technical Impact

- **Module boundary crossing:** Resolved via `IExternalPairProvider` interface in `common/interfaces/`. `OddsPipeService` and `PredexonMatchingService` implement it; `ExternalPairIngestionService` consumes via DI token.
- **Database schema:** Likely addition of `source` or `origin` field to `contract_matches` table (or use existing metadata JSON) to track candidate provenance.
- **Deduplication logic:** Critical design decision — `ExternalPairIngestionService` must determine which external pairs are genuinely new vs. already in `ContractMatch`. Options: composite key match (polymarketContractId + kalshiContractId), fuzzy title matching, or both. The story spec must be precise here since incorrect dedup leads to either missed opportunities (false positive dedup) or duplicate processing (false negative dedup).
- **No existing behavior changes:** Purely additive. Existing discovery pipeline, validation pipeline, and all scoring infrastructure remain unchanged.

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

Single standalone story added to sprint backlog. Additive change with high infrastructure reuse.

### Rationale

1. **High infrastructure reuse:** The services to fetch external pairs already exist and are battle-tested (`OddsPipeService`, `PredexonMatchingService` — shipped in Stories 10-9-1b and 10-9-2 with 130+ tests combined). The LLM scoring pipeline already exists (`ConfidenceScorerService`, `OutcomeDirectionValidator` — Epic 8). This is primarily a wiring exercise.

2. **Low risk:** No existing behavior changes. No rollback risk. The `IExternalPairProvider` interface cleanly decouples modules per existing architectural constraints.

3. **High value:** Every external-only pair that passes LLM validation becomes a new arbitrage opportunity. OddsPipe alone provides 2,500+ pre-matched pairs. Even if only 10-20% are novel (not already discovered by our pipeline), that's hundreds of potential new tradeable pairs.

4. **Cost efficiency:** LLM-validating pre-matched pairs from high-accuracy sources (Predexon 99%+) is cheaper than brute-force catalog discovery — skip TF-IDF pre-filter overhead, go straight to LLM scoring on high-confidence candidates.

### Effort Estimate

**Medium.** Key work items:
- `IExternalPairProvider` interface definition (straightforward — essentially `fetchPairs(): Promise<ExternalMatchedPair[]>`)
- `ExternalPairIngestionService` (new service: fetch → deduplicate → LLM score → create ContractMatch)
- DI wiring (backtesting module exports implementations, contract-matching module injects via token)
- Deduplication logic (the design-critical piece)
- Source/origin tracking on ContractMatch
- Integration with existing `CandidateDiscoveryService` scheduling (or independent cron)
- TDD test suite

### Risk Assessment

**Low.**
- No breaking changes to existing pipelines
- External API integration is already proven
- LLM scoring pipeline is production-tested
- Module boundary crossing is clean (interface-based DI)
- Only risk: dedup logic correctness (mitigated by precise spec + TDD)

### Timeline Impact

None on existing sprint. Story runs in parallel with remaining backlog.

---

## Section 4: Detailed Change Proposals

### 4.1 Architecture Update

**Module Dependencies — Allowed Imports:**

```
ADDITION:
modules/contract-matching/ → common/interfaces/ (IExternalPairProvider — consumes external pair sources)
```

**Data Flow:**

```
OLD:
├── OddsPipe (matched pairs + OHLCV)
├── Predexon (cross-platform matching validation)
├── MatchValidationService (cross-ref our matches vs OddsPipe/Predexon)

NEW:
├── OddsPipe (matched pairs for discovery + OHLCV for backtesting)
├── Predexon (matched pairs for discovery + validation for backtesting)
├── MatchValidationService (cross-ref accuracy reporting)
├── ExternalPairIngestionService (feeds external-only pairs → ConfidenceScorerService → ContractMatch)
```

**Forbidden Dependencies:** No violation. `contract-matching` imports `IExternalPairProvider` from `common/interfaces/`, never imports backtesting services directly. Implementations are injected via DI token.

### 4.2 New Story: External Pair Candidate Ingestion

**Story Title:** External Pair Candidate Ingestion via OddsPipe & Predexon

**As** an operator,
**I want** the discovery pipeline to proactively import matched pairs from OddsPipe and Predexon as LLM scoring candidates,
**So that** the system discovers arbitrage opportunities beyond what catalog brute-force finds, substantially expanding the tradeable pair universe.

**Key Design Decisions (must be addressed in story spec):**

1. **Deduplication strategy:** Dual-path dedup based on provider data quality. **Predexon** (provides contract IDs): deterministic composite key match (`polymarketContractId` + `kalshiContractId`) — no ambiguity. **OddsPipe** (titles only): fuzzy title matching with a conservative threshold — **bias toward inclusion** (re-score over skip). A duplicate LLM call costs fractions of a cent; a missed arbitrage opportunity costs real money. The spec must set an explicit fuzzy dedup threshold that errs toward letting borderline candidates through to LLM scoring rather than aggressively filtering them out.

2. **Scheduling:** **Independent cron**, separate from `CandidateDiscoveryService`. The catalog discovery pipeline already does catalog sync + TF-IDF pre-filter + LLM scoring in one cycle — adding external API fetches extends that critical path and muddies failure modes. `ExternalPairIngestionService` runs on its own schedule (once or twice daily — external pair lists don't change minute-to-minute). Keeps concerns clean, failure isolation clear.

3. **Source tracking:** Required `origin` field (or equivalent) on `ContractMatch` to distinguish `discovery`, `predexon`, `oddspipe`, and `manual` (legacy YAML pairs). Operator uses this during review to calibrate scrutiny level — a Predexon-sourced candidate (99%+ accuracy) warrants less scrutiny than an OddsPipe-sourced one (fuzzy matching).

**Acceptance Criteria (high-level — full spec in story file):**

- `IExternalPairProvider` interface defined in `common/interfaces/` with `fetchPairs(): Promise<ExternalMatchedPair[]>` and `getSourceId(): string` (provider identifier for origin tracking without inspecting pair data)
- `OddsPipeService` and `PredexonMatchingService` implement `IExternalPairProvider`
- `ExternalPairIngestionService` fetches pairs from all registered providers
- External pairs are deduplicated against existing `ContractMatch` records (by composite ID for Predexon, by composite ID + fuzzy title for OddsPipe)
- Novel pairs are scored through `ConfidenceScorerService` (same LLM pipeline as catalog discovery)
- Novel pairs are validated through `OutcomeDirectionValidator`
- Scored pairs are persisted as `ContractMatch` records with `origin` field set
- Auto-approve/review/reject thresholds match existing discovery pipeline configuration
- `ContractMatch` table has `origin` field (migration) indicating source: `discovery`, `predexon`, `oddspipe`, `manual`
- Dashboard matches table displays origin for operator context
- Discovery run stats track external-sourced candidates separately (fetched, deduplicated, scored, approved, rejected)
- Existing discovery pipeline behavior unchanged
- Event emission follows existing patterns (`MatchApprovedEvent`, `MatchPendingReviewEvent`, etc.)
- When an external provider is unreachable (API down, rate limited, auth failure), the ingestion run degrades gracefully — processes pairs from available providers and logs the failure. A single provider outage must not fail the entire run. Mirrors existing `MatchValidationService` pattern where missing Predexon source degrades the report but doesn't block it.

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by development team. No backlog reorganization or fundamental replan needed.

### Handoff

| Role | Responsibility |
|------|---------------|
| SM (Bob) | Update sprint-status.yaml, sequence story in backlog |
| Architect (Winston) | Review story spec (IExternalPairProvider contract, dedup strategy, origin schema) |
| Dev (Serena) | Implement via TDD — interface, service, DI wiring, migration, dashboard origin display |
| Arbi | Review and approve story spec before implementation begins |

### Sequencing

1. **Story spec creation** (via `bmad-create-story`) — include all design decisions above
2. **Implementation** — TDD cycle per CLAUDE.md conventions
3. **Code review** — 3-layer adversarial (standard for this project)
4. 10-9-6 can proceed in parallel

### Success Criteria

- External pairs from OddsPipe and Predexon appear as `ContractMatch` records after ingestion run
- Operator can distinguish external-sourced matches from discovery-sourced in dashboard
- No regression in existing discovery pipeline behavior
- Dedup logic prevents duplicate ContractMatch records
- LLM scoring and direction validation applied to all external candidates
- All tests green, lint clean
