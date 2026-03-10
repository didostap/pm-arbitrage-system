# Sprint Change Proposal — Epic 8: Add Candidate Discovery Pipeline

**Date:** 2026-03-09
**Triggered by:** Pre-implementation analysis of Epic 8 (Intelligent Contract Matching & Knowledge Base)
**Change scope:** Moderate — new story, new FR, architecture additions
**Approved by:** Arbi

---

## Section 1: Issue Summary

### Problem Statement

Epic 8 as specified has a gap in the end-to-end contract matching flow. Stories 8.1–8.3 define what happens after two contract descriptions are available for comparison: schema expansion (8.1), confidence scoring with auto-approve/review workflow (8.2), and resolution feedback (8.3). However, no story specifies how the system identifies which descriptions to compare.

There is no mechanism for the system to go from "here is Polymarket contract A" to "here are Kalshi contracts B1, B2, B3 that might be the same event." Without this, scaling from 20-30 manual pairs (MVP) to 50+ (Phase 1 target) depends entirely on the operator manually searching both platforms and hand-identifying candidates.

### Discovery Context

Identified during pre-implementation planning review of Epic 8, before any Epic 8 stories were started. The gap was discovered by tracing the data flow: FR-CM-01 (manual curation) feeds the MVP, but no FR specifies how Phase 1 automated scoring (FR-CM-02) gets its input. Story 8.2's acceptance criteria begin with "Given contract descriptions are available from both platforms" — a precondition that no story produces.

### Evidence

1. **Story 8.2 AC gap:** "Given contract descriptions are available from both platforms, When the confidence scorer analyzes a potential pair..." — the "given" clause has no producing story.
2. **PRD target mismatch:** Phase 1 Success Criteria require "50+ validated cross-platform contract pairs in knowledge base" — not achievable at scale with manual candidate identification.
3. **FR coverage gap:** FR-CM-01 [MVP] is manual curation. FR-CM-02 [Phase 1] is semantic matching. No FR covers discovery of which contracts to match.
4. **Architecture gap:** `contract-matcher.service.ts` is described as "MVP: manual pair lookup; Phase 1: NLP matching" — matching, not discovery.

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Detail |
|------|--------|--------|
| **Epic 8** | **Direct — story added** | New Story 8.4 (Cross-Platform Candidate Discovery Pipeline). Story order: 8.1 → 8.2 → 8.4 → 8.3. Epic description updated to reflect full pipeline. |
| Epic 9 | None | Operates on positions, not match discovery. |
| Epic 10 | None | Exit logic is downstream of matching. |
| Epic 11 | Minor positive | `IContractCatalogProvider` extends the plugin architecture — third-party connectors optionally implement it for automatic discovery participation. |
| Epic 12 | None | Audit/export is agnostic to match source. |

### Artifact Conflicts

**PRD:**
- No conflicts with existing FRs. Gap filled by adding FR-CM-05 [Phase 1] covering automated candidate discovery.
- FR Coverage Map updated to map FR-CM-05 → Epic 8.

**Architecture:**
- No conflicts. Additions only:
  - `IContractCatalogProvider` interface in `common/interfaces/` (separate from `IPlatformConnector`)
  - Three new files in `contract-matching/`: `candidate-discovery.service.ts`, `catalog-sync.service.ts`, `pre-filter.service.ts`
  - New dependency rule: `modules/contract-matching/ → connectors/` (via `IContractCatalogProvider`)
  - `LlmScoringError` (4100-4199) added as `SystemHealthError` subclass

**UI/UX:**
- No changes needed. Discovered candidates flow into Story 7.3's existing contract matching approval interface.

### Technical Impact

- **LLM API integration:** First external API dependency outside trading platforms and Telegram. Requires API key management (env vars now, secrets manager per Epic 11), error handling (`LlmScoringError`), and configurable model selection.
- **Scheduling:** Uses existing `@nestjs/schedule` infrastructure (same pattern as NTP sync, daily health digests). No new scheduling infrastructure needed.
- **Hot path:** Zero impact. Discovery runs asynchronously via cron, completely decoupled from detection → risk → execution cycle. If discovery fails, trading continues unaffected.

---

## Section 3: Recommended Approach

### Selected: Option 1 — Direct Adjustment

**Rationale:**
- The gap is a missing story in an unstarted epic — simplest possible change category
- No completed work is affected (Epics 1–7.5 are done; Epic 8 is backlog)
- No architectural conflicts — new components follow established patterns (interface-based DI, scheduled jobs, `SystemError` hierarchy)
- The discovery pipeline is fully decoupled from the trading hot path — zero risk to live operations
- All artifact changes are additions, not modifications to existing content (except minimal clarification on Story 8.2's scoring approach)

**Alternatives considered:**
- **Rollback:** Not applicable — nothing completed needs reverting
- **MVP scope review:** Not applicable — MVP is complete; this is Phase 1 scope

**Effort estimate:** Low-Medium. One new story (8.4 is substantial in implementation — three-stage pipeline — but well-scoped with clear interfaces).

**Risk level:** Low. Discovery is a cold scheduled job that feeds the existing scoring/approval pipeline. Failure mode is "no new candidates discovered this run" — the system continues operating on existing pairs.

**Timeline impact:** Adds ~1 story to Epic 8 implementation. No impact on other epics or overall project timeline.

---

## Section 4: Detailed Change Proposals

### 4.1 PRD Changes

**FR-CM-05 [Phase 1] added** after FR-CM-04:

> **FR-CM-05 [Phase 1]:** System shall automatically discover candidate cross-platform contract pairs by: (1) periodically syncing active contract catalogs from all connected platforms via scheduled batch job (1-2x daily, off the trading hot path), (2) applying deterministic pre-filters (category match, settlement date proximity, TF-IDF/cosine similarity on titles) to narrow the cross-product to plausible candidates, and (3) routing surviving candidates through the confidence scoring pipeline (FR-AD-05, FR-CM-02) for automated approval (≥85%) or operator review (<85%). Pairs already in the knowledge base (approved, rejected, or pending) are excluded from re-scoring.

### 4.2 Epic Changes

**Epic 8 description** updated to reflect full pipeline: "System automatically discovers candidate contract pairs from platform catalogs, scores confidence via semantic analysis, auto-approves high-confidence matches, and learns from resolution outcomes."

**FRs covered** updated: added FR-CM-05.

**FR Coverage Map** updated: `FR-CM-05: Epic 8 - Automated cross-platform candidate discovery`.

**Story 8.2 clarified** (minimal touch — three AC lines changed):
- Initial `IScoringStrategy` implementation uses LLM-based semantic analysis (cost-efficient model with optional escalation)
- Deterministic string-based analysis implemented as separate `PreFilterService` for candidate narrowing, not as primary scorer
- LLM provider, model selection, and escalation thresholds configurable via environment variables

**Story 8.4 added** — Cross-Platform Candidate Discovery Pipeline. Full acceptance criteria covering: scheduled catalog sync via `IContractCatalogProvider`, deterministic pre-filtering, routing through `ConfidenceScorerService`, `LlmScoringError` handling with queue-for-retry strategy, and optional `IContractCatalogProvider` for Epic 11 extensibility.

**Story order within Epic 8:** 8.1 → 8.2 → 8.4 → 8.3.

### 4.3 Architecture Changes

- `contract-catalog-provider.interface.ts` (`IContractCatalogProvider`) added to `common/interfaces/`
- `candidate-discovery.service.ts`, `catalog-sync.service.ts`, `pre-filter.service.ts` (with specs) added to `contract-matching/` directory tree
- Dependency rule added: `modules/contract-matching/ → connectors/` (via `IContractCatalogProvider`)
- `LlmScoringError` (4100-4199) added as `SystemHealthError` subclass in error hierarchy and directory tree

### 4.4 Sprint Status Changes

- Story `8-4-cross-platform-candidate-discovery-pipeline: backlog` added between 8-2 and 8-3
- Total stories updated: 68 → 69

---

## Section 5: Implementation Handoff

### Change Scope Classification: Moderate

New story within existing epic, new FR, architecture additions. No fundamental replan needed, but requires artifact updates beyond just code.

### Handoff

| Responsibility | Role | Action |
|---------------|------|--------|
| Artifact updates (PRD, Architecture, Epics, Sprint Status) | SM (this session) | **Complete** — all edits applied |
| Story 8.4 creation (detailed story file for dev) | SM via Create Story workflow | When Epic 8 sprint planning begins |
| Implementation | Dev agent | Sequential: 8.1 → 8.2 → 8.4 → 8.3 |

### Success Criteria

1. Discovery pipeline runs on schedule without affecting trading hot path
2. Candidates appear in existing dashboard approval interface (Story 7.3)
3. LLM failures are gracefully handled (queue for retry, never block)
4. `IContractCatalogProvider` is separate from `IPlatformConnector` and optional for new connectors
5. Phase 1 target of 50+ validated pairs becomes achievable without manual platform searching

### Dependencies

- Story 8.4 depends on 8.1 (knowledge base schema) and 8.2 (scoring interface)
- Story 8.2 and 8.4 could theoretically be developed in parallel if `IScoringStrategy` interface is agreed upfront, but sequential is more practical for solo developer to avoid integration risk
